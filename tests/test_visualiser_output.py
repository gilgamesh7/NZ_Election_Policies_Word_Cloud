"""Unit tests for Phase 7: Word clouds and output management."""

from pathlib import Path

import pytest

from nz_policy_wordcloud.analysis import TermRank
from nz_policy_wordcloud.crawler import CrawlManifest, PageRecord
from nz_policy_wordcloud.extractor import ExtractedDocument, ExtractionStatus
from nz_policy_wordcloud.output_manager import OutputManager, make_run_directory
from nz_policy_wordcloud.visualiser import (
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    build_wordcloud_filename,
    generate_wordcloud_png,
)


def test_build_wordcloud_filename() -> None:
    """Filename must be deterministic, lowercase, and safe."""
    assert build_wordcloud_filename("ACT", "frequency") == "act_frequency.png"
    assert build_wordcloud_filename("Te Pati Maori", "tfidf") == "te_pati_maori_tfidf.png"
    assert build_wordcloud_filename("Greens", "FREQUENCY") == "greens_frequency.png"


def test_generate_wordcloud_png_success(tmp_path: Path) -> None:
    """Non-empty terms must produce a valid PNG image."""
    ranks = [
        TermRank(term="health", score=10.0, rank=1, party_id="labour", method="frequency"),
        TermRank(term="education", score=8.0, rank=2, party_id="labour", method="frequency"),
        TermRank(term="housing", score=5.0, rank=3, party_id="labour", method="frequency"),
    ]
    out_file = tmp_path / "labour_freq.png"
    saved = generate_wordcloud_png(ranks, out_file, title="Labour Party Frequency")

    assert saved == out_file
    assert out_file.exists()
    assert out_file.stat().st_size > 0

    # Verify PNG header bytes (89 50 4E 47 0D 0A 1A 0A)
    with out_file.open("rb") as f:
        header = f.read(8)
    assert header == b"\x89PNG\r\n\x1a\n"


def test_generate_wordcloud_png_empty_ranks_returns_none(tmp_path: Path) -> None:
    """Empty terms list must not produce an image and return None."""
    out_file = tmp_path / "empty.png"
    saved = generate_wordcloud_png([], out_file)

    assert saved is None
    assert not out_file.exists()


def test_make_run_directory_creates_timestamped_dir(tmp_path: Path) -> None:
    """Run directory must be created under base_dir with run_ prefix."""
    run_dir = make_run_directory(tmp_path)
    assert run_dir.exists()
    assert run_dir.is_dir()
    assert run_dir.name.startswith("run_")


def test_output_manager_manifest_export(tmp_path: Path) -> None:
    """Crawl manifest must be written as CSV with correct columns."""
    manager = OutputManager(tmp_path)
    manifest = CrawlManifest(
        records=[
            PageRecord(
                party_id="act",
                attempted_url="https://www.act.org.nz/policies",
                final_url="https://www.act.org.nz/policies",
                status_code=200,
                is_starting_page=True,
                success=True,
                content_type="text/html",
                content_bytes=1024,
            )
        ]
    )

    out_csv = manager.save_crawl_manifest(manifest)
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8")
    assert "party_id,attempted_url,final_url,status_code" in content
    assert "https://www.act.org.nz/policies" in content


def test_output_manager_manifest_empty(tmp_path: Path) -> None:
    """Empty manifest must produce an empty file without crashing."""
    manager = OutputManager(tmp_path)
    manifest = CrawlManifest()
    out_csv = manager.save_crawl_manifest(manifest)
    assert out_csv.exists()
    assert out_csv.read_text(encoding="utf-8") == ""


def test_output_manager_extracted_documents(tmp_path: Path) -> None:
    """Extracted documents must be saved in run_dir/extracted_text/party_id/."""
    manager = OutputManager(tmp_path)
    doc = ExtractedDocument(
        party_id="greens",
        source_url="https://www.greens.org.nz/climate",
        final_url="https://www.greens.org.nz/climate",
        text="Clean energy and climate action policies for Aotearoa.",
        character_count=55,
        word_count=8,
        status=ExtractionStatus.SUCCESS_PRIMARY,
        extraction_method="trafilatura",
    )

    saved_paths = manager.save_extracted_documents([doc])
    assert len(saved_paths) == 1
    saved_file = saved_paths[0]
    assert saved_file.exists()
    content = saved_file.read_text(encoding="utf-8")
    assert "party_id: greens" in content
    assert "source_url: https://www.greens.org.nz/climate" in content
    assert "Clean energy and climate action policies" in content


def test_output_manager_csv_exports(tmp_path: Path) -> None:
    """Frequency and TF-IDF CSVs must be exported into csv/ subfolder."""
    manager = OutputManager(tmp_path)
    ranks = {
        "party_a": [
            TermRank(party_id="party_a", rank=1, term="economy", score=25.0, method="frequency"),
            TermRank(party_id="party_a", rank=2, term="tax", score=15.0, method="frequency"),
        ]
    }

    freq_top, freq_all = manager.save_frequency_csv(ranks, top_n=1)
    assert freq_top.exists()
    assert freq_all.exists()
    assert "frequency_top20.csv" in str(freq_top)
    assert "frequency_all.csv" in str(freq_all)

    # Top file should contain only rank 1
    top_lines = freq_top.read_text(encoding="utf-8").strip().splitlines()
    assert len(top_lines) == 2  # Header + 1 row
    assert "economy" in top_lines[1]

    # All file should contain both
    all_lines = freq_all.read_text(encoding="utf-8").strip().splitlines()
    assert len(all_lines) == 3  # Header + 2 rows

    tfidf_ranks = {
        "party_a": [
            TermRank(party_id="party_a", rank=1, term="economy", score=0.85, method="tfidf"),
            TermRank(party_id="party_a", rank=2, term="tax", score=0.45, method="tfidf"),
        ]
    }
    tfidf_top, tfidf_all = manager.save_tfidf_csv(tfidf_ranks, top_n=1)
    assert tfidf_top.exists()
    assert tfidf_all.exists()


def test_output_manager_save_wordclouds(tmp_path: Path) -> None:
    """Word clouds should be generated for each party with data."""
    manager = OutputManager(tmp_path)
    freq_ranks = {
        "party_a": [
            TermRank(party_id="party_a", rank=1, term="economy", score=25.0, method="frequency"),
            TermRank(party_id="party_a", rank=2, term="jobs", score=15.0, method="frequency"),
        ],
        "party_empty": [],
    }
    tfidf_ranks = {
        "party_a": [
            TermRank(party_id="party_a", rank=1, term="jobs", score=0.8, method="tfidf"),
            TermRank(party_id="party_a", rank=2, term="economy", score=0.4, method="tfidf"),
        ],
        "party_empty": [],
    }

    saved = manager.save_wordclouds(freq_ranks, tfidf_ranks)
    assert "party_a" in saved
    assert len(saved["party_a"]) == 2  # freq + tfidf
    for p in saved["party_a"]:
        assert p.exists()
        assert p.suffix == ".png"
        assert p.stat().st_size > 0

    assert "party_empty" in saved
    assert len(saved["party_empty"]) == 0  # No clouds generated for empty party


def test_output_manager_save_run_summary(tmp_path: Path) -> None:
    """Run summary JSON must include collection stats and neutrality disclaimer."""
    manager = OutputManager(tmp_path)
    metadata = {
        "parties": ["national", "labour"],
        "total_pages_crawled": 12,
        "total_documents_extracted": 10,
    }

    summary_file = manager.save_run_summary(metadata)
    assert summary_file.exists()
    content = summary_file.read_text(encoding="utf-8")
    assert '"parties": [' in content
    assert '"disclaimer":' in content
    assert "Word clouds and term rankings describe patterns" in content
    assert "generated_at_utc" in content
