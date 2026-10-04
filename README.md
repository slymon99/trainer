# trainer

Read your training data, calculate a few conservative summaries, and write exactly
the workouts you request to your calendar. Several athletes can share one checkout,
each with their own keys and data.

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
pixi run profiles new simon     # creates profiles/simon/.env from .env.example
```

Each athlete is a **profile**: a directory under `profiles/` (gitignored) with
their own `.env`, Strava tokens and data. Repeat the steps below for each one,
with their own keys and their own Strava app. Commands act on the active
profile:

```bash
export TRAINER_PROFILE=simon    # in your shell, or…
pixi run activate simon         # …remembered in profiles/.active
pixi run sync --profile sabrina # one-off override
pixi run profiles               # list them, and whose keys each holds
```

`--profile` beats `TRAINER_PROFILE`, which beats `pixi run activate`. With a
single profile it's used automatically; with several and none chosen, commands
stop rather than guess.

### intervals.icu

Get an API key from [intervals.icu/settings](https://intervals.icu/settings) →
**Developer Settings**, and put it in `profiles/<name>/.env`:

```
INTERVALS_API_KEY=your_key_here
INTERVALS_ATHLETE_ID=0
```

`0` means "the current athlete" and is usually right. Verify — this also records who the key belongs to, and writes to the calendar
are refused until it has:

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
2. Put the Client ID and Secret in the profile's `.env`.
3. Authorize once:

```bash
pixi run strava-auth
```

This opens a browser, catches the redirect on `localhost:8000`, and saves tokens
to `profiles/<name>/strava_tokens.json`. Make sure the browser is logged in to
Strava as *that* athlete — the consent page authorizes whoever is signed in. Tick **"View data about your private activities"** on
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

This lands every source in `profiles/<name>/data/warehouse/` as parquet, normalised and joined
on activity id. The first run backfills a year; Strava's rate limit means
per-rep detail arrives over a few runs, newest first. Everything downstream
reads from here rather than the APIs — see
[docs/data-store.md](docs/data-store.md).

### Training plans

Athlete-specific long-term schedules, progression rules, and check-ins are not kept
in this repository and are not inputs to future workout generation. The repository
holds reusable workout-writing references and the data needed for ad-hoc analysis.

## Layout

```
trainer/
  intervals.py       IntervalsClient — activities, wellness, calendar events
  strava.py          StravaClient — activities, streams, segments
  strava_auth.py     one-time OAuth flow, per profile
  config.py          profiles — which athlete, whose keys, where their data lives
  identity.py        refuses writes if a profile's key belongs to someone else
  profiles.py        list / new / migrate / activate  (pixi run profiles)
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
profiles/<name>/     one athlete's .env, Strava tokens and data (gitignored)
```

## Using it directly

It's ordinary Python and SQL if you'd rather not go through Claude:

```python
from trainer.store import Store

store = Store()   # the active profile's warehouse
store.sql("""
    SELECT date, planned_name, planned_load, actual_np, lap_count
    FROM planned_vs_actual WHERE date >= '2026-08-01' ORDER BY date
""").show()
```

See [docs/data-store.md](docs/data-store.md) for the tables, and
[docs/reading-data.md](docs/reading-data.md) for what the numbers mean.

## Notes

- Strava allows 100 requests / 15 min and 1000 / day. `pixi run sync` fetches each activity once, caches the raw response under the profile's `data/`, and stops short of the wall. The quota is per Strava app, so athletes with their own apps don't share it.
- Nothing here writes to Strava — it's read-only. Only intervals.icu gets written to, and only to the calendar.
