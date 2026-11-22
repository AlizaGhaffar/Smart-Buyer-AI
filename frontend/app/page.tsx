"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, BookOpen, Check, Download, Globe2, History, Info, Search, TriangleAlert } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import KnowledgePanel from "@/components/KnowledgePanel";
import LeadCard from "@/components/LeadCard";
import { getJob, startSearch } from "@/lib/api";
import { exportLeads } from "@/lib/csv";
import { CLASS_INFO, QUALIFIED, type Classification, type Job, type ProductId, type SearchMode, type SearchResult } from "@/lib/types";

const PRODUCTS: { id: ProductId; label: string; emoji: string; note: string }[] = [
  { id: "raw_sheep_wool", label: "Raw Sheep Wool", emoji: "🐑", note: "Greasy / scoured wool fibre" },
  { id: "duck_down", label: "Duck Down", emoji: "🦆", note: "Natural filling material" },
  { id: "cashmere", label: "Cashmere", emoji: "🧶", note: "Raw / dehaired goat fibre" },
];
const MODES: { id: SearchMode; label: string; note: string }[] = [
  { id: "live", label: "Live web search", note: "Searches the web and checks company websites (1-3 minutes)." },
  { id: "seed", label: "My company URLs", note: "Analyses only the websites you paste below. No web search." },
  { id: "replay", label: "Saved replay", note: "Re-analyses the pages saved by the last live search for this product and country. No internet needed." },
];
const STAGE_LABEL: Record<string, string> = {
  searching: "Searching the web for buyer companies",
  collecting: "Removing duplicates and directory sites",
  verifying: "Checking official company websites",
  analysing: "Extracting facts and running the knowledge-base rules",
  done: "Qualifying leads",
};
const PIPELINE_STAGES = ["searching", "collecting", "verifying", "analysing", "done"];
const POLL_MS = 1500;
const MAX_WAIT_MS = 10 * 60 * 1000;

type Tab = "qualified" | Classification | "excluded";

function Radar() {
  return <div className="radar relative flex h-32 w-32 items-center justify-center rounded-full border border-cyan-300/20 bg-cyan-300/[0.035]" aria-hidden="true">
    <span className="absolute inset-3 rounded-full border border-cyan-300/15"/><span className="absolute inset-7 rounded-full border border-cyan-300/15"/><span className="absolute inset-[42px] rounded-full border border-cyan-300/20"/>
    <span className="radar-sweep absolute inset-0 overflow-hidden rounded-full"/><span className="absolute left-1/2 top-1/2 h-px w-[46%] origin-left bg-cyan-300/50"/><span className="relative z-10 h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_5px_rgba(34,211,238,.5)]"/>
  </div>;
}

export default function Home() {
  const [product, setProduct] = useState<ProductId>("raw_sheep_wool");
  const [country, setCountry] = useState("");
  const [mode, setMode] = useState<SearchMode>("live");
  const [seedText, setSeedText] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [tab, setTab] = useState<Tab>("qualified");
  const [showKb, setShowKb] = useState(false);
  const [showWarnings, setShowWarnings] = useState(false);
  const runId = useRef(0);

  useEffect(() => () => { runId.current += 1; }, []);  // stop polling on unmount

  const seedUrls = seedText.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (mode === "seed" && seedUrls.length === 0) { setError("Paste at least one company website URL."); return; }
    if (seedUrls.some((u) => !/^https?:\/\/\S+\.\S+/.test(u))) { setError("Every seed URL must start with http:// or https://"); return; }
    const myRun = ++runId.current;
    setIsSearching(true); setResult(null); setJob(null); setTab("qualified"); setShowWarnings(false);
    try {
      const jobId = await startSearch({
        product, country: country.trim() || null, mode,
        seed_urls: mode === "seed" ? seedUrls.slice(0, 20) : [], max_candidates: 12,
      });
      const started = Date.now();
      while (runId.current === myRun) {
        const current = await getJob(jobId);
        if (runId.current !== myRun) return;
        setJob(current);
        if (current.status === "done" && current.result) { setResult(current.result); break; }
        if (current.status === "failed") throw new Error(current.error ?? "The search failed.");
        if (Date.now() - started > MAX_WAIT_MS) throw new Error("The search took too long. Please try again.");
        await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
      }
    } catch (cause) {
      if (runId.current === myRun) setError(cause instanceof Error ? cause.message : "The analysis service is unavailable.");
    } finally {
      if (runId.current === myRun) setIsSearching(false);
    }
  }

  const leads = result?.leads ?? [];
  const qualified = leads.filter((l) => QUALIFIED.includes(l.classification));
  const visible = tab === "qualified" ? qualified : tab === "excluded" ? [] : leads.filter((l) => l.classification === tab);
  const count = (c: Classification) => leads.filter((l) => l.classification === c).length;
  const closeKb = useCallback(() => setShowKb(false), []);
  const productName = PRODUCTS.find((p) => p.id === product)?.label;

  const tabs: { id: Tab; label: string; n: number }[] = [
    { id: "qualified", label: "Qualified", n: qualified.length },
    { id: "confirmed_purchaser", label: "Confirmed", n: count("confirmed_purchaser") },
    { id: "strong_potential_buyer", label: "Strong", n: count("strong_potential_buyer") },
    { id: "possible_potential_buyer", label: "Possible", n: count("possible_potential_buyer") },
    { id: "insufficient_evidence", label: "Insufficient", n: count("insufficient_evidence") },
    { id: "not_relevant", label: "Not relevant", n: count("not_relevant") },
    { id: "excluded", label: "Excluded sites", n: result?.excluded.length ?? 0 },
  ];

  return <main className="relative min-h-screen overflow-hidden bg-[#0f172a] text-slate-100">
    <div className="ambient ambient-one"/><div className="ambient ambient-two"/>
    <header className="relative z-10 border-b border-white/[0.07] bg-[#0b1220]/75 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-[1440px] items-center justify-between px-4 sm:px-8 lg:px-12">
        <a href="#" className="flex items-center gap-3" aria-label="Smart Buyer AI home"><span className="brand-mark">S.</span><span className="text-sm font-semibold tracking-tight">Smart Buyer <span className="gradient-text">AI</span></span></a>
        <div className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-[11px] font-medium text-slate-400"><span className="status-dot"/> Knowledge-based buyer detection</div>
      </div>
    </header>

    <div className="relative z-[1] mx-auto max-w-[1440px] px-4 pb-16 pt-9 sm:px-8 sm:pt-12 lg:px-12">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .45 }} className="mb-9 flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div>
          <p className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[.19em] text-cyan-300"><span className="h-px w-6 bg-cyan-300/70"/> Smart Buyer AI</p>
          <h1 className="max-w-3xl text-[30px] font-semibold leading-[1.1] tracking-[-.04em] sm:text-[40px]">A Knowledge Base Intelligent <span className="gradient-text">Potential Customer Detection</span> System</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Finds international companies that may need raw sheep wool, duck down or cashmere. Every result shows the website evidence and the knowledge-base rules behind it.</p>
        </div>
        <div className="flex items-center gap-2 pb-1 text-xs text-slate-400"><span className="flex h-7 w-7 items-center justify-center rounded-full border border-emerald-300/15 bg-emerald-300/[0.08] text-emerald-300"><Check size={15} aria-hidden="true"/></span> Evidence from company websites only</div>
      </motion.div>

      <div className="grid items-start gap-5 xl:grid-cols-[350px_minmax(0,1fr)]">
        <motion.aside initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .4, delay: .05 }} className="glass-panel rounded-2xl p-5 sm:p-6">
          <div className="mb-5 flex items-start justify-between"><div><h2 className="text-sm font-semibold">Build your search</h2><p className="mt-1 text-xs text-slate-500">Choose one raw material</p></div><span className="step-label">01 <span className="text-slate-600">/</span> 02</span></div>
          <form onSubmit={search}>
            <div className="space-y-2.5" role="radiogroup" aria-label="Product">
              {PRODUCTS.map((p) => { const checked = product === p.id; return <motion.button key={p.id} type="button" role="radio" aria-checked={checked} whileHover={{ y: -1 }} whileTap={{ scale: .99 }} onClick={() => setProduct(p.id)} disabled={isSearching} className={`product-card ${checked ? "product-card-selected" : ""}`}>
                <span className={`product-emoji ${checked ? "product-emoji-selected" : ""}`}>{p.emoji}</span><span className="min-w-0 flex-1"><span className="block text-[13px] font-semibold text-slate-200">{p.label}</span><span className="mt-0.5 block text-[11px] text-slate-500">{p.note}</span></span><span className={`check-box rounded-full ${checked ? "check-box-selected" : ""}`}>{checked && <Check size={13}/>}</span>
              </motion.button>; })}
            </div>
            <button type="button" onClick={() => setShowKb(true)} className="mt-3 inline-flex items-center gap-1.5 text-[11px] text-cyan-300/90 hover:text-cyan-200"><BookOpen size={13} aria-hidden="true"/> View the {productName} knowledge base and rules</button>

            <div className="my-5 h-px bg-white/[0.07]"/>
            <label htmlFor="country" className="mb-2 block text-xs font-medium text-slate-300">Target country <span className="font-normal text-slate-600">(optional)</span></label>
            <div className="relative"><Globe2 size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" aria-hidden="true"/><input id="country" value={country} onChange={(e) => setCountry(e.target.value)} maxLength={100} placeholder="e.g. Japan" disabled={isSearching} className="field-input w-full" style={{ paddingLeft: 36 }}/></div>

            <div className="my-5 h-px bg-white/[0.07]"/>
            <p className="mb-2 text-xs font-medium text-slate-300">Data source</p>
            <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-label="Data source">
              {MODES.map((m) => <button key={m.id} type="button" role="radio" aria-checked={mode === m.id} onClick={() => setMode(m.id)} disabled={isSearching} className={`mode-button ${mode === m.id ? "mode-button-selected" : ""}`}>{m.label}</button>)}
            </div>
            <p className="mt-2 text-[10px] leading-4 text-slate-500">{MODES.find((m) => m.id === mode)?.note}</p>
            {mode === "seed" && <textarea value={seedText} onChange={(e) => setSeedText(e.target.value)} rows={4} placeholder={"https://company-one.com\nhttps://company-two.it"} aria-label="Company website URLs" className="field-input mt-2 h-auto w-full py-2 leading-5"/>}

            {error && <p role="alert" className="mt-4 rounded-lg border border-rose-400/20 bg-rose-400/[0.08] px-3 py-2 text-xs leading-5 text-rose-200">{error}</p>}
            <button type="submit" disabled={isSearching} className="scan-button mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-xl text-[13px] font-semibold text-slate-950 disabled:cursor-wait disabled:opacity-75">
              {isSearching ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950/30 border-t-slate-950"/>Analysing…</> : <><Search size={17} aria-hidden="true"/>Find potential buyers<ArrowUpRight size={15} className="ml-1" aria-hidden="true"/></>}
            </button>
            <p className="mt-3 text-center text-[10px] text-slate-600">Respects robots.txt <span className="mx-1.5">·</span> No paid API required</p>
          </form>
        </motion.aside>

        <motion.section initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .4, delay: .1 }} className="glass-panel min-h-[540px] overflow-hidden rounded-2xl">
          <div className="flex flex-col justify-between gap-4 border-b border-white/[0.07] px-5 py-5 sm:flex-row sm:items-center sm:px-6">
            <div>
              <div className="flex items-center gap-2.5"><h2 className="text-sm font-semibold">Buyer analysis</h2>{result && <span className="count-badge">{qualified.length} qualified</span>}</div>
              <p className="mt-1 text-xs text-slate-500">{isSearching ? `Analysing ${productName} buyers…` : result
                ? `${result.summary.examined} companies examined for ${result.product.name}${result.country ? ` in ${result.country}` : ""} · ${result.summary.duplicates_removed} duplicates removed`
                : "Qualified companies and their evidence will appear here"}</p>
            </div>
            <button type="button" onClick={() => result && exportLeads(result, qualified)} disabled={!qualified.length} className="export-button" title="Exports Confirmed, Strong and Possible buyers with their evidence"><Download size={15} aria-hidden="true"/>Download CSV</button>
          </div>

          {isSearching ? <Progress job={job}/> : result ? <div className="px-5 py-4 sm:px-6">
            {result.mode === "replay" && <div className="mb-4 flex items-start gap-2 rounded-lg border border-indigo-300/20 bg-indigo-300/[0.06] px-3 py-2.5 text-xs leading-5 text-indigo-100/90"><History size={15} className="mt-0.5 shrink-0" aria-hidden="true"/>Replay: these results re-analyse pages saved on {result.recorded_at ? new Date(result.recorded_at).toLocaleString() : "an earlier run"}. This is not a live search.</div>}
            {result.warnings.length > 0 && <div className="mb-4 rounded-lg border border-amber-300/15 bg-amber-300/[0.05] px-3 py-2.5 text-xs leading-5 text-amber-100/80">
              <button type="button" onClick={() => setShowWarnings((v) => !v)} className="flex items-center gap-2"><TriangleAlert size={14} aria-hidden="true"/>{result.warnings.length} notices: some searches or pages could not be checked ({showWarnings ? "hide" : "show"})</button>
              {showWarnings && <ul className="mt-2 max-h-40 space-y-0.5 overflow-y-auto text-[10px] text-amber-100/60">{result.warnings.map((w, i) => <li key={i}>{w.company ? `${w.company}: ` : w.query ? `“${w.query}”: ` : ""}{w.message}</li>)}</ul>}
            </div>}

            <div className="mb-4 flex flex-wrap gap-1.5" role="tablist" aria-label="Filter by classification">
              {tabs.map((t) => <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)} className={`tab-button ${tab === t.id ? "tab-button-selected" : ""}`}>{t.label} <span className="opacity-60">{t.n}</span></button>)}
            </div>
            {tab !== "qualified" && tab !== "excluded" && <p className="mb-3 flex items-start gap-1.5 text-[11px] leading-4 text-slate-500"><Info size={13} className="mt-0.5 shrink-0" aria-hidden="true"/>{CLASS_INFO[tab].description}</p>}

            {tab === "excluded" ? (result.excluded.length ? <ul className="space-y-1.5">{result.excluded.map((e, i) => <li key={i} className="evidence-item text-[11px]"><span className="block truncate text-slate-300">{e.url}</span><span className="text-slate-500">{e.reason}</span></li>)}</ul> : <Empty title="No sites were excluded" text="Every search result was a company website."/>)
              : visible.length ? <div className="space-y-3">{visible.map((lead) => <LeadCard key={lead.company_key} lead={lead}/>)}</div>
              : tab === "qualified" ? <Empty title="No qualified buyers found" text={result.summary.examined
                  ? `${result.summary.examined} companies were examined, but none had enough website evidence. Check the Insufficient and Not relevant tabs to see why, or try another country.`
                  : "The search found no company websites to check. Try another country, or paste company URLs."}/>
              : <Empty title="No companies in this group" text="Choose another tab to see the other results."/>}
          </div>
          : <Empty title={error ? "The search did not finish" : "Ready when you are"} text={error || "Choose a raw material, optionally a country, and start the search. Each result explains why the company was or was not selected."}/>}
        </motion.section>
      </div>
      <footer className="mt-7 flex flex-col gap-2 text-[10px] text-slate-600 sm:flex-row sm:items-center sm:justify-between">
        <p>Classifications are based on public website statements. A potential buyer is not a confirmed customer, so check the evidence before you get in touch.</p>
        <p>Smart Buyer AI · Knowledge Representation &amp; Reasoning</p>
      </footer>
    </div>
    {showKb && <KnowledgePanel product={product} onClose={closeKb}/>}
  </main>;
}

function Progress({ job }: { job: Job | null }) {
  const current = job?.stage ?? "queued";
  const index = PIPELINE_STAGES.indexOf(current);
  return <div className="flex min-h-[440px] flex-col items-center justify-center px-6 py-12 text-center" aria-live="polite">
    <Radar/>
    <p className="mt-7 text-sm font-semibold text-slate-100">{STAGE_LABEL[current] ?? "Starting the search"}</p>
    <div className="mt-5 w-full max-w-[320px] space-y-2.5 text-left">
      {PIPELINE_STAGES.map((stage, i) => <div key={stage} className={`scan-step ${i === index ? "scan-step-active" : i < index ? "scan-step-done" : ""}`}>
        <span className="step-indicator">{i < index ? <Check size={11}/> : i === index ? <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300"/> : <span className="h-1 w-1 rounded-full bg-slate-700"/>}</span>
        {STAGE_LABEL[stage]}
        {i === index && job && job.progress.total > 0 && <span className="ml-auto text-slate-500">{job.progress.done}/{job.progress.total}</span>}
      </div>)}
    </div>
    {job?.progress.message && <p className="mt-5 max-w-sm truncate text-[11px] text-slate-500">{job.progress.message}</p>}
  </div>;
}

function Empty({ title, text }: { title: string; text: string }) {
  return <div className="flex min-h-[380px] flex-col items-center justify-center px-6 py-12 text-center">
    <div className="empty-orbit"><Search size={23} aria-hidden="true"/></div>
    <p className="mt-5 text-sm font-semibold text-slate-200">{title}</p>
    <p className="mt-1.5 max-w-[420px] text-xs leading-5 text-slate-500">{text}</p>
  </div>;
}
