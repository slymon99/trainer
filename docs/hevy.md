# Hevy — the strength log

Hevy is where gym sessions are entered and where lifting prescriptions are
pushed. `HevyClient` wraps it; `pixi run sync` pulls it into the warehouse.

Auth is an `api-key` header — **not** Bearer, and not OAuth. The key comes from
<https://hevy.com/settings?developer> and needs **Hevy Pro**. It lives in the
athlete's `profiles/<name>/.env` as `HEVY_API_KEY`.

API docs: <https://api.hevyapp.com/docs/> (Swagger UI; the spec itself is
embedded in `swagger-ui-init.js` rather than served as JSON).

```bash
pixi run check hevy                     # who am I, how many sessions
pixi run sync --tables lifts,exercises  # pull sessions and the catalogue
```

## The three constraints that shape everything

**Pages are capped at 10 items** (100 for exercise templates). Anything that
walks history is a loop, not a request. At one or two gym sessions a week that
is cheap — a month of sessions is one page — but a full backfill of a busy
lifting year is ~50 requests. There is no documented rate limit; the client
retries 5xx and surfaces a 429 as `RateLimitExceeded` like the others.

**Nothing can be deleted through the API.** There is no DELETE on workouts,
routines, folders, exercise templates or body measurements. A routine written
by mistake can only be removed by hand in the app, and the account caps how
many routines you can have — `POST /v1/routines` returns 403 when you hit it.
So the push model is *update in place*, never create-per-week. See
[Pushing a routine](#pushing-a-routine).

**Routines carry absolute kilograms.** There is no %1RM — no equivalent of the
`%FTP` that keeps every scheduled bike workout correct through a re-anchor.
This is exactly the staleness trap `CLAUDE.md` names, and the API gives no way
out of it. The mitigation is procedural, not technical:

- The **prescription comes from the user** — preserve sets, reps, and loads
  exactly, and ask before filling in anything missing.

A weight written straight into a Hevy routine should be treated as the user's
explicit instruction, not as an inferred progression.

## Units

The API accepts and returns **kilograms only** (`weight_kg`). The athlete thinks
in pounds, so the push script converts at the boundary and the app is set to
display lb. Two places this bites:

- Converting on the way in and reading back raw kg looks wrong until you
  convert back — `lb = kg / 0.45359237`.
- A round number in lb is not a round number in kg. Push the lb figure through
  the conversion rather than rounding the kg, or 85 lb becomes 38.5 kg becomes
  84.9 lb in the app.

## Routines vs workouts

| | |
|---|---|
| **Routine** | A template you start a session *from* — the prescription. Created and updated over the API. |
| **Workout** | A completed session, with what was actually lifted. Read over the API; entered in the app. |

A workout started from a routine carries `routine_id`, which is the only link
Hevy gives between prescription and execution. It's the strength analogue of
intervals.icu's `paired_activity_id`, and it's set only if the session was
actually started from the routine rather than logged freehand.

### Pushing a routine

Push scripts live in `scripts/`, which is gitignored — they carry personal
targets, so the worked example is here rather than in the tree:

```python
client.create_routine(
    title="Tue — Heavy",
    exercises=[
        {
            "exercise_template_id": "3D0C7C75",   # Goblet Squat
            "rest_seconds": 90,
            "notes": "Deliberately trivial.",
            "sets": [{"type": "normal", "reps": 8, "weight_kg": 13.61}],
        },
    ],
)
```

Rules learned the hard way:

- **Resolve every `exercise_template_id` against the catalogue before writing.**
  A bad id is a 400 on a POST you cannot undo. The 451 built-ins are in
  `hevy_exercise_templates`, so this is a local query, not a request.
- **Look up the routine by title and `update_routine` if it exists.** A second
  `create_routine` with the same title spends another slot.
- **Put session-level guidance in the first exercise's `notes`.** The API
  accepts `notes` on the routine body, but the `Routine` read schema has no
  such field — anything put there does not come back, and may not be stored at
  all. Per-exercise `notes` round-trip fine.
- Set `type` per set: `normal`, `warmup`, `dropset`, `failure`. Warm-ups are
  excluded from every volume figure downstream, so label them.
- `rep_range: {"start": 8, "end": 12}` exists as an alternative to a fixed
  `reps`.
- Request field names differ from response field names on custom exercises:
  you send `muscle_group` / `equipment_category`, you read back
  `primary_muscle_group` / `equipment`.

## Tables

| Table | Grain | What it's for |
|---|---|---|
| `hevy_workouts` | one row per session | date, duration, set counts, total volume |
| `hevy_sets` | **one row per set** | weight, reps, RPE — where progression is actually judged |
| `hevy_exercise_templates` | one row per exercise | the catalogue; join on `exercise_template_id` |

And one view:

| View | What it is |
|---|---|
| `lift_sets` | `hevy_sets` + session title + muscle group, with an estimated 1RM |

`lift_sets.est_1rm_kg` is **Epley** — `w × (1 + reps/30)`. It's a model, not a
measurement, and it drifts high past about 12 reps, so it's NULL there rather
than quietly wrong.

```sql
-- Is the bench actually moving?
SELECT date, weight_kg, reps, est_1rm_kg
FROM lift_sets
WHERE exercise_title LIKE 'Bench Press%' AND set_type = 'normal'
ORDER BY date DESC;
```

### Things worth knowing about the data

- **`hevy_workouts.date` is the UTC date of `start_time`.** Hevy timestamps
  carry no offset, so there is nothing to localise with. For an evening session
  that's the local date too, except after ~23:00 British Summer Time.
- **`volume_kg` and `working_set_count` exclude warm-ups.** Warm-ups scale with
  the working weight, so counting them scores a heavier session as more work
  than it was.
- **A session logged freehand has no `routine_id`**, so it can't be matched
  back to what was prescribed. Starting from the routine in the app is what
  makes the comparison possible.

## How the sync decides what to fetch

| Step | Window | Why |
|---|---|---|
| `lifts` | watermark − 30d → today, widened by the events feed | sessions get edited and deleted after the fact |
| `exercises` | once, unless `--refresh` | the catalogue only changes when a custom exercise is added |

`lifts` re-reads its window whole and writes with a **replace range**, so a
session deleted in the app disappears from `hevy_workouts` and `hevy_sets`
together.

That alone only covers the last 30 days. `GET /v1/workouts/events?since=` is
what covers the rest: it reports updates *and deletions* since a timestamp, and
the sync uses it to widen the replace range far enough back to reach whatever
changed. The list endpoint can only ever show you what still exists — the
events feed is the one place a deletion is reported at all.

For a deletion the feed gives only an id, so the session's date is looked up in
the warehouse. A deleted session that was never synced locally is therefore
invisible, which is correct: there's nothing to remove.

The `since` watermark is `max(_synced_at)`, read with `epoch()`. Reading it as a
timestamp makes DuckDB reach for `pytz`, and rendering it with `strftime`
converts to local time while still stamping a `Z` on it — a silent four-hour
shift.
