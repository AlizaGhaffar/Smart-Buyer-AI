"""Forward-chaining reasoning engine.

Input : a company's extracted Facts (each with Evidence) + fetch statistics.
Output: an InferenceResult holding the three evidence layers (relevance,
        usage, purchasing), every rule that fired with its supporting facts,
        vetoes, caps, conflicts and missing information.

The engine does NOT assign the final class or a score; that is done by the
qualification and scoring modules from this result. Facts that are not backed
by the company's own website are ignored by rules (rule G1) and are reported.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..knowledge.generic_rules import build_generic_rules
from ..knowledge.schema import (
    RELEVANCE_ORDER,
    USAGE_ORDER,
    Fact,
    Has,
    Lacks,
    ProductKB,
    Rule,
)

# Catches empty / JavaScript-only pages ("Loading... enable JavaScript" ~40 chars).
# Real company pages are normally thousands of characters long.
MIN_TEXT_CHARS = 150


@dataclass
class CompanyFacts:
    """What the extraction stage hands to the reasoning stage."""

    company_key: str
    facts: list[Fact]
    pages_fetched: int  # own-site pages successfully fetched
    text_chars: int  # characters of usable (English) own-site text
    english: bool = True
    non_english_share: float = 0.0  # share of own-site text the extractor cannot read


@dataclass
class FiredRule:
    rule_id: str
    kind: str
    text: str
    supporting_fact_ids: list[str]
    evidence: list[dict]  # {"url", "quote"} for each supporting fact
    effect: dict


@dataclass
class NearMiss:
    rule_id: str
    text: str
    unmet: list[str]


@dataclass
class Conflict:
    type: str  # "polarity" | "exclusive_alternative"
    description: str
    fact_ids: list[str]
    evidence: list[dict]


@dataclass
class InferenceResult:
    company_key: str
    product_id: str
    sufficient: bool = True
    insufficiency_reasons: list[str] = field(default_factory=list)
    relevance: str = "none"
    usage: str = "none"  # none | mentioned | supported | contradicted
    purchasing: str = "none"  # none | direct | contradicted
    roles: set[str] = field(default_factory=set)
    fired: list[FiredRule] = field(default_factory=list)
    vetoes: list[FiredRule] = field(default_factory=list)
    caps: list[FiredRule] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
    conflicts: list[Conflict] = field(default_factory=list)
    near_misses: list[NearMiss] = field(default_factory=list)
    evidence_items: dict[str, bool] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    ignored_fact_ids: list[str] = field(default_factory=list)
    derived_facts: list[Fact] = field(default_factory=list)
    fact_ids_used: set[str] = field(default_factory=set)

    @property
    def fired_ids(self) -> list[str]:
        return [f.rule_id for f in self.fired]

    def to_trace(self) -> dict:
        def rule(f: FiredRule) -> dict:
            return {
                "id": f.rule_id,
                "kind": f.kind,
                "text": f.text,
                "facts": f.supporting_fact_ids,
                "evidence": f.evidence,
            }

        return {
            "sufficient": self.sufficient,
            "insufficiency_reasons": self.insufficiency_reasons,
            "layers": {
                "relevance": self.relevance,
                "usage": self.usage,
                "purchasing": self.purchasing,
            },
            "roles": sorted(self.roles),
            "rules_fired": [rule(f) for f in self.fired],
            "vetoes": [rule(f) for f in self.vetoes],
            "caps": [rule(f) for f in self.caps],
            "flags": sorted(self.flags),
            "conflicts": [
                {
                    "type": c.type,
                    "description": c.description,
                    "facts": c.fact_ids,
                    "evidence": c.evidence,
                }
                for c in self.conflicts
            ],
            "near_misses": [
                {"id": n.rule_id, "text": n.text, "unmet": n.unmet} for n in self.near_misses
            ],
            "missing": self.missing,
            "ignored_facts": self.ignored_fact_ids,
        }


# --------------------------------------------------------------------------


def infer(kb: ProductKB, data: CompanyFacts) -> InferenceResult:
    result = InferenceResult(company_key=data.company_key, product_id=kb.id)

    # G2 - sufficiency: do we have enough own-site text to judge at all?
    if data.pages_fetched < 1:
        result.insufficiency_reasons.append("NO_OWN_SITE_PAGE")
    if data.pages_fetched >= 1 and data.text_chars < MIN_TEXT_CHARS:
        result.insufficiency_reasons.append("TOO_LITTLE_TEXT")
    if not data.english:
        result.insufficiency_reasons.append("NON_ENGLISH")
    result.ignored_fact_ids = [f.id for f in data.facts if not f.admissible]  # G1
    if result.insufficiency_reasons:
        result.sufficient = False
        result.missing.append("Not enough readable English text from the company's own website.")
        return result

    memory: list[Fact] = [f for f in data.facts if f.admissible]
    rules: list[Rule] = [*build_generic_rules(kb), *kb.rules]
    fired_ids: set[str] = set()
    derived_n = 0

    changed = True
    while changed:  # forward chaining to a fixpoint
        changed = False
        for rule in rules:
            if rule.id in fired_ids:
                continue
            support = _match(rule, memory)
            if support is None:
                continue
            fired_ids.add(rule.id)
            changed = True
            fired = _record(rule, support, memory)
            _apply(rule, fired, support, result)
            role = rule.effect.derive_role
            if role and not any(f.predicate == "role" and f.object == role for f in memory):
                derived_n += 1
                derived = Fact(
                    id=f"D{derived_n}",
                    predicate="role",
                    object=role,
                    derived=True,
                    support=tuple(f.id for f in support),
                )
                memory.append(derived)
                result.derived_facts.append(derived)
                result.roles.add(role)
            elif role:
                result.roles.add(role)

    # Absence of evidence in text we cannot read is not evidence of absence:
    # an "unrelated business" verdict needs the site to be mostly readable.
    unrelated = [v for v in result.vetoes if v.effect.get("veto") == "unrelated_industry"]
    if unrelated and data.non_english_share > 0.5:
        result.vetoes = [v for v in result.vetoes if v not in unrelated]
        result.sufficient = False
        result.insufficiency_reasons.append("MOSTLY_NON_ENGLISH")
        result.missing.append("Most of the website is not in English, so the system could not read it.")
        return result

    result.conflicts = _find_conflicts(kb, memory)
    if any(c.type == "exclusive_alternative" or c.type == "polarity" for c in result.conflicts):
        if any(f.predicate == "uses_material" for f in memory):
            result.usage = "contradicted"

    _near_misses(rules, fired_ids, memory, result)
    _evidence_items(kb, memory, result)
    _missing(kb, result)
    return result


# --------------------------------------------------------------------------


def _match(rule: Rule, memory: list[Fact]) -> list[Fact] | None:
    """Return supporting facts if every condition holds, else None."""
    support: list[Fact] = []
    for cond in rule.when:
        if isinstance(cond, Lacks):
            if any(cond.inner.matches(f) for f in memory):
                return None
        else:
            matched = [f for f in memory if cond.matches(f)]
            if not matched:
                return None
            support.extend(m for m in matched if m not in support)
    return support


def _record(rule: Rule, support: list[Fact], memory: list[Fact]) -> FiredRule:
    by_id = {f.id: f for f in memory}

    def grounded(fact: Fact):
        """Yield (source fact id, Evidence) down to the original extracted facts."""
        if fact.derived:
            for sid in fact.support:
                yield from grounded(by_id[sid])
        else:
            for ev in fact.evidence:
                yield fact.id, ev

    evidence, seen = [], set()
    for fact in support:
        for source_id, ev in grounded(fact):
            if (source_id, ev.url, ev.quote) not in seen:
                seen.add((source_id, ev.url, ev.quote))
                evidence.append({"fact": source_id, "url": ev.url, "quote": ev.quote})
    effect = {k: v for k, v in vars(rule.effect).items() if v}
    return FiredRule(
        rule_id=rule.id,
        kind=rule.kind,
        text=rule.explain,
        supporting_fact_ids=[f.id for f in support],
        evidence=evidence,
        effect=effect,
    )


def _apply(rule: Rule, fired: FiredRule, support: list[Fact], result: InferenceResult) -> None:
    effect = rule.effect
    result.fired.append(fired)
    result.fact_ids_used.update(f.id for f in support if not f.derived)
    if effect.relevance and RELEVANCE_ORDER.index(effect.relevance) > RELEVANCE_ORDER.index(result.relevance):
        result.relevance = effect.relevance
    if effect.usage and USAGE_ORDER.index(effect.usage) > USAGE_ORDER.index(result.usage if result.usage in USAGE_ORDER else "none"):
        result.usage = effect.usage
    if effect.purchasing:
        if effect.purchasing == "direct" or result.purchasing == "none":
            result.purchasing = effect.purchasing
    if effect.veto:
        result.vetoes.append(fired)
    if effect.cap:
        result.caps.append(fired)
    if effect.flag:
        result.flags.add(effect.flag)
    if effect.missing and effect.missing not in result.missing:
        result.missing.append(effect.missing)


def _find_conflicts(kb: ProductKB, memory: list[Fact]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    own = [f for f in memory if not f.derived]

    # (a) the same statement asserted and denied
    seen: set[tuple[str, str]] = set()
    for fact in own:
        key = (fact.predicate, fact.object)
        if key in seen:
            continue
        opposite = [g for g in own if (g.predicate, g.object) == key and g.polarity != fact.polarity]
        if opposite:
            seen.add(key)
            group = [g for g in own if (g.predicate, g.object) == key]
            conflicts.append(
                Conflict(
                    "polarity",
                    f"'{fact.predicate} {fact.object}' is both stated and denied on the website.",
                    [g.id for g in group],
                    [{"fact": g.id, "url": e.url, "quote": e.quote} for g in group for e in g.evidence],
                )
            )

    # (b) a sweeping alternative-material claim contradicts a target-material claim
    material_ids = set(kb.material_ids("target", "related", "ambiguous"))
    uses = [f for f in own if f.predicate == "uses_material" and f.polarity and f.object in material_ids]
    alts = [
        f for f in own
        if f.predicate == "uses_alternative" and f.polarity and f.attrs.get("exclusive")
    ]
    for alt in alts:
        for use in uses:
            line_a, line_u = alt.attrs.get("product_line"), use.attrs.get("product_line")
            if line_a and line_u and line_a != line_u:
                continue  # different product lines: mixed use, not a contradiction
            if set(alt.quotes) & set(use.quotes):
                continue  # named together in one sentence (a list of fibres): mixed use
            conflicts.append(
                Conflict(
                    "exclusive_alternative",
                    f"The website states {use.object} and also that all/only "
                    f"{alt.object} is used for the same products.",
                    [use.id, alt.id],
                    [
                        {"fact": f.id, "url": e.url, "quote": e.quote}
                        for f in (use, alt)
                        for e in f.evidence
                    ],
                )
            )
    return conflicts


def _near_misses(rules, fired_ids, memory, result) -> None:
    for rule in rules:
        if rule.id in fired_ids or rule.kind != "positive":
            continue
        has_conds = [c for c in rule.when if isinstance(c, Has)]
        met = [c for c in has_conds if any(c.matches(f) for f in memory)]
        unmet = [c.describe() for c in has_conds if c not in met]
        if met and unmet:
            result.near_misses.append(NearMiss(rule.id, rule.explain, unmet))


def _evidence_items(kb: ProductKB, memory: list[Fact], result: InferenceResult) -> None:
    own = [f for f in memory if not f.derived and f.polarity]
    non_buyer = set(kb.activity_ids(tiers={"non_buyer"}))
    material_ids = set(kb.material_ids("target", "related", "ambiguous"))
    target_ids = set(kb.material_ids("target"))

    activity = [f for f in own if f.predicate == "performs" and f.object not in non_buyer]
    material = [f for f in own if f.predicate == "uses_material" and f.object in material_ids]
    specific = [f for f in own if f.predicate == "uses_material" and f.object in target_ids]
    urls = {
        e.url
        for f in activity + material
        for e in f.evidence
        if e.is_official
    }
    result.evidence_items = {
        "activity": bool(activity),
        "material": bool(material),
        "specificity": bool(specific),
        "official_source": bool(own),
        "corroboration": len(urls) >= 2,
    }


def _missing(kb: ProductKB, result: InferenceResult) -> None:
    for key, met in result.evidence_items.items():
        if not met:
            text = f"Missing: {kb.required_evidence[key]}."
            if text not in result.missing:
                result.missing.append(text)
    if result.purchasing == "none":
        target = next(iter(kb.material_ids("target")), kb.name)
        name = kb.materials[target].name if target in kb.materials else kb.name
        result.missing.append(f"No direct statement that the company buys or sources {name}.")
