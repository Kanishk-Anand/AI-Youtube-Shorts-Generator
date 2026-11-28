import os
import threading

import pytest

from shorts_generator import jobs
from shorts_generator.jobs import CancelledError, JobContext
from shorts_generator.layout import Layout
from shorts_generator.local import clipper
from shorts_generator.local.system import run_text


# ------------------------------------------------------------------ pure helpers

def test_aspect_ratio_parsing():
    assert clipper._ratio("9:16") == 9 / 16
    assert clipper._ratio("1:1") == 1.0
    assert clipper._ratio("garbage") == 9 / 16   # falls back to vertical


def test_fill_gaps_interpolates_and_reports_empty():
    np = pytest.importorskip("numpy")
    assert list(clipper._fill_gaps(np.array([1.0, np.nan, 3.0]))) == [1.0, 2.0, 3.0]
    assert clipper._fill_gaps(np.array([np.nan, np.nan])) is None


def test_deadzone_holds_still_until_the_target_moves_far_enough():
    np = pytest.importorskip("numpy")
    out = clipper._hold_in_deadzone(np.array([100.0, 103, 98, 101, 150, 151]), 10)
    assert list(out[:4]) == [100.0] * 4         # jitter inside the zone is ignored
    assert out[4] == 140.0 and out[5] == 141.0  # a real move is followed at the zone edge


def test_smoothing_removes_flip_flopping_between_two_faces():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(0)
    raw = np.where(np.arange(200) % 2 == 0, 100.0, 300.0) + rng.normal(0, 5, 200)  # alternates every sample
    raw[::7] = np.nan                                                              # plus detector dropouts
    path = clipper._smooth_path(raw, sample_fps=10, deadzone=30)
    assert path is not None and len(path) == 200
    # The raw input jumps 200 px every sample; the camera must move at most 5% of that per sample.
    assert np.abs(np.diff(path)).max() < 10


def test_no_detections_means_no_path():
    np = pytest.importorskip("numpy")
    assert clipper._smooth_path(np.full(30, np.nan), 10, 30) is None


# ------------------------------------------------------------------ real ffmpeg renders

def audio_streams(path):
    out = run_text(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name",
                    "-of", "csv=p=0", str(path)]).stdout
    return [line for line in out.splitlines() if line.strip()]


@pytest.mark.ffmpeg
def test_probe_reads_size_fps_and_duration(synthetic_video):
    info = clipper._probe(str(synthetic_video))
    assert (info["width"], info["height"]) == (320, 180)
    assert 29 <= info["fps"] <= 31 and 5.5 <= info["duration"] <= 6.5


@pytest.mark.ffmpeg
def test_probe_reports_unreadable_files_clearly(tmp_path):
    bad = tmp_path / "not a video.mp4"
    bad.write_bytes(b"this is not media")
    with pytest.raises(RuntimeError, match="ffprobe could not read"):
        clipper._probe(str(bad))


@pytest.mark.ffmpeg
def test_split_with_a_facecam_box_makes_a_stacked_vertical_clip_with_audio(synthetic_video, tmp_path):
    out = tmp_path / "out dir" / "split.mp4"
    out.parent.mkdir()
    layout = Layout(mode="split", facecam=(0, 90, 120, 90))
    clipper._render_split(str(synthetic_video), 1.0, 4.0, "9:16", str(out), layout)
    info = clipper._probe(str(out))
    assert (info["width"], info["height"]) == (100, 180)           # 9:16 at the source height
    assert 2.8 <= info["duration"] <= 3.3
    assert audio_streams(out), "the source audio must be kept"


@pytest.mark.ffmpeg
def test_split_with_a_shorter_bottom_video_loops_it(synthetic_video, tmp_path):
    filler = tmp_path / "filler.mp4"
    run_text(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=15:duration=1",
              "-pix_fmt", "yuv420p", str(filler)], check=True)                         # 1s, clip below is 4s
    out = tmp_path / "split.mp4"
    clipper._render_split(str(synthetic_video), 0.0, 4.0, "9:16", str(out), Layout(mode="split", bottom_video=str(filler)))
    assert 3.7 <= clipper._probe(str(out))["duration"] <= 4.3


@pytest.mark.ffmpeg
def test_facecam_box_outside_the_video_is_a_clear_error(synthetic_video, tmp_path):
    with pytest.raises(ValueError, match="falls outside"):
        clipper._render_split(str(synthetic_video), 0, 3, "9:16", str(tmp_path / "x.mp4"),
                              Layout(mode="split", facecam=(300, 170, 100, 100)))


@pytest.mark.ffmpeg
def test_center_mode_renders_every_clip_and_reports_progress(synthetic_video, tmp_path):
    pytest.importorskip("cv2")
    highlights = [{"title": "one", "start_time": 0.0, "end_time": 3.0, "score": 1},
                  {"title": "two", "start_time": 2.0, "end_time": 5.0, "score": 1}]
    events = []
    with jobs.activate(JobContext(events.append)):
        results = clipper.crop_highlights_local(str(synthetic_video), highlights, out_dir=str(tmp_path / "out"),
                                                layout=Layout(mode="center"))
    assert [os.path.basename(r["clip_url"]) for r in results] == ["short_01.mp4", "short_02.mp4"]
    assert all(os.path.getsize(r["clip_url"]) > 1000 for r in results)
    assert clipper._probe(results[0]["clip_url"])["width"] == 100
    assert [e.status for e in events if e.stage == "render"][0] == "start"
    assert events[-1].stage == "render" and events[-1].status == "done"
    assert not [p for p in os.listdir(tmp_path / "out") if p.endswith(".cut.mp4")]   # temp files cleaned up


@pytest.mark.ffmpeg
def test_face_mode_runs_without_a_face_and_falls_back_to_the_centre(synthetic_video, tmp_path):
    pytest.importorskip("cv2")
    res = clipper.crop_highlights_local(str(synthetic_video), [{"title": "t", "start_time": 0.0, "end_time": 3.0, "score": 1}],
                                        out_dir=str(tmp_path), layout=Layout(mode="face"))
    assert res[0]["clip_url"] and clipper._probe(res[0]["clip_url"])["height"] == 180


@pytest.mark.ffmpeg
def test_cancel_before_rendering_leaves_no_files_behind(synthetic_video, tmp_path):
    cancel = threading.Event()
    cancel.set()
    with jobs.activate(JobContext(cancel=cancel)):
        with pytest.raises(CancelledError):
            clipper.crop_highlights_local(str(synthetic_video), [{"title": "t", "start_time": 0.0, "end_time": 3.0}],
                                          out_dir=str(tmp_path / "out"), layout=Layout(mode="center"))
    assert not list((tmp_path / "out").glob("*"))


@pytest.mark.ffmpeg
@pytest.mark.parametrize("failure", [CancelledError, RuntimeError])
def test_a_half_written_clip_is_removed_when_rendering_is_cancelled_or_fails(synthetic_video, tmp_path, monkeypatch, failure):
    out = tmp_path / "short.mp4"

    def half_done(in_path, out_path, aspect_ratio, mode="face"):
        with open(out_path, "wb") as f:       # the render got part-way, then stopped
            f.write(b"partial data")
        raise failure("stopped")

    monkeypatch.setattr(clipper, "_reframe_vertical", half_done)
    with pytest.raises(failure):
        clipper.crop_clip_local(str(synthetic_video), 0.0, 3.0, "9:16", str(out), Layout(mode="center"))
    assert not out.exists(), "a partial clip must never be left behind"
    assert not (tmp_path / "short.mp4.cut.mp4").exists(), "the temporary cut must be cleaned up too"


@pytest.mark.ffmpeg
def test_one_bad_clip_does_not_stop_the_others(synthetic_video, tmp_path):
    highlights = [{"title": "ok", "start_time": 0.0, "end_time": 3.0}, {"title": "ok2", "start_time": 1.0, "end_time": 4.0}]
    res = clipper.crop_highlights_local(str(synthetic_video), highlights, out_dir=str(tmp_path), layout=Layout(mode="center"))
    assert all(r.get("clip_url") for r in res)
