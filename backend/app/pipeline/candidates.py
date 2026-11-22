"""Stage 3 - candidate collection: URL normalisation, de-duplication, blocklist."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

# Directories, marketplaces, social media, encyclopaedias and news sites are
# not company websites; their pages are never used as company evidence.
BLOCKED_DOMAINS = (
    "wikipedia.org", "wikimedia.org", "linkedin.com", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "youtube.com", "tiktok.com", "pinterest.com", "reddit.com",
    "quora.com", "medium.com", "amazon.com", "amazon.co.jp", "amazon.co.uk", "amazon.de",
    "ebay.com", "etsy.com", "alibaba.com", "aliexpress.com", "made-in-china.com",
    "indiamart.com", "globalsources.com", "tradeindia.com", "ec21.com", "ecplaza.net",
    "kompass.com", "europages.com", "europages.co.uk", "thomasnet.com", "yellowpages.com",
    "yelp.com", "tripadvisor.com", "bloomberg.com", "reuters.com", "bbc.co.uk", "bbc.com",
    "nytimes.com", "forbes.com", "dnb.com", "zoominfo.com", "crunchbase.com",
    "volza.com", "importgenius.com", "foursource.com", "listcompany.org", "exporthub.com",
    "fibre2fashion.com", "bizvibe.com", "exportersindia.com", "tradewheel.com", "panjiva.com", "tradekey.com", "go4worldbusiness.com",
)
BLOCKED_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip")


def company_key(url: str) -> str:
    """Normalised host used as the company identity ('https://www.X.com/a' -> 'x.com')."""
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    for prefix in ("www.", "www2.", "m."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    return host


def homepage(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme or 'https'}://{parts.hostname}/"


def blocked_reason(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return "not a web URL"
    key = company_key(url)
    if any(key == d or key.endswith("." + d) for d in BLOCKED_DOMAINS):
        return "directory, marketplace, social media or news site (not a company website)"
    if parts.path.lower().endswith(BLOCKED_EXTENSIONS):
        return "document file, not a company website"
    return None


@dataclass
class Candidate:
    key: str
    start_url: str  # homepage of the company site
    result_url: str  # the page the search engine / seed list pointed at
    title: str = ""
    snippet: str = ""  # display only - never used as evidence
    source: str = "search"  # search | seed
    queries: list[str] = field(default_factory=list)


@dataclass
class CandidateSet:
    candidates: list[Candidate] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    duplicates_removed: int = 0


def collect_candidates(hits, seed_urls=(), max_candidates: int = 12) -> CandidateSet:
    result = CandidateSet()
    by_key: dict[str, Candidate] = {}
    entries = [("seed", url, "", "", None) for url in seed_urls]
    entries += [("search", h.url, h.title, h.snippet, h.query) for h in hits]
    for source, url, title, snippet, query in entries:
        reason = blocked_reason(url)
        if reason:
            result.excluded.append({"url": url, "reason": reason, "source": source})
            continue
        key = company_key(url)
        if key in by_key:
            result.duplicates_removed += 1
            if query and query not in by_key[key].queries:
                by_key[key].queries.append(query)
            continue
        if len(by_key) >= max_candidates:
            result.excluded.append({"url": url, "reason": "candidate limit reached", "source": source})
            continue
        by_key[key] = Candidate(key, homepage(url), url, title, snippet, source, [query] if query else [])
    result.candidates = list(by_key.values())
    return result
