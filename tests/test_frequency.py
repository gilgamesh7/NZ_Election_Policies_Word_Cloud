"""Unit tests for term frequency calculation, deterministic ranking, and CSV export."""

import csv
from pathlib import Path
import pytest

from nz_policy_wordcloud.analysis import (
    TermRank,
    calculate_all_term_frequencies,
    calculate_term_frequencies,
    export_ranks_to_csv,
)


def test_frequency_calculation_and_counts() -> None:
    """Verify term counts and rankings correspond to input token frequencies."""
    tokens = ["health", "health", "health", "housing", "housing", "transport"]
    ranks = calculate_term_frequencies(tokens, party_id="labour", top_n=20)

    assert len(ranks) == 3
    assert ranks[0].term == "health"
    assert ranks[0].score == 3.0
    assert ranks[0].rank == 1
    assert ranks[0].party_id == "labour"
    assert ranks[0].method == "frequency"

    assert ranks[1].term == "housing"
    assert ranks[1].score == 2.0
    assert ranks[1].rank == 2

    assert ranks[2].term == "transport"
    assert ranks[2].score == 1.0
    assert ranks[2].rank == 3


def test_deterministic_tie_breaking() -> None:
    """Verify that ties in frequency are broken alphabetically by term."""
    # "water", "apple", "zebra", "mountain" all have count 2
    tokens = [
        "zebra", "water", "apple", "mountain",
        "zebra", "water", "apple", "mountain",
    ]
    ranks = calculate_term_frequencies(tokens, party_id="greens", top_n=20)

    # All counts are 2, so order MUST be alphabetical: apple, mountain, water, zebra
    terms = [r.term for r in ranks]
    assert terms == ["apple", "mountain", "water", "zebra"]
    assert [r.rank for r in ranks] == [1, 2, 3, 4]


def test_top_20_limit() -> None:
    """Verify that when more than 20 unique terms exist, exactly the top 20 are returned."""
    # Generate 30 unique terms with varying frequencies
    tokens: list[str] = []
    for i in range(1, 31):
        word = f"term{i:02d}"
        tokens.extend([word] * i)  # term30 appears 30 times, term01 appears 1 time

    ranks = calculate_term_frequencies(tokens, party_id="national", top_n=20)
    assert len(ranks) == 20
    assert ranks[0].term == "term30"
    assert ranks[0].score == 30.0
    assert ranks[0].rank == 1
    assert ranks[19].term == "term11"
    assert ranks[19].score == 11.0
    assert ranks[19].rank == 20


def test_fewer_than_20_terms_without_padding() -> None:
    """Verify that fewer than 20 terms returns exactly the available count without padding."""
    tokens = ["economy", "jobs", "tax"]
    ranks = calculate_term_frequencies(tokens, party_id="act", top_n=20)
    assert len(ranks) == 3
    for r in ranks:
        assert r.term is not None and r.term != ""
        assert r.score > 0


def test_empty_tokens_handling() -> None:
    """Verify empty token input returns empty list."""
    assert calculate_term_frequencies([], party_id="top", top_n=20) == []
    assert calculate_all_term_frequencies([], party_id="top") == []


def test_export_ranks_to_csv(tmp_path: Path) -> None:
    """Verify CSV export formats headers, fields, and values accurately."""
    ranks = [
        TermRank(party_id="nz_first", rank=1, term="regions", score=15.0, method="frequency"),
        TermRank(party_id="nz_first", rank=2, term="infrastructure", score=10.0, method="frequency"),
    ]
    csv_file = tmp_path / "frequency_top20.csv"
    export_ranks_to_csv(ranks, csv_file)

    assert csv_file.exists()
    with csv_file.open(encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0] == {
            "rank": "1",
            "party_id": "nz_first",
            "term": "regions",
            "score": "15",
            "method": "frequency",
        }
        assert reader[1] == {
            "rank": "2",
            "party_id": "nz_first",
            "term": "infrastructure",
            "score": "10",
            "method": "frequency",
        }
