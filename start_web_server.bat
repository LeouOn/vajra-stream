@echo off
echo ============================================================
echo   Vajra Stream Web Server
echo ============================================================
echo.
echo Starting web server...
echo   - API Documentation: http://localhost:8000/docs
echo   - Visualization Gallery: http://localhost:8000/visualizations
echo   - WebSocket: ws://localhost:8000/ws
echo ============================================================
echo.

python start_web_server.py

pause
