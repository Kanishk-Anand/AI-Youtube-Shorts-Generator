# AI YouTube Shorts Generator: Windows installer.
#
# Safe to re-run. Installs into this folder (.venv) and needs no admin rights, except where
# winget asks for them (ffmpeg). Usually started by double-clicking Install-Windows.bat.
# Windows PowerShell 5.1 turns native-command stderr (uv progress output) into errors under "Stop",
# so errors are checked explicitly: $LASTEXITCODE for programs, -ErrorAction Stop on cmdlets.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Say($m)  { Write-Host ""; Write-Host "==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  ok  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host ""; Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }
function Has($n)  { return [bool](Get-Command $n -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

$PyVersion = "3.12"

# ---------------------------------------------------------------- 1. uv
Say "1/5  Python tooling (uv)"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
if (-not (Has uv)) {
    Write-Host "  Installing uv with its official installer (https://astral.sh/uv)..."
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    if (-not (Has uv)) { Die "uv was installed but is not on PATH yet. Open a new terminal and run Install-Windows.bat again." }
}
Ok ("uv " + ((uv --version) -replace "^uv\s+", ""))

# ---------------------------------------------------------------- 2. Python environment
Say "2/5  Python $PyVersion environment (.venv)"
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $VenvPy) {
    $found = (& $VenvPy -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null)
    if ($found -in @("3.10", "3.11", "3.12", "3.13")) {
        Ok "reusing the existing .venv (Python $found)"
    } else {
        Warn "the existing .venv uses Python $found, which this tool does not support; recreating it"
        Remove-Item -Recurse -Force (Join-Path $Root ".venv") -ErrorAction Stop
    }
}
if (-not (Test-Path $VenvPy)) {
    uv venv --python $PyVersion (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPy)) {
        Die "could not create a Python $PyVersion environment. Check your internet connection and try again."
    }
    Ok ("created .venv with Python " + (& $VenvPy -c "import platform; print(platform.python_version())"))
}

# ---------------------------------------------------------------- 3. dependencies
Say "3/5  Python packages"
# Some packages are large (OpenCV is ~45 MB), so allow slow connections and retry once.
if (-not $env:UV_HTTP_TIMEOUT) { $env:UV_HTTP_TIMEOUT = "180" }
$Req = Join-Path $Root "requirements-local.txt"
uv pip install --python $VenvPy -r $Req
if ($LASTEXITCODE -ne 0) {
    Warn "the download failed; retrying once..."
    uv pip install --python $VenvPy -r $Req
    if ($LASTEXITCODE -ne 0) { Die "installing the Python packages failed. Check your internet connection and run Install-Windows.bat again." }
}
Ok "packages installed"

# ---------------------------------------------------------------- 4. ffmpeg
Say "4/5  ffmpeg"
if ((Has ffmpeg) -and (Has ffprobe)) {
    Ok "ffmpeg already installed"
} else {
    if (Has winget) {
        Write-Host "  Installing ffmpeg with winget (this can take a few minutes)..."
        winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
        Refresh-Path
    } else {
        Warn "winget was not found, so ffmpeg could not be installed automatically."
    }
    if ((Has ffmpeg) -and (Has ffprobe)) {
        Ok "ffmpeg installed"
    } else {
        Warn "ffmpeg is not available in this window yet. If you just installed it, open a new terminal; otherwise run:  winget install Gyan.FFmpeg   (or: choco install ffmpeg)"
    }
}

# ---------------------------------------------------------------- 5. config, command, check
Say "5/5  Settings and the 'shorts' command"
$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Root ".env.example") $EnvFile -ErrorAction Stop
    Ok "created .env (edit it to choose your LLM and settings)"
} else {
    Ok ".env already exists, left unchanged"
}

Say "Checking your setup"
& $VenvPy (Join-Path $Root "main.py") --doctor
$status = $LASTEXITCODE

Write-Host ""
if ($status -eq 0) { Write-Host "Installed. Try it:" -ForegroundColor Green }
else { Write-Host "Installed, but the checks above found problems to fix. Then try:" -ForegroundColor Yellow }
Write-Host @"

    .\shorts.cmd "https://www.youtube.com/watch?v=VIDEO_ID" --mode local
    .\shorts.cmd path\to\video.mp4 --critique

  Run these from this folder: $Root
  (To use 'shorts' from anywhere, add that folder to your PATH.)

  For fully offline use, install Ollama (https://ollama.com/download), then:
    ollama pull qwen3:30b-a3b
  and set  LLM_PROVIDER=ollama  and  OLLAMA_MODEL=qwen3:30b-a3b  in .env.
"@
exit $status
