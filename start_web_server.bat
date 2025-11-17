@echo off
echo ============================================================
echo   Vajra Stream Web Server
echo ============================================================
echo.
echo Starting web server...
echo   - API Documentation: http://localhost:8001/docs
echo   - Visualization Gallery: http://localhost:8001/visualizations
echo   - WebSocket: ws://localhost:8001/ws
echo ============================================================
echo.

python start_web_server.py

pause
