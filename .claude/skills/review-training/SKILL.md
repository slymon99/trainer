---
name: review-training
description: Pull recent training data from intervals.icu and Strava and assess how the block is going — whether load is ramping as planned, whether prescribed sessions were actually executed, and whether to progress, repeat, or back off. Use when asked how training is going, to review a week or block, to check CTL/fitness/fatigue trends, or whether to keep pushing.
---

# Review training

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

Default to the current block, or the last 6 weeks if no block is defined:

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

If `plan.md` exists, apply **its** rules and its check-in question rather than
inventing criteria. Ask any subjective check-in questions **before** presenting a
conclusion — otherwise the answers get rationalised to fit a verdict already on
screen. Append the answer to `plan/check-ins.md` if that file exists.

**Check what a session was designed to feel like before reading how it felt as a
signal.** A session prescribed as sub-threshold, coming in at a moderate RPE with HR
proportional to power, is the design working — not evidence the target is soft. The
plan may not carry a rule for this; the misread is on you either way. `plan/decisions.md`
has the worked example.

## Reporting

- Lead with the verdict: progress, repeat, or back off — and the one or two numbers that drove it.
- Show planned vs. actual as a table.
- **Flag every assumption.** If a number is missing (RPE, sleep, whether a session was outdoors in heat), say what you assumed and what changes if it's wrong. Don't invent data.
- Don't recommend raising the working FTP just because sessions felt easy. That's a decision the plan's own re-anchoring protocol governs, and sub-threshold work feeling comfortable is expected rather than evidence.
