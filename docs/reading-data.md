# Reading training data

What's available from each source, and which one to reach for.

## Which source

Intervals.icu already ingests Strava, so **intervals.icu is the default** — it has
everything Strava has plus the modelled load numbers. Reach for Strava only when
you need something intervals.icu doesn't carry: raw streams at full resolution,
segment efforts, kudos/social data, or photos.

## intervals.icu

```python
from trainer import IntervalsClient
client = IntervalsClient()

client.athlete()                                   # FTP, LTHR, zones, resting HR
client.activities(oldest="2026-07-01", newest="2026-08-13")
client.activity_intervals(activity_id)             # per-rep actuals
client.wellness(oldest="2026-07-01", newest="2026-08-13")
client.events(oldest="2026-08-17", newest="2026-08-23")   # what was *planned*
```

Fields that matter for judging a block:

| Field | Where | Meaning |
|---|---|---|
| `icu_training_load` | activity | TSS for that session |
| `icu_ftp`, `icu_eftp` | activity / athlete | prescribed FTP vs. what the ride implies |
| `icu_weighted_avg_watts` | activity | normalized power |
| `ctl`, `atl` | wellness | chronic (fitness) and acute (fatigue) load |
| `restingHR`, `hrv` | wellness | readiness signals |
| `icu_intervals` | activity_intervals | actual watts/HR **per rep** |

**Planned vs. actual is the whole game.** `events()` gives the prescription and
`activities()` gives what happened; comparing them is how you tell whether a block
is working or the athlete is quietly failing sessions.

## Strava

```python
from trainer import StravaClient
client = StravaClient()

client.activities(limit=30)          # after=/before= are Unix timestamps
client.activity(activity_id)         # laps + segment efforts
client.activity_streams(activity_id) # time series: watts, heartrate, altitude...
client.stats()                       # YTD / all-time totals
```

Strava's list endpoint returns summary objects only — `client.activity(id)` is
needed for laps and segment efforts, and costs an extra request each.

**Rate limits:** 100 requests per 15 minutes, 1000 per day. Pulling streams for a
whole season will blow through that; pull selectively and cache to `data/`
(gitignored) rather than re-fetching.

## Judging a block

Rough order of operations, all of which is just reading the above:

1. `wellness()` over the block — is CTL actually ramping, and at what rate?
2. `events()` vs `activities()` — which prescribed sessions were completed, cut short, or skipped?
3. `activity_intervals()` on the key sessions — were the target watts actually hit, or were later reps fading?
4. `restingHR` / `hrv` trend against the athlete's own baseline, not population norms.

Interpretation belongs in `plan.md`, not here. This doc tells you what the numbers
are; the athlete's plan is what says which of them justify progressing, repeating,
or backing off a week.
