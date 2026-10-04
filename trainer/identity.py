"""Who a profile's credentials belong to — and the check that runs before any write.

`pixi run check` (and `pixi run strava-auth`) record the account each service
reports for a profile's keys in `profiles/<name>/identity.json`. Before the first
write to intervals.icu or Hevy, the client asks the API who it is again and
refuses if the answer differs. That catches a key pasted into the wrong
profile's `.env`, which would otherwise write one athlete's workouts onto
another's calendar — and Hevy has no DELETE to undo it with.
"""

import json
import sys

from trainer.config import Profile, profile_names


class WrongAthlete(RuntimeError):
    """The live account behind a profile's keys isn't the one recorded for it."""


def recorded(profile: Profile) -> dict:
    if not profile.identity_path.exists():
        return {}
    return json.loads(profile.identity_path.read_text())


def record(
    profile: Profile, service: str, account_id, name: str | None, reset: bool = False
) -> None:
    """Remember who `service` says this profile's keys belong to.

    Refuses to replace a *different* recorded account unless `reset` — otherwise
    the check the docs tell you to run would quietly launder a wrong key into
    the record that's meant to catch it.
    """
    held = recorded(profile)
    previous = held.get(service)
    if previous and previous["id"] != str(account_id) and not reset:
        raise WrongAthlete(
            f"Profile {profile.name!r} is recorded as {service} account {previous['name']} "
            f"(id {previous['id']}), but its key now belongs to {name} (id {account_id}). "
            f"Fix {profile.env_path}, or re-run with --reset-identity if the change is intended."
        )
    held[service] = {"id": str(account_id), "name": name}
    profile.identity_path.write_text(json.dumps(held, indent=2) + "\n")


def confirm(profile: Profile, service: str, account_id, name: str | None) -> None:
    """Refuse to write unless the live account matches the recorded one."""
    held = recorded(profile).get(service)
    if held is None:
        raise WrongAthlete(
            f"No {service} identity recorded for profile {profile.name!r}, so there's "
            f"nothing to check this write against. Run `pixi run check {service}` first."
        )
    if held["id"] != str(account_id):
        raise WrongAthlete(
            f"Profile {profile.name!r} expects {service} account {held['name']} "
            f"(id {held['id']}), but its key belongs to {name} (id {account_id}). "
            f"Fix {profile.env_path} — nothing was written."
        )
    print(f"writing to {service}: {name} (id {account_id}, profile {profile.name})", file=sys.stderr)


def claimed_by(service: str, account_id, exclude: str) -> list[str]:
    """Other profiles that already hold this account — two profiles, one athlete."""
    owners = []
    for name in profile_names():
        if name == exclude:
            continue
        held = recorded(Profile.load(name)).get(service)
        if held and held["id"] == str(account_id):
            owners.append(name)
    return owners
