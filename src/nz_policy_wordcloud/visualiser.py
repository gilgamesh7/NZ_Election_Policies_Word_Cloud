"""Word cloud image generation from ranked term lists."""

from pathlib import Path
from typing import Final

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — no display required
import matplotlib.pyplot as plt
from wordcloud import WordCloud

from nz_policy_wordcloud.analysis import TermRank

# Consistent image dimensions for all word clouds
IMAGE_WIDTH: Final[int] = 1200
IMAGE_HEIGHT: Final[int] = 800
IMAGE_DPI: Final[int] = 150
IMAGE_BACKGROUND: Final[str] = "white"
IMAGE_COLORMAP: Final[str] = "viridis"
MAX_FONT_SIZE: Final[int] = 200
MAX_WORDS: Final[int] = 200  # WordCloud internal cap, actual cap is top_n from analysis


def _build_word_frequencies(ranks: list[TermRank]) -> dict[str, float]:
    """Convert TermRank list to the {word: weight} dict required by WordCloud."""
    return {r.term: r.score for r in ranks}


def generate_wordcloud_png(
    ranks: list[TermRank],
    output_path: Path,
    title: str | None = None,
) -> Path | None:
    """Generate and save a PNG word cloud from a list of ranked terms.

    Args:
        ranks: Ranked terms with scores. Must be non-empty for an image to be produced.
        output_path: Full path including filename where the PNG will be written.
        title: Optional subtitle drawn below the word cloud image.

    Returns:
        The saved Path on success, or None if ranks is empty.
    """
    if not ranks:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)

    frequencies = _build_word_frequencies(ranks)

    wc = WordCloud(
        width=IMAGE_WIDTH,
        height=IMAGE_HEIGHT,
        background_color=IMAGE_BACKGROUND,
        colormap=IMAGE_COLORMAP,
        max_font_size=MAX_FONT_SIZE,
        max_words=MAX_WORDS,
        prefer_horizontal=0.9,
    ).generate_from_frequencies(frequencies)

    fig, ax = plt.subplots(figsize=(IMAGE_WIDTH / IMAGE_DPI, IMAGE_HEIGHT / IMAGE_DPI), dpi=IMAGE_DPI)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")

    if title:
        fig.text(
            0.5, 0.01, title,
            ha="center", va="bottom",
            fontsize=9, color="grey",
            wrap=True,
        )

    plt.tight_layout(pad=0)
    fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches="tight")
    plt.close(fig)

    return output_path


def build_wordcloud_filename(party_id: str, method: str) -> str:
    """Return a deterministic, filesystem-safe PNG filename for a party + method pair."""
    safe_party = party_id.replace(" ", "_").lower()
    safe_method = method.lower()
    return f"{safe_party}_{safe_method}.png"
