"""Which athlete a process works for — getting this wrong writes to someone else's calendar."""

import pytest

from trainer import config, identity
from trainer.config import ACTIVE_FILE, ENV_VAR, Profile, active_profile


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(config, "PROFILES", tmp_path)
    return tmp_path


def make(base, name, env="INTERVALS_API_KEY=key-" + "{name}\n"):
    (base / name).mkdir()
    (base / name / ".env").write_text(env.format(name=name))


def test_only_profile_is_used_without_being_asked(base):
    make(base, "simon")
    assert active_profile().name == "simon"


def test_several_profiles_and_none_chosen_refuses(base):
    make(base, "simon")
    make(base, "sabrina")
    with pytest.raises(SystemExit, match="none active"):
        active_profile()


def test_precedence_flag_then_env_then_file(base, monkeypatch):
    for name in ("simon", "sabrina", "alex"):
        make(base, name)
    (base / ACTIVE_FILE).write_text("alex\n")
    assert active_profile().name == "alex"

    monkeypatch.setenv(ENV_VAR, "sabrina")
    assert active_profile().name == "sabrina"

    assert active_profile("simon").name == "simon"


def test_unknown_profile_is_an_error_not_a_fallback(base, monkeypatch):
    make(base, "simon")
    monkeypatch.setenv(ENV_VAR, "simno")
    with pytest.raises(SystemExit, match="No profile 'simno'"):
        active_profile()


def test_credentials_come_from_the_profile_not_the_shell(base, monkeypatch):
    make(base, "sabrina", env="")
    monkeypatch.setenv("INTERVALS_API_KEY", "simons-key")
    profile = Profile.load("sabrina", base=base)
    with pytest.raises(SystemExit, match="not set for profile 'sabrina'"):
        profile.require("INTERVALS_API_KEY")


def test_profiles_get_separate_data_dirs(base):
    make(base, "simon")
    make(base, "sabrina")
    a, b = Profile.load("simon", base=base), Profile.load("sabrina", base=base)
    assert a.warehouse != b.warehouse and a.raw != b.raw
    assert a.require("INTERVALS_API_KEY") == "key-simon"


def test_write_refused_when_key_belongs_to_someone_else(base):
    make(base, "sabrina")
    profile = Profile.load("sabrina", base=base)
    identity.record(profile, "intervals", "i222", "Sabrina")

    identity.confirm(profile, "intervals", "i222", "Sabrina")  # matches — fine
    with pytest.raises(identity.WrongAthlete, match="belongs to Simon"):
        identity.confirm(profile, "intervals", "i111", "Simon")


def test_write_refused_when_no_identity_recorded(base):
    make(base, "sabrina")
    with pytest.raises(identity.WrongAthlete, match="pixi run check intervals"):
        identity.confirm(Profile.load("sabrina", base=base), "intervals", "i222", "Sabrina")


def test_check_cannot_quietly_replace_a_recorded_account(base):
    """Re-running check after a key mix-up must not launder the wrong account into the record."""
    make(base, "sabrina")
    profile = Profile.load("sabrina", base=base)
    identity.record(profile, "intervals", "i222", "Sabrina")

    with pytest.raises(identity.WrongAthlete, match="--reset-identity"):
        identity.record(profile, "intervals", "i111", "Simon")
    identity.confirm(profile, "intervals", "i222", "Sabrina")  # record untouched

    identity.record(profile, "intervals", "i111", "Simon", reset=True)
    identity.confirm(profile, "intervals", "i111", "Simon")
