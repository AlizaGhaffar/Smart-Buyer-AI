"use client";

import { ChevronDown, CircleCheck, CircleMinus, ExternalLink, Globe2, Mail, Phone, Quote } from "lucide-react";
import { useState } from "react";

import { CLASS_INFO, type Lead } from "@/lib/types";

const PREDICATE_LABEL: Record<string, string> = {
  performs: "Business activity",
  uses_material: "Material",
  uses_alternative: "Alternative material",
  sources: "Buys / sources",
  supplies: "Sells / supplies",
  sells_finished: "Sells finished goods",
};
const LAYER_LABEL: Record<string, string> = { relevance: "Business relevance", usage: "Material use", purchasing: "Purchasing" };
const FACTOR_LABEL: Record<string, string> = {
  material_usage: "Material usage evidence",
  business_activity: "Relevant activity",
  buyer_category: "Buyer category match",
  source_reliability: "Source reliability",
  evidence_completeness: "Evidence completeness",
  purchasing_evidence: "Purchasing evidence",
};

function layerTone(value: string) {
  if (["strong", "supported", "direct"].includes(value)) return "layer-good";
  if (["moderate", "mentioned", "weak"].includes(value)) return "layer-mid";
  if (value === "contradicted") return "layer-bad";
  return "layer-none";
}

function shortUrl(url: string) {
  return url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");
}

export function ClassBadge({ lead }: { lead: Lead }) {
  const info = CLASS_INFO[lead.classification];
  return <span className={`class-badge ${info.tone}`} title={info.description}>{info.short}</span>;
}

export default function LeadCard({ lead }: { lead: Lead }) {
  const [open, setOpen] = useState(false);
  const facts = lead.facts.filter((f) => f.predicate in PREDICATE_LABEL);
  const hasContacts = lead.contacts.emails.length > 0 || lead.contacts.phones.length > 0;

  return (
    <article className="lead-card">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="truncate text-[14px] font-semibold text-slate-100" title={`Name source: ${lead.company_name_source}`}>
            {lead.company_name}
          </h3>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
            {lead.official_website ? (
              <a href={lead.official_website} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:text-cyan-200">
                {shortUrl(lead.official_website)} <ExternalLink size={11} aria-hidden="true" />
              </a>
            ) : <span>Website not reachable ({lead.company_key})</span>}
            <span className="inline-flex items-center gap-1" title={lead.country.source ?? "No country found on the website"}>
              <Globe2 size={11} aria-hidden="true" />
              {lead.country.value ?? "Country not found"}
              {lead.country.source?.includes("inferred") && <span className="text-slate-600">(inferred)</span>}
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <ClassBadge lead={lead} />
          {lead.score && (
            <span className="score-pill" title="Evidence score from the breakdown below. It ranks leads; it is not a probability.">
              {lead.score.value}<span className="text-slate-500">/100</span>
            </span>
          )}
        </div>
      </div>

      <p className="mt-3 text-[12px] leading-5 text-slate-300">{lead.explanation}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {Object.entries(lead.layers).map(([key, value]) => (
          <span key={key} className={`layer-pill ${layerTone(value)}`}>{LAYER_LABEL[key]}: <b className="font-semibold">{value}</b></span>
        ))}
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <ul className="space-y-1">
          {lead.verification.map((v) => (
            <li key={v.label} className={`flex items-center gap-1.5 text-[11px] ${v.ok ? "text-emerald-300/90" : "text-slate-500"}`}>
              {v.ok ? <CircleCheck size={13} aria-hidden="true" /> : <CircleMinus size={13} aria-hidden="true" />}
              {v.label}{!v.ok && " - no"}
            </li>
          ))}
        </ul>
        <div className="space-y-1.5 text-[11px]">
          {lead.contacts.emails.slice(0, 3).map((c) => (
            <div key={c.value} className="flex min-w-0 items-center gap-2">
              <a href={`mailto:${c.value}`} className="contact-link min-w-0"><Mail size={13} aria-hidden="true" /><span className="truncate">{c.value}</span></a>
              <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="source-mini">source</a>
            </div>
          ))}
          {lead.contacts.phones.slice(0, 2).map((c) => (
            <div key={c.value} className="flex min-w-0 items-center gap-2">
              <a href={`tel:${c.value}`} className="contact-link"><Phone size={13} aria-hidden="true" />{c.value}</a>
              <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="source-mini">source</a>
            </div>
          ))}
          {!lead.contacts.emails.length && <p className="text-slate-600">Email: Not found</p>}
          {!lead.contacts.phones.length && <p className="text-slate-600">Phone: Not found</p>}
          {hasContacts && <p className="text-[10px] text-slate-600">Public contacts from the company website. Check them before you get in touch.</p>}
        </div>
      </div>

      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="details-toggle">
        <ChevronDown size={14} className={`transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
        {open ? "Hide" : "Show"} evidence and reasoning
        <span className="text-slate-600">({facts.length} facts, {lead.trace.rules_fired.length} rules)</span>
      </button>

      {open && (
        <div className="mt-3 space-y-5 border-t border-white/[0.06] pt-4">
          <section>
            <h4 className="detail-title">Evidence from the company website</h4>
            {facts.length === 0 ? <p className="detail-empty">No statements about this product were found on the pages checked.</p> : (
              <ul className="space-y-2">
                {facts.map((f) => (
                  <li key={f.id} className="evidence-item">
                    <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                      <span className="fact-id">{f.id}</span>
                      <span className="text-slate-400">{PREDICATE_LABEL[f.predicate]}:</span>
                      <span className={f.polarity ? "text-slate-200" : "text-rose-300 line-through"}>{f.object_name}</span>
                      {!f.polarity && <span className="text-rose-300">(denied on the website)</span>}
                    </div>
                    {f.evidence.slice(0, 2).map((e) => (
                      <blockquote key={e.url + e.quote} className="mt-1.5 flex gap-2 text-[11px] leading-5 text-slate-300">
                        <Quote size={12} className="mt-1 shrink-0 text-slate-600" aria-hidden="true" />
                        <span>
                          “{e.quote}”{" "}
                          <a href={e.url} target="_blank" rel="noopener noreferrer" className="whitespace-nowrap text-cyan-300/80 hover:text-cyan-200">
                            {e.page_type} page <ExternalLink size={10} className="inline" aria-hidden="true" />
                          </a>
                        </span>
                      </blockquote>
                    ))}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h4 className="detail-title">Reasoning: knowledge-base rules that fired</h4>
            {lead.trace.rules_fired.length === 0 ? <p className="detail-empty">No rule fired.{!lead.trace.sufficient && " The website could not be analysed."}</p> : (
              <ul className="space-y-1.5">
                {lead.trace.rules_fired.map((r) => {
                  const veto = lead.trace.vetoes.some((v) => v.id === r.id);
                  const cap = lead.trace.caps.some((c) => c.id === r.id);
                  return (
                    <li key={r.id} className="flex gap-2 text-[11px] leading-5 text-slate-300">
                      <span className={`rule-id ${veto ? "rule-veto" : cap ? "rule-cap" : r.kind === "positive" ? "rule-pos" : ""}`}>{r.id}</span>
                      <span>{r.text}{r.facts.length > 0 && <span className="text-slate-600"> (based on {r.facts.join(", ")})</span>}</span>
                    </li>
                  );
                })}
              </ul>
            )}
            {lead.trace.conflicts.map((c, i) => (
              <div key={i} className="mt-2 rounded-lg border border-amber-300/20 bg-amber-300/[0.05] p-2.5 text-[11px] text-amber-100/90">
                <b>Conflicting evidence:</b> {c.description}
                {c.evidence.map((e) => <div key={e.quote} className="mt-1 text-amber-100/70">“{e.quote}”</div>)}
              </div>
            ))}
          </section>

          {lead.missing_information.length > 0 && (
            <section>
              <h4 className="detail-title">Missing information</h4>
              <ul className="list-disc space-y-0.5 pl-4 text-[11px] leading-5 text-slate-400">
                {lead.missing_information.map((m) => <li key={m}>{m}</li>)}
              </ul>
            </section>
          )}

          {lead.score && (
            <section>
              <h4 className="detail-title">Evidence score breakdown <span className="font-normal normal-case tracking-normal text-slate-600">(ranks leads; not a probability)</span></h4>
              <div className="space-y-1.5">
                {lead.score.breakdown.map((b) => (
                  <div key={b.factor} className="grid grid-cols-[150px_1fr_52px] items-center gap-2 text-[10px]" title={b.reason}>
                    <span className="text-slate-400">{FACTOR_LABEL[b.factor] ?? b.factor}</span>
                    <span className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                      <span className="block h-full rounded-full bg-cyan-300/70" style={{ width: `${(b.earned / b.weight) * 100}%` }} />
                    </span>
                    <span className="text-right text-slate-300">{b.earned}/{b.weight}</span>
                  </div>
                ))}
                {lead.score.penalties.map((p) => (
                  <div key={p.reason} className="text-[10px] text-rose-300">{p.points} points: {p.reason}</div>
                ))}
                {lead.score.cap && <div className="text-[10px] text-amber-200">{lead.score.cap}</div>}
              </div>
            </section>
          )}

          <section className="grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="detail-title">Pages checked</h4>
              {lead.pages_checked.length === 0 ? <p className="detail-empty">None. {lead.errors[0]}</p> : (
                <ul className="space-y-0.5 text-[10px]">
                  {lead.pages_checked.map((p) => (
                    <li key={p.url} className="truncate">
                      <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-cyan-200">
                        <span className="text-slate-600">{p.page_type}:</span> {shortUrl(p.url)}
                      </a>
                    </li>
                  ))}
                  {lead.retrieved_at && <li className="text-slate-600">Retrieved {new Date(lead.retrieved_at).toLocaleString()}</li>}
                </ul>
              )}
            </div>
            <div>
              <h4 className="detail-title">How it was found</h4>
              <p className="text-[10px] leading-4 text-slate-500">
                {lead.found_via.source === "seed" ? "From your seed URL list." : `Search result: “${lead.found_via.title}”.`}{" "}
                {lead.found_via.note}
              </p>
            </div>
          </section>
        </div>
      )}
    </article>
  );
}
