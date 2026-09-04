"""Generate the compact EDA payload used by the SNOSCOT website.

Run from the repository root:

    python scripts/generate_eda.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "docs" / "data" / "points.csv"
OUTPUT_PATH = ROOT / "docs" / "data" / "eda_summary.json"

SEASONS = ("Winter", "Spring", "Summer", "Autumn", "Unknown")
MONTH_NAMES = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def season_for(row: pd.Series) -> str:
    explicit = str(row.get("season", "")).strip().title()
    if explicit in SEASONS[:-1]:
        return explicit

    month = pd.to_numeric(row.get("month"), errors="coerce")
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    if month in (9, 10, 11):
        return "Autumn"
    return "Unknown"


def count_records(series: pd.Series, *, sort_index: bool = False) -> list[dict]:
    counts = series.value_counts(dropna=False)
    if sort_index:
        counts = counts.sort_index()
    return [
        {"label": str(label), "count": int(count)}
        for label, count in counts.items()
    ]


def top_entity_terms(series: pd.Series, limit: int = 18) -> list[dict]:
    terms: Counter[str] = Counter()
    for value in series.dropna().astype(str):
        for raw_term in re.split(r"[,;/|]+", value.lower()):
            term = re.sub(r"\s+", " ", raw_term.strip(" .:-_"))
            if term and term not in {"none", "n/a", "na"}:
                terms[term] += 1
    return [
        {"label": term, "count": int(count)}
        for term, count in terms.most_common(limit)
    ]


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    years = pd.to_numeric(df["year"], errors="coerce")
    months = pd.to_numeric(df["month"], errors="coerce")
    scores = pd.to_numeric(df["score"], errors="coerce")
    valid_months = months.where(months.between(1, 12))

    season_series = df.apply(season_for, axis=1)
    decades = ((years.dropna() // 10) * 10).astype(int)

    month_counts = valid_months.value_counts().sort_index()
    score_counts = scores.value_counts().sort_index()
    season_counts = season_series.value_counts().reindex(SEASONS, fill_value=0)
    location_counts = df["general_location"].fillna("Unknown").value_counts()
    decade_counts = decades.value_counts().sort_index()

    completeness_fields = {
        "Text": "text",
        "Entity label": "entity",
        "Year": "year",
        "Month": "month",
        "Specific location": "specific_location",
        "Map coordinates": "Coordinates",
    }
    completeness = []
    for label, column in completeness_fields.items():
        present = int(df[column].notna().sum())
        if column == "month":
            present = int(valid_months.notna().sum())
        completeness.append(
            {
                "label": label,
                "present": present,
                "missing": int(len(df) - present),
                "percent": round(100 * present / len(df), 1),
            }
        )

    payload = {
        "generated_from": str(CSV_PATH.relative_to(ROOT)),
        "summary": {
            "observations": int(len(df)),
            "broad_regions": int(df["general_location"].nunique()),
            "specific_locations": int(df["specific_location"].nunique()),
            "earliest_year": int(years.min()),
            "latest_year": int(years.max()),
            "years_represented": int(years.nunique()),
            "geocoded": int(df["Coordinates"].notna().sum()),
            "geocoded_percent": round(100 * df["Coordinates"].notna().mean(), 1),
            "mean_score": round(float(scores.mean()), 2),
            "median_score": round(float(scores.median()), 1),
            "records_with_month": int(valid_months.notna().sum()),
            "invalid_month_values": int((months.notna() & ~months.between(1, 12)).sum()),
        },
        "locations": [
            {"label": str(label), "count": int(count)}
            for label, count in location_counts.items()
        ],
        "months": [
            {"label": MONTH_NAMES[month - 1], "month": month, "count": int(month_counts.get(month, 0))}
            for month in range(1, 13)
        ],
        "seasons": [
            {"label": season, "count": int(season_counts[season])}
            for season in SEASONS
        ],
        "scores": [
            {"label": str(score), "score": score, "count": int(score_counts.get(score, 0))}
            for score in range(0, 11)
        ],
        "decades": [
            {"label": f"{decade}s", "decade": int(decade), "count": int(count)}
            for decade, count in decade_counts.items()
        ],
        "top_entities": top_entity_terms(df["entity"]),
        "completeness": completeness,
        "notes": [
            "Counts describe surviving journal coverage and the curation process; they are not a direct climate time series.",
            "Months are available for most, but not all, observations. One invalid month value is excluded from seasonal charts.",
            "Map coordinates identify broad regional groupings rather than the precise position of every quoted observation.",
        ],
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUTPUT_PATH.relative_to(ROOT)}: "
        f"{payload['summary']['observations']:,} observations, "
        f"{payload['summary']['broad_regions']} regions."
    )


if __name__ == "__main__":
    main()
