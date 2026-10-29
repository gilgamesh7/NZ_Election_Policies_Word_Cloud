"""Unit tests for TextCleaner and tokenisation."""

import pytest

from nz_policy_wordcloud.cleaner import TextCleaner


def test_standard_stop_word_removal() -> None:
    """Verify common English stop words are removed while content words remain."""
    cleaner = TextCleaner()
    text = "The government should invest in our public hospitals and healthcare systems for the future."
    tokens = cleaner.clean_and_tokenize(text)

    # Stop words should be gone
    assert "the" not in tokens
    assert "should" not in tokens
    assert "in" not in tokens
    assert "our" not in tokens
    assert "and" not in tokens
    assert "for" not in tokens

    # Meaningful content words must be retained
    assert "government" in tokens
    assert "invest" in tokens
    assert "public" in tokens
    assert "hospitals" in tokens
    assert "healthcare" in tokens
    assert "systems" in tokens
    assert "future" in tokens


def test_custom_exclusions() -> None:
    """Verify user-configured stop words are excluded alongside standard stop words."""
    cleaner = TextCleaner(custom_stop_words=["policy", "read", "click", "page"])
    text = "Please read our policy on this page and click for more details regarding transport."
    tokens = cleaner.clean_and_tokenize(text)

    assert "policy" not in tokens
    assert "read" not in tokens
    assert "click" not in tokens
    assert "page" not in tokens
    assert "transport" in tokens
    assert "details" in tokens


def test_te_reo_maori_macrons_preserved() -> None:
    """Verify Māori words with macron vowels (ā, ē, ī, ō, ū) are preserved as valid tokens."""
    cleaner = TextCleaner()
    text = "Supporting whānau, protecting māori heritage, and advancing hauora for all communities."
    tokens = cleaner.clean_and_tokenize(text)

    assert "whānau" in tokens
    assert "māori" in tokens
    assert "hauora" in tokens
    assert "protecting" in tokens
    assert "heritage" in tokens
    assert "communities" in tokens


def test_short_tokens_filtered_out() -> None:
    """Verify tokens with fewer than 3 characters are excluded."""
    cleaner = TextCleaner()
    text = "He is on a bus to go by me at 9am."
    tokens = cleaner.clean_and_tokenize(text)

    # 1- and 2-letter tokens must be omitted
    for token in tokens:
        assert len(token) >= 3
    assert "bus" in tokens


def test_empty_and_whitespace_input() -> None:
    """Verify empty or purely whitespace/symbol strings return empty token lists."""
    cleaner = TextCleaner()
    assert cleaner.clean_and_tokenize("") == []
    assert cleaner.clean_and_tokenize("   \n\t   ") == []
    assert cleaner.clean_and_tokenize("12345 67890 !@#$%^&*()") == []
