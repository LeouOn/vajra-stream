@echo off
title Vajra.Stream - Headless ComfyUI API Launcher
color 0B

echo ====================================================================
echo   🔱 Vajra.Stream — Headless ComfyUI API Service Launcher 🔱
echo ====================================================================
echo.
echo This script starts ComfyUI as an isolated API microservice.
echo It enables --api-only mode to skip the Electron frontend browser
echo window, saving RAM/VRAM for Vajra.Stream sigil generation.
echo.

REM Define paths
set "DESKTOP_PATH=C:\Users\Y\AppData\Local\Programs\ComfyUI"
set "PORTABLE_PATH_1=C:\ComfyUI_windows_portable"
set "PORTABLE_PATH_2=..\ComfyUI_windows_portable"

REM Auto-detect installation type
if exist "%DESKTOP_PATH%\resources\ComfyUI\main.py" (
    set "COMFY_TYPE=desktop"
    set "RUN_DIR=%DESKTOP_PATH%\resources\ComfyUI"
    set "RUNNER=..\uv\win\uv.exe run main.py"
    echo [OK] Detected ComfyUI Desktop Installation in AppData.
    goto :select_hardware
)

if exist "%PORTABLE_PATH_1%\ComfyUI\main.py" (
    set "COMFY_TYPE=portable"
    set "RUN_DIR=%PORTABLE_PATH_1%"
    set "RUNNER=.\python_embeded\python.exe -s ComfyUI\main.py"
    echo [OK] Detected ComfyUI Portable Installation at C:\ComfyUI_windows_portable.
    goto :select_hardware
)

if exist "%PORTABLE_PATH_2%\ComfyUI\main.py" (
    set "COMFY_TYPE=portable"
    set "RUN_DIR=%PORTABLE_PATH_2%"
    set "RUNNER=.\python_embeded\python.exe -s ComfyUI\main.py"
    echo [OK] Detected ComfyUI Portable Installation in adjacent directory.
    goto :select_hardware
)

echo [WARNING] Could not auto-detect ComfyUI main directory.
echo.
echo [1] Use ComfyUI Desktop (AppData default path)
echo [2] Use ComfyUI Portable (Specify custom path)
echo.
set /p path_choice="Select installation type [1-2]: "

if "%path_choice%"=="1" (
    set "COMFY_TYPE=desktop"
    set "RUN_DIR=%DESKTOP_PATH%\resources\ComfyUI"
    set "RUNNER=..\uv\win\uv.exe run main.py"
) else (
    set /p custom_path="Enter full path to ComfyUI folder (e.g. D:\ComfyUI): "
    set "COMFY_TYPE=portable"
    set "RUN_DIR=%custom_path%"
    set "RUNNER=.\python_embeded\python.exe -s ComfyUI\main.py"
)

:select_hardware
echo.
echo ====================================================================
echo   SELECT GPU/HARDWARE RUNTIME FLAGS
echo ====================================================================
echo [1] Standard GPU mode (Nvidia / Default AMD ROCm)
echo [2] AMD GPU (with --directml flag for DirectML versions)
echo [3] AMD/Low-VRAM (Disable smart memory - fixes out-of-memory errors)
echo [4] CPU Only mode (Slower fallback)
echo.
set /p hw_choice="Choose option [1-4]: "

set "FLAGS=--api-only --listen 127.0.0.1 --port 8188"

if "%hw_choice%"=="2" (
    set "FLAGS=%FLAGS% --directml"
)
if "%hw_choice%"=="3" (
    set "FLAGS=%FLAGS% --disable-smart-memory"
)
if "%hw_choice%"=="4" (
    set "FLAGS=%FLAGS% --cpu"
)

echo.
echo ====================================================================
echo   LAUNCHING HEADLESS COMFYUI API SERVER
echo ====================================================================
echo Directory: %RUN_DIR%
echo Executing: %RUNNER% %FLAGS%
echo.

cd /d "%RUN_DIR%"
if "%COMFY_TYPE%"=="desktop" (
    ..\uv\win\uv.exe run main.py %FLAGS%
) else (
    .\python_embeded\python.exe -s ComfyUI\main.py %FLAGS%
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Launch failed. Check if python environments or dependencies are set up.
)
pause
