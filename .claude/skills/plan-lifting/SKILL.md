---
name: plan-lifting
description: Create or update gym sessions as Hevy routines, and review lifting progression. Use when asked to plan a gym or strength session, program lifts, push a lifting week to Hevy, adjust loads, or check whether a lift is progressing.
---

# Plan lifting in Hevy

Read [docs/hevy.md](../../../docs/hevy.md) first — it has the auth, the table
reference, and three constraints that have already caused mistakes: pages cap at
10, **nothing can be deleted over the API**, and routines take absolute
kilograms rather than a %1RM.

Use the client, not raw HTTP:

```python
from trainer import HevyClient
client = HevyClient()
```

Run from the repo root with `pixi run python <script>.py`.

## Before writing

1. Read `plan.md`, especially the **Strength** section — it sets the weekly
   floor, which day takes loaded legs, the reps-in-reserve ceiling, and the
   ramp. Then read `plan/block-*.md` for the week you're programming into. If
   the plan carries instructions for whoever plans from it, follow those over
   anything here.
2. Read what's already in the warehouse rather than the API:
   `SELECT * FROM lift_sets ORDER BY date DESC` for recent loads, and
   `hevy_exercise_templates` to resolve exercise names to ids.
3. Run `pixi run sync --tables lifts` if the store looks stale — the athlete
   enters sets in the app, so the warehouse trails reality by however long since
   the last sync.

## Loads

**Sets, reps and reps-in-reserve are the prescription. Kilograms are a
resolution of it.** Hevy has no %1RM, so absolute weights are unavoidable in the
routine itself — which makes them exactly as prone to going stale as a watt
number written into a bike workout. Keep the relative form in `plan.md` and
resolve to kilograms in the push script, from anchors in `plan/decisions.md`.
Push scripts go in `scripts/`, which is gitignored.

Never invent a load. If there's no anchor for a movement, say so and either ask
or leave the set unweighted for the session to calibrate — Hevy carries forward
whatever gets logged.

## Writing

- **Update the routine in place.** Look it up by title first; a second
  `create_routine` with the same title spends a slot that only the app can
  reclaim. There is no DELETE.
- **Validate every `exercise_template_id` against the catalogue before pushing.**
  A bad id is a 400 on a POST you can't undo, and the check is a local query.
- **Put session-level guidance in the first exercise's `notes`** — routine-level
  `notes` do not come back from the API.
- Label warm-up sets `"type": "warmup"`, or they inflate every volume figure.
- Put the routine in a **file** and run it, never `python -c "..."` — the same
  shell-escaping rule as the bike workouts.

## After writing

Report the session as a table (exercise, sets × reps, load, why) rather than
dumping the API response. Convert to whatever unit the athlete thinks in. Say
which loads came from a recorded anchor and which are estimates awaiting
calibration, and flag anything you deliberately left off.
