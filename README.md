# trainer

Read your training data, calculate a few conservative summaries, and write exactly
the workouts you request to your calendar.

It's a thin Python client over [intervals.icu](https://intervals.icu) and
[Strava](https://www.strava.com), plus a set of Claude Code skills and reference
docs. There's no app and no server — you talk to Claude, and Claude uses these.

**What you can ask for:**

- *"How did the last four weeks actually go?"* — pulls CTL, planned vs. completed sessions, and per-rep power, then gives a progress / repeat / back off verdict.
- *"Schedule this exact workout on Thursday."* — writes a structured workout to the intervals.icu calendar.
- *"Summarize the last 14 days."* — queries the local warehouse and reports basic stats.

## Setup

Requires [pixi](https://pixi.sh). Everything below is one-time.

```bash
git clone git@github.com:slymon99/trainer.git
cd trainer
pixi install
cp .env.example .env
```

### intervals.icu

Get an API key from [intervals.icu/settings](https://intervals.icu/settings) →
**Developer Settings**, and put it in `.env`:

```
INTERVALS_API_KEY=your_key_here
INTERVALS_ATHLETE_ID=0
```

`0` means "the current athlete" and is usually right. Verify:

```bash
pixi run check intervals
# intervals.icu  OK — Your Name (id i123456)
```

### Strava

intervals.icu imports your Strava activities but **won't serve their detail back
over its API** — so per-rep power and HR come from Strava directly. Set this up
unless you only care about the CTL/ATL model and the calendar.

1. Create an app at [strava.com/settings/api](https://www.strava.com/settings/api).
   Set **Authorization Callback Domain** to exactly `localhost` — no port, no `http://`.
2. Put the Client ID and Secret in `.env`.
3. Authorize once:

```bash
pixi run strava-auth
```

This opens a browser, catches the redirect on `localhost:8000`, and saves tokens
to `.strava_tokens.json`. Tick **"View data about your private activities"** on
the consent screen, or private rides stay invisible. Access tokens expire every
6 hours and refresh automatically from then on.

```bash
pixi run check strava
```

### Pull your data

```bash
pixi run sync     # incremental — safe to re-run any time
pixi run sql      # see what's stored
```

This lands both sources in `data/warehouse/` as parquet, normalised and joined
on activity id. The first run backfills a year; Strava's rate limit means
per-rep detail arrives over a few runs, newest first. Everything downstream
reads from here rather than the APIs — see
[docs/data-store.md](docs/data-store.md).

### Training notes

The old athlete-specific schedule, progression rules, check-ins, and source notes
were assessed and moved to `~/archive/trainer-notes`. They are not inputs to future
workout generation. Use [docs/stats.md](docs/stats.md) for the small HRV/resting-HR summary.

## Layout

```
trainer/
  intervals.py       IntervalsClient — activities, wellness, calendar events
  strava.py          StravaClient — activities, streams, segments
  strava_auth.py     one-time OAuth flow
  http.py            timeouts, retries, rate-limit budget
  tables.py          warehouse schemas and the API field mapping
  store.py           parquet + DuckDB — read, merge, partition
  sync.py            incremental pull  (pixi run sync)
  query.py           ad-hoc SQL        (pixi run sql)
docs/
  data-store.md          the tables, how to query them, how the sync decides
  reading-data.md        what each field means, which source to use
  intervals-workouts.md  workout-text syntax and the calendar API
  stats.md               basic individual-baseline readiness summary
.claude/skills/
  review-training/   summarize recent data
  create-workouts/   write exactly requested workouts to the calendar
  plan-lifting/      write exactly requested strength routines
data/                your training data (gitignored)
.env                 your credentials (gitignored)
```

## Using it directly

It's ordinary Python and SQL if you'd rather not go through Claude:

```python
from trainer.store import Store

store = Store()
store.sql("""
    SELECT date, planned_name, planned_load, actual_np, lap_count
    FROM planned_vs_actual WHERE date >= '2026-08-01' ORDER BY date
""").show()
```

See [docs/data-store.md](docs/data-store.md) for the tables, and
[docs/reading-data.md](docs/reading-data.md) for what the numbers mean.

## Notes

- Strava allows 100 requests / 15 min and 1000 / day. `pixi run sync` fetches each activity once, caches the raw response under `data/`, and stops short of the wall.
- Nothing here writes to Strava — it's read-only. Only intervals.icu gets written to, and only to the calendar.
