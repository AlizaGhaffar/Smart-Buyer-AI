import type { Job, KnowledgeBase, ProductId, SearchMode, Snapshot } from "./types";

export function errorMessage(payload: unknown, fallback = "The request failed. Please try again."): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (typeof item === "object" && item !== null && "msg" in item ? String(item.msg) : ""))
        .filter(Boolean);
      if (messages.length) return messages.join(" ");
    }
  }
  return fallback;
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function startSearch(body: {
  product: ProductId;
  country: string | null;
  mode: SearchMode;
  seed_urls: string[];
  max_candidates: number;
}): Promise<{ jobId: string; job: Job | null }> {
  const response = await fetch("/api/v2/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(errorMessage(payload, "Could not start the search."));
  if (typeof payload !== "object" || payload === null || !("job_id" in payload)) {
    throw new Error("The analysis service returned an unexpected response.");
  }
  // A serverless backend runs the search inside this request and returns the finished job.
  const { job_id, job } = payload as { job_id: string; job?: Job | null };
  return { jobId: String(job_id), job: job ?? null };
}

export async function getJob(jobId: string): Promise<Job> {
  const response = await fetch(`/api/v2/search/${jobId}`, { cache: "no-store" });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(errorMessage(payload, "Could not read the search status."));
  return payload as Job;
}

export async function getKnowledge(product: ProductId): Promise<KnowledgeBase> {
  const response = await fetch(`/api/v2/knowledge/${product}`);
  const payload = await readJson(response);
  if (!response.ok) throw new Error(errorMessage(payload, "Could not load the knowledge base."));
  return payload as KnowledgeBase;
}

export async function getSnapshots(): Promise<Snapshot[]> {
  const response = await fetch("/api/v2/snapshots", { cache: "no-store" });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(errorMessage(payload, "Could not load saved searches."));
  return Array.isArray(payload) ? (payload as Snapshot[]) : [];
}
