# Normalizes duty names returned by the xivpf API to a canonical name.
# Use this when xivpf fixes a duty but uses a slightly different name than our override,
# so historical token data stays merged under one name.
# Keys are case-insensitive substrings matched against the API-returned name.
DUTY_NAME_NORMALIZATIONS: dict[str, str] = {
    "dancing mad": "Dancing Mad (Ultimate)",
}


# Overrides for duties that xivpf's API doesn't recognize yet (duty_info: null).
# Matched top-to-bottom; first match wins.
# Add entries here whenever a new fight releases before xivpf updates their database.
DUTY_OVERRIDES: list[dict] = [
    {
        "name": "Dancing Mad (Ultimate)",
        "category": "HighEndDuty",
        # Matched if ANY of these keywords appear in the description (case-insensitive).
        # When a new Savage/Ultimate releases with duty_info=null, add a new entry
        # ABOVE this one with its own keywords so it takes priority.
        "description_contains": [
            # DMU-exclusive mechanics
            "arrows", "arrow", "graven", "forsaken", "merry", "telepo", "テレポ",
            # DMU-exclusive strategy names/guides
            "toxic", "xolo", "kff", "ぬけまる", "nukemaru",
            "yarn", "ヤーン", "x13", "kefkabin",
            # Phase markers
            "p1", "p2", "p3", "p4",
            # JP farming language specific to this tier
            "weapon farm", "羽",
        ],
    },
]

# Aliases for bot commands — maps any alias to the exact duty_name_en stored in the DB.
# Case-insensitive. Add your own shortcuts here.
DUTY_ALIASES: dict[str, str] = {
    # Dancing Mad (Ultimate)
    "dmu":          "Dancing Mad (Ultimate)",
    "dm":           "Dancing Mad (Ultimate)",
    "umad":         "Dancing Mad (Ultimate)",
    "dancing mad":  "Dancing Mad (Ultimate)",

    # AAC Heavyweight (current Savage tier)
    "m1s":          "AAC Heavyweight M1 (Savage)",
    "m1":           "AAC Heavyweight M1 (Savage)",
    "m2s":          "AAC Heavyweight M2 (Savage)",
    "m2":           "AAC Heavyweight M2 (Savage)",
    "m3s":          "AAC Heavyweight M3 (Savage)",
    "m3":           "AAC Heavyweight M3 (Savage)",
    "m4s":          "AAC Heavyweight M4 (Savage)",
    "m4":           "AAC Heavyweight M4 (Savage)",

    # Ultimates
    "fru":          "Futures Rewritten (Ultimate)",
    "dsr":          "Dragonsong's Reprise (Ultimate)",
    "tea":          "The Epic of Alexander (Ultimate)",
    "ucob":         "The Unending Coil of Bahamut (Ultimate)",
    "uwu":          "The Weapon's Refrain (Ultimate)",
    "top":          "The Omega Protocol (Ultimate)",

    # Extremes
    "ne":           "The Minstrel's Ballad: Necron's Embrace",
    "necron":       "The Minstrel's Ballad: Necron's Embrace",
    "sb":           "The Minstrel's Ballad: Sphene's Burden",
    "sphene":       "The Minstrel's Ballad: Sphene's Burden",
    "wld":          "Worqor Lar Dor (Extreme)",
    "recollection": "Recollection (Extreme)",
    "hon":          "Hell on Rails (Extreme)",
}


def resolve_duty(name: str) -> str:
    """Resolve an alias or partial name to the full duty name."""
    return DUTY_ALIASES.get(name.lower().strip(), name.strip())
