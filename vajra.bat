@echo off
REM
REM Vajra Stream - Windows Launcher
REM Sacred Technology for Healing & Liberation
REM

setlocal enabledelayedexpansion

REM Print header
:header
echo.
echo ╦  ╦┌─┐ ┬┬─┐┌─┐  ╔═╗┌┬┐┬─┐┌─┐┌─┐┌┬┐
echo ╚╗╔╝├─┤ ││├┬┘├─┤  ╚═╗ │ ├┬┘├┤ ├─┤│││
echo  ╚╝ ┴ ┴└┘┴┴└─┴ ┴  ╚═╝ ┴ ┴└─└─┘┴ ┴┴ ┴
echo.
echo Sacred Technology for Healing ^& Liberation
echo Terra MOPS Scalar Wave Edition
echo.

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Main command dispatcher
if "%1"=="" goto help
if "%1"=="serve" goto serve
if "%1"=="ui" goto ui
if "%1"=="benchmark" goto benchmark
if "%1"=="visualize" goto visualize
if "%1"=="test" goto test
if "%1"=="install" goto install
if "%1"=="status" goto status
if "%1"=="help" goto help
if "%1"=="-h" goto help
if "%1"=="--help" goto help

echo Unknown command: %1
echo Run 'vajra.bat help' for usage information
exit /b 1

:serve
echo 🚀 Starting Vajra Stream API Server...
set HOST=%2
set PORT=%3
if "%HOST%"=="" set HOST=0.0.0.0
if "%PORT%"=="" set PORT=8000
echo    Host: %HOST%:%PORT%
echo    API Docs: http://localhost:%PORT%/docs
echo    WebSocket: ws://localhost:%PORT%/ws
echo.
python -m uvicorn backend.app.main:app --host %HOST% --port %PORT% --reload
goto end

:ui
echo 🎨 Launching Enhanced Terminal UI
echo.
python scripts\vajra_stream_ui.py
goto end

:benchmark
set METHOD=%2
set DURATION=%3
if "%METHOD%"=="" set METHOD=all
if "%DURATION%"=="" set DURATION=3
echo ⚡ Running Scalar Wave Benchmark
echo    Method: %METHOD%
echo    Duration: %DURATION%s per method
echo.
python scripts\scalar_wave_benchmark.py --method %METHOD% --duration %DURATION%
goto end

:visualize
echo 🌈 Generating Meridian Visualizations
echo.
python core\meridian_visualization.py
goto end

:test
echo 🧪 Running Test Suite
echo.
REM Install pytest if needed
python -m pip install -q pytest pytest-asyncio 2>nul
python -m pytest tests\ -v
goto end

:install
echo 📦 Installing Dependencies
echo.
python -m pip install -r requirements.txt
echo.
echo ✅ Dependencies installed successfully!
goto end

:status
python vajra.py status
goto end

:help
echo Usage:
echo   vajra.bat ^<command^> [options]
echo.
echo Commands:
echo   serve [host] [port]    Start the API server (default: 0.0.0.0:8000)
echo   ui                     Launch terminal UI
echo   benchmark [method]     Run scalar wave benchmark
echo   visualize              Generate meridian visualizations
echo   test                   Run test suite
echo   install                Install dependencies
echo   status                 Show system status
echo   help                   Show this help message
echo.
echo Examples:
echo   vajra.bat serve                    # Start server on 0.0.0.0:8000
echo   vajra.bat serve 127.0.0.1 3000    # Start server on 127.0.0.1:3000
echo   vajra.bat benchmark hybrid 5       # Benchmark hybrid method for 5s
echo   vajra.bat ui                       # Launch terminal UI
echo   vajra.bat test                     # Run tests
echo.
echo API Endpoints:
echo   /api/v1/scalar         - Scalar wave generation ^& benchmarking
echo   /api/v1/radionics      - Radionics broadcasting
echo   /api/v1/anatomy        - Meridian ^& chakra visualization
echo   /api/v1/blessings      - Blessing generation
echo   /api/v1/audio          - Audio synthesis
echo   /api/v1/sessions       - Healing sessions
echo   /api/v1/astrology      - Astrological analysis
echo.
echo May all beings benefit! 🙏
goto end

:end
endlocal
