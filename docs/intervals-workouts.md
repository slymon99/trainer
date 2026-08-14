# Writing workouts to intervals.icu

Reference for building structured workouts on the calendar. The workout-text
syntax in [§ Workout text syntax](#workout-text-syntax) is the part worth
reading closely — it's the only non-obvious piece.

## Creating

```python
from trainer import IntervalsClient

client = IntervalsClient()
client.create_workout(
    category="WORKOUT",
    start_date_local="2026-08-20T00:00:00",   # local date/time, no timezone
    type="Ride",                               # Ride, Run, Swim, WeightTraining, ...
    name="Sweet spot 3x12",
    description="- 15m 60%\n\n3x\n- 12m 90%\n- 5m 55%\n\n- 10m 55%",
    external_id="plan-2026-08-20-ss",
)
```

For several workouts at once (a week, a block), use `client.create_workouts([...])`
with a list of the same dicts — one HTTP call instead of N.

**Always set `external_id`** to a stable string you choose (e.g. `"plan-week3-tue"`).
With the default `upsert=True`, re-running the same call updates that event instead
of creating a duplicate, which makes edits and re-runs safe. Without it, every call
creates a new event.

## Two gotchas that have actually bitten

1. **Run multi-step workouts from a file, never `python -c "..."`.** Passing a
   description through the shell turns `\n` escapes into literal backslash-n, and
   intervals.icu then parses the whole workout as a single step. A 210-minute
   session silently became 160 minutes that way.
2. **`%` targets resolve against *sport settings* FTP, not `athlete()["icu_ftp"]`.**
   The athlete-level `icu_ftp` is often `None` while cycling sport settings carry a
   perfectly good `ftp` — percentages still resolve, and intervals.icu returns a
   normal `icu_training_load`. Check the sport-settings row for the activity type:

   ```python
   [s for s in client.athlete()["sportSettings"] if "Ride" in s["types"]]
   ```

   Set `indoor_ftp` alongside `ftp`. If they diverge, the same `%` workout means
   different watts indoors and out, and the CTL series quietly mixes both.

## Deleting and finding

```python
client.delete_events(external_ids=["plan-2026-08-20-ss"])
client.delete_events(ids=[128792719])

client.events(oldest="2026-08-18", newest="2026-08-24")   # each has an `id`
```

Always call `events()` over the target range before writing a week, so you don't
clobber or duplicate something already there.

## Workout text syntax

The `description` field. Plain text, one step per line starting with `-`.
Intervals.icu parses durations, targets and cadence automatically.

**Basic line:** `- [duration or distance] [target] [optional cadence]`

| Element | Syntax |
|---|---|
| Duration | `1h`, `10m`, `30s`, `5m30s` — `m` is **minutes**, not meters |
| Distance | `500mtr`, `2km`, `10km`, `1mi` |
| Power | `75%` (of FTP), `95-105%`, `220w`, `200-240w`, `Z2`, `Z3-Z4`, `60% MMP 5m` |
| Heart rate | `70% HR` (% max), `95% LTHR`, `Z2 HR` |
| Pace | `60% Pace`, `Z2 Pace`, `5:00/km Pace`, `3:00/100m-4:00/100m Pace` |
| Cadence | append after target: `- 10m 75% 90rpm`, `- 12m 85% 90-100rpm` |
| Ramp | `- 10m ramp 50%-75%`, `- 15m ramp 60%-90% 85rpm` |
| Free ride (ERG off) | `- 20m freeride` |

**Repeats:** put `Nx` on its own line immediately before the steps to repeat, with
a **blank line before and after** the block:

```
- 10m 60%

3x
- 5m 90%
- 3m 55%

- 10m 55%
```

Nested repeats are not supported.

**Text cues:** any words before the duration become a step cue — `- Warmup 10m 60%`,
`- Recovery 3m 50%`.

**Markdown** (headings, bold, tables, `---`) is allowed in the description for
readability; the workout parser ignores it.

## Worked example: a full week

```python
from trainer import IntervalsClient

client = IntervalsClient()
client.create_workouts([
    {
        "category": "WORKOUT", "start_date_local": "2026-08-17T00:00:00", "type": "Ride",
        "name": "Endurance", "description": "- 1h 65%",
        "external_id": "week1-mon",
    },
    {
        "category": "WORKOUT", "start_date_local": "2026-08-19T00:00:00", "type": "Ride",
        "name": "VO2 max 5x4",
        "description": "- 15m 60%\n\n5x\n- 4m 115%\n- 4m 55%\n\n- 10m 55%",
        "external_id": "week1-wed",
    },
])
```

## Reference

- Full endpoint list / schemas: `curl -s https://intervals.icu/api/v1/docs | python3 -m json.tool`
- `create_workouts` → `POST /api/v1/athlete/{id}/events/bulk?upsert=true`
- `delete_events` → `PUT /api/v1/athlete/{id}/events/bulk-delete`
