"use client";

import { useEffect, useState } from "react";

import { FibreSwatch } from "@/components/Brand";
import { getKnowledge } from "@/lib/api";
import type { KnowledgeBase, ProductId } from "@/lib/types";

const PRODUCTS: { id: ProductId; label: string }[] = [
  { id: "raw_sheep_wool", label: "Raw Sheep Wool" },
  { id: "duck_down", label: "Duck Down" },
  { id: "cashmere", label: "Cashmere" },
];
const ROLE_LABEL: Record<string, string> = {
  target: "Target raw material",
  related: "Related material",
  ambiguous: "Ambiguous mention (weak evidence)",
  alternative: "Alternative material (negative evidence)",
  distractor: "Distractor (not this product)",
};
const TIER_LABEL: Record<string, string> = {
  core: "Core activities (handle the raw material)",
  adjacent: "Adjacent activities (weak relevance)",
  non_buyer: "Non-buyer roles",
};
type RuleFilter = "all" | "positive" | "negative" | "generic";

function Logic({ conditions, then }: { conditions: string[]; then: Record<string, string> }) {
  return (
    <div className="rule-logic">
      <b>IF</b> {conditions.map((c, i) => (
        <span key={i}>{i > 0 && <b> AND </b>}{c.replaceAll("/", " / ")}</span>
      ))}
      <br />
      <b>THEN</b> {Object.entries(then).map(([k, v]) => `${k} = ${v}`).join(", ")}
    </div>
  );
}

export default function KnowledgeView({ initial }: { initial: ProductId }) {
  const [product, setProduct] = useState<ProductId>(initial);
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<RuleFilter>("all");

  useEffect(() => {
    let active = true;
    setKb(null);
    setError("");
    getKnowledge(product).then((d) => active && setKb(d)).catch((e: Error) => active && setError(e.message));
    return () => { active = false; };
  }, [product]);

  const rules = kb?.rules.filter((r) => filter === "all" || r.kind === filter) ?? [];

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Product knowledge base">
        {PRODUCTS.map((p) => (
          <button key={p.id} type="button" role="radio" aria-checked={product === p.id} onClick={() => setProduct(p.id)}
                  className="product-option" style={{ width: "auto", minWidth: 210 }}>
            <FibreSwatch product={p.id} />
            <span className="option-title">{p.label}</span>
          </button>
        ))}
      </div>

      {error && <p role="alert" className="alert alert-error m-0">{error}</p>}
      {!kb && !error && <div className="panel panel-pad muted">Loading the knowledge base…</div>}

      {kb && (
        <>
          <div className="panel panel-pad grid gap-4">
            <div>
              <p className="section-label">Definition</p>
              <p className="m-0 text-[16px]" style={{ maxWidth: "75ch" }}>{kb.definition}</p>
            </div>
            <div className="kpis">
              <div className="kpi"><b>{kb.materials.length}</b><span>materials</span></div>
              <div className="kpi"><b>{kb.activities.length}</b><span>business activities</span></div>
              <div className="kpi"><b>{kb.buyer_categories.length}</b><span>buyer categories</span></div>
              <div className="kpi"><b>{kb.rules.length}</b><span>reasoning rules</span></div>
              <div className="kpi"><b>{kb.relations.length}</b><span>KB relations</span></div>
            </div>
            <div>
              <p className="section-label">Also known as</p>
              <div className="chip-list">{kb.aliases.map((a) => <span key={a} className="chip">{a}</span>)}</div>
            </div>
          </div>

          <div className="grid-2">
            <div className="panel panel-pad grid gap-4">
              <h3 className="panel-title">Materials</h3>
              {Object.keys(ROLE_LABEL).map((role) => {
                const items = kb.materials.filter((m) => m.role === role);
                if (!items.length) return null;
                return (
                  <div key={role}>
                    <p className="section-label">{ROLE_LABEL[role]}</p>
                    <div className="chip-list">
                      {items.map((m) => <span key={m.id} className="chip" title={`Recognised terms: ${m.terms.join(", ")}`}>{m.name}</span>)}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="panel panel-pad grid gap-4">
              <h3 className="panel-title">Business activities</h3>
              {Object.keys(TIER_LABEL).map((tier) => {
                const items = kb.activities.filter((a) => a.tier === tier);
                if (!items.length) return null;
                return (
                  <div key={tier}>
                    <p className="section-label">{TIER_LABEL[tier]}</p>
                    <div className="chip-list">{items.map((a) => <span key={a.id} className="chip">{a.name}</span>)}</div>
                  </div>
                );
              })}
            </div>
            <div className="panel panel-pad grid gap-3">
              <h3 className="panel-title">Buyer categories</h3>
              {kb.buyer_categories.map((c) => (
                <div key={c.id} className="flex items-start gap-3">
                  <span className="tag">Tier {c.tier}</span>
                  <span>{c.name}</span>
                </div>
              ))}
            </div>
            <div className="panel panel-pad grid gap-3">
              <h3 className="panel-title">Required evidence</h3>
              <ul className="bullets text-2">
                {Object.values(kb.required_evidence).map((v) => <li key={v}>{v}</li>)}
              </ul>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h3 className="panel-title">Reasoning rules</h3>
                <p className="panel-sub">Forward chaining: rules fire until no new fact can be derived. Negative rules can veto or cap a result.</p>
              </div>
              <div className="tabs" role="tablist" aria-label="Rule type">
                {(["all", "positive", "negative", "generic"] as RuleFilter[]).map((f) => (
                  <button key={f} type="button" role="tab" aria-selected={filter === f} className="tab" onClick={() => setFilter(f)}>
                    {f[0].toUpperCase() + f.slice(1)}
                    <span className="count">{f === "all" ? kb.rules.length : kb.rules.filter((r) => r.kind === f).length}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="panel-pad grid-2">
              {rules.map((r) => (
                <div key={r.id} className="rule-card">
                  <div className="flex items-center gap-2">
                    <span className={`tag ${r.kind === "positive" ? "pos" : r.kind === "negative" ? "neg" : ""}`}>{r.id}</span>
                    <span className="muted text-[13px]">{r.kind}</span>
                  </div>
                  <p className="m-0 text-[14.5px]">{r.explain}</p>
                  <Logic conditions={r.if} then={r.then} />
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
