"""CLI entry point.

Usage:
    python main.py "https://www.youtube.com/watch?v=..." \
        --num-clips 3 --aspect-ratio 9:16
"""
import argparse
import json
import sys

# Windows uses 'charmap' by default, which can't encode Unicode characters
# like →. Reconfigure stdout/stderr to UTF-8 so output works on all platforms.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from shorts_generator import generate_shorts
from shorts_generator.layout import MODES, Layout, parse_box
from shorts_generator.local import llm as llm_backend


def main() -> int:
    parser = argparse.ArgumentParser(description="AI YouTube Shorts Generator")
    parser.add_argument("url", nargs="?", help="YouTube URL, file:// URL, or local file path")
    parser.add_argument("--doctor", action="store_true",
                        help="Check this machine (Python, ffmpeg, dependencies, LLM) and print how to fix anything missing")
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
    args = parser.parse_args()

    if args.llm or args.llm_model:
        if args.mode == "api" and not args.critique:
            print("FAILED: --llm/--llm-model only apply to --mode local (or --critique).", file=sys.stderr)
            return 2
        llm_backend.configure(provider=args.llm, model=args.llm_model)

    if args.doctor:
        from shorts_generator.doctor import run_doctor
        return run_doctor()
    if not args.url:
        parser.error("a YouTube URL or video file path is required (or use --doctor)")

    if args.critique:
        from shorts_generator.critique import critique_video, format_report
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

    try:
        result = generate_shorts(
            youtube_url=args.url,
            num_clips=args.num_clips,
            aspect_ratio=args.aspect_ratio,
            download_format=args.format,
            language=args.language,
            mode=args.mode,
            layout=layout,
        )
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


if __name__ == "__main__":
    sys.exit(main())
