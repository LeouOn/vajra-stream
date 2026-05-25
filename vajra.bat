@echo off
REM
REM Vajra Stream - Windows Launcher
REM Sacred Technology for Healing & Liberation
REM

SETLOCAL EnableDelayedExpansion

cd /d "%~dp0"

REM 1. Check if virtual environment exists
IF EXIST ".venv\Scripts\python.exe" (
    SET "PYTHON_EXEC=.venv\Scripts\python.exe"
    echo [OK] Found virtual environment Python at .venv\Scripts\python.exe
) ELSE (
    echo [WARN] Virtual environment .venv not found.
    echo Attempting to create virtual environment...
    python -m venv .venv
    IF EXIST ".venv\Scripts\python.exe" (
        SET "PYTHON_EXEC=.venv\Scripts\python.exe"
        echo [OK] Created virtual environment successfully.
    ) ELSE (
        SET "PYTHON_EXEC=python"
        echo [WARN] Could not create virtual environment. Falling back to system Python.
    )
)

echo [OK] Launching Vajra.Stream with: !PYTHON_EXEC!
echo.

REM 2. Run consolidated launcher with pre-flight check
"!PYTHON_EXEC!" "%~dp0run.py" %*

ENDLOCAL
