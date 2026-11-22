import { CLASS_INFO, type Classification, type SearchResult } from "@/lib/types";

const ORDER: Classification[] = [
  "confirmed_purchaser", "strong_potential_buyer", "possible_potential_buyer", "insufficient_evidence", "not_relevant",
];
const COLOR: Record<Classification, string> = {
  confirmed_purchaser: "var(--c-confirmed)",
  strong_potential_buyer: "var(--c-strong)",
  possible_potential_buyer: "var(--c-possible)",
  insufficient_evidence: "var(--c-insufficient)",
  not_relevant: "var(--c-rejected)",
};

/** Class distribution (to scale) plus the pipeline's own counters. */
export default function ResultsSummary({ result }: { result: SearchResult }) {
  const counts = ORDER.map((c) => ({ c, n: result.leads.filter((l) => l.classification === c).length }));
  const total = counts.reduce((sum, x) => sum + x.n, 0) || 1;
  const evidenceQuotes = result.leads.reduce((n, l) => n + l.facts.reduce((m, f) => m + f.evidence.length, 0), 0);
  const rulesFired = result.leads.reduce((n, l) => n + l.trace.rules_fired.length, 0);
  const pages = result.leads.reduce((n, l) => n + l.pages_checked.length, 0);

  return (
    <div className="grid gap-4">
      <div className="summary-bar" role="img"
           aria-label={counts.map(({ c, n }) => `${CLASS_INFO[c].short}: ${n}`).join(", ")}>
        {counts.filter(({ n }) => n > 0).map(({ c, n }) => (
          <span key={c} style={{ width: `${(n / total) * 100}%`, background: COLOR[c] }} title={`${CLASS_INFO[c].short}: ${n}`} />
        ))}
      </div>
      <div className="legend">
        {counts.map(({ c, n }) => (
          <span key={c}><i style={{ background: COLOR[c] }} />{CLASS_INFO[c].short} <b className="mono">{n}</b></span>
        ))}
      </div>
      <div className="kpis">
        <div className="kpi"><b>{result.summary.examined}</b><span>companies analysed</span></div>
        <div className="kpi"><b>{pages}</b><span>company pages read</span></div>
        <div className="kpi"><b>{evidenceQuotes}</b><span>evidence quotes</span></div>
        <div className="kpi"><b>{rulesFired}</b><span>rule firings</span></div>
        <div className="kpi"><b>{result.excluded.length + result.summary.duplicates_removed}</b><span>duplicates and non-company sites removed</span></div>
      </div>
    </div>
  );
}
