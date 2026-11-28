import json
import types

import pytest
import requests

from shorts_generator import config
from shorts_generator.local import llm


class Resp:
    def __init__(self, code, body, headers=None):
        self.status_code, self._body, self.headers = code, body, headers or {}
        self.text = json.dumps(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


@pytest.fixture(autouse=True)
def reset_llm_state(monkeypatch):
    llm._override.update(provider=None, model=None)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)  # no real backoff in tests
    yield
    llm._override.update(provider=None, model=None)


@pytest.fixture
def net(monkeypatch):
    """Replace the HTTP layer. `net.plan` lists status codes to return before succeeding."""
    state = types.SimpleNamespace(plan=[], calls=[], tags=["qwen3:30b-a3b", "llama3:latest"])

    def post(url, json=None, headers=None, timeout=None):
        if ":9/" in url or url.endswith(":9"):
            raise requests.ConnectionError("refused")
        state.calls.append((url, (headers or {}).get("Authorization"), json))
        code = state.plan.pop(0) if state.plan else 200
        if code != 200:
            return Resp(code, {"error": "boom " + "x" * 600}, {"retry-after": "1"} if code == 429 else None)
        if url.endswith("/chat/completions"):
            return Resp(200, {"choices": [{"message": {"content": "<think>hmm {no}</think>{\"ok\": true}"}}]})
        return Resp(200, {"message": {"content": "{\"ollama\": true}"}})

    def get(url, timeout=None, **kw):
        if ":9" in url:
            raise requests.ConnectionError("refused")
        return Resp(200, {"models": [{"name": n} for n in state.tags]})

    monkeypatch.setattr(llm.requests, "post", post)
    monkeypatch.setattr(llm.requests, "get", get)
    return state


def use_compatible(monkeypatch, base="https://api.example.test/v1", key="sk-test", model="m"):
    monkeypatch.setattr(config, "LLM_BASE_URL", base)
    monkeypatch.setattr(config, "LLM_API_KEY", key)
    monkeypatch.setattr(config, "LLM_MODEL", "")
    llm.configure(provider="openai_compatible", model=model)


# ------------------------------------------------------------------ openai_compatible

def test_compatible_sends_key_and_model_and_strips_think(net, monkeypatch):
    use_compatible(monkeypatch)
    assert llm.call_local_llm("hi") == '{"ok": true}'
    url, auth, body = net.calls[-1]
    assert url == "https://api.example.test/v1/chat/completions"
    assert auth == "Bearer sk-test" and body["model"] == "m"


def test_aliases_resolve_to_openai_compatible(monkeypatch):
    use_compatible(monkeypatch)
    for alias in ("lmstudio", "vllm", "custom", "openai-compatible"):
        llm.configure(provider=alias)
        assert llm.active().name == "openai_compatible"


def test_transient_errors_are_retried(net, monkeypatch):
    use_compatible(monkeypatch)
    net.plan = [503, 429]
    assert llm.call_local_llm("hi") == '{"ok": true}'
    assert len(net.calls) == 3


def test_client_errors_are_not_retried_and_never_echo_the_key(net, monkeypatch):
    use_compatible(monkeypatch)
    net.plan = [400]
    with pytest.raises(RuntimeError) as err:
        llm.call_local_llm("hi")
    assert len(net.calls) == 1
    assert "sk-test" not in str(err.value) and len(str(err.value)) < 450


def test_gives_up_after_three_attempts(net, monkeypatch):
    use_compatible(monkeypatch)
    net.plan = [503] * 9
    with pytest.raises(RuntimeError, match="HTTP 503"):
        llm.call_local_llm("hi")
    assert len(net.calls) == 3


def test_unreachable_server_message_is_actionable(net, monkeypatch):
    use_compatible(monkeypatch, base="http://127.0.0.1:9", key="")
    with pytest.raises(RuntimeError, match="Is the server running"):
        llm.call_local_llm("hi")


def test_missing_base_url_and_model_are_reported(monkeypatch):
    use_compatible(monkeypatch, base="", model=None)
    with pytest.raises(RuntimeError, match="LLM_BASE_URL"):
        llm.validate()
    monkeypatch.setattr(config, "LLM_BASE_URL", "https://api.example.test/v1")
    with pytest.raises(RuntimeError, match="needs a model"):
        llm.validate()


# ------------------------------------------------------------------ base URL safety

@pytest.mark.parametrize("url,key,ok", [
    ("https://api.example.test/v1", "k", True),
    ("http://localhost:1234/v1", "k", True),          # loopback + key is fine
    ("http://127.0.0.1:1234/v1", "k", True),
    ("http://10.0.0.5:1234/v1", "", True),            # LAN without a key is fine
    ("http://10.0.0.5:1234/v1", "k", False),          # key over plain http to a remote host
    ("https://user:pw@api.example.test/v1", "k", False),
    ("ftp://api.example.test/v1", "", False),
    ("http://", "", False),
])
def test_base_url_rules(monkeypatch, url, key, ok):
    use_compatible(monkeypatch, base=url, key=key)
    if ok:
        llm.validate()
    else:
        with pytest.raises(RuntimeError):
            llm.validate()


def test_openai_provider_applies_the_same_key_rules(monkeypatch):
    llm.configure(provider="openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "your_openai_key_here")
    with pytest.raises(RuntimeError, match="placeholder"):
        llm.validate()
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-" + "a" * 30)
    llm.validate()
    monkeypatch.setattr(config, "OPENAI_BASE_URL", "http://evil.example.test/v1")
    with pytest.raises(RuntimeError, match="plain HTTP"):
        llm.validate()


# ------------------------------------------------------------------ ollama

def use_ollama(monkeypatch, model="qwen3:30b-a3b"):
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", "https://ollama.example.test")
    monkeypatch.setattr(config, "LLM_MODEL", "")
    llm.configure(provider="ollama", model=model)


def test_ollama_validates_the_model_is_installed(net, monkeypatch):
    use_ollama(monkeypatch)
    llm.validate()
    llm.configure(model="llama3")  # matches "llama3:latest"
    llm.validate()
    llm.configure(model="typo-model")
    with pytest.raises(RuntimeError, match="ollama pull typo-model"):
        llm.validate()


def test_ollama_down_says_how_to_start_it(net, monkeypatch):
    use_ollama(monkeypatch)
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", "http://127.0.0.1:9")
    with pytest.raises(RuntimeError, match="ollama serve"):
        llm.validate()


def test_ollama_call_sets_context_json_mode_and_no_thinking(net, monkeypatch):
    use_ollama(monkeypatch)
    monkeypatch.setattr(config, "OLLAMA_NUM_CTX", 12345)
    assert llm.call_local_llm("hi") == '{"ollama": true}'
    body = net.calls[-1][2]
    assert body["options"]["num_ctx"] == 12345 and body["format"] == "json" and body["think"] is False


# ------------------------------------------------------------------ selection

def test_unknown_provider_lists_the_available_ones():
    llm.configure(provider="nope")
    with pytest.raises(RuntimeError, match="ollama, openai, openai_compatible"):
        llm.validate()


def test_model_precedence_cli_over_env_over_provider_default(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_MODEL", "default-model")
    llm.configure(provider="ollama")
    monkeypatch.setattr(config, "LLM_MODEL", "")
    assert llm.describe() == "ollama (default-model)"
    monkeypatch.setattr(config, "LLM_MODEL", "from-env")
    assert llm.describe() == "ollama (from-env)"
    llm.configure(model="from-cli")
    assert llm.describe() == "ollama (from-cli)"


def test_strip_think_removes_reasoning_blocks():
    assert llm._strip_think("<think>a\nb</think>  {\"x\":1}") == '{"x":1}'
