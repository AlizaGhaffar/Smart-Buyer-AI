"use client";

import { X } from "lucide-react";
import { useEffect, useState } from "react";

import { getKnowledge } from "@/lib/api";
import type { KnowledgeBase, ProductId } from "@/lib/types";

const ROLE_LABEL: Record<string, string> = {
  target: "Target raw material",
  related: "Related material",
  ambiguous: "Ambiguous mention",
  alternative: "Alternative (negative evidence)",
  distractor: "Distractor (not this product)",
};

export default function KnowledgePanel({ product, onClose }: { product: ProductId; onClose: () => void }) {
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setKb(null);
    setError("");
    getKnowledge(product).then((data) => active && setKb(data)).catch((e: Error) => active && setError(e.message));
    return () => { active = false; };
  }, [product]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 backdrop-blur-sm" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label="Knowledge base"
             className="glass-panel h-full w-full max-w-2xl overflow-y-auto p-5 sm:p-7" onClick={(e) => e.stopPropagation()}>
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[.18em] text-cyan-300">Knowledge base</p>
            <h2 className="mt-1 text-lg font-semibold">{kb?.name ?? "Loading…"}</h2>
          </div>
          <button type="button" onClick={onClose} className="add-button" aria-label="Close knowledge base"><X size={15} /></button>
        </div>
        {error && <p role="alert" className="rounded-lg border border-rose-400/20 bg-rose-400/[0.08] p-3 text-xs text-rose-200">{error}</p>}
        {kb && (
          <div className="space-y-6 text-[12px] text-slate-300">
            <p className="leading-5">{kb.definition}</p>

            <section>
              <h3 className="detail-title">Materials</h3>
              <div className="space-y-2">
                {Object.keys(ROLE_LABEL).map((role) => {
                  const items = kb.materials.filter((m) => m.role === role);
                  if (!items.length) return null;
                  return (
                    <div key={role}>
                      <p className="text-[10px] text-slate-500">{ROLE_LABEL[role]}</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {items.map((m) => <span key={m.id} className="keyword-pill" title={m.terms.join(", ")}>{m.name}</span>)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section>
              <h3 className="detail-title">Buyer categories</h3>
              <ul className="space-y-1">
                {kb.buyer_categories.map((c) => (
                  <li key={c.id}><span className="text-slate-500">Tier {c.tier}:</span> {c.name}</li>
                ))}
              </ul>
            </section>

            <section>
              <h3 className="detail-title">Required evidence</h3>
              <ul className="list-disc space-y-0.5 pl-4 text-slate-400">
                {Object.values(kb.required_evidence).map((v) => <li key={v}>{v}</li>)}
              </ul>
            </section>

            <section>
              <h3 className="detail-title">Rules ({kb.rules.length}): IF conditions THEN conclusion</h3>
              <div className="space-y-2">
                {kb.rules.map((r) => (
                  <div key={r.id} className="evidence-item">
                    <div className="flex items-center gap-2">
                      <span className={`rule-id ${r.kind === "negative" ? "rule-veto" : r.kind === "positive" ? "rule-pos" : ""}`}>{r.id}</span>
                      <span className="text-[10px] uppercase tracking-wide text-slate-500">{r.kind}</span>
                    </div>
                    <p className="mt-1 leading-5">{r.explain}</p>
                    <p className="mt-1 font-mono text-[10px] leading-4 text-slate-500 [overflow-wrap:anywhere]">
                      IF {r.if.map((c) => c.replaceAll("/", " / ")).join(" AND ")}<br />
                      THEN {Object.entries(r.then).map(([k, v]) => `${k} = ${v}`).join(", ")}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <p className="text-[10px] text-slate-600">{kb.relations.length} knowledge-base relations (product → industry, activity → material, category → activity, product → alternatives).</p>
          </div>
        )}
      </aside>
    </div>
  );
}
