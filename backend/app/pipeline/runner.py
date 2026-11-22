"""The full lead-detection pipeline (stages 2-7) and its response schema.

Modes
  live    search the web (+ optional seed URLs), fetch websites, analyse
  seed    only the user's seed URLs (no web search)
  replay  re-analyse the pages saved by the last live/seed run for the same
          product and country - no network. Marked as replay in the response.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..company_analysis import CompanyAnalysis, analyze_company
from ..extraction.nlp_extractor import PageText
from ..knowledge.products import get_kb
from ..knowledge.schema import ProductKB
from ..reasoning.qualification import CONFIRMED, INSUFFICIENT, NOT_RELEVANT, POSSIBLE, STRONG
from .candidates import Candidate, collect_candidates
from .contacts import extract_contacts
from .search_service import SearchError, search_candidates
from .website import CrawlResult, FetchedPage, RobotsPolicy, SafeHttpFetcher, crawl

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "data" / "snapshots"
CLASS_ORDER = [CONFIRMED, STRONG, POSSIBLE, INSUFFICIENT, NOT_RELEVANT]
STAGES = ["searching", "collecting", "verifying", "analysing", "done"]
CRAWL_WORKERS = 4
DIRECTORY_TITLE_RE = re.compile(
    r"\b(directory|marketplace|b2b platform|suppliers? list|manufacturers? list|yellow pages|"
    r"index|intelligence|news|magazine|journal|portal|database)\b", re.I)


@dataclass
class PipelineRequest:
    product: str
    country: str | None = None
    max_candidates: int = 12
    seed_urls: list[str] = field(default_factory=list)
    mode: str = "live"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def snapshot_path(product: str, country: str | None) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", (country or "any").lower()).strip("-") or "any"
    return SNAPSHOT_DIR / f"{product}__{slug}.json"


# ------------------------------------------------------------- run ---------


def run_pipeline(req: PipelineRequest, progress=lambda **kw: None, *,
                 search_provider=None, fetcher=None, search_sleep=None,
                 snapshot_dir: Path | None = None) -> dict:
    kb = get_kb(req.product)
    warnings: list[dict] = []
    started = _now()
    snapshot_file = (snapshot_dir / snapshot_path(req.product, req.country).name
                     if snapshot_dir else snapshot_path(req.product, req.country))

    if req.mode == "replay":
        progress(stage="analysing", done=0, total=0, message="Loading saved snapshot")
        crawls, excluded, recorded_at = _load_snapshot(snapshot_file)
        queries: list[str] = []
        duplicates = 0
    else:
        recorded_at = None
        hits, queries = [], []
        if req.mode == "live":
            progress(stage="searching", done=0, total=0, message="Searching the web")
            kwargs = {"sleep": search_sleep} if search_sleep else {}
            outcome = search_candidates(kb, req.country, search_provider, **kwargs)
            warnings += outcome.warnings
            queries = outcome.queries
            hits = outcome.hits
            if outcome.successful_queries == 0 and not req.seed_urls:
                raise SearchError("The web search failed for every query (the provider may be "
                                  "rate-limiting). Try again later, add seed URLs, or use replay mode.")
            if outcome.successful_queries == 0:
                warnings.append({"stage": "search", "message": "Web search failed; continuing with seed URLs only."})
        progress(stage="collecting", done=0, total=0, message="Removing duplicates and directory sites")
        cset = collect_candidates(hits, req.seed_urls, req.max_candidates)
        excluded, duplicates = cset.excluded, cset.duplicates_removed

        fetcher = fetcher or SafeHttpFetcher()
        robots = RobotsPolicy(fetcher)
        total = len(cset.candidates)
        progress(stage="verifying", done=0, total=total, message="Checking company websites")
        crawls = []
        with ThreadPoolExecutor(max_workers=CRAWL_WORKERS) as pool:
            futures = {pool.submit(crawl, c, fetcher, robots): c for c in cset.candidates}
            for i, future in enumerate(as_completed(futures), 1):
                c = futures[future]
                try:
                    crawls.append(future.result())
                except Exception as error:  # never drop a candidate silently
                    logger.exception("Crawl failed for %s", c.key)
                    crawls.append(CrawlResult(c, errors=[f"unexpected error: {type(error).__name__}"]))
                progress(stage="verifying", done=i, total=total, message=f"Checked {c.key}")
        order = {c.key: i for i, c in enumerate(cset.candidates)}
        crawls.sort(key=lambda r: order[r.candidate.key])
        _save_snapshot(snapshot_file, req, crawls, excluded)

    progress(stage="analysing", done=0, total=len(crawls), message="Extracting facts and reasoning")
    leads = []
    for i, cr in enumerate(crawls, 1):
        identity = cr.identity or {}
        if cr.reachable and DIRECTORY_TITLE_RE.search(f'{identity.get("name", "")} {identity.get("title", "")}'):
            excluded.append({"url": cr.official_website, "source": cr.candidate.source,
                             "reason": "directory, news or information site (detected from its title)"})
            continue
        analysis = analyze_company(kb, cr.candidate.key, [p.as_page_text() for p in cr.pages],
                                   company_name=(cr.identity or {}).get("name"))
        leads.append(build_lead(kb, cr, analysis, req.country))
        for error in cr.errors:
            warnings.append({"stage": "verifying", "company": cr.candidate.key, "message": error})
        progress(stage="analysing", done=i, total=len(crawls), message=f"Analysed {cr.candidate.key}")
    leads.sort(key=lambda l: (CLASS_ORDER.index(l["classification"]), -(l["score"] or {}).get("value", -1)))

    summary = {c: sum(l["classification"] == c for l in leads) for c in CLASS_ORDER}
    summary.update(examined=len(leads), excluded_before_analysis=len(excluded),
                   duplicates_removed=duplicates)
    return {
        "mode": req.mode,
        "recorded_at": recorded_at,
        "product": {"id": kb.id, "name": kb.name},
        "country": req.country,
        "queries": queries,
        "started_at": started,
        "finished_at": _now(),
        "summary": summary,
        "leads": leads,
        "excluded": excluded,
        "warnings": warnings,
    }


# ---------------------------------------------------------- lead schema ----


def _fact_view(kb: ProductKB, f) -> dict:
    names = {**{k: v.name for k, v in kb.materials.items()},
             **{k: v.name for k, v in kb.activities.items()},
             **{k: v.name for k, v in kb.applications.items()}}
    return {
        "id": f.id, "predicate": f.predicate, "object": f.object,
        "object_name": names.get(f.object, f.object), "polarity": f.polarity,
        "attrs": {k: v for k, v in f.attrs.items() if v not in (None, False)},
        "evidence": [{"url": e.url, "quote": e.quote, "page_type": e.page_type,
                      "retrieved_at": e.retrieved_at, "extractor": e.extractor} for e in f.evidence],
    }


def build_lead(kb: ProductKB, cr: CrawlResult, a: CompanyAnalysis, target_country: str | None) -> dict:
    inf, q = a.inference, a.qualification
    facts = [_fact_view(kb, f) for f in a.data.facts]
    positive = [f for f in facts if f["polarity"]]
    contacts = cr.contacts if cr.contacts is not None else extract_contacts(cr.pages)
    identity = cr.identity or {}
    country = identity.get("country")
    matches = None
    if target_country and country:
        matches = target_country.strip().casefold() in country.casefold() or country.casefold() in target_country.casefold()
    labels = [
        {"label": "Official website found", "ok": cr.reachable},
        {"label": "Business activity supported by source", "ok": bool(inf.evidence_items.get("activity"))},
        {"label": "Material usage supported by source", "ok": inf.usage == "supported"},
        {"label": "Public contact found", "ok": bool(contacts["emails"] or contacts["phones"])},
        {"label": "Purchasing evidence found", "ok": inf.purchasing == "direct"},
    ]
    retrieved = [p.retrieved_at for p in cr.pages]
    return {
        "company_name": identity.get("name") or cr.candidate.key,
        "company_name_source": identity.get("name_source") or "domain name",
        "company_key": cr.candidate.key,
        "official_website": cr.official_website,
        "found_via": {"source": cr.candidate.source, "url": cr.candidate.result_url,
                      "title": cr.candidate.title, "snippet": cr.candidate.snippet,
                      "note": "Search snippets are only used to find candidates, never as evidence."},
        "country": {"value": country, "source": identity.get("country_source"), "matches_target": matches},
        "classification": q.classification,
        "label": q.label,
        "reason_code": q.reason_code,
        "explanation": q.explanation,
        "layers": {"relevance": inf.relevance, "usage": inf.usage, "purchasing": inf.purchasing},
        "score": a.score,
        "trace": inf.to_trace(),
        "business_activities": sorted({f["object_name"] for f in positive if f["predicate"] == "performs"}),
        "materials_used": sorted({f["object_name"] for f in positive if f["predicate"] == "uses_material"}),
        "alternative_materials": sorted({f["object_name"] for f in positive if f["predicate"] == "uses_alternative"}),
        "facts": facts,
        "contacts": contacts,
        "verification": labels,
        "missing_information": inf.missing,
        "pages_checked": [{"url": p.url, "page_type": p.page_type, "retrieved_at": p.retrieved_at} for p in cr.pages],
        "retrieved_at": max(retrieved) if retrieved else None,
        "rejected_facts": a.rejected_facts,
        "errors": cr.errors,
    }


# ------------------------------------------------------- snapshot/replay ---


def _save_snapshot(path: Path, req: PipelineRequest, crawls: list[CrawlResult], excluded) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "product": req.product, "country": req.country, "recorded_at": _now(),
            "excluded": excluded,
            "companies": [{
                "candidate": asdict(cr.candidate),
                "official_website": cr.official_website,
                "identity": cr.identity,
                "errors": cr.errors,
                "robots_blocked": cr.robots_blocked,
                "contacts": extract_contacts(cr.pages),
                "pages": [{"url": p.url, "page_type": p.page_type, "text": p.text,
                           "retrieved_at": p.retrieved_at} for p in cr.pages],
            } for cr in crawls],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as error:
        logger.warning("Could not save snapshot %s: %s", path, error)


def _load_snapshot(path: Path):
    if not path.exists():
        raise FileNotFoundError("No saved snapshot for this product and country yet. "
                                "Run a live search once to create one.")
    data = json.loads(path.read_text(encoding="utf-8"))
    crawls = []
    for item in data["companies"]:
        cr = CrawlResult(Candidate(**item["candidate"]))
        cr.official_website = item["official_website"]
        cr.identity = item["identity"]
        cr.errors = item["errors"]
        cr.robots_blocked = item.get("robots_blocked", False)
        cr.contacts = item["contacts"]
        cr.pages = [FetchedPage(p["url"], p["page_type"], p["text"], "", p["retrieved_at"]) for p in item["pages"]]
        crawls.append(cr)
    return crawls, data.get("excluded", []), data["recorded_at"]
