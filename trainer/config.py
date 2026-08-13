"""Shared config: locates the repo root and loads .env once."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def require_env(name: str) -> str:
    """Fetch an env var, treating unset and empty-string as the same failure.

    dotenv happily loads `FOO=` as "", which would otherwise sail through to the
    API and come back as an opaque "invalid credentials" error.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"{name} is not set. Copy .env.example to .env and fill it in — see README.md."
        )
    return value


def get_env(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default
