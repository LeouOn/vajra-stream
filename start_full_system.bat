@echo off
echo ======================================================================
echo   Vajra Stream - Full System Startup
echo ======================================================================
echo.
echo Starting Backend API Server on port 8001...
start "Vajra Backend" python start_web_server.py
timeout /t 3 /nobreak >nul

echo.
echo Starting Frontend Dev Server on port 3009...
cd frontend
if exist node_modules (
    start "Vajra Frontend" npm run dev
    echo.
    echo ======================================================================
    echo   Vajra Stream is Running!
    echo ======================================================================
    echo.
    echo   Backend API:       http://localhost:8001
    echo   Visualizations:    http://localhost:8001/visualizations
    echo   API Docs:          http://localhost:8001/docs
    echo.
    echo   Frontend:          http://localhost:3009
    echo.
    echo ======================================================================
    echo.
    echo Close the server windows to stop.
) else (
    echo.
    echo WARNING: Frontend dependencies not installed!
    echo Run: cd frontend ^&^& npm install
    echo.
    echo Backend is running at: http://localhost:8001/visualizations
    echo.
)

pause
