#!/usr/bin/env python3
"""
Start both backend and frontend servers for Vajra Stream
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("=" * 70)
    print("🔱 Vajra Stream - Full System Startup")
    print("=" * 70)
    print(f"📁 Project Root: {project_root}")
    print()

    processes = []

    try:
        # Start backend server
        print("🚀 Starting Backend API Server (Port 8001)...")
        print("-" * 70)
        backend_cmd = [sys.executable, "start_web_server.py"]
        backend_process = subprocess.Popen(
            backend_cmd,
            cwd=project_root,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        processes.append(("Backend", backend_process))
        print("✅ Backend server starting in new window...")
        time.sleep(2)

        # Start frontend server
        print()
        print("🎨 Starting Frontend Dev Server (Port 3009)...")
        print("-" * 70)

        frontend_dir = project_root / "frontend"
        if not frontend_dir.exists():
            print("⚠️  Frontend directory not found. Skipping frontend startup.")
            print("   Backend API and visualization gallery will still work!")
        else:
            # Check if node_modules exists
            if not (frontend_dir / "node_modules").exists():
                print("⚠️  Frontend dependencies not installed.")
                print("   Run: cd frontend && npm install")
                print("   Skipping frontend startup for now...")
            else:
                frontend_cmd = ["npm", "run", "dev"]
                frontend_process = subprocess.Popen(
                    frontend_cmd,
                    cwd=frontend_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
                )
                processes.append(("Frontend", frontend_process))
                print("✅ Frontend server starting in new window...")

        print()
        print("=" * 70)
        print("🎉 Vajra Stream is Running!")
        print("=" * 70)
        print()
        print("📍 Access Points:")
        print("-" * 70)
        print("  🌐 Backend API:")
        print("     • Main Page:        http://localhost:8001/")
        print("     • API Docs:         http://localhost:8001/docs")
        print("     • Visualization:    http://localhost:8001/visualizations")
        print("     • WebSocket:        ws://localhost:8001/ws")
        print()
        if len(processes) > 1:
            print("  🎨 Frontend (React/Vite):")
            print("     • Dev Server:       http://localhost:3009/")
            print()
        print("=" * 70)
        print()
        print("💡 Quick Start:")
        print("   1. Open http://localhost:8001/visualizations for the gallery")
        print("   2. Click any card to generate sacred visualizations")
        print("   3. Use Ctrl+C here to stop all servers")
        print()
        print("Press Ctrl+C to stop all servers...")
        print("=" * 70)

        # Wait for user interrupt
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down all servers...")
        for name, process in processes:
            print(f"   Stopping {name}...")
            process.terminate()
        print("✅ All servers stopped. Goodbye! 🙏")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        for name, process in processes:
            process.terminate()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
