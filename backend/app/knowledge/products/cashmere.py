"""Cashmere knowledge base."""

from ..schema import (
    BuyerCategory,
    BusinessActivity as A,
    Effect,
    Material as M,
    ProductApplication as App,
    ProductKB,
    Rule,
    has,
    lacks,
)

PID = "cashmere"

MATERIALS = {
    m.id: m
    for m in (
        M("raw_cashmere", "Raw / dehaired cashmere fibre", "target",
          ("raw cashmere", "dehaired cashmere", "de-haired cashmere", "cashmere fibre",
           "cashmere fiber", "cashmere top", "cashmere tops", "cashmere wool fibre")),
        M("cashmere_yarn", "Cashmere yarn", "related", ("cashmere yarn", "cashmere yarns")),
        M("cashmere_unspecified", "Cashmere (form not stated)", "ambiguous",
          ("cashmere", "pure cashmere", "cashmere blend", "pashmina")),
        M("faux_cashmere", "Imitation 'cashmere-feel'", "alternative",
          ("cashmere-feel", "cashmere feel", "cashmere-like", "cashmere like", "faux cashmere",
           "cashmere alternative", "cashmere touch")),
        M("synthetic_fibre", "Synthetic fibre", "alternative",
          ("acrylic", "polyester", "viscose", "nylon", "synthetic fibre", "synthetic fiber")),
        M("ordinary_wool", "Ordinary wool / other animal fibres", "alternative",
          ("merino wool", "lambswool", "lamb's wool", "camel hair", "yak wool")),
    )
}

PROCESSING = ("cashmere_dehairing_processing", "cashmere_spinning")
TRADING = ("cashmere_trading",)
MANUFACTURING = ("knitwear_manufacturing", "woven_fabric_manufacturing", "garment_manufacturing")
ANY_CASHMERE = ("raw_cashmere", "cashmere_yarn", "cashmere_unspecified")

ACTIVITIES = {
    a.id: a
    for a in (
        A("cashmere_dehairing_processing", "Cashmere dehairing / processing", "core", "processing",
          ("dehairing", "de-hairing", "cashmere processing", "cashmere dehairer", "cashmere scouring"),
          ("raw_cashmere",), objects=("cashmere",)),
        A("cashmere_spinning", "Cashmere spinning", "core", "manufacturing",
          ("cashmere spinning", "cashmere spinner", "cashmere yarn manufacturer"),
          ("raw_cashmere",), objects=("cashmere yarn", "yarn"), verbs=r"spin(?:s|ning)?|spun"),
        A("cashmere_trading", "Cashmere fibre / yarn trading", "core", "trading",
          ("cashmere trader", "cashmere merchant", "cashmere fibre trading", "cashmere trading"),
          ("raw_cashmere", "cashmere_yarn"), objects=("cashmere",)),
        A("knitwear_manufacturing", "Knitwear manufacturing", "core", "manufacturing",
          ("knitwear manufacturer", "knitwear factory", "knitting mill", "knitting factory"),
          ("cashmere_yarn", "raw_cashmere"),
          objects=("knitwear", "sweater", "jumper", "cardigan", "pullover")),
        A("woven_fabric_manufacturing", "Woven fabric / shawl manufacturing", "core", "manufacturing",
          ("woven fabric manufacturer", "weaving mill", "shawl manufacturer", "scarf manufacturer"),
          ("cashmere_yarn", "raw_cashmere"), objects=("fabric", "cloth", "shawl", "scarf", "scarves")),
        A("garment_manufacturing", "Garment manufacturing (own production)", "core", "manufacturing",
          ("garment manufacturer", "garment factory"),
          ("cashmere_yarn", "raw_cashmere"), objects=("garment", "coat", "clothing", "apparel")),
        A("general_textile_manufacturing", "General textile manufacturing", "adjacent", "manufacturing",
          ("textile manufacturer", "textile mill"), objects=("textile", "jersey")),
        A("goat_herding_production", "Goat herding / fibre production", "non_buyer", "producer",
          ("goat farm", "goat herder", "cashmere goat breeder", "cashmere producer", "herding cooperative"),
          objects=("goat",)),
        A("retail_brand", "Retail / fashion brand", "non_buyer", "retail",
          ("online store", "our shop", "retailer", "fashion brand", "our brand", "online shop")),
    )
}

APPLICATIONS = {
    a.id: a
    for a in (
        App("cashmere_knitwear", "Finished cashmere sweaters and knitwear", ("cashmere_unspecified", "cashmere_yarn"),
            ("sweater", "jumper", "cardigan", "knitwear", "pullover", "hoodie")),
        App("cashmere_accessories", "Cashmere scarves, shawls, accessories", ("cashmere_unspecified", "cashmere_yarn"),
            ("scarf", "scarves", "shawl", "wrap", "beanie", "glove")),
        App("cashmere_fabric", "Cashmere coat/suit fabric", ("raw_cashmere", "cashmere_yarn"), ("fabric", "cloth")),
    )
}

BUYER_CATEGORIES = {
    c.id: c
    for c in (
        BuyerCategory("cashmere_processor_spinner", "Cashmere dehairer / spinner / trader", 1,
                      PROCESSING + TRADING),
        BuyerCategory("cashmere_product_manufacturer", "Cashmere knitwear / fabric / garment manufacturer", 2,
                      MANUFACTURING),
    )
}

REQUIRED_EVIDENCE = {
    "activity": "A cashmere spinning, processing, knitting, weaving, garment-making or trading activity",
    "material": "A statement naming cashmere as a material",
    "specificity": "Raw or dehaired cashmere fibre stated (not just 'cashmere' products)",
    "official_source": "Evidence taken from the company's own website",
    "corroboration": "Activity/material facts confirmed on a second page of the website",
}

RULES = [
    Rule(
        "CA-P1", PID, "positive",
        (has("performs", PROCESSING), has("uses_material", ["raw_cashmere"])),
        Effect(relevance="strong", usage="supported"),
        "Dehairs/spins/processes cashmere and states raw cashmere fibre: strong fit.",
    ),
    Rule(
        "CA-P2", PID, "positive",
        (has("performs", MANUFACTURING), has("uses_material", ["raw_cashmere"], linked_to=MANUFACTURING)),
        Effect(relevance="strong", usage="supported"),
        "Own knitwear/fabric/garment production and states raw or dehaired cashmere fibre as input.",
    ),
    Rule(
        "CA-P2b", PID, "positive",
        (has("performs", MANUFACTURING), has("uses_material", ["cashmere_yarn"], linked_to=MANUFACTURING),
         lacks("uses_material", ["raw_cashmere"])),
        Effect(relevance="moderate", usage="supported",
               missing="Uses cashmere yarn; no evidence that it buys raw or dehaired cashmere fibre."),
        "Own production from cashmere yarn. It works with cashmere, but a yarn buyer is "
        "not necessarily a buyer of raw fibre, so it is rated Possible, not Strong.",
    ),
    Rule(
        "CA-P3", PID, "positive",
        (has("performs", TRADING), has("uses_material", ["raw_cashmere", "cashmere_yarn"])),
        Effect(relevance="strong", usage="supported"),
        "Trades cashmere fibre or yarn.",
    ),
    Rule(
        "CA-P4", PID, "positive",
        (has("performs", MANUFACTURING + PROCESSING),
         has("uses_material", ["cashmere_unspecified"]),
         lacks("uses_material", ["raw_cashmere", "cashmere_yarn"])),
        Effect(relevance="moderate", usage="mentioned",
               missing="Cashmere fibre or yarn input is not stated (only 'cashmere' products)."),
        "Own production of cashmere goods but the fibre/yarn input is not stated.",
    ),
    Rule(
        "CA-P5", PID, "positive",
        (has("sources", ["raw_cashmere"]),),
        Effect(purchasing="direct"),
        "The company states that it buys/sources raw cashmere fibre (direct purchasing statement).",
    ),
    Rule(
        "CA-N1", PID, "negative",
        (has("role", ["retailer"]),),
        Effect(veto="retailer_or_brand"),
        "Fashion brand or retailer without own manufacturing: it sells clothing, "
        "it does not buy raw cashmere.",
    ),
    Rule(
        "CA-N2", PID, "negative",
        (has("uses_alternative", ["faux_cashmere"]), lacks("uses_material", ANY_CASHMERE)),
        Effect(veto="imitation_only"),
        "Only 'cashmere-feel' / imitation fibre: not genuine cashmere.",
    ),
    Rule(
        "CA-N3", PID, "negative",
        (has("uses_alternative", ["synthetic_fibre"]), lacks("uses_material", ANY_CASHMERE)),
        Effect(veto="synthetic_only"),
        "Synthetic textile producer with no cashmere statement.",
    ),
    Rule(
        "CA-N4", PID, "negative",
        (has("uses_alternative", ["ordinary_wool"]), lacks("uses_material", ANY_CASHMERE)),
        Effect(veto="ordinary_wool_only"),
        "Works with ordinary wool or other fibres and never mentions cashmere.",
    ),
]

KB = ProductKB(
    id=PID,
    name="Cashmere",
    definition=(
        "The fine undercoat fibre of the cashmere goat, in raw, dehaired, top or yarn "
        "form. Distinct from ordinary wool, synthetic fibres and 'cashmere-feel' imitations."
    ),
    aliases=("cashmere", "raw cashmere", "dehaired cashmere", "cashmere fibre"),
    industries=("cashmere_processing", "luxury_knitwear_and_textiles"),
    materials=MATERIALS,
    activities=ACTIVITIES,
    applications=APPLICATIONS,
    buyer_categories=BUYER_CATEGORIES,
    required_evidence=REQUIRED_EVIDENCE,
    rules=RULES,
    purchase_terms=("source", "sourcing", "buy", "purchase", "procure", "import", "we buy"),
    search_queries=('cashmere dehairing company', 'cashmere yarn spinning mill', 'raw cashmere fibre trader', 'cashmere knitwear manufacturer factory', 'dehaired cashmere fibre buyer'),
)
