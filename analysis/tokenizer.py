import re

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

_STOP_WORDS: set[str] = set(stopwords.words("english")) | {
    # PF noise — carry no strategy signal
    "lf", "lf1m", "lf2m", "lf3m", "lf4m", "lf5m", "lf6m",
    "dc", "na", "eu", "jp", "oce", "ocg",
    "pf", "party", "finder",
    "item", "ilvl", "ilv",
    "prog", "reclear", "clear", "farm",
    "one", "per", "job",
    "must", "please", "know", "knowing",
    "mech", "mechs", "mechanic", "mechanics",
    "fill", "spot", "spots", "exp", "experienced",
    "join", "run", "runs", "run",
    "yes", "not", "none",
    "week", "weekly",
    "new", "old",
    "alt", "main",
    "use", "using",
    "want", "need",
    "raid", "boss",
    "p1", "p2", "p3", "p4",   # floor labels often noise
    "also", "etc",
}

_MIN_TOKEN_LEN = 3


def _normalize(text: str) -> str:
    text = text.lower()
    # Replace brackets/parens with space (strategy names often appear in [brackets])
    text = re.sub(r"[\[\](){}|/\\]", " ", text)
    # Strip punctuation except hyphens and apostrophes
    text = re.sub(r"[^\w\s\-]", " ", text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


def tokenize(description: str) -> list[str]:
    if not description:
        return []

    normalized = _normalize(description)
    words = word_tokenize(normalized)

    filtered = [
        w for w in words
        if len(w) >= _MIN_TOKEN_LEN and w not in _STOP_WORDS and not w.isdigit()
    ]

    # Unigrams
    tokens = list(filtered)

    # Bigrams — slide over filtered words
    for i in range(len(filtered) - 1):
        bigram = f"{filtered[i]} {filtered[i + 1]}"
        tokens.append(bigram)

    return tokens
