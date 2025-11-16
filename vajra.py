#!/usr/bin/env python3
"""
Vajra Stream - Universal Cross-Platform Launcher
Unified command-line interface for all Vajra Stream functionality
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Terminal colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    """Print Vajra Stream header"""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╦  ╦┌─┐ ┬┬─┐┌─┐  ╔═╗┌┬┐┬─┐┌─┐┌─┐┌┬┐
╚╗╔╝├─┤ ││├┬┘├─┤  ╚═╗ │ ├┬┘├┤ ├─┤│││
 ╚╝ ┴ ┴└┘┴┴└─┴ ┴  ╚═╝ ┴ ┴└─└─┘┴ ┴┴ ┴
{Colors.END}
{Colors.GREEN}Sacred Technology for Healing & Liberation{Colors.END}
{Colors.YELLOW}Terra MOPS Scalar Wave Edition{Colors.END}
""")

def get_python_cmd():
    """Get the appropriate Python command"""
    if sys.platform == "win32":
        return "python"
    return "python3"

def run_api_server(host="0.0.0.0", port=8000):
    """Start the FastAPI server"""
    print(f"{Colors.GREEN}🚀 Starting Vajra Stream API Server...{Colors.END}")
    print(f"{Colors.CYAN}   Host: {host}:{port}{Colors.END}")
    print(f"{Colors.CYAN}   API Docs: http://localhost:{port}/docs{Colors.END}")
    print(f"{Colors.CYAN}   WebSocket: ws://localhost:{port}/ws{Colors.END}\n")

    cmd = [
        get_python_cmd(),
        "-m", "uvicorn",
        "backend.app.main:app",
        "--host", host,
        "--port", str(port),
        "--reload"
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Shutting down API server...{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error starting server: {e}{Colors.END}")
        sys.exit(1)

def run_scalar_benchmark(method="all", duration=3):
    """Run scalar wave benchmark"""
    print(f"{Colors.GREEN}⚡ Running Scalar Wave Benchmark{Colors.END}")
    print(f"{Colors.CYAN}   Method: {method}{Colors.END}")
    print(f"{Colors.CYAN}   Duration: {duration}s per method{Colors.END}\n")

    cmd = [
        get_python_cmd(),
        "scripts/scalar_wave_benchmark.py",
        "--method", method,
        "--duration", str(duration)
    ]

    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"{Colors.RED}Error running benchmark: {e}{Colors.END}")
        sys.exit(1)

def run_ui():
    """Run the enhanced terminal UI"""
    print(f"{Colors.GREEN}🎨 Launching Enhanced Terminal UI{Colors.END}\n")

    cmd = [get_python_cmd(), "scripts/vajra_stream_ui.py"]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Exiting UI...{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error running UI: {e}{Colors.END}")
        sys.exit(1)

def visualize_meridians():
    """Generate meridian visualizations"""
    print(f"{Colors.GREEN}🌈 Generating Meridian Visualizations{Colors.END}\n")

    cmd = [get_python_cmd(), "core/meridian_visualization.py"]

    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"{Colors.RED}Error generating visualizations: {e}{Colors.END}")
        sys.exit(1)

def run_tests():
    """Run test suite"""
    print(f"{Colors.GREEN}🧪 Running Test Suite{Colors.END}\n")

    # Check if pytest is available
    try:
        subprocess.run([get_python_cmd(), "-m", "pytest", "--version"],
                      capture_output=True, check=True)
    except:
        print(f"{Colors.YELLOW}Installing pytest...{Colors.END}")
        subprocess.run([get_python_cmd(), "-m", "pip", "install", "pytest", "pytest-asyncio"])

    cmd = [get_python_cmd(), "-m", "pytest", "tests/", "-v"]

    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"{Colors.RED}Error running tests: {e}{Colors.END}")
        sys.exit(1)

def install_dependencies():
    """Install required dependencies"""
    print(f"{Colors.GREEN}📦 Installing Dependencies{Colors.END}\n")

    cmd = [get_python_cmd(), "-m", "pip", "install", "-r", "requirements.txt"]

    try:
        subprocess.run(cmd, check=True)
        print(f"\n{Colors.GREEN}✅ Dependencies installed successfully!{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error installing dependencies: {e}{Colors.END}")
        sys.exit(1)

def show_status():
    """Show system status"""
    print(f"{Colors.GREEN}📊 Vajra Stream System Status{Colors.END}\n")

    # Check Python version
    print(f"Python Version: {sys.version.split()[0]}")

    # Check core modules
    core_modules = [
        "advanced_scalar_waves",
        "integrated_scalar_radionics",
        "meridian_visualization",
        "blessing_narratives",
        "radionics_engine",
        "energetic_anatomy"
    ]

    print(f"\n{Colors.CYAN}Core Modules:{Colors.END}")
    for module in core_modules:
        module_path = Path(f"core/{module}.py")
        status = "✅" if module_path.exists() else "❌"
        print(f"  {status} {module}")

    # Check backend
    backend_path = Path("backend/app/main.py")
    status = "✅" if backend_path.exists() else "❌"
    print(f"\n{Colors.CYAN}Backend:{Colors.END}")
    print(f"  {status} FastAPI Application")

    # Check dependencies
    print(f"\n{Colors.CYAN}Key Dependencies:{Colors.END}")
    deps = ["fastapi", "uvicorn", "pydantic", "pillow", "numpy"]
    for dep in deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep}")

def main():
    """Main entry point"""
    print_header()

    parser = argparse.ArgumentParser(
        description="Vajra Stream - Sacred Technology Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  serve        Start the API server
  ui           Launch terminal UI
  benchmark    Run scalar wave benchmark
  visualize    Generate meridian visualizations
  test         Run test suite
  install      Install dependencies
  status       Show system status

Examples:
  python vajra.py serve
  python vajra.py serve --port 3000
  python vajra.py benchmark --method hybrid --duration 5
  python vajra.py ui
  python vajra.py test
        """
    )

    parser.add_argument("command",
                       choices=["serve", "ui", "benchmark", "visualize", "test", "install", "status"],
                       help="Command to execute")

    # Server arguments
    parser.add_argument("--host", default="0.0.0.0", help="API server host")
    parser.add_argument("--port", type=int, default=8000, help="API server port")

    # Benchmark arguments
    parser.add_argument("--method", default="all", help="Scalar wave method to benchmark")
    parser.add_argument("--duration", type=float, default=3.0, help="Benchmark duration per method")

    args = parser.parse_args()

    # Execute command
    if args.command == "serve":
        run_api_server(args.host, args.port)
    elif args.command == "ui":
        run_ui()
    elif args.command == "benchmark":
        run_scalar_benchmark(args.method, args.duration)
    elif args.command == "visualize":
        visualize_meridians()
    elif args.command == "test":
        run_tests()
    elif args.command == "install":
        install_dependencies()
    elif args.command == "status":
        show_status()

if __name__ == "__main__":
    main()
