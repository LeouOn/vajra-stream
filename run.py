#!/usr/bin/env python3
"""
Vajra.Stream - Consolidated Launcher
All-in-one launcher for the Digital Dharma Technology platform.
"""

import sys
import os
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


def print_banner():
    print("=" * 60)
    print("  Vajra.Stream - Sacred Technology for Healing & Liberation")
    print("  Terra MOPS Scalar Wave Edition")
    print("=" * 60)
    print()


def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=SCRIPT_DIR)
    print("Done!")


def start_backend(port=8008, host="0.0.0.0"):
    """Start the FastAPI backend server"""
    print(f"Starting backend server at {host}:{port}...")
    import uvicorn
    from backend.app.main import app
    uvicorn.run(app, host=host, port=port, reload=False)


def start_frontend():
    """Start the Vite frontend dev server"""
    print("Starting frontend dev server...")
    import subprocess
    frontend_dir = SCRIPT_DIR / "frontend"
    subprocess.run(["npm", "run", "dev"], cwd=frontend_dir)


def start_full_system(backend_port=8008, frontend_port=3009):
    """Start both backend and frontend"""
    import subprocess
    import threading

    print(f"Starting full system (Backend: {backend_port}, Frontend: {frontend_port})...")

    backend_thread = threading.Thread(
        target=lambda: start_backend(port=backend_port),
        daemon=True
    )
    backend_thread.start()

    print("Backend started. Waiting 5 seconds...")
    import time
    time.sleep(5)

    print("Starting frontend...")
    frontend_dir = SCRIPT_DIR / "frontend"
    subprocess.run(["npm", "run", "dev"], cwd=frontend_dir)


def run_tests():
    """Run the test suite"""
    print("Running tests...")
    import subprocess
    result = subprocess.run([sys.executable, "scripts/test_full_stack.py"], cwd=SCRIPT_DIR)
    return result.returncode == 0


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Vajra.Stream - Sacred Technology Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  serve [host] [port]    Start API server (default: 0.0.0.0:8008)
  frontend                Start frontend dev server
  full                    Start full stack (backend + frontend)
  test                    Run integration tests
  install                 Install dependencies

Examples:
  python run.py serve              Start server on 0.0.0.0:8008
  python run.py serve 127.0.0.1    Start server on 127.0.0.1:8008
  python run.py serve 0.0.0.0 9000 Start server on 0.0.0.0:9000
  python run.py frontend          Start frontend only
  python run.py full              Start full stack
  python run.py test              Run tests
        """
    )

    parser.add_argument('command', nargs='?', default='serve',
                        choices=['serve', 'frontend', 'full', 'test', 'install'])

    parser.add_argument('host', nargs='?', default='0.0.0.0')
    parser.add_argument('port', type=int, nargs='?', default=8008)

    args = parser.parse_args()

    if args.command == 'install':
        install_dependencies()
    elif args.command == 'serve':
        start_backend(host=args.host, port=args.port)
    elif args.command == 'frontend':
        start_frontend()
    elif args.command == 'full':
        start_full_system(backend_port=args.port)
    elif args.command == 'test':
        run_tests()


if __name__ == "__main__":
    main()
