# AI YouTube Shorts Generator

[![Powered by MuAPI](https://img.shields.io/badge/Powered%20by-MuAPI-6366f1?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMSAxNHYtNGgtMnYtMmg0djZoLTJ6bTAtOFY2aDJ2MmgtMnoiLz48L3N2Zz4=)](https://muapi.ai?utm_source=github&utm_medium=badge&utm_campaign=ai-youtube-shorts-generator)


**The open-source alternative to Opus Clip, Vidyo.ai, Klap, SubMagic, 2short.ai, and other AI clipping tools.** Drop in any long-form YouTube video and get back ranked, viral-ready 9:16 shorts — for free, with no per-clip credits, no watermarks, and full control over the highlight algorithm.

Built for creators, agencies, and developers who don't want to pay $20–$300/month or be capped on minutes processed. Uses GPT-class LLM highlight detection and Whisper transcription to extract the most viral-worthy moments and auto-crop them vertically for TikTok, Reels, and Shorts.

<p align="center"><a href="https://www.youtube.com/watch?v=16f6fyhmX1c"><img src="https://i.ytimg.com/vi/16f6fyhmX1c/maxresdefault.jpg" width="720"></a></p>
<p align="center"><a href="https://www.youtube.com/watch?v=16f6fyhmX1c"><b>▶  Watch: Suno API Guide: Best AI Music API (Full Songs From Code) </b></a></p>

> **Building your own Opus Clip–style SaaS?** Skip the infra and ship on the same APIs that power this repo:
> - [AI Clipping API](https://muapi.ai/playground/ai-clipping?utm_source=github&utm_medium=readme&utm_campaign=ai-youtube-shorts-generator) — end-to-end clip selection + render
> - [Auto-Crop API](https://muapi.ai/playground/autocrop?utm_source=github&utm_medium=readme&utm_campaign=ai-youtube-shorts-generator) — vertical reframing only

![longshorts](https://github.com/user-attachments/assets/3f5d1abf-bf3b-475f-8abf-5e253003453a)

<p align="center">
  <a href="https://github.com/Anil-matcha/awesome-generative-ai-apps">
    <img src="https://img.shields.io/badge/Part%20of-Awesome%20Generative%20AI%20Apps-FFD700?style=for-the-badge&logo=github&logoColor=black" alt="Awesome Generative AI Apps">
  </a>
</p>

> 🎨 **[Explore 50+ more open-source AI apps →](https://github.com/Anil-matcha/awesome-generative-ai-apps)**

## Why Use This Instead of Opus Clip / Vidyo.ai / Klap?

| | This repo | Opus Clip / Vidyo.ai / Klap / SubMagic |
|---|---|---|
| **Price** | Free + open source (pay only for API usage) | $20–$300/month subscriptions |
| **Per-clip credits** | None — process unlimited videos | Monthly minute caps, overage fees |
| **Watermarks** | Never | On free tiers |
| **Highlight algorithm** | Fully editable virality framework | Black box |
| **Output format** | Any aspect ratio, any resolution | Locked presets |
| **Batch processing** | `xargs` an entire URL list | Manual upload one-by-one |
| **JSON / API output** | Built-in (`--output-json`) | Limited or paid tier only |
| **Self-hostable** | Yes — runs on your machine or server | SaaS only, your videos sit on their servers |
| **White-label / embeddable** | Yes — MIT licensed, import as Python lib | No |

## Features

- **🎬 YouTube In, Vertical Out**: Hand it any YouTube URL — get back N viral-ready 9:16 mp4s
- **🔀 Two Modes — API (fast) or Local (offline)**: Default `--mode api` uses MuAPI for download/transcription/cropping; `--mode local` runs on your machine with `yt-dlp`, `faster-whisper`, and `ffmpeg`/`opencv`, and works fully offline with a local Ollama model
- **🤖 Virality-Aware Highlight Selection**: Clips ranked on hooks, emotional peaks, opinion bombs, revelation moments, conflict, quotable lines, story peaks, and practical value — not just generic "interesting"
- **📈 Score + Hook + Reason for Every Clip**: Each highlight comes with a viral score, an opening hook line, and a one-sentence explanation of why it works
- **🎤 Whisper Transcription, Your Choice**: Cloud (`/openai-whisper` via MuAPI) or local (`faster-whisper`, CPU or CUDA) — same downstream output shape
- **🔌 Pluggable LLM (local mode)**: Use Ollama, OpenAI, or any OpenAI-compatible server (LM Studio, vLLM, llama.cpp, OpenRouter, Groq) with `--llm`; the setup is checked before any slow step starts
- **🧩 Long-Video Aware**: Videos over 30 minutes are split into 15-minute overlapping chunks, then the best candidates are re-ranked against each other in one extra call so scores are comparable across the whole video
- **✂️ Clean Clip Boundaries**: Clips are kept between 20 and 180 seconds and snapped to transcript segment edges, so they don't start or end mid-sentence
- **♻️ Smart Dedupe**: Overlapping highlights are collapsed by score so you never get two near-duplicate clips
- **🎯 Smooth Vertical Crop**: API mode uses MuAPI's auto-crop; local mode smooths the face-tracking path (sparse detection, median filter, dead zone) so the frame doesn't shake, and encodes straight to H.264
- **🧱 Layouts**: `face`, `center`, or `split` (the source on top, a webcam box or any video you choose below) for streams and gameplay
- **📱 Any Aspect Ratio**: 9:16 for TikTok/Reels/Shorts, 1:1 for square, anything else by flag
- **🧰 CLI + Python Library**: Use it from the shell or import `generate_shorts(...)` into your own pipeline
- **📦 JSON Output**: `--output-json` dumps the full result (transcript + every candidate highlight + final clip URLs/paths) for downstream automation
- **🔎 Critique Mode**: `--critique` reviews any existing video or short and tells you what works, what doesn't, and what to change
- **🖥️ macOS and Windows**: `--doctor` checks your setup and prints the exact fix for your OS

## Quick Start (No Setup)

Don't want to self-host? The [AI Clipping API](https://muapi.ai/playground/ai-clipping?utm_source=github&utm_medium=readme&utm_campaign=ai-youtube-shorts-generator) gives you the same Opus Clip–style pipeline as a single HTTP call — no Python, no dependencies, pay-per-clip instead of monthly subscriptions.

---

## Installation (Self-Hosted)

### Easy install (macOS and Windows)

Download the project (**Code** > **Download ZIP**, then unzip it, or `git clone`), then:

| | Do this |
|---|---|
| **macOS** | Double-click **`Install-Mac.command`**. The first time, right-click it and choose **Open**, because macOS blocks scripts downloaded from the internet. |
| **Windows** | Double-click **`Install-Windows.bat`**. If Windows says it protected your PC, click **More info**, then **Run anyway**. |

Prefer a terminal? `bash installers/install.sh` (macOS/Linux) or `powershell -ExecutionPolicy Bypass -File installers\install.ps1` (Windows).

The installer needs no admin rights and is safe to re-run. It:

1. installs [`uv`](https://docs.astral.sh/uv/) (a Python tool manager) if you don't have it;
2. downloads Python 3.12 and creates a private environment in the project folder (`.venv`), so your system Python is never touched;
3. installs the packages (about 400 MB on disk, so allow a few minutes);
4. installs ffmpeg with Homebrew (macOS) or winget (Windows) if it's missing. Without Homebrew it tells you the command to run;
5. creates `.env` from the example (an existing `.env` is never overwritten) and runs `--doctor` to confirm everything works.

Then run the tool with the launcher in the project folder: `./shorts ...` on macOS, `.\shorts.cmd ...` on Windows. On macOS the installer also links `shorts` into `~/.local/bin`, so it works from any folder. To uninstall, delete the project folder (and `~/.local/bin/shorts` on macOS).

For manual setup, or to understand each step, follow the steps below.

### Install as a command (any OS)

Already have Python 3.10 to 3.13 and ffmpeg? Install the `shorts` command from a checkout of this repository:

```bash
uv tool install ".[local]"     # recommended: an isolated environment, and `shorts` goes on your PATH
pip install ".[local]"         # or: into the virtual environment you have active
```

`.[local]` includes everything for `--mode local` and `--critique`; plain `.` installs only what API mode needs. If your terminal says `shorts: command not found` after `uv tool install`, run `uv tool update-shell` and open a new terminal. Then check the setup with `shorts --doctor`.

An installed command keeps its settings in your user folder, so it works from any folder: see [Settings](#settings).

### Manual install

### Prerequisites

- Python 3.10 to 3.13 (3.12 recommended; newer versions often lack prebuilt wheels for `av`, `ctranslate2` and OpenCV)
- For **API mode (default)**: a MuAPI key — powers download, transcription, highlight ranking, and clipping in a single dependency
- For **Local mode** (`--mode local`): `ffmpeg` on your PATH and either an `OPENAI_API_KEY` or a running Ollama server (`ollama serve`)

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator.git
   cd AI-Youtube-Shorts-Generator
   ```

2. **Install Python 3.12 and ffmpeg** (ffmpeg is only needed for `--mode local` and `--critique`):

   | | Command |
   |---|---|
   | macOS (Homebrew) | `brew install python@3.12 ffmpeg` |
   | Windows (PowerShell) | `winget install Python.Python.3.12 Gyan.FFmpeg`, then open a **new** terminal |

3. **Create and activate a virtual environment:**

   macOS / Linux:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
   Windows (PowerShell):
   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   If PowerShell refuses to run the script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. In `cmd.exe` use `.venv\Scripts\activate.bat`.

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   # Only if you plan to use --mode local or --critique:
   pip install -r requirements-local.txt
   ```

5. **Set up environment variables:**

   Create a `.env` file in the project root:
   ```bash
   # API mode (default)
   MUAPI_API_KEY=your_muapi_key_here

   # Local mode (--mode local)
   LLM_PROVIDER=openai         # openai or ollama
   OPENAI_API_KEY=your_openai_key_here
   OPENAI_MODEL=gpt-4o-mini          # optional, default gpt-4o-mini
   OLLAMA_BASE_URL=http://localhost:11434   # optional
   OLLAMA_MODEL=qwen3.8:27b           # optional, any model from `ollama list`
   OLLAMA_NUM_CTX=16384               # optional, context window (default 16384)
   LOCAL_WHISPER_MODEL=base          # tiny / base / small / medium / large-v3
   LOCAL_WHISPER_DEVICE=auto         # auto / cpu / cuda
   LOCAL_OUTPUT_DIR=output           # where local mp4s land
   ```

   The `.env` file works the same on macOS and Windows and is the easiest place for settings. On Windows write paths with forward slashes (`LOCAL_BOTTOM_VIDEO=C:/Videos/filler.mp4`) or without quotes; backslashes inside quotes are treated as escapes.

6. **Check your setup:**
   ```bash
   python main.py --doctor
   ```
   It checks Python, ffmpeg, the dependencies, OpenCV and your LLM provider, and prints the exact command to fix anything missing for your OS.

> **Command syntax.** The examples use macOS/Linux shell syntax. `\` continues a long command onto the next line there; in PowerShell use a backtick (`` ` ``) or put the command on one line, and in `cmd.exe` use `^`. To set an option for a single run, put it in `.env`, or: macOS/Linux `LLM_PROVIDER=ollama python main.py ...`, PowerShell `$env:LLM_PROVIDER="ollama"; python main.py ...`, cmd.exe `set LLM_PROVIDER=ollama && python main.py ...`.

### Settings

Settings are plain `KEY=value` lines (all of them are listed in `.env.example`). They are read from these places, **highest priority first**:

1. real environment variables
2. a `.env` file in the current folder
3. a `.env` file in the project folder (only when running from a source checkout)
4. a `.env` file in your **user config folder**

| OS | User config folder |
|---|---|
| macOS | `~/Library/Application Support/AI-Shorts` |
| Windows | `%APPDATA%\AI-Shorts` |
| Linux | `~/.config/ai-shorts` (or `$XDG_CONFIG_HOME/ai-shorts`) |

The user folder is the right home for settings when you installed the `shorts` command: it works from any folder and survives upgrades.

```bash
shorts --init-config    # creates the file there from the template (readable only by you)
shorts --config         # shows every place settings are looked up, and which files exist
```

A value found earlier in the list is never overridden by a later one. Set `SHORTS_CONFIG_DIR` to use a different folder.

## Usage

### Quick start

```bash
shorts "https://www.youtube.com/watch?v=VIDEO_ID" --mode local    # a YouTube link
shorts path/to/video.mp4 --mode local --num-clips 5                # a video you already have
shorts short.mp4 --critique                                        # review an existing short
shorts --doctor                                                    # check your setup
```

`shorts` is the installed command. From a source checkout the same thing runs as `./shorts` (after the easy installer), `python main.py ...`, or `python -m shorts_generator ...`; the examples below use `python main.py`, and all of these behave identically.

Progress prints as it runs. Press **Ctrl+C once** to cancel cleanly: the download or render stops, partly written clips are deleted, and the command exits with code 130. Press it twice to quit immediately.

### Single video (API mode — default)

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Single video (Local mode — fully offline with Ollama)

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mode local
```

Local mode writes the rendered shorts to `./output/short_01.mp4`, `short_02.mp4`, … (override with `LOCAL_OUTPUT_DIR`).

### Security notes

- Replace the example API key values in `.env.example` before running a mode that uses them. The app rejects empty, placeholder, and short keys before it starts downloading or processing a video; OpenAI keys are also checked for their `sk-` prefix.
- Remote video URLs must use HTTPS and an exact YouTube or `youtu.be` hostname. Local mode also accepts a local path or `file://` URL for trusted, single-user use.
- If you expose this library through a web service, validate user input at the service boundary: accept only approved YouTube URLs and do not pass user-supplied paths or `file://` URLs to local mode. The library intentionally supports local files for CLI use.
- `LLM_BASE_URL` and `OPENAI_BASE_URL` must be http(s) URLs without embedded credentials, and an API key is never sent over plain HTTP to a non-local host.
- All transcript text is passed to the LLM as quoted, untrusted data (highlight ranking, reranking and `--critique`); model output is stripped of control characters before it is printed.
- `MUAPI_BASE_URL` must use HTTPS and the host `api.muapi.ai`. Other hosts are rejected because requests include the configured `MUAPI_API_KEY`.

### With options

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" \
    --mode api \
    --num-clips 5 \
    --aspect-ratio 9:16 \
    --output-json result.json
```

### Local file or path

In `--mode local`, you can pass a `file://` URL or a direct filesystem path and skip YouTube entirely:

```bash
python main.py "/Users/you/Videos/input.mp4" --mode local
python main.py "file:///Users/you/Videos/input.mp4" --mode local
```

The Python API works the same way:

```python
from shorts_generator import generate_shorts

result = generate_shorts(
    "/Users/you/Videos/input.mp4",
    num_clips=5,
    aspect_ratio="9:16",
    mode="local",
)
for short in result["shorts"]:
    print(short["score"], short["title"], short["clip_url"])
```

### Progress and cancel from Python

Every run is a job that reports progress and can be cancelled. This is what a UI or a service wants:

```python
from shorts_generator import start_job

job = start_job("https://www.youtube.com/watch?v=VIDEO_ID", mode="local", num_clips=3)
for event in job.events():        # yields progress until the job finishes
    print(event.stage, event.status, event.message, event.fraction)
    # when the user clicks Cancel, from any thread:  job.cancel()
result = job.result()             # the same dict generate_shorts() returns
```

Or stay synchronous: `generate_shorts(url, mode="local", on_event=callback, cancel=threading.Event())`.

| Event field | Meaning |
|---|---|
| `stage` | `pipeline`, `download`, `transcribe`, `highlights`, `rerank`, `render` (or `api` while waiting on MuAPI) |
| `status` | `start`, `progress`, `done`, `warn`, `error`, `cancelled`, `finished` |
| `message`, `data` | A human-readable note, and extras such as the clip number or output path |
| `current`, `total`, `fraction` | How far along the stage is (`fraction` is 0 to 1, or `None` if unknown) |

Cancelling is cooperative: downloads and ffmpeg runs stop within a fraction of a second, and an LLM call that is already in flight finishes first. A cancelled run raises `shorts_generator.CancelledError` (a `BaseException`, like asyncio's, so a stray `except Exception` can't swallow it) and removes any half-written clip. A job's `state` is `running`, `done`, `failed` or `cancelled`.

Local transcription is cached as an `.srt` file in `LOCAL_OUTPUT_DIR` named after the
video plus a short hash of its full path (so same-named files never share a transcript). If the cache already exists and is newer than the source
file, the app reuses it instead of running Whisper again.

Local downloads are also cached in `LOCAL_OUTPUT_DIR` as
`source_<youtube_id>.mp4` when the input is a YouTube URL. If that file already
exists, the app skips `yt-dlp` and reuses the cached video.

### Batch processing

Create a `urls.txt` file with one URL per line, then:

```bash
xargs -a urls.txt -I{} python main.py "{}"
```

### CLI flags

| Flag | Default | Notes |
|------|---------|-------|
| `--mode` | `api` | `api` (MuAPI, fast, no setup) or `local` (remote URL, `file://`, or local path + faster-whisper + LLM provider + ffmpeg) |
| `--num-clips` | `3` | How many shorts to render |
| `--aspect-ratio` | `9:16` | Any ratio; `9:16` for TikTok/Reels, `1:1` for square |
| `--format` | `720` | Source download resolution: `360` / `480` / `720` / `1080` |
| `--language` | auto | Force Whisper language code (e.g. `en`) |
| `--output-json` | — | Dump the full result (transcript + all candidates) to a file |
| `--llm` | `LLM_PROVIDER` or `openai` | Local mode / `--critique`: `ollama`, `openai`, or `openai_compatible` |
| `--llm-model` | provider default | Model name for the chosen provider (overrides `LLM_MODEL`) |
| `--layout` | `face` | Local mode framing: `face`, `center`, or `split` |
| `--facecam X,Y,W,H` | — | Split layout: webcam box in the source video, in pixels |
| `--bottom-video FILE` | — | Split layout: any video for the bottom panel (overrides `--facecam`) |
| `--split-ratio` | `0.6` | Split layout: share of the height used by the top panel (0.3–0.8) |
| `--critique` | off | Review an existing video or short instead of generating clips |
| `--no-llm` | off | With `--critique`: measured checks only, no LLM review |
| `--doctor` | off | Check this machine (Python, ffmpeg, dependencies, OpenCV, LLM) and print fixes |
| `--config` | off | Show every place settings are read from, and which of those files exist |
| `--init-config` | off | Create the settings file in your user config folder from the template |
| `--version` | — | Print the version |

### API mode vs Local mode

| Step | API mode (`--mode api`) | Local mode (`--mode local`) |
|---|---|---|
| Download | MuAPI `/youtube-download` | `yt-dlp` for remote URLs, direct file path for local inputs |
| Transcription | MuAPI `/openai-whisper` | `faster-whisper` (CPU or CUDA) |
| Highlight LLM | MuAPI `gpt-5-mini` | `LLM_PROVIDER=openai` uses OpenAI (`gpt-4o-mini` by default), `LLM_PROVIDER=ollama` uses a local Ollama model (`qwen3.8:27b` by default) |
| Vertical crop | MuAPI `/autocrop` | `ffmpeg` + OpenCV face tracking |
| Output | hosted URLs | local mp4 paths |
| Required keys | `MUAPI_API_KEY` | `OPENAI_API_KEY` or a running Ollama server (+ `ffmpeg` on PATH) |

#### Choosing the LLM (local mode and `--critique`)

The LLM that ranks highlights and writes the critique is pluggable. Pick it with `LLM_PROVIDER` or `--llm`, and its model with `LLM_MODEL` or `--llm-model`:

| Provider | Talks to | Needs |
|---|---|---|
| `openai` | OpenAI (official SDK) | `OPENAI_API_KEY`, optional `OPENAI_MODEL`, `OPENAI_BASE_URL` |
| `ollama` | a local Ollama server | `OLLAMA_MODEL` (checked against `ollama list` before the run), `OLLAMA_NUM_CTX` |
| `openai_compatible` | any server with `/chat/completions`: LM Studio, vLLM, llama.cpp, OpenRouter, Groq, ... | `LLM_BASE_URL`, `LLM_MODEL`, optional `LLM_API_KEY` |

```bash
python main.py video.mp4 --mode local --llm ollama --llm-model qwen3:30b-a3b
python main.py video.mp4 --mode local --llm openai_compatible --llm-model llama-3.3-70b   # LLM_BASE_URL in .env
```

The provider is checked before the download and transcription start, so a typo or missing key fails in seconds. To add a provider, write one function in `shorts_generator/local/llm.py` that takes a prompt and returns text, and register it with `@provider(...)`.

#### Local-mode layouts

`--layout face|center|split` (or `LOCAL_CROP_MODE`) controls how clips are framed in `--mode local`:

- `face` (default): follows the speaker's face with a smoothed crop. Best for podcasts and talking heads.
- `center`: fixed centre crop, no tracking.
- `split`: two panels stacked vertically. The source video is on top and the bottom panel is either a box cut out of the source (the streamer's webcam) or any video you supply.

```bash
# Streamer webcam box (x,y,w,h in source pixels) under the gameplay
python main.py video.mp4 --mode local --layout split --facecam 0,305,260,165

# Any other video below (looped or trimmed to the clip length; its audio is ignored)
python main.py video.mp4 --mode local --bottom-video ~/Videos/filler.mp4 --split-ratio 0.55
```

`--bottom-video` or `--facecam` on their own imply `--layout split`. The audio always comes from the source video.


### Critique an existing video or short

Give it a video you already made (a file or a YouTube URL) and it tells you what is working, what isn't, and what to change:

```bash
python main.py path/to/short.mp4 --critique
python main.py short.mp4 --critique --llm ollama --llm-model qwen3:30b-a3b
python main.py short.mp4 --critique --no-llm          # measured checks only
```

It combines two layers:

- **Measured checks** (no LLM, fast): length, format and resolution, how soon the first words start, dead air, loudness and clipping, speech pace, filler words, visual variety, face size and position, and trailing silence. Each is marked ✓, `!` or ✗ with a one-line fix.
- **An LLM review** of the transcript, grounded in those numbers: a hook verdict with a suggested rewrite, what works, what doesn't, and up to six changes ranked by impact, with timestamps. Anything it can't judge from the data is listed under "not assessed".

```
MEASURED CHECKS  (rules of thumb, not a prediction)
  ✓ Length: 34s
  ! Format: 404x720
  ✓ First words begin at: 0.0s
  ! Face on screen: in 80% of samples, median height 12% of frame
CHANGE THESE FIRST
  1. [high] @30s End on the 'she gave me up' line
       why: last 4s trail off
```

What to keep in mind:

- The thresholds are rules of thumb, **not a trained model, and there is no virality score**. Nothing here can predict views.
- The LLM sees only the measured numbers and the transcript. It cannot see the picture, hear the audio, or read on-screen text, so captions, music and picture quality are not assessed.
- Only the first 120 seconds are analysed. If the LLM is unavailable, you still get the measured checks.

## How It Works

1. **Download**: API mode fetches the video via MuAPI. Local mode uses `yt-dlp` (HTTPS YouTube URLs only) or reads a file path you give it
2. **Transcribe**: MuAPI `/openai-whisper`, or local `faster-whisper` (cached as an `.srt` file), produces a timestamped transcript
3. **Detect content type**: An LLM classifies the video (podcast, interview, tutorial, vlog, etc.) and density, so the prompt can be tuned per content style
4. **Long-video chunking**: Videos > 30 min are split into 15-min overlapping chunks, with timestamps re-based per chunk. A chunk that fails is skipped instead of aborting the run
5. **Highlight ranking**: An LLM scans the transcript through a virality framework — hook moments, emotional peaks, opinion bombs, revelations, conflict, quotables, story peaks, practical value — and returns scored candidates with a title, hook line and reason. The transcript is passed as quoted, untrusted data. Clips must be 20–180 seconds long and are snapped to transcript segment boundaries
6. **Dedupe**: Overlapping candidates are collapsed by score (>50% overlap → keep the higher score)
7. **Cross-chunk rerank** (long videos only): one extra call re-scores the best candidates against each other, because scores from separate chunks aren't comparable
8. **Top-N selection**: The top `--num-clips` candidates are selected
9. **Frame and render**: API mode uses MuAPI's `/autocrop`. Local mode renders with the chosen layout (`face`, `center` or `split`) through ffmpeg and OpenCV

**Output**: a list of mp4 URLs plus, for each clip, its title, viral score, hook sentence, and a one-line reason explaining why it should perform.

## Output

Console output looks like:

```
========================================================================
Highlights:    7 candidates → kept top 3
========================================================================

#1  score=92  124.3s → 187.6s
     title:  The one mistake that cost me $50K
     hook:   "Nobody talks about this, but it killed my first startup..."
     clip:   https://.../short_1.mp4

#2  score=88  ...
```

`--output-json result.json` produces:

```json
{
  "source_video_url": "...",
  "transcript": { "duration": 1873.4, "segments": [...] },
  "highlights": [ {...}, {...}, ... ],
  "shorts": [
    {
      "title": "...",
      "start_time": 124.3,
      "end_time": 187.6,
      "score": 92,
      "hook_sentence": "...",
      "virality_reason": "...",
      "clip_url": "https://.../short_1.mp4"
    }
  ]
}
```

## Configuration

### Highlight selection criteria
Edit `shorts_generator/highlights.py`:
- **Virality framework**: `VIRALITY_CRITERIA` — the ranked list of signals the LLM optimizes for
- **System prompt**: `HIGHLIGHT_SYSTEM_PROMPT` — duration sweet spot, hook rules, JSON schema
- **Chunk size**: `CHUNK_SIZE_SECONDS` (default 900) — chunk length for long videos
- **Long-video threshold**: `LONG_VIDEO_THRESHOLD` (default 1800) — videos longer than this are chunked
- **Chunk overlap**: `CHUNK_OVERLAP_SECONDS` (default 60) — overlap between chunks so cross-boundary clips aren't missed
- **Clip length**: `MIN_CLIP_SECONDS` (default 20) and `MAX_CLIP_SECONDS` (default 180) — clips outside this range are rejected and the model is asked again
- **Rerank pool**: `RERANK_MIN_POOL` / `RERANK_MAX_POOL` (default 10 / 20) — how many candidates the cross-chunk rerank sees

### Polling / timeout
Edit `shorts_generator/config.py` (or set env vars):
- `MUAPI_POLL_INTERVAL` (default 5s) — seconds between job-status polls
- `MUAPI_POLL_TIMEOUT` (default 600s) — give up after this long

### Whisper transcription
In API mode, audio is transcribed by MuAPI's `/openai-whisper` endpoint (server-side `whisper-1`). In local mode it runs `faster-whisper` on your machine: choose the size with `LOCAL_WHISPER_MODEL` (`tiny` … `large-v3`, default `base`) and the device with `LOCAL_WHISPER_DEVICE`. The model downloads once on first use. Pass `--language <code>` to lock the recognition to a specific language; otherwise it auto-detects.

### Local-mode settings
All are optional and can go in `.env` (see `.env.example`):

| Setting | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` / `LLM_MODEL` | `openai` / provider default | Which LLM ranks highlights (also `--llm`, `--llm-model`) |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_NUM_CTX` | `localhost:11434`, `qwen3.8:27b`, `16384` | Ollama server, model, and context window |
| `LLM_BASE_URL`, `LLM_API_KEY` | — | `openai_compatible` server and optional key |
| `LOCAL_WHISPER_MODEL`, `LOCAL_WHISPER_DEVICE` | `base`, `auto` | Transcription model and device |
| `LOCAL_OUTPUT_DIR` | `output` | Where downloads, transcripts and clips are written |
| `LOCAL_CROP_MODE`, `LOCAL_FACECAM`, `LOCAL_BOTTOM_VIDEO`, `LOCAL_SPLIT_RATIO` | `face`, —, —, `0.6` | Layout settings (same as the `--layout` flags) |

## Project Structure

```
AI-Youtube-Shorts-Generator/
├── main.py                       runs the CLI from a source checkout (the CLI lives in shorts_generator/cli.py)
├── requirements.txt              core deps (api mode)
├── requirements-local.txt        optional deps for --mode local and --critique
├── .env.example
├── pyproject.toml                package metadata, dependencies, and the `shorts` command
├── tests/                        pytest suite (no network, keys or model downloads needed)
├── .github/workflows/ci.yml      CI: tests on macOS, Windows and Linux, the installers, the wheel build
├── Install-Mac.command           double-click installer (macOS)
├── Install-Windows.bat           double-click installer (Windows)
├── shorts, shorts.cmd            launchers that use the installed environment (macOS / Windows)
├── installers/                   install.sh (macOS/Linux) and install.ps1 (Windows)
└── shorts_generator/
    ├── cli.py                    command-line interface (`shorts`, `python -m shorts_generator`)
    ├── jobs.py                   progress events, cancellation, and the background Job
    ├── paths.py                  where settings live (user config folder) and how they are loaded
    ├── data/env.example          the settings template that `shorts --init-config` writes
    ├── config.py                 env / settings (MuAPI + local LLM + Whisper + layout)
    ├── url_validation.py         only HTTPS YouTube URLs are accepted as remote sources
    ├── muapi.py                  generic submit + poll wrapper
    ├── downloader.py             API mode: YouTube download via MuAPI
    ├── transcriber.py            API mode: MuAPI /openai-whisper client
    ├── highlights.py             shared LLM virality ranking, chunking, rerank, clip-length rules
    ├── clipper.py                API mode: MuAPI /autocrop
    ├── layout.py                 local-mode layout options (face / center / split)
    ├── critique.py               --critique: measured checks + LLM review of an existing video
    ├── doctor.py                 --doctor: setup checks with per-OS fixes
    ├── pipeline.py               mode dispatcher (api ↔ local)
    └── local/                    --mode local backends
        ├── downloader.py         yt-dlp download / local file handling
        ├── transcriber.py        faster-whisper transcription (cached as .srt)
        ├── llm.py                provider registry: openai, ollama, openai_compatible
        ├── clipper.py            smoothed face tracking, split layout, ffmpeg render
        └── system.py             ffmpeg detection, UTF-8 subprocess helper, cancellable ffmpeg runs, install hints
```

## Troubleshooting

### `shorts: command not found`
After `uv tool install`, run `uv tool update-shell` and open a new terminal. You can always use `python -m shorts_generator ...` (or `python main.py ...` from a checkout) instead.

### First, run the doctor
```bash
python main.py --doctor
```
It checks Python, ffmpeg, every dependency, OpenCV, the `av` compatibility problem and your LLM provider, and prints the exact fix for each failure on your OS.

### `open() got an unexpected keyword argument 'metadata_errors'`
`faster-whisper` is paired with a too-new `av`. Run `pip install "av>=14,<16"`.

### `module 'cv2' has no attribute 'CascadeClassifier'`
OpenCV 5.x removed the face detector this project uses. Run `pip install "opencv-python>=4.8,<5"`.

### Installing fails while building `av` ("pkg-config is required")
Your Python is too new for prebuilt wheels. Use Python 3.12 in a fresh virtual environment (see Installation).

### The crop shakes, or follows the wrong thing
Face tracking suits talking heads. For gameplay or streams with a webcam overlay, use `--layout center`, or `--layout split --facecam X,Y,W,H` to show the game and the webcam together.

### Ollama is slow, times out, or never answers
Check `ollama ps`: a large model already loaded (or busy with another job) blocks new requests. Long transcripts need a context window that fits them, so raise `OLLAMA_NUM_CTX` if highlights look truncated. The model must be pulled first (`ollama pull <model>`); the run checks this before starting.

### The YouTube download stalls or times out
Re-run the same command: `yt-dlp` resumes the partial file. A lower `--format` such as `480` also helps. To test the pipeline quickly, download just a section with `yt-dlp --download-sections "*0:00-15:00" ...` and pass that file instead.

### "You are sending unauthenticated requests to the HF Hub"
Harmless. It appears while `faster-whisper` downloads its model on first use. A token is only needed for higher rate limits.

### Whisper produced no segments
The video may have no detectable speech, or it may be in a language Whisper struggles with. Try passing `--language en` (or the correct ISO-639-1 code) to skip auto-detection.

### Looking for better results?
The [AI Clipping API](https://muapi.ai/playground/ai-clipping?utm_source=github&utm_medium=readme&utm_campaign=ai-youtube-shorts-generator) uses an improved algorithm that produces higher-quality clips with better highlight detection.

## Development

```bash
git clone <your fork> && cd AI-Youtube-Shorts-Generator
python3.12 -m venv .venv && source .venv/bin/activate      # Windows: py -3.12 -m venv .venv, then .venv\Scripts\Activate.ps1
pip install -e ".[local,dev]"
pytest
```

The tests need no network, API keys or model downloads, and they never read your real `.env` (they set `SHORTS_IGNORE_DOTENV=1`). Tests marked `ffmpeg` render real video and are skipped when ffmpeg isn't installed. A few tests are drift guards that fail if files that must stay in sync diverge: `pyproject.toml` and the requirements files, `.env.example` and `shorts_generator/data/env.example`, the CLI flags and this README, the line endings of the installer scripts.

CI (`.github/workflows/ci.yml`) runs the suite on macOS, Windows and Linux (Python 3.12 on all three, plus 3.10 and 3.13 on Linux), runs both one-click installers for real, and builds the wheel and installs it into a clean environment.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.

## Related Projects

- [awesome-vibecoded-saas](https://github.com/Anil-matcha/awesome-vibecoded-saas) — broader catalog of open-source SaaS alternatives featuring this Shorts workflow.
- [Muapi open-source alternatives](https://muapi.ai/open-source/alternative) — compare the Shorts workflow with the paid creator tools it targets.
- [AI Influencer Generator](https://github.com/SamurAIGPT/AI-Influencer-Generator)
- [Text to Video AI](https://github.com/SamurAIGPT/Text-To-Video-AI)
- [Faceless Video Generator](https://github.com/SamurAIGPT/Faceless-Video-Generator)
- [AI B-roll Generator](https://github.com/Anil-matcha/AI-B-roll)
- [No-code YouTube Shorts Generator](https://www.vadoo.tv/clip-youtube-video)
- [ai-creator-academy](https://github.com/Anil-matcha/ai-creator-academy) — free curriculum teaching creators how to monetize AI-generated shorts and video content
