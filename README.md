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

### Strava (optional)

Intervals.icu already imports your Strava activities, so **you only need this for
raw streams, segment efforts, or photos.** Skip it otherwise.

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

### Your plan

Write a `plan.md` at the repo root. It's the brief Claude reads before prescribing
anything — your goal, zones, weekly structure, and the rules for when to push
versus back off. There's no required format; write it the way you'd brief a coach,
or ask Claude to interview you and draft it.

The one thing worth being explicit about is **decision rules** — what has to be
true to progress, repeat, or back off a week. Without those, a plan drifts into
"whatever felt good", and neither you nor Claude can tell whether it's working.

**`plan.md` is gitignored.** This repo is public and the plan will hold weight,
resting HR, HRV and physiological history. Keep it that way.

## Layout

```
trainer/
  intervals.py       IntervalsClient — activities, wellness, calendar events
  strava.py          StravaClient — activities, streams, segments
  strava_auth.py     one-time OAuth flow
docs/
  reading-data.md        what each field means, which source to use
  intervals-workouts.md  workout-text syntax and the calendar API
.claude/skills/
  review-training/   pull data, assess the block
  create-workouts/   write workouts to the calendar
  adjust-plan/       revise plan.md
plan.md              your plan (gitignored)
.env                 your credentials (gitignored)
```

## Using it directly

The clients are ordinary Python if you'd rather not go through Claude:

```python
from trainer import IntervalsClient

client = IntervalsClient()
for a in client.activities(oldest="2026-08-01", newest="2026-08-13"):
    print(a["start_date_local"][:10], a["name"], a["icu_training_load"])
```

See [docs/reading-data.md](docs/reading-data.md) for the full surface.

## Notes

- Strava allows 100 requests / 15 min and 1000 / day. Cache to `data/` (gitignored) rather than re-fetching streams.
- Nothing here writes to Strava — it's read-only. Only intervals.icu gets written to, and only to the calendar.
