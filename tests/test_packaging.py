"""Guards for files that have to stay in sync, and for how the tool is started."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from shorts_generator import __version__, cli

ROOT = Path(__file__).resolve().parent.parent


def requirement_lines(path: Path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-r"):
            out.append(re.sub(r"\s+", "", line))
    return sorted(out)


@pytest.fixture(scope="module")
def pyproject():
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_pyproject_dependencies_match_the_requirements_files(pyproject):
    project = pyproject["project"]
    assert sorted(re.sub(r"\s+", "", d) for d in project["dependencies"]) == requirement_lines(ROOT / "requirements.txt")
    local = sorted(re.sub(r"\s+", "", d) for d in project["optional-dependencies"]["local"])
    assert local == requirement_lines(ROOT / "requirements-local.txt")


def test_pyproject_declares_the_shorts_command_and_package_data(pyproject):
    assert pyproject["project"]["scripts"]["shorts"] == "shorts_generator.cli:main"
    assert "data/*" in pyproject["tool"]["setuptools"]["package-data"]["shorts_generator"]
    assert pyproject["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "shorts_generator.__version__"


def test_version_looks_like_a_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_the_bundled_settings_template_matches_env_example():
    bundled = (ROOT / "shorts_generator" / "data" / "env.example").read_text(encoding="utf-8")
    assert bundled == (ROOT / ".env.example").read_text(encoding="utf-8"), \
        "keep shorts_generator/data/env.example identical to .env.example"


def test_every_cli_flag_is_documented_in_the_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    flags = {opt for action in cli._build_parser()._actions for opt in action.option_strings if opt.startswith("--")}
    missing = sorted(f for f in flags - {"--help"} if f not in readme)
    assert not missing, f"flags missing from the README: {missing}"


def test_files_named_in_the_readme_structure_exist():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = readme[readme.index("## Project Structure"):readme.index("## Troubleshooting")]
    names = set(re.findall(r"[A-Za-z0-9_.\-]+\.(?:py|txt|sh|ps1|bat|cmd|command|example)\b", block))
    existing = {p.name for p in ROOT.rglob("*") if p.is_file() and ".venv" not in p.parts and ".git" not in p.parts}
    assert names, "no files found in the Project Structure block"
    assert not sorted(n for n in names if n not in existing), "README names files that do not exist"


# ------------------------------------------------------------------ installers and launchers

WINDOWS_SCRIPTS = ["installers/install.ps1", "Install-Windows.bat", "shorts.cmd"]
UNIX_SCRIPTS = ["installers/install.sh", "Install-Mac.command", "shorts"]


@pytest.mark.parametrize("name", WINDOWS_SCRIPTS)
def test_windows_scripts_use_crlf_and_plain_ascii(name):
    data = (ROOT / name).read_bytes()
    assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b""), f"{name} must use CRLF line endings"
    assert all(b < 128 for b in data), f"{name} must be ASCII (Windows PowerShell 5.1 reads it as ANSI)"


@pytest.mark.parametrize("name", UNIX_SCRIPTS)
def test_unix_scripts_use_lf(name):
    assert b"\r" not in (ROOT / name).read_bytes(), f"{name} must use LF line endings"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
@pytest.mark.parametrize("name", UNIX_SCRIPTS)
def test_unix_scripts_are_executable(name):
    assert os.access(ROOT / name, os.X_OK)


@pytest.mark.skipif(sys.platform == "win32" or not shutil.which("bash"), reason="needs bash")
@pytest.mark.parametrize("name", UNIX_SCRIPTS)
def test_unix_scripts_have_valid_shell_syntax(name):
    assert subprocess.run(["bash", "-n", str(ROOT / name)], capture_output=True).returncode == 0


def test_gitattributes_protects_line_endings():
    attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for pattern in ("*.bat -text", "*.cmd -text", "*.ps1 -text", "*.sh text eol=lf"):
        assert pattern in attrs


# ------------------------------------------------------------------ the three ways to start it

@pytest.mark.parametrize("args", [["main.py"], ["-m", "shorts_generator"]])
def test_version_runs_from_a_source_checkout(args):
    res = subprocess.run([sys.executable, *args, "--version"], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0 and res.stdout.strip() == f"shorts {__version__}"


def test_the_installed_command_is_registered_when_the_package_is_installed():
    from importlib import metadata

    try:
        metadata.distribution("ai-youtube-shorts-generator")
    except metadata.PackageNotFoundError:
        pytest.skip("package is not pip-installed in this environment")
    commands = {ep.name: ep.value for ep in metadata.entry_points(group="console_scripts")}
    assert commands.get("shorts") == "shorts_generator.cli:main"
