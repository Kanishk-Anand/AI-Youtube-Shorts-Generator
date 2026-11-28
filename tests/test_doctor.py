import collections
import types

import pytest

from shorts_generator import config, doctor

VI = collections.namedtuple("VI", "major minor micro")


def test_python_versions(monkeypatch):
    monkeypatch.setattr(doctor, "sys", types.SimpleNamespace(version_info=VI(3, 9, 0)))
    assert doctor.check_python()[0] == doctor.FAIL
    monkeypatch.setattr(doctor, "sys", types.SimpleNamespace(version_info=VI(3, 12, 1)))
    assert doctor.check_python()[0] == doctor.OK
    monkeypatch.setattr(doctor, "sys", types.SimpleNamespace(version_info=VI(3, 15, 2)))
    status, _, detail, fix = doctor.check_python()
    assert status == doctor.WARN and "wheels" in detail and "3.12" in fix


@pytest.mark.parametrize("os_name,expected", [("mac", "brew install ffmpeg"), ("windows", "winget install Gyan.FFmpeg")])
def test_missing_ffmpeg_is_a_failure_with_an_os_specific_fix(monkeypatch, os_name, expected):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    monkeypatch.setattr(doctor, "os_name", lambda: os_name)
    results = doctor.check_ffmpeg()
    assert results[0][0] == doctor.FAIL and expected in results[0][3]


def test_opencv_5_is_detected_as_incompatible(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "cv2", types.SimpleNamespace(__version__="5.1.0"))
    status, _, detail, fix = doctor.check_opencv_faces()
    assert status == doctor.FAIL and "CascadeClassifier" in detail and "<5" in fix


def test_muapi_key_states(monkeypatch):
    monkeypatch.setattr(config, "MUAPI_API_KEY", "")
    assert doctor.check_muapi()[0] == doctor.WARN
    monkeypatch.setattr(config, "MUAPI_API_KEY", "your_muapi_key_here")
    status, _, detail, _ = doctor.check_muapi()
    assert status == doctor.WARN and "placeholder" in detail
    monkeypatch.setattr(config, "MUAPI_API_KEY", "a" * 30)
    assert doctor.check_muapi()[0] == doctor.OK


def test_settings_file_report(monkeypatch, isolated_config):
    monkeypatch.setattr(config, "LOADED_ENV_FILES", [])
    status, _, _, fix = doctor.check_config()
    assert status == doctor.WARN and "--init-config" in fix
    monkeypatch.setattr(config, "LOADED_ENV_FILES", [isolated_config / ".env"])
    assert doctor.check_config()[0] == doctor.OK


def test_output_folder_must_be_writable(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOCAL_OUTPUT_DIR", str(tmp_path / "out"))
    assert doctor.check_output_dir()[0] == doctor.OK
    blocker = tmp_path / "a file"
    blocker.write_text("x")
    monkeypatch.setattr(config, "LOCAL_OUTPUT_DIR", str(blocker / "inside"))   # a folder can't live inside a file
    assert doctor.check_output_dir()[0] == doctor.FAIL


def fake_checks(monkeypatch, status):
    for name in ("check_python", "check_venv", "check_opencv_faces", "check_av_compat", "check_output_dir",
                 "check_config", "check_whisper_cache", "check_llm", "check_muapi"):
        monkeypatch.setattr(doctor, name, lambda: (doctor.OK, "x", "", ""))
    monkeypatch.setattr(doctor, "check_ffmpeg", lambda: [(status, "ffmpeg", "d", "fix it")])
    monkeypatch.setattr(doctor, "check_imports", lambda: [])
    monkeypatch.setattr(doctor, "check_paths", lambda: [])


def test_doctor_exit_code_reflects_failures(monkeypatch, capsys):
    fake_checks(monkeypatch, doctor.OK)
    assert doctor.run_doctor() == 0
    assert "looks good" in capsys.readouterr().out
    fake_checks(monkeypatch, doctor.FAIL)
    assert doctor.run_doctor() == 1
    out = capsys.readouterr().out
    assert "[FAIL] ffmpeg" in out and "fix: fix it" in out


def test_doctor_output_is_plain_ascii(monkeypatch, capsys):
    fake_checks(monkeypatch, doctor.WARN)
    doctor.run_doctor()
    assert capsys.readouterr().out.isascii()      # renders in any Windows or macOS terminal
