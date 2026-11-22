"""Stage 4 - website verification.

Fetches the company homepage plus up to three relevant same-site pages
(About / Products / Contact / Sourcing / Manufacturing / Materials), respecting
robots.txt and a per-host request interval. Re-uses the SSRF protection from
finder.py (public hosts only, redirects re-validated, size and type limits).
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from ..extraction.nlp_extractor import PageText, page_is_english
from ..finder import MAX_PAGE_BYTES, UnsafeTargetError, _SafeRedirectHandler, _validate_public_url
from .candidates import Candidate, company_key

logger = logging.getLogger(__name__)

USER_AGENT = "SmartBuyerAI/1.0 (university research prototype; respects robots.txt)"
HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
REQUEST_TIMEOUT_SECONDS = 8
MIN_HOST_INTERVAL_SECONDS = 1.0
MAX_EXTRA_PAGES = 3

PAGE_TYPE_PATTERNS = (  # checked in priority order
    ("about", r"about|company|who-?we-?are|our-?story|profile|history"),
    ("products", r"product|collection|range|catalog|shop"),
    ("contact", r"contact|kontakt|reach-?us|enquir|inquir"),
    ("sourcing", r"sourc|supplier|procure|purchas|raw-?material"),
    ("manufacturing", r"manufactur|factory|production|mill|process|facilit"),
    ("materials", r"material|fibre|fiber|filling|wool|down|cashmere|quality"),
)
CCTLD_COUNTRIES = {
    "jp": "Japan", "de": "Germany", "uk": "United Kingdom", "it": "Italy", "fr": "France",
    "cn": "China", "in": "India", "pk": "Pakistan", "au": "Australia", "nz": "New Zealand",
    "mn": "Mongolia", "tr": "Turkey", "kr": "South Korea", "vn": "Vietnam", "pl": "Poland",
    "hu": "Hungary", "be": "Belgium", "nl": "Netherlands", "es": "Spain", "pt": "Portugal",
    "dk": "Denmark", "se": "Sweden", "ch": "Switzerland", "at": "Austria", "ca": "Canada",
    "ie": "Ireland", "lt": "Lithuania", "cz": "Czech Republic", "ro": "Romania", "tw": "Taiwan",
    "bd": "Bangladesh", "np": "Nepal", "ae": "United Arab Emirates", "za": "South Africa",
}


class FetchError(Exception):
    pass


@dataclass
class FetchResult:
    url: str  # final URL after redirects
    content_type: str
    body: str


class SafeHttpFetcher:
    """HTTP(S) fetcher: public hosts only, size/type/time limits, per-host pacing."""

    def __init__(self, min_interval: float = MIN_HOST_INTERVAL_SECONDS, timeout: int = REQUEST_TIMEOUT_SECONDS):
        self.min_interval = min_interval
        self.timeout = timeout
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def _pace(self, host: str) -> None:
        with self._lock:
            wait = self._last.get(host, 0.0) + self.min_interval - time.monotonic()
            self._last[host] = time.monotonic() + max(wait, 0.0)
        if wait > 0:
            time.sleep(wait)

    def fetch(self, url: str, allowed_types=HTML_TYPES) -> FetchResult:
        try:
            _validate_public_url(url)
            self._pace(urlsplit(url).hostname or "")
            request = Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,text/plain",
                "Accept-Encoding": "identity",
            })
            with build_opener(_SafeRedirectHandler()).open(request, timeout=self.timeout) as response:
                final = response.geturl()
                _validate_public_url(final)
                ctype = response.headers.get_content_type()
                if ctype not in allowed_types:
                    raise FetchError(f"unsupported content type {ctype}")
                # Large pages (heavy inline scripts) are cut at the size limit, not rejected.
                body = response.read(MAX_PAGE_BYTES)
                charset = response.headers.get_content_charset() or "utf-8"
                return FetchResult(final, ctype, body.decode(charset, errors="replace"))
        except FetchError:
            raise
        except HTTPError as error:
            raise FetchError(f"HTTP {error.code}") from error
        except (UnsafeTargetError, URLError, OSError, TimeoutError, ValueError) as error:
            text = str(error)
            if "CERTIFICATE_VERIFY_FAILED" in text:
                text = "SSL certificate could not be verified; page not fetched (security)"
            elif "timed out" in text.lower():
                text = "website did not respond in time"
            raise FetchError(text or type(error).__name__) from error


class RobotsPolicy:
    """Caches robots.txt per host. A missing robots.txt allows crawling."""

    def __init__(self, fetcher):
        self.fetcher = fetcher
        self._parsers: dict[str, RobotFileParser | None] = {}
        self._lock = threading.Lock()

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        with self._lock:
            cached = base in self._parsers
            parser = self._parsers.get(base)
        if not cached:
            parser = None
            try:
                result = self.fetcher.fetch(f"{base}/robots.txt", allowed_types={"text/plain"})
                parser = RobotFileParser()
                parser.parse(result.body.splitlines())
            except FetchError:
                parser = None  # no readable robots.txt -> no restrictions declared
            with self._lock:
                self._parsers[base] = parser
        return True if parser is None else parser.can_fetch(USER_AGENT, url)


# ----------------------------------------------------------------- parsing --

BLOCK_TAGS = ("p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th",
              "tr", "section", "article", "main", "aside", "dd", "dt", "blockquote", "figcaption", "table")


def html_to_text(html: str) -> str:
    """Visible main text with sentence boundaries at block elements."""
    soup = BeautifulSoup(html, "html.parser")
    for el in soup(["script", "style", "noscript", "svg", "nav", "footer", "form", "iframe", "template", "button"]):
        el.decompose()
    for el in soup.find_all(attrs={"class": re.compile(r"cookie|consent|newsletter|popup|modal", re.I)}):
        el.decompose()
    for el in soup.find_all(attrs={"id": re.compile(r"cookie|consent|newsletter|popup|modal", re.I)}):
        el.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for el in soup.find_all(BLOCK_TAGS):
        el.insert_before("\n")
        el.insert_after("\n")
    lines = [" ".join(line.split()) for line in soup.get_text(" ").splitlines()]
    sentences = []
    for line in filter(None, lines):
        line = re.sub(r"\s+([.,!?;:])", r"\1", line)
        sentences.append(line if line[-1] in ".!?:;" else line + ".")
    return " ".join(sentences)


def _json_ld_objects(soup: BeautifulSoup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                yield item
                stack.extend(v for v in item.values() if isinstance(v, (dict, list)))
            elif isinstance(item, list):
                stack.extend(item)


ORG_TYPES = {"Organization", "Corporation", "LocalBusiness", "Store", "Manufacturer", "OnlineStore"}


def company_identity(html: str, url: str) -> dict:
    """Company name and country with the source of each value."""
    soup = BeautifulSoup(html, "html.parser")
    name = name_source = country = country_source = None
    for obj in _json_ld_objects(soup):
        types = obj.get("@type")
        types = set(types) if isinstance(types, list) else {types}
        if types & ORG_TYPES:
            if not name and isinstance(obj.get("name"), str) and obj["name"].strip():
                name, name_source = obj["name"].strip(), "schema.org Organization"
            address = obj.get("address")
            if isinstance(address, dict) and not country:
                value = address.get("addressCountry")
                if isinstance(value, dict):
                    value = value.get("name")
                if isinstance(value, str) and value.strip():
                    country, country_source = value.strip(), "stated (schema.org address)"
    if not name:
        og = soup.find("meta", attrs={"property": "og:site_name"})
        if og and og.get("content", "").strip():
            name, name_source = og["content"].strip(), "og:site_name"
    if not name and soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(" ", strip=True)
        name = re.split(r"\s+[|–—-]\s+", title, maxsplit=1)[0].strip()
        name_source = "page title"
    if not name:
        name, name_source = company_key(url), "domain name"
    name = " ".join(html_lib.unescape(html_lib.unescape(name)).split())
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if not country:
        tld = (urlsplit(url).hostname or "").rsplit(".", 1)[-1]
        if tld in CCTLD_COUNTRIES:
            country, country_source = CCTLD_COUNTRIES[tld], "inferred from domain ending (not verified)"
    return {"name": name, "name_source": name_source, "title": title,
            "country": country, "country_source": country_source}


ARTICLE_PATH_RE = re.compile(r"/(?:news|blog|blogs|article|articles|press|media|insights|magazine|stories|post|posts)(?:/|$)")


def is_article(url: str) -> bool:
    return bool(ARTICLE_PATH_RE.search((urlsplit(url).path or "").lower()))


def classify_page(url: str, anchor: str = "") -> str | None:
    path = (urlsplit(url).path or "").lower()
    if is_article(url):
        return None
    haystack = f"{path} {anchor.lower()}"
    for page_type, pattern in PAGE_TYPE_PATTERNS:
        if re.search(pattern, haystack):
            return page_type
    return None


def discover_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Same-site links to relevant pages, one per page type, in priority order."""
    soup = BeautifulSoup(html, "html.parser")
    base_key = company_key(base_url)
    found: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip())
        parts = urlsplit(href)
        if parts.scheme not in {"http", "https"} or company_key(href) != base_key:
            continue
        clean = urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))
        if clean.rstrip("/") == base_url.rstrip("/"):
            continue
        page_type = classify_page(clean, a.get_text(" ", strip=True))
        if page_type and page_type not in found:
            found[page_type] = clean
    order = [t for t, _ in PAGE_TYPE_PATTERNS]
    return sorted(((t, u) for t, u in found.items()), key=lambda x: order.index(x[0]))


def find_english_version(html: str, base_url: str) -> str | None:
    """Same-site English version of a non-English page (hreflang, 'EN' link, /en/ path)."""
    soup = BeautifulSoup(html, "html.parser")
    base_key = company_key(base_url)
    candidates = []
    for link in soup.find_all("link", hreflang=True, href=True):
        if link["hreflang"].lower().startswith("en"):
            candidates.append(link["href"])
    for a in soup.find_all("a", href=True):
        label = a.get_text(" ", strip=True).lower()
        path = urlsplit(urljoin(base_url, a["href"])).path.lower()
        if label in {"en", "eng", "english"} or re.match(r"^/en(?:[/_-]|$)", path):
            candidates.append(a["href"])
    for href in candidates:
        url = urljoin(base_url, href.strip())
        if company_key(url) == base_key and url.rstrip("/") != base_url.rstrip("/"):
            return url
    return None


# ------------------------------------------------------------------ crawl ---


@dataclass
class FetchedPage:
    url: str
    page_type: str
    text: str
    html: str
    retrieved_at: str

    def as_page_text(self) -> PageText:
        return PageText(self.url, self.page_type, self.text)


@dataclass
class CrawlResult:
    candidate: Candidate
    pages: list[FetchedPage] = field(default_factory=list)
    official_website: str | None = None
    identity: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    robots_blocked: bool = False
    contacts: dict | None = None  # set when replaying a snapshot (no HTML kept)

    @property
    def reachable(self) -> bool:
        return bool(self.pages)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def crawl(candidate: Candidate, fetcher, robots: RobotsPolicy, max_extra_pages: int = MAX_EXTRA_PAGES) -> CrawlResult:
    result = CrawlResult(candidate)
    home = None
    parts = urlsplit(candidate.start_url)
    host = parts.hostname or ""
    other = host[4:] if host.startswith("www.") else f"www.{host}"
    variant = f"{parts.scheme}://{other}/"  # many sites answer on only one of www / non-www
    for url in dict.fromkeys([candidate.start_url, variant, candidate.result_url]):
        if not robots.allowed(url):
            result.robots_blocked = True
            result.errors.append(f"robots.txt disallows {url}")
            continue
        try:
            home = fetcher.fetch(url)
            break
        except FetchError as error:
            result.errors.append(f"{url}: {error}")
    if home is None:
        return result

    if company_key(home.url) != candidate.key:
        result.errors.append(f"{candidate.start_url} redirected to another site ({home.url}); not used.")
        return result

    first_type = "homepage" if urlsplit(home.url).path in {"", "/"} else classify_page(home.url) or "other_official"
    result.pages.append(FetchedPage(home.url, first_type, html_to_text(home.body), home.body, _now()))
    result.official_website = f"{urlsplit(home.url).scheme}://{urlsplit(home.url).netloc}"
    result.identity = company_identity(home.body, home.url)

    link_source = home
    if not page_is_english(result.pages[0].text):
        english_url = find_english_version(home.body, home.url)
        if english_url and robots.allowed(english_url):
            try:
                english = fetcher.fetch(english_url)
                if company_key(english.url) == candidate.key:
                    result.pages.append(FetchedPage(english.url, "homepage", html_to_text(english.body),
                                                    english.body, _now()))
                    link_source = english
            except FetchError as error:
                result.errors.append(f"{english_url}: {error}")

    targets = discover_links(link_source.body, link_source.url)
    result_type = classify_page(candidate.result_url)
    if (candidate.result_url.rstrip("/") != home.url.rstrip("/")
            and company_key(candidate.result_url) == candidate.key
            and not is_article(candidate.result_url)):
        targets.insert(0, (result_type or "other_official", candidate.result_url))
    seen = {p.url.rstrip("/") for p in result.pages}
    limit = len(result.pages) + max_extra_pages
    for page_type, url in targets:
        if len(result.pages) >= limit:
            break
        if url.rstrip("/") in seen:
            continue
        seen.add(url.rstrip("/"))
        if not robots.allowed(url):
            result.errors.append(f"robots.txt disallows {url}")
            continue
        try:
            page = fetcher.fetch(url)
        except FetchError as error:
            result.errors.append(f"{url}: {error}")
            continue
        if company_key(page.url) != candidate.key:
            continue
        result.pages.append(FetchedPage(page.url, page_type, html_to_text(page.body), page.body, _now()))
    return result
