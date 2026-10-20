#!/bin/bash
#
# Vajra Stream - Unix/Linux/Mac Launcher
# Sacred Technology for Healing & Liberation
#
# Thin wrapper around run.py - see: python3 run.py --help
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -x "${SCRIPT_DIR}/.venv/bin/python" ]; then
    PYTHON_EXEC="${SCRIPT_DIR}/.venv/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_EXEC="$VIRTUAL_ENV/bin/python"
else
    PYTHON_EXEC="python3"
fi

exec "$PYTHON_EXEC" "${SCRIPT_DIR}/run.py" "$@"
