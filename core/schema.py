"""
core.schema — Single source of truth for the Vajra.Stream SQLite schema.

Provides :func:`init_db` and :func:`apply_schema` so that *every* part of the
codebase that needs a table — endpoint modules, background daemons, scripts —
goes through the same idempotent migration runner instead of sprinkling
``CREATE TABLE IF NOT EXISTS`` calls across the tree.

Schema versioning is tracked in the ``_schema_version`` table. Each call to
:func:`apply_schema` records the current :data:`SCHEMA_VERSION` along with a
human-readable description and a UTC timestamp.

Public API
----------
- :data:`SCHEMA_VERSION`  — integer; bump when the schema changes
- :func:`apply_schema`    — run all ``CREATE TABLE IF NOT EXISTS`` on a conn
- :func:`init_db`         — open (or create) ``vajra_stream.db`` and apply
- :func:`get_db_path`     — resolve the project-root-relative DB path

Conventions
-----------
- All datetimes stored as ISO-8601 strings in UTC.
- Foreign keys are declared but ``PRAGMA foreign_keys=ON`` is *not* enabled by
  default (SQLite default). Turn it on in caller code if you need cascade
  semantics; the extractor tables are intentionally permissive.
- New tables: append to :data:`_TABLE_DDL` and bump :data:`SCHEMA_VERSION`.
- Existing tables: never modify the DDL of a shipped table; add a new
  ``CREATE TABLE IF NOT EXISTS`` statement for the new shape and migrate data
  in code if needed.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION: int = 1
SCHEMA_DESCRIPTION: str = (
    "Initial centralized schema: extraction_runs, extraction_results, "
    "astrology_locations, plus idempotent CREATE TABLE IF NOT EXISTS for all "
    "pre-existing vajra-stream tables."
)


def get_project_root() -> Path:
    """Locate the project root (directory holding ``pyproject.toml`` or
    ``vajra_stream.db``) by walking up from this file."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / "vajra_stream.db").exists():
            return parent
    return current.parent


def get_db_path(db_url: str | None = None) -> str:
    """Resolve the SQLite database file path.

    Honors ``settings.DATABASE_URL`` (``sqlite:///./vajra_stream.db`` style)
    when available, otherwise falls back to ``<project_root>/vajra_stream.db``.

    The import of :mod:`backend.app.config` is deferred so this module can be
    imported during cold-start paths (tests, scripts) without requiring the
    full backend settings stack.
    """
    if db_url is None:
        try:
            from backend.app.config import settings  # type: ignore

            db_url = settings.DATABASE_URL
        except Exception:
            db_url = "sqlite:///./vajra_stream.db"

    db_path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = str((get_project_root() / db_path).resolve())
    return db_path


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------
# Each entry is a (table_name, ddl) pair. ``CREATE TABLE IF NOT EXISTS`` is
# used so re-running the migration is a no-op. NEVER alter the DDL of a
# shipped table — add a new table instead and migrate data in code.
# ---------------------------------------------------------------------------

_TABLE_DDL: tuple[tuple[str, str], ...] = (
    # --- Migration bookkeeping ---
    (
        "_schema_version",
        """
        CREATE TABLE IF NOT EXISTS _schema_version (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            version     INTEGER NOT NULL,
            applied_at  TIMESTAMP NOT NULL,
            description TEXT
        )
        """,
    ),
    # --- New: astrology extraction sweep (Task 1) ---
    (
        "extraction_runs",
        """
        CREATE TABLE IF NOT EXISTS extraction_runs (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at        TIMESTAMP NOT NULL,
            config_json       TEXT,
            status            TEXT NOT NULL
                                CHECK (status IN ('queued','running','done','error','partial')),
            total_tuples      INTEGER DEFAULT 0,
            completed_tuples  INTEGER DEFAULT 0,
            error_message     TEXT,
            algo_version      TEXT
        )
        """,
    ),
    (
        "extraction_results",
        """
        CREATE TABLE IF NOT EXISTS extraction_results (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id              INTEGER NOT NULL,
            tuple_idx           INTEGER NOT NULL,
            date_iso            TEXT,
            lat                 REAL,
            lon                 REAL,
            chart_json          TEXT,
            formatted_markdown  TEXT,
            formatted_json      TEXT,
            latency_ms          INTEGER,
            status              TEXT,
            error_message       TEXT,
            created_at          TIMESTAMP
        )
        """,
    ),
    (
        "extraction_results_idx_run_id",
        "CREATE INDEX IF NOT EXISTS idx_extraction_results_run_id ON extraction_results (run_id)",
    ),
    (
        "astrology_locations",
        """
        CREATE TABLE IF NOT EXISTS astrology_locations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            lat         REAL,
            lon         REAL,
            category    TEXT
                        CHECK (category IN ('sacred_site','astrocartography_anchor','custom')),
            timezone    TEXT,
            tags_json   TEXT,
            notes       TEXT,
            created_at  TIMESTAMP
        )
        """,
    ),
    (
        "astrology_locations_idx_category",
        "CREATE INDEX IF NOT EXISTS idx_astrology_locations_category ON astrology_locations (category)",
    ),
    # --- Pre-existing: outlook_narratives ---
    # DDL must match the column list created in
    # backend/app/api/v1/endpoints/outlook.py:73-88 exactly.
    (
        "outlook_narratives",
        """
        CREATE TABLE IF NOT EXISTS outlook_narratives (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            type                TEXT NOT NULL,
            genre               TEXT,
            languages           TEXT,
            lat                 REAL,
            lon                 REAL,
            date_generated      TIMESTAMP,
            content             TEXT,
            astrology_context   TEXT,
            divination_context  TEXT,
            divination_raw      TEXT,
            entities_invoked    TEXT
        )
        """,
    ),
    # --- Pre-existing: saved_natal_charts ---
    # DDL must match backend/app/api/v1/endpoints/astrology.py:33-49 exactly.
    (
        "saved_natal_charts",
        """
        CREATE TABLE IF NOT EXISTS saved_natal_charts (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            name              TEXT NOT NULL,
            birth_time_iso    TEXT NOT NULL,
            latitude          REAL NOT NULL,
            longitude         REAL NOT NULL,
            timezone          TEXT NOT NULL,
            city              TEXT NOT NULL,
            description       TEXT DEFAULT '',
            tags              TEXT DEFAULT '',
            cached_chart_data TEXT,
            notes             TEXT DEFAULT '',
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        )
        """,
    ),
    # --- Pre-existing: agent_suggestions ---
    # DDL must match backend/app/api/v1/endpoints/agent_suggestions.py:22-40.
    (
        "failed_tool_calls",
        """
        CREATE TABLE IF NOT EXISTS failed_tool_calls (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      TEXT,
            tool_name      TEXT,
            arguments      TEXT,
            error_message  TEXT
        )
        """,
    ),
    (
        "intentional_paths",
        """
        CREATE TABLE IF NOT EXISTS intentional_paths (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT,
            agent_id        TEXT,
            intention       TEXT,
            missing_tools   TEXT,
            context         TEXT
        )
        """,
    ),
    # --- Pre-existing: sessions, intentions, generated_content, healing_history,
    #     scheduled_events, blessing_targets, blessing_sessions,
    #     mantra_dedications, user_preferences ---
    # DDL preserved verbatim from scripts/setup_database.py + core/compassionate_blessings.py
    # to keep fresh-DB bootstraps working. Do not edit.
    (
        "sessions",
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_type  TEXT,
            start_time    TIMESTAMP,
            end_time      TIMESTAMP,
            intention     TEXT,
            focus_area    TEXT,
            settings      TEXT,
            notes         TEXT
        )
        """,
    ),
    (
        "intentions",
        """
        CREATE TABLE IF NOT EXISTS intentions (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            intention_text       TEXT UNIQUE,
            created_at           TIMESTAMP,
            times_used           INTEGER DEFAULT 1,
            category             TEXT,
            parent_intention_id  INTEGER,
            FOREIGN KEY (parent_intention_id) REFERENCES intentions(id)
        )
        """,
    ),
    (
        "generated_content",
        """
        CREATE TABLE IF NOT EXISTS generated_content (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type    TEXT,
            content         TEXT,
            created_at      TIMESTAMP,
            intention_id    INTEGER,
            quality_rating  INTEGER,
            archived        BOOLEAN DEFAULT 0,
            FOREIGN KEY (intention_id) REFERENCES intentions(id)
        )
        """,
    ),
    (
        "healing_history",
        """
        CREATE TABLE IF NOT EXISTS healing_history (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          INTEGER,
            chakra              TEXT,
            meridian            TEXT,
            duration_minutes    INTEGER,
            frequencies_used    TEXT,
            subjective_result   TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
        """,
    ),
    (
        "scheduled_events",
        """
        CREATE TABLE IF NOT EXISTS scheduled_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type      TEXT,
            target_datetime TIMESTAMP,
            location_lat    REAL,
            location_lon    REAL,
            intention       TEXT,
            status          TEXT DEFAULT 'pending',
            created_at      TIMESTAMP
        )
        """,
    ),
    (
        "blessing_targets",
        """
        CREATE TABLE IF NOT EXISTS blessing_targets (
            identifier              TEXT PRIMARY KEY,
            name                    TEXT,
            category                TEXT NOT NULL,
            description             TEXT,
            case_number             TEXT,
            relevant_date           TEXT,
            discovery_date          TEXT,
            last_updated            TEXT NOT NULL,
            coordinates_json        TEXT,
            photograph_path         TEXT,
            additional_data_json    TEXT,
            mantras_dedicated       INTEGER DEFAULT 0,
            prayer_wheel_rotations  INTEGER DEFAULT 0,
            dedication_sessions_json TEXT,
            intention               TEXT,
            priority                INTEGER DEFAULT 5
        )
        """,
    ),
    (
        "blessing_sessions",
        """
        CREATE TABLE IF NOT EXISTS blessing_sessions (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date           TEXT NOT NULL,
            mantra_type            TEXT,
            total_mantras          INTEGER DEFAULT 0,
            total_rotations        INTEGER DEFAULT 0,
            targets_blessed        INTEGER DEFAULT 0,
            allocation_method      TEXT,
            notes                  TEXT,
            astrological_data_json TEXT
        )
        """,
    ),
    (
        "mantra_dedications",
        """
        CREATE TABLE IF NOT EXISTS mantra_dedications (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            target_identifier TEXT NOT NULL,
            session_id        INTEGER,
            mantra_type       TEXT,
            mantras_count     INTEGER DEFAULT 0,
            dedication_date   TEXT NOT NULL,
            dedicator         TEXT,
            notes             TEXT,
            FOREIGN KEY (target_identifier) REFERENCES blessing_targets(identifier),
            FOREIGN KEY (session_id) REFERENCES blessing_sessions(id)
        )
        """,
    ),
    (
        "user_preferences",
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
        """,
    ),
)


def apply_schema(conn: sqlite3.Connection) -> None:
    """Run every ``CREATE TABLE IF NOT EXISTS`` in :data:`_TABLE_DDL` on ``conn``.

    Safe to call repeatedly: every statement is idempotent.

    Does NOT record the schema version; use :func:`init_db` for that.
    """
    cursor = conn.cursor()
    for _name, ddl in _TABLE_DDL:
        cursor.execute(ddl)
    conn.commit()


def _current_schema_version(conn: sqlite3.Connection) -> int | None:
    """Return the highest ``_schema_version.version`` row, or None if empty."""
    try:
        row = conn.execute("SELECT MAX(version) FROM _schema_version").fetchone()
    except sqlite3.OperationalError:
        # Table doesn't exist yet — caller is about to create it.
        return None
    if not row or row[0] is None:
        return None
    return int(row[0])


def _record_schema_version(conn: sqlite3.Connection) -> None:
    """Insert a ``_schema_version`` row for the current :data:`SCHEMA_VERSION`."""
    conn.execute(
        "INSERT INTO _schema_version (version, applied_at, description) VALUES (?, ?, ?)",
        (
            SCHEMA_VERSION,
            datetime.now(timezone.utc).isoformat(),
            SCHEMA_DESCRIPTION,
        ),
    )
    conn.commit()


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    """Open (or create) the SQLite database and apply the full schema.

    This is the **single public entry point** for bootstrapping the database.
    Endpoint modules and scripts should call this function instead of issuing
    their own ``CREATE TABLE IF NOT EXISTS`` statements.

    Idempotent: a fresh database gets all tables; an already-migrated
    database is left untouched (no error, no duplicate ``_schema_version``
    rows for the current version).

    Returns the open :class:`sqlite3.Connection`. The caller is responsible
    for closing it (or using a ``with`` block).
    """
    if db_path is None:
        db_path = get_db_path()

    # ``check_same_thread=False`` lets the FastAPI thread pool share the
    # connection; callers that need stricter isolation should still open their
    # own short-lived connections.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    apply_schema(conn)

    # Only record a new schema-version row if one isn't already present for
    # the current version — keeps ``init_db()`` truly idempotent.
    current = _current_schema_version(conn)
    if current is None or current < SCHEMA_VERSION:
        _record_schema_version(conn)

    return conn


def list_tables(conn: sqlite3.Connection | None = None) -> list[str]:
    """Return the sorted list of user-visible tables in the database.

    Useful for tests and sanity checks. Excludes the internal ``_schema_version``
    bookkeeping table from the returned list.
    """
    own_conn = conn is None
    if own_conn:
        conn = init_db()
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return [r[0] for r in rows if r[0] != "_schema_version"]
    finally:
        if own_conn:
            conn.close()


__all__: Iterable[str] = (
    "SCHEMA_VERSION",
    "SCHEMA_DESCRIPTION",
    "apply_schema",
    "init_db",
    "get_db_path",
    "get_project_root",
    "list_tables",
)
