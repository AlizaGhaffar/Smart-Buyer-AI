"use client";

import { BookOpen, Download, History, Info, Moon, Search, Sun, TriangleAlert, Workflow } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { FibreSwatch, Logo } from "@/components/Brand";
import HowItWorks from "@/components/HowItWorks";
import KnowledgeView from "@/components/KnowledgeView";
import LeadCard from "@/components/LeadCard";
import ResultsSummary from "@/components/ResultsSummary";
import SearchProgress, { type LogEntry } from "@/components/SearchProgress";
import Splash from "@/components/Splash";
import { getJob, getSnapshots, startSearch } from "@/lib/api";
import { exportLeads } from "@/lib/csv";
import {
  CLASS_INFO, QUALIFIED, type Classification, type Job, type ProductId, type SearchMode, type SearchResult, type Snapshot,
} from "@/lib/types";

const PRODUCTS: { id: ProductId; label: string; note: string }[] = [
  { id: "raw_sheep_wool", label: "Raw Sheep Wool", note: "Greasy or scoured wool fibre" },
  { id: "duck_down", label: "Duck Down", note: "Natural filling material" },
  { id: "cashmere", label: "Cashmere", note: "Raw or dehaired goat fibre" },
];
const MODES: { id: SearchMode; label: string; note: string }[] = [
  { id: "live", label: "Live web search", note: "Takes 1-3 minutes." },
  { id: "seed", label: "My company URLs", note: "Only the websites you paste below." },
  { id: "replay", label: "Saved search", note: "Works without internet." },
];
const VIEWS = [
  { id: "search", label: "Buyer Search", icon: Search },
  { id: "knowledge", label: "Knowledge Base", icon: BookOpen },
  { id: "how", label: "How it works", icon: Workflow },
] as const;
type View = (typeof VIEWS)[number]["id"];
type Tab = "qualified" | Classification | "excluded";

const POLL_MS = 1500;
const MAX_WAIT_MS = 10 * 60 * 1000;

function formatDate(iso: string | null) {
  if (!iso) return "unknown date";
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function Home() {
  const [ready, setReady] = useState(false);
  const [view, setView] = useState<View>("search");
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const [product, setProduct] = useState<ProductId>("raw_sheep_wool");
  const [country, setCountry] = useState("");
  const [mode, setMode] = useState<SearchMode>("live");
  const [seedText, setSeedText] = useState("");
  const [snapshots, setSnapshots] = useState<Snapshot[] | null>(null);

  const [job, setJob] = useState<Job | null>(null);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [tab, setTab] = useState<Tab>("qualified");
  const [showWarnings, setShowWarnings] = useState(false);
  const [showQueries, setShowQueries] = useState(false);
  const runId = useRef(0);

  // view from the URL hash (#knowledge, #how) and the saved theme
  useEffect(() => {
    const fromHash = () => {
      const h = window.location.hash.slice(1);
      setView(h === "knowledge" || h === "how" ? h : "search");
    };
    fromHash();
    window.addEventListener("hashchange", fromHash);
    setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
    return () => window.removeEventListener("hashchange", fromHash);
  }, []);
  useEffect(() => () => { runId.current += 1; }, []);

  useEffect(() => {
    if (mode !== "replay" || snapshots !== null) return;
    getSnapshots().then(setSnapshots).catch(() => setSnapshots([]));
  }, [mode, snapshots]);

  function go(next: View) {
    window.location.hash = next === "search" ? "" : next;
    setView(next);
  }
  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("sbai-theme", next); } catch { /* storage may be blocked */ }
  }

  const seedUrls = seedText.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
  const productName = PRODUCTS.find((p) => p.id === product)?.label ?? "";

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (mode === "seed" && seedUrls.length === 0) { setError("Paste at least one company website address."); return; }
    if (mode === "seed" && seedUrls.some((u) => !/^https?:\/\/\S+\.\S+/.test(u))) { setError("Every address must start with http:// or https://"); return; }
    const myRun = ++runId.current;
    setIsSearching(true); setResult(null); setJob(null); setLog([]); setElapsed(0);
    setTab("qualified"); setShowWarnings(false); setShowQueries(false);
    const started = Date.now();
    const stamp = () => {
      const s = Math.floor((Date.now() - started) / 1000);
      return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    };
    const clock = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    let lastMessage = "";
    try {
      const jobId = await startSearch({
        product, country: country.trim() || null, mode,
        seed_urls: mode === "seed" ? seedUrls.slice(0, 20) : [], max_candidates: 12,
      });
      setLog([{ at: stamp(), text: `Job started: ${productName}${country.trim() ? ` · ${country.trim()}` : ""} · ${mode}` }]);
      while (runId.current === myRun) {
        const current = await getJob(jobId);
        if (runId.current !== myRun) return;
        setJob(current);
        const message = current.progress.message;
        if (message && message !== lastMessage) {
          lastMessage = message;
          setLog((items) => [...items.slice(-80), { at: stamp(), text: message }]);
        }
        if (current.status === "done" && current.result) { setResult(current.result); break; }
        if (current.status === "failed") throw new Error(current.error ?? "The search failed.");
        if (Date.now() - started > MAX_WAIT_MS) throw new Error("The search took too long. Please try again.");
        await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
      }
    } catch (cause) {
      if (runId.current === myRun) setError(cause instanceof Error ? cause.message : "The analysis service is unavailable.");
    } finally {
      window.clearInterval(clock);
      if (runId.current === myRun) setIsSearching(false);
    }
  }

  const leads = result?.leads ?? [];
  const qualified = leads.filter((l) => QUALIFIED.includes(l.classification));
  const visible = tab === "qualified" ? qualified : tab === "excluded" ? [] : leads.filter((l) => l.classification === tab);
  const count = (c: Classification) => leads.filter((l) => l.classification === c).length;
  const tabs: { id: Tab; label: string; n: number }[] = [
    { id: "qualified", label: "Qualified", n: qualified.length },
    { id: "confirmed_purchaser", label: "Confirmed", n: count("confirmed_purchaser") },
    { id: "strong_potential_buyer", label: "Strong", n: count("strong_potential_buyer") },
    { id: "possible_potential_buyer", label: "Possible", n: count("possible_potential_buyer") },
    { id: "insufficient_evidence", label: "Insufficient", n: count("insufficient_evidence") },
    { id: "not_relevant", label: "Not relevant", n: count("not_relevant") },
    { id: "excluded", label: "Excluded sites", n: result?.excluded.length ?? 0 },
  ];
  const onSplashDone = useCallback(() => setReady(true), []);

  return (
    <>
      {!ready && <Splash onDone={onSplashDone} />}
      <header className="topbar">
        <div className="topbar-inner">
          <a href="#" className="brand" onClick={(e) => { e.preventDefault(); go("search"); }} aria-label="Smart Buyer AI home">
            <Logo />
            <span>
              <span className="brand-name block">Smart Buyer AI</span>
              <span className="brand-sub block">Knowledge-based buyer detection</span>
            </span>
          </a>
          <div className="flex flex-wrap items-center gap-3">
            <nav className="nav" role="tablist" aria-label="Sections">
              {VIEWS.map(({ id, label, icon: Icon }) => (
                <button key={id} type="button" role="tab" aria-selected={view === id} onClick={() => go(id)}>
                  <Icon size={16} aria-hidden="true" />{label}
                </button>
              ))}
            </nav>
            <button type="button" className="icon-btn" onClick={toggleTheme}
                    aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
                    title={theme === "dark" ? "Light theme (better on a projector)" : "Dark theme"}>
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
          </div>
        </div>
      </header>

      <main className="shell">
        {view === "search" && (
          <>
            <div className="page-head">
              <span className="eyebrow">Smart Buyer AI</span>
              <h1 className="page-title">A Knowledge Base Intelligent Potential Customer Detection System</h1>
              <p className="page-lede">Find companies that may buy raw sheep wool, duck down or cashmere, with website evidence for every result.</p>
              <div className="stat-strip">
                <span><b>3</b> product knowledge bases</span>
                <span><b>7</b>-stage pipeline</span>
                <span><b>5</b> qualification classes</span>
                <span><b>0</b> paid APIs</span>
              </div>
            </div>

            <div className="grid items-start gap-5 xl:grid-cols-[370px_minmax(0,1fr)]">
              <aside className="panel panel-pad">
                <form onSubmit={search} className="grid gap-5">
                  <div>
                    <p className="section-label">1 · Raw material</p>
                    <div className="grid gap-2" role="radiogroup" aria-label="Raw material">
                      {PRODUCTS.map((p) => (
                        <button key={p.id} type="button" role="radio" aria-checked={product === p.id} disabled={isSearching}
                                className="product-option" onClick={() => setProduct(p.id)}>
                          <FibreSwatch product={p.id} />
                          <span className="min-w-0 flex-1">
                            <span className="option-title">{p.label}</span>
                            <span className="option-note">{p.note}</span>
                          </span>
                          <span className="radio-dot" aria-hidden="true" />
                        </button>
                      ))}
                    </div>

                  </div>

                  <div>
                    <label htmlFor="country" className="field-label">2 · Target country <span className="muted font-normal">(optional)</span></label>
                    <input id="country" className="field" value={country} onChange={(e) => setCountry(e.target.value)}
                           maxLength={100} placeholder="e.g. Japan" disabled={isSearching} />
                  </div>

                  <div>
                    <p className="field-label">3 · Data source</p>
                    <div className="segmented" role="radiogroup" aria-label="Data source">
                      {MODES.map((m) => (
                        <button key={m.id} type="button" role="radio" aria-checked={mode === m.id} disabled={isSearching} onClick={() => setMode(m.id)}>{m.label}</button>
                      ))}
                    </div>
                    <p className="hint">{MODES.find((m) => m.id === mode)?.note}</p>
                    {mode === "seed" && (
                      <textarea id="seed-urls" className="field mt-2" rows={4} value={seedText} onChange={(e) => setSeedText(e.target.value)}
                                placeholder={"https://company-one.com\nhttps://company-two.it"} aria-label="Company website addresses" />
                    )}
                    {mode === "replay" && (
                      <div className="snapshot-list" role="radiogroup" aria-label="Saved searches">
                        {snapshots === null && <span className="hint">Loading saved searches…</span>}
                        {snapshots?.length === 0 && <span className="hint">No saved searches yet. Run a live search first.</span>}
                        {snapshots?.map((s) => {
                          const selected = s.product === product && (s.country ?? "") === country.trim();
                          return (
                            <button key={`${s.product}-${s.country}`} type="button" role="radio" aria-checked={selected} className="snapshot"
                                    onClick={() => { setProduct(s.product); setCountry(s.country ?? ""); }}>
                              <span className="flex min-w-0 items-center gap-2">
                                <FibreSwatch product={s.product} />
                                <span className="min-w-0">
                                  <span className="block font-medium">{s.product_name} · {s.country ?? "any country"}</span>
                                  <span className="block muted text-[12.5px]">{s.companies} companies · {formatDate(s.recorded_at)}</span>
                                </span>
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {error && <p role="alert" className="alert alert-error m-0">{error}</p>}
                  <button type="submit" className="btn-primary" disabled={isSearching}>
                    {isSearching ? <><span className="pulse" style={{ background: "var(--accent-ink)" }} />Analysing…</> : <><Search size={18} aria-hidden="true" />Find potential buyers</>}
                  </button>
                </form>
              </aside>

              <section className="panel min-w-0" aria-label="Results">
                <div className="panel-head">
                  <div>
                    <h2 className="panel-title">Buyer analysis</h2>
                    <p className="panel-sub">
                      {isSearching ? `Analysing ${productName} buyers${country.trim() ? ` in ${country.trim()}` : ""}`
                        : result ? `${result.product.name}${result.country ? ` · ${result.country}` : ""} · finished ${formatDate(result.finished_at)}`
                        : "Results, evidence and reasoning will appear here"}
                    </p>
                  </div>
                  <button type="button" className="btn-secondary" disabled={!qualified.length}
                          onClick={() => result && exportLeads(result, qualified)} title="Confirmed, Strong and Possible buyers with their evidence">
                    <Download size={16} aria-hidden="true" />Download CSV
                  </button>
                </div>

                {isSearching ? <SearchProgress job={job} log={log} elapsed={elapsed} /> : result ? (
                  <div className="panel-pad grid gap-5">
                    {result.mode === "replay" && (
                      <div className="alert alert-info flex items-start gap-2">
                        <History size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
                        <span>Saved search: these results re-analyse pages recorded on {formatDate(result.recorded_at)}. This is not a live search.</span>
                      </div>
                    )}
                    <ResultsSummary result={result} />
                    <div className="flex flex-wrap gap-4">
                      {result.queries.length > 0 && (
                        <button type="button" className="link-btn" onClick={() => setShowQueries((v) => !v)}>
                          <Search size={15} aria-hidden="true" />{showQueries ? "Hide" : "Show"} the {result.queries.length} search queries used
                        </button>
                      )}
                      {result.warnings.length > 0 && (
                        <button type="button" className="link-btn" onClick={() => setShowWarnings((v) => !v)}>
                          <TriangleAlert size={15} aria-hidden="true" />{showWarnings ? "Hide" : "Show"} {result.warnings.length} notices (sites that could not be checked)
                        </button>
                      )}
                    </div>
                    {showQueries && <div className="log">{result.queries.map((q) => <div key={q}>{q}</div>)}</div>}
                    {showWarnings && (
                      <div className="log">
                        {result.warnings.map((w, i) => <div key={i}>{w.company ? `${w.company}: ` : w.query ? `"${w.query}": ` : ""}{w.message}</div>)}
                      </div>
                    )}

                    <div className="tabs" role="tablist" aria-label="Filter by class">
                      {tabs.map((t) => (
                        <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} className="tab" onClick={() => setTab(t.id)}>
                          {t.label}<span className="count">{t.n}</span>
                        </button>
                      ))}
                    </div>
                    {tab !== "qualified" && tab !== "excluded" && (
                      <p className="m-0 flex items-start gap-2 text-[14px] muted"><Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />{CLASS_INFO[tab].description}</p>
                    )}

                    {tab === "excluded" ? (
                      result.excluded.length ? (
                        <div className="grid gap-2">
                          {result.excluded.map((e, i) => (
                            <div key={i} className="evidence">
                              <span className="truncate text-[14px]">{e.url}</span>
                              <span className="muted text-[13px]">{e.reason}</span>
                            </div>
                          ))}
                        </div>
                      ) : <Empty title="No sites were excluded" text="Every search result was a company website." />
                    ) : visible.length ? (
                      <div className="grid gap-3">{visible.map((lead) => <LeadCard key={lead.company_key} lead={lead} />)}</div>
                    ) : tab === "qualified" ? (
                      <Empty title="No qualified buyers found" text={result.summary.examined
                        ? `${result.summary.examined} companies were examined, but none had enough website evidence. Open the Insufficient and Not relevant tabs to see why, or try another country.`
                        : "The search found no company websites to check. Try another country or paste company addresses."} />
                    ) : <Empty title="No companies in this group" text="Choose another tab to see the other results." />}
                  </div>
                ) : (
                  <Empty title={error ? "The search did not finish" : "Ready when you are"}
                         text={error || "Choose a raw material and press Find potential buyers."} />
                )}
              </section>
            </div>
          </>
        )}

        {view === "knowledge" && (
          <>
            <div className="page-head">
              <span className="eyebrow">Knowledge representation</span>
              <h1 className="page-title">Product knowledge bases</h1>
              <p className="page-lede">Separate knowledge and rules for each raw material.</p>
            </div>
            <KnowledgeView initial={product} />
          </>
        )}

        {view === "how" && (
          <>
            <div className="page-head">
              <span className="eyebrow">System architecture</span>
              <h1 className="page-title">How Smart Buyer AI decides</h1>
              <p className="page-lede">AI reads the websites. Rules make the decision. Every step keeps its evidence.</p>
            </div>
            <HowItWorks />
          </>
        )}
      </main>
    </>
  );
}

function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <div>
        <div className="mx-auto w-fit opacity-80"><Logo size={48} /></div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </div>
  );
}
