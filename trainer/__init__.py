"""Trainer — pull training data from intervals.icu, Strava and Hevy, plan workouts."""

from trainer.hevy import HevyClient
from trainer.intervals import IntervalsClient
from trainer.strava import StravaClient

__all__ = ["HevyClient", "IntervalsClient", "StravaClient"]
