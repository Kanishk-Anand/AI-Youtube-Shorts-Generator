@echo off
rem Launcher: runs the tool with its own Python environment.
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Not installed yet. Double-click Install-Windows.bat first.
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %*
