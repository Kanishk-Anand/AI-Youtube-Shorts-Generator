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
- **🔀 Two Modes — API (fast) or Local (offline)**: Default `--mode api` uses MuAPI for download/transcription/cropping; `--mode local` runs entirely on your machine with `yt-dlp`, `faster-whisper`, and `ffmpeg`/`opencv`, and lets you pick OpenAI or a local Ollama model for highlight ranking
- **🤖 Virality-Aware Highlight Selection**: Clips ranked on hooks, emotional peaks, opinion bombs, revelation moments, conflict, quotable lines, story peaks, and practical value — not just generic "interesting"
- **📈 Score + Hook + Reason for Every Clip**: Each highlight comes with a viral score, an opening hook line, and a one-sentence explanation of why it works
- **🎤 Whisper Transcription, Your Choice**: Cloud (`/openai-whisper` via MuAPI) or local (`faster-whisper`, CPU or CUDA) — same downstream output shape
- **🧩 Long-Video Aware**: Videos over 30 minutes are auto-chunked with overlap so nothing gets missed
- **♻️ Smart Dedupe**: Overlapping highlights are collapsed by score so you never get two near-duplicate clips
- **🎯 Smart Vertical Crop**: API mode uses MuAPI's auto-crop; local mode runs OpenCV face tracking with motion smoothing
- **📱 Any Aspect Ratio**: 9:16 for TikTok/Reels/Shorts, 1:1 for square, anything else by flag
- **🧰 CLI + Python Library**: Use it from the shell or import `generate_shorts(...)` into your own pipeline
- **📦 JSON Output**: `--output-json` dumps the full result (transcript + every candidate highlight + final clip URLs/paths) for downstream automation

## Quick Start (No Setup)

Don't want to self-host? The [AI Clipping API](https://muapi.ai/playground/ai-clipping?utm_source=github&utm_medium=readme&utm_campaign=ai-youtube-shorts-generator) gives you the same Opus Clip–style pipeline as a single HTTP call — no Python, no dependencies, pay-per-clip instead of monthly subscriptions.

---

## Installation (Self-Hosted)

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

## Usage

### Single video (API mode — default)

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Single video (Local mode — runs offline except for the LLM call)

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


## How It Works

1. **Download**: Fetches the source video from YouTube
2. **Transcribe**: MuAPI `/openai-whisper` produces a timestamped transcript (verbose_json segments)
3. **Detect content type**: An LLM classifies the video (podcast, interview, tutorial, vlog, etc.) and density, so the prompt can be tuned per content style
4. **Long-video chunking**: Videos > 30 min are split into 20-min overlapping chunks
5. **Highlight ranking**: An LLM scans the transcript through a virality framework — hook moments, emotional peaks, opinion bombs, revelations, conflict, quotables, story peaks, practical value — and emits ranked candidates with scores 0–100
6. **Dedupe**: Overlapping candidates are collapsed by score (>50% overlap → keep the higher score)
7. **Top-N selection**: The top `--num-clips` candidates are selected
8. **Auto-crop**: Each highlight is rendered as a vertical short at the requested aspect ratio

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
- **Chunk size**: `CHUNK_SIZE_SECONDS` (default 1200) — chunk length for long videos
- **Long-video threshold**: `LONG_VIDEO_THRESHOLD` (default 1800) — videos longer than this are chunked
- **Chunk overlap**: `CHUNK_OVERLAP_SECONDS` (default 60) — overlap between chunks so cross-boundary clips aren't missed

### Polling / timeout
Edit `shorts_generator/config.py` (or set env vars):
- `MUAPI_POLL_INTERVAL` (default 5s) — seconds between job-status polls
- `MUAPI_POLL_TIMEOUT` (default 1800s) — give up after this long

### Whisper transcription
Audio is transcribed by MuAPI's `/openai-whisper` endpoint (server-side `whisper-1`). Pass `--language <code>` to lock the recognition to a specific language; otherwise it auto-detects.

## Project Structure

```
AI-Youtube-Shorts-Generator/
├── main.py                       CLI entry point
├── requirements.txt              core deps (api mode)
├── requirements-local.txt        optional deps for --mode local
├── .env.example
└── shorts_generator/
    ├── config.py                 env / settings (MuAPI + local LLM + Whisper)
    ├── muapi.py                  generic submit + poll wrapper
    ├── downloader.py             API mode: YouTube download via MuAPI
    ├── transcriber.py            API mode: MuAPI /openai-whisper client
    ├── highlights.py             shared LLM virality ranking (pluggable backend)
    ├── clipper.py                API mode: MuAPI /autocrop
    ├── pipeline.py               mode dispatcher (api ↔ local)
    └── local/                    --mode local backends (offline)
        ├── downloader.py         yt-dlp download
        ├── transcriber.py        faster-whisper transcription
        ├── llm.py                OpenAI or Ollama client selector
        └── clipper.py            ffmpeg cut + OpenCV vertical crop
```

## Troubleshooting

### Whisper produced no segments
The video may have no detectable speech, or it may be in a language Whisper struggles with. Try passing `--language en` (or the correct ISO-639-1 code) to skip auto-detection.

### Looking for better results?
The [AI Clipping API](https://muapi.ai/playground/ai-clipping?utm_source=github&utm_medium=readme&utm_campaign=ai-youtube-shorts-generator) uses an improved algorithm that produces higher-quality clips with better highlight detection.

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
