# GIC Tudum

Data pipeline to collect and enrich Netflix Top 10 English TV shows.

## Steps to reproduce

### 1. Scrape the data

```bash
uv run scrape_netflix_top10.py
```

Fetches the Netflix Top 10 TV (English) weekly rankings from
[netflix.com/tudum/top10/tv](https://www.netflix.com/tudum/top10/tv) for the last
2 years, iterating over every available week. For each week it scrapes the table
and writes one row per ranked show with columns: `week_start`, `week_end`, `rank`,
`title`, `weeks_in_top10`, `views`, `runtime`, and `hours_viewed`.

Output: `01.netflix_top10_english_shows.csv`

### 2. Add season columns

```bash
uv run add_season_columns.py
```

Reads `01.netflix_top10_english_shows.csv` and adds two new columns:

- **`title_clean`** — the show name with the season label removed
  (e.g. `"Stranger Things"` from `"Stranger Things: Season 4"`).
- **`season`** — the extracted season label
  (e.g. `"Season 4"`, `"Limited Series"`, `"Part 1"`), or empty if no
  recognisable season indicator was found.

Output: `02.netflix_top10_english_shows_with_seasons.csv`
