"""Shared HTTP plumbing for the API clients: timeouts, retries, rate limits.

A sync that walks months of history makes hundreds of calls, so the difference
between a run that resumes cleanly and one that dies half-written lives here.
Retries and backoff are urllib3's; this module only adds the two things it
doesn't do — a default timeout, and error messages that keep the response body.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# (connect, read). Without these a hung socket blocks the whole sync forever.
TIMEOUT = (10, 60)

# Transient server-side failures only. 429 is deliberately absent: the sync is
# incremental, so surfacing the quota (below) and resuming later beats sleeping
# through a 15-minute Strava window.
RETRY_STATUS = (500, 502, 503, 504)


class RateLimitExceeded(RuntimeError):
    """The API's quota is spent. Nothing to do but come back later."""


class _TimeoutAdapter(HTTPAdapter):
    """HTTPAdapter that applies a default timeout to requests that omit one."""

    def __init__(self, timeout=TIMEOUT, **kwargs):
        self.timeout = timeout
        super().__init__(**kwargs)

    def send(self, request, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def make_session(retries: int = 3, timeout=TIMEOUT) -> requests.Session:
    """A Session that retries transient failures and never hangs indefinitely.

    Retries are restricted to urllib3's idempotent default methods, so a failed
    `create_workouts` POST is never silently replayed onto the calendar.
    """
    session = requests.Session()
    adapter = _TimeoutAdapter(
        timeout=timeout,
        max_retries=Retry(
            total=retries,
            status_forcelist=RETRY_STATUS,
            backoff_factor=0.5,
            backoff_jitter=0.3,
            raise_on_status=False,
        ),
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def check(resp: requests.Response) -> requests.Response:
    """raise_for_status, but keeping the body — and naming a 429 for what it is.

    Both APIs explain themselves in the body (intervals.icu's 422 on
    Strava-sourced activities says so in as many words); the stock requests
    error throws that away.
    """
    if resp.ok:
        return resp
    if resp.status_code == 429:
        raise RateLimitExceeded(
            f"quota exhausted at {resp.url}\n{resp.text[:300]}\n"
            "Re-run later — the sync resumes where it stopped."
        )
    raise requests.HTTPError(
        f"{resp.status_code} {resp.reason} for {resp.url}\n{resp.text[:500]}",
        response=resp,
    )
