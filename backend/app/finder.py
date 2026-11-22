import ipaddress
import logging
import re
import socket
from collections.abc import Iterable
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException

logger = logging.getLogger(__name__)

BUYER_TERMS = (
    "importer",
    "importers",
    "wholesaler",
    "wholesalers",
    "distributor",
    "distributors",
    "buyer",
    "buyers",
    "procurement",
    "purchasing",
    "bulk supplier",
)
EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d().\-\s]{5,}\d)(?!\w)")
MAX_PAGE_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 8


class SearchError(RuntimeError):
    """Raised when every product query fails before returning search results."""


class UnsafeTargetError(ValueError):
    """Raised when a search result points to a non-public or unsupported URL."""


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        target = urljoin(request.full_url, new_url)
        _validate_public_url(target)
        return super().redirect_request(
            request, response, code, message, headers, target
        )


def build_queries(
    products: Iterable[str], custom_products: Iterable[str], country: str | None
) -> list[tuple[str, str]]:
    """Return distinct (product, search query) pairs in caller-provided order."""
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw_product in [*products, *custom_products]:
        product = " ".join(raw_product.split())
        key = product.casefold()
        if not product or key in seen:
            continue
        seen.add(key)
        location = f" in {country}" if country else ""
        pairs.append(
            (
                product,
                f'"{product}" (importer OR wholesaler OR distributor OR buyer){location}',
            )
        )
    return pairs


def extract_contact_info(html: str) -> dict[str, list[str]]:
    parsed = BeautifulSoup(html, "html.parser")
    emails: set[str] = set()
    phones: set[str] = set()

    for link in parsed.select("a[href]"):
        href = link.get("href", "").strip()
        if href.lower().startswith("mailto:"):
            emails.update(EMAIL_PATTERN.findall(unescape(href[7:].split("?", 1)[0])))
        elif href.lower().startswith("tel:"):
            phones.update(_validated_phones([href[4:]]))

    for element in parsed(["script", "style", "noscript", "svg"]):
        element.decompose()
    visible_text = parsed.get_text(" ", strip=True)
    emails.update(EMAIL_PATTERN.findall(unescape(visible_text)))
    phones.update(_validated_phones(PHONE_PATTERN.findall(visible_text)))
    return {
        "emails": sorted(email.lower() for email in emails),
        "phones": sorted(phones),
    }


def score_lead(product: str, text: str) -> tuple[int, list[str]]:
    normalized = _normalize_text(text)
    matched_buyers = [
        term for term in BUYER_TERMS if _contains_phrase(normalized, term)
    ]
    matched = matched_buyers.copy()
    product_matched = _contains_phrase(normalized, _normalize_text(product))
    if product_matched:
        matched.append(product)
    return (25 * bool(matched_buyers) + 25 * product_matched, matched)


def find_leads(
    products: list[str],
    custom_products: list[str],
    country: str | None,
    max_results_per_query: int,
) -> tuple[list[dict], list[dict[str, str]]]:
    queries = build_queries(products, custom_products, country)
    leads_by_site: dict[str, dict] = {}
    warnings: list[dict[str, str]] = []
    successful_queries = 0

    for product, query in queries:
        try:
            # Materialize inside the try block because the iterator can raise
            # network errors after DDGS.text() returns.
            results = list(
                DDGS(timeout=REQUEST_TIMEOUT_SECONDS).text(
                    query, max_results=max_results_per_query
                )
            )
            successful_queries += 1
        except (
            DuckDuckGoSearchException,
            OSError,
            RuntimeError,
            TimeoutError,
            ValueError,
        ) as error:
            logger.warning("DuckDuckGo search failed for query %r: %s", query, error)
            warnings.append(
                {"query": query, "message": "Search provider failed for this query."}
            )
            continue

        for result in results:
            result_url = result.get("href") or result.get("url")
            if not result_url:
                continue
            try:
                _validate_public_url(result_url)
            except (TypeError, ValueError) as error:
                logger.info("Skipped unsafe search result %r: %s", result_url, error)
                warnings.append(
                    {"query": query, "message": "Skipped an unsafe search result URL."}
                )
                continue
            try:
                page = _fetch_page(result_url)
            except (HTTPError, OSError, TimeoutError, URLError, ValueError) as error:
                logger.info("Could not fetch search result %r: %s", result_url, error)
                warnings.append(
                    {
                        "query": query,
                        "message": "Could not fetch a search result page.",
                    }
                )
                page = {"title": "", "text": "", "html": "", "url": result_url}

            title = page["title"] or result.get("title", "")
            snippet = result.get("body") or result.get("snippet") or ""
            score, matched_keywords = score_lead(
                product, f"{title} {snippet} {page['text']}"
            )
            if score == 0:
                continue

            parts = urlsplit(page["url"])
            host = (parts.hostname or "").lower()
            if not host:
                continue
            website = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
            lead = {
                "company_name": _company_name(title, host),
                "website": website.rstrip("/"),
                "relevance_score": score,
                "matched_keywords": sorted(matched_keywords, key=str.casefold),
                "contact_info": extract_contact_info(page["html"]),
                "source_url": page["url"],
            }
            _merge_lead(leads_by_site, host, lead)

    if successful_queries == 0:
        raise SearchError("DuckDuckGo search failed for all requested products.")

    leads = sorted(
        leads_by_site.values(),
        key=lambda lead: (-lead["relevance_score"], lead["company_name"].casefold()),
    )
    return leads, warnings


def _fetch_page(url: str) -> dict[str, str]:
    _validate_public_url(url)
    opener = build_opener(_SafeRedirectHandler())
    request = Request(
        url,
        headers={
            "User-Agent": "MamuExportLeadFinder/1.0 (+public contact discovery)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Encoding": "identity",
        },
    )
    with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        _validate_public_url(final_url)
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("Search result is not an HTML page.")
        body = response.read(MAX_PAGE_BYTES + 1)
        if len(body) > MAX_PAGE_BYTES:
            raise ValueError("Search result exceeds the maximum page size.")
        html = body.decode(
            response.headers.get_content_charset() or "utf-8", errors="replace"
        )

    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return {
        "url": final_url,
        "title": title,
        "text": soup.get_text(" ", strip=True),
        "html": html,
    }


def _validate_public_url(url: str) -> None:
    parts = urlsplit(url)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise UnsafeTargetError("Only public HTTP(S) URLs are supported.")
    if parts.port not in (None, 80, 443):
        raise UnsafeTargetError("Non-standard URL ports are not supported.")

    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(
                parts.hostname,
                parts.port or (443 if parts.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
    except (OSError, ValueError) as error:
        raise UnsafeTargetError("URL host could not be resolved.") from error
    if not addresses or any(not address.is_global for address in addresses):
        raise UnsafeTargetError("Only publicly routable hosts can be fetched.")


def _validated_phones(values: Iterable[str]) -> set[str]:
    phones = set()
    for value in values:
        phone = re.sub(r"\s+", " ", value).strip()
        digits = sum(character.isdigit() for character in phone)
        if 7 <= digits <= 15:
            phones.add(phone)
    return phones


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def _company_name(title: str, host: str) -> str:
    cleaned = re.split(r"\s+[|–—-]\s+", title.strip(), maxsplit=1)[0].strip()
    return cleaned or host.removeprefix("www.")


def _merge_lead(leads_by_site: dict[str, dict], host: str, lead: dict) -> None:
    existing = leads_by_site.get(host)
    if existing is None:
        leads_by_site[host] = lead
        return
    if lead["relevance_score"] > existing["relevance_score"]:
        existing["relevance_score"] = lead["relevance_score"]
        existing["company_name"] = lead["company_name"]
        existing["source_url"] = lead["source_url"]
    existing["matched_keywords"] = sorted(
        set(existing["matched_keywords"]) | set(lead["matched_keywords"])
    )
    for contact_type in ("emails", "phones"):
        existing["contact_info"][contact_type] = sorted(
            set(existing["contact_info"][contact_type])
            | set(lead["contact_info"][contact_type])
        )
