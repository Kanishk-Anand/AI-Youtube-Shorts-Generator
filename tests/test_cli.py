import json

import pytest

from shorts_generator import cli, jobs, paths
from shorts_generator.jobs import CancelledError, Job, ProgressEvent


def run(argv):
    return cli.main(argv)


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        run(["--version"])
    assert exit_info.value.code == 0 and capsys.readouterr().out.startswith("shorts ")


def test_a_url_is_required(capsys):
    with pytest.raises(SystemExit) as exit_info:
        run([])
    assert exit_info.value.code == 2 and "required" in capsys.readouterr().err


def test_config_shows_every_place_settings_come_from(isolated_config, capsys):
    assert run(["--config"]) == 0
    out = capsys.readouterr().out
    assert "environment variables" in out and str(isolated_config) in out and "--init-config" in out


def test_init_config_creates_the_file_and_is_idempotent(isolated_config, capsys):
    assert run(["--init-config"]) == 0
    assert (isolated_config / ".env").is_file() and "Created" in capsys.readouterr().out
    (isolated_config / ".env").write_text("EDITED=1\n", encoding="utf-8")
    assert run(["--init-config"]) == 0
    assert "already exists" in capsys.readouterr().out
    assert (isolated_config / ".env").read_text(encoding="utf-8") == "EDITED=1\n"


def test_doctor_flag_returns_the_doctors_exit_code(monkeypatch):
    from shorts_generator import doctor

    monkeypatch.setattr(doctor, "run_doctor", lambda: 7)
    assert run(["--doctor"]) == 7


def test_llm_flags_are_rejected_in_api_mode(capsys):
    assert run(["https://youtu.be/x", "--llm", "ollama"]) == 2
    assert "only apply to --mode local" in capsys.readouterr().err


def test_bad_facecam_is_reported_before_any_work(capsys):
    assert run(["video.mp4", "--mode", "local", "--facecam", "1,2,3"]) == 2
    assert "facecam" in capsys.readouterr().err


# ------------------------------------------------------------------ running a job from the CLI

RESULT = {"mode": "local", "source_video_url": "/v.mp4", "transcript": {"segments": []},
          "highlights": [{}], "shorts": [{"title": "Tést ビデオ", "score": 91, "start_time": 1.0, "end_time": 31.0,
                                           "hook_sentence": "Wow", "clip_url": "/out/short_01.mp4"}]}


def fake_start_job(work):
    def start(url, on_event=None, **kwargs):
        start.kwargs = kwargs
        return Job(work, on_event=on_event).start()
    return start


def test_a_successful_run_prints_the_result_and_writes_utf8_json(monkeypatch, tmp_path, capsys):
    def work(ctx):
        jobs.emit("transcribe", "progress", current=5, total=10)
        jobs.emit("transcribe", "progress", current=10, total=10)
        return RESULT

    monkeypatch.setattr(cli, "start_job", fake_start_job(work))
    out_file = tmp_path / "result.json"
    assert run(["video.mp4", "--mode", "local", "--num-clips", "2", "--output-json", str(out_file)]) == 0
    out = capsys.readouterr().out
    assert "score=91" in out and "/out/short_01.mp4" in out and "[transcribe] 50%" in out
    assert json.loads(out_file.read_text(encoding="utf-8"))["shorts"][0]["title"] == "Tést ビデオ"
    assert cli.start_job.kwargs["num_clips"] == 2 and cli.start_job.kwargs["mode"] == "local"


def test_layout_flags_are_passed_through(monkeypatch):
    monkeypatch.setattr(cli, "start_job", fake_start_job(lambda ctx: RESULT))
    run(["video.mp4", "--mode", "local", "--layout", "center"])
    assert cli.start_job.kwargs["layout"].mode == "center"


def test_a_failed_job_exits_1_with_the_reason(monkeypatch, capsys):
    def work(ctx):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(cli, "start_job", fake_start_job(work))
    assert run(["video.mp4", "--mode", "local"]) == 1
    assert "FAILED: ffmpeg exploded" in capsys.readouterr().err


def test_a_cancelled_job_exits_130(monkeypatch, capsys):
    def work(ctx):
        raise CancelledError()

    monkeypatch.setattr(cli, "start_job", fake_start_job(work))
    assert run(["video.mp4", "--mode", "local"]) == 130
    assert "Cancelled" in capsys.readouterr().err


def test_ctrl_c_cancels_the_job_cleanly(monkeypatch, capsys):
    started = []

    def work(ctx):
        started.append(1)
        while True:
            jobs.checkpoint()
            import time
            time.sleep(0.01)

    job = Job(work).start()
    real_wait = job.wait
    state = {"interrupted": False}

    def wait_then_interrupt(timeout=None):
        if started and not state["interrupted"]:
            state["interrupted"] = True
            raise KeyboardInterrupt
        return real_wait(timeout)

    monkeypatch.setattr(job, "wait", wait_then_interrupt)
    with pytest.raises(CancelledError):
        cli._wait(job)
    assert job.cancel_requested and "Cancelling" in capsys.readouterr().out


def test_progress_printer_prints_every_ten_percent_and_warnings(capsys):
    printer = cli._ProgressPrinter()
    for i in range(0, 101):
        printer(ProgressEvent("download", "progress", current=i, total=100))
    printer(ProgressEvent("render", "warn", "Clip 2 failed"))
    lines = [line.strip() for line in capsys.readouterr().out.splitlines()]
    assert lines[0] == "[download] 0%" and lines[-2] == "[download] 100%" and len(lines) == 12
    assert lines[-1] == "[render] Clip 2 failed"
