#!/usr/bin/env python3
"""
Simple launcher for Vajra Stream Web Server
Ensures all paths are set correctly
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run the server
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🔱 Vajra Stream Web Server")
    print("=" * 60)
    print(f"📁 Project Root: {project_root}")
    print()
    print("Starting server...")
    print("  • API Documentation: http://localhost:8000/docs")
    print("  • Visualization Gallery: http://localhost:8000/visualizations")
    print("  • WebSocket: ws://localhost:8000/ws")
    print("=" * 60)
    print()

    # Import the FastAPI app
    from backend.app.main import app

    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload to avoid path issues
        log_level="info"
    )
