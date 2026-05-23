# /// script
# dependencies = ["requests", "beautifulsoup4"]
# ///

import csv
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.netflix.com/tudum/top10/tv"
OUTPUT_FILE = "01.netflix_top10_english_shows.csv"
LOOKBACK_MONTHS = 13
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page(url: str) -> tuple[BeautifulSoup, str]:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser"), response.text


def get_available_weeks(html: str) -> list[dict]:
    """
    Extract all available week date ranges from the JSON embedded in the page,
    filtered to the last LOOKBACK_MONTHS months. Returns a list oldest-first.
    """
    cutoff = date.today() - timedelta(days=30 * LOOKBACK_MONTHS)

    matches = re.findall(
        r'\{"startDate":"(\d{4}-\d{2}-\d{2})","endDate":"(\d{4}-\d{2}-\d{2})"\}',
        html,
    )
    if not matches:
        return []

    seen = set()
    weeks = []
    for start, end in matches:
        if start not in seen and date.fromisoformat(start) >= cutoff:
            seen.add(start)
            weeks.append({"startDate": start, "endDate": end})
    return weeks


def parse_table(soup: BeautifulSoup) -> list[dict]:
    """
    Parse the Top 10 data table using data-uia attribute selectors.
    Columns extracted: rank, title, weeks_in_top10, views, runtime_hm, hours_viewed.
    """
    rows = []
    table = soup.find("table")
    if not table:
        return rows

    for tr in table.find_all("tr"):
        title_td = tr.find("td", {"data-uia": "top10-table-row-title"})
        if not title_td:
            continue

        rank_span = title_td.find("span", class_="rank")
        title_btn = title_td.find("button")
        weeks_td = tr.find("td", {"data-uia": "top10-table-row-weeks"})
        views_td = tr.find("td", {"data-uia": "top10-table-row-views"})
        runtime_td = tr.find("td", {"data-uia": "top10-table-row-runtime"})
        hours_td = tr.find("td", {"data-uia": "top10-table-row-hours"})

        if not (rank_span and title_btn and weeks_td and views_td):
            continue

        rank = int(rank_span.get_text(strip=True))
        title = title_btn.get_text(strip=True)
        weeks_in_top10 = int(weeks_td.get_text(strip=True))

        views_raw = views_td.get_text(strip=True).replace(",", "")
        views = int(views_raw) if views_raw.isdigit() else None

        runtime = runtime_td.get_text(strip=True) if runtime_td else None

        hours_raw = hours_td.get_text(strip=True).replace(",", "") if hours_td else None
        hours_viewed = int(hours_raw) if hours_raw and hours_raw.isdigit() else None

        rows.append({
            "rank": rank,
            "title": title,
            "weeks_in_top10": weeks_in_top10,
            "views": views,
            "runtime": runtime,
            "hours_viewed": hours_viewed,
        })

    return rows


def main():
    print("Fetching base page to discover available weeks...")
    soup, html = fetch_page(BASE_URL)

    weeks = get_available_weeks(html)
    if not weeks:
        print("ERROR: Could not find week data in the page. HTML structure may have changed.")
        return

    print(f"Found {len(weeks)} weeks of data ({weeks[0]['startDate']} → {weeks[-1]['startDate']}). Starting download...\n")

    fieldnames = ["week_start", "week_end", "rank", "title", "weeks_in_top10", "views", "runtime", "hours_viewed"]
    total_rows = 0

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, week in enumerate(weeks, 1):
            start_date = week["startDate"]
            end_date = week["endDate"]
            url = f"{BASE_URL}?week={start_date}"
            try:
                week_soup, _ = fetch_page(url)
                rows = parse_table(week_soup)

                if not rows:
                    print(f"  [{i}/{len(weeks)}] {start_date} — WARNING: no table rows found, skipping")
                else:
                    for row in rows:
                        writer.writerow({"week_start": start_date, "week_end": end_date, **row})
                    f.flush()
                    total_rows += len(rows)
                    print(f"  [{i}/{len(weeks)}] {start_date} → {end_date}  ({len(rows)} rows, {total_rows} total)")

            except requests.HTTPError as e:
                print(f"  [{i}/{len(weeks)}] {start_date} — HTTP error: {e}, skipping")
            except Exception as e:
                print(f"  [{i}/{len(weeks)}] {start_date} — unexpected error: {e}, skipping")

            if i < len(weeks):
                time.sleep(1)

    print(f"\nDone. {total_rows} rows written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
