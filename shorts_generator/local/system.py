"""Cross-platform helpers: external tools, subprocess decoding, per-OS install hints."""
import platform
import shutil
import subprocess
from typing import List

FFMPEG_HINT = {
    "mac": "brew install ffmpeg",
    "windows": "winget install Gyan.FFmpeg   (then open a new terminal)   or: choco install ffmpeg",
    "linux": "sudo apt install ffmpeg",
}
PYTHON_HINT = {
    "mac": "brew install python@3.12",
    "windows": "winget install Python.Python.3.12",
    "linux": "sudo apt install python3.12 python3.12-venv",
}


def os_name() -> str:
    """'mac', 'windows' or 'linux'."""
    return {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")


def run_text(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, capturing stdout/stderr as UTF-8 text.

    ffmpeg/ffprobe write UTF-8 on every OS, but `text=True` decodes with the locale codec
    (cp1252 on Windows) and can raise on non-ASCII file names. Undecodable bytes are replaced.
    """
    return subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", **kwargs)


def ensure_ffmpeg() -> None:
    """Raise a RuntimeError with an install command for this OS if ffmpeg/ffprobe are missing."""
    missing = [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None]
    if missing:
        raise RuntimeError(
            f"{' and '.join(missing)} not found on PATH. Install it with:\n    {FFMPEG_HINT[os_name()]}"
        )
