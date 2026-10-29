"""Pytest configuration and shared fixtures for nz-policy-wordcloud tests."""

import pytest
from pathlib import Path


@pytest.fixture
def project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent
