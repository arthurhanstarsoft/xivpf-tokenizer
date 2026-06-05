import re

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

_STOP_WORDS: set[str] = set(stopwords.words("english")) | {
    # URL fragments
    "https", "http", "www", "com", "net", "org", "io", "docs", "google",
    # PF noise
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
    "p1", "p2", "p3", "p4",
    "also", "etc",
    # Run descriptors — not strategy signals
    "fresh", "enrage",
    # Noise from partial tokenization of known service names
    "kefka", "bin",
}

_MIN_TOKEN_LEN = 3

# Matches any CJK character (Chinese, Japanese, Korean)
_CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿ｦ-ﾟ]")

_URL_SERVICE_NAMES: dict[str, str] = {
    "raidplan.io": "raidplan",
    "pastebin.com": "pastebin",
    "kefkabin.com": "kefkabin",
    "ff14.toolboxgaming.space": "toolbox",
    "toolboxgaming.space": "toolbox",
    "docs.google.com": "google docs",
    "cdn.discordapp.com": "discord",
    "imgur.com": "imgur",
    "i.imgur.com": "imgur",
}

_URL_PATTERN = re.compile(r"https?://\S+")


def _extract_url_token(url: str) -> str | None:
    """Return a single combined token for a URL, e.g. 'raidplan p8JvSSs1_QKMVX13'.
    Returns just the service name if no plan ID found, or None if unrecognized."""
    match = re.search(r"https?://([^/\s]+)(.*)", url)
    if not match:
        return None
    host = match.group(1).lower().lstrip("www.")  # lowercase host only for matching
    path = match.group(2)                          # preserve original casing for plan ID
    service = _URL_SERVICE_NAMES.get(host)
    if not service:
        return None

    path = re.split(r"[?#]", path)[0]  # no .lower() here
    segments = [s for s in path.split("/") if s and len(s) >= 4]
    if segments:
        plan_id = re.sub(r"[^\w\-]", "", segments[-1])
        if plan_id:
            return f"{service} {plan_id}"

    return service


def _normalize(text: str) -> str:
    """Strip URLs from text (they are handled separately) and normalize."""
    text = text.lower()
    text = _URL_PATTERN.sub(" ", text)
    text = re.sub(r"[\[\](){}|/\\]", " ", text)
    text = re.sub(r"[^\w\s\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(description: str) -> list[str]:
    if not description:
        return []

    # Extract URL tokens first from original text to preserve plan ID casing
    url_tokens = []
    for url_match in _URL_PATTERN.finditer(description):
        token = _extract_url_token(url_match.group(0))
        if token:
            url_tokens.append(token)

    # Tokenize the remaining text normally
    normalized = _normalize(description)
    words = word_tokenize(normalized)
    filtered = [
        w for w in words
        if len(w) >= _MIN_TOKEN_LEN
        and w not in _STOP_WORDS
        and not w.isdigit()
        and not _CJK_RE.search(w)
    ]

    tokens = list(filtered)
    for i in range(len(filtered) - 1):
        tokens.append(f"{filtered[i]} {filtered[i + 1]}")

    # Add URL tokens — they don't participate in bigrams with surrounding words
    tokens.extend(url_tokens)

    return tokens
