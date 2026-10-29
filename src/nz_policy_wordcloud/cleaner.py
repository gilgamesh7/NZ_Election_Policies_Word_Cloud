"""Text normalisation, Māori macron-aware tokenisation, and stop-word filtering."""

from collections.abc import Iterable
import re
import unicodedata

# Standard English stop words (articles, prepositions, pronouns, common verbs, auxiliary terms)
STANDARD_STOP_WORDS: frozenset[str] = frozenset(
    {
        "about", "above", "after", "again", "against", "all", "almost", "also", "although",
        "always", "among", "amongst", "and", "another", "any", "anybody", "anyhow", "anyone",
        "anything", "anyway", "anywhere", "are", "aren", "around", "became", "because",
        "become", "becomes", "becoming", "been", "before", "beforehand", "behind", "being",
        "below", "beside", "besides", "between", "beyond", "both", "but", "cannot", "could",
        "couldn", "did", "didn", "does", "doesn", "doing", "don", "done", "down", "during",
        "each", "either", "else", "elsewhere", "enough", "etc", "even", "ever", "every",
        "everybody", "everyone", "everything", "everywhere", "few", "first", "for", "from",
        "further", "had", "hadn", "has", "hasn", "have", "haven", "having", "her", "here",
        "herein", "hereupon", "hers", "herself", "him", "himself", "his", "how", "however",
        "hundred", "into", "its", "itself", "just", "last", "latter", "latterly", "least",
        "less", "let", "like", "many", "may", "maybe", "meantime", "meanwhile", "might",
        "more", "moreover", "most", "mostly", "much", "must", "myself", "namely", "neither",
        "never", "nevertheless", "next", "nobody", "none", "noone", "nor", "not", "nothing",
        "now", "nowhere", "off", "often", "once", "one", "only", "onto", "other", "others",
        "otherwise", "our", "ours", "ourselves", "out", "over", "own", "per", "perhaps",
        "please", "quite", "rather", "really", "same", "say", "second", "see", "seem",
        "seemed", "seeming", "seems", "several", "she", "should", "shouldn", "since",
        "some", "somebody", "somehow", "someone", "something", "sometime", "sometimes",
        "somewhere", "still", "such", "than", "that", "the", "their", "theirs", "them",
        "themselves", "then", "thence", "there", "thereafter", "thereby", "therefore",
        "therein", "thereupon", "these", "they", "this", "those", "though", "three",
        "through", "throughout", "thru", "thus", "together", "too", "toward", "towards",
        "under", "until", "upon", "used", "using", "very", "via", "was", "wasn", "well",
        "were", "weren", "what", "whatever", "when", "whence", "whenever", "where",
        "whereafter", "whereas", "whereby", "wherein", "whereupon", "wherever", "whether",
        "which", "while", "whither", "who", "whoever", "whole", "whom", "whose", "why",
        "will", "with", "within", "without", "won", "would", "wouldn", "yet", "you",
        "your", "yours", "yourself", "yourselves",
    }
)

# Token pattern: at least 3 letters, explicitly supporting Te Reo Māori vowels with macrons (ā, ē, ī, ō, ū)
TOKEN_PATTERN = re.compile(r"\b[a-z\u0101\u0113\u012b\u014d\u016b]{3,}\b")


class TextCleaner:
    """Normalises text and produces filtered token streams."""

    def __init__(self, custom_stop_words: Iterable[str] | None = None) -> None:
        self.stop_words: set[str] = set(STANDARD_STOP_WORDS)
        if custom_stop_words:
            for word in custom_stop_words:
                clean_w = word.strip().lower()
                if clean_w:
                    self.stop_words.add(clean_w)

    def clean_and_tokenize(self, text: str) -> list[str]:
        """Normalise Unicode, lowercase, and tokenize text while filtering stop words."""
        if not text:
            return []

        # Normalise Unicode characters to NFKC form (resolves composite characters and symbols)
        normalized = unicodedata.normalize("NFKC", text).lower()

        # Extract tokens matching length and alphabet requirements
        tokens = TOKEN_PATTERN.findall(normalized)

        # Filter out stop words
        return [t for t in tokens if t not in self.stop_words]

    def tokenize(self, text: str) -> list[str]:
        """Alias for clean_and_tokenize."""
        return self.clean_and_tokenize(text)

    def clean_text(self, text: str) -> str:
        """Return cleaned text as a whitespace-joined string of filtered tokens."""
        return " ".join(self.clean_and_tokenize(text))
