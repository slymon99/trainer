"""Connection smoke tests — and where each profile's identity gets recorded.

    pixi run check                      # every service, active profile
    pixi run check intervals            # just one
    pixi run check --profile alex       # another athlete

A passing check records who each service says the keys belong to in
`profiles/<name>/identity.json`. Writes are checked against that before they
go out — see trainer/identity.py.
"""

import argparse

from trainer.config import Profile, active_profile
from trainer.identity import claimed_by, record


def check_intervals(profile: Profile) -> bool:
    from trainer import IntervalsClient

    client = IntervalsClient(profile)
    me = client.athlete()
    record(profile, "intervals", me.get("id"), me.get("name"))
    ftp = me.get("icu_ftp")
    print(f"intervals.icu  OK — {me.get('name')} (id {me.get('id')})")
    if ftp:
        print(f"               FTP {ftp} W")
    else:
        print("               FTP not set — use absolute watts, % targets won't resolve")
    _warn_shared(profile, "intervals", me.get("id"))
    return True


def check_strava(profile: Profile) -> bool:
    from trainer import StravaClient

    client = StravaClient(profile)
    me = client.athlete()
    name = f"{me.get('firstname')} {me.get('lastname')}"
    record(profile, "strava", me.get("id"), name)
    print(f"strava         OK — {name} (id {me.get('id')})")
    for a in client.activities(limit=5):
        km = a["distance"] / 1000
        mins = a["moving_time"] / 60
        print(f"               {a['start_date_local'][:10]}  {a['type']:<10} {km:5.1f} km  {mins:4.0f} min  {a['name']}")
    _warn_shared(profile, "strava", me.get("id"))
    return True


def check_hevy(profile: Profile) -> bool:
    from trainer import HevyClient

    client = HevyClient(profile)
    me = client.user()
    record(profile, "hevy", me.get("id"), me.get("name"))
    count = client.workout_count()
    print(f"hevy           OK — {me.get('name')} (id {me.get('id')})")
    print(f"               {count} workouts logged")
    for w in client.workouts(limit=3):
        sets = sum(len(e.get("sets") or []) for e in w.get("exercises") or [])
        print(f"               {w['start_time'][:10]}  {w['title'][:30]:<30} {sets:3} sets")
    _warn_shared(profile, "hevy", me.get("id"))
    return True


def _warn_shared(profile: Profile, service: str, account_id) -> None:
    if others := claimed_by(service, account_id, exclude=profile.name):
        print(f"               WARNING: the same {service} account is recorded for {', '.join(others)}")


CHECKS = {"intervals": check_intervals, "strava": check_strava, "hevy": check_hevy}


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "services", nargs="*", metavar="SERVICE", help=f"any of {', '.join(CHECKS)} (default: all)"
    )
    parser.add_argument("--profile", help="athlete profile (default: the active one)")
    args = parser.parse_args(argv)
    if unknown := set(args.services) - set(CHECKS):
        parser.error(f"unknown check(s) {', '.join(sorted(unknown))} — pick from {', '.join(CHECKS)}")
    profile = active_profile(args.profile)

    failed = False
    for name in args.services or list(CHECKS):
        try:
            CHECKS[name](profile)
        except SystemExit as e:  # missing credentials — expected, keep going
            print(f"{name:<14} skipped — {e}")
        except Exception as e:
            failed = True
            print(f"{name:<14} FAILED — {type(e).__name__}: {e}")

    if failed:
        print(f"\nCredentials live in {profile.env_path} — see README.md")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
