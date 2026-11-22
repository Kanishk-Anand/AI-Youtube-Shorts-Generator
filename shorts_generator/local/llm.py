"""Pluggable LLM backends for --mode local (highlight ranking) and --critique.

Pick one with LLM_PROVIDER (or --llm); override its model with LLM_MODEL (or --llm-model).

  openai             OpenAI via the official SDK       OPENAI_API_KEY, OPENAI_MODEL, [OPENAI_BASE_URL]
  ollama             a local Ollama server             OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_NUM_CTX
  openai_compatible  any server that speaks            LLM_BASE_URL, LLM_MODEL, [LLM_API_KEY]
                     /chat/completions: LM Studio, vLLM, llama.cpp server, OpenRouter, Groq, ...

A provider is one function that takes a prompt string and returns the reply text, registered with
@provider(...). The pipeline parses JSON from the reply itself, so providers stay thin. To add one,
write the function, a no-network `check` that raises RuntimeError with a fix hint when it is
misconfigured, and decorate it.
"""
import re
import time
from urllib.parse import urlsplit
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import requests

from .. import config

LLMFn = Callable[[str], str]

_ALIASES = {"compatible": "openai_compatible", "custom": "openai_compatible", "lmstudio": "openai_compatible",
            "lm_studio": "openai_compatible", "vllm": "openai_compatible", "llamacpp": "openai_compatible"}


@dataclass(frozen=True)
class Provider:
    name: str
    call: LLMFn
    check: Callable[[], None]
    model: Callable[[], str]
    needs: str


_REGISTRY: Dict[str, Provider] = {}
_override: Dict[str, Optional[str]] = {"provider": None, "model": None}


def provider(name: str, check: Callable[[], None], model: Callable[[], str], needs: str):
    def deco(fn: LLMFn) -> LLMFn:
        _REGISTRY[name] = Provider(name, fn, check, model, needs)
        return fn
    return deco


def available_providers() -> list:
    return sorted(_REGISTRY)


def configure(provider: Optional[str] = None, model: Optional[str] = None) -> None:
    """Override LLM_PROVIDER / LLM_MODEL for this process (used by the CLI flags)."""
    if provider:
        _override["provider"] = provider
    if model:
        _override["model"] = model


def _normalize(name: str) -> str:
    n = (name or "").strip().lower().replace("-", "_")
    return _ALIASES.get(n, n)


def active() -> Provider:
    name = _normalize(_override["provider"] or config.LLM_PROVIDER or "openai")
    if name not in _REGISTRY:
        raise RuntimeError(f"Unknown LLM provider {name!r}. Available: {', '.join(available_providers())}.")
    return _REGISTRY[name]


def _model(default: str) -> str:
    return _override["model"] or config.LLM_MODEL or default


def describe() -> str:
    p = active()
    return f"{p.name} ({p.model()})"


def validate() -> None:
    """Fail fast, before the slow steps, if the selected provider can't work."""
    active().check()


def call_local_llm(prompt: str) -> str:
    """Send one prompt to the selected provider and return its text reply."""
    return active().call(prompt)


# ------------------------------------------------------------------------------ shared HTTP

def _retry_after(resp) -> Optional[float]:
    try:
        return min(30.0, float(resp.headers.get("retry-after", "")))
    except ValueError:
        return None


def _post_json(url: str, payload: dict, headers: Optional[dict] = None, timeout: float = 300.0,
               retries: int = 2, hint: str = "") -> dict:
    """POST JSON, retrying connection errors, 408/409/429 and 5xx. Never echoes request headers."""
    last: Exception = RuntimeError("no attempt made")
    for attempt in range(retries + 1):
        delay: Optional[float] = None
        try:
            resp = requests.post(url, json=payload, headers=headers or {}, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            last = RuntimeError(f"could not reach {url} ({e.__class__.__name__}). {hint}".strip())
        else:
            if resp.status_code < 400:
                try:
                    return resp.json()
                except ValueError:
                    raise RuntimeError(f"{url} returned non-JSON: {resp.text[:200]!r}") from None
            last = RuntimeError(f"{url} -> HTTP {resp.status_code}: {resp.text[:300]}")
            if resp.status_code not in (408, 409, 429) and resp.status_code < 500:
                raise last
            delay = _retry_after(resp)
        if attempt < retries:
            time.sleep(delay if delay is not None else 2.0 * (attempt + 1))
    raise last


def _strip_think(text: str) -> str:
    """Some servers inline <think>…</think> reasoning; drop it so JSON parsing isn't confused."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


# ------------------------------------------------------------------------------ openai

_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def _validate_base_url(url: str, name: str, sends_key: bool) -> None:
    """Reject malformed URLs, embedded credentials, and API keys sent over plain HTTP to remote hosts."""
    try:
        parsed = urlsplit(url)
        host, _ = parsed.hostname, parsed.port  # .port also validates the port number
    except ValueError:
        raise RuntimeError(f"{name} is not a valid URL: {url!r}") from None
    if parsed.scheme not in ("http", "https") or not host:
        raise RuntimeError(f"{name} must be an http(s) URL, got {url!r}.")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError(f"{name} must not contain credentials; put the key in the API key setting instead.")
    if sends_key and parsed.scheme == "http" and host.lower() not in _LOOPBACK:
        raise RuntimeError(f"{name} uses plain HTTP to a remote host, which would send your API key unencrypted. Use https://.")


def _check_openai() -> None:
    config.require_openai_key()
    if config.OPENAI_BASE_URL:
        _validate_base_url(config.OPENAI_BASE_URL, "OPENAI_BASE_URL", sends_key=True)


@provider("openai", _check_openai, lambda: _model(config.OPENAI_MODEL),
          "OPENAI_API_KEY (optional: OPENAI_MODEL, OPENAI_BASE_URL)")
def call_openai_llm(prompt: str) -> str:
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as e:
        raise RuntimeError("openai is required for LLM_PROVIDER=openai. Install it with:\n"
                           "    pip install -r requirements-local.txt") from e
    client = OpenAI(api_key=config.require_openai_key(), base_url=config.OPENAI_BASE_URL or None)
    response = client.chat.completions.create(
        model=_model(config.OPENAI_MODEL),
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


# ------------------------------------------------------------------------------ ollama

def _check_ollama() -> None:
    """Config + a quick reachability/model check, so a typo costs seconds, not a 30-minute run."""
    model = _model(config.OLLAMA_MODEL)
    try:
        resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3)
        resp.raise_for_status()
        names = {m.get("name", "") for m in resp.json().get("models", [])}
    except requests.ConnectionError:
        raise RuntimeError(f"Could not reach Ollama at {config.OLLAMA_BASE_URL}. Start it with `ollama serve`.") from None
    except Exception:
        return  # slow or busy server: don't block the run on a health check
    if model not in names and f"{model}:latest" not in names:
        raise RuntimeError(f"Ollama model {model!r} is not installed. Run `ollama pull {model}`, "
                           f"or pick one of: {', '.join(sorted(names)) or '(none installed)'}.")


@provider("ollama", _check_ollama, lambda: _model(config.OLLAMA_MODEL),
          "a running Ollama server (OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_NUM_CTX)")
def call_ollama_llm(prompt: str) -> str:
    data = _post_json(
        f"{config.OLLAMA_BASE_URL}/api/chat",
        {
            "model": _model(config.OLLAMA_MODEL),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",   # constrain output to valid JSON
            "think": False,     # skip reasoning traces on thinking models
            "options": {"temperature": 0.2, "num_ctx": config.OLLAMA_NUM_CTX},
        },
        timeout=config.OLLAMA_TIMEOUT_SECONDS,
        retries=0,  # a timeout here means the server is busy; the highlight loop retries
        hint="Start it with `ollama serve`.",
    )
    return data.get("message", {}).get("content", "") or ""


# ------------------------------------------------------------------------------ openai_compatible

def _check_compatible() -> None:
    if not config.LLM_BASE_URL:
        raise RuntimeError("LLM_PROVIDER=openai_compatible needs LLM_BASE_URL, e.g. http://localhost:1234/v1 "
                           "(LM Studio) or https://openrouter.ai/api/v1.")
    _validate_base_url(config.LLM_BASE_URL, "LLM_BASE_URL", sends_key=bool(config.LLM_API_KEY))
    if not _model(""):
        raise RuntimeError("LLM_PROVIDER=openai_compatible needs a model: set LLM_MODEL or pass --llm-model.")


@provider("openai_compatible", _check_compatible, lambda: _model(""),
          "LLM_BASE_URL and LLM_MODEL (optional: LLM_API_KEY)")
def call_openai_compatible_llm(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
    data = _post_json(
        f"{config.LLM_BASE_URL}/chat/completions",
        {"model": _model(""), "temperature": 0.2, "messages": [{"role": "user", "content": prompt}]},
        headers=headers,
        timeout=config.LLM_TIMEOUT_SECONDS,
        hint=f"Is the server running at {config.LLM_BASE_URL}?",
    )
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"unexpected response shape from {config.LLM_BASE_URL}: {str(data)[:200]}") from None
    return _strip_think(content if isinstance(content, str) else "")
