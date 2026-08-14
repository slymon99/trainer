"""Client for the intervals.icu API.

Auth: HTTP Basic, username "API_KEY", password is your personal API key
from https://intervals.icu/settings ("Developer Settings").
Docs: https://intervals.icu/api-docs.html
"""

from trainer.config import get_env, require_env
from trainer.http import check, make_session

BASE_URL = "https://intervals.icu"


class IntervalsClient:
    def __init__(self, api_key: str | None = None, athlete_id: str | None = None):
        self.api_key = api_key or require_env("INTERVALS_API_KEY")
        self.athlete_id = athlete_id or get_env("INTERVALS_ATHLETE_ID", "0")
        self.session = make_session()
        self.session.auth = ("API_KEY", self.api_key)

    def _get(self, path: str, **params):
        return check(self.session.get(f"{BASE_URL}{path}", params=params)).json()

    def _post(self, path: str, json_body, **params):
        return check(self.session.post(f"{BASE_URL}{path}", json=json_body, params=params)).json()

    def _put(self, path: str, json_body, **params):
        return check(self.session.put(f"{BASE_URL}{path}", json=json_body, params=params)).json()

    # --- reading -----------------------------------------------------------

    def athlete(self):
        """Profile, including icu_ftp, icu_resting_hr, sportSettings and zones."""
        return self._get(f"/api/v1/athlete/{self.athlete_id}")

    def activities(self, oldest: str, newest: str):
        """Completed activities. oldest/newest are ISO dates, e.g. '2026-07-01'."""
        return self._get(
            f"/api/v1/athlete/{self.athlete_id}/activities",
            oldest=oldest,
            newest=newest,
        )

    def activity(self, activity_id: str):
        return self._get(f"/api/v1/activity/{activity_id}")

    def activity_intervals(self, activity_id: str):
        """Per-interval splits for one activity — actual watts/HR achieved per rep.

        This is what you compare against the prescription to judge execution.
        """
        return self._get(f"/api/v1/activity/{activity_id}/intervals")

    def wellness(self, oldest: str, newest: str):
        """Daily wellness rows: restingHR, hrv, sleep, weight, plus ctl/atl/rampRate."""
        return self._get(
            f"/api/v1/athlete/{self.athlete_id}/wellness",
            oldest=oldest,
            newest=newest,
        )

    def events(self, oldest: str, newest: str):
        """Planned workouts, notes etc. on the calendar."""
        return self._get(
            f"/api/v1/athlete/{self.athlete_id}/events",
            oldest=oldest,
            newest=newest,
        )

    # --- writing -----------------------------------------------------------

    def create_workouts(self, workouts: list[dict], upsert: bool = True):
        """Create or update planned workouts (or notes etc.) on the calendar.

        Each item is an EventEx dict — see docs/intervals-workouts.md for the
        `description` workout-text syntax and a worked example.

        If upsert=True (default), events with a matching external_id are updated
        instead of duplicated on repeat calls; external_id must be set for that
        item to match. Returns the list of created/updated Event objects.
        """
        return self._post(
            f"/api/v1/athlete/{self.athlete_id}/events/bulk",
            workouts,
            upsert=upsert,
            upsertOnUid=False,
            updatePlanApplied=False,
        )

    def create_workout(self, **event_fields):
        """Convenience wrapper around create_workouts for a single workout."""
        return self.create_workouts([event_fields])[0]

    def duplicate_events(self, event_ids: list[int], weeks_between: int, num_copies: int = 1):
        return self._post(
            f"/api/v1/athlete/{self.athlete_id}/duplicate-events",
            {"eventIds": event_ids, "weeksBetween": weeks_between, "numCopies": num_copies},
        )

    def delete_events(self, ids: list[int] | None = None, external_ids: list[str] | None = None):
        doomed = [{"id": i} for i in (ids or [])] + [{"external_id": e} for e in (external_ids or [])]
        return self._put(f"/api/v1/athlete/{self.athlete_id}/events/bulk-delete", doomed)

    def update_sport_settings(self, settings_id: int, **fields):
        """Patch one sport-settings row — `ftp`, `lthr`, `max_hr`, `indoor_ftp`, zones.

        Get the id from `athlete()["sportSettings"]`; each row covers a set of
        activity types. Only the fields you pass are changed.

        These values drive every zone intervals.icu displays and the TSS it models,
        so they should track `plan.md` rather than drift from it — a stale FTP here
        silently rescales the load history.
        """
        return self._put(
            f"/api/v1/athlete/{self.athlete_id}/sport-settings/{settings_id}", fields
        )
