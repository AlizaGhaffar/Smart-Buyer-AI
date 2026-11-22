"""Offline fakes for the web: a fake search provider and a fake website server."""

from app.pipeline.website import FetchError, FetchResult


class FakeProvider:
    def __init__(self, results=None, fail=False):
        self.results = results or []
        self.fail = fail
        self.queries = []

    def search(self, query, max_results):
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("rate limited")
        return list(self.results)


class FakeFetcher:
    """sites: {url: html | (content_type, body) | Exception}"""

    def __init__(self, sites):
        self.sites = {k.rstrip("/"): v for k, v in sites.items()}
        self.requested = []

    def fetch(self, url, allowed_types=frozenset({"text/html"})):
        self.requested.append(url)
        value = self.sites.get(url.rstrip("/"))
        if value is None:
            raise FetchError("HTTP 404")
        if isinstance(value, Exception):
            raise FetchError(str(value))
        ctype, body = value if isinstance(value, tuple) else ("text/html", value)
        if ctype not in allowed_types:
            raise FetchError("unsupported content type")
        return FetchResult(url, ctype, body)


def html(body, title="", head=""):
    return f"<html><head><title>{title}</title>{head}</head><body>{body}</body></html>"
