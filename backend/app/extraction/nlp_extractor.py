"""Offline NLP extractor: page text -> source-grounded Facts.

No external model or API is needed. The extractor uses the product KB as a
gazetteer and applies light linguistic processing:

* sentence segmentation, every fact keeps its sentence as a verbatim quote
* longest-match-first term spotting ("cashmere-feel" is not "cashmere",
  "down-alternative" is not down, the bare word "down" never matches)
* activity recognition = KB phrase, or a verb of the right kind
  (manufacture / scour / trade / farm ...) + a KB object noun in one sentence
* negation scope ("we do not use duck down" -> negative fact)
* direction of trade (buy/source/import vs. sell/supply/export)
* exclusivity cues ("all our", "100%", "only") and product-line detection
* linking a material to an activity (same sentence -> product noun of a
  performed activity -> activity on the same page)

It never invents anything: no sentence, no fact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..knowledge.schema import Evidence, Fact, ProductKB
from ..reasoning.engine import CompanyFacts

VERBS = {
    "manufacturing": r"manufactur\w*|produc(?:e|es|ed|ing|tion)|factor(?:y|ies)|workshops?|mills?|"
                     r"hand-?build\w*|sew(?:s|n|ing)?|knit(?:s|ted|ting)?|"
                     r"weav(?:e|es|ing)|woven|spin(?:s|ning)?|spun|tuft(?:s|ed|ing)?",
    "processing": r"scour\w*|wash(?:es|ed|ing)?|sort(?:s|ed|ing)?|grad(?:e|es|ed|ing)|"
                  r"process(?:es|ed|ing)?|de-?hair\w*|comb(?:s|ed|ing)?|clean(?:s|ed|ing)?",
    "trading": r"trad(?:e|es|ed|ing|er|ers)|import(?:s|ed|ing|er|ers)?|export\w*|merchants?|"
               r"brokers?|distribut\w*|wholesal\w*",
    "producer": r"farm(?:s|ing)?|rais(?:e|es|ed|ing)|breed\w*|herd\w*|graz\w*|shear\w*|growers?",
}
VERB_RE = {kind: re.compile(rf"(?<![\w-])(?:{p})(?![\w-])") for kind, p in VERBS.items()}
BUY_RE = re.compile(r"(?<![\w-])(?:buy(?:s|ing)?|bought|purchas\w*|procur\w*|sourc(?:e|es|ed|ing))(?![\w-])")
SELL_RE = re.compile(r"(?<![\w-])(?:sell(?:s|ing)?|sold|suppl(?:y|ies|ied|ying)|export\w*)(?![\w-])")
# The negation must govern the material directly: "no duck down", "never use duck down",
# "free of down", "without any wool" - not "No irritation from the sheep's wool".
NEGATION_RE = re.compile(
    r"(?<![\w-])(?:no|not|never|without|free of|free from|don't|doesn't|do not|does not)"
    r"(?:\s+(?:use|uses|using|contain|contains|include|includes|any|real|natural))*\s+(?:[\w%'-]+\s+)?$"
)
EXCLUSIVE_RE = re.compile(r"(?<![\w-])(?:all our|100%|only|exclusively|entirely|solely)(?![\w-])|100%")
RETAIL_RE = re.compile(
    r"(?<![\w-])(?:shop (?:our|the|now|online)|shop online|buy now|add to (?:cart|basket)|"
    r"free (?:delivery|shipping|returns)|discover (?:our|the)|our collection|new collection|"
    r"online (?:shop|store)|our boutiques?)(?![\w-])"
)
OUTSOURCED_RE = re.compile(
    r"(?<![\w-])(?:manufactured|produced|made|crafted|knitted|sewn|woven|filled)\b[^.]{0,40}?\bby\b(?![^.]{0,6}\b(?:us|hand|our own)\b)"
    r"|(?<![\w-])(?:our|trusted|selected) (?:partner|supplier|manufacturer)s?\b"
    r"|(?<![\w-])partner (?:workshops?|factories|factory|mills?|manufacturers?)\b"
    r"|(?<![\w-])third[- ]party\b|(?<![\w-])we (?:only |just )?(?:retail|resell|distribute)\b"
)
OWN_PRODUCTION_RE = re.compile(r"(?<![\w-])(?:our own|in-house|in house|we manufacture|we produce|our factory|our mill|our workshop)\b")
SELF_RE = re.compile(r"(?<![\w-])(?:we|our|ours|us|we're|we've)(?![\w-])")
SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")

ENGLISH_STOPWORDS = frozenset(
    "the and of to in our we for is are with a an from by on at as that this it be our "
    "us you your has have all each every can which or into".split()
)
MIN_ENGLISH_RATIO = 0.15


@dataclass
class PageText:
    url: str
    page_type: str
    text: str


def term_regex(term: str, plural: bool = True) -> re.Pattern:
    words = [re.escape(w) for w in term.lower().split()]
    body = r"[\s-]+".join(words)
    suffix = "(?:s|es)?" if plural else ""
    return re.compile(rf"(?<![\w-]){body}{suffix}(?![\w-])")


def latin_share(text: str) -> float:
    """Share of letters that are Latin script (Japanese/Chinese/Cyrillic pages score low)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0
    return sum(c.isascii() or "À" <= c <= "ɏ" for c in letters) / len(letters)


def page_is_english(text: str) -> bool:
    return latin_share(text) >= 0.7 and is_english(text)


def is_english(text: str) -> bool:
    tokens = re.findall(r"[a-zà-ÿ']+", text.lower())
    if len(tokens) < 20:
        return True  # too short to judge; sufficiency handles tiny pages
    return sum(t in ENGLISH_STOPWORDS for t in tokens) / len(tokens) >= MIN_ENGLISH_RATIO


class NLPExtractor:
    name = "nlp"

    def __init__(self, kb: ProductKB):
        self.kb = kb
        # (regex, material) ordered longest term first, so the longest match wins
        self.material_terms = sorted(
            ((term_regex(t), m, len(t)) for m in kb.materials.values() for t in m.terms),
            key=lambda x: -x[2],
        )
        self.activity_terms = [(term_regex(t, plural=a.kind != "retail"), a)
                               for a in kb.activities.values() for t in a.terms]
        self.activity_objects = [
            (term_regex(o), a) for a in kb.activities.values() for o in a.objects
        ]
        self.activity_verbs = {
            a.id: re.compile(rf"(?<![\w-])(?:{a.verbs})(?![\w-])") for a in kb.activities.values() if a.verbs
        }
        self.app_terms = [(term_regex(t), app, t) for app in kb.applications.values() for t in app.terms]
        self.line_terms = sorted(
            {t for app in kb.applications.values() for t in app.terms}
            | {o for a in kb.activities.values() for o in a.objects if a.kind == "manufacturing"},
            key=len, reverse=True,
        )

    # ------------------------------------------------------------------
    def extract(self, company_key: str, pages: list[PageText], company_name: str | None = None) -> CompanyFacts:
        official = [p for p in pages if p.page_type not in {"snippet", "directory", "third_party"}]
        # Only English pages are analysed; text we cannot read is never used as evidence.
        readable = [p for p in official if page_is_english(p.text)]
        sentences = []  # (page, original sentence, lowercased, offset)
        for p in readable:
            for m in SENTENCE_RE.finditer(p.text):
                original = m.group().strip()
                if len(original) >= 3:
                    sentences.append((p, original, _mask_name(original.lower(), company_name), m.start()))

        builder = _FactBuilder()
        # pass 1: activities
        sentence_activities: dict[int, list[str]] = {}
        page_activities: dict[str, list[str]] = {}
        name_rx = _name_regex(company_name)
        about_self = [self._about_self(original, name_rx) for _, original, _, _ in sentences]
        for i, (p, original, low, offset) in enumerate(sentences):
            spans = self._material_spans(low)
            # an activity counts only when the sentence is about this company ("we", "our", its name)
            found = self._activities(low, spans)
            if not about_self[i]:  # retail wording ("online shop") needs no subject
                found = [a for a in found if self.kb.activities[a].kind == "retail"]
            sentence_activities[i] = found
            for act in found:
                page_activities.setdefault(p.url, []).append(act)
                builder.add("performs", act, p, original, offset)
        performed = {a for acts in sentence_activities.values() for a in acts}

        # pass 2: materials, trade direction, retail statements
        for i, (p, original, low, offset) in enumerate(sentences):
            spans = self._material_spans(low)
            line = self._product_line(low)
            buys, sells = bool(BUY_RE.search(low)), bool(SELL_RE.search(low))
            for start, end, material in spans:
                negated = bool(NEGATION_RE.search(low[max(0, start - 40):start]))
                # weak (ambiguous) mentions must be tied to an activity in their own sentence
                on_page = [] if material.role == "ambiguous" else page_activities.get(p.url, [])
                link = self._link(low, sentence_activities[i], performed, on_page)
                attrs = {"linked_activity": link, "product_line": line}
                if material.role == "alternative":
                    # the cue must govern this material: "100% polyester", "all our duvets use polyester"
                    attrs["exclusive"] = bool(EXCLUSIVE_RE.search(low[max(0, start - 60):start]))
                    builder.add("uses_alternative", material.id, p, original, offset, not negated, attrs)
                    continue
                builder.add("uses_material", material.id, p, original, offset, not negated, attrs)
                if negated:
                    continue
                if buys and about_self[i]:
                    builder.add("sources", material.id, p, original, offset)
                if sells and about_self[i]:
                    builder.add("supplies", material.id, p, original, offset)
            if RETAIL_RE.search(low):
                for rx, app, _ in self.app_terms:
                    if rx.search(low):
                        builder.add("sells_finished", app.id, p, original, offset)
                        break

        total_chars = sum(len(p.text) for p in official)
        readable_chars = sum(len(p.text) for p in readable)
        return CompanyFacts(
            company_key=company_key,
            facts=builder.facts(),
            pages_fetched=len(official),
            text_chars=readable_chars,
            english=bool(readable) or not official,
            non_english_share=(1 - readable_chars / total_chars) if total_chars else 0.0,
        )

    # ------------------------------------------------------------------
    def _material_spans(self, low: str):
        taken: list[tuple[int, int, object]] = []
        for rx, material, _ in self.material_terms:
            for m in rx.finditer(low):
                if any(m.start() < e and s < m.end() for s, e, _ in taken):
                    continue
                if material.role != "alternative" and _inside_alternative_phrase(low, m.start(), m.end()):
                    continue
                taken.append((m.start(), m.end(), material))
        return sorted(taken, key=lambda t: t[0])

    def _activities(self, low: str, material_spans) -> list[str]:
        found: list[str] = []
        # "manufactured by Ringsted Dun", "made by our partner workshops": someone else's production
        outsourced = bool(OUTSOURCED_RE.search(low)) and not OWN_PRODUCTION_RE.search(low)
        for rx, act in self.activity_terms:
            if outsourced and act.kind in {"manufacturing", "processing"}:
                continue
            if rx.search(low) and act.id not in found:
                found.append(act.id)
        for rx, act in self.activity_objects:
            if act.id in found or act.kind not in VERB_RE:
                continue
            if outsourced and act.kind in {"manufacturing", "processing"}:
                continue
            verb_re = self.activity_verbs.get(act.id, VERB_RE[act.kind])
            if not verb_re.search(low):
                continue
            for m in rx.finditer(low):
                inside_material = any(m.start() >= s and m.end() <= e for s, e, _ in material_spans)
                if act.kind == "producer" and inside_material:
                    continue  # "duck" inside "duck down" is not a duck farm
                found.append(act.id)
                break
        return found

    @staticmethod
    def _about_self(sentence: str, name_rx) -> bool:
        """First person ("we", "our", "us") or the company's own name."""
        if SELF_RE.search(sentence.lower()):
            return True
        return bool(name_rx and name_rx.search(sentence.lower()))

    def _link(self, low, here, performed, on_page) -> str | None:
        core = [a for a in here if self.kb.activities[a].tier == "core"]
        if core:
            return core[0]
        for rx, act in self.activity_objects:
            if act.id in performed and act.tier == "core" and rx.search(low):
                return act.id
        page_core = [a for a in on_page if self.kb.activities[a].tier == "core"]
        return page_core[0] if page_core else None

    def _product_line(self, low: str) -> str | None:
        """The first product noun in the sentence (usually its subject)."""
        best: tuple[int, str] | None = None
        for term in self.line_terms:  # longest first, so ties keep the longer term
            m = term_regex(term).search(low)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), term)
        return best[1].rstrip("s") if best else None


NAME_STOPWORDS = frozenset(
    "the and of company co ltd limited inc gmbh srl spa llc plc group international sp kg ag sa bv "
    "home welcome official site".split()
)


def _name_regex(company_name: str | None):
    """Regex for the company's distinctive name word ('Feltworks Germany' -> 'feltworks')."""
    if not company_name:
        return None
    words = [w for w in re.findall(r"[a-z0-9][a-z0-9&'-]+", company_name.lower())
             if w not in NAME_STOPWORDS and len(w) >= 4]
    return term_regex(words[0], plural=False) if words else None


def _mask_name(low: str, company_name: str | None) -> str:
    """Blank out the company's own name so it is never read as a material or activity."""
    if not company_name or len(company_name.strip()) < 3:
        return low
    rx = term_regex(company_name)
    return rx.sub(lambda m: " " * len(m.group()), low)


def _inside_alternative_phrase(low: str, start: int, end: int) -> bool:
    """'cashmere' in 'cashmere-feel', 'wool' in 'wool-look', 'down' in 'down-alternative'."""
    after = low[end:end + 12]
    return bool(re.match(r"[\s-]*(?:feel|like|look|alternative|touch)\b", after))


class _FactBuilder:
    def __init__(self):
        self._facts: dict[tuple, Fact] = {}

    def add(self, predicate, obj, page, quote, offset, polarity=True, attrs=None):
        attrs = attrs or {}
        key = (predicate, obj, polarity, tuple(sorted(attrs.items())))
        evidence = Evidence(url=page.url, quote=quote, page_type=page.page_type,
                            extractor="nlp", char_offset=offset)
        if key in self._facts:
            fact = self._facts[key]
            if evidence.quote not in fact.quotes or evidence.url not in {e.url for e in fact.evidence}:
                fact.evidence = (*fact.evidence, evidence)
            return
        self._facts[key] = Fact(
            id=f"F{len(self._facts) + 1}", predicate=predicate, object=obj,
            polarity=polarity, attrs=dict(attrs), evidence=(evidence,),
        )

    def facts(self) -> list[Fact]:
        return list(self._facts.values())
