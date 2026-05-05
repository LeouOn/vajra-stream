#!/usr/bin/env python3
"""Start the Vajra.Stream backend server"""
import sys
import os

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import uvicorn
    print("Starting Vajra.Stream Backend Server...")
    print("API Documentation: http://localhost:8008/docs")
    print("WebSocket: ws://localhost:8008/ws")
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8008,
        reload=False,
        log_level="info"
    )