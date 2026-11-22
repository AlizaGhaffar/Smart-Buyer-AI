import type { Lead, SearchResult } from "./types";

function csvCell(value: string | number | null | undefined) {
  const text = value === null || value === undefined ? "" : String(value);
  // Leading = + - @ would be treated as a formula by Excel.
  const safe = /^[=+\-@]/.test(text) ? `'${text}` : text;
  return `"${safe.replaceAll('"', '""')}"`;
}

/** The strongest piece of material evidence for a lead (falls back to the first fact). */
export function keyEvidence(lead: Lead) {
  const material = lead.facts.find((f) => f.polarity && f.predicate === "uses_material");
  const fact = material ?? lead.facts.find((f) => f.polarity);
  return fact?.evidence[0] ?? null;
}

export function exportLeads(result: SearchResult, leads: Lead[]) {
  const header = [
    "Company", "Official website", "Country", "Country source", "Product", "Classification",
    "Evidence score (0-100, not a probability)", "Why", "Rules fired", "Business activities",
    "Materials used", "Alternative materials", "Key evidence quote", "Evidence URL", "Emails",
    "Email source", "Phones", "Phone source", "Purchasing evidence", "Missing information",
    "Retrieved at", "Data mode",
  ];
  const rows = leads.map((lead) => {
    const evidence = keyEvidence(lead);
    return [
      lead.company_name,
      lead.official_website ?? "Not found",
      lead.country.value ?? "Not found",
      lead.country.source ?? "",
      result.product.name,
      lead.label,
      lead.score?.value ?? "",
      lead.explanation,
      lead.trace.rules_fired.map((r) => r.id).join("; "),
      lead.business_activities.join("; "),
      lead.materials_used.join("; "),
      lead.alternative_materials.join("; "),
      evidence?.quote ?? "",
      evidence?.url ?? "",
      lead.contacts.emails.map((c) => c.value).join("; ") || "Not found",
      [...new Set(lead.contacts.emails.map((c) => c.source_url))].join("; "),
      lead.contacts.phones.map((c) => c.value).join("; ") || "Not found",
      [...new Set(lead.contacts.phones.map((c) => c.source_url))].join("; "),
      lead.layers.purchasing === "direct" ? "Yes (self-declared on website)" : "Not found",
      lead.missing_information.join(" | "),
      lead.retrieved_at ?? "",
      result.mode === "replay" ? `replay of data recorded ${result.recorded_at}` : result.mode,
    ];
  });
  const csv = [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob(["﻿", csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `smart-buyer-ai-${result.product.id}-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
