# Basic training stats

`trainer.stats.readiness(rows)` summarizes recent `hrv` and `resting_hr` values
from `iv_wellness` against the same athlete's preceding baseline. It uses a
seven-day baseline and a three-day recent window by default. A day is flagged
when HRV is below the baseline mean by one baseline standard deviation or
resting HR is at least 3 bpm above baseline; two flagged days produce
`elevated`, one `mixed`, and none `normal`.

These are intentionally simple screening signals, not a medical assessment and
not an automatic training prescription. Missing values are ignored, and too
few rows raise an error. Look at sleep, illness, soreness, heat, and subjective
stress before acting on the result.

```python
from trainer.stats import readiness
from trainer.store import Store

rows = Store().sql("""
    SELECT date, hrv, resting_hr
    FROM iv_wellness
    WHERE date >= current_date - INTERVAL 14 DAY
    ORDER BY date
""").fetchall()
print(readiness([{"date": r[0], "hrv": r[1], "resting_hr": r[2]} for r in rows]))
```

The design follows research showing that morning lnRMSSD/HRV is most useful
when interpreted against an individual's baseline and that HRV-guided training
can individualize the timing of harder sessions. The evidence does not justify
calling one abnormal reading “fatigue,” so this helper requires a short run of
recent observations and reports a signal rather than a verdict.

Sources: [Schmitt et al. (2015), review of HRV and athlete fatigue](https://pubmed.ncbi.nlm.nih.gov/26635629/),
[Kiviniemi et al. (2007), daily HRV-guided endurance training](https://pubmed.ncbi.nlm.nih.gov/17849143/),
and [Bellenger et al. (2016), individualized HRV training prescription](https://pubmed.ncbi.nlm.nih.gov/26909534/).
