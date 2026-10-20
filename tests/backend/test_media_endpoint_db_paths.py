"""Pin how the media endpoints choose their SQLite file.

``image_generation._db_path`` and ``video_generation._db_path`` must delegate
to the canonical resolver :func:`core.schema.get_db_path`, which honours
``settings.DATABASE_URL``. If either endpoint ever reverts to its own guess —
the old ``VAJRA_DB_PATH`` environment variable, or a project-root /
``backend/app`` mirror search — saved image/video configuration would silently
start landing in a different file from the rest of the app. These tests fail
loudly the moment that regresses.

Safety of this file
-------------------
Several tests here deliberately write, because "the endpoint opened *that*
file" can only be proven by writing through its own connection and reading the
row back from that path. Three layers keep that write contained:

1. ``_assert_scratch_path`` screens the path the endpoint *would* open, before
   any connection exists.
2. The ``connect_guard`` fixture intercepts ``sqlite3.connect`` — the module
   attribute — for the whole test, so a regression that connects by a literal
   filename is refused at the moment the connect is attempted. URI forms
   (``file:``, ``uri=True``) and non-file targets are rejected outright rather
   than forwarded. The fixture also patches any ``sqlite3.connect`` /
   ``sqlite3.Connection`` ALIAS captured in the two endpoint modules; at the
   time of writing there are none, so the scan is defensive.
3. ``_roundtrip`` re-checks the open connection's real file via
   ``PRAGMA database_list`` before running any DDL.

What is actually guaranteed
---------------------------
"THIS TEST NEVER WRITES TO A NON-SCRATCH FILE, AND FAILS LOUDLY IF IT TRIES."

It is NOT guaranteed that no connection is ever opened. Layer 2 covers connects
made through ``sqlite3.connect`` (as a module attribute) and through the
endpoint-module aliases found at fixture time. A regression that reaches a real
database by some other route — an alias captured elsewhere at import time, or
direct ``sqlite3.Connection(...)`` construction — could still cause that file to
be OPENED; layer 3 then stops it before any DDL or write. So the failure mode
for such a regression is a loud test failure with a scratch-screen message, not
a guaranteed absence of a file handle.

Import safety: importing either endpoint module transitively loads the whole
``backend.app.api.v1.endpoints`` package (that package's ``__init__`` is what
pulls in the sibling routers). Neither module builds a paid client at import
time — the generation service is lazy inside ``get_service()`` — and after item
5 the package no longer performs import-time database initialisation. What
actually keeps those imports off the repository database is the
``DATABASE_URL`` redirect that ``tests/conftest.py`` installs at conftest import
time, not the lazy services. No API key is read or required here.
"""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

import core.schema
from backend.app.api.v1.endpoints import image_generation, video_generation

ENDPOINTS = [
    ("image", image_generation),
    ("video", video_generation),
]

REPO_ROOT = Path(core.schema.get_project_root()).resolve()
_NON_FILE_TARGETS = frozenset({":memory:", ""})


def _scratch_db(tmp_path: Path, name: str) -> str:
    """An absolute path to a throwaway SQLite file inside tmp_path."""
    return str(tmp_path / name)


def _assert_not_repository_db(label: str, path: Path) -> None:
    """Refuse any path that is, or sits inside, the repository's database tree.

    This is the guard that makes the rest of this file safe. If an endpoint
    helper regresses to the old logic it resolves to the project-root database
    (or the ``backend/app`` mirror, or any ``*.db`` sitting directly under the
    repo root). Connecting there would CREATE TABLE and INSERT into the owner's
    live data, so we raise *before* any connection is opened.
    """
    resolved = path.resolve()
    forbidden = {
        (REPO_ROOT / "vajra_stream.db").resolve(),
        (REPO_ROOT / "backend" / "app" / "vajra_stream.db").resolve(),
    }
    if resolved in forbidden:
        raise AssertionError(f"{label}: refusing to open repository database {resolved}")
    if resolved.parent == REPO_ROOT:
        raise AssertionError(f"{label}: refusing to open {resolved.name} directly under the repo root")
    if REPO_ROOT in resolved.parents:
        raise AssertionError(f"{label}: refusing to open a database inside the repository: {resolved}")


def _assert_scratch_path(label: str, resolved: str, scratch_root: Path) -> Path:
    """Guard to run BEFORE calling ``endpoint._connect_db()``.

    Resolves the path the endpoint *would* open and proves it is inside the
    scratch directory and nowhere near the repository, so a regression fails the
    test without ever opening a connection.
    """
    path = Path(resolved)
    if not path.is_absolute():
        raise AssertionError(f"{label}: resolved path is not absolute: {resolved!r}")
    _assert_not_repository_db(label, path)
    scratch = scratch_root.resolve()
    resolved_path = path.resolve()
    if resolved_path.parent != scratch and scratch not in resolved_path.parents:
        raise AssertionError(f"{label}: resolved outside the scratch dir {scratch}: {resolved_path}")
    return resolved_path


def _connect_interceptor(real_connect, scratch_root: Path):
    """Wrap ``sqlite3.connect`` so every attempt is screened before it happens.

    Only an absolute path inside the scratch directory is allowed through.
    URI forms are REJECTED rather than forwarded: a ``file:`` URI can name any
    file on disk (``file:/…/vajra_stream.db?mode=rw``), and this layer exists
    precisely to stop that. ``uri=True``, ``:memory:`` and ``""`` are rejected
    too — the endpoints under test never need them, and a total rule is easier
    to reason about than a carve-out.
    """

    def guarded(database, *args, **kwargs):
        if kwargs.get("uri"):
            raise AssertionError(
                f"sqlite3.connect: refusing uri=True target {database!r}; "
                f"these tests only connect to scratch files by plain path"
            )
        if not isinstance(database, str | bytes | os.PathLike):
            raise AssertionError(f"sqlite3.connect: refusing non-path target of type {type(database).__name__}")
        raw = os.fsdecode(database)
        if raw.startswith("file:"):
            raise AssertionError(f"sqlite3.connect: refusing file: URI {raw!r}; " f"a URI can name any file on disk")
        if raw in _NON_FILE_TARGETS:
            raise AssertionError(f"sqlite3.connect: refusing non-file target {raw!r}")
        _assert_scratch_path("sqlite3.connect", raw, scratch_root)
        return real_connect(database, *args, **kwargs)

    return guarded


@pytest.fixture
def connect_guard(monkeypatch, tmp_path):
    """Install the connect interceptor for the duration of a connection test.

    Patches the ``sqlite3.connect`` module attribute (both endpoint modules call
    ``sqlite3.connect(...)`` through the module, at call time) and then scans
    the two endpoint modules for any ALIAS of ``sqlite3.connect`` /
    ``sqlite3.Connection`` captured at their import time, patching those too.
    As of this writing the scan finds none — both modules hold only the
    ``sqlite3`` module — so it is a guard against a future refactor.

    Restored by monkeypatch at teardown.
    """
    real_connect = sqlite3.connect
    real_connection = sqlite3.Connection
    monkeypatch.setattr(sqlite3, "connect", _connect_interceptor(real_connect, tmp_path))
    aliases: list[str] = []
    for endpoint in (image_generation, video_generation):
        for name, value in list(vars(endpoint).items()):
            if value is real_connect:
                monkeypatch.setattr(endpoint, name, _connect_interceptor(real_connect, tmp_path))
                aliases.append(f"{endpoint.__name__}.{name}")
            elif value is real_connection:
                monkeypatch.setattr(endpoint, name, _connection_interceptor(real_connection, tmp_path))
                aliases.append(f"{endpoint.__name__}.{name}")
    return aliases


def _connection_interceptor(real_connection, scratch_root: Path):
    """Screen direct ``sqlite3.Connection(path)`` construction too."""

    def guarded(database, *args, **kwargs):
        if not isinstance(database, str | bytes | os.PathLike):
            raise AssertionError(f"sqlite3.Connection: refusing non-path target of type {type(database).__name__}")
        raw = os.fsdecode(database)
        if raw.startswith("file:"):
            raise AssertionError(f"sqlite3.Connection: refusing file: URI {raw!r}")
        if raw in _NON_FILE_TARGETS:
            raise AssertionError(f"sqlite3.Connection: refusing non-file target {raw!r}")
        _assert_scratch_path("sqlite3.Connection", raw, scratch_root)
        return real_connection(database, *args, **kwargs)

    return guarded


def _assert_connection_is_scratch(connection: sqlite3.Connection, label: str, scratch_root: Path) -> None:
    """Third layer: verify the OPEN connection's real file, via PRAGMA."""
    rows = connection.execute("PRAGMA database_list").fetchall()
    if not rows or not rows[0][2]:
        raise AssertionError(f"{label}: PRAGMA database_list reported no file (in-memory?)")
    actual = Path(rows[0][2]).resolve()
    _assert_not_repository_db(label, actual)
    scratch = scratch_root.resolve()
    if actual.parent != scratch and scratch not in actual.parents:
        raise AssertionError(f"{label}: connection opened {actual}, outside scratch dir {scratch}")


def _roundtrip(connection: sqlite3.Connection, table: str, scratch_root: Path) -> None:
    """Write and commit through the endpoint's own connection object.

    The connection's real file is verified first, so a helper that regressed to
    a real database fails here without executing any DDL.
    """
    _assert_connection_is_scratch(connection, f"_roundtrip[{table}]", scratch_root)
    connection.execute(f"CREATE TABLE {table} (value TEXT)")
    connection.execute(f"INSERT INTO {table} VALUES ('written-here')")
    connection.commit()
    connection.close()


def _read_back(path: str, table: str, scratch_root: Path) -> str:
    """Read the row back with an independent connection to the same file."""
    _assert_not_repository_db(f"_read_back[{table}]", Path(path))
    with sqlite3.connect(path) as check:
        row = check.execute(f"SELECT value FROM {table}").fetchone()
    assert row is not None, f"no {table} row in {path}"
    return row[0]


# ---------------------------------------------------------------------------
# The connect guard itself
# ---------------------------------------------------------------------------
def test_connect_guard_rejects_uri_forms(tmp_path, monkeypatch):
    """URI and non-file connect targets are refused before any connect happens.

    A recorder stands in for the real connector, so "was the connector
    reached?" is directly observable — it must not be. This is the layer that
    previously forwarded every ``file:`` string, which a regressed
    ``_connect_db`` could have used to name any file on disk.
    """
    reached = []

    def recorder(database, *args, **kwargs):
        reached.append(database)
        raise AssertionError("recorder reached: a real connect would have happened")

    monkeypatch.setattr(sqlite3, "connect", _connect_interceptor(recorder, tmp_path))

    with pytest.raises(AssertionError, match="refusing uri=True"):
        sqlite3.connect(f"file:{tmp_path / 'uri.db'}?mode=rw", uri=True)
    with pytest.raises(AssertionError, match="refusing file: URI"):
        sqlite3.connect(f"file:{tmp_path / 'uri2.db'}")
    with pytest.raises(AssertionError, match="refusing non-file target"):
        sqlite3.connect(":memory:")
    with pytest.raises(AssertionError, match="refusing non-file target"):
        sqlite3.connect("")

    assert not reached, f"recorder was reached: {reached}"


def test_connect_guard_rejects_repository_paths(tmp_path, monkeypatch):
    """The guard refuses the repository database and anything outside scratch."""
    reached = []

    def recorder(database, *args, **kwargs):
        reached.append(database)
        raise AssertionError("recorder reached")

    monkeypatch.setattr(sqlite3, "connect", _connect_interceptor(recorder, tmp_path))

    live = REPO_ROOT / "vajra_stream.db"
    with pytest.raises(AssertionError, match="refusing to open repository database"):
        sqlite3.connect(str(live))
    with pytest.raises(AssertionError, match="refusing to open .* directly under the repo root"):
        sqlite3.connect(str(REPO_ROOT / "probe.db"))
    with pytest.raises(AssertionError, match="resolved outside the scratch dir"):
        sqlite3.connect(str(Path(tempfile.gettempdir()) / "elsewhere.db"))

    assert not reached, f"recorder was reached: {reached}"


def test_connect_guard_allows_a_scratch_path(tmp_path, monkeypatch):
    """The guard is not vacuous: a scratch file still connects."""
    reached = []

    def recorder(database, *args, **kwargs):
        reached.append(database)
        return sqlite3.Connection(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", _connect_interceptor(recorder, tmp_path))
    conn = sqlite3.connect(str(tmp_path / "allowed.db"))
    conn.close()

    assert reached == [str(tmp_path / "allowed.db")], reached
    assert Path(tmp_path / "allowed.db").exists()


def test_no_connection_aliases_are_captured_in_the_endpoint_modules():
    """Documents why the alias scan in connect_guard currently finds nothing.

    If a future refactor adds ``from sqlite3 import connect`` to either endpoint
    module, this fails and the scan in connect_guard starts doing real work.
    """
    real_connect = sqlite3.connect
    real_connection = sqlite3.Connection
    for endpoint in (image_generation, video_generation):
        for name, value in vars(endpoint).items():
            assert value is not real_connect, f"{endpoint.__name__}.{name} aliases sqlite3.connect"
            assert value is not real_connection, f"{endpoint.__name__}.{name} aliases sqlite3.Connection"


# ---------------------------------------------------------------------------
# The helpers must delegate to the canonical resolver
# ---------------------------------------------------------------------------
def test_db_path_delegates_to_canonical_resolver(tmp_path, monkeypatch):
    """Both ``_db_path`` helpers return whatever ``core.schema.get_db_path``
    returns — they must not compute a path of their own."""
    for label, endpoint in ENDPOINTS:
        target = _scratch_db(tmp_path, f"{label}_delegated.db")
        monkeypatch.setattr(core.schema, "get_db_path", lambda *a, **k: target)
        assert endpoint._db_path() == target, f"{label}._db_path() ignored the canonical resolver"


def test_connect_db_opens_the_canonical_path(tmp_path, monkeypatch, connect_guard):
    """``_connect_db`` must open the resolver's file.

    Screened three ways before any DDL runs: the resolved path, the intercepted
    ``sqlite3.connect`` call, and the open connection's ``PRAGMA
    database_list``. The row is then written through the endpoint's own
    connection and read back from that path independently, so this also fails
    if the helper opens some other scratch file.
    """
    for label, endpoint in ENDPOINTS:
        target = _scratch_db(tmp_path, f"{label}_connect.db")
        monkeypatch.setattr(core.schema, "get_db_path", lambda *a, **k: target)
        assert not Path(target).exists()

        _assert_scratch_path(f"{label}._connect_db", endpoint._db_path(), tmp_path)
        _roundtrip(endpoint._connect_db(), f"probe_{label}", tmp_path)

        assert Path(target).exists(), f"{label}._connect_db() did not create {target}"
        assert (
            _read_back(target, f"probe_{label}", tmp_path) == "written-here"
        ), f"{label}._connect_db() opened a different file"


def test_legacy_vajra_db_path_env_does_not_win(tmp_path, monkeypatch):
    """``VAJRA_DB_PATH`` must not override the canonical setting.

    This was the old escape hatch: it pointed the media endpoints at a
    different file than the rest of the app. Setting it to a perfectly valid
    alternate path must change nothing.
    """
    canonical = _scratch_db(tmp_path, "canonical.db")
    decoy = _scratch_db(tmp_path, "decoy.db")
    monkeypatch.setenv("VAJRA_DB_PATH", decoy)
    monkeypatch.setattr(core.schema, "get_db_path", lambda *a, **k: canonical)

    for label, endpoint in ENDPOINTS:
        resolved = endpoint._db_path()
        assert resolved == canonical, f"{label}._db_path() let VAJRA_DB_PATH win ({resolved})"
        assert resolved != decoy, f"{label}._db_path() returned the legacy VAJRA_DB_PATH value"


def test_legacy_env_does_not_redirect_the_connection(tmp_path, monkeypatch, connect_guard):
    """Same guard for the connection helper: the decoy file stays untouched."""
    canonical = _scratch_db(tmp_path, "canonical_conn.db")
    decoy = _scratch_db(tmp_path, "decoy_conn.db")
    monkeypatch.setenv("VAJRA_DB_PATH", decoy)
    monkeypatch.setattr(core.schema, "get_db_path", lambda *a, **k: canonical)

    for label, endpoint in ENDPOINTS:
        _assert_scratch_path(f"{label}._connect_db", endpoint._db_path(), tmp_path)
        _roundtrip(endpoint._connect_db(), f"legacy_{label}", tmp_path)
        assert Path(canonical).exists(), f"{label} wrote nowhere expected"
        assert not Path(decoy).exists(), f"{label} wrote to the legacy VAJRA_DB_PATH file"


# ---------------------------------------------------------------------------
# The real resolver: relative and absolute DATABASE_URL forms
# ---------------------------------------------------------------------------
def test_real_resolver_keeps_an_absolute_url_verbatim(tmp_path):
    """An absolute SQLite URL resolves to exactly that absolute path."""
    target = _scratch_db(tmp_path, "absolute.db")
    assert core.schema.get_db_path(f"sqlite:///{target}") == target


def test_real_resolver_anchors_a_relative_url_at_the_project_root(tmp_path, monkeypatch):
    """A relative URL is anchored at the project root, not the working directory.

    ``monkeypatch.chdir`` moves the process into ``tmp_path`` first, so a
    resolver that wrongly used ``os.path.abspath(relative_name)`` would resolve
    under tmp_path and fail here. Only the returned string is inspected; nothing
    is opened.
    """
    monkeypatch.chdir(tmp_path)
    resolved = core.schema.get_db_path("sqlite:///./relative_probe.db")
    assert Path(resolved).is_absolute()
    assert Path(resolved).name == "relative_probe.db"
    assert Path(resolved).parent == Path(core.schema.get_project_root()).resolve()


def test_real_resolver_handles_a_bare_relative_name(tmp_path, monkeypatch):
    """A URL with no leading ./ is still anchored at the project root."""
    monkeypatch.chdir(tmp_path)
    resolved = core.schema.get_db_path("sqlite:///bare_relative_probe.db")
    assert Path(resolved) == Path(core.schema.get_project_root()) / "bare_relative_probe.db"


def test_real_resolver_handles_a_raw_filename(tmp_path, monkeypatch):
    """A bare filename with no ``sqlite:///`` prefix is anchored too.

    ``get_db_path`` only strips that literal prefix, so a raw name passes
    through the same absolute-path branch.
    """
    monkeypatch.chdir(tmp_path)
    resolved = core.schema.get_db_path("raw_relative_probe.db")
    assert Path(resolved) == Path(core.schema.get_project_root()) / "raw_relative_probe.db"


# ---------------------------------------------------------------------------
# In-suite wiring: conftest redirects DATABASE_URL to a temp DB
# ---------------------------------------------------------------------------
def test_endpoints_agree_with_the_canonical_resolver():
    """Both helpers agree with ``core.schema.get_db_path()`` right now."""
    expected = core.schema.get_db_path()
    for label, endpoint in ENDPOINTS:
        assert endpoint._db_path() == expected, f"{label}._db_path() diverged from the resolver"


def test_endpoints_do_not_point_at_the_live_database():
    """The resolved file must be the temp DB conftest set up, not the repo one."""
    live = Path(core.schema.get_project_root()) / "vajra_stream.db"
    temp_root = Path(tempfile.gettempdir()).resolve()
    for label, endpoint in ENDPOINTS:
        resolved = Path(endpoint._db_path()).resolve()
        assert resolved != live.resolve(), f"{label}._db_path() points at the live repo database"
        assert resolved.is_absolute()
        assert temp_root in resolved.parents, f"{label}._db_path() resolved outside the temp dir: {resolved}"


def test_settings_url_and_resolver_agree():
    """The endpoint path is the pydantic setting, resolved — not a second guess."""
    from config.backend_settings import backend_settings as settings

    url = settings.DATABASE_URL
    assert url.startswith("sqlite:///")
    expected = core.schema.get_db_path(url)
    for label, endpoint in ENDPOINTS:
        assert endpoint._db_path() == expected, f"{label} did not use settings.DATABASE_URL"
