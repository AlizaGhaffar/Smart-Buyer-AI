"""Stage 2 - product-specific web search.

Queries describe buyer *companies* (from the product KB's search_queries),
not just the product name. The provider is pluggable so tests run offline.
Search results are only candidates; a snippet is never used as evidence.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from ..knowledge.schema import ProductKB

logger = logging.getLogger(__name__)

MAX_QUERIES = 5
RESULTS_PER_QUERY = 8
CACHE_TTL_SECONDS = 3600
RETRY_DELAYS = (2.0, 5.0)  # backoff after a rate-limit / timeout
PACING_SECONDS = 1.0  # pause between queries


class SearchError(RuntimeError):
    """Raised when every search query failed."""


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str
    query: str


@dataclass
class SearchOutcome:
    hits: list[SearchHit] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    successful_queries: int = 0


def build_queries(kb: ProductKB, country: str | None, limit: int = MAX_QUERIES) -> list[str]:
    location = f" {country}" if country else ""
    return [f"{q}{location}" for q in kb.search_queries[:limit]]


class DDGSProvider:
    """Wraps the `ddgs` metasearch library (successor of duckduckgo_search)."""

    def __init__(self, timeout: int = 10, sleep=time.sleep):
        self.timeout = timeout
        self.sleep = sleep

    def search(self, query: str, max_results: int) -> list[dict]:
        from ddgs import DDGS
        from ddgs.exceptions import DDGSException

        last_error: Exception | None = None
        for attempt, delay in enumerate((0.0, *RETRY_DELAYS)):
            if delay:
                logger.info("Retrying %r in %.0fs (attempt %d)", query, delay, attempt + 1)
                self.sleep(delay)
            try:
                return list(DDGS(timeout=self.timeout).text(query, max_results=max_results))
            except DDGSException as error:  # rate limit, timeout, or a throttled empty answer
                last_error = error
        raise last_error  # type: ignore[misc]


class _Cache:
    def __init__(self):
        self._data: dict[tuple, tuple[float, list[dict]]] = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if item and time.monotonic() - item[0] < CACHE_TTL_SECONDS:
                return item[1]
            return None

    def put(self, key, value):
        with self._lock:
            self._data[key] = (time.monotonic(), value)


_cache = _Cache()


def search_candidates(kb: ProductKB, country: str | None, provider=None, *,
                      results_per_query: int = RESULTS_PER_QUERY,
                      pacing: float = PACING_SECONDS, sleep=time.sleep,
                      cache: _Cache | None = _cache) -> SearchOutcome:
    provider = provider or DDGSProvider(sleep=sleep)
    outcome = SearchOutcome(queries=build_queries(kb, country))
    for i, query in enumerate(outcome.queries):
        key = (query, results_per_query)
        results = cache.get(key) if cache else None
        if results is None:
            if i and pacing:
                sleep(pacing)
            try:
                results = provider.search(query, results_per_query)
            except Exception as error:  # provider errors vary; never fail silently
                logger.warning("Search failed for %r: %s", query, error)
                outcome.warnings.append({"stage": "search", "query": query,
                                         "message": f"Search provider failed for this query ({type(error).__name__})."})
                continue
            if cache:
                cache.put(key, results)
        outcome.successful_queries += 1
        for r in results:
            url = r.get("href") or r.get("url")
            if url:
                outcome.hits.append(SearchHit(r.get("title", "") or "", url, r.get("body", "") or "", query))
    return outcome
