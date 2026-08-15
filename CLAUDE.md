# trainer

Thin clients over intervals.icu, Strava and Hevy, plus skills that use them to
review training, write workouts, and revise a plan.

## Ground rules

**This repo is private**, so health values in committed files are fine — a real
CTL number in a doc example is clearer than a placeholder. Two things still stay
out of git: `.env` and `.strava_tokens.json`, because credentials leak
independently of who can see the repo. `data/` and `__marimo__/` are gitignored too,
but only because they're regenerable — not secret. `plan.md` and `plan/` **are**
tracked, deliberately: their history is the record of how the plan evolved.

**Read `plan.md` before prescribing anything.** It's the athlete's brief: goal,
zones, weekly structure, and the rules for when to push or back off. It's free-form
and may carry its own instructions for whoever plans from it — follow those over
anything here. If it doesn't exist, say so rather than inventing an athlete profile.

`plan/` holds the parts with a different lifecycle — `block-*.md` (current block),
`roadmap.md`, `decisions.md` (re-anchor history and the evidence behind the plan's
key numbers), `check-ins.md`. Read the block file when planning a week; read
`decisions.md` when re-anchoring FTP.

**Keep these documents currently correct rather than appending to them.** When a rule
changes, rewrite it — don't leave a dated amendment beside it explaining what it used
to say.

**Prescribe in `%FTP`, never absolute watts.** intervals.icu resolves percentages
against sport settings, so re-anchoring updates every scheduled workout at once. A
watt number written into a plan or a workout goes stale silently — that is the
documented root cause of this athlete's 2026 plateau. Neuromuscular targets
(sprints) are the one exception and the plan names them.

**Lifting has no `%FTP`.** Hevy routines take absolute kilograms and the API offers
no %1RM, so the same staleness trap is unavoidable in the tool. Keep the
prescription relative in `plan.md` — sets, reps, reps in reserve — and resolve to
kilograms at push time from anchors in `plan/decisions.md`. See `docs/hevy.md`.

**Don't invent data.** If a number is missing, state the assumption and what
changes if it's wrong.

## Working here

- Run from the repo root: `pixi run python script.py`.
- **Read training data from the store, not the API.** `pixi run sync` refreshes
  it; query it with `Store().sql(...)` or `pixi run sql`. Strava allows 100
  requests per 15 minutes, so a script that re-pulls what's already on disk is a
  bug. Use the clients directly only for something the sync doesn't cover yet.
- Use `IntervalsClient` / `StravaClient`, never raw HTTP — auth, token refresh,
  retries and the rate-limit budget are handled.
- Multi-step workout descriptions must run from a **file**, never `python -c "..."`; shell escaping collapses `\n` and silently merges the workout into one step.
- `pixi run ruff check .` and `pixi run test` before committing.

## Docs

- `docs/data-store.md` — the local tables, how to query and sync them
- `docs/reading-data.md` — fields, sources, rate limits
- `docs/intervals-workouts.md` — workout-text syntax, calendar API
- `docs/hevy.md` — the strength log: routines, sets, and why loads go stale there

Skills in `.claude/skills/` should stay thin and link to these docs rather than
restating them.
