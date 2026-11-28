"""Where settings live: a per-user config folder, plus the usual project `.env`.

Settings are read from these places, highest priority first (a value found earlier is never
overridden by a later source):

  1. real environment variables
  2. `.env` in the current folder
  3. `.env` in the project folder (only when running from a source checkout)
  4. `.env` in the user config folder (created by `shorts --init-config`)

The user folder is the one that survives upgrades and works when the tool is installed with
pip/pipx, so that is where an installed copy should keep its settings:

  macOS    ~/Library/Application Support/AI-Shorts
  Windows  %APPDATA%\\AI-Shorts
  Linux    $XDG_CONFIG_HOME/ai-shorts  (default ~/.config/ai-shorts)

Set SHORTS_CONFIG_DIR to use a different folder. Set SHORTS_IGNORE_DOTENV=1 to read no files at all
(used by the test-suite so a developer's real keys never leak into tests).
"""
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

APP_NAME = "AI-Shorts"


def config_dir() -> Path:
    override = os.environ.get("SHORTS_CONFIG_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    return (Path(xdg) if xdg else Path.home() / ".config") / APP_NAME.lower()


def user_env_file() -> Path:
    return config_dir() / ".env"


def project_root() -> Optional[Path]:
    """The source checkout this package runs from, or None when it was pip-installed."""
    root = Path(__file__).resolve().parent.parent
    if (root / "pyproject.toml").is_file() or (root / ".env.example").is_file():
        return root
    return None


def _candidates() -> List[Tuple[str, Path]]:
    found: List[Tuple[str, Path]] = []
    try:
        found.append(("current folder", Path.cwd() / ".env"))
    except OSError:  # the working directory was deleted
        pass
    root = project_root()
    if root is not None:
        found.append(("project folder", root / ".env"))
    found.append(("user config folder", user_env_file()))
    return found


def env_files() -> List[Path]:
    """Settings files that exist, highest priority first, without duplicates."""
    seen, out = set(), []
    for _, path in _candidates():
        try:
            key = path.resolve()
        except OSError:
            continue
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        out.append(path)
    return out


def load_env_files(files: Optional[List[Path]] = None) -> List[Path]:
    """Load settings files into os.environ without overriding anything already set."""
    if os.environ.get("SHORTS_IGNORE_DOTENV", "").strip() not in ("", "0"):
        return []
    from dotenv import load_dotenv

    files = env_files() if files is None else list(files)
    for f in files:  # highest priority first; override=False means the first value wins
        load_dotenv(f, override=False)
    return files


def env_template() -> str:
    from importlib.resources import files

    return (files("shorts_generator") / "data" / "env.example").read_text(encoding="utf-8")


def init_user_config() -> Tuple[Path, bool]:
    """Create the user settings file from the template. Returns (path, created)."""
    target = user_env_file()
    if target.exists():
        return target, False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(env_template(), encoding="utf-8")
    if os.name == "posix":
        os.chmod(target, 0o600)  # it will hold API keys
    return target, True


def describe() -> List[Tuple[str, Path, bool]]:
    """(label, path, exists) for every place settings are looked up, highest priority first.

    Places that resolve to the same file are merged into one entry.
    """
    merged: List[Tuple[str, Path, bool]] = []
    index = {}
    for label, path in _candidates():
        try:
            key = path.resolve()
        except OSError:
            key = path
        if key in index:
            i = index[key]
            merged[i] = (merged[i][0] + " + " + label, merged[i][1], merged[i][2])
        else:
            index[key] = len(merged)
            merged.append((label, path, path.is_file()))
    return merged
