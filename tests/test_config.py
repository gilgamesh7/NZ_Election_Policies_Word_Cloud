"""Unit tests for configuration loading and validation."""

from pathlib import Path
import pytest

from nz_policy_wordcloud.config import (
    AppConfig,
    CrawlerConfig,
    ExclusionConfig,
    PartyConfig,
    load_config_from_dict,
    load_config_from_yaml,
)


def test_load_example_config(project_root: Path) -> None:
    """Verify config.example.yaml loads and validates successfully."""
    config_file = project_root / "config.example.yaml"
    result = load_config_from_yaml(config_file)
    assert result.is_ok(), f"Failed to load example config: {result.unwrap_err()}"
    config = result.unwrap()
    assert len(config.parties) == 2
    assert config.parties[0].id == "sample_party_one"
    assert "example.org" in config.parties[0].allowed_domains


def test_load_default_parties_config(project_root: Path) -> None:
    """Verify config.yaml containing the 8 NZ political parties loads and validates."""
    config_file = project_root / "config.yaml"
    result = load_config_from_yaml(config_file)
    assert result.is_ok(), f"Failed to load default config.yaml: {result.unwrap_err()}"
    config = result.unwrap()
    assert len(config.parties) == 8
    party_ids = [p.id for p in config.parties]
    assert "national" in party_ids
    assert "labour" in party_ids
    assert "greens" in party_ids
    assert "act" in party_ids
    assert "nz_first" in party_ids
    assert "te_pati_maori" in party_ids
    assert "top" in party_ids
    assert "alcp" in party_ids



def test_load_valid_minimal_dict() -> None:
    """Verify minimal valid dictionary config parses into AppConfig."""
    data = {
        "parties": [
            {
                "id": "act_nz",
                "name": "ACT New Zealand",
                "allowed_domains": ["act.org.nz"],
                "starting_urls": ["https://act.org.nz/policies"],
            }
        ]
    }
    result = load_config_from_dict(data)
    assert result.is_ok()
    config = result.unwrap()
    assert config.parties[0].id == "act_nz"
    assert config.crawler_settings.request_timeout_seconds == 10.0
    assert len(config.exclusions.path_patterns) > 0


def test_file_not_found() -> None:
    """Verify non-existent YAML file path returns Err."""
    result = load_config_from_yaml("non_existent_file.yaml")
    assert result.is_err()
    assert "not found" in result.unwrap_err()


def test_invalid_yaml_syntax(tmp_path: Path) -> None:
    """Verify syntax errors in YAML file return Err."""
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("parties: [unclosed list", encoding="utf-8")
    result = load_config_from_yaml(bad_yaml)
    assert result.is_err()
    assert "Failed to read or parse YAML" in result.unwrap_err()


def test_non_dict_yaml(tmp_path: Path) -> None:
    """Verify YAML that resolves to a list rather than a mapping returns Err."""
    list_yaml = tmp_path / "list.yaml"
    list_yaml.write_text("- item1\n- item2", encoding="utf-8")
    result = load_config_from_yaml(list_yaml)
    assert result.is_err()
    assert "must be a YAML mapping" in result.unwrap_err()


def test_empty_parties_list_rejected() -> None:
    """Verify configuration with no parties fails validation."""
    data = {"parties": []}
    result = load_config_from_dict(data)
    assert result.is_err()
    assert "parties" in result.unwrap_err()


def test_duplicate_party_ids_rejected() -> None:
    """Verify duplicate party IDs are detected and rejected."""
    data = {
        "parties": [
            {
                "id": "labour",
                "name": "Labour Party",
                "allowed_domains": ["labour.org.nz"],
                "starting_urls": ["https://labour.org.nz/our-policies"],
            },
            {
                "id": "labour",
                "name": "Another Labour Party",
                "allowed_domains": ["labour.org.nz"],
                "starting_urls": ["https://labour.org.nz/our-policies"],
            },
        ]
    }
    result = load_config_from_dict(data)
    assert result.is_err()
    assert "Duplicate party ID" in result.unwrap_err()


@pytest.mark.parametrize(
    "invalid_id",
    ["Party One", "party@one", "party!one", "party#1", ""],
)
def test_invalid_party_id_characters(invalid_id: str) -> None:
    """Verify party IDs with whitespace or illegal symbols fail validation."""
    data = {
        "parties": [
            {
                "id": invalid_id,
                "name": "Test Party",
                "allowed_domains": ["example.org"],
                "starting_urls": ["https://example.org/"],
            }
        ]
    }
    result = load_config_from_dict(data)
    assert result.is_err()


def test_invalid_domain_format() -> None:
    """Verify malformed allowed_domains are rejected."""
    data = {
        "parties": [
            {
                "id": "test_party",
                "name": "Test Party",
                "allowed_domains": ["not a domain", "http://example.org"],
                "starting_urls": ["https://example.org/"],
            }
        ]
    }
    result = load_config_from_dict(data)
    assert result.is_err()
    assert "Invalid domain format" in result.unwrap_err()


def test_starting_url_domain_mismatch() -> None:
    """Verify starting URL with domain not in allowed_domains is rejected."""
    data = {
        "parties": [
            {
                "id": "greens",
                "name": "Green Party",
                "allowed_domains": ["greens.org.nz"],
                "starting_urls": ["https://national.org.nz/plan"],
            }
        ]
    }
    result = load_config_from_dict(data)
    assert result.is_err()
    assert "is not in party's allowed_domains" in result.unwrap_err()


def test_unsupported_starting_url_scheme() -> None:
    """Verify non-HTTP/HTTPS schemes in starting URLs are rejected."""
    data = {
        "parties": [
            {
                "id": "test_party",
                "name": "Test Party",
                "allowed_domains": ["example.org"],
                "starting_urls": ["ftp://example.org/policies"],
            }
        ]
    }
    result = load_config_from_dict(data)
    assert result.is_err()
    assert "must use HTTP or HTTPS scheme" in result.unwrap_err()


def test_invalid_crawler_bounds() -> None:
    """Verify boundary checks on crawler configuration options."""
    data = {
        "crawler_settings": {
            "request_timeout_seconds": -5.0,
            "delay_seconds": -1.0,
            "max_retries": 10,
        },
        "parties": [
            {
                "id": "test_party",
                "name": "Test Party",
                "allowed_domains": ["example.org"],
                "starting_urls": ["https://example.org/"],
            }
        ],
    }
    result = load_config_from_dict(data)
    assert result.is_err()
