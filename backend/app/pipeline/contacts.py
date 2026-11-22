"""Public contact extraction - every email/phone keeps the page URL it came from.

Stricter than the original finder.extract_contact_info():
* phone numbers only from tel: links or text right after a phone label
  (bare digit runs such as dates, IDs and prices are ignored; fax is ignored)
* image file names (logo@2x.png) and placeholder domains are not emails
"""

from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup

from ..finder import EMAIL_PATTERN

PHONE_LABEL_RE = re.compile(
    r"(?:tel|telephone|phone|ph|call(?: us)?|mobile|whatsapp)\s*[.:]?\s*(\+?\d[\d().\-\s]{5,}\d)",
    re.IGNORECASE,
)
PLACEHOLDER_DOMAINS = ("example.com", "example.org", "domain.com", "email.com", "yourdomain.com",
                       "sentry.io", "wixpress.com", "sentry-next.wixpress.com")
IMAGE_SUFFIX_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|bmp)$", re.I)


def _valid_email(email: str) -> bool:
    email = email.lower()
    domain = email.rsplit("@", 1)[-1]
    return not IMAGE_SUFFIX_RE.search(email) and not any(domain.endswith(d) for d in PLACEHOLDER_DOMAINS)


def _valid_phone(value: str) -> str | None:
    phone = re.sub(r"\s+", " ", value).strip(" .-")
    digits = sum(c.isdigit() for c in phone)
    return phone if 7 <= digits <= 15 else None


def extract_contacts(pages) -> dict[str, list[dict]]:
    """pages: iterable with .url and .html. Returns {"emails": [...], "phones": [...]}."""
    emails: dict[str, str] = {}
    phones: dict[str, str] = {}
    for page in pages:
        soup = BeautifulSoup(page.html, "html.parser")
        for link in soup.select("a[href]"):
            href = link.get("href", "").strip()
            if href.lower().startswith("mailto:"):
                for e in EMAIL_PATTERN.findall(unescape(href[7:].split("?", 1)[0])):
                    if _valid_email(e):
                        emails.setdefault(e.lower(), page.url)
            elif href.lower().startswith("tel:"):
                phone = _valid_phone(unescape(href[4:]))
                if phone:
                    phones.setdefault(phone, page.url)
        for el in soup(["script", "style", "noscript", "svg"]):
            el.decompose()
        text = unescape(soup.get_text(" ", strip=True))
        for e in EMAIL_PATTERN.findall(text):
            if _valid_email(e):
                emails.setdefault(e.lower(), page.url)
        for match in PHONE_LABEL_RE.finditer(text):
            before = text[max(0, match.start() - 6):match.start()].lower()
            if "fax" in before:
                continue
            phone = _valid_phone(match.group(1))
            if phone:
                phones.setdefault(phone, page.url)
    return {
        "emails": [{"value": v, "source_url": u} for v, u in sorted(emails.items())],
        "phones": [{"value": v, "source_url": u} for v, u in sorted(phones.items())],
    }
