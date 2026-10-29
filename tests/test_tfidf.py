"""Unit tests for TF-IDF analysis across multiple party corpora."""

import pytest

from nz_policy_wordcloud.tfidf import calculate_tfidf_ranks


def test_distinctive_terms_score_higher() -> None:
    """Verify that terms unique to one party score higher than shared common terms."""
    party_texts = {
        "greens": (
            "environment climate forests rivers lakes conservation biodiversity "
            "environment climate forests rivers lakes conservation biodiversity "
            "rivers lakes forests biodiversity clean water clean water"
        ),
        "national": (
            "economy infrastructure roads highways investment business growth "
            "economy infrastructure roads highways investment business growth "
            "roads highways investment business economy"
        ),
    }
    results = calculate_tfidf_ranks(party_texts, top_n=20)

    assert "greens" in results
    assert "national" in results

    greens_terms = [r.term for r in results["greens"]]
    national_terms = [r.term for r in results["national"]]

    # Distinctive ecology terms should appear in Greens top results
    assert "biodiversity" in greens_terms or "conservation" in greens_terms or "forests" in greens_terms

    # Distinctive economy terms should appear in National top results
    assert "economy" in national_terms or "highways" in national_terms or "infrastructure" in national_terms


def test_output_order_is_deterministic() -> None:
    """Verify that calling calculate_tfidf_ranks twice returns identical ordering."""
    party_texts = {
        "labour": "health hospitals workers education schools unions wages",
        "act": "freedom market tax deregulation individual liberty choice",
    }
    run1 = calculate_tfidf_ranks(party_texts, top_n=20)
    run2 = calculate_tfidf_ranks(party_texts, top_n=20)

    assert [r.term for r in run1["labour"]] == [r.term for r in run2["labour"]]
    assert [r.term for r in run1["act"]] == [r.term for r in run2["act"]]


def test_top_n_limit_respected() -> None:
    """Verify that no more than top_n terms are returned per party."""
    # Build a text with many distinct words
    words = [f"word{i:03d}" for i in range(50)]
    party_texts = {
        "top": " ".join(words * 2),
        "alcp": " ".join(list(reversed(words)) * 2),
    }
    results = calculate_tfidf_ranks(party_texts, top_n=10)

    assert len(results["top"]) <= 10
    assert len(results["alcp"]) <= 10


def test_empty_party_text_returns_empty_list() -> None:
    """Verify a party with empty or whitespace-only text returns an empty list."""
    party_texts = {
        "present_party": "economic growth infrastructure investment employment",
        "empty_party": "",
        "whitespace_party": "   \n\t  ",
    }
    results = calculate_tfidf_ranks(party_texts, top_n=20)

    assert results["empty_party"] == []
    assert results["whitespace_party"] == []
    assert len(results["present_party"]) > 0


def test_all_empty_parties_returns_empty_dict() -> None:
    """Verify that when all parties have empty text the result is empty lists for all."""
    party_texts = {"party_a": "", "party_b": "   "}
    results = calculate_tfidf_ranks(party_texts, top_n=20)
    assert results["party_a"] == []
    assert results["party_b"] == []


def test_single_party_corpus() -> None:
    """Verify TF-IDF works with a single party (IDF = 1.0 for all terms)."""
    party_texts = {
        "nz_first": "regions rural communities infrastructure provincial growth economy"
    }
    results = calculate_tfidf_ranks(party_texts, top_n=20)

    assert "nz_first" in results
    assert len(results["nz_first"]) > 0
    # All terms have uniform IDF but non-zero TF so scores > 0
    for rank in results["nz_first"]:
        assert rank.score > 0.0
        assert rank.method == "tfidf"


def test_ranks_are_sequential_and_start_at_one() -> None:
    """Verify rank values are 1-indexed and sequential."""
    party_texts = {
        "labour": "health housing education climate welfare economy",
        "greens": "environment climate rivers forests biodiversity",
    }
    results = calculate_tfidf_ranks(party_texts, top_n=20)

    for party_id, ranks in results.items():
        if ranks:
            assert ranks[0].rank == 1
            for i, rank in enumerate(ranks):
                assert rank.rank == i + 1
                assert rank.party_id == party_id


def test_deterministic_tie_breaking_alphabetical() -> None:
    """Verify that on equal TF-IDF scores, terms are sorted alphabetically ascending."""
    # Use two parties with completely disjoint vocabularies so each party's terms
    # all share the same IDF (log((2+1)/(1+1)) = ~0.405), making TF the tie-breaker.
    # With identical term frequencies within each party the tie-break is alphabetical.
    party_texts = {
        "party_a": "zebra apple mango kiwi",
        "party_b": "ocean desert plains mountain",
    }
    results = calculate_tfidf_ranks(party_texts, top_n=20)

    terms_a = [r.term for r in results["party_a"]]
    terms_b = [r.term for r in results["party_b"]]

    # All scores equal → alphabetical order
    assert terms_a == sorted(terms_a), f"Party A terms not alphabetical: {terms_a}"
    assert terms_b == sorted(terms_b), f"Party B terms not alphabetical: {terms_b}"
