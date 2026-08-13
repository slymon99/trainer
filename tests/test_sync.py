"""Sync behaviour that costs API budget to get wrong.

Strava allows 100 requests per 15 minutes, so these drive the sync with a fake
client that counts calls, rather than the real one.
"""

import json
from datetime import date

import pytest
import requests

from trainer.http import RateLimitExceeded
from trainer.store import Store
from trainer.strava import Budget
from trainer.sync import Sync

TODAY = date(2026, 8, 13)


class FakeStrava:
    """Stands in for StravaClient, counting requests and failing on demand."""

    def __init__(self, details: dict[str, dict], remaining: int = 100, fail_after: int | None = None):
        self.details = details
        self.budget = Budget(used=0, limit=remaining, daily_used=0, daily_limit=1000)
        self.fail_after = fail_after
        self.calls: list[str] = []

    def activity(self, activity_id):
        self.calls.append(activity_id)
        if self.fail_after is not None and len(self.calls) > self.fail_after:
            raise RateLimitExceeded("quota exhausted")
        if activity_id not in self.details:
            raise requests.HTTPError(f"404 for {activity_id}")
        return self.details[activity_id]

    def activity_streams(self, activity_id, keys=None):
        self.calls.append(activity_id)
        return {
            "time": {"data": [0, 1, 2]},
            "watts": {"data": [200, 210, 220]},
            "heartrate": {"data": [140, 142]},  # short on purpose: streams can disagree
        }


def detail(activity_id: str, day: str, laps: int = 2) -> dict:
    return {
        "id": int(activity_id),
        "start_date_local": f"{day}T06:00:00",
        "name": "3x12 threshold",
        "weighted_average_watts": 245,
        "laps": [
            {
                "id": int(f"{activity_id}{i}"),
                "lap_index": i,
                "start_date_local": f"{day}T06:{i:02d}:00",
                "average_watts": 245.0 + i,
                "moving_time": 720,
            }
            for i in range(1, laps + 1)
        ],
    }


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "warehouse")


def make_sync(store, tmp_path, strava, **kwargs):
    return Sync(store, today=TODAY, st=strava, raw=tmp_path / "raw", **kwargs)


def test_details_and_laps_land_in_separate_tables(store, tmp_path):
    store.write("iv_activities", [{"id": "1", "start_date_local": "2026-08-11T06:00:00"}])
    strava = FakeStrava({"1": detail("1", "2026-08-11")})

    make_sync(store, tmp_path, strava).strava_details(budget=10)

    assert store.sql("SELECT name, lap_count, has_detail FROM strava_activities").fetchone() == (
        "3x12 threshold",
        2,
        True,
    )
    assert store.sql(
        "SELECT activity_id, lap_index, average_watts FROM strava_laps ORDER BY lap_index"
    ).fetchall() == [("1", 1, 246.0), ("1", 2, 247.0)]


def test_second_run_fetches_nothing_new(store, tmp_path):
    """The whole point: re-running must not spend the API budget again."""
    store.write("iv_activities", [{"id": "1", "start_date_local": "2026-08-11T06:00:00"}])
    strava = FakeStrava({"1": detail("1", "2026-08-11")})

    make_sync(store, tmp_path, strava).strava_details(budget=10)
    calls_after_first = len(strava.calls)
    make_sync(store, tmp_path, strava).strava_details(budget=10)

    assert calls_after_first == 1
    assert strava.calls == ["1"]


def test_budget_caps_fetches_and_reports_the_remainder(store, tmp_path):
    store.write(
        "iv_activities",
        [{"id": str(i), "start_date_local": "2026-08-11T06:00:00"} for i in range(1, 6)],
    )
    strava = FakeStrava({str(i): detail(str(i), "2026-08-11") for i in range(1, 6)})

    sync = make_sync(store, tmp_path, strava)
    sync.strava_details(budget=2)

    assert len(strava.calls) == 2
    assert sync.pending == ["3 activities still need detail"]


def test_low_quota_overrides_the_requested_budget(store, tmp_path):
    store.write(
        "iv_activities",
        [{"id": str(i), "start_date_local": "2026-08-11T06:00:00"} for i in range(1, 6)],
    )
    strava = FakeStrava({str(i): detail(str(i), "2026-08-11") for i in range(1, 6)})
    strava.budget = Budget(used=94, limit=100, daily_used=0, daily_limit=1000)  # 6 left

    make_sync(store, tmp_path, strava).strava_details(budget=50)

    assert len(strava.calls) == 1  # 6 remaining, minus the reserve of 5


def test_running_out_mid_run_keeps_what_was_fetched(store, tmp_path):
    """A quota stop must not throw away the activities already paid for."""
    store.write(
        "iv_activities",
        [{"id": str(i), "start_date_local": "2026-08-11T06:00:00"} for i in range(1, 6)],
    )
    strava = FakeStrava(
        {str(i): detail(str(i), "2026-08-11") for i in range(1, 6)}, fail_after=2
    )

    with pytest.raises(RateLimitExceeded):
        make_sync(store, tmp_path, strava).strava_details(budget=10)

    assert store.count("strava_activities") == 2
    assert store.count("strava_laps") == 4


def test_cached_activities_are_free(store, tmp_path):
    """Raw JSON on disk is re-read, not re-bought, even with no quota left."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "1.json").write_text(json.dumps(detail("1", "2026-08-11")))
    store.write("iv_activities", [{"id": "1", "start_date_local": "2026-08-11T06:00:00"}])
    strava = FakeStrava({}, remaining=0)
    strava.budget = Budget(used=100, limit=100, daily_used=0, daily_limit=1000)

    sync = make_sync(store, tmp_path, strava)
    sync.strava_details(budget=10)

    assert strava.calls == []
    assert store.count("strava_laps") == 2
    assert sync.pending == []


def test_one_broken_activity_does_not_end_the_run(store, tmp_path):
    store.write(
        "iv_activities",
        [{"id": str(i), "start_date_local": "2026-08-11T06:00:00"} for i in (1, 2)],
    )
    strava = FakeStrava({"2": detail("2", "2026-08-11")})  # 1 is missing -> 404

    make_sync(store, tmp_path, strava).strava_details(budget=10)

    assert store.ids("strava_activities") == {"2"}


def test_streams_transpose_to_one_row_per_sample(store, tmp_path):
    store.write(
        "strava_activities",
        [{"id": "1", "start_date_local": "2026-08-11T06:00:00", "laps": []}],
    )
    strava = FakeStrava({})

    make_sync(store, tmp_path, strava).strava_streams(budget=1)

    assert store.sql(
        "SELECT t, watts, heartrate FROM strava_streams ORDER BY t"
    ).fetchall() == [(0, 200.0, 140.0), (1, 210.0, 142.0), (2, 220.0, None)]
    assert store.sql("SELECT DISTINCT date FROM strava_streams").fetchone()[0] == date(2026, 8, 11)


def test_summaries_do_not_overwrite_fetched_detail(store, tmp_path):
    """The list endpoint has no laps; merging it in must not erase them."""
    store.write("iv_activities", [{"id": "1", "start_date_local": "2026-08-11T06:00:00"}])
    strava = FakeStrava({"1": detail("1", "2026-08-11")})
    make_sync(store, tmp_path, strava).strava_details(budget=10)

    strava.activities = lambda after=None, limit=None: [
        {"id": 1, "start_date_local": "2026-08-11T06:00:00", "name": "Renamed"}
    ]
    make_sync(store, tmp_path, strava).strava_summaries()

    assert store.sql("SELECT name, lap_count FROM strava_activities").fetchone() == (
        "3x12 threshold",
        2,
    )
