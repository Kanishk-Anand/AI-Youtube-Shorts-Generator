"""Local clipping: ffmpeg subclip + OpenCV face-aware vertical crop.

Two stages per highlight:
  1. Cut the source video to [start, end] with ffmpeg (re-encoded, audio kept).
  2. Reframe the cut to the target aspect ratio. For 9:16 we slide a vertical
     window across the frame to keep faces centred (Haar cascade, no external
     models). Tracking is two-pass so the camera doesn't shake:
       a. detect faces on a sparse subset of frames and build a raw path;
       b. median-filter it (drops outliers/flip-flops), hold the camera still
          inside a dead zone, then Gaussian-smooth the pans;
       c. crop every frame along that path and pipe it into ffmpeg (libx264).
     layout 'center' skips tracking and uses a fixed centre crop.

Layout 'split' skips all of that: ffmpeg cuts the source and stacks two panels in one
pass (see _render_split).
"""
import json
import os
import subprocess
from typing import Dict, List, Optional, Tuple

from ..config import LOCAL_OUTPUT_DIR
from ..layout import Layout
from .system import ensure_ffmpeg, run_text


def _ratio(aspect_ratio: str) -> float:
    """Parse '9:16' → 9/16, '1:1' → 1.0."""
    try:
        w, h = aspect_ratio.split(":")
        return float(w) / float(h)
    except (ValueError, ZeroDivisionError):
        return 9.0 / 16.0


def _cut_subclip(source_path: str, start: float, end: float, out_path: str) -> str:
    """ffmpeg -ss start -to end → re-encoded mp4 with audio."""
    source_path = os.path.abspath(os.path.expanduser(source_path))
    out_path = os.path.abspath(os.path.expanduser(out_path))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", source_path,
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        out_path,
    ]
    result = run_text(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed cutting the clip: {result.stderr.strip()[-500:]}")
    return out_path


DETECT_FPS = 10.0          # face detections per second of video (not every frame)
DETECT_MAX_WIDTH = 640     # downscale frames for detection; faster and less noisy
MEDIAN_WINDOW_S = 1.5      # outlier / flip-flop rejection window
DEADZONE_FRAC = 0.08       # camera holds still until the target moves this far (fraction of crop size)
SMOOTH_SIGMA_S = 0.8       # Gaussian smoothing of the remaining pans


def _fill_gaps(raw):
    """Linearly interpolate NaNs; returns None if there is nothing to interpolate."""
    import numpy as np

    valid = ~np.isnan(raw)
    if not valid.any():
        return None
    idx = np.arange(len(raw))
    return np.interp(idx, idx[valid], raw[valid])


def _median_filter(x, window: int):
    import numpy as np

    window = max(3, window | 1)  # odd, at least 3
    pad = window // 2
    padded = np.pad(x, pad, mode="edge")
    return np.median(np.lib.stride_tricks.sliding_window_view(padded, window), axis=1)


def _hold_in_deadzone(x, deadzone: float):
    """Camera stays put until the target leaves a dead zone, then follows at its edge."""
    import numpy as np

    out = np.empty_like(x)
    cam = x[0]
    for i, v in enumerate(x):
        d = v - cam
        if abs(d) > deadzone:
            cam = v - np.sign(d) * deadzone
        out[i] = cam
    return out


def _gaussian_smooth(x, sigma: float):
    import numpy as np

    if sigma < 0.5 or len(x) < 3:
        return x
    radius = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    k /= k.sum()
    padded = np.pad(x, radius, mode="edge")
    return np.convolve(padded, k, mode="valid")


def _smooth_path(raw, sample_fps: float, deadzone: float):
    """raw: per-sample centre (NaN where no face). Returns a stable path or None."""
    filled = _fill_gaps(raw)
    if filled is None:
        return None
    path = _median_filter(filled, int(round(MEDIAN_WINDOW_S * sample_fps)))
    path = _hold_in_deadzone(path, deadzone)
    return _gaussian_smooth(path, SMOOTH_SIGMA_S * sample_fps)


def _detect_face_path(cap, src_w: int, src_h: int, fps: float):
    """Pass 1: sparse face detection. Returns (frame_indices, cx, cy) arrays (NaN = no face)."""
    import cv2  # type: ignore
    import numpy as np

    step = max(1, int(round(fps / DETECT_FPS)))
    scale = min(1.0, DETECT_MAX_WIDTH / src_w)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    min_side = max(24, int(0.04 * src_w * scale))

    frames, cxs, cys = [], [], []
    i = 0
    while True:
        if not cap.grab():
            break
        if i % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if scale < 1.0:
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            faces = cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=6, minSize=(min_side, min_side)
            )
            frames.append(i)
            if len(faces) > 0:
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])  # largest face ≈ speaker
                cxs.append((x + w / 2) / scale)
                cys.append((y + h / 2) / scale)
            else:
                cxs.append(float("nan"))
                cys.append(float("nan"))
        i += 1
    return np.array(frames, dtype=float), np.array(cxs), np.array(cys), step


def _reframe_vertical(in_path: str, out_path: str, aspect_ratio: str, mode: str = "face") -> str:
    """Crop the cut clip to the target aspect ratio, tracking faces smoothly if possible."""
    in_path = os.path.abspath(os.path.expanduser(in_path))
    out_path = os.path.abspath(os.path.expanduser(out_path))
    try:
        import cv2  # type: ignore
        import numpy as np
    except ImportError as e:
        raise RuntimeError(
            "opencv-python is required for --mode local. Install it with:\n"
            "    pip install -r requirements-local.txt"
        ) from e

    target_ratio = _ratio(aspect_ratio)
    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        raise RuntimeError(f"could not open {in_path}")

    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Compute the largest crop that fits inside the frame at the target ratio.
    if target_ratio < src_w / src_h:
        crop_h = src_h
        crop_w = int(crop_h * target_ratio)
    else:
        crop_w = src_w
        crop_h = int(crop_w / target_ratio)
    crop_w = max(2, crop_w - (crop_w % 2))
    crop_h = max(2, crop_h - (crop_h % 2))

    # Pass 1: smoothed camera path (centre of the crop window), sampled sparsely.
    sample_idx = path_x = path_y = None
    if mode != "center":
        sample_idx, raw_x, raw_y, step = _detect_face_path(cap, src_w, src_h, fps)
        sample_fps = fps / step
        path_x = _smooth_path(raw_x, sample_fps, DEADZONE_FRAC * crop_w)
        path_y = _smooth_path(raw_y, sample_fps, DEADZONE_FRAC * crop_h)
        cap.release()
        cap = cv2.VideoCapture(in_path)  # rewind for pass 2
        found = int(np.sum(~np.isnan(raw_x)))
        print(f"[clip/local] face found in {found}/{len(raw_x)} samples", flush=True)

    # Pass 2: crop every frame along the path, pipe raw frames into ffmpeg (libx264),
    # and take the audio from the cut clip. Avoids a lossy intermediate encode.
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{crop_w}x{crop_h}", "-r", f"{fps}", "-i", "-",
        "-i", in_path,
        "-map", "0:v:0", "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    n = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cx = float(np.interp(n, sample_idx, path_x)) if path_x is not None else src_w / 2
            cy = float(np.interp(n, sample_idx, path_y)) if path_y is not None else src_h / 2
            x0 = int(round(max(0, min(src_w - crop_w, cx - crop_w / 2))))
            y0 = int(round(max(0, min(src_h - crop_h, cy - crop_h / 2))))
            proc.stdin.write(np.ascontiguousarray(frame[y0:y0 + crop_h, x0:x0 + crop_w]).tobytes())
            n += 1
        proc.stdin.close()
    except OSError:
        # ffmpeg exited early. A closed pipe is BrokenPipeError on POSIX but can surface as a
        # plain OSError (EINVAL) on Windows; either way its stderr is reported below.
        pass
    finally:
        cap.release()
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while encoding {out_path}: {err.strip()}")
    return out_path


def _probe(path: str) -> Dict:
    """Width/height/fps/duration of the first video stream, via ffprobe."""
    result = run_text(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate:format=duration",
         "-of", "json", path],
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"ffprobe could not read {path}: {result.stderr.strip()[-300:]}")
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    num, _, den = stream["r_frame_rate"].partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": fps or 30.0,
        "duration": float(data.get("format", {}).get("duration") or 0.0),
    }


def _even(n: float) -> int:
    return max(2, int(round(n)) // 2 * 2)


def _render_split(
    source_path: str,
    start: float,
    end: float,
    aspect_ratio: str,
    out_path: str,
    layout: Layout,
) -> str:
    """One ffmpeg pass: cut [start, end] and stack a top panel over a bottom panel.

    top    = centre crop of the source video (the main content)
    bottom = layout.bottom_video if given (looped/trimmed to the clip length, its audio
             ignored), otherwise the layout.facecam box cut out of the source.
    Audio always comes from the source.
    """
    source_path = os.path.abspath(os.path.expanduser(source_path))
    out_path = os.path.abspath(os.path.expanduser(out_path))
    src = _probe(source_path)
    src_w, src_h, fps = src["width"], src["height"], src["fps"]
    duration = end - start

    out_h = _even(src_h)
    out_w = _even(out_h * _ratio(aspect_ratio))
    top_h = _even(out_h * layout.split_ratio)
    bot_h = out_h - top_h

    # Largest centred source region with the top panel's aspect ratio.
    reg_h = float(src_h)
    reg_w = reg_h * out_w / top_h
    if reg_w > src_w:
        reg_w = float(src_w)
        reg_h = reg_w * top_h / out_w
    reg_w, reg_h = _even(reg_w), _even(reg_h)
    top = (
        f"crop={reg_w}:{reg_h}:(iw-{reg_w})/2:(ih-{reg_h})/2,"
        f"scale={out_w}:{top_h},setsar=1"
    )
    cover = (
        f"scale={out_w}:{bot_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{bot_h},setsar=1"
    )

    inputs = ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", source_path]
    if layout.bottom_video:
        bottom_path = os.path.expanduser(layout.bottom_video)
        vid_dur = _probe(bottom_path)["duration"]
        # Deterministic, but different per clip so back-to-back shorts don't repeat footage.
        offset = start % (vid_dur - duration) if vid_dur > duration + 1 else 0.0
        inputs += ["-ss", f"{offset:.3f}", "-stream_loop", "-1", "-i", bottom_path]
        filters = (
            f"[0:v]{top}[top];"
            f"[1:v]fps={fps:.3f},{cover}[bot];"
        )
    else:
        fx, fy, fw, fh = layout.facecam  # type: ignore[misc]
        if fx + fw > src_w or fy + fh > src_h:
            raise ValueError(
                f"facecam box {fx},{fy},{fw},{fh} falls outside the {src_w}x{src_h} source video"
            )
        filters = (
            f"[0:v]split=2[g][f];"
            f"[g]{top}[top];"
            f"[f]crop={fw}:{fh}:{fx}:{fy},{cover}[bot];"
        )
    filters += "[top][bot]vstack=inputs=2,format=yuv420p[v]"

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", *inputs,
        "-filter_complex", filters,
        "-map", "[v]", "-map", "0:a:0?",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        out_path,
    ]
    result = run_text(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg split render failed: {result.stderr.strip()}")
    return out_path


def crop_clip_local(
    source_path: str,
    start_time: float,
    end_time: float,
    aspect_ratio: str,
    out_path: str,
    layout: Optional[Layout] = None,
) -> str:
    """Cut + reframe one highlight, returning the local mp4 path."""
    layout = layout or Layout.from_config()
    if layout.mode == "split":
        return _render_split(source_path, start_time, end_time, aspect_ratio, out_path, layout)

    cut_path = out_path + ".cut.mp4"
    try:
        _cut_subclip(source_path, start_time, end_time, cut_path)
        _reframe_vertical(cut_path, out_path, aspect_ratio, mode=layout.mode)
    finally:
        if os.path.exists(cut_path):
            os.remove(cut_path)
    return out_path


def crop_highlights_local(
    source_path: str,
    highlights: List[Dict],
    aspect_ratio: str = "9:16",
    out_dir: Optional[str] = None,
    layout: Optional[Layout] = None,
) -> List[Dict]:
    ensure_ffmpeg()
    out_dir = os.path.abspath(os.path.expanduser(out_dir or LOCAL_OUTPUT_DIR))
    layout = (layout or Layout.from_config()).validate()
    os.makedirs(out_dir, exist_ok=True)
    results: List[Dict] = []
    for i, h in enumerate(highlights, 1):
        out_path = os.path.join(out_dir, f"short_{i:02d}.mp4")
        print(f"[clip/local] {i}/{len(highlights)}: {h.get('title', '(untitled)')}", flush=True)
        try:
            crop_clip_local(
                source_path,
                float(h["start_time"]),
                float(h["end_time"]),
                aspect_ratio,
                out_path,
                layout=layout,
            )
            results.append({**h, "clip_url": out_path})
        except Exception as e:
            print(f"[clip/local] {i} failed: {e}", flush=True)
            results.append({**h, "clip_url": None, "error": str(e)})
    return results
