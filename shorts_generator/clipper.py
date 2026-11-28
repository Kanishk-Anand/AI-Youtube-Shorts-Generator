"""Per-clip cropping via MuAPI /autocrop.

Given the source video URL plus a highlight's start/end and a target aspect
ratio, MuAPI returns a vertically-cropped short ready for posting.
"""
from typing import Dict

from . import jobs, muapi
from .downloader import _extract_video_url


def crop_clip(source_video_url: str, start_time: float, end_time: float, aspect_ratio: str = "9:16") -> str:
    """Submit one autocrop job and return the URL of the rendered short."""
    payload = {
        "video_url": source_video_url,
        "start_time": float(start_time),
        "end_time": float(end_time),
        "aspect_ratio": aspect_ratio,
    }
    print(f"[clip] {start_time:.1f}s → {end_time:.1f}s @ {aspect_ratio}", flush=True)
    result = muapi.run("autocrop", payload, label=f"autocrop({start_time:.0f}-{end_time:.0f})")
    return _extract_video_url(result)


def crop_highlights(source_video_url: str, highlights: list, aspect_ratio: str = "9:16") -> list:
    """Crop every highlight, attaching the resulting URL back onto the dict."""
    out = []
    total = len(highlights)
    jobs.emit("render", "start", f"Rendering {total} clips via MuAPI", current=0, total=total)
    for i, h in enumerate(highlights, 1):
        print(f"[clip] {i}/{total}: {h.get('title', '(untitled)')}", flush=True)
        jobs.checkpoint()
        jobs.emit("render", "progress", h.get("title", ""), current=i - 1, total=total, clip=i)
        try:
            url = crop_clip(
                source_video_url,
                h["start_time"],
                h["end_time"],
                aspect_ratio=aspect_ratio,
            )
            out.append({**h, "clip_url": url})
            jobs.emit("render", "progress", h.get("title", ""), current=i, total=total, clip=i)
        except Exception as e:
            print(f"[clip] {i} failed: {e}", flush=True)
            out.append({**h, "clip_url": None, "error": str(e)})
            jobs.emit("render", "warn", f"Clip {i} failed: {e}", current=i, total=total, clip=i)
    jobs.emit("render", "done", f"{sum(1 for r in out if r.get('clip_url'))} of {total} clips rendered")
    return out
