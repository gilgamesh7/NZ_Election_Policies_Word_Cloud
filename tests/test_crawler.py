"""Unit tests for HtmlCrawler using httpx.MockTransport."""

import httpx
import pytest

from nz_policy_wordcloud.config import CrawlerConfig, ExclusionConfig, PartyConfig
from nz_policy_wordcloud.crawler import HtmlCrawler, PageRecord


@pytest.fixture
def test_party() -> PartyConfig:
    return PartyConfig(
        id="demo_party",
        name="Demo Party",
        allowed_domains=["demo.org", "www.demo.org"],
        starting_urls=["https://demo.org/start"],
    )


@pytest.fixture
def fast_crawler_config() -> CrawlerConfig:
    return CrawlerConfig(
        user_agent="TestBot/1.0",
        request_timeout_seconds=2.0,
        delay_seconds=0.0,  # Fast tests with no delay
        max_retries=1,
        max_bytes=10000,
    )


def test_crawler_strict_one_level_depth(
    test_party: PartyConfig, fast_crawler_config: CrawlerConfig
) -> None:
    """Verify crawler fetches starting page and direct links, but NEVER follows depth-2 links."""
    start_html = """
    <html>
      <body>
        <h1>Policy Portal</h1>
        <a href="/policy-a">Policy A</a>
        <a href="/policy-b">Policy B</a>
      </body>
    </html>
    """
    policy_a_html = """
    <html>
      <body>
        <h2>Policy A</h2>
        <a href="/deep-level-2">Deep Level 2 Link</a>
      </body>
    </html>
    """
    policy_b_html = "<html><body><h2>Policy B</h2></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"})
        if url == "https://demo.org/start":
            return httpx.Response(200, text=start_html, headers={"content-type": "text/html"})
        if url == "https://demo.org/policy-a":
            return httpx.Response(200, text=policy_a_html, headers={"content-type": "text/html"})
        if url == "https://demo.org/policy-b":
            return httpx.Response(200, text=policy_b_html, headers={"content-type": "text/html"})
        if url == "https://demo.org/deep-level-2":
            pytest.fail("Crawler followed depth-2 link: https://demo.org/deep-level-2")
        return httpx.Response(404, text="Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    crawler = HtmlCrawler(crawler_config=fast_crawler_config)
    records = crawler.crawl_party(test_party, client=client)

    urls_fetched = [r.attempted_url for r in records if r.success]
    assert "https://demo.org/start" in urls_fetched
    assert "https://demo.org/policy-a" in urls_fetched
    assert "https://demo.org/policy-b" in urls_fetched
    assert "https://demo.org/deep-level-2" not in urls_fetched

    # Check is_starting_page flags
    start_rec = next(r for r in records if r.attempted_url == "https://demo.org/start")
    assert start_rec.is_starting_page is True
    a_rec = next(r for r in records if r.attempted_url == "https://demo.org/policy-a")
    assert a_rec.is_starting_page is False


def test_crawler_same_domain_and_exclusions(
    test_party: PartyConfig, fast_crawler_config: CrawlerConfig
) -> None:
    """Verify external hosts, subdomains, excluded paths, and non-HTML files are filtered out."""
    start_html = """
    <html>
      <body>
        <a href="/allowed-policy">Allowed Policy</a>
        <a href="https://external.com/policy">External Domain</a>
        <a href="https://sub.demo.org/policy">Disallowed Subdomain</a>
        <a href="/donate">Donate Pattern</a>
        <a href="/download.pdf">PDF File</a>
        <a href="mailto:contact@demo.org">Email</a>
      </body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"})
        if url == "https://demo.org/start":
            return httpx.Response(200, text=start_html, headers={"content-type": "text/html"})
        if url == "https://demo.org/allowed-policy":
            return httpx.Response(200, text="<html><body>Allowed</body></html>", headers={"content-type": "text/html"})
        return httpx.Response(404, text="Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    crawler = HtmlCrawler(crawler_config=fast_crawler_config)
    records = crawler.crawl_party(test_party, client=client)

    succeeded_urls = [r.attempted_url for r in records if r.success]
    assert succeeded_urls == ["https://demo.org/start", "https://demo.org/allowed-policy"]


def test_crawler_deduplication(
    test_party: PartyConfig, fast_crawler_config: CrawlerConfig
) -> None:
    """Verify links with identical normalised URLs or different fragments are only crawled once."""
    start_html = """
    <html>
      <body>
        <a href="/plan#summary">Plan Summary</a>
        <a href="/plan#details">Plan Details</a>
        <a href="/plan">Plan</a>
      </body>
    </html>
    """
    call_counts: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        call_counts[url] = call_counts.get(url, 0) + 1
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"})
        return httpx.Response(200, text=start_html, headers={"content-type": "text/html"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    crawler = HtmlCrawler(crawler_config=fast_crawler_config)
    records = crawler.crawl_party(test_party, client=client)

    # /plan should only be requested once
    assert call_counts.get("https://demo.org/plan") == 1
    plan_records = [r for r in records if r.attempted_url == "https://demo.org/plan"]
    assert len(plan_records) == 1


def test_page_failure_does_not_crash_run(
    test_party: PartyConfig, fast_crawler_config: CrawlerConfig
) -> None:
    """Verify HTTP errors and timeouts do not stop the crawler from completing remaining pages."""
    start_html = """
    <html>
      <body>
        <a href="/broken-500">Broken 500</a>
        <a href="/good-page">Good Page</a>
        <a href="/missing-404">Missing 404</a>
      </body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"})
        if url == "https://demo.org/start":
            return httpx.Response(200, text=start_html, headers={"content-type": "text/html"})
        if url == "https://demo.org/broken-500":
            return httpx.Response(500, text="Server Error")
        if url == "https://demo.org/good-page":
            return httpx.Response(200, text="<html><body>Good</body></html>", headers={"content-type": "text/html"})
        if url == "https://demo.org/missing-404":
            return httpx.Response(404, text="Not Found")
        return httpx.Response(404, text="Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    crawler = HtmlCrawler(crawler_config=fast_crawler_config)
    records = crawler.crawl_party(test_party, client=client)

    assert len(records) == 4
    good_rec = next(r for r in records if r.attempted_url == "https://demo.org/good-page")
    assert good_rec.success is True
    assert good_rec.status_code == 200

    broken_rec = next(r for r in records if r.attempted_url == "https://demo.org/broken-500")
    assert broken_rec.success is False
    assert "HTTP error 500" in (broken_rec.error_message or "")

    missing_rec = next(r for r in records if r.attempted_url == "https://demo.org/missing-404")
    assert missing_rec.success is False
    assert "HTTP error 404" in (missing_rec.error_message or "")


def test_unsupported_content_type_rejection(
    test_party: PartyConfig, fast_crawler_config: CrawlerConfig
) -> None:
    """Verify pages returning non-HTML mime types are rejected."""
    start_html = '<html><body><a href="/file">Binary File</a></body></html>'

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"})
        if url == "https://demo.org/start":
            return httpx.Response(200, text=start_html, headers={"content-type": "text/html"})
        if url == "https://demo.org/file":
            return httpx.Response(200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"})
        return httpx.Response(404, text="Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    crawler = HtmlCrawler(crawler_config=fast_crawler_config)
    records = crawler.crawl_party(test_party, client=client)

    file_rec = next(r for r in records if r.attempted_url == "https://demo.org/file")
    assert file_rec.success is False
    assert "Unsupported content type" in (file_rec.error_message or "")


def test_max_bytes_rejection(
    test_party: PartyConfig, fast_crawler_config: CrawlerConfig
) -> None:
    """Verify oversized response bodies are rejected."""
    oversized_crawler_config = CrawlerConfig(
        user_agent="TestBot/1.0",
        delay_seconds=0.0,
        max_bytes=1025,  # Valid boundary meeting gt=1024
    )
    large_html = "<html><body>" + ("x" * 3000) + "</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"})
        return httpx.Response(200, text=large_html, headers={"content-type": "text/html"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    crawler = HtmlCrawler(crawler_config=oversized_crawler_config)
    records = crawler.crawl_party(test_party, client=client)

    start_rec = records[0]
    assert start_rec.success is False
    assert "exceeds limit" in (start_rec.error_message or "")


def test_robots_txt_disallow(
    test_party: PartyConfig, fast_crawler_config: CrawlerConfig
) -> None:
    """Verify pages disallowed by robots.txt are skipped."""
    robots_text = "User-agent: *\nDisallow: /disallowed-policy\n"
    start_html = '<html><body><a href="/disallowed-policy">Disallowed</a></body></html>'

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=robots_text, headers={"content-type": "text/plain"})
        if url == "https://demo.org/start":
            return httpx.Response(200, text=start_html, headers={"content-type": "text/html"})
        if url == "https://demo.org/disallowed-policy":
            return httpx.Response(200, text="<html><body>Private</body></html>", headers={"content-type": "text/html"})
        return httpx.Response(404, text="Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    crawler = HtmlCrawler(crawler_config=fast_crawler_config)
    records = crawler.crawl_party(test_party, client=client)

    disallowed_rec = next(r for r in records if r.attempted_url == "https://demo.org/disallowed-policy")
    assert disallowed_rec.success is False
    assert "Disallowed by robots.txt" in (disallowed_rec.error_message or "")


def test_crawl_all_multiple_parties(fast_crawler_config: CrawlerConfig) -> None:
    """Verify crawl_all aggregates records across multiple parties into CrawlManifest."""
    party1 = PartyConfig(
        id="party_1",
        name="Party One",
        allowed_domains=["party1.org"],
        starting_urls=["https://party1.org/home"],
    )
    party2 = PartyConfig(
        id="party_2",
        name="Party Two",
        allowed_domains=["party2.org"],
        starting_urls=["https://party2.org/home"],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"})
        return httpx.Response(200, text="<html><body>Home</body></html>", headers={"content-type": "text/html"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    crawler = HtmlCrawler(crawler_config=fast_crawler_config)
    manifest = crawler.crawl_all([party1, party2], client=client)

    assert manifest.total_attempted == 2
    assert manifest.total_succeeded == 2
    assert manifest.total_failed == 0
    assert len(manifest.records_for_party("party_1")) == 1
    assert len(manifest.records_for_party("party_2")) == 1
    dict_list = manifest.to_dict_list()
    assert len(dict_list) == 2
    assert dict_list[0]["party_id"] == "party_1"
    assert dict_list[1]["party_id"] == "party_2"
