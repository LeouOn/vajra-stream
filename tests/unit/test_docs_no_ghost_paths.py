"""Guard against ghost-path references in canonical documentation.

Wave 3 Task 18 / Evaluation Issue 5.8.

Documentation drift left several canonical docs referencing files and
directories that no longer exist (deleted entrypoints, ghost subpackages,
nonexistent docs subdirectories). This test encodes the Issue 5.8 ghost-path
inventory so regressions are caught immediately.

The test is intentionally concrete (it lists the known ghost tokens) rather
than generically scanning the filesystem, because a generic scan would be
brittle against legitimate external references and false positives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# The four canonical docs that must remain ghost-path-free.
CANONICAL_DOCS = [
    REPO_ROOT / "PROJECT_STRUCTURE.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "README.md",
    REPO_ROOT / "tests" / "README.md",
]


# Ghost references catalogued in Evaluation Issue 5.8.
# Each tuple: (doc path relative to repo root, forbidden substring in doc text).
GHOST_REFERENCES: list[tuple[str, str]] = [
    # --- PROJECT_STRUCTURE.md: deleted root entrypoints (lines 323-325) ---
    ("PROJECT_STRUCTURE.md", "vajra_stream.py"),
    ("PROJECT_STRUCTURE.md", "vajra_stream_v2.py"),
    ("PROJECT_STRUCTURE.md", "start_full_system.py"),
    # --- PROJECT_STRUCTURE.md: ghost core/services/ contents (line 96) ---
    ("PROJECT_STRUCTURE.md", "services/audio_service.py"),
    ("PROJECT_STRUCTURE.md", "services/vajra_service.py"),
    # --- PROJECT_STRUCTURE.md: ghost config/enhanced_settings.py (line 193) ---
    ("PROJECT_STRUCTURE.md", "enhanced_settings.py"),
    # --- PROJECT_STRUCTURE.md: ghost scripts/visualizer.py (line 228) ---
    ("PROJECT_STRUCTURE.md", "scripts/visualizer.py"),
    # --- README.md: deleted launchers (lines 75-76) ---
    ("README.md", "start_web_server.py"),
    ("README.md", "start_web_server.bat"),
    # --- README.md: deleted entrypoint + variant (lines 96, 202) ---
    ("README.md", "vajra_stream_v2"),
    ("README.md", "main_fixed5_stable"),
    # --- docs/README.md: 6 nonexistent subdirs in tree (lines 11-17) ---
    ("docs/README.md", "api/"),
    ("docs/README.md", "architecture/"),
    ("docs/README.md", "features/"),
    ("docs/README.md", "guides/"),
    ("docs/README.md", "implementation/"),
    ("docs/README.md", "radionics/"),
    # --- docs/README.md: broken links into those ghost subdirs (lines 38-40) ---
    ("docs/README.md", "UNIFIED_API_ARCHITECTURE.md"),
    ("docs/README.md", "WEBSOCKET_RADIONICS_PROTOCOL.md"),
    ("docs/README.md", "INTEGRATION_VERIFICATION.md"),
    # --- tests/README.md: deleted test files (lines 14-15) ---
    ("tests/README.md", "test_integration_phase2.py"),
    ("tests/README.md", "test_api_endpoints.py"),
]


@pytest.mark.parametrize(
    "doc_rel,ghost",
    GHOST_REFERENCES,
    ids=[f"{d.replace('/', '__')}__{g.replace('/', '_')}" for d, g in GHOST_REFERENCES],
)
def test_canonical_docs_have_no_ghost_paths(doc_rel: str, ghost: str) -> None:
    """No canonical doc may reference a known ghost path (Issue 5.8)."""
    doc_path = REPO_ROOT / doc_rel
    assert doc_path.exists(), f"canonical doc itself is missing: {doc_rel}"
    text = doc_path.read_text(encoding="utf-8")
    assert ghost not in text, (
        f"ghost-path reference {ghost!r} still present in {doc_rel} (Evaluation Issue 5.8, remediation-18)"
    )


def test_all_canonical_docs_exist() -> None:
    """All four canonical docs must be present for the ghost-path guard to be valid."""
    missing = [str(p.relative_to(REPO_ROOT)) for p in CANONICAL_DOCS if not p.exists()]
    assert not missing, f"canonical docs missing: {missing}"


def test_docs_archive_directory_exists() -> None:
    """docs/_archive/ must exist as the deliberate one-time archive location."""
    archive_dir = REPO_ROOT / "docs" / "_archive"
    assert archive_dir.is_dir(), (
        "docs/_archive/ must exist as deliberate one-time archive (remediation-18, Oracle Phase-1 finding)"
    )


def test_archived_docs_carry_deprecation_banner() -> None:
    """Every archived .md doc must carry a top-of-file deprecation banner.

    If no docs needed to be archived, this test is skipped (legitimate empty archive).
    """
    archive_dir = REPO_ROOT / "docs" / "_archive"
    md_files = sorted(archive_dir.glob("*.md"))
    if not md_files:
        pytest.skip("no archived docs required for remediation-18")
    for md_file in md_files:
        head = md_file.read_text(encoding="utf-8")[:600].lower()
        assert "archived" in head and "deprecated" in head, (
            f"archived doc {md_file.name} is missing a deprecation banner "
            f"(must mention 'archived' and 'deprecated' near the top)"
        )
