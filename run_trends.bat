@echo off
REM IT Trend Radar — one-shot runner for Windows Task Scheduler.
REM Task Scheduler action:
REM   Program/script: d:\CODE\OS\job-radar\run_trends.bat
REM   Start in:       d:\CODE\OS\job-radar

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main_trends.py >> "logs\trends.log" 2>&1
) else (
    python main_trends.py >> "logs\trends.log" 2>&1
)
