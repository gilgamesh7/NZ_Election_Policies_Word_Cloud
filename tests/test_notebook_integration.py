"""Test notebook structure, validity, and execution against local mock fixtures."""

import json
from pathlib import Path

import nbformat
import pytest

from nz_policy_wordcloud.crawler import CrawlManifest, PageRecord
from nz_policy_wordcloud.extractor import HtmlExtractor
from nz_policy_wordcloud.cleaner import TextCleaner
from nz_policy_wordcloud.analysis import calculate_term_frequencies
from nz_policy_wordcloud.tfidf import calculate_tfidf_ranks
from nz_policy_wordcloud.output_manager import OutputManager, make_run_directory


def test_notebook_file_exists_and_is_valid_json() -> None:
    """Notebook file must exist and be valid Jupyter Notebook format (nbformat v4)."""
    notebook_path = Path("notebooks/nz_policy_wordcloud.ipynb")
    assert notebook_path.exists()
    
    with notebook_path.open("r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    assert nb.nbformat == 4
    assert len(nb.cells) > 0


def test_notebook_cells_structure_and_disclaimers() -> None:
    """Notebook must have purpose-labelled cells and neutral analytical disclaimers."""
    notebook_path = Path("notebooks/nz_policy_wordcloud.ipynb")
    with notebook_path.open("r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    markdown_cells = [c for c in nb.cells if c.cell_type == "markdown"]
    code_cells = [c for c in nb.cells if c.cell_type == "code"]

    assert len(markdown_cells) >= 8
    assert len(code_cells) >= 8

    # Verify first markdown cell contains required disclaimers
    first_md = markdown_cells[0].source
    assert "Analytical Neutrality & Disclaimer" in first_md
    assert "Frequency" in first_md
    assert "TF-IDF" in first_md
    assert "policy quality" in first_md


def test_pipeline_dry_run_with_fixtures(tmp_path: Path) -> None:
    """Verify that every step called by the notebook runs cleanly end-to-end on local fixtures."""
    # Step 1 & 2: Output manager and directory
    run_dir = make_run_directory(base_dir=tmp_path)
    manager = OutputManager(run_dir)
    assert run_dir.exists()

    # Step 3 & 4: Mocked crawl manifest
    manifest = CrawlManifest(
        records=[
            PageRecord(
                party_id="greens",
                attempted_url="https://greens.org.nz/climate",
                final_url="https://greens.org.nz/climate",
                status_code=200,
                is_starting_page=True,
                success=True,
                content_type="text/html",
                content_bytes=400,
                html="""
                <html><body>
                <main>
                    <h1>Green Climate and Transport Action</h1>
                    <p>Clean renewable energy, sustainable transport networks, and environmental protection.</p>
                </main>
                </body></html>
                """,
            ),
            PageRecord(
                party_id="act",
                attempted_url="https://act.org.nz/economy",
                final_url="https://act.org.nz/economy",
                status_code=200,
                is_starting_page=True,
                success=True,
                content_type="text/html",
                content_bytes=400,
                html="""
                <html><body>
                <main>
                    <h1>Economic Growth and Productivity</h1>
                    <p>Lower tax rates, reduced regulation, and economic growth for all businesses.</p>
                </main>
                </body></html>
                """,
            ),
        ]
    )
    manifest_csv = manager.save_crawl_manifest(manifest)
    assert manifest_csv.exists()

    # Step 5: HTML Text Extraction
    extractor = HtmlExtractor()
    documents = extractor.extract_from_manifest(manifest)
    assert len(documents) == 2
    saved_doc_paths = manager.save_extracted_documents(documents, extractor)
    assert len(saved_doc_paths) == 2

    # Step 6: Cleaning and tokenisation
    cleaner = TextCleaner()
    party_tokens = {
        "greens": cleaner.tokenize(" ".join(d.text for d in documents if d.party_id == "greens")),
        "act": cleaner.tokenize(" ".join(d.text for d in documents if d.party_id == "act")),
    }
    party_clean_texts = {
        "greens": cleaner.clean_text(" ".join(d.text for d in documents if d.party_id == "greens")),
        "act": cleaner.clean_text(" ".join(d.text for d in documents if d.party_id == "act")),
    }

    assert "renewable" in party_tokens["greens"]
    assert "tax" in party_tokens["act"]

    # Step 7: Frequency and TF-IDF
    frequency_ranks = {
        pid: calculate_term_frequencies(tokens, party_id=pid, top_n=20)
        for pid, tokens in party_tokens.items()
    }
    top_f, all_f = manager.save_frequency_csv(frequency_ranks, top_n=20)
    assert top_f.exists()
    assert all_f.exists()

    tfidf_ranks = calculate_tfidf_ranks(party_clean_texts, top_n=20)
    top_t, all_t = manager.save_tfidf_csv(tfidf_ranks, top_n=20)
    assert top_t.exists()
    assert all_t.exists()

    # Step 8: Word Clouds
    saved_clouds = manager.save_wordclouds(frequency_ranks, tfidf_ranks)
    assert "greens" in saved_clouds
    assert len(saved_clouds["greens"]) == 2
    assert "act" in saved_clouds
    assert len(saved_clouds["act"]) == 2

    # Step 9: Run Summary
    summary_path = manager.save_run_summary(
        {
            "run_dir": str(run_dir),
            "documents_count": len(documents),
        }
    )
    assert summary_path.exists()
