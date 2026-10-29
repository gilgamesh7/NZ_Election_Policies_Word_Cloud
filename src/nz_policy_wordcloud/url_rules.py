"""URL resolution, normalisation, and filtering rules."""

from enum import Enum
from pathlib import PurePosixPath
from typing import Final
from urllib.parse import urljoin, urlparse, urlunsplit

from result import Err, Ok, Result

from nz_policy_wordcloud.config import ExclusionConfig, PartyConfig

# Supported URL schemes
SUPPORTED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})

# Unsupported protocol prefixes that should be rejected immediately
UNSUPPORTED_PREFIXES: Final[tuple[str, ...]] = (
    "mailto:",
    "tel:",
    "javascript:",
    "data:",
    "ftp:",
    "file:",
)


class UrlRejectReason(str, Enum):
    """Categorized reasons for rejecting a URL during crawling."""

    EMPTY_URL = "empty_url"
    UNSUPPORTED_SCHEME = "unsupported_scheme"
    INVALID_STRUCTURE = "invalid_structure"
    EXTERNAL_HOST = "external_host"
    DISALLOWED_SUBDOMAIN = "disallowed_subdomain"
    NON_HTML_EXTENSION = "non_html_extension"
    EXCLUDED_PATH_PATTERN = "excluded_path_pattern"


def resolve_and_normalize_url(base_url: str, link_url: str) -> Result[str, UrlRejectReason]:
    """Resolve a possibly relative link against a base URL and normalise it.

    Performs:
    - Whitespace trimming
    - Rejection of non-web schemes (mailto, tel, javascript)
    - Relative URL resolution via urljoin
    - Fragment removal
    - Scheme and hostname lowercasing
    - Default port stripping (80 for http, 443 for https)
    - Query parameter preservation
    """
    clean_link = link_url.strip()
    if not clean_link:
        return Err(UrlRejectReason.EMPTY_URL)

    lower_link = clean_link.lower()
    for prefix in UNSUPPORTED_PREFIXES:
        if lower_link.startswith(prefix):
            return Err(UrlRejectReason.UNSUPPORTED_SCHEME)

    try:
        resolved = urljoin(base_url.strip(), clean_link)
        parsed = urlparse(resolved)
    except Exception:
        return Err(UrlRejectReason.INVALID_STRUCTURE)

    scheme = parsed.scheme.lower()
    if scheme not in SUPPORTED_SCHEMES:
        return Err(UrlRejectReason.UNSUPPORTED_SCHEME)

    netloc = parsed.netloc.lower()
    if not netloc:
        return Err(UrlRejectReason.INVALID_STRUCTURE)

    # Strip standard default ports if present
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Clean path: ensure at least a slash if empty, collapse double slashes
    path = parsed.path or "/"
    while "//" in path:
        path = path.replace("//", "/")

    # Fragments are stripped; query strings are strictly preserved
    normalized = urlunsplit((scheme, netloc, path, parsed.query, ""))
    return Ok(normalized)


def check_host_allowed(hostname: str, allowed_domains: list[str]) -> Result[None, UrlRejectReason]:
    """Verify whether a hostname matches the party's allowed domains."""
    lowered_host = hostname.lower()
    lowered_allowed = [d.lower() for d in allowed_domains]

    if lowered_host in lowered_allowed:
        return Ok(None)

    # Check if this host is a subdomain of an allowed domain
    for allowed in lowered_allowed:
        if lowered_host.endswith(f".{allowed}"):
            return Err(UrlRejectReason.DISALLOWED_SUBDOMAIN)

    return Err(UrlRejectReason.EXTERNAL_HOST)


def is_url_allowed_for_party(
    url: str,
    party: PartyConfig,
    exclusions: ExclusionConfig,
) -> Result[str, UrlRejectReason]:
    """Determine whether a resolved URL is permitted to be crawled for a party.

    Validates:
    - Hostname is explicitly listed in party allowed_domains
    - File extension is not in exclusions.file_extensions
    - Path does not contain any pattern from exclusions.path_patterns
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return Err(UrlRejectReason.INVALID_STRUCTURE)

    host = parsed.hostname
    if not host:
        return Err(UrlRejectReason.INVALID_STRUCTURE)

    host_check = check_host_allowed(host, party.allowed_domains)
    if host_check.is_err():
        return Err(host_check.unwrap_err())

    # Check file extension from path
    posix_path = PurePosixPath(parsed.path)
    extension = posix_path.suffix.lower()
    if extension:
        lowered_file_exts = {ext.lower() for ext in exclusions.file_extensions}
        if extension in lowered_file_exts:
            return Err(UrlRejectReason.NON_HTML_EXTENSION)

    # Check excluded path patterns
    lowered_path = parsed.path.lower()
    for pattern in exclusions.path_patterns:
        if pattern.lower() in lowered_path:
            return Err(UrlRejectReason.EXCLUDED_PATH_PATTERN)

    return Ok(url)
