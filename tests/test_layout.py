import pytest

from shorts_generator import config
from shorts_generator.layout import Layout, parse_box


def test_parse_box_accepts_pixels_and_blank():
    assert parse_box("0,305,260,165") == (0, 305, 260, 165)
    assert parse_box(" 1.0, 2, 30, 40 ") == (1, 2, 30, 40)
    assert parse_box("") is None and parse_box(None) is None


@pytest.mark.parametrize("bad", ["1,2,3", "a,b,c,d", "-1,0,10,10", "0,0,0,10"])
def test_parse_box_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_box(bad)


def test_split_needs_a_bottom_panel():
    with pytest.raises(ValueError, match="needs a bottom panel"):
        Layout(mode="split").validate()
    Layout(mode="split", facecam=(0, 0, 10, 10)).validate()


def test_split_validates_ratio_and_bottom_video(tmp_path):
    with pytest.raises(ValueError, match="between 0.3 and 0.8"):
        Layout(mode="split", facecam=(0, 0, 10, 10), split_ratio=0.95).validate()
    with pytest.raises(ValueError, match="not found"):
        Layout(mode="split", bottom_video=str(tmp_path / "missing.mp4")).validate()
    real = tmp_path / "filler.mp4"
    real.write_bytes(b"x")
    Layout(mode="split", bottom_video=str(real)).validate()


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="Unknown layout"):
        Layout(mode="wat").validate()


def test_overrides_skip_none_values():
    base = Layout(mode="face", split_ratio=0.6)
    out = base.with_overrides(mode=None, split_ratio=0.5, facecam=None)
    assert out.mode == "face" and out.split_ratio == 0.5


def test_layout_is_built_from_settings(monkeypatch):
    monkeypatch.setattr(config, "LOCAL_CROP_MODE", "split")
    monkeypatch.setattr(config, "LOCAL_FACECAM", "1,2,3,4")
    monkeypatch.setattr(config, "LOCAL_BOTTOM_VIDEO", "")
    monkeypatch.setattr(config, "LOCAL_SPLIT_RATIO", 0.55)
    layout = Layout.from_config()
    assert (layout.mode, layout.facecam, layout.bottom_video, layout.split_ratio) == ("split", (1, 2, 3, 4), None, 0.55)
