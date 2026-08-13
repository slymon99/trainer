# trainer

Thin clients over intervals.icu and Strava, plus skills that use them to review
training, write workouts, and revise a plan.

## Ground rules

**This repo is public. `plan.md`, `.env`, `.strava_tokens.json` and `data/` are
gitignored and must stay that way** — `plan.md` holds weight, resting HR, HRV and
physiological history. Never quote personal health values into a committed file,
a commit message, or a docs example — use obvious placeholders instead.

**Read `plan.md` before prescribing anything.** It's the athlete's brief: goal,
zones, weekly structure, and the rules for when to push or back off. It's free-form
and may carry its own instructions for whoever plans from it — follow those over
anything here. If it doesn't exist, say so rather than inventing an athlete profile.

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

Skills in `.claude/skills/` should stay thin and link to these docs rather than
restating them.
