# DnD Tudum — Competition Plan

## Context

**Goal:** Predict the Global Top 10 Netflix TV Shows (English) for the week of 22–28 June 2026, plus the Tomatometer rating for the #1 show.
**Submission deadline:** 29 May 2026 (6 days away).
**Results revealed:** 30 June 2026 (Tuesday after the target week).

The data pipeline (steps 1–3) is complete and functional. The project now needs an **analysis and prediction layer** to actually answer the competition question.

---

## Best Course of Action to Win

### The single most powerful signal: Netflix's release calendar

For any given week, the #1 Netflix show is almost always a **new release in its first 1–3 weeks**, OR a returning mega-franchise season. Historical ranking data confirms this — the top weekly performers (Stranger Things 4: 29 weeks, Wednesday S1: 28 weeks) all debuted at #1. The June 22–28 window is ~4–5 weeks out, and Netflix announces titles weeks in advance.

**Priority actions (manual research, no code needed):**
1. Look up Netflix's confirmed June 2026 release schedule — any major franchise drops (Squid Game, Stranger Things, Bridgerton, Wednesday, Outer Banks, Ginny & Georgia, etc.) near that week will almost certainly be #1.
2. Check if any shows currently in the top 10 (as of early May 2026) are still airing new episodes — they may still chart.
3. For the Tomatometer guess: Rotten Tomatoes publishes critic scores when a show premieres. If the #1 is a new release, its RT score will be available by mid-June; if submitting before May 29, use comparable franchise seasons as a proxy (e.g. Stranger Things S3: 93%, S4: 86%; Wednesday S1: 67%).

### Analytical signals from existing data

| Signal | How to use |
|---|---|
| **Show persistence** | Measure median weeks in top 10 per show; returning franchises sustain long runs |
| **Genre + network** | Drama + Netflix Original = ~70% of top 10 slots |
| **Season recency** | `season_air_date` within 3 weeks of the target date = strong predictor of charting |
| **TMDB score** | Scores ≥ 7.5 correlate with longer chart runs; <5 shows typically fall out quickly |

---

## What's Been Done Well

- **Clean 3-step pipeline** — scraper → season parser → TMDB enrichment is well-structured and idiomatic.
- **Scraper is robust** — polite rate-limiting (1s delay), graceful HTTP error handling, incremental writes with `flush()`.
- **TMDB enrichment is resumable** — skips already-processed pairs; safe to rerun without API waste.
- **Season label parsing is comprehensive** — handles Korean labels, date-based labels, `S10: Ohio`-style formats.
- **89% TMDB match rate** on 91 pairs — good enrichment coverage.

---

## Improvement Suggestions

### Critical (affects prediction quality)

1. **File 02 and 03 are out of sync with file 01.**
   File 01 has 2,540 rows (2021–2026), but file 02/03 only cover 18 weeks (Jan–May 2026, 180 rows). Step 2 and Step 3 were run on an older, smaller version of file 01. **Regenerate file 02 and 03 from the current file 01** to unlock full 5-year historical enrichment.

2. **No Rotten Tomatoes / Tomatometer data.**
   TMDB `vote_average` is audience score, not Tomatometer (critic score). These diverge significantly (e.g. Wednesday S1: TMDB ~7.5, RT critic 67%). Add an enrichment step using the RT API or scraping `rottentomatoes.com` to get actual Tomatometer scores for the likely #1 contenders.

3. **No analysis/prediction step.**
   Steps 1–3 collect data; nothing produces a ranked prediction. Add a `04.predict.py` (or notebook) that:
   - Computes show persistence curves from file 01 (weeks-to-dropoff distribution)
   - Identifies currently charting shows and their expected remaining shelf-life
   - Factors in known upcoming releases from the Netflix calendar
   - Outputs a ranked top-10 prediction list

### Moderate

4. **`LOOKBACK_YEARS = 2` limits future scrapes.** The current 5-year history in file 01 was accumulated over time; re-running the scraper today would overwrite it with only 2 years. Either increase `LOOKBACK_YEARS` or add a merge-append mode to avoid losing history.

5. **`main.py` is a stub.** Wire the three steps together so the pipeline can be run end-to-end with one command.

6. **Stranger Things seasons 2–5 missing TMDB data** due to non-standard naming (no season label). These are historically the most dominant titles. The enrichment script should fall back to a fuzzy title search for unmatched rows.

---

## Verification

After implementing:
- Run `uv run add_season_columns.py` and confirm file 02 has ~2,540 rows (not 180).
- Run `uv run enrich_with_tmdb.py` and confirm file 03 grows from 91 to ~800+ unique pairs.
- Run prediction script and inspect output — cross-check #1 pick against publicly announced Netflix June 2026 releases.
