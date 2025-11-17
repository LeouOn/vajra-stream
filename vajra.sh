#!/bin/bash
#
# Vajra Stream - Unix/Linux/Mac Launcher
# Sacred Technology for Healing & Liberation
#

set -e

# Colors for terminal output
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print header
print_header() {
    echo -e "${CYAN}${BOLD}"
    cat << "EOF"
╦  ╦┌─┐ ┬┬─┐┌─┐  ╔═╗┌┬┐┬─┐┌─┐┌─┐┌┬┐
╚╗╔╝├─┤ ││├┬┘├─┤  ╚═╗ │ ├┬┘├┤ ├─┤│││
 ╚╝ ┴ ┴└┘┴┴└─┴ ┴  ╚═╝ ┴ ┴└─└─┘┴ ┴┴ ┴
EOF
    echo -e "${NC}"
    echo -e "${GREEN}Sacred Technology for Healing & Liberation${NC}"
    echo -e "${YELLOW}Terra MOPS Scalar Wave Edition${NC}"
    echo ""
}

# Check if Python 3 is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi
}

# Main command dispatcher
case "${1:-help}" in
    serve)
        print_header
        check_python
        echo -e "${GREEN}🚀 Starting Vajra Stream API Server...${NC}"
        HOST="${2:-0.0.0.0}"
        PORT="${3:-8000}"
        echo -e "${CYAN}   Host: ${HOST}:${PORT}${NC}"
        echo -e "${CYAN}   API Docs: http://localhost:${PORT}/docs${NC}"
        echo -e "${CYAN}   WebSocket: ws://localhost:${PORT}/ws${NC}"
        echo ""
        python3 -m uvicorn backend.app.main:app --host "$HOST" --port "$PORT" --reload
        ;;

    ui)
        print_header
        check_python
        echo -e "${GREEN}🎨 Launching Enhanced Terminal UI${NC}"
        echo ""
        python3 scripts/vajra_stream_ui.py
        ;;

    benchmark)
        print_header
        check_python
        METHOD="${2:-all}"
        DURATION="${3:-3}"
        echo -e "${GREEN}⚡ Running Scalar Wave Benchmark${NC}"
        echo -e "${CYAN}   Method: ${METHOD}${NC}"
        echo -e "${CYAN}   Duration: ${DURATION}s per method${NC}"
        echo ""
        python3 scripts/scalar_wave_benchmark.py --method "$METHOD" --duration "$DURATION"
        ;;

    visualize)
        print_header
        check_python
        echo -e "${GREEN}🌈 Generating Meridian Visualizations${NC}"
        echo ""
        python3 core/meridian_visualization.py
        ;;

    test)
        print_header
        check_python
        echo -e "${GREEN}🧪 Running Test Suite${NC}"
        echo ""
        # Install pytest if needed
        python3 -m pip install -q pytest pytest-asyncio 2>/dev/null || true
        python3 -m pytest tests/ -v
        ;;

    install)
        print_header
        check_python
        echo -e "${GREEN}📦 Installing Dependencies${NC}"
        echo ""
        python3 -m pip install -r requirements.txt
        echo ""
        echo -e "${GREEN}✅ Dependencies installed successfully!${NC}"
        ;;

    status)
        print_header
        check_python
        python3 vajra.py status
        ;;

    help|--help|-h)
        print_header
        cat << EOF
${GREEN}${BOLD}Usage:${NC}
  ./vajra.sh <command> [options]

${GREEN}${BOLD}Commands:${NC}
  serve [host] [port]    Start the API server (default: 0.0.0.0:8000)
  ui                     Launch terminal UI
  benchmark [method]     Run scalar wave benchmark
  visualize              Generate meridian visualizations
  test                   Run test suite
  install                Install dependencies
  status                 Show system status
  help                   Show this help message

${GREEN}${BOLD}Examples:${NC}
  ./vajra.sh serve                    # Start server on 0.0.0.0:8000
  ./vajra.sh serve 127.0.0.1 3000    # Start server on 127.0.0.1:3000
  ./vajra.sh benchmark hybrid 5       # Benchmark hybrid method for 5s
  ./vajra.sh ui                       # Launch terminal UI
  ./vajra.sh test                     # Run tests

${GREEN}${BOLD}API Endpoints:${NC}
  /api/v1/scalar         - Scalar wave generation & benchmarking
  /api/v1/radionics      - Radionics broadcasting
  /api/v1/anatomy        - Meridian & chakra visualization
  /api/v1/blessings      - Blessing generation
  /api/v1/audio          - Audio synthesis
  /api/v1/sessions       - Healing sessions
  /api/v1/astrology      - Astrological analysis

${YELLOW}May all beings benefit! 🙏${NC}
EOF
        ;;

    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run './vajra.sh help' for usage information"
        exit 1
        ;;
esac
