# trainer

Thin clients over intervals.icu, Strava and Hevy, plus skills that use them to
review training, write workouts, and revise a plan.

## Ground rules

**This repo is private**, so health values in committed files are fine — a real
CTL number in a doc example is clearer than a placeholder. Two things still stay
out of git: `.env` and `.strava_tokens.json`, because credentials leak
independently of who can see the repo. `data/` and `__marimo__/` are gitignored too,
but only because they're regenerable — not secret. Athlete-specific long-term plans
do not belong in this repository. Do not invent an athlete profile or training plan
from repository context.

**Keep these documents currently correct rather than appending to them.** When a rule
changes, rewrite it — don't leave a dated amendment beside it explaining what it used
to say.

**Preserve the requested target units.** intervals.icu accepts percentages, zones,
absolute watts, heart rate, pace, and cadence. Use the units the user supplies rather
than importing assumptions from an old plan. When percentages are requested, remember
that intervals.icu resolves them against the athlete's current sport settings.

**Lifting has no `%FTP`.** Hevy routines take absolute kilograms and the API offers
no %1RM, so loads must be used only when the user supplies or approves them.
See `docs/hevy.md`.

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
- `docs/stats.md` — conservative HRV/resting-HR summaries based on individual baselines

Skills in `.claude/skills/` should stay thin and link to these docs rather than
restating them.
