import json

import pytest

from app.knowledge.products import get_kb
from app.pipeline.candidates import Candidate, blocked_reason, collect_candidates, company_key
from app.pipeline.contacts import extract_contacts
from app.pipeline.runner import PipelineRequest, run_pipeline
from app.pipeline.search_service import DDGSProvider, SearchError, SearchHit, _Cache, build_queries, search_candidates
from app.pipeline.website import (
    FetchedPage,
    RobotsPolicy,
    company_identity,
    crawl,
    discover_links,
    html_to_text,
)
from tests.fakes import FakeFetcher, FakeProvider, html

DD = get_kb("duck_down")

DUVET_HOME = html(
    '<nav>Home | Shop | Cart</nav>'
    '<p>Founded in 1994, Northwind Bedding manufactures duvets and pillows in our own factory in Poland.</p>'
    '<p>We supply hotels and distributors across Europe with high quality bedding products every season.</p>'
    '<a href="/about-us">About us</a> <a href="/products/duvets">Our duvets</a>'
    '<a href="/contact">Contact</a> <a href="https://facebook.com/northwind">Facebook</a>'
    '<footer>Online shop - free delivery</footer>',
    title="Northwind Bedding | Duvets",
    head='<script type="application/ld+json">{"@type":"Organization","name":"Northwind Bedding Sp. z o.o.",'
         '"address":{"addressCountry":"Poland"}}</script>',
)
DUVET_PRODUCTS = html(
    "<h1>Premium duvet</h1><p>Our premium duvet is filled with <b>90% white duck down</b> and 10% feather. "
    "Each duvet is box-stitched to keep the filling evenly spread across the whole bed.</p>")
DUVET_CONTACT = html(
    '<p>Write to <a href="mailto:Sales@northwind.test">sales</a>. Tel: +48 58 123 4567. Fax: +48 58 765 4321.</p>'
    "<p>Order 2024-11-05 ref 123456789. Logo: logo@2x.png</p>")
RESTAURANT = html(
    "<p>Welcome to Osaka Duck House. Our restaurant serves roast duck and duck ramen every day.</p>"
    "<p>We are open daily and the kitchen shuts down at 10pm. For wholesale inquiries contact our purchasing team.</p>")

SITES = {
    "https://northwind.test/robots.txt": ("text/plain", "User-agent: *\nDisallow: /private\n"),
    "https://northwind.test/": DUVET_HOME,
    "https://northwind.test/about-us": html("<p>We manufacture duvets at our factory near Gdansk since 1994.</p>"),
    "https://northwind.test/products/duvets": DUVET_PRODUCTS,
    "https://northwind.test/contact": DUVET_CONTACT,
    "https://osaka-duck.test/": RESTAURANT,
}
HITS = [
    {"title": "Northwind Bedding", "href": "https://www.northwind.test/products/duvets", "body": "duvets"},
    {"title": "Northwind again", "href": "https://northwind.test/", "body": "dup"},
    {"title": "Osaka Duck House", "href": "https://osaka-duck.test/", "body": "purchasing team"},
    {"title": "Top duck down suppliers", "href": "https://www.alibaba.com/duck-down", "body": "directory"},
    {"title": "Brochure", "href": "https://other.test/catalogue.pdf", "body": "pdf"},
    {"title": "Dead site", "href": "https://dead.test/", "body": "duck down importer"},
]


# ------------------------------------------------------------ candidates ---


def test_company_key_normalises_hosts():
    assert company_key("https://WWW.Example.com/about?x=1") == "example.com"
    assert company_key("http://example.com") == company_key("https://www.example.com/")


def test_blocklist_rejects_directories_social_and_documents():
    assert blocked_reason("https://www.alibaba.com/x")
    assert blocked_reason("https://uk.linkedin.com/company/x")
    assert blocked_reason("https://example.com/file.PDF")
    assert blocked_reason("ftp://example.com/")
    assert blocked_reason("https://northwind.test/") is None


def test_collect_candidates_dedups_and_limits():
    hits = [SearchHit(h["title"], h["href"], h["body"], "q") for h in HITS]
    cset = collect_candidates(hits, seed_urls=["https://seed.test/about"], max_candidates=3)
    keys = [c.key for c in cset.candidates]
    assert keys == ["seed.test", "northwind.test", "osaka-duck.test"]
    assert cset.duplicates_removed == 1
    reasons = {e["url"]: e["reason"] for e in cset.excluded}
    assert "alibaba" in next(u for u in reasons if "alibaba" in u)
    assert reasons["https://dead.test/"] == "candidate limit reached"
    assert cset.candidates[0].source == "seed"


# --------------------------------------------------------------- search ----


def test_queries_are_product_specific_and_include_country():
    queries = build_queries(DD, "Japan")
    assert all(q.endswith(" Japan") for q in queries)
    assert any("duvet manufacturer" in q for q in queries)
    assert build_queries(get_kb("cashmere"), None) != build_queries(DD, None)


def test_search_failure_is_reported_not_silent():
    outcome = search_candidates(DD, None, FakeProvider(fail=True), pacing=0, cache=None)
    assert outcome.successful_queries == 0 and len(outcome.warnings) == len(outcome.queries)


def test_search_results_are_cached():
    cache, provider = _Cache(), FakeProvider(HITS[:1])
    search_candidates(DD, "Japan", provider, pacing=0, cache=cache)
    first = len(provider.queries)
    search_candidates(DD, "Japan", provider, pacing=0, cache=cache)
    assert len(provider.queries) == first


def test_ddgs_provider_backs_off_on_rate_limit(monkeypatch):
    from ddgs.exceptions import RatelimitException

    calls, sleeps = [], []

    class FlakyDDGS:
        def __init__(self, timeout):
            pass

        def text(self, query, max_results):
            calls.append(query)
            if len(calls) < 3:
                raise RatelimitException("202 Ratelimit")
            return [{"title": "t", "href": "https://a.test/", "body": "b"}]

    monkeypatch.setattr("ddgs.DDGS", FlakyDDGS)
    results = DDGSProvider(sleep=sleeps.append).search("q", 5)
    assert len(calls) == 3 and sleeps == [2.0, 5.0] and results[0]["href"] == "https://a.test/"


# --------------------------------------------------------------- website ---


def test_html_to_text_keeps_sentences_and_drops_navigation():
    text = html_to_text(DUVET_HOME + DUVET_PRODUCTS)
    assert "Home | Shop" not in text and "free delivery" not in text
    assert "Our premium duvet is filled with 90% white duck down and 10% feather." in text
    assert "Premium duvet." in text  # heading becomes its own sentence


def test_company_identity_prefers_schema_org_and_marks_inferred_country():
    ident = company_identity(DUVET_HOME, "https://northwind.test/")
    assert ident["name"] == "Northwind Bedding Sp. z o.o." and ident["name_source"] == "schema.org Organization"
    assert ident["country"] == "Poland" and ident["country_source"].startswith("stated")
    jp = company_identity(html("x", title="Kyoto Wool | Home"), "https://kyoto-wool.jp/")
    assert jp["name"] == "Kyoto Wool" and jp["country"] == "Japan" and "not verified" in jp["country_source"]


def test_discover_links_only_same_site_relevant_pages():
    links = dict(discover_links(DUVET_HOME, "https://northwind.test/"))
    assert links == {
        "about": "https://northwind.test/about-us",
        "products": "https://northwind.test/products/duvets",
        "contact": "https://northwind.test/contact",
    }


def test_robots_txt_is_respected():
    fetcher = FakeFetcher({"https://shy.test/robots.txt": ("text/plain", "User-agent: *\nDisallow: /\n"),
                           "https://shy.test/": DUVET_HOME})
    result = crawl(Candidate("shy.test", "https://shy.test/", "https://shy.test/"), fetcher, RobotsPolicy(fetcher))
    assert result.robots_blocked and not result.reachable
    assert "https://shy.test/" not in fetcher.requested


def test_unreachable_site_gives_empty_crawl_with_error():
    fetcher = FakeFetcher({})
    result = crawl(Candidate("dead.test", "https://dead.test/", "https://dead.test/"), fetcher, RobotsPolicy(fetcher))
    assert not result.reachable and result.errors


def test_crawl_fetches_homepage_plus_relevant_pages():
    fetcher = FakeFetcher(SITES)
    c = Candidate("northwind.test", "https://northwind.test/", "https://www.northwind.test/products/duvets")
    result = crawl(c, fetcher, RobotsPolicy(fetcher))
    types = [p.page_type for p in result.pages]
    assert types[0] == "homepage" and set(types[1:]) == {"products", "about", "contact"}
    assert len(result.pages) == 4
    assert result.official_website == "https://northwind.test"


# -------------------------------------------------------------- contacts ---


def test_contacts_keep_source_and_ignore_fax_dates_and_images():
    pages = [FetchedPage("https://northwind.test/contact", "contact", "", DUVET_CONTACT, "now")]
    contacts = extract_contacts(pages)
    assert contacts["emails"] == [{"value": "sales@northwind.test", "source_url": "https://northwind.test/contact"}]
    assert [p["value"] for p in contacts["phones"]] == ["+48 58 123 4567"]


def test_no_contacts_gives_empty_lists():
    assert extract_contacts([FetchedPage("u", "about", "", "<p>No contact here.</p>", "now")]) == {"emails": [], "phones": []}


# -------------------------------------------------------------- pipeline ---


@pytest.fixture
def live_result(tmp_path):
    return run_pipeline(PipelineRequest("duck_down", "Japan"), search_provider=FakeProvider(HITS),
                        fetcher=FakeFetcher(SITES), search_sleep=lambda s: None, snapshot_dir=tmp_path), tmp_path


def test_pipeline_end_to_end(live_result):
    result, _ = live_result
    leads = {l["company_key"]: l for l in result["leads"]}
    assert set(leads) == {"northwind.test", "osaka-duck.test", "dead.test"}

    northwind = leads["northwind.test"]
    assert northwind["classification"] == "strong_potential_buyer"
    assert northwind["company_name"] == "Northwind Bedding Sp. z o.o."
    assert northwind["country"] == {"value": "Poland", "source": "stated (schema.org address)", "matches_target": False}
    duck = next(f for f in northwind["facts"] if f["object"] == "duck_down")
    assert duck["evidence"][0]["url"] == "https://northwind.test/products/duvets"
    assert "white duck down" in duck["evidence"][0]["quote"]
    assert northwind["contacts"]["emails"][0]["source_url"] == "https://northwind.test/contact"
    assert {v["label"]: v["ok"] for v in northwind["verification"]}["Purchasing evidence found"] is False

    assert leads["osaka-duck.test"]["classification"] == "not_relevant"
    assert leads["osaka-duck.test"]["score"] is None
    assert leads["dead.test"]["classification"] == "insufficient_evidence"

    # the fake provider returns the same 6 hits for each of the 5 queries:
    # northwind 2x5-1, osaka 5-1, dead 5-1 duplicates (alibaba/pdf are excluded, not duplicates)
    assert result["summary"]["duplicates_removed"] == 9 + 4 + 4
    assert any("alibaba" in e["url"] for e in result["excluded"])
    assert result["leads"][0]["company_key"] == "northwind.test"  # best class first


def test_replay_reproduces_live_result_without_network(live_result):
    result, snapshots = live_result
    replay = run_pipeline(PipelineRequest("duck_down", "Japan", mode="replay"),
                          fetcher=FakeFetcher({}), snapshot_dir=snapshots)
    assert replay["mode"] == "replay" and replay["recorded_at"]
    assert [(l["company_key"], l["classification"]) for l in replay["leads"]] == \
           [(l["company_key"], l["classification"]) for l in result["leads"]]
    northwind = next(l for l in replay["leads"] if l["company_key"] == "northwind.test")
    assert northwind["contacts"]["emails"]
    saved = json.loads(next(snapshots.iterdir()).read_text(encoding="utf-8"))
    assert saved["product"] == "duck_down" and saved["companies"]


def test_replay_without_snapshot_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="No saved snapshot"):
        run_pipeline(PipelineRequest("cashmere", "Peru", mode="replay"), snapshot_dir=tmp_path)


def test_all_search_queries_failing_raises(tmp_path):
    with pytest.raises(SearchError):
        run_pipeline(PipelineRequest("duck_down"), search_provider=FakeProvider(fail=True),
                     fetcher=FakeFetcher({}), search_sleep=lambda s: None, snapshot_dir=tmp_path)


def test_search_failure_falls_back_to_seed_urls(tmp_path):
    result = run_pipeline(PipelineRequest("duck_down", seed_urls=["https://northwind.test/"]),
                          search_provider=FakeProvider(fail=True), fetcher=FakeFetcher(SITES),
                          search_sleep=lambda s: None, snapshot_dir=tmp_path)
    assert [l["company_key"] for l in result["leads"]] == ["northwind.test"]
    assert any("seed URLs only" in w["message"] for w in result["warnings"])


def test_seed_mode_does_not_search(tmp_path):
    provider = FakeProvider(HITS)
    run_pipeline(PipelineRequest("duck_down", mode="seed", seed_urls=["https://northwind.test/"]),
                 search_provider=provider, fetcher=FakeFetcher(SITES), snapshot_dir=tmp_path)
    assert provider.queries == []


# ------------------------------------------- fixes from the live smoke run --


def test_mostly_japanese_site_is_insufficient_not_unrelated(tmp_path):
    japanese = "京都の寝具専門店です。高級羽毛ふとんとオーダーマットレスを製造しています。" * 20
    sites = {
        "https://iwata.test/": html(f"<p>{japanese}</p><a href='/about-us'>About us</a>"),
        "https://iwata.test/about-us": html("<p>Made in Japan. Luxury bedding for hotels and homes, made by "
                                            "artisans with care and tradition since 1830. Visit our showrooms "
                                            "in Kyoto and Tokyo to experience our quality for yourself.</p>"),
    }
    result = run_pipeline(PipelineRequest("duck_down", mode="seed", seed_urls=["https://iwata.test/"]),
                          fetcher=FakeFetcher(sites), snapshot_dir=tmp_path)
    lead = result["leads"][0]
    assert lead["classification"] == "insufficient_evidence"
    assert "MOSTLY_NON_ENGLISH" in lead["trace"]["insufficiency_reasons"]


def test_directory_detected_from_title_is_excluded(tmp_path):
    sites = {"https://fibres-hub.test/": html("<p>Find duck down manufacturers in Japan and suppliers worldwide "
                                              "on our platform for sourcing professionals.</p>",
                                              title="Manufacturers Directory | Fibres Hub")}
    result = run_pipeline(PipelineRequest("duck_down", mode="seed", seed_urls=["https://fibres-hub.test/"]),
                          fetcher=FakeFetcher(sites), snapshot_dir=tmp_path)
    assert result["leads"] == []
    assert "directory" in result["excluded"][-1]["reason"]


def test_html_entities_in_company_name_are_decoded():
    head = '<meta property="og:site_name" content="Beaumont &amp;amp; Brown">'
    assert company_identity(html("x", head=head), "https://bb.test/")["name"] == "Beaumont & Brown"


def test_non_english_homepage_switches_to_english_version():
    italian = ("Il nostro lanificio produce filati di cashmere di alta qualità dal 1950 per i marchi della moda "
               "italiana e internazionale, con passione e tradizione nel distretto di Biella. ") * 3
    sites = {
        "https://lanificio.test/": html(f"<p>{italian}</p><a href='/en/'>EN</a><a href='/azienda'>Chi siamo</a>"),
        "https://lanificio.test/en/": html("<p>We spin cashmere yarn at our mill in Biella from dehaired cashmere "
                                           "fibre.</p><a href='/en/about-us'>About us</a>"),
        "https://lanificio.test/en/about-us": html("<p>We purchase dehaired cashmere fibre from Inner Mongolia "
                                                   "every season and test every lot before spinning.</p>"),
    }
    fetcher = FakeFetcher(sites)
    result = crawl(Candidate("lanificio.test", "https://lanificio.test/", "https://lanificio.test/"),
                   fetcher, RobotsPolicy(fetcher))
    assert [p.url for p in result.pages] == [
        "https://lanificio.test/", "https://lanificio.test/en/", "https://lanificio.test/en/about-us"]


def test_company_name_is_not_material_evidence():
    from app.extraction.nlp_extractor import NLPExtractor, PageText
    from app.knowledge.products import get_kb as kb_for

    text = ("Cashmere Cafe is a small coffee shop in Kobe serving coffee and cakes. "
            "About us | Cashmere Cafe. We roast our beans every morning for our guests.")
    data = NLPExtractor(kb_for("cashmere")).extract("cafe.test", [PageText("https://cafe.test/", "homepage", text)],
                                                    company_name="Cashmere Cafe")
    assert data.facts == []


def test_weaving_yarn_is_not_spinning():
    from app.extraction.nlp_extractor import NLPExtractor, PageText
    from app.knowledge.products import get_kb as kb_for

    text = ("Our real strength is weaving yarn into fine cloth for fashion houses around the world, "
            "in our family weaving mill in Prato.")
    data = NLPExtractor(kb_for("cashmere")).extract("a.test", [PageText("https://a.test/", "about", text)])
    performed = {f.object for f in data.facts if f.predicate == "performs"}
    assert "cashmere_spinning" not in performed and "woven_fabric_manufacturing" in performed


def test_news_and_blog_pages_are_not_company_evidence():
    from app.pipeline.website import is_article
    assert is_article("https://mill.test/news/cotton-season-opens")
    assert is_article("https://mill.test/blog/how-wool-scouring-works/")
    assert not is_article("https://mill.test/about-us")
    links = dict(discover_links(html("<a href='/blog/scouring'>About scouring</a><a href='/about'>About</a>"),
                                "https://mill.test/"))
    assert links == {"about": "https://mill.test/about"}


def test_information_site_detected_from_title_is_excluded(tmp_path):
    sites = {"https://mill-index.test/": html(
        "<p>We spin and scour greasy wool news every day for spinning mills around the world in our weekly report.</p>",
        title="The Mill Index - Global textile mill intelligence and sourcing resources")}
    result = run_pipeline(PipelineRequest("raw_sheep_wool", mode="seed", seed_urls=["https://mill-index.test/"]),
                          fetcher=FakeFetcher(sites), snapshot_dir=tmp_path)
    assert result["leads"] == [] and "information site" in result["excluded"][-1]["reason"]
