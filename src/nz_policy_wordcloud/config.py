"""Configuration models and loading utilities."""

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from result import Err, Ok, Result

# Valid party ID pattern: lowercase alphanumeric, hyphens, and underscores
PARTY_ID_PATTERN = re.compile(r"^[a-z0-9_-]+$")

# Valid domain name pattern
DOMAIN_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$"
)


class CrawlerConfig(BaseModel):
    """Configuration options for HTTP crawling."""

    user_agent: str = Field(
        default="NZPolicyWordCloudResearch/1.0 (+https://example.org/bot)",
        min_length=5,
        description="User-Agent string identifying the crawler politely.",
    )
    request_timeout_seconds: float = Field(
        default=10.0,
        gt=0.0,
        le=60.0,
        description="Per-request HTTP timeout in seconds.",
    )
    delay_seconds: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Polite delay between consecutive requests to the same host.",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts on transient network errors.",
    )
    max_bytes: int = Field(
        default=5_242_880,  # 5 MB
        gt=1024,
        le=50_000_000,
        description="Maximum allowed response body size in bytes.",
    )


class ExclusionConfig(BaseModel):
    """Exclusion rules for paths, file types, and analysis terms."""

    path_patterns: list[str] = Field(
        default_factory=lambda: [
            "/donate",
            "/join",
            "/volunteer",
            "/shop",
            "/cart",
            "/checkout",
            "/login",
            "/privacy",
            "/terms",
            "/contact",
            "/media-release",
        ],
        description="Substrings or paths that disqualify a URL from collection.",
    )
    file_extensions: list[str] = Field(
        default_factory=lambda: [
            ".pdf",
            ".zip",
            ".tar",
            ".gz",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".mp3",
            ".mp4",
            ".docx",
            ".xlsx",
        ],
        description="File extensions to skip.",
    )
    custom_stop_words: list[str] = Field(
        default_factory=list,
        description="Additional project-specific words to exclude during analysis.",
    )


class PartyConfig(BaseModel):
    """Configuration for an individual political party."""

    id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier for the party, safe for filenames.",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Human-readable party display name.",
    )
    allowed_domains: list[str] = Field(
        ...,
        min_length=1,
        description="List of fully-qualified hostnames permitted for crawling.",
    )
    starting_urls: list[str] = Field(
        ...,
        min_length=1,
        description="Starting policy page URLs to crawl.",
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, value: str) -> str:
        lowered = value.strip().lower()
        if not PARTY_ID_PATTERN.match(lowered):
            raise ValueError(
                f"Party ID '{value}' is invalid. Must contain only lowercase alphanumeric, hyphens, or underscores."
            )
        return lowered

    @field_validator("allowed_domains")
    @classmethod
    def validate_domains(cls, domains: list[str]) -> list[str]:
        cleaned: list[str] = []
        for domain in domains:
            d = domain.strip().lower()
            if not DOMAIN_PATTERN.match(d):
                raise ValueError(
                    f"Invalid domain format '{domain}'. Expected valid FQDN (e.g. 'example.org')."
                )
            if d not in cleaned:
                cleaned.append(d)
        return cleaned

    @field_validator("starting_urls")
    @classmethod
    def validate_starting_urls(cls, urls: list[str]) -> list[str]:
        cleaned: list[str] = []
        for url in urls:
            u = url.strip()
            parsed = urlparse(u)
            if parsed.scheme.lower() not in {"http", "https"}:
                raise ValueError(f"Starting URL '{url}' must use HTTP or HTTPS scheme.")
            if not parsed.hostname:
                raise ValueError(f"Starting URL '{url}' has an invalid hostname.")
            if u not in cleaned:
                cleaned.append(u)
        return cleaned

    @model_validator(mode="after")
    def validate_starting_urls_match_allowed_domains(self) -> "PartyConfig":
        allowed_set = {d.lower() for d in self.allowed_domains}
        for url in self.starting_urls:
            host = (urlparse(url).hostname or "").lower()
            if host not in allowed_set:
                raise ValueError(
                    f"Starting URL '{url}' host '{host}' is not in party's allowed_domains {self.allowed_domains}."
                )
        return self


class AppConfig(BaseModel):
    """Top-level application configuration."""

    crawler_settings: CrawlerConfig = Field(default_factory=CrawlerConfig)
    exclusions: ExclusionConfig = Field(default_factory=ExclusionConfig)
    parties: list[PartyConfig] = Field(
        ...,
        min_length=1,
        description="List of parties to collect and analyse.",
    )

    @field_validator("parties")
    @classmethod
    def validate_unique_party_ids(cls, parties: list[PartyConfig]) -> list[PartyConfig]:
        seen_ids: set[str] = set()
        for party in parties:
            if party.id in seen_ids:
                raise ValueError(f"Duplicate party ID detected: '{party.id}'. Party IDs must be unique.")
            seen_ids.add(party.id)
        return parties


def load_config_from_dict(data: dict[str, Any]) -> Result[AppConfig, str]:
    """Parse and validate configuration data from a dictionary."""
    if not isinstance(data, dict):
        return Err("Configuration data must be a dictionary.")
    try:
        config = AppConfig.model_validate(data)
        return Ok(config)
    except Exception as exc:
        return Err(f"Configuration validation failed: {exc}")


def load_config_from_yaml(path: str | Path) -> Result[AppConfig, str]:
    """Load, parse, and validate application configuration from a YAML file."""
    config_path = Path(path)
    if not config_path.is_file():
        return Err(f"Configuration file not found: {config_path}")

    try:
        content = config_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
    except Exception as exc:
        return Err(f"Failed to read or parse YAML file '{config_path}': {exc}")

    if not isinstance(parsed, dict):
        return Err(f"Configuration in '{config_path}' must be a YAML mapping.")

    return load_config_from_dict(parsed)
