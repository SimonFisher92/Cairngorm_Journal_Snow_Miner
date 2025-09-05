import regex as re

# Optional regex matching if GPT doesnt do well
SNOW_TERMS = [
    # core
    "snow", "snowfall", "snowing", "snowed", "powder", "spindrift", "windslab",
    "drift", "drifts", "cornice", "cornices", "neve", "névé", "firn", "ice",
    "verglas", "hardpack", "hard-packed", "consolidated",
    # conditions
    "deep", "waist-deep", "knee-deep", "banked", "banked-out", "loaded",
    "cover", "good cover", "full cover", "banked out",
    # state changes
    "thaw", "thawing", "melt", "melted", "melting", "gone", "disappeared",
    "slushy", "patchy", "none", "bare",
    # events
    "avalanche", "avalanched", "avalanches", "sluff", "sluffs", "slough",
    # scottish/generic winter terms
    "gully", "gullies", "coire", "corrie", "coire an t-sneachda", "sneachda",
    "alpine", "winter", "rim(e)", "graupel", "sleet", "blizzard", "storm snow",
    "spindrift", "windpacked"
]

# Phrases/patterns with scores. Highest match wins.
# 0 (negative) → 5 (very positive). "avalanche" is set high as requested.
SCORE_PATTERNS = [
    (5, r"\b(waist[- ]deep|knee[- ]deep|very deep|superb powder|powder day|avalanche(?:d)?|avalanches?)\b"),
    (4, r"\b(deep|loaded|banked(?:[- ]out)?|good cover|full cover|excellent cover|plenty of snow|drifts?)\b"),
    (3, r"\b(snow(?:fall|ing|ed)?|neve|névé|firn|cornices?|windslab|hardpack|consolidated|spindrift|ice)\b"),
    (2, r"\b(patchy|slushy|thin cover|verglas|frost)\b"),
    (1, r"\b(thaw(?:ing)?|diminish(?:ing|ed)|retreat(?:ing)?|going fast|going)\b"),
    (0, r"\b(melt(?:ed|ing)?|none|bare|gone|disappeared|clear of snow|snowless)\b"),
]

SCORE_REGEXES = [(score, re.compile(pattern, flags=re.IGNORECASE)) for score, pattern in SCORE_PATTERNS]

# General snow entity detection patterns (broad net). These are used to tag the "entity" value.
ENTITY_PATTERNS = [
    r"\b(powder|spindrift|windslab|drifts?|cornices?|neve|névé|firn|ice|verglas)\b",
    r"\b(thaw(?:ing)?|melt(?:ed|ing)?|slush(?:y)?|patchy|none|bare|gone|disappeared)\b",
    r"\b(snow(?:fall|ing|ed)?|cover|deep|loaded|banked(?:[- ]out)?)\b",
    r"\b(avalanche(?:d)?|avalanches?|sluffs?|slough)\b",
    r"\b(gully|gullies|coire(?:\s+an\s+t-sneachda)?|corrie|sneachda)\b",
]

ENTITY_REGEX = re.compile("|".join(ENTITY_PATTERNS), flags=re.IGNORECASE)

# Sentence-ish splitter
SENT_SPLIT = re.compile(r"(?<=\.|\?|!|\n)\s+")

# Date window (number of characters to search around an entity mention)
DATE_WINDOW_CHARS = 240

# Year pattern for file name/year detection
YEAR_REGEX = re.compile(r"\b(18|19|20)\d{2}\b")
