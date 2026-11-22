"use client";

import { useEffect, useRef, useState } from "react";

import { Logo } from "@/components/Brand";
import { getKnowledge } from "@/lib/api";
import type { KnowledgeBase, ProductId } from "@/lib/types";

const PRODUCTS: ProductId[] = ["raw_sheep_wool", "duck_down", "cashmere"];
type Line = { text: string; status: "ok" | "warn" | "info" };

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([promise, new Promise<T>((_, reject) => setTimeout(() => reject(new Error("timeout")), ms))]);
}

/** Start-up screen: loads the real knowledge bases and reports what was loaded. */
export default function Splash({ onDone }: { onDone: () => void }) {
  const [lines, setLines] = useState<Line[]>([]);
  const [total, setTotal] = useState(8);
  const [leaving, setLeaving] = useState(false);
  const [visible, setVisible] = useState(false);
  const finished = useRef(false);

  function finish() {
    if (finished.current) return;
    finished.current = true;
    try { sessionStorage.setItem("sbai-intro-seen", "1"); } catch { /* storage may be blocked */ }
    setLeaving(true);
    window.setTimeout(onDone, 500);
  }

  useEffect(() => {
    let seen = false;
    try { seen = sessionStorage.getItem("sbai-intro-seen") === "1"; } catch { /* ignore */ }
    if (seen) { onDone(); return; }
    setVisible(true);

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const step = reduced ? 60 : 380;
    const timers: number[] = [];
    let cancelled = false;

    (async () => {
      const results = await Promise.allSettled(PRODUCTS.map((p) => withTimeout(getKnowledge(p), 4000)));
      if (cancelled) return;
      const kbs = results.map((r) => (r.status === "fulfilled" ? r.value : null));
      const loaded = kbs.filter(Boolean) as KnowledgeBase[];
      const generic = loaded[0]?.rules.filter((r) => r.id.startsWith("G")).length ?? 0;
      const productRules = loaded.reduce((n, kb) => n + kb.rules.filter((r) => !r.id.startsWith("G")).length, 0);

      const plan: Line[] = [{ text: "Starting Smart Buyer AI", status: "info" }];
      kbs.forEach((kb, i) => {
        plan.push(kb
          ? { text: `Knowledge base · ${kb.name.padEnd(14)} ${kb.materials.length} materials · ${kb.activities.length} activities · ${kb.rules.filter((r) => !r.id.startsWith("G")).length} rules`, status: "ok" }
          : { text: `Knowledge base · ${PRODUCTS[i]} not reachable (is the backend running on port 8000?)`, status: "warn" });
      });
      plan.push(
        loaded.length
          ? { text: `Reasoning engine · forward chaining · ${generic} generic + ${productRules} product rules`, status: "ok" }
          : { text: "Reasoning engine · waiting for the backend", status: "warn" },
        { text: "Evidence grounding · every quote must exist on the company's own page", status: "ok" },
        { text: "Qualification · 5 classes · evidence score 0-100 (not a probability)", status: "ok" },
        { text: "Ready", status: "info" },
      );
      setTotal(plan.length);
      plan.forEach((line, i) => {
        timers.push(window.setTimeout(() => setLines((current) => [...current, line]), step * (i + 1)));
      });
      timers.push(window.setTimeout(finish, step * (plan.length + 1) + 400));
    })();

    return () => { cancelled = true; timers.forEach(clearTimeout); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!visible) return null;
  const progress = Math.round((lines.length / total) * 100);

  return (
    <div className={`splash ${leaving ? "is-leaving" : ""}`} role="status" aria-live="polite" aria-label="Loading Smart Buyer AI">
      <div className="splash-card">
        <div className="flex items-center gap-4">
          <Logo size={56} animated />
          <div>
            <h1 className="splash-title">Smart Buyer AI</h1>
            <p className="splash-sub">A Knowledge Base Intelligent Potential Customer Detection System</p>
          </div>
        </div>
        <div className="boot">
          {lines.map((line, i) => (
            <div key={i} className="boot-line">
              <span className={line.status === "ok" ? "ok" : line.status === "warn" ? "warn" : "muted"}>
                {line.status === "ok" ? "[ ok ]" : line.status === "warn" ? "[warn]" : "[ .. ]"}
              </span>
              <span>{line.text}</span>
            </div>
          ))}
        </div>
        <div className="grid gap-2">
          <div className="bar" aria-hidden="true"><span style={{ width: `${progress}%` }} /></div>
          <div className="flex justify-between text-[13px]">
            <span className="muted mono">{progress}%</span>
            <button type="button" className="link-btn" onClick={finish}>Skip</button>
          </div>
        </div>
      </div>
    </div>
  );
}
