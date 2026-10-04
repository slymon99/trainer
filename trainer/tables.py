"""Table definitions for the local warehouse — one grain per table.

Each table is a declarative column list: `(name, type, source_key)`, where
`source_key` is the field in the raw API payload (dotted for nested lookups,
omitted when it matches the column name). Keeping the schema and the mapping
in one place is what stops the two from drifting apart.

Naming: columns are snake_case even where the API isn't (`restingHR` →
`resting_hr`), and every id is a **string**, so intervals.icu ids and Strava
ids join without casting. See docs/data-store.md for the field reference.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import pyarrow as pa

STR = pa.string()
INT = pa.int64()
FLOAT = pa.float64()
BOOL = pa.bool_()
DATE = pa.date32()
TS = pa.timestamp("s")  # naive — these are local times, and the offset is a column
TSZ = pa.timestamp("s", tz="UTC")

SYNCED_AT = "_synced_at"

Column = tuple[str, pa.DataType] | tuple[str, pa.DataType, str]


@dataclass(frozen=True)
class Table:
    """One table: its schema, its unique key, and how it partitions on disk."""

    name: str
    columns: list[Column]
    key: tuple[str, ...]
    date_column: str | None = "date"
    partitioned: bool = True
    derive: Callable[[dict], dict] | None = field(default=None, compare=False)
    doc: str = ""

    @property
    def schema(self) -> pa.Schema:
        fields = [pa.field(c[0], c[1]) for c in self.columns]
        return pa.schema([*fields, pa.field(SYNCED_AT, TSZ)])

    def source_key(self, column: str) -> str:
        for spec in self.columns:
            if spec[0] == column:
                return spec[2] if len(spec) == 3 else spec[0]
        raise KeyError(f"{self.name} has no column {column}")

    def row(self, payload: dict, synced_at: datetime) -> dict:
        """Flatten one API payload into a row matching this table's schema."""
        extra = self.derive(payload) if self.derive else {}
        out = {}
        for spec in self.columns:
            name, dtype = spec[0], spec[1]
            if name in extra:
                value = extra[name]
            else:
                value = _lookup(payload, spec[2] if len(spec) == 3 else name)
            try:
                out[name] = _cast(value, dtype)
            except (TypeError, ValueError) as exc:
                # Name the column: a sync that dies on one odd field should say
                # which one, not just "could not convert string to float".
                raise ValueError(
                    f"{self.name}.{name}: cannot store {value!r} as {dtype}"
                ) from exc
        out[SYNCED_AT] = synced_at
        return out

    def rows(self, payloads, synced_at: datetime | None = None) -> list[dict]:
        synced_at = synced_at or datetime.now(timezone.utc).replace(microsecond=0)
        return [self.row(p, synced_at) for p in payloads]


def _lookup(payload: dict, path: str):
    """Fetch `path` from a payload, following dots into nested objects."""
    value = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _cast(value, dtype: pa.DataType):
    """Coerce an API value to something Arrow will accept for `dtype`.

    The APIs are loose — ids arrive as int or str depending on endpoint, dates
    as full ISO timestamps where only the day matters — so every value is
    normalised here rather than at each call site.
    """
    if value is None or value == "":
        return None
    if dtype == STR:
        return value if isinstance(value, str) else json.dumps(value, default=str)
    if dtype == DATE:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        return date.fromisoformat(str(value)[:10])
    if dtype in (TS, TSZ):
        return _timestamp(value, utc=dtype == TSZ)
    if dtype == BOOL:
        return bool(value)
    if dtype == INT:
        return int(round(float(value))) if not isinstance(value, bool) else int(value)
    if dtype == FLOAT:
        return float(value)
    raise TypeError(f"no cast rule for {dtype}")


def _timestamp(value, utc: bool) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if utc:
        parsed = (
            parsed.replace(tzinfo=timezone.utc)
            if parsed.tzinfo is None
            else parsed.astimezone(timezone.utc)
        )
    elif parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed.replace(microsecond=0)


# --- intervals.icu ---------------------------------------------------------

IV_WELLNESS = Table(
    name="iv_wellness",
    doc="Daily wellness and the fitness model. One row per calendar day.",
    key=("date",),
    columns=[
        ("date", DATE, "id"),
        ("ctl", FLOAT),
        ("atl", FLOAT),
        ("ramp_rate", FLOAT, "rampRate"),
        ("ctl_load", FLOAT, "ctlLoad"),
        ("atl_load", FLOAT, "atlLoad"),
        ("resting_hr", INT, "restingHR"),
        ("hrv", FLOAT),
        ("hrv_sdnn", FLOAT, "hrvSDNN"),
        ("avg_sleeping_hr", FLOAT, "avgSleepingHR"),
        ("sleep_secs", INT, "sleepSecs"),
        ("sleep_score", FLOAT, "sleepScore"),
        ("sleep_quality", INT, "sleepQuality"),
        ("weight", FLOAT),
        ("body_fat", FLOAT, "bodyFat"),
        ("abdomen", FLOAT),
        ("vo2max", FLOAT),
        ("spo2", FLOAT, "spO2"),
        ("respiration", FLOAT),
        ("blood_glucose", FLOAT, "bloodGlucose"),
        ("lactate", FLOAT),
        ("steps", INT),
        ("readiness", FLOAT),
        ("baevsky_si", FLOAT, "baevskySI"),
        ("fatigue", INT),
        ("soreness", INT),
        ("stress", INT),
        ("mood", INT),
        ("motivation", INT),
        ("injury", INT),
        ("systolic", INT),
        ("diastolic", INT),
        ("hydration", FLOAT),
        ("hydration_volume", INT, "hydrationVolume"),
        ("kcal_consumed", INT, "kcalConsumed"),
        ("carbohydrates", FLOAT),
        ("protein", FLOAT),
        ("fat_total", FLOAT, "fatTotal"),
        ("temp_weight", BOOL, "tempWeight"),
        ("temp_resting_hr", BOOL, "tempRestingHR"),
        ("locked", BOOL),
        ("comments", STR),
        ("sport_info", STR, "sportInfo"),
        ("updated", TSZ),
    ],
)

IV_EVENTS = Table(
    name="iv_events",
    doc="The calendar: what was *prescribed*. One row per intervals.icu event.",
    key=("id",),
    columns=[
        ("id", STR),
        ("date", DATE, "start_date_local"),
        ("start_date_local", TS),
        ("end_date_local", TS),
        ("category", STR),
        ("type", STR),
        ("sub_type", STR),
        ("name", STR),
        ("description", STR),
        ("indoor", BOOL),
        ("moving_time", INT),
        ("distance", FLOAT),
        ("icu_training_load", INT),
        ("icu_intensity", FLOAT),
        ("icu_atl", FLOAT),
        ("icu_ctl", FLOAT),
        ("joules", INT),
        ("joules_above_ftp", INT),
        ("load_target", FLOAT),
        ("time_target", FLOAT),
        ("distance_target", FLOAT),
        # The prescription→execution link, straight from intervals.icu.
        ("paired_activity_id", STR),
        ("external_id", STR),
        ("uid", STR),
        ("plan_name", STR),
        ("plan_workout_id", STR),
        ("athlete_id", STR),
        ("color", STR),
        ("tags", STR),
        ("workout_doc", STR),
        ("show_as_note", BOOL),
        ("not_on_fitness_chart", BOOL),
        ("updated", TSZ),
    ],
)

IV_ACTIVITIES = Table(
    name="iv_activities",
    doc=(
        "Index of completed activities known to intervals.icu. Strava-sourced "
        "rows are stubs by design and their id is the Strava id; rows from "
        "Garmin, file uploads or manual entry get intervals.icu's own `i…` id "
        "and carry the Strava twin in strava_id. Either way, the detail lives "
        "in strava_activities, joined on COALESCE(strava_id, id)."
    ),
    key=("id",),
    columns=[
        ("id", STR),
        ("date", DATE, "start_date_local"),
        ("start_date_local", TS),
        ("source", STR),
        ("strava_id", STR),
        ("athlete_id", STR, "icu_athlete_id"),
        ("name", STR),
        ("type", STR),
        ("moving_time", INT),
        ("icu_training_load", INT),
        ("icu_weighted_avg_watts", FLOAT),
        ("icu_intensity", FLOAT),
        ("icu_eftp", FLOAT),
    ],
)

IV_ATHLETE = Table(
    name="iv_athlete",
    doc=(
        "Daily snapshot of the sport settings intervals.icu models with — FTP, "
        "LTHR, zones. Snapshotted because these change, and a review of an old "
        "block needs the numbers that were in force *then*."
    ),
    key=("captured_on", "id"),
    date_column="captured_on",
    partitioned=False,
    columns=[
        ("captured_on", DATE),
        ("id", STR),
        ("sport", STR),
        ("types", STR),
        ("ftp", INT),
        ("indoor_ftp", INT),
        ("lthr", INT),
        ("max_hr", INT),
        ("w_prime", INT),
        ("p_max", INT),
        ("power_zones", STR),
        ("power_zone_names", STR),
        ("hr_zones", STR),
        ("hr_zone_names", STR),
        ("sweet_spot_min", INT),
        ("sweet_spot_max", INT),
        ("threshold_pace", FLOAT),
        ("updated", TSZ),
    ],
)

# --- Strava ----------------------------------------------------------------


def _activity_extras(payload: dict) -> dict:
    laps = payload.get("laps")
    return {
        "lap_count": len(laps) if laps is not None else None,
        "has_detail": "laps" in payload,
    }


STRAVA_ACTIVITIES = Table(
    name="strava_activities",
    doc="What was actually *done*: one row per Strava activity, with measured power and HR.",
    key=("id",),
    derive=_activity_extras,
    columns=[
        ("id", STR),
        ("date", DATE, "start_date_local"),
        ("start_date_local", TS),
        ("start_date", TSZ),
        ("timezone", STR),
        ("utc_offset", FLOAT),
        ("name", STR),
        ("type", STR),
        ("sport_type", STR),
        ("description", STR),
        ("private_note", STR),
        ("trainer", BOOL),
        ("commute", BOOL),
        ("manual", BOOL),
        ("distance", FLOAT),
        ("moving_time", INT),
        ("elapsed_time", INT),
        ("total_elevation_gain", FLOAT),
        ("elev_high", FLOAT),
        ("elev_low", FLOAT),
        ("average_speed", FLOAT),
        ("max_speed", FLOAT),
        ("average_watts", FLOAT),
        ("weighted_average_watts", FLOAT),
        ("max_watts", FLOAT),
        ("device_watts", BOOL),
        ("kilojoules", FLOAT),
        ("has_heartrate", BOOL),
        ("average_heartrate", FLOAT),
        ("max_heartrate", FLOAT),
        ("average_cadence", FLOAT),
        ("calories", FLOAT),
        ("suffer_score", FLOAT),
        ("perceived_exertion", FLOAT),
        ("gear_id", STR),
        ("device_name", STR),
        ("external_id", STR),
        ("upload_id", STR),
        # False for rows that came from the list endpoint only: no laps fetched yet.
        ("has_detail", BOOL),
        ("lap_count", INT),
    ],
)

STRAVA_LAPS = Table(
    name="strava_laps",
    doc=(
        "Per-lap splits — the per-rep actuals. On a structured workout the laps "
        "*are* the reps. Strava does not report max_watts per lap; only the "
        "average is available."
    ),
    key=("id",),
    columns=[
        ("id", STR),
        ("activity_id", STR, "activity.id"),
        ("date", DATE, "start_date_local"),
        ("lap_index", INT),
        ("split", INT),
        ("name", STR),
        ("start_date_local", TS),
        ("start_index", INT),
        ("end_index", INT),
        ("moving_time", INT),
        ("elapsed_time", INT),
        ("distance", FLOAT),
        ("total_elevation_gain", FLOAT),
        ("average_speed", FLOAT),
        ("max_speed", FLOAT),
        ("average_watts", FLOAT),
        ("device_watts", BOOL),
        ("average_cadence", FLOAT),
        ("average_heartrate", FLOAT),
        ("max_heartrate", FLOAT),
    ],
)

STRAVA_STREAMS = Table(
    name="strava_streams",
    doc=(
        "Full-resolution time series, one row per sample. Opt-in: a season of "
        "these is millions of rows and one API call per activity."
    ),
    key=("activity_id", "t"),
    columns=[
        ("activity_id", STR),
        ("date", DATE),
        ("t", INT),
        ("watts", FLOAT),
        ("heartrate", FLOAT),
        ("cadence", FLOAT),
        ("velocity_smooth", FLOAT),
        ("altitude", FLOAT),
        ("distance", FLOAT),
        ("grade_smooth", FLOAT),
        ("temp", FLOAT),
        ("moving", BOOL),
    ],
)

# --- Hevy ------------------------------------------------------------------


def _workout_extras(payload: dict) -> dict:
    """Roll the nested sets up to session level.

    Counted here rather than left to a query because `hevy_sets` is the only
    other place these numbers exist, and a session with zero logged sets — an
    accidental start-and-abandon — should be visible without a join.
    """
    exercises = payload.get("exercises") or []
    sets = [s for e in exercises for s in (e.get("sets") or [])]
    working = [s for s in sets if s.get("type") != "warmup"]
    return {
        "exercise_count": len(exercises),
        "set_count": len(sets),
        # The load figure lifters actually track. Warm-ups are excluded: they
        # scale with the working weight, so counting them double-counts a
        # heavier session as more work than it was.
        "working_set_count": len(working),
        "volume_kg": sum(
            (s.get("weight_kg") or 0) * (s.get("reps") or 0) for s in working
        )
        or None,
    }


HEVY_WORKOUTS = Table(
    name="hevy_workouts",
    doc=(
        "One row per completed gym session. The per-set detail lives in "
        "hevy_sets, joined on id = workout_id."
    ),
    key=("id",),
    derive=_workout_extras,
    columns=[
        ("id", STR),
        # Hevy timestamps are UTC with no offset, so this is the UTC date. For
        # an evening session that is the local date too, except after ~23:00
        # British Summer Time — rare enough to name rather than model.
        ("date", DATE, "start_time"),
        ("start_time", TSZ),
        ("end_time", TSZ),
        ("title", STR),
        ("description", STR),
        # Set when the session was started from a routine — the link back to
        # what was prescribed, and the only one Hevy gives.
        ("routine_id", STR),
        ("exercise_count", INT),
        ("set_count", INT),
        ("working_set_count", INT),
        ("volume_kg", FLOAT),
        ("created_at", TSZ),
        ("updated_at", TSZ),
    ],
)


def _set_extras(payload: dict) -> dict:
    weight, reps = payload.get("weight_kg"), payload.get("reps")
    return {"volume_kg": (weight * reps) if weight and reps else None}


HEVY_SETS = Table(
    name="hevy_sets",
    doc=(
        "One row per set — the grain progression is actually judged at. "
        "Flattened out of the workout payload by the sync; Hevy nests it."
    ),
    key=("workout_id", "exercise_index", "set_index"),
    derive=_set_extras,
    columns=[
        ("workout_id", STR),
        ("date", DATE),
        ("exercise_index", INT),
        ("set_index", INT),
        ("exercise_title", STR),
        # Stable across renames, and what a routine push references. Join to
        # hevy_exercise_templates.
        ("exercise_template_id", STR),
        ("supersets_id", INT),
        ("exercise_notes", STR),
        # 'normal', 'warmup', 'dropset' or 'failure'. Filter warm-ups out of
        # any volume or intensity figure.
        ("set_type", STR, "type"),
        ("weight_kg", FLOAT),
        ("reps", INT),
        ("rpe", FLOAT),
        ("duration_seconds", INT),
        ("distance_meters", FLOAT),
        ("custom_metric", FLOAT),
        ("volume_kg", FLOAT),
    ],
)

HEVY_EXERCISE_TEMPLATES = Table(
    name="hevy_exercise_templates",
    doc=(
        "Hevy's exercise catalogue — ~450 built-ins plus any custom ones. "
        "Reference data: no date, refreshed whole."
    ),
    key=("id",),
    date_column=None,
    partitioned=False,
    columns=[
        ("id", STR),
        ("title", STR),
        # 'weight_reps', 'reps_only', 'bodyweight_reps', 'duration', ...
        # Decides which set fields are meaningful.
        ("type", STR),
        ("primary_muscle_group", STR),
        ("secondary_muscle_groups", STR),
        ("equipment_category", STR, "equipment"),
        ("is_custom", BOOL),
    ],
)

TABLES: dict[str, Table] = {
    t.name: t
    for t in (
        IV_WELLNESS,
        IV_EVENTS,
        IV_ACTIVITIES,
        IV_ATHLETE,
        STRAVA_ACTIVITIES,
        STRAVA_LAPS,
        STRAVA_STREAMS,
        HEVY_WORKOUTS,
        HEVY_SETS,
        HEVY_EXERCISE_TEMPLATES,
    )
}


def get(name: str) -> Table:
    try:
        return TABLES[name]
    except KeyError:
        raise KeyError(f"unknown table {name!r}; known: {', '.join(TABLES)}") from None
