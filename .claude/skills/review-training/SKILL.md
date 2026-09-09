---
name: review-training
description: Summarize recent training data and basic readiness signals without inventing a training plan.
---

# Summarize training

Everything is already on disk, normalised and joined. Refresh it, then query —
don't call the APIs directly.

```bash
pixi run sync
```

```python
from trainer.store import Store
store = Store()
```

[docs/data-store.md](../../../docs/data-store.md) has the tables and views;
[docs/reading-data.md](../../../docs/reading-data.md) has what each field means
and the TSS-recovery formulas.

## What to pull

Default to the last 14 days unless the user gives a different window:

1. `iv_wellness` — CTL/ATL trend, resting HR, HRV
2. `planned_vs_actual` — prescription against execution, already joined
3. `strava_laps` — per-rep actuals for the key sessions
4. `iv_athlete` — the FTP/LTHR intervals.icu was modelling with **at the time**

```python
store.sql("""
    SELECT date, planned_name, planned_load, actual_secs/60 AS actual_min, actual_np
    FROM planned_vs_actual WHERE date >= ? ORDER BY date
""", block_start).show()
```

If a session is missing its laps, `pixi run sync --details 20` fetches them;
Strava's quota means the store holds recent activities in full and older ones
as summaries.

## How to assess

**Planned vs. actual is the whole review.** A block where CTL is ramping nicely
but the hard sessions are quietly being cut short is failing, and the summary
numbers won't show it.

Work through:

- Is CTL ramping at the rate the plan called for? Judge on **build weeks**, not the block average — a recovery week drags the mean down and makes a healthy ramp look flat.
- Which prescribed sessions were completed, cut short, or skipped?
- On interval sessions, were target watts hit on every rep, or fading on the last two? Fading late reps is the earliest signal of too much load.
- Are resting HR and HRV drifting against the athlete's **own** baseline?

Use `trainer.stats.readiness()` for the HRV/resting-HR summary. Report the
underlying dates and values. This is a screening signal, not a diagnosis or an
automatic instruction to change training.

**Check what a session was designed to feel like before reading how it felt as a
signal.** A session prescribed as sub-threshold, coming in at a moderate RPE with HR
proportional to power, is the design working — not evidence the target is soft.

## Reporting

- Lead with observed facts and the one or two numbers that drove the summary.
- Show planned vs. actual as a table.
- **Flag every assumption.** If a number is missing (RPE, sleep, whether a session was outdoors in heat), say what you assumed and what changes if it's wrong. Don't invent data.
- Don't recommend changing FTP from repository context or a single easy session.
  Report the evidence and leave prescription changes to an explicit user request.
