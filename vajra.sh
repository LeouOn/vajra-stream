#!/bin/bash
#
# Vajra Stream - Unix/Linux/Mac Launcher
# Sacred Technology for Healing & Liberation
#
# Thin wrapper around run.py - see: python3 run.py --help
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 "${SCRIPT_DIR}/run.py" "$@"
