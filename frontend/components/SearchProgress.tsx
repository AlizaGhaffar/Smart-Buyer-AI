"use client";

import { Check } from "lucide-react";
import { useEffect, useRef } from "react";

import type { Job } from "@/lib/types";

export const PIPELINE_STAGES = [
  { id: "searching", label: "Product-specific web search", detail: "Queries built from the knowledge base" },
  { id: "collecting", label: "Candidate collection", detail: "Duplicates, directories and marketplaces removed" },
  { id: "verifying", label: "Website verification", detail: "Own pages only, robots.txt respected" },
  { id: "analysing", label: "Extraction and reasoning", detail: "Facts, grounding check, KRR rules, qualification" },
];

export type LogEntry = { at: string; text: string };

export default function SearchProgress({ job, log, elapsed }: { job: Job | null; log: LogEntry[]; elapsed: number }) {
  const stage = job?.stage ?? "queued";
  const index = PIPELINE_STAGES.findIndex((s) => s.id === stage);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [log.length]);

  const stagePart = index < 0 ? 0 : index / PIPELINE_STAGES.length;
  const within = job && job.progress.total > 0 ? job.progress.done / job.progress.total / PIPELINE_STAGES.length : 0;
  const percent = Math.min(99, Math.round((stagePart + within) * 100));

  return (
    <div className="panel-pad grid gap-5" aria-live="polite">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="section-label">Pipeline running</p>
          <p className="m-0 text-[17px] font-semibold">{index >= 0 ? PIPELINE_STAGES[index].label : "Starting the search job"}</p>
        </div>
        <span className="mono muted text-[13px]">{percent}% · {elapsed}s</span>
      </div>
      <div className="bar" aria-hidden="true"><span style={{ width: `${percent}%` }} /></div>

      <div className="stepper">
        {PIPELINE_STAGES.map((s, i) => {
          const state = index < 0 ? "" : i < index ? "is-done" : i === index ? "is-active" : "";
          return (
            <div key={s.id} className={`step ${state}`}>
              <span className="step-dot">{i < index ? <Check size={14} /> : i === index ? <span className="pulse" /> : i + 1}</span>
              <span>
                <span className="block font-medium">{s.label}</span>
                <span className="block text-[13px] muted">{s.detail}</span>
              </span>
              {i === index && job && job.progress.total > 0 && (
                <span className="mono text-[13px]">{job.progress.done}/{job.progress.total}</span>
              )}
            </div>
          );
        })}
      </div>

      <div>
        <p className="section-label">Live log</p>
        <div className="log" ref={logRef}>
          {log.length === 0 ? <div className="muted">Waiting for the first update…</div> : log.map((entry, i) => (
            <div key={i} className="log-line"><time>{entry.at}</time><span>{entry.text}</span></div>
          ))}
        </div>
      </div>
    </div>
  );
}
