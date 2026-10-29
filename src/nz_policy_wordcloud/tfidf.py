"""TF-IDF analysis across multiple party corpora.

TF-IDF (Term Frequency–Inverse Document Frequency) highlights terms that are
relatively distinctive to a party's corpus compared with the full set of party
corpora included in a run. A high TF-IDF score does NOT imply policy importance,
truth, intent, or outcomes. Results change when the included set of parties changes.
"""

from typing import Final

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from nz_policy_wordcloud.analysis import TermRank

# Documented vectorizer settings for reproducibility
_SUBLINEAR_TF: Final[bool] = True   # log(1 + tf) dampens very common term counts
_SMOOTH_IDF: Final[bool] = True     # prevents zero-division on single-party terms
_MIN_DF: Final[int] = 1             # include terms appearing in ≥1 document


def calculate_tfidf_ranks(
    party_texts: dict[str, str],
    top_n: int = 20,
) -> dict[str, list[TermRank]]:
    """Compute per-party TF-IDF rankings across the full set of supplied party texts.

    Args:
        party_texts: Mapping of party_id → aggregated cleaned text for that party.
                     Each value is a single document representing the party's corpus.
        top_n: Maximum number of ranked terms to return per party (default 20).

    Returns:
        Mapping of party_id → list of TermRank sorted by TF-IDF score descending,
        then term alphabetically ascending on ties.

    Notes:
        - Results depend on which parties are included; adding or removing a party
          changes every party's relative scores.
        - Parties with empty text are omitted from vectorization and return an empty list.
        - When only one party has text, IDF becomes uniform (all scores equal 1.0).
    """
    # Filter out parties with no usable text
    valid_parties: dict[str, str] = {
        pid: text.strip() for pid, text in party_texts.items() if text and text.strip()
    }

    if not valid_parties:
        return {pid: [] for pid in party_texts}

    party_ids = list(valid_parties.keys())
    documents = [valid_parties[pid] for pid in party_ids]

    vectorizer = TfidfVectorizer(
        sublinear_tf=_SUBLINEAR_TF,
        smooth_idf=_SMOOTH_IDF,
        min_df=_MIN_DF,
        token_pattern=r"[a-z\u0101\u0113\u012b\u014d\u016b]{3,}",
    )

    tfidf_matrix = vectorizer.fit_transform(documents)
    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()

    result: dict[str, list[TermRank]] = {}

    for doc_idx, party_id in enumerate(party_ids):
        row = tfidf_matrix[doc_idx]
        # Convert sparse row to dense 1-D array
        scores: np.ndarray = np.asarray(row.todense()).ravel()

        # Pair terms with scores and filter zero-score terms
        term_scores = [
            (feature_names[i], float(scores[i]))
            for i in range(len(feature_names))
            if scores[i] > 0.0
        ]

        # Deterministic sort: descending score, then ascending term on ties
        term_scores.sort(key=lambda item: (-item[1], item[0]))

        selected = term_scores[:top_n]
        result[party_id] = [
            TermRank(
                party_id=party_id,
                rank=rank_idx,
                term=term,
                score=score,
                method="tfidf",
            )
            for rank_idx, (term, score) in enumerate(selected, start=1)
        ]

    # Parties with no text get empty lists
    for pid in party_texts:
        if pid not in result:
            result[pid] = []

    return result
