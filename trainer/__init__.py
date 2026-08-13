"""Trainer — pull training data from intervals.icu and Strava, plan workouts."""

from trainer.intervals import IntervalsClient
from trainer.strava import StravaClient

__all__ = ["IntervalsClient", "StravaClient"]
