import os
import shutil
import sys
import types

import pytest

from shorts_generator.local import downloader, system


@pytest.mark.parametrize("os_name,expected", [
    ("mac", "brew install ffmpeg"), ("windows", "winget install Gyan.FFmpeg"), ("linux", "apt install ffmpeg"),
])
def test_missing_ffmpeg_message_has_the_right_install_command(monkeypatch, os_name, expected):
    monkeypatch.setattr(system.shutil, "which", lambda name: None)
    monkeypatch.setattr(system, "os_name", lambda: os_name)
    with pytest.raises(RuntimeError, match="ffmpeg and ffprobe not found") as err:
        system.ensure_ffmpeg()
    assert expected in str(err.value)


def test_ensure_ffmpeg_is_quiet_when_both_tools_exist(monkeypatch):
    monkeypatch.setattr(system.shutil, "which", lambda name: "/usr/bin/" + name)
    system.ensure_ffmpeg()


def test_run_text_decodes_non_ascii_output_as_utf8():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    res = system.run_text([sys.executable, "-c", "print('vídeo ビデオ …')"], env=env)
    assert res.stdout.strip() == "vídeo ビデオ …"


def test_run_text_replaces_undecodable_bytes_instead_of_crashing():
    res = system.run_text([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'ok \\xff\\xfe end')"])
    assert res.stdout.startswith("ok") and res.stdout.endswith("end")


def test_os_name_is_one_of_three():
    assert system.os_name() in {"mac", "windows", "linux"}


# ------------------------------------------------------------------ local file handling

def test_plain_paths_with_spaces_and_unicode_resolve(tmp_path):
    f = tmp_path / "dir with spaces" / "vídeo 01.mp4"
    f.parent.mkdir()
    f.write_bytes(b"x")
    assert downloader._resolve_local_path(str(f)) == str(f.resolve())


def test_a_missing_local_path_is_an_error_not_a_url(tmp_path):
    with pytest.raises(RuntimeError, match="does not exist"):
        downloader._resolve_local_path(str(tmp_path / "nope.mp4"))


def test_file_urls_go_through_url2pathname(monkeypatch, tmp_path):
    f = tmp_path / "a b.mp4"
    f.write_bytes(b"x")
    seen = []
    monkeypatch.setattr(downloader, "url2pathname", lambda p: seen.append(p) or str(f))
    assert downloader._resolve_local_path("file:///C:/Users/me/a%20b.mp4") == str(f.resolve())
    assert seen == ["/C:/Users/me/a%20b.mp4"]


def test_windows_file_urls_convert_to_drive_paths():
    import nturl2path

    assert nturl2path.url2pathname("/C:/Users/me/My%20Videos/a.mp4") == r"C:\Users\me\My Videos\a.mp4"


def test_remote_non_youtube_urls_are_rejected():
    with pytest.raises(ValueError):
        downloader.download_youtube_local("https://evil.example/video.mp4")
    with pytest.raises(ValueError):
        downloader.download_youtube_local("http://www.youtube.com/watch?v=abc")


@pytest.mark.parametrize("url,vid", [
    ("https://www.youtube.com/watch?v=abc123", "abc123"),
    ("https://youtu.be/abc123", "abc123"),
    ("https://www.youtube.com/shorts/abc123", "abc123"),
    ("https://youtube.com.evil.com/watch?v=abc123", None),
    ("https://example.com/watch?v=abc123", None),
])
def test_video_id_extraction_only_trusts_real_youtube_hosts(url, vid):
    assert downloader._extract_youtube_video_id(url) == vid
