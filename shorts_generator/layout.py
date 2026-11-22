"""How each short is framed in --mode local.

  face    track the speaker's face with a smoothed vertical crop (talking heads)
  center  fixed centre crop, no tracking
  split   two panels stacked: the source video on top, and below it either
            * a box cut out of the source (the streamer's facecam), or
            * any other video you supply (e.g. a looping gameplay clip).
"""
import os
from dataclasses import dataclass, replace
from typing import Optional, Tuple

from . import config

MODES = ("face", "center", "split")
Box = Tuple[int, int, int, int]  # x, y, width, height in source pixels


def parse_box(value: Optional[str]) -> Optional[Box]:
    """'x,y,w,h' -> (x, y, w, h); empty -> None."""
    if not value or not str(value).strip():
        return None
    try:
        x, y, w, h = (int(float(p)) for p in str(value).split(","))
    except ValueError:
        raise ValueError(f"facecam must be 'x,y,w,h' in source pixels, got {value!r}") from None
    if x < 0 or y < 0 or w <= 0 or h <= 0:
        raise ValueError(f"facecam box must have x,y >= 0 and w,h > 0, got {value!r}")
    return x, y, w, h


@dataclass(frozen=True)
class Layout:
    mode: str = "face"
    facecam: Optional[Box] = None
    bottom_video: Optional[str] = None
    split_ratio: float = 0.6

    @classmethod
    def from_config(cls) -> "Layout":
        return cls(
            mode=config.LOCAL_CROP_MODE,
            facecam=parse_box(config.LOCAL_FACECAM),
            bottom_video=config.LOCAL_BOTTOM_VIDEO or None,
            split_ratio=config.LOCAL_SPLIT_RATIO,
        )

    def with_overrides(self, **kw) -> "Layout":
        """Apply only the options that were actually given (None = keep current)."""
        return replace(self, **{k: v for k, v in kw.items() if v is not None})

    def validate(self) -> "Layout":
        if self.mode not in MODES:
            raise ValueError(f"Unknown layout {self.mode!r}. Use one of: {', '.join(MODES)}.")
        if self.mode != "split":
            return self
        if not 0.3 <= self.split_ratio <= 0.8:
            raise ValueError(f"split ratio must be between 0.3 and 0.8, got {self.split_ratio}")
        if self.bottom_video:
            path = os.path.expanduser(self.bottom_video)
            if not os.path.isfile(path):
                raise ValueError(f"bottom video not found: {self.bottom_video}")
        elif not self.facecam:
            raise ValueError(
                "split layout needs a bottom panel: pass --bottom-video FILE, or --facecam x,y,w,h "
                "to use a box from the source video (env: LOCAL_BOTTOM_VIDEO / LOCAL_FACECAM)."
            )
        return self
