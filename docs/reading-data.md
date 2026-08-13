# Reading training data

What's available from each source, and which one to reach for.

> **Read from the store, not the API.** Both sources are synced into
> `data/warehouse/` and queried with SQL — see [data-store.md](data-store.md).
> This doc is the *why*: what each field means, which source owns it, and the
> quirks the sync is working around. Reach for the clients directly only when
> you need something the sync doesn't pull yet.

## Which source

Use **both, joined on activity id** — neither is sufficient alone.

- **intervals.icu** owns everything *modelled or planned*: CTL/ATL/ramp rate, the
  wellness series (resting HR, HRV, sleep), and the calendar of prescribed workouts.
- **Strava** owns everything *measured*: average and normalized power, HR, and the
  per-lap splits that tell you whether each rep actually hit target.

The reason you need Strava for the second half: when an activity was ingested
**from Strava**, intervals.icu will not serve its detail back over the API. You get
a stub, and the intervals endpoint 422s:

```python
client.activity("19694957323")
# {"id": "...", "source": "STRAVA", "_note": "STRAVA activities are not available via the API"}
client.activity_intervals("19694957323")
# HTTPError: 422 Unprocessable Entity
```

This is a limit on *Strava-sourced* activities specifically. Wellness, events, and
the CTL/ATL model are unaffected, and files uploaded to intervals.icu directly
still return full detail.

## intervals.icu

```python
from trainer import IntervalsClient
client = IntervalsClient()

client.athlete()                                   # FTP, LTHR, zones, resting HR
client.activities(oldest="2026-07-01", newest="2026-08-13")  # ids + dates (stubs)
client.activity_intervals(activity_id)             # per-rep actuals — 422s on Strava-sourced
client.wellness(oldest="2026-07-01", newest="2026-08-13")
client.events(oldest="2026-08-17", newest="2026-08-23")   # what was *planned*
```

Fields that matter for judging a block:

| Field | Where | Meaning |
|---|---|---|
| `ctl`, `atl` | wellness | chronic (fitness) and acute (fatigue) load |
| `restingHR`, `hrv` | wellness | readiness signals |
| `icu_training_load` | event | TSS **prescribed** for a planned session |
| `moving_time` | event | prescribed duration |
| `ftp`, `lthr`, `max_hr` | `athlete()["sportSettings"]` | what intervals.icu models with — verify against the plan |

Per-activity fields (`icu_training_load`, `icu_weighted_avg_watts`, `icu_eftp`,
`icu_intervals`) are documented by intervals.icu but come back **empty for
Strava-sourced rides**. Get the equivalents from Strava — see below.

**Planned vs. actual is the whole game.** `events()` gives the prescription and
`activities()` gives what happened; comparing them is how you tell whether a block
is working or the athlete is quietly failing sessions.

## Joining the two

**The id intervals.icu returns for a Strava-sourced activity *is* the Strava
activity id.** So the stub is still useful — it tells you which ids exist on which
day, and Strava fills in the rest.

The sync does this join for you; it's the `activities` view:

```python
from trainer.store import Store

store = Store()
store.sql("""
    SELECT date, name, np, average_heartrate, lap_count
    FROM activities WHERE date >= '2026-08-10'
""").show()
```

`strava_laps` is the replacement for `activity_intervals()` — on a structured
workout the laps are the reps, so this is where you check whether rep 3 held
target watts and what HR it cost:

```python
store.sql("""
    SELECT lap_index, moving_time/60 AS min, average_watts, average_heartrate
    FROM strava_laps WHERE activity_id = ? ORDER BY lap_index
""", activity_id).show()
```

**Per-activity TSS** is not in the stub either. Two ways to recover it:

| Method | How | Use when |
|---|---|---|
| Compute from NP | `(NP/FTP)**2 * hours * 100` | You want it per activity. Uses *your* working FTP, not intervals.icu's. |
| Back-solve from CTL | `TSS = (CTL_t - CTL_t-1)/K + CTL_t-1`, `K = 1-exp(-1/42)` | You want the number intervals.icu actually modelled with |

They will not agree exactly — intervals.icu computes NP with its own smoothing and
uses the FTP configured in **sport settings**, which is not necessarily the working
FTP in the plan. Check `athlete()["sportSettings"]` before trusting either.

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
whole season will blow through that. This is the reason the store exists: `pixi
run sync` fetches each activity once, caches the raw response, and stops short
of the wall. `client.budget.remaining` reports what's left in the window.

## Judging a block

Rough order of operations, all of which is just querying the store:

1. `iv_wellness` over the block — is CTL actually ramping, and at what rate?
2. `planned_vs_actual` — which prescribed sessions were completed, cut short, or skipped?
3. `strava_laps` on the key sessions — were the target watts actually hit, or were later reps fading? And **what HR did they cost**: watts on target at a HR well below the expected band is a re-anchoring signal, not a good session.
4. `resting_hr` / `hrv` trend against the athlete's own baseline, not population norms.

Interpretation belongs in `plan.md`, not here. This doc tells you what the numbers
are; the athlete's plan is what says which of them justify progressing, repeating,
or backing off a week.
