KNOWN_STRATEGIES: list[str] = [
    # Common strategy guide authors / names
    "hector",
    "nukemaru",
    "raidplan",
    "zena",
    "braindead",
    "hamkatsu",
    "rinon",
    "akito",
    "lucrezia",
    "uptime",
    "mm2",
    "toxic",
    "poikos",
    "ilya",
    "kobe",
    "mathos",
    "pastebin",
    "toolbox",
    # Descriptive strategy terms
    "static",
    "strat",
    "prog",
    "clear",
    "reclear",
    "farm",
    "speed",
    "no-rush",
    "nour",
]


def extract_keywords(description: str) -> list[str]:
    lower = description.lower()
    return [kw for kw in KNOWN_STRATEGIES if kw in lower]
