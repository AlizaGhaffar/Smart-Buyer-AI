import { Brain, Database, FileSearch, Filter, Gauge, Globe2, Link2, Scale, Search, ShieldCheck } from "lucide-react";

import { CLASS_INFO, type Classification } from "@/lib/types";

const STAGES = [
  { icon: Search, title: "Product-specific search", text: "Search phrases come from each product's knowledge base and describe buyer companies (for example a wool scouring company), not just the product name.", meta: "ddgs metasearch · retry with backoff · 1 h cache" },
  { icon: Filter, title: "Candidate collection", text: "Web addresses are normalised, duplicates are merged, and directories, marketplaces, social media and news sites are removed.", meta: "55 blocked domains · title-based directory check" },
  { icon: Globe2, title: "Website verification", text: "The homepage and up to three of the company's own pages (About, Products, Contact, Sourcing) are read. Search snippets are never used as evidence.", meta: "robots.txt · 1 request/s per site · public hosts only" },
  { icon: FileSearch, title: "AI / NLP extraction", text: "Sentences are turned into facts: activities, materials, buying and selling statements, negation and exclusivity. A fact only counts if the sentence is about the company itself.", meta: "offline · no paid API · English pages" },
  { icon: ShieldCheck, title: "Grounding check", text: "Every fact must quote text that really exists on the fetched page. Anything else is dropped, so the system cannot invent evidence.", meta: "verbatim quote + source URL for every fact" },
  { icon: Brain, title: "Knowledge representation and reasoning", text: "Product rules fire over the facts until nothing new can be derived. Roles such as retailer or supplier are derived, and negative rules veto or cap a result.", meta: "forward chaining · inference trace · conflict detection" },
  { icon: Scale, title: "Qualification and scoring", text: "A decision table assigns one of five classes. An evidence score (0-100) ranks companies inside a class and is not a probability.", meta: "confirmed purchaser needs a direct buying statement" },
];

const ENTITIES = ["Product", "Company", "Industry", "BusinessActivity", "Material", "ProductApplication", "BuyerCategory", "Country", "Evidence", "ContactInformation"];
const RELATIONS = [
  "Product belongs to Industry", "Product has ProductApplication", "BusinessActivity uses Material",
  "BuyerCategory includes BusinessActivity", "Product is distinguished from Material", "Company performs BusinessActivity",
  "Company uses Material", "Company sources / supplies Material", "Evidence supports Fact", "Company has ContactInformation",
];
const CLASSES: Classification[] = ["confirmed_purchaser", "strong_potential_buyer", "possible_potential_buyer", "insufficient_evidence", "not_relevant"];

const FPR = [
  { set: "Fictional test", n: 18, old: 90, krr: 10 },
  { set: "Real-world A", n: 83, old: 78, krr: 30 },
  { set: "Fresh set B", n: 55, old: 85, krr: 15 },
];

export default function HowItWorks() {
  return (
    <div className="grid gap-5">
      <div className="panel">
        <div className="panel-head">
          <div>
            <h3 className="panel-title">Seven-stage pipeline</h3>
            <p className="panel-sub">Every stage is logged and every decision is traceable to a quote from the company's own website.</p>
          </div>
        </div>
        <div className="panel-pad pipeline">
          {STAGES.map(({ icon: Icon, title, text, meta }) => (
            <div key={title} className="stage">
              <span className="stage-num"><Icon size={20} aria-hidden="true" /></span>
              <div>
                <h4>{title}</h4>
                <p>{text}</p>
                <div className="meta">{meta}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid-2">
        <div className="panel panel-pad grid gap-4">
          <h3 className="panel-title inline-flex items-center gap-2"><Database size={18} aria-hidden="true" />Knowledge representation</h3>
          <div>
            <p className="section-label">Entities</p>
            <div className="chip-list">{ENTITIES.map((e) => <span key={e} className="chip mono">{e}</span>)}</div>
          </div>
          <div>
            <p className="section-label">Relationships</p>
            <ul className="bullets text-2 text-[14px]">{RELATIONS.map((r) => <li key={r}>{r}</li>)}</ul>
          </div>
          <p className="m-0 muted text-[13.5px]">Three separate knowledge bases (raw sheep wool, duck down, cashmere). Each has its own materials, activities, buyer categories, required evidence and rules.</p>
        </div>

        <div className="panel panel-pad grid gap-3">
          <h3 className="panel-title inline-flex items-center gap-2"><Link2 size={18} aria-hidden="true" />Three separate evidence layers</h3>
          <p className="m-0 text-2 text-[14.5px]">Being in the right industry is not treated as proof of buying.</p>
          <div className="grid gap-2 text-[14.5px]">
            <div><b>Business relevance</b> <span className="muted">· is it the right kind of company?</span></div>
            <div><b>Material use</b> <span className="muted">· does it say it uses or processes this material?</span></div>
            <div><b>Purchasing</b> <span className="muted">· does it say it buys or sources the raw material?</span></div>
          </div>
          <p className="section-label mt-2">Five classes</p>
          <div className="grid gap-2">
            {CLASSES.map((c) => (
              <div key={c} className="flex flex-wrap items-start gap-2 text-[14px]">
                <span className={`badge ${CLASS_INFO[c].tone}`}>{CLASS_INFO[c].short}</span>
                <span className="text-2" style={{ flex: "1 1 220px" }}>{CLASS_INFO[c].description}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h3 className="panel-title inline-flex items-center gap-2"><Gauge size={18} aria-hidden="true" />Verification results</h3>
            <p className="panel-sub">From the Phase 5 verification report (22 Nov 2026). Fresh set B: 58 new companies, system frozen before testing.</p>
          </div>
        </div>
        <div className="panel-pad grid gap-5">
          <div className="grid-3">
            <div className="metric"><span>Precision on new companies</span><b>90%</b><small>18 of 20 leads were real buyers</small></div>
            <div className="metric"><span>False-positive rate</span><b>15%</b><small>old keyword finder: 85%</small></div>
            <div className="metric"><span>Recall on new companies</span><b>43%</b><small>cautious by design; non-English sites are missed</small></div>
            <div className="metric"><span>Evidence audit</span><b style={{ color: "var(--c-confirmed)" }}>Pass</b><small>3,293 quotes checked, none invented</small></div>
          </div>
          <div className="compare" role="img" aria-label="False-positive rate: old finder versus Smart Buyer AI on three test sets">
            <p className="section-label m-0">False-positive rate (lower is better)</p>
            {FPR.map((row) => (
              <div key={row.set} className="grid gap-1">
                <span className="text-[13.5px] font-medium">{row.set} <span className="muted">(n={row.n})</span></span>
                <div className="compare-row"><span className="muted">Old finder</span><span className="track"><span className="fill block" style={{ width: `${row.old}%`, background: "var(--c-insufficient)" }} /></span><span className="mono text-right">{row.old}%</span></div>
                <div className="compare-row"><span>Smart Buyer AI</span><span className="track"><span className="fill block" style={{ width: `${row.krr}%`, background: "var(--accent)" }} /></span><span className="mono text-right">{row.krr}%</span></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
