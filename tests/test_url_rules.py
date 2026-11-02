"""Unit tests for URL normalisation, resolution, and filtering rules."""

import pytest

from nz_policy_wordcloud.config import ExclusionConfig, PartyConfig
from nz_policy_wordcloud.url_rules import (
    UrlRejectReason,
    check_host_allowed,
    is_url_allowed_for_party,
    resolve_and_normalize_url,
)


@pytest.fixture
def sample_party() -> PartyConfig:
    return PartyConfig(
        id="sample_party",
        name="Sample Party",
        allowed_domains=["example.org", "www.example.org"],
        starting_urls=["https://example.org/policy"],
    )


@pytest.fixture
def sample_exclusions() -> ExclusionConfig:
    return ExclusionConfig(
        path_patterns=["/donate", "/join", "/shop", "/media-release"],
        file_extensions=[".pdf", ".zip", ".png", ".jpg", ".docx"],
        custom_stop_words=["policy"],
    )


class TestResolveAndNormalizeUrl:
    def test_relative_url_resolution(self) -> None:
        base = "https://example.org/policy/index.html"
        link = "transport"
        result = resolve_and_normalize_url(base, link)
        assert result.is_ok()
        assert result.unwrap() == "https://example.org/policy/transport"

    def test_root_relative_url(self) -> None:
        base = "https://example.org/policy/index.html"
        link = "/housing"
        result = resolve_and_normalize_url(base, link)
        assert result.is_ok()
        assert result.unwrap() == "https://example.org/housing"

    def test_absolute_url_scheme_and_host_lowercased(self) -> None:
        base = "https://example.org/"
        link = "HTTPS://EXAMPLE.ORG/Policies/Health"
        result = resolve_and_normalize_url(base, link)
        assert result.is_ok()
        assert result.unwrap() == "https://example.org/Policies/Health"

    def test_strip_default_ports(self) -> None:
        http_result = resolve_and_normalize_url("http://example.org:80/page", "link")
        assert http_result.is_ok()
        assert http_result.unwrap() == "http://example.org/link"

        https_result = resolve_and_normalize_url("https://example.org:443/page", "link")
        assert https_result.is_ok()
        assert https_result.unwrap() == "https://example.org/link"

    def test_fragment_removal(self) -> None:
        base = "https://example.org/policy"
        link = "transport#section-2"
        result = resolve_and_normalize_url(base, link)
        assert result.is_ok()
        assert result.unwrap() == "https://example.org/transport"

    def test_fragment_deduplication(self) -> None:
        """Verify different fragments on the same path normalise to identical URLs."""
        base = "https://example.org/policy"
        u1 = resolve_and_normalize_url(base, "/plan#summary")
        u2 = resolve_and_normalize_url(base, "/plan#costings")
        u3 = resolve_and_normalize_url(base, "/plan")
        assert u1.is_ok() and u2.is_ok() and u3.is_ok()
        assert u1.unwrap() == u2.unwrap() == u3.unwrap() == "https://example.org/plan"

    def test_query_parameters_preserved(self) -> None:
        """Verify query parameters are not deleted."""
        base = "https://example.org/policy"
        link = "/filter?topic=economy&year=2026"
        result = resolve_and_normalize_url(base, link)
        assert result.is_ok()
        assert result.unwrap() == "https://example.org/filter?topic=economy&year=2026"

    @pytest.mark.parametrize(
        "unsupported_link",
        [
            "mailto:info@example.org",
            "tel:+6491234567",
            "javascript:void(0)",
            "data:text/html,<html></html>",
            "ftp://example.org/file.txt",
        ],
    )
    def test_unsupported_schemes_rejected(self, unsupported_link: str) -> None:
        base = "https://example.org/policy"
        result = resolve_and_normalize_url(base, unsupported_link)
        assert result.is_err()
        assert result.unwrap_err() == UrlRejectReason.UNSUPPORTED_SCHEME

    def test_empty_link_rejected(self) -> None:
        base = "https://example.org/policy"
        result = resolve_and_normalize_url(base, "   ")
        assert result.is_err()
        assert result.unwrap_err() == UrlRejectReason.EMPTY_URL


class TestHostAllowed:
    def test_exact_host_match(self) -> None:
        assert check_host_allowed("example.org", ["example.org"]).is_ok()
        assert check_host_allowed("EXAMPLE.ORG", ["example.org"]).is_ok()

    def test_subdomain_rejected_when_not_listed(self) -> None:
        result = check_host_allowed("shop.example.org", ["example.org"])
        assert result.is_err()
        assert result.unwrap_err() == UrlRejectReason.DISALLOWED_SUBDOMAIN

    def test_subdomain_allowed_when_explicitly_listed(self) -> None:
        allowed = ["example.org", "shop.example.org"]
        assert check_host_allowed("shop.example.org", allowed).is_ok()

    def test_external_host_rejected(self) -> None:
        result = check_host_allowed("external.com", ["example.org"])
        assert result.is_err()
        assert result.unwrap_err() == UrlRejectReason.EXTERNAL_HOST


class TestIsUrlAllowedForParty:
    def test_allowed_policy_url(
        self, sample_party: PartyConfig, sample_exclusions: ExclusionConfig
    ) -> None:
        url = "https://example.org/policies/transport"
        result = is_url_allowed_for_party(url, sample_party, sample_exclusions)
        assert result.is_ok()
        assert result.unwrap() == url

    def test_rejected_external_domain(
        self, sample_party: PartyConfig, sample_exclusions: ExclusionConfig
    ) -> None:
        url = "https://otherdomain.com/policies"
        result = is_url_allowed_for_party(url, sample_party, sample_exclusions)
        assert result.is_err()
        assert result.unwrap_err() == UrlRejectReason.EXTERNAL_HOST

    def test_rejected_unapproved_subdomain(
        self, sample_party: PartyConfig, sample_exclusions: ExclusionConfig
    ) -> None:
        url = "https://blog.example.org/post"
        result = is_url_allowed_for_party(url, sample_party, sample_exclusions)
        assert result.is_err()
        assert result.unwrap_err() == UrlRejectReason.DISALLOWED_SUBDOMAIN

    @pytest.mark.parametrize(
        "file_url",
        [
            "https://example.org/policy.pdf",
            "https://example.org/archive.ZIP",
            "https://example.org/photo.PNG",
            "https://example.org/document.docx",
        ],
    )
    def test_rejected_non_html_file_extensions(
        self,
        file_url: str,
        sample_party: PartyConfig,
        sample_exclusions: ExclusionConfig,
    ) -> None:
        result = is_url_allowed_for_party(file_url, sample_party, sample_exclusions)
        assert result.is_err()
        assert result.unwrap_err() == UrlRejectReason.NON_HTML_EXTENSION

    @pytest.mark.parametrize(
        "pattern_url",
        [
            "https://example.org/donate",
            "https://example.org/join-us",
            "https://example.org/shop/items",
            "https://example.org/media-release/2026/speech",
        ],
    )
    def test_rejected_excluded_path_patterns(
        self,
        pattern_url: str,
        sample_party: PartyConfig,
        sample_exclusions: ExclusionConfig,
    ) -> None:
        result = is_url_allowed_for_party(pattern_url, sample_party, sample_exclusions)
        assert result.is_err()
        assert result.unwrap_err() == UrlRejectReason.EXCLUDED_PATH_PATTERN

    def test_rejected_default_exclusions(self, sample_party: PartyConfig) -> None:
        default_exclusions = ExclusionConfig()
        test_cases = [
            "https://example.org/party-information",
            "https://example.org/about-us",
            "https://example.org/news/update",
            "https://example.org/health-and-safety",
            "https://example.org/our-people",
            "https://example.org/team/members",
            "https://example.org/mps/luxon",
            "https://example.org/events/rally",
            "https://example.org/terms-of-service",
            "https://example.org/payment-terms",
            "https://example.org/groups",
            "https://example.org/mp-news/update",
            "https://example.org/sign-in",
            "https://example.org/tos",
            "https://example.org/party-rules",
            "https://example.org/bod",
            "https://example.org/ourcandidates",
            "https://example.org/our-team",
            "https://example.org/members/portal",
            "https://example.org/about_our_charter",
            "https://example.org/our_people",
            "https://example.org/about_us_our_mps",
            "https://example.org/get_involved",
            "https://example.org/membership-join",
            "https://example.org/sign_up",
            "https://example.org/work-for-us",
            "https://example.org/email-protection",
            "https://example.org/calendar/2026",
            "https://example.org/get-involved",
            "https://example.org/store/merch",
            "https://example.org/search?q=test",
            "https://example.org/facebook/share",
            "https://example.org/subscribe",
            "https://example.org/the-team",
            "https://example.org/north-candidates",
            "https://example.org/in-memory",
        ]
        for url in test_cases:
            result = is_url_allowed_for_party(url, sample_party, default_exclusions)
            assert result.is_err(), f"Expected {url} to be rejected by default exclusions"
            assert result.unwrap_err() == UrlRejectReason.EXCLUDED_PATH_PATTERN
