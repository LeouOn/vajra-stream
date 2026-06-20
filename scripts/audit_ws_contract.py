#!/usr/bin/env python3
"""
audit_ws_contract.py — WebSocket message-type drift auditor.

Wave 4 Task 24 (remediation-24) regression guard.

Compares the set of WebSocket message types emitted by the ACTIVE backend
sources against the set of `case` labels handled by the frontend switch in
useWebSocketStable.ts. Exits 0 when the two sets are equal, non-zero on any
drift in either direction.

Source of truth for which backend files count as "active":
    .omo/evidence/wave0-task3-ws-whitelist.json#methodology.backend_emit_sources

Deliberately EXCLUDED (would inflate the backend set with stale types):
    - backend/websocket/connection_manager.py        (dead, Task 16 deletion target)
    - backend/websocket/connection_manager_stable.py (dead, Task 16 deletion target)
    - backend/simple_server.py                       (standalone alt entrypoint,
                                                      not the active FastAPI app)

Usage:
    python scripts/audit_ws_contract.py

Exit codes:
    0 — backend and frontend message-type sets match exactly (no drift)
    1 — contract drift detected (missing handlers and/or dead cases)
    2 — structural error (missing file, unparseable switch, etc.)

Companion test: frontend/src/__tests__/hooks/ws-contract.test.ts runs the
same comparison inside vitest; this script runs it in CI / pre-commit.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Active backend WS emit sources (per wave0-task3-ws-whitelist.json).
ACTIVE_BACKEND_SOURCES = [
    "backend/websocket/connection_manager_stable_v2.py",
    "backend/core/services/vajra_service.py",
    "backend/app/main.py",
]

# Canonical supplement: backend-emitted types whose source files are NOT in
# ACTIVE_BACKEND_SOURCES (they live under core/, not backend/) OR whose emit
# site uses an indirection helper (e.g. `_broadcast_ws(event_type, ...)`)
# that the BACKEND_TYPE_RE regex cannot statically resolve.
#
# These types are part of the active runtime contract — the frontend switch
# in useWebSocketStable.ts MUST handle them — so they are unioned into the
# canonical set the audit compares against.
#
# Sources:
#   - core/buddha_recitation_loop.py (BUDDHA_RECITATION_STARTED/NAME_RECITED/STOPPED)
#   - core/ritual_engine.py (RITUAL_ENGINE_STATUS/PHASE/COMPLETED, PLANETARY_HOUR_SHIFT)
#   - core/character_journey.py (JOURNEY_STAGE_STARTED/COMPLETED, JOURNEY_COMPLETED)
#
# Restored after remediation Task 24 regressively deleted their case branches.
CANONICAL_SUPPLEMENT_TYPES: set[str] = {
    "BUDDHA_RECITATION_STARTED",
    "BUDDHA_NAME_RECITED",
    "BUDDHA_RECITATION_STOPPED",
    "RITUAL_ENGINE_STATUS",
    "RITUAL_PHASE",
    "RITUAL_COMPLETED",
    "PLANETARY_HOUR_SHIFT",
    "JOURNEY_STAGE_STARTED",
    "JOURNEY_STAGE_COMPLETED",
    "JOURNEY_COMPLETED",
}

FRONTEND_HOOK = "frontend/src/hooks/useWebSocketStable.ts"

# Capture the message-type string literal from `"type": "<NAME>"` patterns.
# Tolerates either quote style for key and value and whitespace around colon.
BACKEND_TYPE_RE = re.compile(r'["\']type["\']\s*:\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']')

# Capture `case '<NAME>':` labels (string-literal cases only).
FRONTEND_CASE_RE = re.compile(r'\bcase\s+["\']([A-Za-z_][A-Za-z0-9_]*)["\']\s*:')


def extract_backend_types() -> set[str]:
    """Return the set of WS message types emitted by active backend sources.

    Includes CANONICAL_SUPPLEMENT_TYPES (types emitted from core/ files or via
    indirection helpers that the static regex cannot resolve).
    """
    types: set[str] = set()
    for rel in ACTIVE_BACKEND_SOURCES:
        path = REPO_ROOT / rel
        if not path.exists():
            print(f"WARN: active backend source missing: {rel}", file=sys.stderr)
            continue
        text = path.read_text(encoding="utf-8")
        for m in BACKEND_TYPE_RE.finditer(text):
            types.add(m.group(1))
    types |= CANONICAL_SUPPLEMENT_TYPES
    return types


def extract_frontend_cases() -> set[str]:
    """Return the set of `case '<TYPE>':` labels in the frontend WS switch."""
    path = REPO_ROOT / FRONTEND_HOOK
    if not path.exists():
        print(f"FATAL: frontend hook missing: {FRONTEND_HOOK}", file=sys.stderr)
        sys.exit(2)

    text = path.read_text(encoding="utf-8")

    # Scope to the `switch (data.type) { ... }` block so stray `case` keywords
    # elsewhere in the file cannot pollute the comparison.
    switch_start = text.find("switch (data.type)")
    if switch_start == -1:
        print("FATAL: could not locate `switch (data.type)` in frontend hook", file=sys.stderr)
        sys.exit(2)

    brace_start = text.find("{", switch_start)
    if brace_start == -1:
        print("FATAL: malformed switch — no opening brace", file=sys.stderr)
        sys.exit(2)

    depth = 0
    switch_end = -1
    for i in range(brace_start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                switch_end = i
                break
    if switch_end == -1:
        print("FATAL: could not find closing brace of switch block", file=sys.stderr)
        sys.exit(2)

    block = text[brace_start:switch_end]
    return set(FRONTEND_CASE_RE.findall(block))


def main() -> int:
    backend_types = extract_backend_types()
    frontend_cases = extract_frontend_cases()

    missing = sorted(backend_types - frontend_cases)  # backend emits, frontend silent
    dead = sorted(frontend_cases - backend_types)     # frontend handles, backend never emits

    sep = "=" * 72
    print(sep)
    print("WebSocket message-type contract audit (wave4-task24 / remediation-24)")
    print(sep)
    print(f"Active backend sources : {len(ACTIVE_BACKEND_SOURCES)}")
    for rel in ACTIVE_BACKEND_SOURCES:
        print(f"    - {rel}")
    print(f"Frontend hook          : {FRONTEND_HOOK}")
    print(f"Backend-emitted types  : {len(backend_types)}")
    print(f"Frontend case labels   : {len(frontend_cases)}")
    print(f"Matched (intersection) : {len(backend_types & frontend_cases)}")
    print()

    drift = False
    if missing:
        drift = True
        print(f"DRIFT - backend emits but frontend has no case ({len(missing)}):")
        for t in missing:
            print(f"    + {t}")
        print()
    if dead:
        drift = True
        print(f"DRIFT - frontend handles but backend never emits ({len(dead)}):")
        for t in dead:
            print(f"    - {t}")
        print()

    if drift:
        print("RESULT: FAIL - contract drift detected.")
        print("Fix: add the missing `case` branches and/or delete the dead ones in")
        print("useWebSocketStable.ts, then re-run this script. If the drift is")
        print("intentional (new backend emitter), update the canonical whitelist at")
        print(".omo/evidence/wave0-task3-ws-whitelist.json first.")
        return 1

    print("RESULT: PASS - backend and frontend message-type sets match exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
