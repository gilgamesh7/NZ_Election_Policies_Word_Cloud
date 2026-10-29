"""Term frequency and analytical ranking for political policy corpora."""

from collections import Counter
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TermRank:
    """Individual ranked term with score, rank, and source party identifier."""

    party_id: str
    rank: int
    term: str
    score: float
    method: str  # "frequency" or "tfidf"

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_id": self.party_id,
            "rank": self.rank,
            "term": self.term,
            "score": int(self.score) if self.method == "frequency" else round(self.score, 6),
            "method": self.method,
        }


def calculate_term_frequencies(
    tokens: list[str],
    party_id: str,
    top_n: int = 20,
) -> list[TermRank]:
    """Calculate raw term frequencies with deterministic tie-breaking.

    Tie-breaking rule:
    1. Descending by frequency count (-count)
    2. Ascending alphabetically by term (term)

    Handles fewer than 20 terms without empty padding.
    """
    if not tokens:
        return []

    counts = Counter(tokens)
    # Sort deterministically: highest count first; on ties, alphabetical order
    sorted_items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    selected = sorted_items[:top_n]
    return [
        TermRank(
            party_id=party_id,
            rank=idx,
            term=term,
            score=float(count),
            method="frequency",
        )
        for idx, (term, count) in enumerate(selected, start=1)
    ]


def calculate_all_term_frequencies(
    tokens: list[str],
    party_id: str,
) -> list[TermRank]:
    """Calculate complete term frequencies sorted deterministically."""
    if not tokens:
        return []

    counts = Counter(tokens)
    sorted_items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [
        TermRank(
            party_id=party_id,
            rank=idx,
            term=term,
            score=float(count),
            method="frequency",
        )
        for idx, (term, count) in enumerate(sorted_items, start=1)
    ]


def export_ranks_to_csv(ranks: list[TermRank], output_path: Path) -> None:
    """Export ranked terms to a standard CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["rank", "party_id", "term", "score", "method"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rank in ranks:
            writer.writerow(
                {
                    "rank": rank.rank,
                    "party_id": rank.party_id,
                    "term": rank.term,
                    "score": int(rank.score) if rank.method == "frequency" else round(rank.score, 6),
                    "method": rank.method,
                }
            )
