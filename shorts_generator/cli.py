"""Command-line interface (`shorts ...`, `python -m shorts_generator ...`, `python main.py ...`).

Usage:
    shorts "https://www.youtube.com/watch?v=..." --num-clips 3 --aspect-ratio 9:16
"""
import argparse
import json
import sys
from typing import List, Optional

from . import __version__, paths
from .jobs import CancelledError, Job, ProgressEvent
from .layout import MODES, Layout, parse_box
from .local import llm as llm_backend
from .pipeline import start_job


def _utf8_console() -> None:
    # Windows consoles default to a legacy code page that can't print characters like "→".
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


class _ProgressPrinter:
    """Prints a line every 10% for stages that report a fraction, and any warnings."""

    def __init__(self) -> None:
        self._last: dict = {}

    def __call__(self, event: ProgressEvent) -> None:
        if event.status == "warn":
            print(f"  [{event.stage}] {event.message}", flush=True)
            return
        fraction = event.fraction
        if event.status == "progress" and fraction is not None:
            step = int(fraction * 10)
            if self._last.get(event.stage) != step:
                self._last[event.stage] = step
                print(f"  [{event.stage}] {int(fraction * 100)}%", flush=True)


def _wait(job: Job):
    """Wait for the job; the first Ctrl+C cancels it cleanly, a second one quits at once."""
    try:
        while not job.wait(0.2):
            pass
    except KeyboardInterrupt:
        print("\nCancelling... (press Ctrl+C again to quit immediately)", flush=True)
        job.cancel()
        try:
            while not job.wait(0.2):
                pass
        except KeyboardInterrupt:
            raise SystemExit(130)
    return job.result()


def _print_config() -> None:
    print("Settings are read from these places. Real environment variables always win;")
    print("after that, the first file in this list that sets a value wins.\n")
    print("  1. environment variables")
    for n, (label, path, exists) in enumerate(paths.describe(), start=2):
        print(f"  {n}. {label}: {path}   [{'found' if exists else 'not found'}]")
    print(f"\nUser config folder: {paths.config_dir()}")
    print("Create the user settings file with:  shorts --init-config")


def _init_config() -> int:
    path, created = paths.init_user_config()
    if created:
        print(f"Created {path}\nEdit it to choose your LLM and settings.")
    else:
        print(f"{path} already exists, left unchanged.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shorts", description="AI YouTube Shorts Generator")
    parser.add_argument("url", nargs="?", help="YouTube URL, file:// URL, or local file path")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--doctor", action="store_true",
                        help="Check this machine (Python, ffmpeg, dependencies, LLM) and print how to fix anything missing")
    parser.add_argument("--config", action="store_true", help="Show where settings are read from")
    parser.add_argument("--init-config", action="store_true",
                        help="Create the settings file in your user config folder from the template")
    parser.add_argument(
        "--mode",
        choices=["api", "local"],
        default="api",
        help="api (default, MuAPI) or local (remote URL, file://, or local path + faster-whisper + LLM provider + ffmpeg).",
    )
    parser.add_argument("--num-clips", type=int, default=3, help="How many shorts to render (default: 3)")
    parser.add_argument("--aspect-ratio", default="9:16", help="Output aspect ratio (default: 9:16)")
    parser.add_argument("--format", default="720", help="Source download resolution: 360 / 480 / 720 / 1080 (default: 720)")
    parser.add_argument("--language", default=None, help="Force Whisper language code, e.g. 'en' (default: auto-detect)")
    parser.add_argument("--layout", choices=MODES, default=None,
                        help="local mode framing: face (track speaker), center, or split (two stacked panels). Default: LOCAL_CROP_MODE or face")
    parser.add_argument("--bottom-video", default=None, metavar="FILE",
                        help="split layout: video to show in the bottom panel (looped/trimmed to the clip)")
    parser.add_argument("--facecam", default=None, metavar="X,Y,W,H",
                        help="split layout: box in the source video to show in the bottom panel (ignored if --bottom-video is set)")
    parser.add_argument("--split-ratio", type=float, default=None,
                        help="split layout: fraction of the height used by the top panel (0.3-0.8, default 0.6)")
    parser.add_argument("--llm", default=None, metavar="PROVIDER",
                        help=f"LLM for highlight ranking / critique: {', '.join(llm_backend.available_providers())} (default: LLM_PROVIDER or openai)")
    parser.add_argument("--llm-model", default=None, metavar="MODEL",
                        help="model name for the chosen provider (default: its *_MODEL setting, or LLM_MODEL)")
    parser.add_argument("--critique", action="store_true",
                        help="Don't generate clips: review an existing video/short (file or URL) and report what works, what doesn't and what to change. Uses LLM_PROVIDER for the content review.")
    parser.add_argument("--no-llm", action="store_true", help="With --critique: measured checks only, skip the LLM review")
    parser.add_argument("--output-json", default=None, help="Write the full result JSON to this path")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    _utf8_console()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.config:
        _print_config()
        return 0
    if args.init_config:
        return _init_config()

    if args.llm or args.llm_model:
        if args.mode == "api" and not args.critique:
            print("FAILED: --llm/--llm-model only apply to --mode local (or --critique).", file=sys.stderr)
            return 2
        llm_backend.configure(provider=args.llm, model=args.llm_model)

    if args.doctor:
        from .doctor import run_doctor
        return run_doctor()
    if not args.url:
        parser.error("a YouTube URL or video file path is required (or use --doctor)")

    if args.critique:
        from .critique import critique_video, format_report
        try:
            report = critique_video(args.url, language=args.language, use_llm=not args.no_llm)
        except Exception as e:
            print(f"\nFAILED: {e}", file=sys.stderr)
            return 1
        print("\n" + format_report(report))
        if args.output_json:
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\nFull JSON written to {args.output_json}")
        return 0

    layout = None
    if any(v is not None for v in (args.layout, args.bottom_video, args.facecam, args.split_ratio)):
        try:
            layout = Layout.from_config().with_overrides(
                mode=args.layout or ("split" if (args.bottom_video or args.facecam) else None),
                bottom_video=args.bottom_video,
                facecam=parse_box(args.facecam),
                split_ratio=args.split_ratio,
            )
        except ValueError as e:
            print(f"FAILED: {e}", file=sys.stderr)
            return 2

    job = start_job(
        args.url,
        on_event=_ProgressPrinter(),
        num_clips=args.num_clips,
        aspect_ratio=args.aspect_ratio,
        download_format=args.format,
        language=args.language,
        mode=args.mode,
        layout=layout,
    )
    try:
        result = _wait(job)
    except CancelledError:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1

    print("\n" + "=" * 72)
    print(f"Mode:          {result.get('mode', args.mode)}")
    print(f"Source video:  {result['source_video_url']}")
    print(f"Highlights:    {len(result['highlights'])} candidates → kept top {len(result['shorts'])}")
    print("=" * 72)
    for i, s in enumerate(result["shorts"], 1):
        print(f"\n#{i}  score={s.get('score')}  {s.get('start_time'):.1f}s → {s.get('end_time'):.1f}s")
        print(f"     title:  {s.get('title')}")
        print(f"     hook:   {s.get('hook_sentence')}")
        if s.get("clip_url"):
            print(f"     clip:   {s['clip_url']}")
        else:
            print(f"     clip:   FAILED ({s.get('error')})")

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\nFull JSON written to {args.output_json}")

    return 0
