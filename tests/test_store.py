"""Merge semantics for the warehouse — the part that can silently lose data."""

from datetime import date

import pyarrow as pa
import pytest

from trainer import tables
from trainer.store import Store
from trainer.tables import IV_ATHLETE, IV_WELLNESS, Table


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "warehouse")


def wellness(day: str, **fields) -> dict:
    """A wellness payload as intervals.icu sends it — camelCase, id is the date."""
    return {"id": day, **fields}


def test_roundtrip_normalises_names_and_types(store):
    store.write("iv_wellness", [wellness("2026-08-01", ctl=48.5, restingHR=44, sleepSecs=27000)])

    row = store.sql("SELECT date, ctl, resting_hr, sleep_secs FROM iv_wellness").fetchone()
    assert row == (date(2026, 8, 1), 48.5, 44, 27000)


def test_missing_fields_are_null_not_absent(store):
    store.write("iv_wellness", [wellness("2026-08-01", ctl=48.5)])

    assert store.sql("SELECT hrv, weight FROM iv_wellness").fetchone() == (None, None)


def test_write_is_upsert_on_key(store):
    store.write("iv_wellness", [wellness("2026-08-01", ctl=48.5)])
    store.write("iv_wellness", [wellness("2026-08-01", ctl=51.0)])

    assert store.count("iv_wellness") == 1
    assert store.sql("SELECT ctl FROM iv_wellness").fetchone()[0] == 51.0


def test_writing_one_month_leaves_other_months_intact(store):
    store.write("iv_wellness", [wellness("2026-07-15", ctl=40.0), wellness("2026-08-01", ctl=48.5)])
    store.write("iv_wellness", [wellness("2026-09-02", ctl=55.0)])

    assert store.count("iv_wellness") == 3
    assert {p.parent.name for p in store._files(IV_WELLNESS)} == {
        "month=2026-07",
        "month=2026-08",
        "month=2026-09",
    }


def test_replace_range_drops_rows_the_api_no_longer_returns(store):
    """A workout deleted from the calendar has to disappear from the store too."""
    store.write("iv_events", [_event("1", "2026-08-10"), _event("2", "2026-08-11")])
    store.write(
        "iv_events",
        [_event("1", "2026-08-10")],
        replace_range=(date(2026, 8, 1), date(2026, 8, 31)),
    )

    assert store.ids("iv_events") == {"1"}


def test_replace_range_leaves_rows_outside_the_window_alone(store):
    store.write("iv_events", [_event("1", "2026-07-20"), _event("2", "2026-08-11")])
    store.write(
        "iv_events", [], replace_range=(date(2026, 8, 1), date(2026, 8, 31))
    )

    assert store.ids("iv_events") == {"1"}


def test_emptied_partition_is_removed_not_left_stale(store):
    store.write("iv_events", [_event("1", "2026-08-11")])
    store.write("iv_events", [], replace_range=(date(2026, 8, 1), date(2026, 8, 31)))

    assert store.count("iv_events") == 0
    assert not (store.root / "iv_events" / "month=2026-08").exists()


def test_unpartitioned_table_writes_one_file(store):
    store.write("iv_athlete", [{"captured_on": "2026-08-13", "id": 953869, "ftp": 268}])
    store.write("iv_athlete", [{"captured_on": "2026-08-14", "id": 953869, "ftp": 272}])

    assert [p.name for p in store._files(IV_ATHLETE)] == ["data.parquet"]
    assert store.sql("SELECT ftp FROM iv_athlete ORDER BY captured_on").fetchall() == [
        (268,),
        (272,),
    ]


def test_column_added_after_files_were_written_reads_as_null(store, monkeypatch):
    """Adding a column to tables.py must not break reads of older parquet."""
    store.write("iv_wellness", [wellness("2026-08-01", ctl=48.5)])

    widened = Table(
        name=IV_WELLNESS.name,
        columns=[*IV_WELLNESS.columns, ("brand_new", pa.float64())],
        key=IV_WELLNESS.key,
    )
    monkeypatch.setitem(tables.TABLES, "iv_wellness", widened)
    fresh = Store(store.root)

    assert fresh.sql("SELECT ctl, brand_new FROM iv_wellness").fetchone() == (48.5, None)


def test_max_date_is_the_sync_watermark(store):
    assert store.max_date("iv_wellness") is None

    store.write("iv_wellness", [wellness("2026-08-01"), wellness("2026-08-09")])

    assert store.max_date("iv_wellness") == date(2026, 8, 9)


def test_queries_work_before_anything_is_written(store):
    """An empty warehouse answers queries instead of erroring on missing files."""
    assert store.count("iv_wellness") == 0
    assert store.sql("SELECT * FROM planned_vs_actual").fetchall() == []


def test_ids_of_activities_needing_detail(store):
    store.write("strava_activities", [{"id": 1, "start_date_local": "2026-08-11T06:00:00"}])
    store.write(
        "strava_activities",
        [{"id": 2, "start_date_local": "2026-08-12T06:00:00", "laps": [{"id": 9}]}],
    )

    assert store.ids("strava_activities", where="NOT has_detail") == {"1"}


def test_bad_value_names_the_column_it_choked_on(store):
    with pytest.raises(ValueError, match="iv_wellness.ctl"):
        store.write("iv_wellness", [wellness("2026-08-01", ctl="not a number")])


def _event(event_id: str, day: str) -> dict:
    return {"id": event_id, "start_date_local": f"{day}T00:00:00", "category": "WORKOUT"}


def test_garmin_activity_joins_its_strava_twin_once(store):
    """intervals.icu's `i…` id and Strava's id are one ride — one row, paired to the calendar."""
    store.write(
        "iv_activities",
        [{"id": "i9", "start_date_local": "2026-08-11T06:00:00", "source": "GARMIN_CONNECT",
          "strava_id": "77", "icu_training_load": 60}],
    )
    store.write(
        "strava_activities",
        [{"id": 77, "start_date_local": "2026-08-11T06:00:00", "average_watts": 200}],
    )
    store.write(
        "iv_events",
        [{"id": 5, "start_date_local": "2026-08-11T00:00:00", "category": "WORKOUT",
          "name": "Z2", "paired_activity_id": "i9"}],
    )

    rows = store.sql("SELECT id, iv_id, average_watts, icu_training_load FROM activities").fetchall()
    assert rows == [("77", "i9", 200.0, 60)]
    paired = store.sql("SELECT activity_id FROM planned_vs_actual").fetchall()
    assert paired == [("77",)]
