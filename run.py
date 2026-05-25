#!/usr/bin/env python3
"""
Vajra.Stream - Consolidated Launcher
All-in-one launcher for the Digital Dharma Technology platform.

Usage:
  python run.py serve [--host H] [--port P]   Start API server
  python run.py frontend                       Start frontend dev server
  python run.py full [--port P]                Start full stack (backend + frontend)
  python run.py test                           Run test suite
  python run.py install                        Install dependencies
  python run.py status                         Show system status
  python run.py benchmark [--duration D]       Run scalar wave benchmark
  python run.py ui                             Launch terminal UI
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _cmd(args, **kwargs):
    kwargs.setdefault("cwd", SCRIPT_DIR)
    if sys.platform == "win32":
        kwargs.setdefault("shell", True)
    return subprocess.run(args, **kwargs)


def _popen(args, **kwargs):
    kwargs.setdefault("cwd", SCRIPT_DIR)
    if sys.platform == "win32":
        kwargs.setdefault("shell", True)
    return subprocess.Popen(args, **kwargs)


def print_banner():
    print("=" * 60)
    print("  Vajra.Stream - Sacred Technology for Healing & Liberation")
    print("  Terra MOPS Scalar Wave Edition")
    print("=" * 60)
    print()


BACKEND_PORT = 8008
FRONTEND_PORT = 3009


def install_dependencies():
    print("Installing dependencies...")
    _cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Done!")


def start_backend(port=BACKEND_PORT, host="0.0.0.0"):
    print(f"Starting backend server at {host}:{port}...")
    print(f"  API Docs:      http://localhost:{port}/docs")
    print(f"  Visualizations: http://localhost:{port}/visualizations")
    print(f"  WebSocket:     ws://localhost:{port}/ws")
    print()
    import uvicorn

    from backend.app.main import app

    uvicorn.run(app, host=host, port=port, reload=False)


def start_frontend():
    print(f"Starting frontend dev server (port {FRONTEND_PORT})...")
    frontend_dir = SCRIPT_DIR / "frontend"
    if not frontend_dir.exists():
        print("ERROR: frontend/ directory not found.")
        sys.exit(1)
    if not (frontend_dir / "node_modules").exists():
        print("ERROR: node_modules not found. Run: cd frontend && npm install")
        sys.exit(1)
    _cmd(["npm", "run", "dev"], cwd=frontend_dir)


def start_full_system(backend_port=BACKEND_PORT):
    processes = []
    try:
        print("Starting full system...")
        print(f"  Backend:  port {backend_port}")
        print(f"  Frontend: port {FRONTEND_PORT}")
        print()

        if sys.platform == "win32":
            backend_proc = _popen(
                f'"{sys.executable}" "{SCRIPT_DIR / "run.py"}" serve --port {backend_port}',
                cwd=SCRIPT_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            backend_proc = _popen(
                [sys.executable, str(SCRIPT_DIR / "run.py"), "serve", "--port", str(backend_port)],
                cwd=SCRIPT_DIR,
            )
        processes.append(("Backend", backend_proc))
        print(f"[OK] Backend starting on port {backend_port}...")
        time.sleep(3)

        frontend_dir = SCRIPT_DIR / "frontend"
        if (frontend_dir / "node_modules").exists():
            if sys.platform == "win32":
                frontend_proc = _popen(
                    "npm run dev",
                    cwd=frontend_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                frontend_proc = _popen(
                    ["npm", "run", "dev"],
                    cwd=frontend_dir,
                )
            processes.append(("Frontend", frontend_proc))
            print(f"[OK] Frontend starting on port {FRONTEND_PORT}...")
        else:
            print("[WARN] Frontend node_modules not found. Skipping frontend.")
            print("       Run: cd frontend && npm install")

        print()
        print("=" * 60)
        print("  Vajra.Stream is Running!")
        print("=" * 60)
        print(f"  Backend API:       http://localhost:{backend_port}")
        print(f"  API Docs:          http://localhost:{backend_port}/docs")
        print(f"  Visualizations:    http://localhost:{backend_port}/visualizations")
        if len(processes) > 1:
            print(f"  Frontend:          http://localhost:{FRONTEND_PORT}")
        print("=" * 60)
        print()
        print("Press Ctrl+C to stop all servers...")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down all servers...")
        for name, proc in processes:
            print(f"  Stopping {name}...")
            proc.terminate()
        print("All servers stopped.")

    except Exception as e:
        print(f"\nError: {e}")
        for name, proc in processes:
            proc.terminate()
        return 1

    return 0


def run_tests():
    print("Running test suite...")
    result = _cmd([sys.executable, "-m", "pytest", "tests/", "-v"])
    return result.returncode


def run_benchmark(duration=3):
    print(f"Running scalar wave benchmark ({duration}s per method)...")
    benchmark_script = SCRIPT_DIR / "scripts" / "scalar_wave_benchmark.py"
    if benchmark_script.exists():
        _cmd([sys.executable, str(benchmark_script), "--method", "all", "--duration", str(duration)])
    else:
        print("ERROR: scripts/scalar_wave_benchmark.py not found")


def run_ui():
    print("Launching terminal UI...")
    ui_script = SCRIPT_DIR / "scripts" / "vajra_stream_ui.py"
    if ui_script.exists():
        _cmd([sys.executable, str(ui_script)])
    else:
        print("ERROR: scripts/vajra_stream_ui.py not found")


def show_status():
    print("Vajra.Stream System Status")
    print("=" * 50)
    print(f"  Python:  {sys.version.split()[0]}")
    print(f"  Project: {SCRIPT_DIR}")
    print()

    core_modules = [
        "advanced_scalar_waves",
        "integrated_scalar_radionics",
        "meridian_visualization",
        "energetic_anatomy",
        "blessing_narratives",
        "radionics_engine",
    ]
    print("  Core Modules:")
    for mod in core_modules:
        exists = (SCRIPT_DIR / "core" / f"{mod}.py").exists()
        print(f"    {'[OK]' if exists else '[MISSING]'} {mod}")

    backend_main = SCRIPT_DIR / "backend" / "app" / "main.py"
    print(f"\n  Backend:  {'[OK]' if backend_main.exists() else '[MISSING]'} FastAPI app")

    frontend_pkg = SCRIPT_DIR / "frontend" / "package.json"
    print(f"  Frontend: {'[OK]' if frontend_pkg.exists() else '[MISSING]'} React/Vite app")

    print("\n  Key Dependencies:")
    for dep in ["fastapi", "uvicorn", "pydantic", "numpy"]:
        try:
            __import__(dep)
            print(f"    [OK] {dep}")
        except ImportError:
            print(f"    [MISSING] {dep}")

def preflight_checks():
    print("=" * 60)
    print("  Performing System Pre-Flight Checks...")
    print("=" * 60)
    
    # 1. Git Update Check
    git_dir = SCRIPT_DIR / ".git"
    if git_dir.exists():
        print("Checking for repository updates...")
        try:
            # Run git fetch to check for upstream changes
            # Use a timeout of 3 seconds to avoid hanging if offline
            res = _cmd(["git", "fetch"], timeout=3, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                local_res = _cmd(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE)
                local_hash = local_res.stdout.decode().strip() if local_res.returncode == 0 else ""
                
                upstream_res = _cmd(["git", "rev-parse", "@{u}"], stdout=subprocess.PIPE)
                upstream_hash = upstream_res.stdout.decode().strip() if upstream_res.returncode == 0 else ""
                
                if local_hash and upstream_hash and local_hash != upstream_hash:
                    print("[INFO] New repository updates are available.")
                    print("       Pulling latest changes...")
                    pull_res = _cmd(["git", "pull"], timeout=10)
                    if pull_res.returncode == 0:
                        print("[OK] Repository updated successfully.")
                    else:
                        print("[WARN] Failed to pull repository updates. Proceeding with local version.")
                else:
                    print("[OK] Repository is up-to-date.")
            else:
                print("[INFO] Could not fetch remote repository status. Proceeding offline.")
        except FileNotFoundError:
            print("[INFO] Git executable not found in PATH. Skipping git check.")
        except Exception as e:
            print(f"[INFO] Skipping git check: {e}")
    else:
        print("[INFO] Not a git repository. Skipping git check.")

    # 2. Python Dependency Check
    req_file = SCRIPT_DIR / "requirements.txt"
    if req_file.exists():
        print("Verifying Python dependencies...")
        try:
            import importlib.metadata
            import re
            
            missing = []
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Parse package name
                    match = re.match(r"^([a-zA-Z0-9_\-]+)", line)
                    if match:
                        pkg = match.group(1)
                        try:
                            importlib.metadata.version(pkg)
                        except importlib.metadata.PackageNotFoundError:
                            missing.append(line)
            
            if missing:
                print(f"[WARN] Missing {len(missing)} Python packages (e.g. {', '.join([m.split('>=')[0] for m in missing[:3]])}).")
                print("       Installing dependencies...")
                _cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
                print("[OK] Python dependencies installed.")
            else:
                print("[OK] Python dependencies are satisfied.")
        except Exception as e:
            print(f"[WARN] Error verifying Python dependencies: {e}. Running pip install just in case...")
            _cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # 3. Frontend Dependency Check
    frontend_dir = SCRIPT_DIR / "frontend"
    if frontend_dir.exists():
        print("Verifying Frontend dependencies...")
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("[WARN] frontend/node_modules not found.")
            print("       Running 'npm install' in frontend directory (this may take a minute)...")
            try:
                # Run npm install
                res = _cmd(["npm", "install"], cwd=frontend_dir)
                if res.returncode == 0:
                    print("[OK] Frontend dependencies installed successfully.")
                else:
                    print("[ERROR] 'npm install' failed. Frontend server may fail to start.")
            except FileNotFoundError:
                print("[ERROR] 'npm' command not found. Please install Node.js and npm to run the frontend.")
            except Exception as e:
                print(f"[ERROR] Could not run 'npm install': {e}")
        else:
            print("[OK] Frontend dependencies are installed.")
            
    print("Pre-flight checks complete.\n")


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Vajra.Stream - Sacred Technology Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  serve        Start API server (default port: 8008)
  frontend     Start frontend dev server (port 3009)
  full         Start full stack (backend + frontend)
  test         Run test suite
  install      Install dependencies
  status       Show system status
  benchmark    Run scalar wave benchmark
  ui           Launch terminal UI

Examples:
  python run.py serve
  python run.py serve --port 9000
  python run.py full
  python run.py test
  python run.py status
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="full",
        choices=["serve", "frontend", "full", "test", "install", "status", "benchmark", "ui", "help"],
    )

    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=BACKEND_PORT)
    parser.add_argument("--duration", type=float, default=3.0)

    args = parser.parse_args()

    if args.command == "help":
        parser.print_help()
        return 0

    sys.path.insert(0, str(SCRIPT_DIR))

    if args.command in ["serve", "frontend", "full"]:
        preflight_checks()

    if args.command == "install":
        install_dependencies()
    elif args.command == "serve":
        start_backend(host=args.host, port=args.port)
    elif args.command == "frontend":
        start_frontend()
    elif args.command == "full":
        return start_full_system(backend_port=args.port)
    elif args.command == "test":
        return run_tests()
    elif args.command == "status":
        show_status()
    elif args.command == "benchmark":
        run_benchmark(duration=args.duration)
    elif args.command == "ui":
        run_ui()

    return 0


if __name__ == "__main__":
    sys.exit(main())
