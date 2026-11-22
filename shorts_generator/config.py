import os
import re
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()

MUAPI_API_KEY = os.getenv("MUAPI_API_KEY", "").strip()


def _muapi_base_url() -> str:
    value = os.getenv("MUAPI_BASE_URL", "https://api.muapi.ai/api/v1").strip().rstrip("/")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        # Accessing .port also validates malformed port numbers.
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("MUAPI_BASE_URL must be a valid HTTPS URL.") from exc

    if (
        parsed.scheme.lower() != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or port not in (None, 443)
    ):
        raise RuntimeError(
            "MUAPI_BASE_URL must be an HTTPS URL without credentials, query, fragment, "
            "or a non-standard port."
        )

    if host.lower() != "api.muapi.ai":
        raise RuntimeError(
            f"MUAPI_BASE_URL host {host!r} is not allowed. Requests include MUAPI_API_KEY; "
            "the host must be api.muapi.ai."
        )
    return value


MUAPI_BASE_URL = _muapi_base_url()

POLL_INTERVAL_SECONDS = float(os.getenv("MUAPI_POLL_INTERVAL", "5"))
POLL_TIMEOUT_SECONDS = float(os.getenv("MUAPI_POLL_TIMEOUT", "600"))

# Local-mode (--mode local) settings — only consulted when running offline.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.8:27b")
# Ollama's default context window is small and silently truncates long prompts,
# so set it explicitly. A 20-min transcript chunk is roughly 8-10k tokens.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT", "600"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
# Provider-neutral overrides (see shorts_generator/local/llm.py)
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()          # overrides the selected provider's model
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")  # for LLM_PROVIDER=openai_compatible
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()      # optional; local servers usually need none
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT", "300"))
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()  # optional, for the openai provider
LOCAL_WHISPER_MODEL = os.getenv("LOCAL_WHISPER_MODEL", "base")
LOCAL_WHISPER_DEVICE = os.getenv("LOCAL_WHISPER_DEVICE", "auto")  # auto / cpu / cuda
LOCAL_OUTPUT_DIR = os.path.abspath(
    os.path.expanduser(os.getenv("LOCAL_OUTPUT_DIR", "output").strip() or "output")
)
# face = track the speaker; center = fixed centre crop (no tracking, no shake)
LOCAL_CROP_MODE = os.getenv("LOCAL_CROP_MODE", "face").strip().lower()
# Split layout (LOCAL_CROP_MODE=split): gameplay on top, a second panel below.
LOCAL_FACECAM = os.getenv("LOCAL_FACECAM", "").strip()            # "x,y,w,h" box in the source video
LOCAL_BOTTOM_VIDEO = os.getenv("LOCAL_BOTTOM_VIDEO", "").strip()  # any video file; overrides the facecam
LOCAL_SPLIT_RATIO = float(os.getenv("LOCAL_SPLIT_RATIO", "0.6"))  # fraction of the height for the top panel

# VAD (Voice Activity Detection) settings for faster-whisper
# Default threshold is 0.5; lower = more sensitive, higher = less sensitive
# Default min_speech_duration_ms is 250ms; increase to avoid tiny false positives
# Default min_silence_duration_ms is 2000ms; increase to avoid splitting mid-sentence
# DISABLED by default because VAD is too aggressive on mixed speech/music content
LOCAL_WHISPER_VAD_FILTER = os.getenv("LOCAL_WHISPER_VAD_FILTER", "false").strip().lower() == "true"
_vad_params_env = os.getenv("LOCAL_WHISPER_VAD_PARAMETERS", "")
if _vad_params_env:
    import json
    LOCAL_WHISPER_VAD_PARAMETERS = json.loads(_vad_params_env)
else:
    # Match faster-whisper defaults when VAD is enabled
    LOCAL_WHISPER_VAD_PARAMETERS = {
        "threshold": 0.5,
        "min_speech_duration_ms": 250,
        "max_speech_duration_s": float("inf"),
        "min_silence_duration_ms": 2000,
        "speech_pad_ms": 400,
    }


_PLACEHOLDER_KEY = re.compile(
    r"^(?:your_[a-z0-9_-]*key_here|xxx+|x{4,}|changeme|change[-_ ]?me|"
    r"replace[-_ ]?me|placeholder|<[^>]+>)$",
    re.IGNORECASE,
)


def _require_key(
    value: str,
    name: str,
    setup_hint: str,
    expected_prefix: str = "",
) -> str:
    if not value:
        raise RuntimeError(f"{name} is not set. {setup_hint}")
    if _PLACEHOLDER_KEY.fullmatch(value.strip()):
        raise RuntimeError(
            f"{name} still contains a placeholder value. Replace it with a real key. {setup_hint}"
        )
    if len(value) < 16:
        raise RuntimeError(f"{name} looks too short to be a valid API key. {setup_hint}")
    if expected_prefix and not value.startswith(expected_prefix):
        raise RuntimeError(
            f"{name} must start with {expected_prefix!r}. Check that you supplied the right key. {setup_hint}"
        )
    return value


def require_api_key() -> str:
    return _require_key(
        MUAPI_API_KEY,
        "MUAPI_API_KEY",
        "Add it to your .env file or export it as an environment variable.",
    )


def require_openai_key() -> str:
    return _require_key(
        OPENAI_API_KEY,
        "OPENAI_API_KEY",
        "Local mode needs an OpenAI key for highlight ranking. Add it to your .env or export it, "
        "or switch back to --mode api.",
        expected_prefix="sk-",
    )
