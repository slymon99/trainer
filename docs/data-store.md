# The local data store

Both APIs are pulled into normalised parquet under `data/warehouse/` and queried
with DuckDB. Read this before writing anything that fetches training data —
almost always the data is already on disk.

## Why it exists

Strava allows **100 requests per 15 minutes**, and one activity's laps is one
request. Pulling a season ad-hoc doesn't fit in the budget, and re-pulling it
for every question wastes it. So the sync is incremental: it works out what's
missing, asks only for that, and everything downstream reads locally.

## Using it

```bash
pixi run sync                  # bring everything up to date
pixi run sql                   # what's stored, and how much
pixi run sql --schema          # every table's columns
```

From Python — this is the normal path for a skill:

```python
from trainer.store import Store

store = Store()
store.sql("SELECT date, ctl, atl FROM iv_wellness ORDER BY date DESC LIMIT 14").fetchall()
```

`store.sql()` returns a DuckDB relation: `.fetchall()`, `.arrow()`, `.show()`.

Ad-hoc from the shell, note that `pixi run sql` eats the quotes inside its
argument. For SQL containing string literals use:

```bash
pixi run python -m trainer.query "SELECT * FROM iv_events WHERE date > '2026-08-01'"
```

## Layout

```
data/warehouse/<table>/month=YYYY-MM/data_0.parquet
data/strava/<activity_id>.json          # raw responses, kept as-is
data/strava/streams/<activity_id>.json
```

Partitioning by month is for **incremental writes**, not query speed: a sync
touches one or two months and rewrites only those files. Everything here is
small enough that queries just scan the lot.

The raw JSON is kept because an activity never changes once uploaded — tables
can be rebuilt from disk without spending a single request. Deleting
`data/warehouse/` is always safe; deleting `data/strava/` costs API budget to
recover.

## Tables

Source-faithful, one grain each. Columns are snake_case even where the API
isn't (`restingHR` → `resting_hr`), and **every id is a string**, so
intervals.icu ids and Strava ids join without casting.

| Table | Grain | What it's for |
|---|---|---|
| `iv_wellness` | one row per day | CTL/ATL, resting HR, HRV, sleep, weight |
| `iv_events` | one row per calendar event | what was **prescribed** |
| `iv_activities` | one row per activity | the index — id, date, source, and the modelled load |
| `iv_athlete` | one row per sport per sync | FTP/LTHR/zones **as they were that day** |
| `strava_activities` | one row per activity | what was **done** — measured power and HR |
| `strava_laps` | one row per lap | per-rep actuals |
| `strava_streams` | one row per sample | per-second data (opt-in) |
| `hevy_workouts` | one row per gym session | duration, set counts, total volume |
| `hevy_sets` | one row per set | weight, reps, RPE — where lifting progression is judged |
| `hevy_exercise_templates` | one row per exercise | Hevy's catalogue, for resolving names to ids |

Three views do the joins for you:

| View | What it is |
|---|---|
| `activities` | `iv_activities` + `strava_activities` on id — the whole picture of one ride |
| `planned_vs_actual` | `iv_events` left-joined to `activities` on intervals.icu's own `paired_activity_id` |
| `lift_sets` | `hevy_sets` + session title + muscle group, with an Epley 1RM estimate |

`pixi run sql --schema <table>` lists columns; `trainer/tables.py` is the
definitive schema, including which API field each column came from.

### Things worth knowing about the data

- **`iv_activities` is a stub for Strava-sourced rides.** intervals.icu won't
  serve their detail over the API, so `name`, `moving_time` and the `icu_*`
  fields are mostly NULL there. The measurements come from `strava_activities`;
  the id is the same number in both systems. See
  [reading-data.md](reading-data.md).
- **Strava reports no `max_watts` per lap** — only the average. There's no
  column for it because there's no data for it.
- **`has_detail`** distinguishes an activity known only from the list endpoint
  from one whose laps have been fetched. `WHERE NOT has_detail` is what the sync
  works through.
- **`iv_athlete` is a daily snapshot**, not current state. Reviewing an old
  block needs the FTP that was configured *then*, and that number changes.
- **Hevy volume figures exclude warm-ups.** They scale with the working weight,
  so counting them scores a heavier session as more work than it was. Hevy
  timestamps also carry no UTC offset — see [hevy.md](hevy.md).

## How the sync decides what to fetch

| Step | Window | Why |
|---|---|---|
| `wellness` | watermark − 45d → today | intervals.icu revises CTL/ATL backwards as activities land |
| `events` | today − 365d → today + 240d | the calendar is edited and deleted, so it's re-read whole |
| `activities` | watermark − 365d → today | same: an activity can be deleted or re-categorised long after the ride |
| `strava` | watermark − 7d → today | the list endpoint; one request per 200 rides |
| `details` | anything `WHERE NOT has_detail` | one request each — this is what the quota bites on |
| `streams` | opt-in, `--streams N` | one request and ~10k rows per activity |
| `lifts` | watermark − 30d → today, widened by Hevy's events feed | sessions get edited and deleted in the app after the fact |
| `exercises` | once, unless `--refresh` | the catalogue only changes when a custom exercise is added |

The two APIs are budgeted differently on purpose. **intervals.icu is not
meaningfully rate limited** — a year of calendar is one request — so its windows
are set by how far back data can still *change*, not by what we can afford. Only
the Strava steps economise.

Windows that get re-read whole (`wellness`, `events`, `activities`) are written
with a **replace range**: held rows in the window are dropped before the merge,
so a workout deleted from the calendar disappears here too. Everything else is a
plain upsert on the key, which can add and update but never notice a deletion.

Two consequences worth knowing:

- **The window runs back from the watermark, not from today.** A season pulled
  in with `--since` sits outside it and is never revisited — which is what keeps
  the replace range from eating the backfill, but also means edits to it won't
  land. Re-run with the same `--since` to refresh that far back.
- **Events beyond the window are frozen.** +240d covers a block written to the
  calendar months ahead; anything further out won't appear locally until it
  comes into range.

Useful flags:

```bash
pixi run sync --since 2025-09-01     # backfill further back than the watermark
pixi run sync --tables wellness      # one step only
pixi run sync --details 200          # raise the per-run cap (default 50)
pixi run sync --streams 10           # pull per-second data for 10 rides
pixi run sync --refresh              # re-fetch detail already stored
```

## Rate limits

`details` and `streams` stop 5 requests short of Strava's quota and report what
they left behind:

```
pending: 227 activities still need detail — re-run to continue
```

That's normal for a backfill, not a failure — re-run after the window rolls
over. Anything already cached in `data/strava/` is free and doesn't count
against the budget, so a re-run after a stop is mostly disk reads. If the quota
runs out mid-run anyway, whatever was fetched is still written before the sync
exits (non-zero).

## Changing the schema

Add the column to the table in `trainer/tables.py`. Older parquet files don't
have it and don't need rewriting — reads union against the declared schema, so
it comes back NULL until a sync refills it. Re-run with `--since` to backfill
from the API, or delete `data/warehouse/<table>/` and rebuild from the raw JSON.

Writes are not atomic per file. If a sync is killed mid-write, that month's
partition can be left short — re-running fixes it, since the source of truth is
the API and the raw cache, never the parquet.
