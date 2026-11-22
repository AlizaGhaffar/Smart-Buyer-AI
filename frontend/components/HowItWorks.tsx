import { Brain, Database, FileSearch, Filter, Gauge, Globe2, Layers, Scale, Search, ShieldCheck } from "lucide-react";

import { CLASS_INFO, type Classification } from "@/lib/types";

const STAGES = [
  { icon: Search, title: "Product-specific search", text: "Searches for buyer companies, not just the product name.", meta: "ddgs metasearch · retry · cache" },
  { icon: Filter, title: "Candidate collection", text: "Removes duplicates, directories, marketplaces and news sites.", meta: "55 blocked domains" },
  { icon: Globe2, title: "Website verification", text: "Reads the company's own pages only.", meta: "robots.txt · 1 request/s per site" },
  { icon: FileSearch, title: "AI / NLP extraction", text: "Turns sentences into facts about the company.", meta: "offline · no paid API" },
  { icon: ShieldCheck, title: "Grounding check", text: "Drops any fact that is not quoted word for word from the page.", meta: "quote + source URL for every fact" },
  { icon: Brain, title: "Reasoning (KRR)", text: "Product rules fire over the facts and explain the decision.", meta: "forward chaining · inference trace" },
  { icon: Scale, title: "Qualification", text: "Assigns one of five classes and an evidence score.", meta: "score 0-100, not a probability" },
];

const ENTITIES = ["Product", "Company", "Industry", "BusinessActivity", "Material", "ProductApplication", "BuyerCategory", "Country", "Evidence", "ContactInformation"];
const RELATIONS = ["belongs to", "has application", "uses", "includes", "distinguished from", "performs", "sources / supplies", "supports", "has contact"];
const CLASSES: { c: Classification; text: string }[] = [
  { c: "confirmed_purchaser", text: "Says it buys this material" },
  { c: "strong_potential_buyer", text: "Activity and material both proven" },
  { c: "possible_potential_buyer", text: "Partly proven" },
  { c: "insufficient_evidence", text: "Site unreadable or conflicting" },
  { c: "not_relevant", text: "Rejected by a rule" },
];
const FPR = [
  { set: "Fictional test", n: 18, old: 90, krr: 10 },
  { set: "Real-world A", n: 83, old: 78, krr: 30 },
  { set: "Fresh set B", n: 55, old: 85, krr: 15 },
];

export default function HowItWorks() {
  return (
    <div className="grid gap-5">
      <div className="panel">
        <div className="panel-head"><h3 className="panel-title">Seven-stage pipeline</h3></div>
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
            <div className="chip-list">{RELATIONS.map((r) => <span key={r} className="chip">{r}</span>)}</div>
          </div>
        </div>

        <div className="panel panel-pad grid gap-4">
          <h3 className="panel-title inline-flex items-center gap-2"><Layers size={18} aria-hidden="true" />Evidence layers and classes</h3>
          <div className="chip-list">
            <span className="chip">Business relevance</span>
            <span className="chip">Material use</span>
            <span className="chip">Purchasing</span>
          </div>
          <div className="grid gap-2">
            {CLASSES.map(({ c, text }) => (
              <div key={c} className="flex flex-wrap items-center gap-3 text-[14.5px]">
                <span className={`badge ${CLASS_INFO[c].tone}`} style={{ minWidth: 170 }}>{CLASS_INFO[c].short}</span>
                <span className="text-2">{text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h3 className="panel-title inline-flex items-center gap-2"><Gauge size={18} aria-hidden="true" />Verification results</h3>
            <p className="panel-sub">58 new companies, system frozen before testing.</p>
          </div>
        </div>
        <div className="panel-pad grid gap-5">
          <div className="grid-3">
            <div className="metric"><span>Precision</span><b>90%</b><small>18 of 20 leads were real buyers</small></div>
            <div className="metric"><span>False-positive rate</span><b>15%</b><small>old finder: 85%</small></div>
            <div className="metric"><span>Recall</span><b>43%</b><small>cautious by design</small></div>
            <div className="metric"><span>Evidence audit</span><b style={{ color: "var(--c-confirmed)" }}>Pass</b><small>3,293 quotes, none invented</small></div>
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
