"""Small, deliberately conservative training-readiness statistics.

These functions operate on rows already read from ``Store``.  They do not
diagnose illness or decide what someone should train; they summarize recent
values against that athlete's own preceding baseline.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from statistics import mean, median, stdev


def _number(row: Mapping, key: str) -> float | None:
    value = row.get(key)
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def readiness(
    rows: Iterable[Mapping], *, baseline_days: int = 7, recent_days: int = 3
) -> dict:
    """Summarize recent HRV and resting-HR changes.

    ``rows`` should be ordered oldest-to-newest.  The baseline is the valid
    observations immediately before the recent window.  A signal is counted
    on a recent day when HRV is below the baseline mean by one baseline SD or
    resting HR is at least 3 bpm above its baseline mean.  The result is
    ``normal``, ``mixed``, or ``elevated`` based on the number of recent days
    carrying either signal.  Thresholds are arguments/clearly named constants,
    not claims of a universal clinical cutoff.
    """

    values = list(rows)
    if len(values) < baseline_days + recent_days:
        raise ValueError("need at least baseline_days + recent_days rows")
    baseline = values[-(baseline_days + recent_days) : -recent_days]
    recent = values[-recent_days:]
    hrv = [_number(row, "hrv") for row in baseline]
    rhr = [_number(row, "resting_hr") for row in baseline]
    hrv = [v for v in hrv if v is not None]
    rhr = [v for v in rhr if v is not None]
    if not hrv and not rhr:
        raise ValueError("baseline has no HRV or resting_hr values")

    hrv_mean = mean(hrv) if hrv else None
    hrv_sd = stdev(hrv) if len(hrv) >= 2 else None
    rhr_mean = mean(rhr) if rhr else None
    days = []
    for row in recent:
        hv, hr = _number(row, "hrv"), _number(row, "resting_hr")
        hrv_low = bool(hv is not None and hrv_mean is not None and hrv_sd and hv < hrv_mean - hrv_sd)
        rhr_high = bool(hr is not None and rhr_mean is not None and hr >= rhr_mean + 3)
        days.append({"date": row.get("date"), "hrv": hv, "resting_hr": hr,
                     "hrv_low": hrv_low, "rhr_high": rhr_high,
                     "signal": hrv_low or rhr_high})
    signals = sum(day["signal"] for day in days)
    status = "elevated" if signals >= 2 else "mixed" if signals == 1 else "normal"
    return {
        "status": status,
        "signal_days": signals,
        "recent_days": days,
        "baseline": {
            "hrv_mean": hrv_mean,
            "hrv_sd": hrv_sd,
            "resting_hr_mean": rhr_mean,
            "days": len(baseline),
        },
    }


def rolling_median(rows: Iterable[Mapping], key: str, window: int = 7) -> float | None:
    """Return the median of the latest ``window`` numeric values."""

    values = [_number(row, key) for row in rows]
    values = [v for v in values if v is not None]
    return median(values[-window:]) if values else None
