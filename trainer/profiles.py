"""Manage athlete profiles — one directory of credentials and data per athlete.

    pixi run profiles                         # list them, marking the active one
    pixi run profiles new alex                # profiles/alex/.env from .env.example
    pixi run profiles new alex --env FILE     # adopt an existing env file (moved in)
    pixi run profiles migrate simon           # move the pre-profile setup into one
    pixi run activate alex                    # make alex active (profiles/.active)
    pixi run activate --clear                 # forget it

`TRAINER_PROFILE` overrides `profiles/.active`, and `--profile` overrides both —
see trainer/config.py for the full order.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from trainer.config import (
    ACTIVE_FILE,
    ENV_VAR,
    NAME,
    PROFILES,
    ROOT,
    Profile,
    active_profile,
    profile_names,
)
from trainer.identity import recorded


def _list() -> int:
    names = profile_names()
    if not names:
        print("No profiles yet — `pixi run profiles new <name>`.")
        return 0
    try:
        current = active_profile().name
    except SystemExit as exc:
        current = None
        print(exc, file=sys.stderr)
    for name in names:
        held = recorded(Profile.load(name))
        who = ", ".join(f"{svc} {v['name']}" for svc, v in held.items()) or "no identity — run check"
        print(f"{'*' if name == current else ' '} {name:<14} {who}")
    return 0


def _activate(name: str | None, clear: bool) -> int:
    path = PROFILES / ACTIVE_FILE
    if clear:
        path.unlink(missing_ok=True)
        print("No profile active.")
        return 0
    if name is None:
        return _list()
    if name not in profile_names():
        raise SystemExit(f"No profile {name!r}. Known: {', '.join(profile_names()) or 'none'}.")
    path.write_text(name + "\n")
    print(f"Active profile: {name}")
    if (env := os.environ.get(ENV_VAR, "").strip()) and env != name:
        print(f"Note: {ENV_VAR}={env} is set in this shell and takes precedence.", file=sys.stderr)
    return 0


def _new(name: str, env: Path | None) -> int:
    if not NAME.match(name):
        raise SystemExit(f"Profile names are lowercase letters, digits, - and _: {name!r}")
    directory = PROFILES / name
    if directory.exists():
        raise SystemExit(f"{directory} already exists.")
    directory.mkdir(parents=True)
    if env is not None:
        shutil.move(env, directory / ".env")
        print(f"Moved {env} → {directory / '.env'}")
    else:
        shutil.copy(ROOT / ".env.example", directory / ".env")
        print(f"Created {directory / '.env'} — fill in the athlete's keys.")
    print(f"Then: `pixi run check --profile {name}` to record who the keys belong to.")
    return 0


def _migrate(name: str) -> int:
    """Move the single-athlete layout (.env, .strava_tokens.json, data/) into a profile."""
    if not NAME.match(name):
        raise SystemExit(f"Profile names are lowercase letters, digits, - and _: {name!r}")
    moves = [
        (ROOT / ".env", PROFILES / name / ".env"),
        (ROOT / ".strava_tokens.json", PROFILES / name / "strava_tokens.json"),
        (ROOT / "data", PROFILES / name / "data"),
    ]
    present = [(src, dst) for src, dst in moves if src.exists()]
    if not present:
        raise SystemExit("Nothing to migrate — no .env, .strava_tokens.json or data/ at the repo root.")
    if clash := [dst for _, dst in present if dst.exists()]:
        raise SystemExit(f"Refusing to overwrite: {', '.join(map(str, clash))}")
    (PROFILES / name).mkdir(parents=True, exist_ok=True)
    for src, dst in present:
        shutil.move(src, dst)
        print(f"Moved {src.relative_to(ROOT)} → {dst.relative_to(ROOT)}")
    print(f"Then: `pixi run check --profile {name}` to record who the keys belong to.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="list profiles (the default)")
    activate = sub.add_parser("activate", help="make a profile active")
    activate.add_argument("name", nargs="?")
    activate.add_argument("--clear", action="store_true", help="remove profiles/.active")
    new = sub.add_parser("new", help="create a profile")
    new.add_argument("name")
    new.add_argument("--env", type=Path, help="existing env file to move in")
    migrate = sub.add_parser("migrate", help="move the pre-profile layout into a profile")
    migrate.add_argument("name")
    args = parser.parse_args(argv)

    if args.command == "activate":
        return _activate(args.name, args.clear)
    if args.command == "new":
        return _new(args.name, args.env)
    if args.command == "migrate":
        return _migrate(args.name)
    return _list()


if __name__ == "__main__":
    raise SystemExit(main())
