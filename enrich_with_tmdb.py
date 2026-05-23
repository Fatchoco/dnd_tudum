# /// script
# dependencies = ["requests", "python-dotenv", "pandas"]
# ///

import os
import re
import time

import pandas as pd
import requests
from dotenv import load_dotenv

INPUT_FILE = "02.netflix_top10_english_shows_with_seasons.csv"
OUTPUT_FILE = "03.netflix_top10_english_shows_with_tmdb.csv"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
REQUEST_DELAY = 0.25  # seconds between API calls


def load_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise RuntimeError("TMDB_API_KEY not found. Add it to a .env file.")
    return api_key


def infer_season_number(season_label: str) -> tuple[int, str]:
    """Extract the first integer from a season label; fall back to 1.

    Returns a tuple of (season_number, lookup_type) where lookup_type is
    'inferred' when a digit was found in the label or 'defaulted' when not.
    """
    match = re.search(r"\d+", season_label)
    if match:
        return int(match.group()), "inferred"
    return 1, "defaulted"


def search_tmdb_show(title: str, api_key: str) -> dict | None:
    """Search TMDB for a TV show by title; return the top result or None."""
    url = f"{TMDB_BASE_URL}/search/tv"
    try:
        response = requests.get(
            url,
            params={"query": title, "api_key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0] if results else None
    except (requests.RequestException, ValueError):
        return None


def fetch_show_details(tmdb_id: int, api_key: str) -> dict:
    """Fetch detailed TV show info from TMDB; return a dict of enriched fields."""
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
    try:
        response = requests.get(url, params={"api_key": api_key}, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "tmdb_score": data.get("vote_average"),
            "status": data.get("status"),
            "network": " | ".join(n["name"] for n in data.get("networks", [])) or None,
            "type": data.get("type"),
            "genre": " | ".join(g["name"] for g in data.get("genres", [])) or None,
        }
    except (requests.RequestException, ValueError):
        return {
            "tmdb_score": None,
            "status": None,
            "network": None,
            "type": None,
            "genre": None,
        }


def fetch_season_air_date(tmdb_id: int, season_num: int, api_key: str) -> str | None:
    """Fetch the air date for a specific season of a TV show."""
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}/season/{season_num}"
    try:
        response = requests.get(url, params={"api_key": api_key}, timeout=10)
        response.raise_for_status()
        return response.json().get("air_date")
    except (requests.RequestException, ValueError):
        return None


def search_tmdb_movie(title: str, api_key: str) -> dict | None:
    """Search TMDB for a movie by title; return the top result or None."""
    url = f"{TMDB_BASE_URL}/search/movie"
    try:
        response = requests.get(
            url,
            params={"query": title, "api_key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0] if results else None
    except (requests.RequestException, ValueError):
        return None


def fetch_movie_details(tmdb_id: int, api_key: str) -> dict:
    """Fetch detailed movie info from TMDB; mapped to the same fields as TV shows."""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    try:
        response = requests.get(url, params={"api_key": api_key}, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "tmdb_score": data.get("vote_average"),
            "status": data.get("status"),
            "network": None,
            "type": "Movie",
            "genre": " | ".join(g["name"] for g in data.get("genres", [])) or None,
            "season_air_date": data.get("release_date"),
        }
    except (requests.RequestException, ValueError):
        return {
            "tmdb_score": None,
            "status": None,
            "network": None,
            "type": "Movie",
            "genre": None,
            "season_air_date": None,
        }


def main() -> None:
    api_key = load_api_key()

    df = pd.read_csv(INPUT_FILE)
    df["season"] = df["season"].fillna("")
    pairs = df[["title_clean", "season"]].drop_duplicates().reset_index(drop=True)

    # Resume: skip pairs already present in the output file.
    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(OUTPUT_FILE)
        existing_df["season"] = existing_df["season"].fillna("")
        done: set[tuple[str, str]] = set(
            zip(existing_df["title_clean"], existing_df["season"])
        )
        print(f"Found {len(done)} already-processed pairs in {OUTPUT_FILE}.")
    else:
        done = set()

    pending = pairs[
        ~pairs.apply(lambda r: (r["title_clean"], r["season"]) in done, axis=1)
    ].reset_index(drop=True)

    total = len(pending)
    if total == 0:
        print("Nothing to do — all pairs already processed.")
        return

    print(f"Skipping {len(done)} already done. Processing {total} remaining...")

    write_header = not os.path.exists(OUTPUT_FILE)
    written = 0

    for i, row in pending.iterrows():
        title_clean: str = row["title_clean"]
        season_label: str = row["season"]
        season_num, lookup_type = infer_season_number(season_label)

        print(f"  [{i + 1}/{total}] {title_clean} — {season_label or '(no season)'}")

        tv_result = search_tmdb_show(title_clean, api_key)
        time.sleep(REQUEST_DELAY)

        if tv_result is not None:
            tmdb_id: int = tv_result["id"]
            tmdb_title: str = tv_result.get("name")

            details = fetch_show_details(tmdb_id, api_key)
            time.sleep(REQUEST_DELAY)

            season_air_date = fetch_season_air_date(tmdb_id, season_num, api_key)
            time.sleep(REQUEST_DELAY)

            row_data = {
                "title_clean": title_clean,
                "season": season_label,
                "tmdb_id": tmdb_id,
                "tmdb_title": tmdb_title,
                **details,
                "season_air_date": season_air_date,
                "tmdb_lookup_type": lookup_type,
            }
        else:
            movie_result = search_tmdb_movie(title_clean, api_key)
            time.sleep(REQUEST_DELAY)

            if movie_result is not None:
                tmdb_id = movie_result["id"]
                tmdb_title = movie_result.get("title")

                details = fetch_movie_details(tmdb_id, api_key)
                time.sleep(REQUEST_DELAY)

                row_data = {
                    "title_clean": title_clean,
                    "season": season_label,
                    "tmdb_id": tmdb_id,
                    "tmdb_title": tmdb_title,
                    **details,
                    "tmdb_lookup_type": "movie",
                }
            else:
                row_data = {
                    "title_clean": title_clean,
                    "season": season_label,
                    "tmdb_id": None,
                    "tmdb_title": None,
                    "tmdb_score": None,
                    "status": None,
                    "network": None,
                    "type": None,
                    "genre": None,
                    "season_air_date": None,
                    "tmdb_lookup_type": None,
                }

        pd.DataFrame([row_data]).to_csv(OUTPUT_FILE, mode="a", header=write_header, index=False)
        write_header = False
        written += 1

    print(f"\nDone! {written} new rows written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
