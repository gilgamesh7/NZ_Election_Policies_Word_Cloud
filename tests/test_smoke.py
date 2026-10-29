"""Smoke tests verifying package structure and runtime dependencies."""

import sys
import nz_policy_wordcloud


def test_package_import() -> None:
    """Verify package imports correctly and exposes expected version."""
    assert nz_policy_wordcloud.__version__ == "0.1.0"


def test_python_version() -> None:
    """Verify Python runtime meets the >= 3.14 requirement."""
    assert sys.version_info >= (3, 14)


def test_core_dependencies_importable() -> None:
    """Verify primary third-party libraries import cleanly in the virtual environment."""
    import bs4  # noqa: F401
    import httpx  # noqa: F401
    import pydantic  # noqa: F401
    import result  # noqa: F401
    import sklearn  # noqa: F401
    import trafilatura  # noqa: F401
    import wordcloud  # noqa: F401
    import yaml  # noqa: F401

    assert result.Ok(1).is_ok()
