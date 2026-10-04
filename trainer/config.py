"""Which athlete this process works for, and where their credentials and data live.

Each athlete is a directory under `profiles/` (gitignored):

    profiles/<name>/.env                 API keys and Strava app credentials
    profiles/<name>/strava_tokens.json   written by `pixi run strava-auth`
    profiles/<name>/identity.json        who the keys belong to, from `pixi run check`
    profiles/<name>/data/                the warehouse and raw Strava cache

The active profile is the first of:

    1. an explicit name (`--profile alex` on a CLI, or `active_profile("alex")`)
    2. the TRAINER_PROFILE environment variable
    3. `profiles/.active`, written by `pixi run activate alex`
    4. the only profile, if exactly one exists

With several profiles and none chosen, this refuses rather than guessing: a
silent default is how a workout lands on the wrong athlete's calendar.

Credentials are read from the profile's own `.env` and never from the process
environment, so a key exported in the shell can't leak into another athlete's
session.
"""

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"
ENV_VAR = "TRAINER_PROFILE"
ACTIVE_FILE = ".active"
NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True)
class Profile:
    name: str
    dir: Path
    source: str = "explicit"
    _env: dict = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def load(cls, name: str, source: str = "explicit", base: Path | None = None) -> "Profile":
        base = base or PROFILES
        directory = base / name
        if not directory.is_dir():
            known = ", ".join(profile_names(base)) or "none yet"
            raise SystemExit(
                f"No profile {name!r} under {base}. Known: {known}. "
                f"Create one with `pixi run profiles new {name}`."
            )
        env = dotenv_values(directory / ".env") if (directory / ".env").exists() else {}
        return cls(name, directory, source, {k: v for k, v in env.items() if v is not None})

    # --- paths -------------------------------------------------------------

    @property
    def env_path(self) -> Path:
        return self.dir / ".env"

    @property
    def strava_tokens(self) -> Path:
        return self.dir / "strava_tokens.json"

    @property
    def identity_path(self) -> Path:
        return self.dir / "identity.json"

    @property
    def data(self) -> Path:
        return self.dir / "data"

    @property
    def warehouse(self) -> Path:
        return self.data / "warehouse"

    @property
    def raw(self) -> Path:
        return self.data / "strava"

    # --- credentials -------------------------------------------------------

    def require(self, name: str) -> str:
        """Fetch a credential, treating unset and empty-string as the same failure.

        dotenv happily loads `FOO=` as "", which would otherwise sail through to
        the API and come back as an opaque "invalid credentials" error.
        """
        value = self._env.get(name, "").strip()
        if not value:
            raise SystemExit(
                f"{name} is not set for profile {self.name!r}. "
                f"Fill it in at {self.env_path} — see README.md."
            )
        return value

    def get(self, name: str, default: str) -> str:
        return self._env.get(name, "").strip() or default


def profile_names(base: Path | None = None) -> list[str]:
    base = base or PROFILES
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and NAME.match(p.name))


def read_active_file(base: Path | None = None) -> str | None:
    path = (base or PROFILES) / ACTIVE_FILE
    if not path.exists():
        return None
    return path.read_text().strip() or None


def active_profile(name: str | None = None, base: Path | None = None) -> Profile:
    """Resolve the profile this process works for, in the order the module doc gives."""
    base = base or PROFILES
    if name:
        return _announce(Profile.load(name, "--profile", base))
    if env := os.environ.get(ENV_VAR, "").strip():
        return _announce(Profile.load(env, ENV_VAR, base))
    if active := read_active_file(base):
        return _announce(Profile.load(active, f"{base.name}/{ACTIVE_FILE}", base))

    names = profile_names(base)
    if len(names) == 1:
        return _announce(Profile.load(names[0], "only profile", base))
    if not names:
        legacy = (ROOT / ".env").exists() or (ROOT / "data").exists()
        hint = (
            "Move the existing setup into one with `pixi run profiles migrate <name>`."
            if legacy
            else "Create one with `pixi run profiles new <name>`."
        )
        raise SystemExit(f"No athlete profiles yet. {hint}")
    raise SystemExit(
        f"Several profiles ({', '.join(names)}) and none active. "
        f"Run `pixi run activate <name>`, set {ENV_VAR}, or pass --profile."
    )


_announced: set[tuple[str, str]] = set()


def _announce(profile: Profile) -> Profile:
    """Say once per process who we're working for — on stderr, so piped output stays clean."""
    key = (profile.name, profile.source)
    if key not in _announced:
        _announced.add(key)
        print(f"athlete: {profile.name} (from {profile.source})", file=sys.stderr)
    return profile
