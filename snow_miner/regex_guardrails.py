from __future__ import annotations

import regex as re

SNOW_REGEX = re.compile(
    r"\b("
    # core nouns
    r"snow|snowy|snowfall|snowpack|snowfield|snowdrift|drift(?:ed|s)?|"
    r"powder|spindrift|windslab|slab|hardpack|hard-packed|crud|crust(?:ed)?|"
    r"cornice(?:s)?|avalanche(?:s|d)?|sluff(?:s)?|slough|"
    r"névé|neve|firn|glacier(?:s)?|serac(?:s)?|bergschrund|icefall|ice|icicle(?:s)?|verglas|"
    # precip / events
    r"blizzard|white[-\s]?out|storm\s*snow|graupel|sleet|hail|freez(?:e|ing)|frost|hoar|rime|spindrift|"
    # adjectives / conditions
    r"frozen|icy|slushy|patchy|thin\s*cover|deep|loaded|drifted|banked(?:[- ]out)?|"
    r"waist[- ]deep|knee[- ]deep|superb\s*powder|excellent\s*cover|plenty\s*of\s*snow|"
    r"good\s*cover|full\s*cover|"
    r"melt(?:ed|ing)?|thaw(?:ing)?|bare|gone|disappeared|snowless|clear\s*of\s*snow|retreat(?:ing)?|diminish(?:ing|ed)|"
    # scottish / alpine place-words often indicating snow context
    r"gully|gullies|corrie|coire(?:\s+an\s+t-sneachda)?|sneachda|alpine|winter"
    r")\b",
    flags=re.IGNORECASE
)


def is_snowy(text: str) -> bool:
    """
    enforce snow regex to stop GPT timewasting with irrelevant entities
    """
    return bool(SNOW_REGEX.search(text or ""))


MONTHS = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
SEASONS = r"(winter|spring|summer|autumn|fall)"
ORDINAL = r"(?:st|nd|rd|th)"
YEAR = r"(?:18|19|20)\d{2}"
DATE_PATTERNS = [
    rf"\b\d{{1,2}}{ORDINAL}?\s+{MONTHS}\s+{YEAR}\b",  # 12th July 2019
    rf"\b{MONTHS}\s+\d{{1,2}}{ORDINAL}?,\s*{YEAR}\b",  # July 12, 2019
    rf"\b\d{{1,2}}{ORDINAL}?\s+{MONTHS}\b",  # 12 July
    rf"\b{MONTHS}\s+\d{{1,2}}{ORDINAL}?\b",  # July 12
    rf"\b{MONTHS}\s+{YEAR}\b",  # July 2019
    rf"\b{YEAR}\s+{MONTHS}\b",  # 2019 July
    rf"\b{SEASONS}\s+{YEAR}\b",  # Winter 1986
    rf"\b{YEAR}\b",  # 1986
    r"\b\d{1,2}[\/\-]\d{1,2}([\/\-]\d{2,4})?\b",  # 13/2/1988 or 13-02-88
]
DATE_REGEXES = [re.compile(p, flags=re.IGNORECASE) for p in DATE_PATTERNS]
