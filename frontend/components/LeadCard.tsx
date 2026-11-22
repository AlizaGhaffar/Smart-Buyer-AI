"use client";

import { ChevronDown, CircleCheck, CircleMinus, ExternalLink, Globe2, Mail, Phone } from "lucide-react";
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
const INSUFFICIENT_REASON: Record<string, string> = {
  NO_OWN_SITE_PAGE: "The company website could not be opened.",
  TOO_LITTLE_TEXT: "The website has almost no readable text.",
  NON_ENGLISH: "The website is not in English.",
  MOSTLY_NON_ENGLISH: "Most of the website is not in English.",
};

function layerTone(value: string) {
  if (["strong", "supported", "direct"].includes(value)) return "good";
  if (["moderate", "mentioned", "weak"].includes(value)) return "mid";
  if (value === "contradicted") return "bad";
  return "";
}

/** The first sentence of an explanation, for the compact card. */
function firstSentence(text: string) {
  const match = text.match(/^.+?[.!?](?=\s|$)/);
  return match ? match[0] : text;
}

const shortUrl = (url: string) => url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");

export function ClassBadge({ lead }: { lead: Lead }) {
  const info = CLASS_INFO[lead.classification];
  return <span className={`badge ${info.tone}`} title={info.description}>{info.short}</span>;
}

export default function LeadCard({ lead }: { lead: Lead }) {
  const [open, setOpen] = useState(false);
  const facts = lead.facts.filter((f) => f.predicate in PREDICATE_LABEL);
  const reasons = lead.trace.insufficiency_reasons.map((r) => INSUFFICIENT_REASON[r] ?? r);

  return (
    <article className="lead-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="lead-name" title={`Name source: ${lead.company_name_source}`}>{lead.company_name}</h3>
          <div className="lead-meta mt-1">
            {lead.official_website ? (
              <a href={lead.official_website} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">
                {shortUrl(lead.official_website)} <ExternalLink size={13} aria-hidden="true" />
              </a>
            ) : <span>{lead.company_key} (website not reachable)</span>}
            <span className="inline-flex items-center gap-1" title={lead.country.source ?? "No country found on the website"}>
              <Globe2 size={14} aria-hidden="true" />
              {lead.country.value ?? "Country not found"}
              {lead.country.source?.includes("inferred") && <span>(from domain)</span>}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ClassBadge lead={lead} />
          {lead.score && (
            <span className="score" title="Evidence score: ranks leads within a class. It is not a probability.">
              {lead.score.value}<small>/100</small>
            </span>
          )}
        </div>
      </div>

      <p className="explanation">{reasons[0] ?? firstSentence(lead.explanation)}</p>

      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <div className="flex min-w-0 flex-wrap gap-x-5 gap-y-1">
          {lead.contacts.emails[0] ? (
            <span className="contact"><Mail size={15} className="muted shrink-0" aria-hidden="true" /><a href={`mailto:${lead.contacts.emails[0].value}`}>{lead.contacts.emails[0].value}</a></span>
          ) : <span className="contact muted"><Mail size={15} aria-hidden="true" />Email not found</span>}
          {lead.contacts.phones[0] ? (
            <span className="contact"><Phone size={15} className="muted shrink-0" aria-hidden="true" /><a href={`tel:${lead.contacts.phones[0].value}`}>{lead.contacts.phones[0].value}</a></span>
          ) : <span className="contact muted"><Phone size={15} aria-hidden="true" />Phone not found</span>}
        </div>
        <button type="button" className="details-toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
          <ChevronDown size={16} style={{ transform: open ? "rotate(180deg)" : undefined, transition: "transform .2s" }} aria-hidden="true" />
          {open ? "Hide details" : "Evidence and reasoning"}
        </button>
      </div>

      {open && (
        <div className="details">
          <section className="grid gap-3">
            <p className="explanation">{lead.explanation}</p>
            {reasons.length > 0 && <p className="m-0 text-[14px] muted">{reasons.join(" ")}</p>}
            <div className="layers">
              {Object.entries(lead.layers).map(([key, value]) => (
                <span key={key} className={`layer ${layerTone(value)}`}>{LAYER_LABEL[key]}: <b>{value}</b></span>
              ))}
            </div>
            <div className="checks md:grid-cols-2">
              {lead.verification.map((v) => (
                <span key={v.label} className={`check ${v.ok ? "ok" : ""}`}>
                  {v.ok ? <CircleCheck size={16} aria-hidden="true" /> : <CircleMinus size={16} aria-hidden="true" />}
                  {v.label}{v.ok ? "" : ": no"}
                </span>
              ))}
            </div>
            {lead.contacts.emails.length + lead.contacts.phones.length > 0 && (
              <div className="grid gap-1">
                {[...lead.contacts.emails.map((c) => ({ ...c, icon: Mail })), ...lead.contacts.phones.map((c) => ({ ...c, icon: Phone }))].map(({ value, source_url, icon: Icon }) => (
                  <span key={value} className="contact text-2">
                    <Icon size={15} className="muted shrink-0" aria-hidden="true" />{value}
                    <a href={source_url} target="_blank" rel="noopener noreferrer" className="source-tag">source</a>
                  </span>
                ))}
              </div>
            )}
          </section>

          <section>
            <p className="section-label">Evidence from the company website</p>
            {facts.length === 0 ? <p className="m-0 muted text-[14px]">No statements about this product were found on the pages that were checked.</p> : (
              <div className="grid gap-2">
                {facts.map((f) => (
                  <div key={f.id} className="evidence">
                    <div className="evidence-head">
                      <span className="tag">{f.id}</span>
                      <span>{PREDICATE_LABEL[f.predicate]}:</span>
                      <strong style={f.polarity ? undefined : { textDecoration: "line-through" }}>{f.object_name}</strong>
                      {!f.polarity && <span style={{ color: "var(--c-rejected)" }}>(denied on the website)</span>}
                    </div>
                    {f.evidence.slice(0, 2).map((e) => (
                      <div key={e.url + e.quote} className="grid gap-1">
                        <p className="quote">“{e.quote}”</p>
                        <a href={e.url} target="_blank" rel="noopener noreferrer" className="text-[13px] inline-flex items-center gap-1">
                          {e.page_type} page: {shortUrl(e.url)} <ExternalLink size={12} aria-hidden="true" />
                        </a>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <p className="section-label">Reasoning: knowledge-base rules that fired</p>
            {lead.trace.rules_fired.length === 0 ? <p className="m-0 muted text-[14px]">No rule fired.</p> : (
              <div className="grid gap-2">
                {lead.trace.rules_fired.map((r) => {
                  const veto = lead.trace.vetoes.some((v) => v.id === r.id);
                  const cap = lead.trace.caps.some((c) => c.id === r.id);
                  return (
                    <div key={r.id} className="rule-row">
                      <span className={`tag ${veto ? "neg" : cap ? "cap" : r.kind === "positive" ? "pos" : ""}`}>{r.id}</span>
                      <span>{r.text}{r.facts.length > 0 && <span className="muted"> Based on {r.facts.join(", ")}.</span>}</span>
                    </div>
                  );
                })}
              </div>
            )}
            {lead.trace.conflicts.map((c, i) => (
              <div key={i} className="alert alert-warn mt-3">
                <b>Conflicting evidence:</b> {c.description}
                {c.evidence.slice(0, 2).map((e) => <div key={e.quote} className="mt-1 text-2">“{e.quote}”</div>)}
              </div>
            ))}
          </section>

          {lead.missing_information.length > 0 && (
            <section>
              <p className="section-label">Missing information</p>
              <ul className="bullets text-[14px] text-2">
                {lead.missing_information.map((m) => <li key={m}>{m}</li>)}
              </ul>
            </section>
          )}

          {lead.score && (
            <section>
              <p className="section-label">Evidence score breakdown (ranks leads, not a probability)</p>
              <div className="grid gap-2">
                {lead.score.breakdown.map((b) => (
                  <div key={b.factor} className="score-row" title={b.reason}>
                    <span className="text-2">{FACTOR_LABEL[b.factor] ?? b.factor}</span>
                    <span className="score-track"><span style={{ width: `${(b.earned / b.weight) * 100}%` }} /></span>
                    <span className="mono text-right">{b.earned}/{b.weight}</span>
                  </div>
                ))}
                {lead.score.penalties.map((p) => <div key={p.reason} className="text-[13.5px]" style={{ color: "var(--c-rejected)" }}>{p.points} points: {p.reason}</div>)}
                {lead.score.cap && <div className="text-[13.5px]" style={{ color: "var(--c-possible)" }}>{lead.score.cap}</div>}
              </div>
            </section>
          )}

          <section className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="section-label">Pages checked</p>
              {lead.pages_checked.length === 0 ? <p className="m-0 muted text-[14px]">None. {lead.errors[0]}</p> : (
                <ul className="m-0 grid gap-1 p-0 text-[13.5px]" style={{ listStyle: "none" }}>
                  {lead.pages_checked.map((p) => (
                    <li key={p.url} className="truncate">
                      <span className="muted">{p.page_type}: </span>
                      <a href={p.url} target="_blank" rel="noopener noreferrer">{shortUrl(p.url)}</a>
                    </li>
                  ))}
                  {lead.retrieved_at && <li className="muted">Retrieved {new Date(lead.retrieved_at).toLocaleString()}</li>}
                </ul>
              )}
            </div>
            <div>
              <p className="section-label">How it was found</p>
              <p className="m-0 text-[13.5px] text-2">
                {lead.found_via.source === "seed" ? "From your list of company URLs." : `Search result: “${lead.found_via.title}”.`} {lead.found_via.note}
              </p>
            </div>
          </section>
        </div>
      )}
    </article>
  );
}
