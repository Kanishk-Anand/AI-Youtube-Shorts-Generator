import os
import types

import pytest

from shorts_generator import config, paths
from shorts_generator.url_validation import validate_youtube_url


# ------------------------------------------------------------------ upstream hardening

def test_muapi_base_url_default_and_overrides(monkeypatch):
    monkeypatch.delenv("MUAPI_BASE_URL", raising=False)
    assert config._muapi_base_url() == "https://api.muapi.ai/api/v1"
    monkeypatch.setenv("MUAPI_BASE_URL", "https://api.muapi.ai/api/v1/")
    assert config._muapi_base_url() == "https://api.muapi.ai/api/v1"


@pytest.mark.parametrize("bad", [
    "http://api.muapi.ai/api/v1",              # not https
    "https://evil.example.com/api/v1",         # key would go to another host
    "https://user:pw@api.muapi.ai/api/v1",     # credentials in the URL
    "https://api.muapi.ai:8443/api/v1",        # odd port
    "https://api.muapi.ai/api/v1?x=1",         # query
])
def test_muapi_base_url_rejects_unsafe_values(monkeypatch, bad):
    monkeypatch.setenv("MUAPI_BASE_URL", bad)
    with pytest.raises(RuntimeError):
        config._muapi_base_url()


@pytest.mark.parametrize("value,prefix,ok", [
    ("", "", False),
    ("your_muapi_key_here", "", False),         # placeholder from .env.example
    ("short", "", False),
    ("sk-" + "a" * 30, "sk-", True),
    ("a" * 30, "sk-", False),                   # wrong provider prefix
])
def test_require_key_rules(value, prefix, ok):
    if ok:
        assert config._require_key(value, "K", "hint", prefix) == value
    else:
        with pytest.raises(RuntimeError):
            config._require_key(value, "K", "hint", prefix)


@pytest.mark.parametrize("url,ok", [
    ("https://www.youtube.com/watch?v=abc", True),
    ("https://youtu.be/abc", True),
    ("http://www.youtube.com/watch?v=abc", False),
    ("https://youtube.com.evil.com/watch?v=abc", False),
    ("https://user:pw@youtube.com/watch?v=abc", False),
    ("https://evil.example/x.mp4", False),
    ("", False),
])
def test_only_https_youtube_urls_are_accepted(url, ok):
    if ok:
        assert validate_youtube_url(url) == url
    else:
        with pytest.raises(ValueError):
            validate_youtube_url(url)


# ------------------------------------------------------------------ user config folder

def fake_sys(platform):
    return types.SimpleNamespace(platform=platform)


def test_config_dir_per_platform(monkeypatch, tmp_path):
    monkeypatch.delenv("SHORTS_CONFIG_DIR", raising=False)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))

    monkeypatch.setattr(paths, "sys", fake_sys("darwin"))
    assert paths.config_dir() == tmp_path / "Library" / "Application Support" / "AI-Shorts"

    monkeypatch.setattr(paths, "sys", fake_sys("win32"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert paths.config_dir() == tmp_path / "Roaming" / "AI-Shorts"
    monkeypatch.delenv("APPDATA")
    assert paths.config_dir() == tmp_path / "AppData" / "Roaming" / "AI-Shorts"

    monkeypatch.setattr(paths, "sys", fake_sys("linux"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert paths.config_dir() == tmp_path / "xdg" / "ai-shorts"
    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert paths.config_dir() == tmp_path / ".config" / "ai-shorts"


def test_config_dir_can_be_overridden(isolated_config):
    assert paths.config_dir() == isolated_config
    assert paths.user_env_file() == isolated_config / ".env"


def test_first_file_wins_and_real_environment_variables_beat_all_files(monkeypatch, tmp_path):
    monkeypatch.delenv("SHORTS_IGNORE_DOTENV")
    high, low = tmp_path / "high.env", tmp_path / "low.env"
    high.write_text("T_ONLY_HIGH=h\nT_BOTH=from-high\nT_ENV=from-file\n", encoding="utf-8")
    low.write_text("T_ONLY_LOW=l\nT_BOTH=from-low\n", encoding="utf-8")
    for key in ("T_ONLY_HIGH", "T_ONLY_LOW", "T_BOTH"):
        monkeypatch.setenv(key, "x")      # register for cleanup,
        monkeypatch.delenv(key)           # then make sure it starts unset
    monkeypatch.setenv("T_ENV", "from-environment")

    assert paths.load_env_files([high, low]) == [high, low]
    assert os.environ["T_ONLY_HIGH"] == "h" and os.environ["T_ONLY_LOW"] == "l"
    assert os.environ["T_BOTH"] == "from-high"
    assert os.environ["T_ENV"] == "from-environment"


def test_ignore_flag_reads_nothing(tmp_path):
    f = tmp_path / "x.env"
    f.write_text("T_IGNORED=1\n", encoding="utf-8")
    assert os.environ.get("SHORTS_IGNORE_DOTENV") == "1"
    assert paths.load_env_files([f]) == []
    assert "T_IGNORED" not in os.environ


def test_env_files_lists_only_existing_files_without_duplicates(monkeypatch, isolated_config, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert (tmp_path / ".env").exists() is False
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    found = paths.env_files()
    assert found[0] == tmp_path / ".env"
    assert len({p.resolve() for p in found}) == len(found)


def test_describe_merges_places_that_are_the_same_file(monkeypatch, isolated_config):
    root = paths.project_root()
    assert root is not None, "tests run from a source checkout"
    monkeypatch.chdir(root)
    labels = [label for label, _, _ in paths.describe()]
    assert any("current folder + project folder" in label for label in labels)


def test_init_user_config_creates_the_file_once(isolated_config):
    path, created = paths.init_user_config()
    assert created and path.read_text(encoding="utf-8") == paths.env_template()
    if os.name == "posix":
        assert (path.stat().st_mode & 0o777) == 0o600   # it will hold API keys
    path.write_text("EDITED=1\n", encoding="utf-8")
    again, created_again = paths.init_user_config()
    assert not created_again and again.read_text(encoding="utf-8") == "EDITED=1\n"
