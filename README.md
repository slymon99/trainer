# trainer

Let Claude read your training data, judge how a block is going, and write the next
week to your calendar.

It's a thin Python client over [intervals.icu](https://intervals.icu) and
[Strava](https://www.strava.com), plus a set of Claude Code skills and reference
docs. There's no app and no server — you talk to Claude, and Claude uses these.

**What you can ask for:**

- *"How did the last four weeks actually go?"* — pulls CTL, planned vs. completed sessions, and per-rep power, then gives a progress / repeat / back off verdict.
- *"Build next week."* — writes structured workouts straight to the intervals.icu calendar.
- *"I was sick for ten days, redo the block."* — revises the plan document and the calendar together.

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

### Your plan

Write a `plan.md` at the repo root. It's the brief Claude reads before prescribing
anything — your goal, zones, weekly structure, and the rules for when to push
versus back off. There's no required format; write it the way you'd brief a coach,
or ask Claude to interview you and draft it.

The one thing worth being explicit about is **decision rules** — what has to be
true to progress, repeat, or back off a week. Without those, a plan drifts into
"whatever felt good", and neither you nor Claude can tell whether it's working.

Two things this plan learned the hard way, both worth copying:

- **Write targets as percentages of FTP, not watts.** intervals.icu resolves `%`
  against your sport settings, so re-testing updates every scheduled workout at
  once. Absolute watts scattered through a plan go stale silently, and training off
  a stale FTP is the classic way to spend a season getting nowhere.
- **Split anything that grows.** Block detail expires in a month and check-in logs
  grow forever; neither belongs in the file that gets read before every session.
  Optional `plan/` files keep the brief short — see the layout below.

**`plan.md` is tracked**, deliberately: its history is worth having, and this repo
is private. It holds weight, resting HR, HRV and physiological history, so if you
fork this, decide that deliberately — untrack it *before* the first commit, since
rewriting history is the only way to remove it afterwards.

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
.claude/skills/
  review-training/   assess the block
  create-workouts/   write workouts to the calendar
  adjust-plan/       revise plan.md
data/                your training data (gitignored)
plan.md              the standing brief — read before every prescription
plan/
  block-1.md         the current block; expires when the block does
  roadmap.md         later blocks and the test schedule
  decisions.md       re-anchor history and the evidence behind the key numbers
  check-ins.md       weekly subjective check-in log
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
