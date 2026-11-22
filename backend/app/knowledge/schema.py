"""Knowledge-representation schema for Smart Buyer AI.

Everything the reasoning engine works with is defined here:

* KB entities (Material, BusinessActivity, ProductApplication, BuyerCategory)
* ProductKB - one structured knowledge base per product
* Evidence / Fact - extracted, source-grounded statements about a company
* Has / Lacks / Effect / Rule - the declarative rule language

A Fact can never exist without Evidence (url + verbatim quote); derived facts
must instead point at the facts that support them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# Evidence and facts
# --------------------------------------------------------------------------

OFFICIAL_PAGE_TYPES = frozenset(
    {
        "homepage",
        "about",
        "products",
        "materials",
        "manufacturing",
        "sourcing",
        "contact",
        "other_official",
    }
)
NON_OFFICIAL_PAGE_TYPES = frozenset({"directory", "snippet", "third_party"})
PAGE_RELIABILITY: dict[str, float] = {
    "about": 1.0,
    "products": 1.0,
    "materials": 1.0,
    "manufacturing": 1.0,
    "sourcing": 1.0,
    "homepage": 0.8,
    "contact": 0.6,
    "other_official": 0.5,
}
EXTRACTORS = frozenset({"nlp", "llm", "manual"})

PREDICATES = frozenset(
    {
        "performs",  # Company performs BusinessActivity
        "uses_material",  # Company uses target/related/ambiguous Material
        "uses_alternative",  # Company uses an alternative Material
        "sells_finished",  # Company sells a finished ProductApplication
        "sources",  # Company buys/sources Material (buyer direction)
        "supplies",  # Company sells/supplies Material (seller direction)
        "operates_in",  # Company operates in Industry
        "role",  # derived: retailer / supplier
    }
)
ROLES = frozenset({"retailer", "supplier"})

RELEVANCE_ORDER = ("none", "weak", "moderate", "strong")
USAGE_ORDER = ("none", "mentioned", "supported")


@dataclass(frozen=True)
class Evidence:
    """A verbatim quote from a specific page, with provenance."""

    url: str
    quote: str
    page_type: str
    extractor: str = "nlp"
    char_offset: int | None = None
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("Evidence requires a source URL.")
        if not self.quote.strip():
            raise ValueError("Evidence requires a non-empty supporting quote.")
        if self.page_type not in OFFICIAL_PAGE_TYPES | NON_OFFICIAL_PAGE_TYPES:
            raise ValueError(f"Unknown page_type {self.page_type!r}.")
        if self.extractor not in EXTRACTORS:
            raise ValueError(f"Unknown extractor {self.extractor!r}.")

    @property
    def is_official(self) -> bool:
        return self.page_type in OFFICIAL_PAGE_TYPES

    @property
    def reliability(self) -> float:
        return PAGE_RELIABILITY.get(self.page_type, 0.0)


@dataclass
class Fact:
    """subject (the company) - predicate - object, with provenance.

    attrs carries qualifiers the extractor found, e.g. ``linked_activity``
    (the activity the material was tied to in the same sentence/section),
    ``product_line``, ``exclusive`` (the statement says "all"/"100%"/"only").
    """

    id: str
    predicate: str
    object: str
    polarity: bool = True
    attrs: dict = field(default_factory=dict)
    evidence: tuple[Evidence, ...] = ()
    derived: bool = False
    support: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.predicate not in PREDICATES:
            raise ValueError(f"Unknown predicate {self.predicate!r}.")
        self.evidence = tuple(self.evidence)
        self.support = tuple(self.support)
        if self.derived:
            if not self.support:
                raise ValueError("A derived fact must list the facts supporting it.")
        elif not self.evidence:
            raise ValueError("A fact without evidence cannot exist.")

    @property
    def admissible(self) -> bool:
        """Only facts backed by the company's own website may satisfy rules (G1)."""
        return self.derived or any(e.is_official for e in self.evidence)

    @property
    def quotes(self) -> list[str]:
        return [e.quote for e in self.evidence]


# --------------------------------------------------------------------------
# Rule language
# --------------------------------------------------------------------------


def _freeze(values) -> tuple | None:
    return None if values is None else tuple(values)


@dataclass(frozen=True)
class Has:
    """Condition: at least one positive, admissible fact matches."""

    predicate: str
    objects: tuple[str, ...] | None = None  # None = any object
    linked_to: tuple[str, ...] | None = None  # fact.attrs["linked_activity"]
    attrs: tuple[tuple[str, tuple], ...] = ()

    def matches(self, fact: Fact) -> bool:
        if fact.predicate != self.predicate or not fact.polarity:
            return False
        if self.objects is not None and fact.object not in self.objects:
            return False
        if self.linked_to is not None and fact.attrs.get("linked_activity") not in self.linked_to:
            return False
        return all(fact.attrs.get(key) in allowed for key, allowed in self.attrs)

    def describe(self) -> str:
        target = "/".join(self.objects) if self.objects else "any"
        text = f"{self.predicate}({target})"
        if self.linked_to:
            text += f" linked to {'/'.join(self.linked_to)}"
        return text


@dataclass(frozen=True)
class Lacks:
    """Condition: no fact matches the inner Has."""

    inner: Has

    def describe(self) -> str:
        return f"no {self.inner.describe()}"


def has(predicate, objects=None, linked_to=None, **attrs) -> Has:
    return Has(
        predicate,
        _freeze(objects),
        _freeze(linked_to),
        tuple((k, tuple(v) if isinstance(v, (list, tuple, set, frozenset)) else (v,)) for k, v in attrs.items()),
    )


def lacks(predicate, objects=None, linked_to=None, **attrs) -> Lacks:
    return Lacks(has(predicate, objects, linked_to, **attrs))


@dataclass(frozen=True)
class Effect:
    relevance: str | None = None
    usage: str | None = None
    purchasing: str | None = None
    derive_role: str | None = None
    veto: str | None = None  # reason code, e.g. "synthetic_only"
    cap: str | None = None  # maximum class, e.g. "possible"
    flag: str | None = None  # e.g. "mixed_materials"
    missing: str | None = None  # text added to "missing information"


@dataclass(frozen=True)
class Rule:
    id: str
    product: str  # product id, or "*" for generic rules
    kind: str  # positive | negative | generic
    when: tuple
    effect: Effect
    explain: str

    def __post_init__(self) -> None:
        if self.kind not in {"positive", "negative", "generic"}:
            raise ValueError(f"Rule {self.id}: bad kind {self.kind!r}.")
        if not self.when:
            raise ValueError(f"Rule {self.id}: needs at least one condition.")


# --------------------------------------------------------------------------
# Product knowledge base
# --------------------------------------------------------------------------

MATERIAL_ROLES = frozenset({"target", "related", "ambiguous", "alternative", "distractor"})
ACTIVITY_TIERS = frozenset({"core", "adjacent", "non_buyer"})
ACTIVITY_KINDS = frozenset(
    {"processing", "manufacturing", "trading", "producer", "retail", "general"}
)
REQUIRED_EVIDENCE_KEYS = (
    "activity",
    "material",
    "specificity",
    "official_source",
    "corroboration",
)


@dataclass(frozen=True)
class Material:
    id: str
    name: str
    role: str  # target | related | ambiguous | alternative | distractor
    terms: tuple[str, ...] = ()  # gazetteer phrases for the extractor


@dataclass(frozen=True)
class BusinessActivity:
    id: str
    name: str
    tier: str  # core (handles raw material) | adjacent | non_buyer
    kind: str
    terms: tuple[str, ...] = ()  # fixed phrases, e.g. "spinning mill"
    uses: tuple[str, ...] = ()  # material ids
    # Nouns the activity acts on (e.g. "duvet"). The extractor recognises the
    # activity when a verb of the right kind (manufacture / scour / trade ...)
    # appears in the same sentence as one of these nouns.
    objects: tuple[str, ...] = ()
    # Optional regex of verbs that override the kind's default verbs.
    verbs: str | None = None


@dataclass(frozen=True)
class ProductApplication:
    id: str
    name: str
    materials: tuple[str, ...] = ()
    terms: tuple[str, ...] = ()  # finished-goods nouns, e.g. "sweater"


@dataclass(frozen=True)
class BuyerCategory:
    id: str
    name: str
    tier: int  # 1 = strongest fit, 2 = weaker fit
    activities: tuple[str, ...] = ()


@dataclass
class ProductKB:
    id: str
    name: str
    definition: str
    aliases: tuple[str, ...]
    industries: tuple[str, ...]
    materials: dict[str, Material]
    activities: dict[str, BusinessActivity]
    applications: dict[str, ProductApplication]
    buyer_categories: dict[str, BuyerCategory]
    required_evidence: dict[str, str]
    rules: list[Rule]
    excluded_bare_terms: tuple[str, ...] = ()
    purchase_terms: tuple[str, ...] = ()
    # Search phrases describing buyer companies (not just the product name).
    search_queries: tuple[str, ...] = ()

    # ---- helpers -------------------------------------------------------
    def material_ids(self, *roles: str) -> tuple[str, ...]:
        return tuple(m.id for m in self.materials.values() if m.role in roles)

    def activity_ids(self, *, tiers=None, kinds=None) -> tuple[str, ...]:
        return tuple(
            a.id
            for a in self.activities.values()
            if (tiers is None or a.tier in tiers) and (kinds is None or a.kind in kinds)
        )

    def category_for(self, activity_ids) -> BuyerCategory | None:
        """Best (lowest-tier-number) buyer category containing any activity."""
        found = [
            c for c in self.buyer_categories.values() if set(c.activities) & set(activity_ids)
        ]
        return min(found, key=lambda c: c.tier) if found else None

    def relations(self) -> list[tuple[str, str, str]]:
        """KB-level relationship triples (static knowledge)."""
        triples: list[tuple[str, str, str]] = []
        for industry in self.industries:
            triples.append((self.id, "belongs_to", industry))
        for app in self.applications.values():
            triples.append((self.id, "has_application", app.id))
        for act in self.activities.values():
            for material in act.uses:
                triples.append((act.id, "uses", material))
        for cat in self.buyer_categories.values():
            for act in cat.activities:
                triples.append((cat.id, "includes", act))
        for mat in self.materials.values():
            if mat.role in {"alternative", "distractor"}:
                triples.append((self.id, "distinguished_from", mat.id))
        return triples

    def validate(self) -> list[str]:
        """Return a list of structural problems (empty list = consistent KB)."""
        problems: list[str] = []
        for key in REQUIRED_EVIDENCE_KEYS:
            if key not in self.required_evidence:
                problems.append(f"required_evidence missing key {key!r}")
        for mat in self.materials.values():
            if mat.role not in MATERIAL_ROLES:
                problems.append(f"material {mat.id}: bad role {mat.role!r}")
        for act in self.activities.values():
            if act.tier not in ACTIVITY_TIERS:
                problems.append(f"activity {act.id}: bad tier {act.tier!r}")
            if act.kind not in ACTIVITY_KINDS:
                problems.append(f"activity {act.id}: bad kind {act.kind!r}")
            for material in act.uses:
                if material not in self.materials:
                    problems.append(f"activity {act.id} uses unknown material {material!r}")
        for app in self.applications.values():
            for material in app.materials:
                if material not in self.materials:
                    problems.append(f"application {app.id} uses unknown material {material!r}")
        for cat in self.buyer_categories.values():
            for act in cat.activities:
                if act not in self.activities:
                    problems.append(f"category {cat.id} includes unknown activity {act!r}")

        seen: set[str] = set()
        known = {
            "performs": set(self.activities),
            "uses_material": set(self.material_ids("target", "related", "ambiguous", "distractor")),
            "uses_alternative": set(self.material_ids("alternative")),
            "sells_finished": set(self.applications),
            "sources": set(self.materials),
            "supplies": set(self.materials),
            "operates_in": set(self.industries),
            "role": set(ROLES),
        }
        for rule in self.rules:
            if rule.id in seen:
                problems.append(f"duplicate rule id {rule.id}")
            seen.add(rule.id)
            if rule.product != self.id:
                problems.append(f"rule {rule.id} belongs to {rule.product!r}, not {self.id!r}")
            for cond in rule.when:
                inner = cond.inner if isinstance(cond, Lacks) else cond
                if inner.predicate not in known:
                    problems.append(f"rule {rule.id}: unknown predicate {inner.predicate!r}")
                    continue
                for obj in inner.objects or ():
                    if obj not in known[inner.predicate]:
                        problems.append(
                            f"rule {rule.id}: {inner.predicate} references unknown {obj!r}"
                        )
                for act in inner.linked_to or ():
                    if act not in self.activities:
                        problems.append(f"rule {rule.id}: linked_to unknown activity {act!r}")
        return problems
