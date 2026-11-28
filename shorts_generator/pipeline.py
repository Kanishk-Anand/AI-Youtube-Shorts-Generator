"""End-to-end orchestrator.

Two modes:
  * mode="api"   (default) — MuAPI does download / transcribe / LLM / autocrop.
                              Fast, no local deps, pay-per-call.
  * mode="local"            — yt-dlp + faster-whisper + OpenAI or Ollama + ffmpeg/opencv.
                              Self-hosted, LLM_PROVIDER selects the LLM.

Every run is also a *job*: it reports structured progress (`on_event`) and can be cancelled
(`cancel`, or `start_job(...).cancel()`). See shorts_generator/jobs.py.
"""
import threading
from typing import Callable, Dict, List, Optional

from . import jobs
from .clipper import crop_highlights
from .config import require_api_key
from .downloader import download_youtube
from .highlights import call_muapi_llm, get_highlights
from .jobs import Job, ProgressEvent
from .layout import Layout
from .transcriber import transcribe


def _pick_top(all_highlights: List[Dict], num_clips: int) -> List[Dict]:
    return sorted(all_highlights, key=lambda h: int(h.get("score", 0)), reverse=True)[:num_clips]


def _run_local(
    youtube_url: str,
    num_clips: int,
    aspect_ratio: str,
    download_format: str,
    language: Optional[str],
    layout: Optional[Layout] = None,
) -> Dict:
    from .local.clipper import crop_highlights_local
    from .local.downloader import download_youtube_local
    from .local.llm import call_local_llm, describe, validate
    from .local.system import ensure_ffmpeg
    from .local.transcriber import transcribe_local

    # Fail fast, before any slow step.
    jobs.emit("pipeline", "start", "Checking setup")
    layout = (layout or Layout.from_config()).validate()
    ensure_ffmpeg()
    validate()
    print(f"[llm] {describe()}", flush=True)
    jobs.emit("pipeline", "done", "Setup OK", llm=describe())

    jobs.checkpoint()
    source_path = download_youtube_local(youtube_url, fmt=download_format)

    jobs.checkpoint()
    transcript = transcribe_local(source_path, language=language)
    if not transcript["segments"]:
        raise RuntimeError(
            "Whisper produced no segments. The video may have no detectable speech."
        )

    jobs.checkpoint()
    highlights_result = get_highlights(transcript, num_clips=num_clips, llm_fn=call_local_llm)
    all_highlights: List[Dict] = highlights_result.get("highlights", [])
    if not all_highlights:
        raise RuntimeError("Highlight generator returned zero clips.")

    top = _pick_top(all_highlights, num_clips)
    print(f"[pipeline/local] cropping {len(top)} of {len(all_highlights)} candidates", flush=True)

    jobs.checkpoint()
    shorts = crop_highlights_local(source_path, top, aspect_ratio=aspect_ratio, layout=layout)

    return {
        "mode": "local",
        "source_video_url": source_path,
        "transcript": transcript,
        "highlights": all_highlights,
        "shorts": shorts,
    }


def _run_api(
    youtube_url: str,
    num_clips: int,
    aspect_ratio: str,
    download_format: str,
    language: Optional[str],
) -> Dict:
    jobs.emit("download", "start", "Downloading via MuAPI")
    source_url = download_youtube(youtube_url, fmt=download_format)
    jobs.emit("download", "done", "Downloaded")

    jobs.checkpoint()
    jobs.emit("transcribe", "start", "Transcribing via MuAPI")
    transcript = transcribe(source_url, language=language)
    if not transcript["segments"]:
        raise RuntimeError(
            "Whisper produced no segments. The video may have no detectable speech."
        )
    jobs.emit("transcribe", "done", f"{len(transcript['segments'])} segments")

    jobs.checkpoint()
    highlights_result = get_highlights(transcript, num_clips=num_clips, llm_fn=call_muapi_llm)
    all_highlights: List[Dict] = highlights_result.get("highlights", [])
    if not all_highlights:
        raise RuntimeError("Highlight generator returned zero clips.")

    top = _pick_top(all_highlights, num_clips)
    print(f"[pipeline] cropping {len(top)} of {len(all_highlights)} candidates", flush=True)

    jobs.checkpoint()
    shorts = crop_highlights(source_url, top, aspect_ratio=aspect_ratio)

    return {
        "mode": "api",
        "source_video_url": source_url,
        "transcript": transcript,
        "highlights": all_highlights,
        "shorts": shorts,
    }


def _generate(
    youtube_url: str,
    num_clips: int,
    aspect_ratio: str,
    download_format: str,
    language: Optional[str],
    mode: str,
    layout: Optional[Layout],
) -> Dict:
    mode = (mode or "api").lower()
    if mode == "local":
        return _run_local(youtube_url, num_clips, aspect_ratio, download_format, language, layout)
    if layout is not None:
        raise ValueError("layout options only apply to --mode local.")
    if mode == "api":
        require_api_key()
        return _run_api(youtube_url, num_clips, aspect_ratio, download_format, language)
    raise ValueError(f"Unknown mode: {mode!r}. Use 'api' or 'local'.")


def generate_shorts(
    youtube_url: str,
    num_clips: int = 3,
    aspect_ratio: str = "9:16",
    download_format: str = "720",
    language: Optional[str] = None,
    mode: str = "api",
    layout: Optional[Layout] = None,
    on_event: Optional[Callable[[ProgressEvent], None]] = None,
    cancel: Optional[threading.Event] = None,
) -> Dict:
    """Run the full pipeline and return a structured result.

    Args:
        youtube_url: source URL.
        num_clips: how many shorts to render.
        aspect_ratio: e.g. "9:16", "1:1".
        download_format: source resolution ("360" / "480" / "720" / "1080").
        language: ISO-639-1 to force Whisper language detection.
        mode: "api" (default, MuAPI) or "local" (yt-dlp + faster-whisper +
            OpenAI or Ollama + ffmpeg).
        layout: local mode only — how clips are framed (see shorts_generator.layout).
            Defaults to the LOCAL_CROP_MODE / LOCAL_FACECAM / LOCAL_BOTTOM_VIDEO env settings.
        on_event: called with a ProgressEvent for every progress update (from the thread running
            the pipeline). Exceptions raised by the callback are ignored.
        cancel: a threading.Event; set it to stop the run at the next checkpoint. The call then
            raises shorts_generator.CancelledError (a BaseException).

    Returns:
        {
          "mode": "api" | "local",
          "source_video_url": str,   # hosted URL (api) or local path (local)
          "transcript": {...},
          "highlights": [...],       # all candidates ranked
          "shorts": [...],           # top `num_clips` with clip_url / local path
        }
    """
    ctx = jobs.current()
    if ctx is None or on_event is not None or cancel is not None:
        ctx = jobs.JobContext(on_event, cancel)
    with jobs.activate(ctx):
        try:
            result = _generate(youtube_url, num_clips, aspect_ratio, download_format, language, mode, layout)
        except jobs.CancelledError:
            jobs.emit("pipeline", "cancelled", "Cancelled")
            raise
        except Exception as exc:
            jobs.emit("pipeline", "error", str(exc))
            raise
        ok = sum(1 for s in result.get("shorts", []) if s.get("clip_url"))
        jobs.emit("pipeline", "finished", f"{ok} of {len(result.get('shorts', []))} clips rendered", clips=ok)
        return result


def start_job(youtube_url: str, on_event: Optional[Callable[[ProgressEvent], None]] = None, **kwargs) -> Job:
    """Start `generate_shorts(youtube_url, **kwargs)` on a background thread and return the Job.

        job = start_job(url, mode="local")
        for event in job.events():       # progress, until the job finishes
            print(event.stage, event.status, event.fraction)
        job.cancel()                     # from any thread, at any time
        result = job.result()            # the generate_shorts() dict

    `on_event` is an optional callback run on the job's thread for each event, in addition to
    `job.events()`. All other keyword arguments are passed to `generate_shorts`.
    """
    return Job(lambda ctx: generate_shorts(youtube_url, **kwargs), on_event=on_event).start()
