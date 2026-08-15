"""Sync behaviour that costs API budget — or silent staleness — to get wrong.

Strava allows 100 requests per 15 minutes, so these drive the sync with a fake
client that counts calls, rather than the real one.

intervals.icu isn't the budget problem; *stale* is. Its steps re-read their
window whole so that an edited or deleted workout stops being true here too,
and the tests below pin that down — a merge-only sync passes every assertion
about edits and fails every assertion about deletions.
"""

import json
from datetime import date, timedelta

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


class FakeIntervals:
    """Stands in for IntervalsClient, serving whatever the calendar says today.

    Rows outside the requested window are withheld, exactly as the real API
    does — which is what makes the window constants testable.
    """

    def __init__(self, events=(), activities=()):
        self.rows = {"events": list(events), "activities": list(activities)}
        self.windows: list[tuple[str, str]] = []

    def _serve(self, kind, oldest, newest):
        self.windows.append((oldest, newest))
        return [r for r in self.rows[kind] if oldest <= r["start_date_local"][:10] <= newest]

    def events(self, oldest, newest):
        return self._serve("events", oldest, newest)

    def activities(self, oldest, newest):
        return self._serve("activities", oldest, newest)


def workout(id_, day, name="3x12 threshold", description="3x12min @ 95% FTP", load=60):
    return {
        "id": id_,
        "start_date_local": f"{day}T06:00:00",
        "category": "WORKOUT",
        "name": name,
        "description": description,
        "icu_training_load": load,
    }


def ride(id_, day, name="Morning ride", load=60):
    return {
        "id": id_,
        "start_date_local": f"{day}T06:00:00",
        "name": name,
        "type": "Ride",
        "icu_training_load": load,
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


# --- intervals.icu staleness ------------------------------------------------
#
# The calendar is the prescription: if it drifts from what intervals.icu holds,
# every review reads the wrong plan. These drive two syncs against one fake and
# change the calendar in between.


def sync_events(store, iv):
    Sync(store, today=TODAY, iv=iv).events()


def sync_activities(store, iv):
    Sync(store, today=TODAY, iv=iv).activities()


def test_edited_workout_refreshes(store):
    iv = FakeIntervals(events=[workout("e1", "2026-08-14")])
    sync_events(store, iv)

    iv.rows["events"] = [
        workout("e1", "2026-08-14", name="4x12 threshold", description="4x12min @ 98%", load=85)
    ]
    sync_events(store, iv)

    assert store.sql("SELECT name, description, icu_training_load FROM iv_events").fetchall() == [
        ("4x12 threshold", "4x12min @ 98%", 85)
    ]


def test_workout_deleted_from_the_calendar_disappears(store):
    iv = FakeIntervals(events=[workout("e1", "2026-08-14"), workout("e2", "2026-08-16")])
    sync_events(store, iv)

    iv.rows["events"] = [workout("e1", "2026-08-14")]
    sync_events(store, iv)

    assert store.ids("iv_events") == {"e1"}


def test_workout_moved_to_another_day_is_not_duplicated(store):
    """A merge on id alone would leave the old date behind as a second row."""
    iv = FakeIntervals(events=[workout("e1", "2026-08-18")])
    sync_events(store, iv)

    iv.rows["events"] = [workout("e1", "2026-08-20")]
    sync_events(store, iv)

    assert store.sql("SELECT id, date FROM iv_events").fetchall() == [("e1", date(2026, 8, 20))]


def test_calendar_window_covers_a_block_pushed_months_ahead(store):
    """Blocks get written to the calendar well in advance; the sync must see them."""
    far = str(TODAY + timedelta(days=200))
    iv = FakeIntervals(events=[workout("e1", far)])

    sync_events(store, iv)

    assert store.ids("iv_events") == {"e1"}


def test_activity_deleted_from_intervals_disappears(store):
    """intervals.icu never says 'deleted' — not finding it again is the signal."""
    iv = FakeIntervals(activities=[ride("a1", "2026-08-11"), ride("a2", "2026-08-12")])
    sync_activities(store, iv)

    iv.rows["activities"] = [ride("a1", "2026-08-11")]
    sync_activities(store, iv)

    assert store.ids("iv_activities") == {"a1"}


def test_activity_edited_long_after_the_fact_refreshes(store):
    """Re-categorising an old ride changes its load, and the edit can come months later.

    The fresh ride matters: it pushes the watermark to today, so a short
    lookback would put the edited one out of reach.
    """
    old = str(TODAY - timedelta(days=90))
    iv = FakeIntervals(activities=[ride("a1", old), ride("a2", str(TODAY))])
    sync_activities(store, iv)

    iv.rows["activities"][0] = ride("a1", old, name="Renamed", load=140)
    sync_activities(store, iv)

    assert store.sql(
        "SELECT name, icu_training_load FROM iv_activities WHERE id = 'a1'"
    ).fetchall() == [("Renamed", 140)]


def test_activities_outside_the_window_are_left_alone(store):
    """The replace range must not eat the backfill it never asked the API for.

    The window runs back from the watermark, so a season pulled in with
    `--since` sits outside it and has to survive untouched.
    """
    ancient = ride("old", str(TODAY - timedelta(days=800)))
    recent = ride("a1", "2026-08-12")
    store.write("iv_activities", [ancient, recent])
    iv = FakeIntervals(activities=[recent])

    sync_activities(store, iv)

    assert store.ids("iv_activities") == {"old", "a1"}
