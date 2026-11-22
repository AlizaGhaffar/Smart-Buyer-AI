// Types for the /api/v2 responses (see backend/app/pipeline/runner.py).

export type ProductId = "raw_sheep_wool" | "duck_down" | "cashmere";
export type SearchMode = "live" | "seed" | "replay";
export type Classification =
  | "confirmed_purchaser"
  | "strong_potential_buyer"
  | "possible_potential_buyer"
  | "insufficient_evidence"
  | "not_relevant";

export type EvidenceItem = { url: string; quote: string; page_type: string; retrieved_at: string; extractor: string };
export type Fact = {
  id: string;
  predicate: string;
  object: string;
  object_name: string;
  polarity: boolean;
  attrs: Record<string, unknown>;
  evidence: EvidenceItem[];
};
export type TraceRule = { id: string; kind: string; text: string; facts: string[]; evidence: { fact: string; url: string; quote: string }[] };
export type Trace = {
  sufficient: boolean;
  insufficiency_reasons: string[];
  layers: { relevance: string; usage: string; purchasing: string };
  roles: string[];
  rules_fired: TraceRule[];
  vetoes: TraceRule[];
  caps: TraceRule[];
  flags: string[];
  conflicts: { type: string; description: string; facts: string[]; evidence: { fact: string; url: string; quote: string }[] }[];
  near_misses: { id: string; text: string; unmet: string[] }[];
  missing: string[];
  ignored_facts: string[];
};
export type ScoreFactor = { factor: string; weight: number; earned: number; reason: string };
export type Score = {
  value: number;
  max: number;
  kind: string;
  breakdown: ScoreFactor[];
  penalties: { reason: string; points: number }[];
  cap: string | null;
};
export type Contact = { value: string; source_url: string };

export type Lead = {
  company_name: string;
  company_name_source: string;
  company_key: string;
  official_website: string | null;
  found_via: { source: string; url: string; title: string; snippet: string; note: string };
  country: { value: string | null; source: string | null; matches_target: boolean | null };
  classification: Classification;
  label: string;
  reason_code: string;
  explanation: string;
  layers: { relevance: string; usage: string; purchasing: string };
  score: Score | null;
  trace: Trace;
  business_activities: string[];
  materials_used: string[];
  alternative_materials: string[];
  facts: Fact[];
  contacts: { emails: Contact[]; phones: Contact[] };
  verification: { label: string; ok: boolean }[];
  missing_information: string[];
  pages_checked: { url: string; page_type: string; retrieved_at: string }[];
  retrieved_at: string | null;
  errors: string[];
};

export type SearchResult = {
  mode: SearchMode;
  recorded_at: string | null;
  product: { id: ProductId; name: string };
  country: string | null;
  queries: string[];
  started_at: string;
  finished_at: string;
  summary: Record<Classification, number> & { examined: number; excluded_before_analysis: number; duplicates_removed: number };
  leads: Lead[];
  excluded: { url: string; reason: string; source: string }[];
  warnings: { stage: string; message: string; company?: string; query?: string }[];
};

export type Job = {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  stage: string;
  stages: string[];
  progress: { done: number; total: number; message: string };
  result: SearchResult | null;
  error: string | null;
};

export type KnowledgeBase = {
  id: ProductId;
  name: string;
  definition: string;
  aliases: string[];
  industries: string[];
  materials: { id: string; name: string; role: string; terms: string[] }[];
  activities: { id: string; name: string; tier: string; kind: string }[];
  buyer_categories: { id: string; name: string; tier: number; activities: string[] }[];
  required_evidence: Record<string, string>;
  relations: { subject: string; predicate: string; object: string }[];
  rules: { id: string; kind: string; explain: string; if: string[]; then: Record<string, string> }[];
};

export const CLASS_INFO: Record<Classification, { short: string; tone: string; description: string }> = {
  confirmed_purchaser: {
    short: "Confirmed purchaser",
    tone: "class-confirmed",
    description: "The company's own website states that it buys or sources this raw material (self-declared, not a verified transaction).",
  },
  strong_potential_buyer: {
    short: "Strong",
    tone: "class-strong",
    description: "Relevant activity and use of the material are both supported by the company's website. No purchase statement.",
  },
  possible_potential_buyer: {
    short: "Possible",
    tone: "class-possible",
    description: "Relevant business, but use of the exact material is only partly evidenced.",
  },
  insufficient_evidence: {
    short: "Insufficient evidence",
    tone: "class-insufficient",
    description: "The website could not be read, was not in English, or its statements conflict. Check manually.",
  },
  not_relevant: {
    short: "Not relevant",
    tone: "class-rejected",
    description: "Rejected by a negative rule: unrelated business, retailer, supplier or alternative material.",
  },
};

export const QUALIFIED: Classification[] = ["confirmed_purchaser", "strong_potential_buyer", "possible_potential_buyer"];

export type Snapshot = {
  product: ProductId;
  product_name: string;
  country: string | null;
  recorded_at: string | null;
  companies: number;
};
