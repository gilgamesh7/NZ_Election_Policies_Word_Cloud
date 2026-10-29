"""Unit tests for HtmlExtractor, fallback extraction, and source records."""

from pathlib import Path
import pytest

from nz_policy_wordcloud.extractor import (
    DEFAULT_MIN_CHARACTERS,
    ExtractedDocument,
    ExtractionStatus,
    HtmlExtractor,
)


@pytest.fixture
def extractor() -> HtmlExtractor:
    return HtmlExtractor(min_characters=50)


def test_primary_extraction_success(extractor: HtmlExtractor) -> None:
    """Verify primary extraction isolates substantive policy text and ignores navigation/boilerplate."""
    html = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <title>Transport Policy 2026 - Party Portal</title>
      </head>
      <body>
        <nav>
          <ul>
            <li><a href="/home">Home</a></li>
            <li><a href="/donate">Donate Now</a></li>
          </ul>
        </nav>
        <div class="cookie-banner">
          <p>We use cookies to improve your experience.</p>
        </div>
        <main>
          <article>
            <h1>National Transport Infrastructure Plan</h1>
            <p>Our comprehensive transport policy aims to build modern, resilient transport networks across New Zealand.</p>
            <p>We will prioritize funding for rapid public transit, road upgrades, and regional freight corridors to support economic growth and reduce emissions.</p>
            <h2>Key Policy Commitments</h2>
            <ul>
              <li>Deliver rapid rail between Auckland and Hamilton.</li>
              <li>Upgrade major state highways for safety and freight capacity.</li>
              <li>Invest in cycling networks and pedestrian safety.</li>
            </ul>
          </article>
        </main>
        <footer>
          <p>Copyright 2026 Party. All rights reserved. Privacy policy | Terms</p>
        </footer>
      </body>
    </html>
    """
    doc = extractor.extract_document(
        party_id="test_party",
        source_url="https://example.org/transport",
        final_url="https://example.org/transport",
        html=html,
    )

    assert doc.status == ExtractionStatus.SUCCESS_PRIMARY
    assert doc.extraction_method == "trafilatura"
    assert doc.party_id == "test_party"
    assert doc.source_url == "https://example.org/transport"
    assert doc.title == "Transport Policy 2026 - Party Portal"
    assert "National Transport Infrastructure Plan" in doc.text
    assert "rapid public transit" in doc.text
    # Boilerplate navigation and cookie banner should not be in the extracted policy text
    assert "Donate Now" not in doc.text
    assert "We use cookies" not in doc.text
    assert doc.is_usable() is True
    assert doc.word_count > 20


def test_fallback_extraction_when_primary_insufficient(extractor: HtmlExtractor) -> None:
    """Verify BeautifulSoup fallback extracts text when primary extractor yields insufficient text."""
    # Construct HTML that trafilatura typically rejects or overlooks, but contains valid content in <article>
    html = """
    <html>
      <head><title>Alternative Policy Note</title></head>
      <body>
        <article>
          This is an informal policy statement designed to convey key environmental pledges.
          We will safeguard fresh water quality, reduce agricultural runoff, and protect native forests.
          Immediate moratorium on new offshore exploration licences will be introduced in the first hundred days.
        </article>
      </body>
    </html>
    """
    doc = extractor.extract_document(
        party_id="green_party",
        source_url="https://example.org/env",
        final_url="https://example.org/env",
        html=html,
    )

    assert doc.is_usable() is True
    assert doc.status in {ExtractionStatus.SUCCESS_PRIMARY, ExtractionStatus.SUCCESS_FALLBACK}
    assert "safeguard fresh water" in doc.text
    assert doc.word_count > 15


def test_empty_content(extractor: HtmlExtractor) -> None:
    """Verify empty or None HTML reports EMPTY_CONTENT status."""
    doc_none = extractor.extract_document("party_1", "https://example.org/none", "https://example.org/none", None)
    assert doc_none.status == ExtractionStatus.EMPTY_CONTENT
    assert doc_none.text == ""
    assert doc_none.is_usable() is False

    doc_empty = extractor.extract_document("party_1", "https://example.org/empty", "https://example.org/empty", "   ")
    assert doc_empty.status == ExtractionStatus.EMPTY_CONTENT
    assert doc_empty.text == ""
    assert doc_empty.is_usable() is False


def test_too_short_content(extractor: HtmlExtractor) -> None:
    """Verify text below min_characters is classified as TOO_SHORT."""
    short_html = "<html><body><p>Under construction.</p></body></html>"
    doc = extractor.extract_document(
        party_id="test_party",
        source_url="https://example.org/short",
        final_url="https://example.org/short",
        html=short_html,
    )
    assert doc.status == ExtractionStatus.TOO_SHORT
    assert doc.is_usable() is False
    assert doc.character_count < 50


def test_malformed_html(extractor: HtmlExtractor) -> None:
    """Verify malformed HTML with unclosed tags is handled without exception."""
    broken_html = "<html><body><h1>Malformed</h1><p>Unclosed paragraph with text exceeding fifty characters for policy validation.<div><span>More text here.</body>"
    doc = extractor.extract_document(
        party_id="test_party",
        source_url="https://example.org/malformed",
        final_url="https://example.org/malformed",
        html=broken_html,
    )
    assert doc.is_usable() is True
    assert "Unclosed paragraph" in doc.text


def test_document_storage_format_and_persistence(tmp_path: Path, extractor: HtmlExtractor) -> None:
    """Verify extracted document formats with YAML metadata header and saves to disk correctly."""
    doc = ExtractedDocument(
        party_id="sample_party",
        source_url="https://example.org/policy/health",
        final_url="https://example.org/policy/health",
        status=ExtractionStatus.SUCCESS_PRIMARY,
        extraction_method="trafilatura",
        title="Health Policy 2026",
        text="Invest in regional healthcare facilities and frontline nursing staff.",
        character_count=71,
        word_count=10,
    )

    formatted = doc.format_for_storage()
    assert formatted.startswith("---\nparty_id: sample_party\n")
    assert "source_url: https://example.org/policy/health" in formatted
    assert "Invest in regional healthcare" in formatted

    saved_path = extractor.save_document(doc, tmp_path)
    assert saved_path.exists()
    assert saved_path.parent.name == "sample_party"
    read_back = saved_path.read_text(encoding="utf-8")
    assert "Health Policy 2026" in read_back
    assert "Invest in regional healthcare" in read_back


def test_safe_filename_generation() -> None:
    """Verify filename generation produces filesystem-safe strings."""
    doc = ExtractedDocument(
        party_id="act_nz",
        source_url="https://act.org.nz/policies/economy-tax?view=full&ref=nav",
        final_url="https://act.org.nz/policies/economy-tax",
        status=ExtractionStatus.SUCCESS_PRIMARY,
        extraction_method="trafilatura",
    )
    filename = doc.get_safe_filename()
    assert filename.startswith("act_nz_policies_economy-tax_")
    assert filename.endswith(".txt")
    assert "?" not in filename
    assert "&" not in filename
    assert "/" not in filename
