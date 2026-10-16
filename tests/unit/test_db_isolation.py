"""The test suite never opens the real ``vajra_stream.db``.

``tests/conftest.py`` does two things at import time, before any test module
(and therefore any backend module) is imported:

1. points ``DATABASE_URL`` at a session temp file, so the env-driven
   ``config.backend_settings.backend_settings`` and ``core.schema.get_db_path()``
   resolve there; and
2. wraps ``sqlite3.connect`` / ``sqlite3.dbapi2.connect`` so that opening either
   live file (repo root or ``backend/app/``) raises instead.

These tests prove both are in force for the running session.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_DBS = [REPO_ROOT / "vajra_stream.db", REPO_ROOT / "backend" / "app" / "vajra_stream.db"]


def _norm(path: str | os.PathLike) -> str:
    return os.path.normcase(os.path.realpath(path))


def _live() -> set[str]:
    return {_norm(p) for p in LIVE_DBS}


def _url_path(url: str) -> str:
    assert url.startswith("sqlite:///"), url
    path = url[len("sqlite:///") :]
    assert os.path.isabs(path), "a relative DATABASE_URL resolves against the project root"
    return path


def test_database_url_points_away_from_the_live_db():
    # The value is conftest's session temp file, or a module's own temp DB
    # (tests/integration/test_extraction.py sets one at collection time).
    assert _norm(_url_path(os.environ["DATABASE_URL"])) not in _live()


def test_frozen_backend_settings_avoid_the_live_db():
    from config.backend_settings import backend_settings

    assert _norm(_url_path(backend_settings.DATABASE_URL)) not in _live()


def test_schema_db_path_is_not_the_live_db():
    from config.backend_settings import backend_settings
    from core.schema import get_db_path

    resolved = get_db_path()
    assert _norm(resolved) == _norm(_url_path(backend_settings.DATABASE_URL))
    assert _norm(resolved) not in _live()


@pytest.mark.parametrize("connect", ["sqlite3.connect", "sqlite3.dbapi2.connect"])
def test_sqlite_connect_is_guarded(connect):
    fn = sqlite3.connect if connect == "sqlite3.connect" else sqlite3.dbapi2.connect
    # Check the guard is installed BEFORE trying it, so a missing guard fails
    # here rather than opening (and creating) the live file.
    assert getattr(fn, "__vajra_live_db_guard__", False), f"{connect} is not the conftest live-DB guard"
    for live in LIVE_DBS:
        existed = live.exists()
        with pytest.raises(RuntimeError, match="live database"):
            fn(str(live))
        assert live.exists() == existed


def test_relative_and_uri_spellings_are_guarded(monkeypatch):
    assert getattr(sqlite3.connect, "__vajra_live_db_guard__", False)
    monkeypatch.chdir(REPO_ROOT)
    for spelling in ("vajra_stream.db", "./vajra_stream.db", "file:vajra_stream.db?mode=ro"):
        with pytest.raises(RuntimeError, match="live database"):
            sqlite3.connect(spelling, uri=spelling.startswith("file:"))


def test_other_databases_still_open(tmp_path):
    conn = sqlite3.connect(tmp_path / "scratch.db")
    try:
        assert conn.execute("select 1").fetchone() == (1,)
    finally:
        conn.close()
    sqlite3.connect(":memory:").close()
