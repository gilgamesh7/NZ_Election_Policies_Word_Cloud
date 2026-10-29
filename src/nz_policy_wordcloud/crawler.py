"""Polite, non-recursive, first-level HTML web crawler."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import httpx
from result import Err, Ok, Result

from nz_policy_wordcloud.config import CrawlerConfig, ExclusionConfig, PartyConfig
from nz_policy_wordcloud.url_rules import (
    UrlRejectReason,
    is_url_allowed_for_party,
    resolve_and_normalize_url,
)


@dataclass
class PageRecord:
    """Record describing the crawl outcome of a single page."""

    party_id: str
    attempted_url: str
    final_url: str | None = None
    status_code: int | None = None
    is_starting_page: bool = False
    success: bool = False
    error_message: str | None = None
    content_type: str | None = None
    content_bytes: int = 0
    html: str | None = None
    timestamp_iso: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class CrawlManifest:
    """Collection of all crawled page records across a crawl execution."""

    records: list[PageRecord] = field(default_factory=list)

    @property
    def total_attempted(self) -> int:
        return len(self.records)

    @property
    def total_succeeded(self) -> int:
        return sum(1 for r in self.records if r.success)

    @property
    def total_failed(self) -> int:
        return sum(1 for r in self.records if not r.success)

    def records_for_party(self, party_id: str) -> list[PageRecord]:
        return [r for r in self.records if r.party_id == party_id]

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Export manifest records as dictionaries suitable for CSV export."""
        return [
            {
                "party_id": r.party_id,
                "attempted_url": r.attempted_url,
                "final_url": r.final_url or "",
                "status_code": r.status_code if r.status_code is not None else "",
                "is_starting_page": r.is_starting_page,
                "success": r.success,
                "error_message": r.error_message or "",
                "content_type": r.content_type or "",
                "content_bytes": r.content_bytes,
                "timestamp_iso": r.timestamp_iso,
            }
            for r in self.records
        ]


class RobotsCache:
    """In-memory cache for robots.txt parsers per hostname."""

    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser] = {}

    def is_allowed(
        self,
        url: str,
        user_agent: str,
        client: httpx.Client,
        timeout: float = 5.0,
    ) -> bool:
        """Check whether fetching url is allowed by the host's robots.txt."""
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if not host:
            return False

        if host not in self._cache:
            parser = RobotFileParser()
            robots_url = f"{parsed.scheme}://{host}/robots.txt"
            try:
                resp = client.get(robots_url, timeout=timeout)
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                else:
                    # If 404 or other non-200, standard behaviour is all allowed
                    parser.allow_all = True
            except Exception:
                # If network fails to fetch robots.txt, default to permissive
                parser.allow_all = True
            self._cache[host] = parser

        return self._cache[host].can_fetch(user_agent, url)


class HtmlCrawler:
    """Polite HTML crawler restricted strictly to starting pages and first-level links."""

    def __init__(
        self,
        crawler_config: CrawlerConfig | None = None,
        exclusion_config: ExclusionConfig | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.crawler_config = crawler_config or CrawlerConfig()
        self.exclusion_config = exclusion_config or ExclusionConfig()
        self._external_client = client
        self._robots = RobotsCache()
        self._last_request_time: dict[str, float] = {}

    def _get_client(self) -> httpx.Client:
        if self._external_client is not None:
            return self._external_client
        return httpx.Client(
            headers={"User-Agent": self.crawler_config.user_agent},
            timeout=self.crawler_config.request_timeout_seconds,
            follow_redirects=True,
        )

    def _rate_limit(self, host: str) -> None:
        """Enforce polite per-host delay between consecutive requests."""
        if self.crawler_config.delay_seconds <= 0.0:
            return

        now = time.time()
        last_time = self._last_request_time.get(host, 0.0)
        elapsed = now - last_time
        if elapsed < self.crawler_config.delay_seconds:
            time.sleep(self.crawler_config.delay_seconds - elapsed)
        self._last_request_time[host] = time.time()

    def fetch_url(
        self,
        url: str,
        client: httpx.Client,
    ) -> Result[tuple[str, int, str, str], str]:
        """Fetch a single URL respecting robots.txt, size limits, and retries.

        Returns Ok((final_url, status_code, content_type, html_content)) or Err(reason).
        """
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        # Check robots.txt
        if not self._robots.is_allowed(
            url,
            self.crawler_config.user_agent,
            client,
            timeout=self.crawler_config.request_timeout_seconds,
        ):
            return Err("Disallowed by robots.txt")

        self._rate_limit(host)

        attempts = 0
        max_attempts = 1 + self.crawler_config.max_retries
        last_error = ""

        while attempts < max_attempts:
            attempts += 1
            try:
                resp = client.get(url)

                if resp.status_code >= 400:
                    return Err(f"HTTP error {resp.status_code}")

                content_type = resp.headers.get("content-type", "").lower()
                # Check content type is HTML
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    return Err(f"Unsupported content type '{content_type}'; expected text/html")

                # Check body size
                content_bytes = len(resp.content)
                if content_bytes > self.crawler_config.max_bytes:
                    return Err(
                        f"Response size {content_bytes} exceeds limit of {self.crawler_config.max_bytes} bytes"
                    )

                return Ok((str(resp.url), resp.status_code, content_type, resp.text))

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as exc:
                last_error = f"Network error: {type(exc).__name__}"
                if attempts < max_attempts:
                    time.sleep(0.5 * attempts)
            except Exception as exc:
                return Err(f"Request failed: {exc}")

        return Err(f"{last_error} after {max_attempts} attempts")

    def extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract and normalise unique links found within an HTML document."""
        discovered: list[str] = []
        seen: set[str] = set()

        soup = BeautifulSoup(html, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            norm_res = resolve_and_normalize_url(base_url, href)
            if norm_res.is_ok():
                clean_url = norm_res.unwrap()
                if clean_url not in seen:
                    seen.add(clean_url)
                    discovered.append(clean_url)

        return discovered

    def crawl_party(
        self,
        party: PartyConfig,
        client: httpx.Client | None = None,
    ) -> list[PageRecord]:
        """Crawl starting pages and eligible first-level direct links for a party."""
        http_client = client or self._get_client()
        records: list[PageRecord] = []
        visited_urls: set[str] = set()
        first_level_queue: list[str] = []

        # Step 1: Process starting pages
        for start_url in party.starting_urls:
            norm_res = resolve_and_normalize_url(start_url, start_url)
            if norm_res.is_err():
                records.append(
                    PageRecord(
                        party_id=party.id,
                        attempted_url=start_url,
                        is_starting_page=True,
                        success=False,
                        error_message=f"Invalid starting URL: {norm_res.unwrap_err()}",
                    )
                )
                continue

            clean_start = norm_res.unwrap()
            if clean_start in visited_urls:
                continue
            visited_urls.add(clean_start)

            # Check if allowed by party and exclusions
            allowed_res = is_url_allowed_for_party(
                clean_start, party, self.exclusion_config
            )
            if allowed_res.is_err():
                records.append(
                    PageRecord(
                        party_id=party.id,
                        attempted_url=clean_start,
                        is_starting_page=True,
                        success=False,
                        error_message=f"Starting URL rejected: {allowed_res.unwrap_err()}",
                    )
                )
                continue

            fetch_res = self.fetch_url(clean_start, http_client)
            if fetch_res.is_err():
                records.append(
                    PageRecord(
                        party_id=party.id,
                        attempted_url=clean_start,
                        is_starting_page=True,
                        success=False,
                        error_message=fetch_res.unwrap_err(),
                    )
                )
                continue

            final_url, status_code, content_type, html = fetch_res.unwrap()
            records.append(
                PageRecord(
                    party_id=party.id,
                    attempted_url=clean_start,
                    final_url=final_url,
                    status_code=status_code,
                    is_starting_page=True,
                    success=True,
                    content_type=content_type,
                    content_bytes=len(html.encode("utf-8")),
                    html=html,
                )
            )

            # Extract first-level links only from successful starting pages
            links = self.extract_links(html, final_url)
            for link in links:
                if link in visited_urls:
                    continue
                # Verify link is permitted
                if is_url_allowed_for_party(link, party, self.exclusion_config).is_ok():
                    if link not in first_level_queue:
                        first_level_queue.append(link)

        # Step 2: Fetch first-level links (strictly depth = 1, do NOT extract further links)
        for link in first_level_queue:
            if link in visited_urls:
                continue
            visited_urls.add(link)

            fetch_res = self.fetch_url(link, http_client)
            if fetch_res.is_err():
                records.append(
                    PageRecord(
                        party_id=party.id,
                        attempted_url=link,
                        is_starting_page=False,
                        success=False,
                        error_message=fetch_res.unwrap_err(),
                    )
                )
                continue

            final_url, status_code, content_type, html = fetch_res.unwrap()
            records.append(
                PageRecord(
                    party_id=party.id,
                    attempted_url=link,
                    final_url=final_url,
                    status_code=status_code,
                    is_starting_page=False,
                    success=True,
                    content_type=content_type,
                    content_bytes=len(html.encode("utf-8")),
                    html=html,
                )
            )

        return records

    def crawl_all(
        self,
        parties: list[PartyConfig],
        client: httpx.Client | None = None,
    ) -> CrawlManifest:
        """Crawl starting pages and first-level links for all supplied parties."""
        http_client = client or self._get_client()
        manifest = CrawlManifest()

        for party in parties:
            party_records = self.crawl_party(party, client=http_client)
            manifest.records.extend(party_records)

        return manifest

    def crawl_all_parties(
        self,
        parties: list[PartyConfig],
        client: httpx.Client | None = None,
    ) -> CrawlManifest:
        """Alias for crawl_all."""
        return self.crawl_all(parties=parties, client=client)
