"""Client for the Hevy API — the strength log.

Auth: an `api-key` header, not Bearer. Get the key from
https://hevy.com/settings?developer — the public API is **Hevy Pro only**.
Docs: https://api.hevyapp.com/docs/

Three properties of this API shape everything below.

**Pages are capped at 10 items** (100 for exercise templates), so anything that
walks history is a loop rather than a request. A year of lifting is a couple of
dozen requests, not one.

**Nothing can be deleted through the API** — there is no DELETE on any
resource. A routine written by mistake is edited into shape or abandoned in the
app by hand. Plan pushes accordingly: update in place, don't rebuild.

**Routines carry absolute kilograms.** There is no %1RM equivalent of `%FTP`
here, which is exactly the staleness trap CLAUDE.md names. The prescription
stays relative in `plan.md`; the kilograms are resolved at push time from the
anchors in `plan/decisions.md`. See docs/hevy.md.
"""

from trainer.config import require_env
from trainer.http import check, make_session

BASE_URL = "https://api.hevyapp.com"

# The API's own ceiling. Asking for more is a 400, not a truncated page.
MAX_PAGE_SIZE = 10
MAX_TEMPLATE_PAGE_SIZE = 100


class HevyClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or require_env("HEVY_API_KEY")
        self.session = make_session()
        self.session.headers.update({"api-key": self.api_key, "Accept": "application/json"})

    def _get(self, path: str, **params):
        params = {k: v for k, v in params.items() if v is not None}
        return check(self.session.get(f"{BASE_URL}{path}", params=params)).json()

    def _post(self, path: str, json_body):
        return check(self.session.post(f"{BASE_URL}{path}", json=json_body)).json()

    def _put(self, path: str, json_body):
        return check(self.session.put(f"{BASE_URL}{path}", json=json_body)).json()

    def _batches(self, path: str, key: str, page_size: int = MAX_PAGE_SIZE, **params):
        """Yield each page of a paginated endpoint as a list.

        Each response carries `page_count`, so this stops on the real last page
        rather than probing for a short one. Callers that want to stop walking
        partway need the page boundary, which is why this yields lists.
        """
        page = 1
        while True:
            payload = self._get(path, page=page, pageSize=page_size, **params)
            yield payload.get(key) or []
            if page >= (payload.get("page_count") or 0):
                return
            page += 1

    def _pages(self, path: str, key: str, page_size: int = MAX_PAGE_SIZE, **params):
        """Every item across a paginated endpoint, flattened."""
        for batch in self._batches(path, key, page_size, **params):
            yield from batch

    # --- reading -----------------------------------------------------------

    def user(self):
        """Profile — id, display name, public URL. The cheapest auth check.

        Unwrapped: this endpoint is the only one that nests its payload under
        `data`.
        """
        return self._get("/v1/user/info")["data"]

    def workout_count(self) -> int:
        """Total workouts on the account, in one request.

        Worth calling before a backfill: at 10 per page it tells you what the
        walk will cost.
        """
        return self._get("/v1/workouts/count")["workout_count"]

    def workouts(self, limit: int | None = None, since: str | None = None):
        """Completed workouts, newest first, with every set nested inside.

        `since` is an ISO date or timestamp. Every row is filtered against it,
        and the walk gives up once an entire page predates it — the filter is
        what's load-bearing, the early stop only saves requests. So if Hevy ever
        returns these out of order the result is a longer walk, not wrong data.
        """
        out: list[dict] = []
        for batch in self._batches("/v1/workouts", "workouts"):
            kept = [w for w in batch if not since or (w.get("start_time") or "") >= since]
            out += kept
            if limit is not None and len(out) >= limit:
                return out[:limit]
            if since and batch and not kept:
                break
        return out

    def workout(self, workout_id: str):
        return self._get(f"/v1/workouts/{workout_id}")

    def workout_events(self, since: str):
        """Updates and deletions since `since` — how a local cache stays honest.

        Returns event dicts of two shapes: `{"type": "updated", "workout": {...}}`
        and `{"type": "deleted", "id": ..., "deleted_at": ...}`. The deleted case
        is the only way to learn a workout is gone; re-reading the list endpoint
        can only ever show you what still exists.

        `since` is an ISO 8601 timestamp, e.g. `2026-07-01T00:00:00Z`.
        """
        return list(self._pages("/v1/workouts/events", "events", since=since))

    def routines(self):
        """Every routine — Hevy's word for a workout template you start from."""
        return list(self._pages("/v1/routines", "routines"))

    def routine(self, routine_id: str):
        return self._get(f"/v1/routines/{routine_id}")

    def routine_folders(self):
        return list(self._pages("/v1/routine_folders", "routine_folders"))

    def exercise_templates(self):
        """The exercise catalogue — ~400 built-ins plus any custom ones.

        `exercise_template_id` is what a routine references, so a push resolves
        names against this first. Pages are 100 here, not 10.
        """
        return list(
            self._pages(
                "/v1/exercise_templates",
                "exercise_templates",
                page_size=MAX_TEMPLATE_PAGE_SIZE,
            )
        )

    def exercise_history(self, exercise_template_id: str):
        """Every set ever logged for one exercise, flat. The progression view."""
        return self._get(f"/v1/exercise_history/{exercise_template_id}")[
            "exercise_history"
        ]

    # --- writing -----------------------------------------------------------

    def create_routine(
        self,
        title: str,
        exercises: list[dict],
        folder_id: int | None = None,
        notes: str | None = None,
    ):
        """Create a routine. Returns the created Routine, whose `id` you keep.

        Each exercise is `{exercise_template_id, sets, rest_seconds?, notes?,
        superset_id?}`; each set is `{type, weight_kg?, reps?, rep_range?,
        duration_seconds?, distance_meters?}` with `type` one of `warmup`,
        `normal`, `failure`, `dropset`.

        There is no delete endpoint and the account has a routine cap, so a
        duplicate title is not a harmless mistake — it's a slot spent. Push a
        week by updating last week's routine where one exists.
        """
        body = {"title": title, "folder_id": folder_id, "exercises": exercises}
        if notes is not None:
            body["notes"] = notes
        return self._post("/v1/routines", {"routine": body})

    def update_routine(self, routine_id: str, title: str, exercises: list[dict], **fields):
        """Replace a routine's contents. `exercises` is the whole list, not a patch."""
        return self._put(
            f"/v1/routines/{routine_id}",
            {"routine": {"title": title, "exercises": exercises, **fields}},
        )

    def create_routine_folder(self, title: str):
        """Create a folder. It lands at index 0 and pushes the others down."""
        return self._post("/v1/routine_folders", {"routine_folder": {"title": title}})

    def create_exercise_template(
        self,
        title: str,
        exercise_type: str,
        muscle_group: str,
        other_muscles: list[str] | None = None,
        equipment_category: str = "none",
    ):
        """Add a custom exercise. Rarely needed — the 451 built-ins cover most of it.

        `exercise_type`: `weight_reps`, `reps_only`, `bodyweight_reps`,
        `bodyweight_assisted_reps`, `duration`, `weight_duration`,
        `distance_duration`, `short_distance_weight`.

        `muscle_group` / `other_muscles`: `quadriceps`, `hamstrings`, `glutes`,
        `calves`, `abductors`, `adductors`, `chest`, `lats`, `upper_back`,
        `lower_back`, `traps`, `shoulders`, `biceps`, `triceps`, `forearms`,
        `abdominals`, `neck`, `cardio`, `full_body`, `other`.

        `equipment_category`: `none`, `barbell`, `dumbbell`, `kettlebell`,
        `machine`, `plate`, `resistance_band`, `suspension`, `other`.

        Note the request field names differ from the ones the read endpoints
        return (`muscle_group` here vs `primary_muscle_group` there).
        """
        return self._post(
            "/v1/exercise_templates",
            {
                "exercise": {
                    "title": title,
                    "exercise_type": exercise_type,
                    "muscle_group": muscle_group,
                    "other_muscles": other_muscles or [],
                    "equipment_category": equipment_category,
                }
            },
        )

    def create_workout(
        self,
        title: str,
        start_time: str,
        end_time: str,
        exercises: list[dict],
        description: str | None = None,
        is_private: bool = False,
    ):
        """Log a completed workout. For backfilling sessions done elsewhere —
        day to day the app is the better place to enter sets."""
        return self._post(
            "/v1/workouts",
            {
                "workout": {
                    "title": title,
                    "description": description,
                    "start_time": start_time,
                    "end_time": end_time,
                    "is_private": is_private,
                    "exercises": exercises,
                }
            },
        )

    def update_workout(self, workout_id: str, **workout_fields):
        return self._put(f"/v1/workouts/{workout_id}", {"workout": workout_fields})
