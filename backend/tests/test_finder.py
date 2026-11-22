import unittest
from unittest.mock import patch

from duckduckgo_search.exceptions import DuckDuckGoSearchException

from app.finder import (
    SearchError,
    UnsafeTargetError,
    build_queries,
    extract_contact_info,
    find_leads,
    score_lead,
)


class FinderTests(unittest.TestCase):
    def test_build_queries_combines_products_country_and_removes_duplicates(self):
        queries = build_queries(
            ["Raw Sheep Wool", "Cashmere"],
            [" raw sheep wool ", "Duck Down"],
            "Japan",
        )

        self.assertEqual(
            queries,
            [
                (
                    "Raw Sheep Wool",
                    '"Raw Sheep Wool" (importer OR wholesaler OR distributor OR buyer) in Japan',
                ),
                (
                    "Cashmere",
                    '"Cashmere" (importer OR wholesaler OR distributor OR buyer) in Japan',
                ),
                (
                    "Duck Down",
                    '"Duck Down" (importer OR wholesaler OR distributor OR buyer) in Japan',
                ),
            ],
        )

    def test_score_awards_specified_points_for_buyer_and_product_matches(self):
        self.assertEqual(
            score_lead("cashmere", "Cashmere importer and wholesaler"),
            (50, ["importer", "wholesaler", "cashmere"]),
        )
        self.assertEqual(score_lead("cashmere", "Cashmere textiles"), (25, ["cashmere"]))
        self.assertEqual(score_lead("cashmere", "Wool importer"), (25, ["importer"]))

    def test_extract_contact_info_finds_public_contacts_and_ignores_scripts(self):
        html = """
        <html><body>
          <a href="mailto:Sales@Example.com?subject=Hello">Email us</a>
          <a href="tel:+1 (212) 555-0199">Call us</a>
          <p>Contact: buyers@example.org</p>
          <script>hidden@example.net</script>
        </body></html>
        """

        self.assertEqual(
            extract_contact_info(html),
            {
                "emails": ["buyers@example.org", "sales@example.com"],
                "phones": ["+1 (212) 555-0199"],
            },
        )

    @patch("app.finder._fetch_page")
    @patch("app.finder.DDGS")
    def test_find_leads_returns_scored_contact_record(self, ddgs, fetch_page):
        ddgs.return_value.text.return_value = [
            {
                "href": "https://example.com/contact",
                "title": "Example Wool Importers",
                "body": "Cashmere and raw wool wholesaler",
            }
        ]
        fetch_page.return_value = {
            "url": "https://example.com/contact",
            "title": "Example Wool Importers",
            "text": "We import cashmere.",
            "html": '<a href="mailto:info@example.com">Email</a>',
        }

        leads, warnings = find_leads(["cashmere"], [], "Japan", 3)

        self.assertEqual(warnings, [])
        self.assertEqual(
            leads,
            [
                {
                    "company_name": "Example Wool Importers",
                    "website": "https://example.com",
                    "relevance_score": 50,
                    "matched_keywords": ["cashmere", "importers", "wholesaler"],
                    "contact_info": {
                        "emails": ["info@example.com"],
                        "phones": [],
                    },
                    "source_url": "https://example.com/contact",
                }
            ],
        )

    @patch("app.finder.socket.getaddrinfo")
    def test_private_network_urls_are_rejected(self, getaddrinfo):
        getaddrinfo.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 443))
        ]

        from app.finder import _validate_public_url

        with self.assertRaises(UnsafeTargetError):
            _validate_public_url("http://localhost/")

    @patch("app.finder.DDGS")
    def test_provider_failures_are_reported_when_all_queries_fail(self, ddgs):
        ddgs.return_value.text.side_effect = DuckDuckGoSearchException("rate limited")

        with self.assertRaises(SearchError):
            find_leads(["cashmere"], [], None, 3)


if __name__ == "__main__":
    unittest.main()
