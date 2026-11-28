"""Shared fixtures. Tests must never read a developer's real settings or API keys."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

# This must run before the package is first imported: config reads the environment at import time.
os.environ["SHORTS_IGNORE_DOTENV"] = "1"
for _name in list(os.environ):
    if _name.startswith(("LLM_", "OLLAMA_", "MUAPI_", "OPENAI_", "LOCAL_")):
        del os.environ[_name]

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def pytest_collection_modifyitems(config, items):
    if HAVE_FFMPEG:
        return
    skip = pytest.mark.skip(reason="ffmpeg/ffprobe are not on PATH")
    for item in items:
        if "ffmpeg" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def synthetic_video(tmp_path_factory) -> Path:
    """A 6-second 320x180 clip with picture and a sine tone, built with ffmpeg.

    The file name has a space in it on purpose: paths with spaces must work everywhere.
    """
    if not HAVE_FFMPEG:
        pytest.skip("ffmpeg/ffprobe are not on PATH")
    out = tmp_path_factory.mktemp("media") / "sample video.mp4"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=6",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)],
        check=True,
    )
    return out


@pytest.fixture
def isolated_config(monkeypatch, tmp_path) -> Path:
    """Point the user config folder at an empty temp folder."""
    folder = tmp_path / "user-config"
    monkeypatch.setenv("SHORTS_CONFIG_DIR", str(folder))
    return folder


def make_transcript(duration: float, seg: float = 10.0) -> dict:
    segments = [{"start": float(t), "end": float(t) + seg, "text": f"line {t}"}
                for t in range(0, int(duration), int(seg))]
    return {"duration": float(duration), "segments": segments}


def highlight(start, end, score=80, title="t", hook="h", reason="r") -> dict:
    return {"title": title, "start_time": start, "end_time": end, "score": score,
            "hook_sentence": hook, "virality_reason": reason}
