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
client = IntervalsClient()
```

Run from the repo root with `pixi run python <script>.py`.

## Before writing

1. If `plan.md` exists, read it. It defines targets, zones, the week structure and
   the rules the prescription must satisfy. If it carries instructions for whoever
   plans from it, follow those over anything here.
2. Call `client.events(oldest=..., newest=...)` over the target range to see what's
   already on the calendar. Don't clobber completed or pre-existing sessions.
3. Check `client.athlete()["icu_ftp"]`. If it's `None`, use absolute watts —
   percentage targets won't resolve.

## Writing

- One `create_workouts([...])` call for a whole week, not N single calls.
- Every event gets a stable `external_id` so re-runs upsert instead of duplicating.
- Put the workout in a **file** and run it. Never `python -c "..."` — shell escaping
  mangles the `\n` in descriptions and collapses the workout into one step.

## After writing

Report back the week as a table (day, session, duration, target, TSS) rather than
dumping the API response. Say explicitly which events were created vs. updated,
and flag anything on the calendar you deliberately left alone.
