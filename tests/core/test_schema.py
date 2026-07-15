"""
Smoke + behaviour tests for ``core.schema``.

Covers:
* Module import + module-level constants (``SCHEMA_VERSION``, ``SCHEMA_DESCRIPTION``)
* :func:`get_db_path` — resolves relative ``sqlite:///`` URLs against the
  project root and leaves absolute paths untouched
* :func:`apply_schema` — runs every DDL statement and is idempotent
* :func:`init_db` — opens (or creates) the DB, applies schema, records the
  schema version exactly once, and is safe to call repeatedly
* :func:`list_tables` — returns a sorted list of user-visible tables and
  filters out the internal ``_schema_version`` bookkeeping table
* Connection row factory — returned connection exposes ``sqlite3.Row`` rows
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from core import schema

# ---------------------------------------------------------------------------
# 1. Import smoke + module-level constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_exports():
    """Module imports cleanly and exposes the public API."""
    assert schema.SCHEMA_VERSION == 3
    assert isinstance(schema.SCHEMA_DESCRIPTION, str)
    assert "buddha_recitation_sessions" in schema.SCHEMA_DESCRIPTION
    assert "healing_dialogue_sessions" in schema.SCHEMA_DESCRIPTION

    # Public API surface
    assert callable(schema.apply_schema)
    assert callable(schema.init_db)
    assert callable(schema.get_db_path)
    assert callable(schema.get_project_root)
    assert callable(schema.list_tables)


# ---------------------------------------------------------------------------
# 2. get_db_path — relative + absolute handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_db_path_resolves_relative_url_against_project_root():
    """A relative ``sqlite:///./<file>`` URL resolves to the project root."""
    db_path = schema.get_db_path("sqlite:///./unit_test_schema.db")
    # Should be an absolute path inside the project root
    assert os.path.isabs(db_path), f"expected absolute path, got {db_path}"
    project_root = schema.get_project_root()
    # Path lives underneath the project root
    Path(db_path).resolve().relative_to(project_root)


@pytest.mark.unit
def test_get_db_path_absolute_url_passes_through():
    """An absolute filesystem path in the URL is returned unchanged."""
    absolute = "C:/tmp/absolute_db.sqlite" if Path("C:/").exists() else "/tmp/absolute_db.sqlite"
    db_path = schema.get_db_path(f"sqlite:///{absolute}")
    # Strip the sqlite:/// prefix exactly; the file does not need to exist.
    assert db_path == absolute


# ---------------------------------------------------------------------------
# 3. apply_schema — idempotent
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_schema_creates_all_tables_idempotently(tmp_path: Path):
    """``apply_schema`` creates every table and can be re-run safely."""
    db = tmp_path / "apply_test.db"
    conn = sqlite3.connect(str(db))
    try:
        schema.apply_schema(conn)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        # All the well-known tables are present
        for required in (
            "extraction_runs",
            "extraction_results",
            "astrology_locations",
            "healing_dialogue_sessions",
            "buddha_recitation_sessions",
            "outlook_narratives",
            "saved_natal_charts",
            "blessing_targets",
            "blessing_sessions",
            "_schema_version",
        ):
            assert required in tables, f"missing table: {required}"

        # Calling again is a no-op (does not raise)
        schema.apply_schema(conn)
        tables_after = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert tables == tables_after
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. init_db — full happy path, idempotent version recording
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_init_db_creates_db_records_version_and_is_idempotent(tmp_path: Path):
    """``init_db`` opens the DB, applies the schema, and records the version once."""
    db_file = str(tmp_path / "init_test.db")
    conn1 = schema.init_db(db_file)
    try:
        # Tables are present
        tables = {row[0] for row in conn1.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "extraction_runs" in tables
        assert "buddha_recitation_sessions" in tables

        # Version recorded exactly once for SCHEMA_VERSION
        versions = [row[0] for row in conn1.execute("SELECT version FROM _schema_version ORDER BY id").fetchall()]
        assert versions == [schema.SCHEMA_VERSION]
    finally:
        conn1.close()

    # A second call should NOT add another _schema_version row
    conn2 = schema.init_db(db_file)
    try:
        versions = [row[0] for row in conn2.execute("SELECT version FROM _schema_version ORDER BY id").fetchall()]
        assert versions == [schema.SCHEMA_VERSION], "init_db must not duplicate the _schema_version row on re-run"
    finally:
        conn2.close()


# ---------------------------------------------------------------------------
# 5. list_tables — excludes _schema_version, returns sorted list
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_list_tables_excludes_schema_version_and_is_sorted(tmp_path: Path):
    """``list_tables`` returns a sorted list without the bookkeeping table."""
    db_file = str(tmp_path / "list_test.db")
    conn = schema.init_db(db_file)
    try:
        tables = schema.list_tables(conn)
    finally:
        conn.close()

    assert isinstance(tables, list)
    assert "_schema_version" not in tables
    assert tables == sorted(tables)
    # Spot-check a few well-known tables
    assert "extraction_runs" in tables
    assert "buddha_recitation_sessions" in tables


# ---------------------------------------------------------------------------
# 6. init_db — connection row factory + autocommit semantics
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_init_db_returns_connection_with_row_factory(tmp_path: Path):
    """The connection returned by ``init_db`` uses ``sqlite3.Row`` for rows."""
    db_file = str(tmp_path / "row_test.db")
    conn = schema.init_db(db_file)
    try:
        assert conn.row_factory is sqlite3.Row
        # sqlite3.Row supports column access by name
        row = conn.execute("SELECT version FROM _schema_version ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        assert row["version"] == schema.SCHEMA_VERSION
    finally:
        conn.close()
