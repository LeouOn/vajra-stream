#!/usr/bin/env python3
"""
Wave 3 Task 16 — Dead duplicate backend files must be deleted.

Behaviour lock (TDD): asserts that the 5 dead duplicate backend files
identified in ADR 001 (``docs/decisions/001-audio-subsystem-canonical.md``)
and ADR 003 (``docs/decisions/003-orchestrator-canonical.md``), plus the
2 collateral stale tests that only referenced them, NO LONGER EXIST on disk.

These artifacts are orphan / dead code:

* ``backend/core/services/audio_service.py``           — AudioService orphan singleton (ADR 001 #3)
* ``backend/core/services/audio_service_fixed.py``     — AudioService orphan singleton (ADR 001 #4)
* ``backend/app/api/v1/endpoints/audio_fixed.py``      — router declared, never mounted (ADR 001 #5)
* ``backend/core/services/orchestrator_service.py``    — OrchestratorService dead, no DI/caller (ADR 003 #4)
* ``backend/websocket/connection_manager_stable.py``   — superseded by ``_v2`` (ADR 001)
* ``tests/unit/test_backend_audio_playback.py``        — only imports ``audio_service.py``
* ``tests/unit/test_audio_fix.py``                     — only imports ``audio_service.py``

Reference: ``.omo/evidence/wave0-task5-audio-matrix.md``,
           ``docs/decisions/001-audio-subsystem-canonical.md``,
           ``docs/decisions/003-orchestrator-canonical.md``
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Repository root = parents[2] up from this test file
# (tests/unit/test_no_dead_duplicates.py -> tests/unit -> tests -> root)
REPO_ROOT = Path(__file__).resolve().parents[2]

# (relative path, short label for assertion messages)
DEAD_FILES: list[tuple[str, str]] = [
    (
        "backend/core/services/audio_service.py",
        "audio_service.py (ADR 001 #3 — orphan AudioService singleton)",
    ),
    (
        "backend/core/services/audio_service_fixed.py",
        "audio_service_fixed.py (ADR 001 #4 — orphan AudioService singleton)",
    ),
    (
        "backend/app/api/v1/endpoints/audio_fixed.py",
        "audio_fixed.py (ADR 001 #5 — unmounted router)",
    ),
    (
        "backend/core/services/orchestrator_service.py",
        "orchestrator_service.py (ADR 003 #4 — dead OrchestratorService)",
    ),
    (
        "backend/websocket/connection_manager_stable.py",
        "connection_manager_stable.py (superseded by connection_manager_stable_v2.py)",
    ),
    (
        "tests/unit/test_backend_audio_playback.py",
        "test_backend_audio_playback.py (stale — only ref to audio_service.py)",
    ),
    (
        "tests/unit/test_audio_fix.py",
        "test_audio_fix.py (stale — only ref to audio_service.py)",
    ),
]


@pytest.mark.parametrize("relpath,label", DEAD_FILES)
def test_dead_duplicate_file_is_deleted(relpath: str, label: str) -> None:
    """Each dead duplicate file MUST NOT exist on disk after Wave 3 Task 16."""
    full = REPO_ROOT / relpath
    assert not full.exists(), (
        f"Dead duplicate file still present: {relpath}\n"
        f"  ({label})\n"
        f"  Resolved: {full}\n"
        f"  Per ADR 001 / ADR 003 this file MUST be deleted in Wave 3 Task 16."
    )


def test_canonical_audio_subsystem_files_remain() -> None:
    """Sanity guard: deletion of dead dupes must NOT remove the canonical artifacts.

    * ``modules/audio.py`` is the canonical LLM-tool audio container (ADR 001) and
      MUST be preserved.
    * ``backend/websocket/connection_manager_stable_v2.py`` is the canonical live
      WebSocket manager and MUST be preserved.
    * ``backend/websocket/connection_manager.py`` (bare original) is intentionally
      left in place per Task 16 instructions (may have other refs).
    """
    must_keep = [
        "modules/audio.py",
        "backend/websocket/connection_manager_stable_v2.py",
        "backend/websocket/connection_manager.py",
    ]
    missing = [p for p in must_keep if not (REPO_ROOT / p).exists()]
    assert not missing, (
        f"Canonical files missing after cleanup: {missing}. "
        f"Task 16 must only delete dead duplicates, not canonical artifacts."
    )


def test_websocket_init_no_longer_eagerly_imports_dead_bare_manager() -> None:
    """``backend/websocket/__init__.py`` must not re-export the dead bare
    ``connection_manager`` submodule in ``__all__`` once the package no
    longer relies on it as an exported surface.

    Note: the file ``connection_manager.py`` itself is intentionally kept
    (per Task 16 scope), only its eager re-export is cleaned.
    """
    init_path = REPO_ROOT / "backend" / "websocket" / "__init__.py"
    if not init_path.exists():
        pytest.skip("backend/websocket/__init__.py not present — nothing to assert.")
    text = init_path.read_text(encoding="utf-8")
    assert '"connection_manager"' not in text, (
        "backend/websocket/__init__.py still exports bare 'connection_manager' "
        "in __all__; Task 16 requires cleaning this re-export."
    )


if __name__ == "__main__":
    # Allow direct execution for quick evidence-gathering outside pytest.
    print(f"Repo root: {REPO_ROOT}")
    print(f"Tracking {len(DEAD_FILES)} dead duplicate files:")
    failures = 0
    for relpath, label in DEAD_FILES:
        full = REPO_ROOT / relpath
        status = "STILL EXISTS (FAIL)" if full.exists() else "deleted (PASS)"
        print(f"  [{status}] {relpath}  — {label}")
        if full.exists():
            failures += 1
    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {len(DEAD_FILES) - failures}/"
          f"{len(DEAD_FILES)} dead files removed")
    raise SystemExit(1 if failures else 0)
