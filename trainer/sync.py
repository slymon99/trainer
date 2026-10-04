"""Incremental pull from intervals.icu, Strava and Hevy into the local warehouse.

    pixi run sync                      # bring everything up to date
    pixi run sync --since 2025-09-01   # backfill further back
    pixi run sync --streams 5          # also pull per-second data for 5 rides
    pixi run sync --profile alex       # another athlete than the active one

Safe to re-run: every step works out what it already holds and asks only for
what's missing. Strava's 100-requests-per-15-minutes is the binding constraint,
so activity detail is fetched under a budget — a big backfill takes a few runs,
and each one keeps what it got.
"""

import argparse
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import requests

from trainer.config import Profile, active_profile
from trainer.hevy import HevyClient
from trainer.http import RateLimitExceeded
from trainer.intervals import IntervalsClient
from trainer.store import Store
from trainer.strava import StravaClient

# intervals.icu is not meaningfully rate limited — a year of calendar is one
# request — so its windows are set by how far back data can still *change*,
# not by what we can afford. Only Strava's steps economise.
#
# Wellness is re-fetched over this window every run: intervals.icu revises
# CTL/ATL backwards as activities land, so yesterday's numbers change.
WELLNESS_LOOKBACK = 45
# Planned workouts get edited and deleted, so the calendar window is re-read
# whole rather than merged. It reaches far enough forward to cover a whole
# block pushed in advance, and far enough back that revising an old week's
# prescription still lands here.
EVENTS_PAST = 365
EVENTS_FUTURE = 240
# Activities are re-read whole over this window too: intervals.icu won't tell
# us an activity was deleted, so the only way to notice is to stop finding it.
ACTIVITIES_LOOKBACK = 365
# How far back to reach when the warehouse is empty.
FIRST_RUN_DAYS = 365
# Stop this far short of Strava's wall, leaving room for an interactive query.
BUDGET_RESERVE = 5
# Hevy pages 10 workouts at a time, so a re-read costs one request per ten
# sessions — at one or two gym sessions a week this window is a request or
# three. Edits and deletions *older* than it are caught by the events feed,
# which widens the window rather than being bounded by it.
HEVY_LOOKBACK = 30

STREAM_KEYS = [
    "time",
    "watts",
    "heartrate",
    "cadence",
    "velocity_smooth",
    "altitude",
    "distance",
    "grade_smooth",
    "temp",
    "moving",
]


class Sync:
    def __init__(
        self,
        store: Store,
        today: date,
        since: date | None = None,
        iv: IntervalsClient | None = None,
        st: StravaClient | None = None,
        hv: HevyClient | None = None,
        raw: Path | None = None,
        profile: Profile | None = None,
    ):
        self.store = store
        self.today = today
        self.since = since
        self._raw = raw
        self._profile = profile
        self._iv = iv
        self._st = st
        self._hv = hv
        self.pending: list[str] = []

    # Clients, the profile and the raw cache are resolved on demand so a
    # wellness-only sync doesn't require Strava authorization to be set up.
    @property
    def profile(self) -> Profile:
        if self._profile is None:
            self._profile = active_profile()
        return self._profile

    @property
    def raw(self) -> Path:
        if self._raw is None:
            self._raw = self.profile.raw
        return self._raw

    @property
    def iv(self) -> IntervalsClient:
        if self._iv is None:
            self._iv = IntervalsClient(self.profile)
        return self._iv

    @property
    def st(self) -> StravaClient:
        if self._st is None:
            self._st = StravaClient(self.profile)
        return self._st

    @property
    def hv(self) -> HevyClient:
        if self._hv is None:
            self._hv = HevyClient(self.profile)
        return self._hv

    def start_for(self, table: str, lookback: int) -> date:
        """Where to resume: back from the watermark, or `--since` if given.

        The lookback overlap is deliberate: it catches anything that landed
        late, and on the steps that re-read whole it is what lets a deletion
        be noticed. How far back is worth reaching depends on the API — see
        the window constants above.
        """
        if self.since is not None:
            return self.since
        held = self.store.max_date(table)
        if held is None:
            return self.today - timedelta(days=FIRST_RUN_DAYS)
        return held - timedelta(days=lookback)

    # --- steps -------------------------------------------------------------

    def wellness(self) -> int:
        start = self.start_for("iv_wellness", WELLNESS_LOOKBACK)
        rows = []
        for chunk_start, chunk_end in _chunks(start, self.today):
            rows += self.iv.wellness(oldest=str(chunk_start), newest=str(chunk_end))
        return self.store.write("iv_wellness", rows, replace_range=(start, self.today))

    def events(self) -> int:
        start = self.since or self.today - timedelta(days=EVENTS_PAST)
        end = self.today + timedelta(days=EVENTS_FUTURE)
        rows = []
        for chunk_start, chunk_end in _chunks(start, end):
            rows += self.iv.events(oldest=str(chunk_start), newest=str(chunk_end))
        return self.store.write("iv_events", rows, replace_range=(start, end))

    def activities(self) -> int:
        start = self.start_for("iv_activities", ACTIVITIES_LOOKBACK)
        rows = []
        for chunk_start, chunk_end in _chunks(start, self.today):
            rows += self.iv.activities(oldest=str(chunk_start), newest=str(chunk_end))
        return self.store.write("iv_activities", rows, replace_range=(start, self.today))

    def athlete(self) -> int:
        settings = self.iv.athlete().get("sportSettings") or []
        snapshot = [
            {**s, "captured_on": self.today, "sport": (s.get("types") or [None])[0]}
            for s in settings
        ]
        return self.store.write("iv_athlete", snapshot)

    def hevy(self) -> int:
        """Gym sessions and their sets, re-read whole over a rolling window.

        Both tables are written from the same payload — Hevy nests the sets
        inside the workout, so one walk fills both — and with the same replace
        range, so a session deleted in the app disappears from both here.
        """
        start = min(self.start_for("hevy_workouts", HEVY_LOOKBACK), self._hevy_changed())
        workouts = self.hv.workouts(since=f"{start}T00:00:00Z")
        self.store.write("hevy_sets", _hevy_set_rows(workouts), replace_range=(start, self.today))
        return self.store.write("hevy_workouts", workouts, replace_range=(start, self.today))

    def hevy_templates(self, refresh: bool = False) -> int:
        """The exercise catalogue. Static enough to fetch once and leave alone —
        five requests, and it only changes when a custom exercise is added."""
        if not refresh and self.store.count("hevy_exercise_templates"):
            return 0
        return self.store.write("hevy_exercise_templates", self.hv.exercise_templates())

    def _hevy_changed(self) -> date:
        """Date of the oldest session edited or deleted since the last sync.

        Re-reading the list endpoint can only ever show what still exists, so a
        session deleted in the app would linger locally forever. The events feed
        is the one place a deletion is reported; this turns it into a wider
        replace range, which is what actually removes the row. Returns
        `self.today` when nothing changed, so it never widens the window.
        """
        # Read as an epoch rather than a timestamp: handing a TIMESTAMPTZ back
        # to Python makes DuckDB reach for pytz, and rendering it with strftime
        # silently converts to local time while still stamping a 'Z' on it.
        row = self.store.sql("SELECT epoch(max(_synced_at)) FROM hevy_workouts").fetchone()
        last = row[0] if row else None
        if last is None:
            return self.today  # nothing held yet — the lookback governs
        stamp = datetime.fromtimestamp(last, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        touched = [self.today]
        for event in self.hv.workout_events(since=stamp):
            if event.get("type") == "deleted":
                # Only the id is given, so the date has to come from what we hold.
                held = self.store.sql(
                    "SELECT date FROM hevy_workouts WHERE id = ?", event.get("id")
                ).fetchone()
                if held and held[0]:
                    touched.append(held[0])
            elif started := (event.get("workout") or {}).get("start_time"):
                touched.append(date.fromisoformat(started[:10]))
        return min(touched)

    def strava_summaries(self) -> int:
        """Strava's own activity list — the index, one request per 200 rides.

        Rows already enriched with laps are left alone: a summary would
        overwrite the detail with a thinner version of the same activity.
        """
        start = self.start_for("strava_activities", 7)
        after = int(datetime.combine(start, time.min, tzinfo=timezone.utc).timestamp())
        detailed = self.store.ids("strava_activities", where="has_detail")
        summaries = [
            a
            for a in self.st.activities(after=after, limit=None)
            if str(a["id"]) not in detailed
        ]
        return self.store.write("strava_activities", summaries)

    def strava_details(self, budget: int, refresh: bool = False) -> int:
        """Full detail (and therefore laps) for activities that lack it.

        One request each, so this is what the rate limit actually bites on.
        Responses are cached as raw JSON — an activity never changes once
        uploaded, and re-deriving tables from disk beats re-fetching.
        """
        wanted = self._needing_detail(refresh)
        todo, deferred = self._afford(wanted, budget, None if refresh else self._detail_cache)
        if deferred:
            self.pending.append(f"{deferred} activities still need detail")

        details: list[dict] = []
        laps: list[dict] = []
        try:
            for activity_id in todo:
                detail = self._detail(activity_id, refresh)
                if detail is None:
                    continue
                details.append(detail)
                laps += [
                    {**lap, "activity": {"id": activity_id}}
                    for lap in detail.get("laps") or []
                ]
        finally:
            # Written even if the quota runs out mid-loop: one merge per table
            # rather than one per activity, and nothing fetched is thrown away.
            self.store.write("strava_activities", details)
            self.store.write("strava_laps", laps)
        return len(details)

    def strava_streams(self, budget: int) -> int:
        """Per-second series. Opt-in: one request and ~10k rows per activity."""
        if budget <= 0:
            return 0
        have = self.store.ids("strava_streams", column="activity_id")
        wanted = [
            r[0]
            for r in self.store.sql(
                "SELECT id FROM strava_activities WHERE has_detail ORDER BY date DESC"
            ).fetchall()
            if r[0] not in have
        ]
        todo, deferred = self._afford(wanted, budget, self._stream_cache)
        if deferred:
            self.pending.append(f"{deferred} activities still need streams")

        rows: list[dict] = []
        try:
            for activity_id in todo:
                rows += self._streams(activity_id)
        finally:
            self.store.write("strava_streams", rows)
        return len(rows)

    # --- helpers -----------------------------------------------------------

    def _afford(self, wanted: list[str], budget: int, cache=None) -> tuple[list[str], int]:
        """Split the work into what the quota allows now and what waits.

        Anything already cached on disk is free and never counts against the
        budget, so a re-run after a stop is mostly disk reads.
        """
        free = [a for a in wanted if cache and cache(a).exists()]
        paid = [a for a in wanted if not (cache and cache(a).exists())]
        if not paid:
            return free, 0  # nothing to buy — don't even authorize with Strava
        allowed = min(budget, max(0, self.st.budget.remaining - BUDGET_RESERVE))
        return free + paid[:allowed], max(0, len(paid) - allowed)

    def _detail_cache(self, activity_id: str) -> Path:
        return self.raw / f"{activity_id}.json"

    def _stream_cache(self, activity_id: str) -> Path:
        return self.raw / "streams" / f"{activity_id}.json"

    def _needing_detail(self, refresh: bool) -> list[str]:
        """Activity ids known to either source but without laps stored.

        intervals.icu is included because it may know about a ride Strava's
        list endpoint hasn't returned in our window. Its own `i…` ids (Garmin,
        uploads, manual) are swapped for the Strava twin it names, and dropped
        when there is none — Strava would answer them with a 404 on every run. Newest first, so a budget-capped run covers the block you're
        most likely reviewing.
        """
        clause = "" if refresh else "WHERE NOT COALESCE(has_detail, false)"
        rows = self.store.sql(
            f"""
            SELECT id FROM (
                SELECT s.id, s.date, s.has_detail FROM strava_activities s
                UNION
                SELECT COALESCE(i.strava_id, i.id), i.date, false FROM iv_activities i
                WHERE COALESCE(i.strava_id, i.id) NOT IN (SELECT id FROM strava_activities)
                  AND regexp_full_match(COALESCE(i.strava_id, i.id), '[0-9]+')
            ) {clause}
            ORDER BY date DESC
            """
        ).fetchall()
        return [r[0] for r in rows]

    def _detail(self, activity_id: str, refresh: bool = False) -> dict | None:
        cached = self._detail_cache(activity_id)
        if cached.exists() and not refresh:
            return json.loads(cached.read_text())
        try:
            detail = self.st.activity(activity_id)
        except requests.HTTPError as exc:  # one unreadable activity shouldn't end the run
            print(f"  ! {activity_id}: {exc}", file=sys.stderr)
            return None
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(detail))
        return detail

    def _streams(self, activity_id: str) -> list[dict]:
        cached = self._stream_cache(activity_id)
        if cached.exists():
            payload = json.loads(cached.read_text())
        else:
            try:
                payload = self.st.activity_streams(activity_id, keys=STREAM_KEYS)
            except requests.HTTPError as exc:
                print(f"  ! streams {activity_id}: {exc}", file=sys.stderr)
                return []
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(payload))
        return _stream_rows(activity_id, payload, self._activity_date(activity_id))

    def _activity_date(self, activity_id: str) -> date | None:
        row = self.store.sql(
            "SELECT date FROM strava_activities WHERE id = ?", activity_id
        ).fetchone()
        return row[0] if row else None


def _hevy_set_rows(workouts: list[dict]) -> list[dict]:
    """Flatten Hevy's nested workout payload into one row per set.

    `index` is carried down from the payload where present and falls back to
    position, because the pair (exercise_index, set_index) is the merge key —
    a null there would collapse a whole session onto one row.
    """
    rows = []
    for workout in workouts:
        day = date.fromisoformat(workout["start_time"][:10])
        for e_pos, exercise in enumerate(workout.get("exercises") or []):
            e_index = exercise.get("index")
            for s_pos, entry in enumerate(exercise.get("sets") or []):
                s_index = entry.get("index")
                rows.append(
                    {
                        **entry,
                        "workout_id": workout["id"],
                        "date": day,
                        "exercise_index": e_pos if e_index is None else e_index,
                        "set_index": s_pos if s_index is None else s_index,
                        "exercise_title": exercise.get("title"),
                        "exercise_template_id": exercise.get("exercise_template_id"),
                        "supersets_id": exercise.get("supersets_id"),
                        "exercise_notes": exercise.get("notes"),
                    }
                )
    return rows


def _stream_rows(activity_id: str, payload: dict, day: date | None) -> list[dict]:
    """Transpose Strava's column-per-key streams into one row per sample."""
    offsets = (payload.get("time") or {}).get("data") or []
    series = {k: (v or {}).get("data") or [] for k, v in payload.items() if k != "time"}
    rows = []
    for i, offset in enumerate(offsets):
        row = {"activity_id": activity_id, "date": day, "t": offset}
        for key, values in series.items():
            row[key] = values[i] if i < len(values) else None
        rows.append(row)
    return rows


def _chunks(start: date, end: date, days: int = 365):
    """Split a long span into windows the APIs will answer in one response."""
    cursor = start
    while cursor <= end:
        stop = min(end, cursor + timedelta(days=days - 1))
        yield cursor, stop
        cursor = stop + timedelta(days=1)


STEPS = (
    "wellness",
    "events",
    "activities",
    "athlete",
    "strava",
    "details",
    "streams",
    "lifts",
    "exercises",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        help="backfill from this date instead of resuming from what's stored",
    )
    parser.add_argument(
        "--tables",
        default=",".join(STEPS),
        help=f"comma-separated subset of: {', '.join(STEPS)}",
    )
    parser.add_argument(
        "--details", type=int, default=50, help="max Strava activity detail fetches (default 50)"
    )
    parser.add_argument(
        "--streams", type=int, default=0, help="max Strava stream fetches (default 0 — opt in)"
    )
    parser.add_argument(
        "--refresh", action="store_true", help="re-fetch activity detail already stored"
    )
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--profile", help="athlete profile (default: the active one)")
    args = parser.parse_args(argv)

    steps = [s.strip() for s in args.tables.split(",") if s.strip()]
    unknown = set(steps) - set(STEPS)
    if unknown:
        parser.error(f"unknown step(s): {', '.join(sorted(unknown))}. Known: {', '.join(STEPS)}")

    profile = active_profile(args.profile)
    store = Store(profile.warehouse)
    sync = Sync(store, today=args.today, since=args.since, profile=profile)
    plan = {
        "wellness": sync.wellness,
        "events": sync.events,
        "activities": sync.activities,
        "athlete": sync.athlete,
        "strava": sync.strava_summaries,
        "details": lambda: sync.strava_details(args.details, refresh=args.refresh),
        "streams": lambda: sync.strava_streams(args.streams),
        "lifts": sync.hevy,
        "exercises": lambda: sync.hevy_templates(refresh=args.refresh),
    }

    stopped_early = False
    for name in steps:
        try:
            written = plan[name]()
        except RateLimitExceeded as exc:
            print(f"\n{exc}", file=sys.stderr)
            stopped_early = True
            break
        except SystemExit as exc:  # a service this athlete hasn't set up — not every profile has all three
            print(f"  {name:<11} skipped — {exc}")
            continue
        print(f"  {name:<11} {written:>7,} rows")

    print()
    for name, rows, first, last in store.summary():
        span = f"{first} → {last}" if rows else "empty"
        print(f"  {name:<20} {rows:>9,} rows   {span}")
    if sync._st is not None:
        print(f"\n  strava budget: {sync.st.budget.remaining} requests left in this window")
    for note in sync.pending:
        print(f"  pending: {note} — re-run to continue")

    return 1 if stopped_early else 0


if __name__ == "__main__":
    raise SystemExit(main())
