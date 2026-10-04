---
name: create-workouts
description: Create, update, or delete planned workouts on the user's intervals.icu calendar. Use when asked to schedule a workout, build a training week or block, add intervals/structured sessions to the calendar, or modify/remove planned workouts on intervals.icu.
---

# Create intervals.icu workouts

Read [docs/intervals-workouts.md](../../../docs/intervals-workouts.md) before
writing anything — it has the workout-text syntax, the `external_id`/upsert rule,
and two gotchas that have caused silent corruption.

Use the client, not raw HTTP:

```python
from trainer import IntervalsClient
client = IntervalsClient()   # the active profile's athlete
```

Run from the repo root with `pixi run python <script>.py`.

**Know whose calendar this is.** Several athletes share this repo. Before
writing, say which profile is active (`pixi run profiles`) and confirm it's the
athlete the user means; switch with `pixi run activate <name>`. Writes refuse
to go out until `pixi run check intervals` has recorded who the profile's key
belongs to.

## Before writing

1. Use only the workout details the user supplied. Ask one concise question for
   any missing field that materially changes the workout; do not infer a plan,
   progression, or intensity.
2. Call `client.events(oldest=..., newest=...)` over the target range to see what's
   already on the calendar. Don't clobber completed or pre-existing sessions.
3. Check the **sport settings** `ftp` for the activity type — that's what `%` targets
   resolve against. Athlete-level `icu_ftp` is often `None` and doesn't matter.

## Preserve the user's targets

Preserve the user's target units exactly. `%FTP` is useful when the user asks for
it, but never convert watts, heart rate, cadence, or RPE into another target.

Two consequences worth knowing:

- **`ftp` and `indoor_ftp` are separate fields.** If they diverge, the same workout
  means different watts indoors and out. Check both.
- **Some targets genuinely aren't a fraction of FTP** — neuromuscular sprints are
  ~3× FTP and don't scale with it. Those get an absolute range, deliberately wide so
  no head unit treats it as a number to hold, and they don't change at a re-anchor.
  The plan should say which targets these are.

## Writing

- One `create_workouts([...])` call for a whole week, not N single calls.
- Every event gets a stable `external_id` so re-runs upsert instead of duplicating.
- Put the workout in a **file** and run it. Never `python -c "..."` — shell escaping
  mangles the `\n` in descriptions and collapses the workout into one step.

## After writing

Report back the week as a table (day, session, duration, target, TSS) rather than
dumping the API response. Say explicitly which events were created vs. updated,
and flag anything on the calendar you deliberately left alone.
