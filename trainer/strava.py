"""Client for the Strava API.

Auth: OAuth2. Run `python -m trainer.strava_auth` once to authorize; this client
then refreshes the access token automatically (they expire every 6h).
Docs: https://developers.strava.com/docs/reference/
"""

import json
import time
from dataclasses import dataclass

import requests

from trainer.config import ROOT, require_env
from trainer.http import check, make_session

BASE_URL = "https://www.strava.com/api/v3"
TOKENS_PATH = ROOT / ".strava_tokens.json"


@dataclass
class Budget:
    """What's left of Strava's quota, as of the last response.

    Strava allows 100 requests per 15 minutes and 1000 per day, and reports
    usage on every response. Reading it lets a sync stop one short of the wall
    and resume later instead of failing mid-write.
    """

    used: int = 0
    limit: int = 0
    daily_used: int = 0
    daily_limit: int = 0

    @property
    def remaining(self) -> int:
        """Requests left before the tighter of the two windows closes."""
        if not self.limit:
            return 100  # nothing observed yet — assume a fresh 15-minute window
        return max(0, min(self.limit - self.used, self.daily_limit - self.daily_used))


class StravaClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self.client_id = client_id or require_env("STRAVA_CLIENT_ID")
        self.client_secret = client_secret or require_env("STRAVA_CLIENT_SECRET")
        if not TOKENS_PATH.exists():
            raise SystemExit(
                f"Not authorized yet — no {TOKENS_PATH.name}. "
                "Run `pixi run python -m trainer.strava_auth` first."
            )
        self.tokens = json.loads(TOKENS_PATH.read_text())
        self.session = make_session()
        self.budget = Budget()

    def _access_token(self) -> str:
        """Return a valid access token, refreshing if it expires within a minute."""
        if self.tokens["expires_at"] - time.time() > 60:
            return self.tokens["access_token"]

        resp = self.session.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.tokens["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        payload = check(resp).json()
        self.tokens = {
            "access_token": payload["access_token"],
            "refresh_token": payload["refresh_token"],
            "expires_at": payload["expires_at"],
        }
        TOKENS_PATH.write_text(json.dumps(self.tokens, indent=2))
        return self.tokens["access_token"]

    def _get(self, path: str, **params):
        resp = self.session.get(
            f"{BASE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {self._access_token()}"},
        )
        self._note_budget(resp)
        return check(resp).json()

    def _note_budget(self, resp: requests.Response) -> None:
        """Record quota usage from the response headers.

        Strava reports both the overall and the read-only allowance; the
        stricter of the two is what actually stops you, so track that.
        """
        for limit_header, usage_header in (
            ("X-RateLimit-Limit", "X-RateLimit-Usage"),
            ("X-ReadRateLimit-Limit", "X-ReadRateLimit-Usage"),
        ):
            limits, usages = resp.headers.get(limit_header), resp.headers.get(usage_header)
            if not limits or not usages:
                continue
            try:
                limit, daily_limit = (int(v) for v in limits.split(","))
                used, daily_used = (int(v) for v in usages.split(","))
            except ValueError:
                continue
            seen = Budget(used, limit, daily_used, daily_limit)
            if not self.budget.limit or seen.remaining < self.budget.remaining:
                self.budget = seen

    def athlete(self):
        return self._get("/athlete")

    def activities(
        self,
        after: int | None = None,
        before: int | None = None,
        limit: int | None = 30,
    ):
        """Recent activities, newest first.

        after/before are Unix timestamps (seconds). Pages through the API as
        needed; `limit=None` means every activity in the range, however many
        pages that takes.
        """
        out: list[dict] = []
        page = 1
        while True:
            per_page = 200 if limit is None else min(200, limit - len(out))
            batch = self._get(
                "/athlete/activities",
                page=page,
                per_page=per_page,
                **{k: v for k, v in (("after", after), ("before", before)) if v is not None},
            )
            out.extend(batch)
            # A short page is the last page — Strava has no "more" flag.
            if len(batch) < per_page:
                break
            if limit is not None and len(out) >= limit:
                break
            page += 1
        return out if limit is None else out[:limit]

    def activity(self, activity_id: int, include_all_efforts: bool = False):
        """Full detail for one activity — more fields than the list endpoint,
        including per-lap splits and segment efforts."""
        return self._get(f"/activities/{activity_id}", include_all_efforts=include_all_efforts)

    def activity_streams(self, activity_id: int, keys: list[str] | None = None):
        """Time-series data: watts, heartrate, velocity_smooth, altitude, latlng, ..."""
        keys = keys or ["time", "heartrate", "watts", "velocity_smooth", "altitude"]
        return self._get(
            f"/activities/{activity_id}/streams",
            keys=",".join(keys),
            key_by_type="true",
        )

    def stats(self, athlete_id: int | None = None):
        """Rolling / YTD / all-time totals."""
        athlete_id = athlete_id or self.athlete()["id"]
        return self._get(f"/athletes/{athlete_id}/stats")
