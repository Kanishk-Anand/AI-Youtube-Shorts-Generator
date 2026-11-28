"""`python main.py --doctor`: check this machine and say exactly how to fix what's missing.

Plain ASCII output so it renders in any Windows or macOS terminal. Exit code 1 if anything
required is broken. Checks that only matter for one mode are reported as warnings.
"""
import importlib
import importlib.metadata as md
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, Tuple

from . import config
from .local.system import FFMPEG_HINT, PYTHON_HINT, os_name, run_text

OK, WARN, FAIL = "OK", "WARN", "FAIL"
Result = Tuple[str, str, str, str]  # status, label, detail, fix


def _venv_cmds() -> str:
    if os_name() == "windows":
        return ("py -3.12 -m venv .venv\n      .venv\\Scripts\\Activate.ps1      (cmd.exe: .venv\\Scripts\\activate.bat)\n"
                "      pip install -r requirements-local.txt")
    return "python3.12 -m venv .venv\n      source .venv/bin/activate\n      pip install -r requirements-local.txt"


def check_python() -> Result:
    v = sys.version_info
    label = f"Python {v.major}.{v.minor}.{v.micro}"
    if v < (3, 10):
        return FAIL, label, "3.10 or newer is required", f"Install Python 3.12: {PYTHON_HINT[os_name()]}"
    if v >= (3, 14):
        return (WARN, label, "dependencies such as av, ctranslate2 and opencv often have no wheels for this version",
                f"Use Python 3.12 in a fresh venv:\n      {_venv_cmds()}")
    return OK, label, "", ""


def check_venv() -> Result:
    if sys.prefix != sys.base_prefix:
        return OK, "Virtual environment", sys.prefix, ""
    return WARN, "Virtual environment", "not active; installs go into the system Python", f"Create and activate one:\n      {_venv_cmds()}"


def check_ffmpeg() -> List[Result]:
    out: List[Result] = []
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        if not path:
            out.append((FAIL, tool, "not found on PATH", f"Install it: {FFMPEG_HINT[os_name()]}"))
            return out
        first = (run_text([tool, "-version"]).stdout.splitlines() or [""])[0]
        out.append((OK, tool, first[:70], ""))
    if "libx264" not in run_text(["ffmpeg", "-hide_banner", "-encoders"]).stdout:
        out.append((FAIL, "ffmpeg libx264 encoder", "this ffmpeg build cannot write H.264",
                    f"Install a full build: {FFMPEG_HINT[os_name()]}"))
    return out


def _version(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "?"


def check_imports() -> List[Result]:
    out: List[Result] = []
    for module, pkg in (("yt_dlp", "yt-dlp"), ("faster_whisper", "faster-whisper"), ("cv2", "opencv-python"),
                        ("av", "av"), ("numpy", "numpy"), ("requests", "requests"), ("dotenv", "python-dotenv")):
        try:
            importlib.import_module(module)
            out.append((OK, pkg, _version(pkg), ""))
        except Exception as e:  # ImportError, or a broken native library
            out.append((FAIL, pkg, f"{e.__class__.__name__}: {str(e)[:80]}", "pip install -r requirements-local.txt"))
    return out


def check_opencv_faces() -> Result:
    try:
        import cv2  # type: ignore
        if not hasattr(cv2, "CascadeClassifier"):
            return (FAIL, "OpenCV face detector", f"opencv {cv2.__version__} has no CascadeClassifier (removed in 5.x)",
                    'pip install "opencv-python>=4.8,<5"')
        xml = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if not xml.exists():
            return FAIL, "OpenCV face detector", f"cascade file missing: {xml}", "pip install --force-reinstall opencv-python"
        return OK, "OpenCV face detector", "haar cascade found", ""
    except Exception as e:
        return FAIL, "OpenCV face detector", str(e)[:100], "pip install -r requirements-local.txt"


def check_av_compat() -> Result:
    """faster-whisper calls av.open(..., metadata_errors=...), which some av versions reject."""
    if not shutil.which("ffmpeg"):
        return WARN, "av / faster-whisper compatibility", "skipped (no ffmpeg)", ""
    try:
        import av  # type: ignore
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "t.mp4")
            r = run_text(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=5:duration=0.4",
                          "-f", "lavfi", "-i", "sine=duration=0.4", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", clip])
            if r.returncode != 0:
                return WARN, "av / faster-whisper compatibility", "could not create a test clip", ""
            av.open(clip, mode="r", metadata_errors="ignore").close()
        return OK, "av / faster-whisper compatibility", f"av {av.__version__}", ""
    except ImportError:
        return WARN, "av / faster-whisper compatibility", "skipped (av not installed)", ""
    except TypeError as e:
        return FAIL, "av / faster-whisper compatibility", str(e)[:90], 'pip install "av>=14,<16"'
    except Exception as e:
        return WARN, "av / faster-whisper compatibility", f"{e.__class__.__name__}: {str(e)[:70]}", ""


def check_output_dir() -> Result:
    d = Path(config.LOCAL_OUTPUT_DIR).resolve()
    try:
        d.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=d):
            pass
        return OK, "Output folder", str(d), ""
    except OSError as e:
        return FAIL, "Output folder", f"{d}: {e}", "Set LOCAL_OUTPUT_DIR to a folder you can write to"


def check_paths() -> List[Result]:
    cwd = str(Path.cwd())
    if os_name() == "windows" and not cwd.isascii():
        return [(WARN, "Working folder", "contains non-ASCII characters; OpenCV can fail to open videos from such paths on Windows",
                 "Run from a folder with a plain ASCII path, e.g. C:\\shorts")]
    return []


def check_whisper_cache() -> Result:
    hub = os.environ.get("HF_HUB_CACHE") or os.path.join(os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface")), "hub")
    cached = list(Path(hub).glob(f"models--*faster-whisper-{config.LOCAL_WHISPER_MODEL}*")) if Path(hub).exists() else []
    if cached:
        return OK, f"Whisper model '{config.LOCAL_WHISPER_MODEL}'", "downloaded", ""
    return WARN, f"Whisper model '{config.LOCAL_WHISPER_MODEL}'", "not downloaded yet; the first local run fetches it (needs internet)", ""


def check_llm() -> Result:
    from .local import llm
    try:
        llm.validate()
        return OK, "LLM provider", llm.describe(), ""
    except RuntimeError as e:
        return WARN, "LLM provider", f"{llm.active().name}: not ready", str(e)
    except Exception as e:
        return WARN, "LLM provider", str(e)[:100], "See --llm / LLM_PROVIDER in the README"


def check_muapi() -> Result:
    if not config.MUAPI_API_KEY:
        return WARN, "MuAPI key (--mode api)", "not set (only needed for --mode api)", "Add MUAPI_API_KEY to .env"
    try:
        config.require_api_key()  # same placeholder / length checks the app applies
    except RuntimeError:
        return (WARN, "MuAPI key (--mode api)", "still a placeholder value (only needed for --mode api)",
                "Put your real key in MUAPI_API_KEY in .env, or ignore this if you only use --mode local")
    return OK, "MuAPI key (--mode api)", "set", ""


def run_doctor() -> int:
    print(f"System: {os_name()} ({sys.platform}), Python {sys.version.split()[0]}\n")
    results: List[Result] = []
    for check in (check_python, check_venv, check_ffmpeg, check_imports, check_opencv_faces, check_av_compat,
                  check_output_dir, check_paths, check_whisper_cache, check_llm, check_muapi):
        r = check()
        results += r if isinstance(r, list) else [r]

    for status, label, detail, fix in results:
        print(f"[{status:<4}] {label}" + (f": {detail}" if detail else ""))
        if fix and status != OK:
            print(f"       fix: {fix}")
    fails = sum(1 for r in results if r[0] == FAIL)
    warns = sum(1 for r in results if r[0] == WARN)
    print(f"\n{'Everything needed for local mode looks good.' if not fails else f'{fails} problem(s) must be fixed before --mode local will work.'}"
          + (f" ({warns} warning(s))" if warns else ""))
    return 1 if fails else 0
