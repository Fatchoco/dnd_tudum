import pandas as pd
import re

df = pd.read_csv("01.netflix_top10_english_shows.csv")

# Patterns that identify a season/episode label at the end of a title
SEASON_PATTERNS = [
    r"^Season \d+(?:\s+-\s+.+)?$",  # Season 1, Season 1 - The Live Semifinals
    r"^Limited Series$",
    r"^Part \d+$",
    r"^Volume \d+$",
    r"^Collection \d+$",
    r"^시즌 \d+$",                   # Korean "Season N"
    r"^Chapter \d+$",
    r"^\d{4} - .+$",               # Date episodes e.g. Raw: 2025 - April 14
]


def is_season_label(segment: str) -> bool:
    return any(re.match(p, segment) for p in SEASON_PATTERNS)


def extract_title_and_season(title) -> tuple[str, str]:
    if not isinstance(title, str):
        return title, ""
    parts = title.split(": ")

    if len(parts) == 1:
        return title, ""

    last = parts[-1]

    # Standard season indicator at the end
    if is_season_label(last):
        return ": ".join(parts[:-1]), last

    # "Love Is Blind: S10: Ohio" — second-to-last segment is SN
    if len(parts) >= 3 and re.match(r"^S\d+$", parts[-2]):
        return ": ".join(parts[:-2]), f"{parts[-2]}: {last}"

    # No recognisable season found — keep the full title
    return title, ""


df[["title_clean", "season"]] = df["title"].apply(
    lambda t: pd.Series(extract_title_and_season(t))
)

out_path = "02.netflix_top10_english_shows_with_seasons.csv"
df.to_csv(out_path, index=False)
print(f"Saved {len(df):,} rows → {out_path}")

# Quick sanity check
sample = df[["title", "title_clean", "season"]].drop_duplicates("title").head(20)
print(sample.to_string(index=False))
