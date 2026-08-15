"""Connection smoke tests.

    pixi run check              # both
    pixi run check intervals    # just one
"""

import sys

from trainer.config import ROOT


def check_intervals() -> bool:
    from trainer import IntervalsClient

    client = IntervalsClient()
    me = client.athlete()
    ftp = me.get("icu_ftp")
    print(f"intervals.icu  OK — {me.get('name')} (id {me.get('id')})")
    if ftp:
        print(f"               FTP {ftp} W")
    else:
        print("               FTP not set — use absolute watts, % targets won't resolve")
    return True


def check_strava() -> bool:
    from trainer import StravaClient

    client = StravaClient()
    me = client.athlete()
    print(f"strava         OK — {me.get('firstname')} {me.get('lastname')} (id {me.get('id')})")
    for a in client.activities(limit=5):
        km = a["distance"] / 1000
        mins = a["moving_time"] / 60
        print(f"               {a['start_date_local'][:10]}  {a['type']:<10} {km:5.1f} km  {mins:4.0f} min  {a['name']}")
    return True


def check_hevy() -> bool:
    from trainer import HevyClient

    client = HevyClient()
    me = client.user()
    count = client.workout_count()
    print(f"hevy           OK — {me.get('name')} (id {me.get('id')})")
    print(f"               {count} workouts logged")
    for w in client.workouts(limit=3):
        sets = sum(len(e.get("sets") or []) for e in w.get("exercises") or [])
        print(f"               {w['start_time'][:10]}  {w['title'][:30]:<30} {sets:3} sets")
    return True


CHECKS = {"intervals": check_intervals, "strava": check_strava, "hevy": check_hevy}


def main():
    wanted = sys.argv[1:] or list(CHECKS)
    failed = False
    for name in wanted:
        if name not in CHECKS:
            raise SystemExit(f"unknown check {name!r} — pick from {', '.join(CHECKS)}")
        try:
            CHECKS[name]()
        except SystemExit as e:  # missing credentials — expected, keep going
            print(f"{name:<14} skipped — {e}")
        except Exception as e:
            failed = True
            print(f"{name:<14} FAILED — {type(e).__name__}: {e}")

    if failed:
        print(f"\nCredentials live in {ROOT / '.env'} — see README.md")
        sys.exit(1)


if __name__ == "__main__":
    main()
