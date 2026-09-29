@echo off
REM Job Radar — one-shot runner for Windows Task Scheduler.
REM Task Scheduler action:
REM   Program/script: d:\CODE\OS\job-radar\run.bat
REM   Start in:       d:\CODE\OS\job-radar

cd /d "%~dp0"

REM Use the local venv if it exists, otherwise fall back to system python.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py >> "logs\radar.log" 2>&1
) else (
    python main.py >> "logs\radar.log" 2>&1
)
