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
* ``astrological_snapshots`` (v5) — the table and its indexes are created, the
  INSERT issued by ``scripts/radionics_operation.py`` still fits the DDL, and
  that writer really does persist a non-NULL ``session_id``
* ``llm_generations`` and ``generated_visuals`` (v6) — both tables and their
  session indexes are created, and the two radionics writers that had no DDL
  really do persist rows
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

import pytest

from core import schema

# ---------------------------------------------------------------------------
# 1. Import smoke + module-level constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_exports():
    """Module imports cleanly and exposes the public API."""
    assert schema.SCHEMA_VERSION == 6
    assert isinstance(schema.SCHEMA_DESCRIPTION, str)
    assert "llm_generations" in schema.SCHEMA_DESCRIPTION
    assert "generated_visuals" in schema.SCHEMA_DESCRIPTION
    assert "astrological_snapshots" in schema.SCHEMA_DESCRIPTION
    assert "outlook_narratives" in schema.SCHEMA_DESCRIPTION
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
            "astrological_snapshots",
            "llm_generations",
            "generated_visuals",
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


# ---------------------------------------------------------------------------
# 7. _COLUMN_ADDITIONS — guarded ALTER migrates old databases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_column_additions_migrate_old_databases(tmp_path: Path):
    """A database with the pre-v4 outlook_narratives shape gains the new columns.

    Existing rows survive with NULL in the added columns; re-running
    init_db is a no-op.
    """
    db = tmp_path / "old_shape.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE outlook_narratives (
        id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, genre TEXT,
        languages TEXT, lat REAL, lon REAL, date_generated TIMESTAMP, content TEXT,
        astrology_context TEXT, divination_context TEXT, divination_raw TEXT,
        entities_invoked TEXT)"""
    )
    conn.execute("INSERT INTO outlook_narratives (type, genre, content) VALUES ('single', 'healing', 'kept row')")
    conn.commit()
    conn.close()

    c1 = schema.init_db(str(db))
    try:
        cols = {r[1] for r in c1.execute("PRAGMA table_info(outlook_narratives)")}
        assert {"model_used", "provider_used"} <= cols
        row = c1.execute("SELECT content, model_used FROM outlook_narratives").fetchone()
        assert row["content"] == "kept row"
        assert row["model_used"] is None
    finally:
        c1.close()

    c2 = schema.init_db(str(db))
    try:
        versions = [r[0] for r in c2.execute("SELECT version FROM _schema_version").fetchall()]
        assert versions == [schema.SCHEMA_VERSION]
    finally:
        c2.close()


# ---------------------------------------------------------------------------
# 8. astrological_snapshots — v5 table exists and accepts the radionics INSERT
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_astrological_snapshots_accepts_radionics_insert(tmp_path: Path):
    """The v5 ``astrological_snapshots`` table matches the writer's INSERT.

    ``core/schema.py`` creates the table plus two indexes, and
    ``scripts/radionics_operation.py`` writes one row per broadcast. Nothing
    tied the two together, so a column renamed or dropped in the DDL would only
    surface at broadcast time, where the script swallows the error behind
    ``⚠ Astrology snapshot save failed``.

    The INSERT below copies the column list from
    ``RadionicsOperation._save_astrology_snapshot`` in
    ``scripts/radionics_operation.py``. That module is not imported here — it
    pulls in the audio/LLM stack — so the column list is duplicated on purpose
    and this test is what keeps the copy honest.
    """
    db_file = str(tmp_path / "astro_snapshots_test.db")
    conn = schema.init_db(db_file)
    try:
        objects = {(row["type"], row["name"]) for row in conn.execute("SELECT type, name FROM sqlite_master")}
        assert ("table", "astrological_snapshots") in objects
        assert ("index", "idx_astro_snapshots_ts") in objects
        assert ("index", "idx_astro_snapshots_session") in objects

        # Same column list as scripts/radionics_operation.py::_save_astrology_snapshot.
        # session_id is included: the writer used to gate on self.session_id but
        # never wrote it, so every snapshot landed unlinked despite the column
        # and idx_astro_snapshots_session existing for exactly that lookup.
        # The script binds a ``datetime`` there via sqlite3's default adapter,
        # which is deprecated since Python 3.12 and stores TEXT anyway, so the
        # sample value is passed as the string that actually lands in the column.
        timestamp = "2026-10-01 15:37:47.096277"
        moon_phase = "Waning Gibbous"
        moon_illumination = 0.62
        lunar_mansion = "Purva Bhadrapada"
        recommended_frequencies = "528.0,432.0,396.0"
        session_id = 7

        conn.execute(
            """
            INSERT INTO astrological_snapshots
            (timestamp, moon_phase, moon_illumination, lunar_mansion,
             recommended_frequencies, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (timestamp, moon_phase, moon_illumination, lunar_mansion, recommended_frequencies, session_id),
        )
        conn.commit()

        row = conn.execute(
            """SELECT timestamp, moon_phase, moon_illumination, lunar_mansion,
                      recommended_frequencies, session_id
               FROM astrological_snapshots"""
        ).fetchone()
        assert row is not None
        assert row["timestamp"] == timestamp
        assert row["moon_phase"] == moon_phase
        assert row["moon_illumination"] == moon_illumination
        assert row["lunar_mansion"] == lunar_mansion
        assert row["recommended_frequencies"] == recommended_frequencies
        # The writer now links each snapshot to its session.
        assert row["session_id"] == session_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 9. radionics_operation._save_astrology_snapshot — real writer, real linkage
# ---------------------------------------------------------------------------

_RADIONICS_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "radionics_operation.py"


def _load_radionics_operation():
    """Load ``scripts/radionics_operation.py`` by file location.

    The script is not an importable package member, so it is loaded with
    ``spec_from_file_location`` — the same pattern used by
    ``tests/unit/test_divination.py`` and
    ``tests/unit/test_orchestrator_bridge_shutdown.py``.

    Only a genuinely missing optional dependency is allowed to skip.
    ``swisseph`` is checked up front with ``importorskip`` (matching
    ``tests/core/test_astrology.py``), and a missing import inside the script
    surfaces as ``ImportError`` — both are legitimate skips. Every other
    exception (``SyntaxError``, ``NameError``, a bad edit) is allowed to
    propagate so it fails the test loudly rather than hiding a real bug behind
    a silent skip.
    """
    pytest.importorskip("swisseph")
    spec = importlib.util.spec_from_file_location("_radionics_operation_under_test", _RADIONICS_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"scripts/radionics_operation.py has an unimportable dependency: {exc!r}")
    return module


@pytest.mark.unit
def test_save_astrology_snapshot_persists_session_id(tmp_path: Path):
    """Regression: the writer gated on ``session_id`` but never wrote it.

    ``_save_astrology_snapshot`` returns early unless ``self.session_id`` is
    set, yet its INSERT omitted the column entirely — so every snapshot was
    stored unlinked, leaving the nullable column and
    ``idx_astro_snapshots_session`` with nothing to index. This exercises the
    real method rather than a copied column list, so the link is proven at the
    writer, not just at the DDL.
    """
    module = _load_radionics_operation()

    db_file = str(tmp_path / "radionics_snapshot.db")
    # init_db applies and commits the schema; the writer opens its own
    # connection, so this one is closed before the call.
    schema.init_db(db_file).close()

    # __new__ skips __init__, which would spin up the audio/LLM/TTS stack.
    # _save_astrology_snapshot only touches db_path and session_id.
    op = module.RadionicsOperation.__new__(module.RadionicsOperation)
    op.db_path = db_file
    op.session_id = 7

    energetics = {
        "moon_phase": {"phase_name": "Waning Gibbous", "illumination": 0.62},
        "lunar_mansion": {"name": "Purva Bhadrapada"},
    }
    op._save_astrology_snapshot(energetics, [432, 528])

    check = sqlite3.connect(db_file)
    check.row_factory = sqlite3.Row
    try:
        row = check.execute(
            """SELECT moon_phase, moon_illumination, lunar_mansion,
                      recommended_frequencies, session_id
               FROM astrological_snapshots"""
        ).fetchone()
    finally:
        check.close()

    # The method swallows its own exceptions behind a printed warning, so a
    # broken INSERT would look like "no row" — assert the row landed first.
    assert row is not None, "no snapshot row was written"
    assert row["session_id"] == 7, "snapshot was saved unlinked to its session"
    # Spot-check that the rest of the payload still binds correctly.
    assert row["moon_phase"] == "Waning Gibbous"
    assert row["moon_illumination"] == 0.62
    assert row["lunar_mansion"] == "Purva Bhadrapada"
    assert row["recommended_frequencies"] == "432,528"


# ---------------------------------------------------------------------------
# 10. _load_radionics_operation — skips only on a missing dependency
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("broken_source", "expected"),
    [
        pytest.param("def f(:\n", SyntaxError, id="syntax-error"),  # unparseable script
        pytest.param("undefined_name\n", NameError, id="name-error"),  # bad edit at module level
    ],
)
def test_load_radionics_operation_propagates_real_script_errors(tmp_path, monkeypatch, broken_source, expected):
    """A broken script must fail the test, not skip it.

    Pins the ``except ImportError`` narrowing in ``_load_radionics_operation``.
    Re-broadening it to ``except Exception`` would swallow these errors and
    skip, and this test must report that as a FAILURE — a skip here would
    recreate the very silent-green bug it is guarding against.
    """
    # The helper importorskips swisseph before loading anything. Without this,
    # a swisseph-less environment would skip for the wrong reason.
    pytest.importorskip("swisseph")
    broken = tmp_path / "radionics_operation.py"
    broken.write_text(broken_source)
    monkeypatch.setattr(sys.modules[__name__], "_RADIONICS_SCRIPT", broken)
    try:
        with pytest.raises(expected):
            _load_radionics_operation()
    except pytest.skip.Exception as exc:
        # Skipped rather than raised: the guard was re-broadened. Fail loudly.
        pytest.fail(f"helper skipped instead of raising {expected.__name__}: {exc}")


@pytest.mark.unit
def test_load_radionics_operation_still_skips_on_missing_dependency(tmp_path, monkeypatch):
    """A genuinely unimportable dependency must still skip, not fail.

    The other side of the narrowing: narrow the guard too far (bare
    ``except:`` with no skip, or letting ImportError escape) and environments
    missing an optional dep would break the suite outright.
    """
    pytest.importorskip("swisseph")
    broken = tmp_path / "radionics_operation.py"
    broken.write_text("from os import nope_nope\n")
    monkeypatch.setattr(sys.modules[__name__], "_RADIONICS_SCRIPT", broken)
    # Assert the skip INSIDE pytest.raises rather than letting it escape and
    # marking this test skipped - a skip here would hide the regression too.
    with pytest.raises(pytest.skip.Exception):
        _load_radionics_operation()


# ---------------------------------------------------------------------------
# 11. llm_generations + generated_visuals — v6 tables fit the radionics writers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_v6_tables_accept_radionics_writer_inserts(tmp_path: Path):
    """v6 adds the two tables the radionics writers had no DDL for.

    ``_save_llm_generation`` and ``_save_visual`` both swallow their errors
    behind a printed warning, so with no ``CREATE TABLE`` they failed on "no
    such table" and nothing went red. These asserts pin the DDL plus the exact
    column lists both writers send.
    """
    conn = schema.init_db(str(tmp_path / "v6_tables_test.db"))
    try:
        objects = {(row["type"], row["name"]) for row in conn.execute("SELECT type, name FROM sqlite_master")}
        assert ("table", "llm_generations") in objects
        assert ("table", "generated_visuals") in objects
        assert ("index", "idx_llm_generations_session") in objects
        assert ("index", "idx_generated_visuals_session") in objects

        # Column list from scripts/radionics_operation.py::_save_llm_generation.
        # Both v6 writers bind datetime.now().isoformat(sep=" ") rather than a
        # raw datetime, so no sqlite3 adapter is involved and a plain string
        # is exactly what lands in the column.
        llm_timestamp = "2026-10-02 06:00:00.000000"
        conn.execute(
            """
            INSERT INTO llm_generations
            (session_id, prompt_type, prompt_text, generated_text, model_used, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (7, "blessing", "prompt text", "generated text", "none", llm_timestamp),
        )
        # Column list from scripts/radionics_operation.py::_save_visual.
        created_at = "2026-10-02 06:00:01.000000"
        conn.execute(
            """
            INSERT INTO generated_visuals
            (session_id, intention, filepath, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (7, "peace", "/tmp/x.png", created_at),
        )
        conn.commit()

        llm_row = conn.execute(
            """SELECT session_id, prompt_type, prompt_text, generated_text,
                      model_used, timestamp
               FROM llm_generations"""
        ).fetchone()
        assert llm_row is not None
        assert llm_row["session_id"] == 7
        assert llm_row["prompt_type"] == "blessing"
        assert llm_row["prompt_text"] == "prompt text"
        assert llm_row["generated_text"] == "generated text"
        assert llm_row["model_used"] == "none"
        assert llm_row["timestamp"] == llm_timestamp

        visual_row = conn.execute(
            "SELECT session_id, intention, filepath, created_at FROM generated_visuals"
        ).fetchone()
        assert visual_row is not None
        assert visual_row["session_id"] == 7
        assert visual_row["intention"] == "peace"
        assert visual_row["filepath"] == "/tmp/x.png"
        assert visual_row["created_at"] == created_at
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 12. radionics_operation v6 writers — rows actually land
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_v6_writers_persist_rows(tmp_path: Path):
    """The real ``_save_llm_generation`` / ``_save_visual`` must persist rows.

    Before v6 both writers hit "no such table" and swallowed it behind a
    printed warning, so a broadcast recorded nothing and no test went red.
    This drives the writers themselves rather than a copied column list — the
    copied list cannot notice a table that does not exist.
    """
    module = _load_radionics_operation()

    db_file = str(tmp_path / "v6_writers.db")
    # init_db applies and commits the schema; the writers open their own
    # connections, so this one is closed before the calls.
    schema.init_db(db_file).close()

    # __new__ skips __init__, which would spin up the audio/LLM/TTS stack.
    op = module.RadionicsOperation.__new__(module.RadionicsOperation)
    op.db_path = db_file
    op.session_id = 7
    op.llm = None  # _save_llm_generation then stores model_used "none"

    op._save_llm_generation("blessing", "prompt text", "generated text")
    op._save_visual("peace", "/tmp/x.png")

    check = sqlite3.connect(db_file)
    check.row_factory = sqlite3.Row
    try:
        llm_rows = check.execute("SELECT * FROM llm_generations").fetchall()
        visual_rows = check.execute("SELECT * FROM generated_visuals").fetchall()
    finally:
        check.close()

    # If the tables are ABSENT the SELECTs above raise sqlite3.OperationalError
    # ("no such table") and the test fails there. The row-count assertions are
    # what catch the remaining silent cases: a table that exists but stays empty
    # because the writer's own try/except swallowed an error. Asserting the
    # count before the contents keeps that reported as "no row written" rather
    # than a confusing wrong-value failure.
    assert len(llm_rows) == 1, "no llm_generations row was written"
    assert llm_rows[0]["session_id"] == 7
    assert llm_rows[0]["prompt_type"] == "blessing"
    assert llm_rows[0]["prompt_text"] == "prompt text"
    assert llm_rows[0]["generated_text"] == "generated text"
    # llm is None, so the writer records the sentinel rather than a model name.
    assert llm_rows[0]["model_used"] == "none"
    # Timestamps are generated at call time, so only assert they were written.
    assert llm_rows[0]["timestamp"]

    assert len(visual_rows) == 1, "no generated_visuals row was written"
    assert visual_rows[0]["session_id"] == 7
    assert visual_rows[0]["intention"] == "peace"
    assert visual_rows[0]["filepath"] == "/tmp/x.png"
    assert visual_rows[0]["created_at"]
