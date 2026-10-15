"""Operations ledger — the record of real, timed operations.

An *operation* is something the instrument actually does and that takes real
time: a local render, a broadcast, a working. Each one moves through

    queued -> running -> success | error | cancelled
                       \\-> interrupted   (process died while it was in flight)

and keeps its real ``started_at`` / ``finished_at`` / ``elapsed_seconds``.
This replaces MOPS-style throughput counters: the honest unit is a completed
operation with a measured duration, not "operations per second".

``provenance`` records where an operation's values came from, using the
roadmap's vocabulary (docs/DEVELOPMENT_ROADMAP.md, "the honest instrument"):
``record`` / ``computed`` / ``draw`` / ``decorative``. A render seed chosen at
random is a ``draw``; it is recorded so the result is reproducible.

Persistence is the ``operations`` table (core/schema.py, schema v7). Every
state change is pushed to registered listeners; ``backend/app/main.py``
registers one that broadcasts ``{"type": "operation_update", "data": op}``
over the WebSocket. This module never imports from ``backend`` (keeps the
core -> backend import cycle from growing).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from core.schema import apply_schema, get_db_path

logger = logging.getLogger(__name__)

KINDS = frozenset({"render", "broadcast", "working", "audio", "tts", "video", "other"})
TERMINAL_STATUSES = frozenset({"success", "error", "cancelled", "interrupted"})
ACTIVE_STATUSES = frozenset({"queued", "running"})
STATUSES = TERMINAL_STATUSES | ACTIVE_STATUSES
PROVENANCE_KINDS = frozenset({"record", "computed", "draw", "decorative"})

_JSON_FIELDS = ("params", "provenance", "result")

Listener = Callable[[dict[str, Any]], None]
_listeners: list[Listener] = []
_listeners_lock = threading.Lock()
_write_lock = threading.Lock()
_schema_ready: set[str] = set()


class OperationError(ValueError):
    """Raised for an unknown operation or an invalid state transition."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        if db_path not in _schema_ready:
            apply_schema(conn)
            _schema_ready.add(db_path)
        yield conn
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    op = dict(row)
    for field in _JSON_FIELDS:
        raw = op.get(field)
        op[field] = json.loads(raw) if raw else None
    return op


def _validate_provenance(provenance: dict[str, Any] | None) -> None:
    if not provenance:
        return
    for key, value in provenance.items():
        if value not in PROVENANCE_KINDS:
            raise OperationError(f"provenance[{key!r}] must be one of {sorted(PROVENANCE_KINDS)}, got {value!r}")


def add_listener(listener: Listener) -> None:
    """Register a callback invoked with the full operation dict on every change."""
    with _listeners_lock:
        if listener not in _listeners:
            _listeners.append(listener)


def remove_listener(listener: Listener) -> None:
    with _listeners_lock:
        if listener in _listeners:
            _listeners.remove(listener)


def _notify(op: dict[str, Any]) -> None:
    with _listeners_lock:
        listeners = list(_listeners)
    for listener in listeners:
        try:
            listener(op)
        except Exception:  # a broken listener must never break the operation
            logger.exception("operation listener failed")


def get_operation(op_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM operations WHERE id = ?", (op_id,)).fetchone()
    return _row_to_dict(row) if row else None


def create_operation(
    kind: str,
    title: str,
    *,
    params: dict[str, Any] | None = None,
    provenance: dict[str, str] | None = None,
    working_id: str | None = None,
) -> dict[str, Any]:
    """Record a new ``queued`` operation and return it."""
    if kind not in KINDS:
        raise OperationError(f"kind must be one of {sorted(KINDS)}, got {kind!r}")
    if not title.strip():
        raise OperationError("title must not be empty")
    _validate_provenance(provenance)
    op_id = uuid.uuid4().hex
    with _write_lock, _connect() as conn:
        conn.execute(
            "INSERT INTO operations (id, kind, status, title, working_id, params, provenance, created_at)"
            " VALUES (?, ?, 'queued', ?, ?, ?, ?, ?)",
            (
                op_id,
                kind,
                title.strip(),
                working_id,
                json.dumps(params) if params is not None else None,
                json.dumps(provenance) if provenance else None,
                _now(),
            ),
        )
        conn.commit()
    op = get_operation(op_id)
    assert op is not None
    _notify(op)
    return op


def _transition(op_id: str, allowed_from: frozenset[str], updates: dict[str, Any]) -> dict[str, Any]:
    with _write_lock, _connect() as conn:
        row = conn.execute("SELECT * FROM operations WHERE id = ?", (op_id,)).fetchone()
        if row is None:
            raise OperationError(f"unknown operation {op_id!r}")
        if row["status"] not in allowed_from:
            raise OperationError(f"operation {op_id} is {row['status']}; cannot move to {updates['status']}")
        if updates["status"] in TERMINAL_STATUSES:
            finished = datetime.now(timezone.utc)
            updates["finished_at"] = finished.isoformat()
            if row["started_at"]:
                started = datetime.fromisoformat(row["started_at"])
                updates["elapsed_seconds"] = round((finished - started).total_seconds(), 3)
        for field in _JSON_FIELDS:
            if field in updates and updates[field] is not None:
                updates[field] = json.dumps(updates[field])
        assignments = ", ".join(f"{column} = ?" for column in updates)
        conn.execute(f"UPDATE operations SET {assignments} WHERE id = ?", (*updates.values(), op_id))
        conn.commit()
    op = get_operation(op_id)
    assert op is not None
    _notify(op)
    return op


def start_operation(op_id: str) -> dict[str, Any]:
    """``queued`` -> ``running``; stamps ``started_at`` (the clock for elapsed time)."""
    return _transition(op_id, frozenset({"queued"}), {"status": "running", "started_at": _now()})


def complete_operation(op_id: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
    """``running`` -> ``success``."""
    return _transition(op_id, frozenset({"running"}), {"status": "success", "result": result})


def fail_operation(op_id: str, error: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
    """``queued``/``running`` -> ``error``. ``result`` may keep partial data (e.g. a backend job id)."""
    return _transition(op_id, ACTIVE_STATUSES, {"status": "error", "error": error[:2000], "result": result})


def cancel_operation(op_id: str) -> dict[str, Any]:
    """``queued``/``running`` -> ``cancelled``."""
    return _transition(op_id, ACTIVE_STATUSES, {"status": "cancelled"})


def update_operation_result(op_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Replace ``result`` on an active operation without changing status (e.g. progress, backend ids)."""
    with _write_lock, _connect() as conn:
        row = conn.execute("SELECT status FROM operations WHERE id = ?", (op_id,)).fetchone()
        if row is None:
            raise OperationError(f"unknown operation {op_id!r}")
        if row["status"] not in ACTIVE_STATUSES:
            raise OperationError(f"operation {op_id} is {row['status']}; result is final")
        conn.execute("UPDATE operations SET result = ? WHERE id = ?", (json.dumps(result), op_id))
        conn.commit()
    op = get_operation(op_id)
    assert op is not None
    _notify(op)
    return op


def list_operations(
    *,
    kind: str | None = None,
    status: str | None = None,
    working_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Newest first."""
    clauses, values = [], []
    for column, value in (("kind", kind), ("status", status), ("working_id", working_id)):
        if value is not None:
            clauses.append(f"{column} = ?")
            values.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit = max(1, min(int(limit), 500))
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM operations {where} ORDER BY created_at DESC LIMIT ?", (*values, limit)
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def summarize_operations(*, since: str | None = None) -> dict[str, Any]:
    """Counts by status and kind, plus total time actually held by completed operations.

    ``since`` is an ISO-8601 timestamp; only operations created at or after it count.
    """
    where, values = ("WHERE created_at >= ?", (since,)) if since else ("", ())
    with _connect() as conn:
        by_status = {
            row["status"]: row["n"]
            for row in conn.execute(f"SELECT status, COUNT(*) AS n FROM operations {where} GROUP BY status", values)
        }
        by_kind = {
            row["kind"]: row["n"]
            for row in conn.execute(f"SELECT kind, COUNT(*) AS n FROM operations {where} GROUP BY kind", values)
        }
        held = conn.execute(
            f"SELECT COALESCE(SUM(elapsed_seconds), 0) AS s FROM operations "
            f"{where + ' AND' if where else 'WHERE'} status = 'success'",
            values,
        ).fetchone()["s"]
    return {
        "since": since,
        "by_status": by_status,
        "by_kind": by_kind,
        "active": by_status.get("queued", 0) + by_status.get("running", 0),
        "completed": by_status.get("success", 0),
        "seconds_held": round(float(held), 3),
    }


def reconcile_interrupted(*, exclude_kinds: frozenset[str] = frozenset()) -> int:
    """Mark operations left ``queued``/``running`` by a dead process as ``interrupted``.

    Call once at startup, before new work is accepted. Kinds that can re-attach
    to an external job that survived the restart (e.g. a ComfyUI render that is
    still executing) should be excluded and reconciled by their owner.
    """
    ops = [
        op
        for status in ACTIVE_STATUSES
        for op in list_operations(status=status, limit=500)
        if op["kind"] not in exclude_kinds
    ]
    for op in ops:
        _transition(
            op["id"],
            ACTIVE_STATUSES,
            {"status": "interrupted", "error": "server restarted while this operation was in flight"},
        )
    return len(ops)
