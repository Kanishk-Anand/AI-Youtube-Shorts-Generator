@echo off
rem Double-click this file to install. If Windows warns that it protected your PC,
rem click "More info", then "Run anyway".
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installers\install.ps1"
echo.
pause
