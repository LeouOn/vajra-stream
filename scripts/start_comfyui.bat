@echo off
setlocal EnableExtensions
title Vajra.Stream - ComfyUI launcher

REM ===================================================================
REM  Starts the ComfyUI install that backs the local render engine
REM  (backend/core/services/render/, /api/v1/render/*).
REM
REM  Vajra.Stream never starts ComfyUI by itself: a Qwen-Image 2.1 load
REM  puts tens of GB on the GPU, so it only runs when you ask for it.
REM
REM  Configure the launcher once, either as an environment variable or
REM  as a line in the project's .env:
REM
REM      COMFYUI_LAUNCHER=D:\ComfyUI\Start-Qwen-ComfyUI.bat
REM
REM  The launcher owns every ComfyUI flag (listen address, port, GPU
REM  options). This script passes none: older versions passed
REM  --api-only, which ComfyUI does not have, and it crashed on start.
REM ===================================================================

set "PROJECT_ROOT=%~dp0.."

REM Environment wins; otherwise read COMFYUI_LAUNCHER / COMFYUI_BASE_URL from .env.
if exist "%PROJECT_ROOT%\.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%PROJECT_ROOT%\.env") do (
        if /i "%%A"=="COMFYUI_LAUNCHER" if not defined COMFYUI_LAUNCHER set "COMFYUI_LAUNCHER=%%~B"
        if /i "%%A"=="COMFYUI_BASE_URL" if not defined COMFYUI_BASE_URL set "COMFYUI_BASE_URL=%%~B"
    )
)
if not defined COMFYUI_BASE_URL set "COMFYUI_BASE_URL=http://127.0.0.1:8188"

if not defined COMFYUI_LAUNCHER goto :no_launcher
if not exist "%COMFYUI_LAUNCHER%" goto :missing_launcher

echo Starting ComfyUI with: %COMFYUI_LAUNCHER%
echo.
echo Once it is up, check:
echo   ComfyUI itself:      %COMFYUI_BASE_URL%/system_stats
echo   Vajra.Stream view:   http://localhost:8008/api/v1/render/health
echo.
for %%F in ("%COMFYUI_LAUNCHER%") do pushd "%%~dpF"
call "%COMFYUI_LAUNCHER%"
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" (
    echo.
    echo [ERROR] The ComfyUI launcher exited with code %RC%.
)
exit /b %RC%

:missing_launcher
echo [ERROR] COMFYUI_LAUNCHER points to a file that does not exist:
echo         %COMFYUI_LAUNCHER%
echo.
goto :instructions

:no_launcher
echo [INFO] COMFYUI_LAUNCHER is not set, so there is nothing to start.
echo.

:instructions
echo To let this script start ComfyUI, set COMFYUI_LAUNCHER to the script
echo that starts your ComfyUI install, as an environment variable or in .env:
echo.
echo     COMFYUI_LAUNCHER=D:\ComfyUI\Start-Qwen-ComfyUI.bat
echo.
echo Or start ComfyUI yourself. Vajra.Stream expects it at
echo     COMFYUI_BASE_URL=%COMFYUI_BASE_URL%
echo with the Qwen-Image 2.1 Turbo models installed.
echo.
echo Health checks:
echo   ComfyUI itself:      %COMFYUI_BASE_URL%/system_stats
echo   Vajra.Stream view:   http://localhost:8008/api/v1/render/health
exit /b 1
