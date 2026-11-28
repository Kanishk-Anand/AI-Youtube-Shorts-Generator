#!/usr/bin/env bash
# AI YouTube Shorts Generator: macOS / Linux installer.
#
# Safe to re-run. Installs into this folder (.venv) and needs no admin rights, except where your
# package manager asks for them (ffmpeg). Flags:
#   --no-link   don't create the `shorts` command in ~/.local/bin
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PATH_BEFORE_INSTALL="$PATH"   # to tell the user honestly whether ~/.local/bin is already on their PATH
LINK=1
for arg in "$@"; do
  case "$arg" in
    --no-link) LINK=0 ;;
    -h|--help) sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mok\033[0m  %s\n' "$*"; }
warn() { printf '  \033[33m!!\033[0m  %s\n' "$*"; }
die()  { printf '\n\033[31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

PY_VERSION="3.12"
OS="$(uname -s)"
case "$OS" in
  Darwin|Linux) ;;
  *) die "Unsupported system: $OS. On Windows, double-click Install-Windows.bat instead." ;;
esac

# ---------------------------------------------------------------- 1. uv
say "1/5  Python tooling (uv)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "  Installing uv with Homebrew..."
    brew install uv
  else
    echo "  Installing uv with its official installer (https://astral.sh/uv)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  command -v uv >/dev/null 2>&1 || die "uv was installed but is not on PATH yet. Open a new terminal and run this installer again."
fi
ok "uv $(uv --version | awk '{print $2}')"

# ---------------------------------------------------------------- 2. Python environment
say "2/5  Python $PY_VERSION environment (.venv)"
VENV_PY="$ROOT/.venv/bin/python"
if [ -x "$VENV_PY" ]; then
  found="$("$VENV_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo 0.0)"
  case "$found" in
    3.10|3.11|3.12|3.13) ok "reusing the existing .venv (Python $found)" ;;
    *) warn "the existing .venv uses Python $found, which this tool does not support; recreating it"
       rm -rf "$ROOT/.venv" ;;
  esac
fi
if [ ! -x "$VENV_PY" ]; then
  uv venv --python "$PY_VERSION" "$ROOT/.venv" \
    || die "could not create a Python $PY_VERSION environment. Check your internet connection and try again."
  ok "created .venv with Python $("$VENV_PY" -c 'import platform; print(platform.python_version())')"
fi

# ---------------------------------------------------------------- 3. dependencies
say "3/5  Python packages"
# Some packages are large (OpenCV is ~45 MB), so allow slow connections and retry once.
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-180}"
if ! uv pip install --python "$VENV_PY" -r "$ROOT/requirements-local.txt"; then
  warn "the download failed; retrying once..."
  uv pip install --python "$VENV_PY" -r "$ROOT/requirements-local.txt" \
    || die "installing the Python packages failed. Check your internet connection and run this installer again."
fi
ok "packages installed"

# ---------------------------------------------------------------- 4. ffmpeg
say "4/5  ffmpeg"
have_ffmpeg() { command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; }
if have_ffmpeg; then
  ok "ffmpeg already installed"
else
  if [ "$OS" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    echo "  Installing ffmpeg with Homebrew (this can take a few minutes)..."
    brew install ffmpeg || warn "brew could not install ffmpeg"
  fi
  if have_ffmpeg; then
    ok "ffmpeg installed"
  elif [ "$OS" = "Darwin" ]; then
    warn "ffmpeg is still missing. Install Homebrew (https://brew.sh), then run:  brew install ffmpeg"
  else
    warn "ffmpeg is still missing. Install it with your package manager, e.g.:  sudo apt install ffmpeg"
  fi
fi

# ---------------------------------------------------------------- 5. config, command, check
say "5/5  Settings and the 'shorts' command"
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  ok "created .env (edit it to choose your LLM and settings)"
else
  ok ".env already exists, left unchanged"
fi
chmod +x "$ROOT/shorts"
if [ "$LINK" = 1 ]; then
  mkdir -p "$HOME/.local/bin"
  ln -sf "$ROOT/shorts" "$HOME/.local/bin/shorts"
  ok "linked  ~/.local/bin/shorts  ->  $ROOT/shorts"
  case ":$PATH_BEFORE_INSTALL:" in
    *":$HOME/.local/bin:"*) ;;
    *) warn "add ~/.local/bin to your PATH so 'shorts' works anywhere:  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc" ;;
  esac
fi

say "Checking your setup"
status=0
"$VENV_PY" "$ROOT/main.py" --doctor || status=$?

echo
if [ "$status" = 0 ]; then
  printf '\033[32mInstalled.\033[0m Try it:\n'
else
  printf '\033[33mInstalled, but the checks above found problems to fix.\033[0m Then try:\n'
fi
cat <<'MSG'

    shorts "https://www.youtube.com/watch?v=VIDEO_ID" --mode local
    shorts path/to/video.mp4 --critique

  (From this folder you can also run  ./shorts ...)

  For fully offline use, install Ollama (https://ollama.com/download), then:
    ollama pull qwen3:30b-a3b
  and set  LLM_PROVIDER=ollama  and  OLLAMA_MODEL=qwen3:30b-a3b  in .env.
MSG
exit "$status"
