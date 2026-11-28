import sys
import threading
import time

import pytest

from shorts_generator import jobs, pipeline
from shorts_generator.jobs import CancelledError, Job, JobContext, ProgressEvent
from shorts_generator.local.system import run_cancellable


# ------------------------------------------------------------------ events and context

def test_event_fraction_is_clamped_and_optional():
    assert ProgressEvent("s", "progress", current=5, total=10).fraction == 0.5
    assert ProgressEvent("s", "progress", current=50, total=10).fraction == 1.0
    assert ProgressEvent("s", "progress", current=1, total=0).fraction is None
    assert ProgressEvent("s", "start").fraction is None
    d = ProgressEvent("s", "progress", "m", 1, 4, {"k": "v"}).to_dict()
    assert d["fraction"] == 0.25 and d["data"] == {"k": "v"} and d["stage"] == "s"


def test_helpers_do_nothing_outside_a_job():
    assert jobs.current() is None
    jobs.emit("download", "start")      # no listener, no error
    jobs.checkpoint()
    jobs.sleep(0)


def test_emit_reaches_the_active_context_and_a_broken_listener_is_ignored():
    seen = []

    def listener(event):
        seen.append(event)
        raise RuntimeError("listener bug")

    with jobs.activate(JobContext(listener)):
        jobs.emit("render", "progress", "hello", current=1, total=2, clip=1)
    assert seen[0].stage == "render" and seen[0].data == {"clip": 1} and seen[0].message == "hello"
    assert jobs.current() is None        # context restored


def test_checkpoint_raises_once_cancelled_and_cancel_is_not_an_exception():
    ev = threading.Event()
    with jobs.activate(JobContext(cancel=ev)):
        jobs.checkpoint()
        ev.set()
        with pytest.raises(CancelledError):
            jobs.checkpoint()
    # A stray `except Exception` must not be able to swallow a cancel.
    assert not issubclass(CancelledError, Exception)


def test_sleep_wakes_up_immediately_on_cancel():
    ev = threading.Event()
    threading.Timer(0.1, ev.set).start()
    with jobs.activate(JobContext(cancel=ev)):
        start = time.time()
        with pytest.raises(CancelledError):
            jobs.sleep(30)
    assert time.time() - start < 5


# ------------------------------------------------------------------ Job

def test_job_returns_the_result_and_streams_events():
    def work(ctx):
        jobs.emit("download", "start")
        jobs.emit("download", "done")
        return {"answer": 42}

    job = Job(work).start()
    assert [(e.stage, e.status) for e in job.events()] == [("download", "start"), ("download", "done")]
    assert job.result() == {"answer": 42} and job.state == "done"


def test_job_failure_is_raised_from_result():
    def work(ctx):
        raise ValueError("bad input")

    job = Job(work).start()
    with pytest.raises(ValueError, match="bad input"):
        job.result(timeout=5)
    assert job.state == "failed"


def test_job_cancel_stops_a_long_loop():
    def work(ctx):
        while True:
            jobs.checkpoint()
            time.sleep(0.01)

    job = Job(work).start()
    time.sleep(0.1)
    job.cancel()
    assert job.wait(5)
    assert job.state == "cancelled" and job.cancel_requested
    with pytest.raises(CancelledError):
        job.result()


def test_completion_does_not_depend_on_thread_liveness(monkeypatch):
    """A Ctrl+C inside Thread.join() can make is_alive() report False while the thread still runs.
    wait()/result() must keep waiting anyway (this caused result() to return None after a cancel)."""
    release = threading.Event()
    job = Job(lambda ctx: release.wait(5) and "finished").start()
    monkeypatch.setattr(job._thread, "is_alive", lambda: False)    # the lie
    try:
        assert job.wait(0.05) is False                              # still running
        with pytest.raises(TimeoutError):
            job.result(timeout=0.05)
    finally:
        release.set()
    assert job.wait(5) and job.result() == "finished"


def test_a_worker_that_raises_a_non_exception_is_recorded_not_lost():
    def work(ctx):
        raise SystemExit(3)

    job = Job(work).start()
    assert job.wait(5) and job.state == "failed"
    with pytest.raises(SystemExit):
        job.result()


def test_result_times_out_while_running():
    release = threading.Event()
    job = Job(lambda ctx: release.wait(5)).start()
    try:
        with pytest.raises(TimeoutError):
            job.result(timeout=0.05)
    finally:
        release.set()
        job.wait(5)


def test_listener_and_events_both_receive_everything():
    heard = []
    job = Job(lambda ctx: jobs.emit("render", "done"), on_event=heard.append).start()
    assert len(list(job.events())) == 1 and len(heard) == 1


# ------------------------------------------------------------------ cancellable subprocess

def test_run_cancellable_returns_output():
    res = run_cancellable([sys.executable, "-c", "print('hi'); import sys; print('err', file=sys.stderr)"])
    assert res.returncode == 0 and res.stdout.strip() == "hi" and "err" in res.stderr


def test_cancel_kills_a_running_process_quickly():
    ev = threading.Event()
    threading.Timer(0.3, ev.set).start()
    with jobs.activate(JobContext(cancel=ev)):
        start = time.time()
        with pytest.raises(CancelledError):
            run_cancellable([sys.executable, "-c", "import time; time.sleep(60)"])
    assert time.time() - start < 10


# ------------------------------------------------------------------ the pipeline as a job

@pytest.fixture
def stub_local_pipeline(monkeypatch, tmp_path):
    """Replace every slow stage of local mode with an instant stub and record which ones ran."""
    from shorts_generator.local import clipper, downloader, llm, system, transcriber

    ran = []
    transcript = {"duration": 100.0, "segments": [{"start": 0.0, "end": 5.0, "text": "hi"}]}
    candidates = [{"title": "t", "start_time": 0.0, "end_time": 30.0, "score": 90,
                   "hook_sentence": "h", "virality_reason": "r"}]

    monkeypatch.setattr(system, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr(llm, "validate", lambda: None)
    monkeypatch.setattr(llm, "describe", lambda: "stub (model)")
    monkeypatch.setattr(downloader, "download_youtube_local", lambda url, fmt="720": ran.append("download") or str(tmp_path / "v.mp4"))
    monkeypatch.setattr(transcriber, "transcribe_local", lambda p, language=None: ran.append("transcribe") or transcript)
    monkeypatch.setattr(pipeline, "get_highlights", lambda t, num_clips, llm_fn: ran.append("highlights") or {"highlights": candidates})
    monkeypatch.setattr(clipper, "crop_highlights_local",
                        lambda src, top, aspect_ratio, layout: ran.append("render") or [{**top[0], "clip_url": "out.mp4"}])
    return ran


def test_generate_shorts_reports_progress(stub_local_pipeline):
    events = []
    result = pipeline.generate_shorts("https://youtu.be/x", mode="local", on_event=events.append)
    assert stub_local_pipeline == ["download", "transcribe", "highlights", "render"]
    assert result["shorts"][0]["clip_url"] == "out.mp4"
    kinds = [(e.stage, e.status) for e in events]
    assert kinds[0] == ("pipeline", "start") and kinds[-1] == ("pipeline", "finished")
    assert ("pipeline", "done") in kinds


def test_cancel_between_stages_stops_the_rest(stub_local_pipeline, monkeypatch):
    from shorts_generator.local import transcriber

    cancel = threading.Event()
    real = transcriber.transcribe_local

    def transcribe_then_cancel(path, language=None):
        out = real(path, language=language)
        cancel.set()                       # the user presses cancel while transcribing finishes
        return out

    monkeypatch.setattr(transcriber, "transcribe_local", transcribe_then_cancel)
    events = []
    with pytest.raises(CancelledError):
        pipeline.generate_shorts("https://youtu.be/x", mode="local", on_event=events.append, cancel=cancel)
    assert stub_local_pipeline == ["download", "transcribe"]       # highlights and render never ran
    assert events[-1].stage == "pipeline" and events[-1].status == "cancelled"


def test_errors_are_reported_as_events_and_still_raised(stub_local_pipeline, monkeypatch):
    from shorts_generator.local import transcriber

    monkeypatch.setattr(transcriber, "transcribe_local", lambda p, language=None: {"duration": 1, "segments": []})
    events = []
    with pytest.raises(RuntimeError, match="no segments"):
        pipeline.generate_shorts("https://youtu.be/x", mode="local", on_event=events.append)
    assert events[-1].status == "error" and "no segments" in events[-1].message


def test_start_job_runs_in_the_background_and_can_be_cancelled(stub_local_pipeline, monkeypatch):
    job = pipeline.start_job("https://youtu.be/x", mode="local")
    result = job.result(timeout=10)
    assert result["mode"] == "local"
    assert any(e.status == "finished" for e in job.events())

    # A job cancelled before its first checkpoint never starts the real work.
    stub_local_pipeline.clear()
    blocker = threading.Event()
    from shorts_generator.local import downloader

    def slow_download(url, fmt="720"):
        blocker.wait(5)
        jobs.checkpoint()
        return "x"

    monkeypatch.setattr(downloader, "download_youtube_local", slow_download)
    job2 = pipeline.start_job("https://youtu.be/x", mode="local")
    job2.cancel()
    blocker.set()
    assert job2.wait(10) and job2.state == "cancelled"
    assert "transcribe" not in stub_local_pipeline


def test_api_mode_without_a_key_fails_cleanly():
    events = []
    with pytest.raises(RuntimeError, match="MUAPI_API_KEY"):
        pipeline.generate_shorts("https://youtu.be/x", mode="api", on_event=events.append)
    assert events[-1].status == "error"


def test_layout_is_rejected_outside_local_mode():
    from shorts_generator.layout import Layout

    with pytest.raises(ValueError, match="only apply to --mode local"):
        pipeline.generate_shorts("https://youtu.be/x", mode="api", layout=Layout(mode="center"))
