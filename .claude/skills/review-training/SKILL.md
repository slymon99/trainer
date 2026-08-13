---
name: review-training
description: Pull recent training data from intervals.icu and Strava and assess how the block is going — whether load is ramping as planned, whether prescribed sessions were actually executed, and whether to progress, repeat, or back off. Use when asked how training is going, to review a week or block, to check CTL/fitness/fatigue trends, or whether to keep pushing.
---

# Review training

Read [docs/reading-data.md](../../../docs/reading-data.md) for what each field
means and which source to use.

```python
from trainer import IntervalsClient
client = IntervalsClient()
```

## What to pull

Default to the current block, or the last 6 weeks if no block is defined:

1. `client.wellness(oldest, newest)` — CTL/ATL trend, resting HR, HRV
2. `client.events(oldest, newest)` — what was **prescribed**
3. `client.activities(oldest, newest)` — what was **done**
4. `client.activity_intervals(id)` on the key sessions — per-rep actuals

## How to assess

**Planned vs. actual is the whole review.** A block where CTL is ramping nicely
but the hard sessions are quietly being cut short is failing, and the summary
numbers won't show it.

Work through:

- Is CTL ramping at the rate the plan called for? Judge on **build weeks**, not the block average — a recovery week drags the mean down and makes a healthy ramp look flat.
- Which prescribed sessions were completed, cut short, or skipped?
- On interval sessions, were target watts hit on every rep, or fading on the last two? Fading late reps is the earliest signal of too much load.
- Are resting HR and HRV drifting against the athlete's **own** baseline?

If `plan.md` exists, apply **its** progress/repeat/back-off rules and its check-in
questions rather than inventing criteria. Ask any subjective check-in questions
**before** presenting a conclusion — otherwise the answers get rationalised to fit
a verdict already on screen.

## Reporting

- Lead with the verdict: progress, repeat, or back off — and the one or two numbers that drove it.
- Show planned vs. actual as a table.
- **Flag every assumption.** If a number is missing (RPE, sleep, whether a session was outdoors in heat), say what you assumed and what changes if it's wrong. Don't invent data.
- Don't recommend raising the working FTP just because sessions felt easy. That's a decision the plan's own re-anchoring protocol governs, and sub-threshold work feeling comfortable is expected rather than evidence.
