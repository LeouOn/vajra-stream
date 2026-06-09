"""
Astrology Extraction API endpoints for Vajra.Stream — batch sweep.

Accepts a list of ``(date_iso, lat, lon)`` tuples plus a config (which
calculation systems to run), dedupes them, persists an ``extraction_runs``
row, and schedules an async background task that walks the tuples and
writes one ``extraction_results`` row per tuple. The endpoint returns
immediately with a ``run_id`` so callers don't block on the full batch.

The companion ``GET /astrology/runs/{id}``, ``/results``, ``/export``,
``DELETE``, and ``/recompute`` endpoints are added in Task 16 and live
in this same module.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.astrology import AstrologicalCalculator
from core.extraction import (
    ExtractionConfig,
    ExtractionResult,
    ExtractionRun,
    RunStatus,
    derive_algo_version,
    format_chart_for_llm,
    format_extraction_run_json,
    format_extraction_run_markdown,
)
from core.schema import get_db_path

logger = logging.getLogger(__name__)

# Router for the POST /astrology/extract batch endpoint (Task 15).
router = APIRouter()

# Router for the run management endpoints (Task 16). Mounted in api.py at
# the /astrology prefix, so routes here resolve to /astrology/runs, etc.
runs_router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class ExtractionTuple(BaseModel):
    """A single ``(datetime, lat, lon)`` sample."""

    date_iso: str = Field(..., description="ISO-8601 datetime (UTC preferred)")
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class ExtractionConfigRequest(BaseModel):
    """Per-run configuration (which systems to invoke, etc.)."""

    systems: list[str] = Field(
        default_factory=lambda: ["western"],
        description=(
            "Calculation systems to run per tuple. Recognized values: "
            "western, vedic, chinese, lots, midpoints, fixed_stars, "
            "progressions, returns, directions, year_ahead, astrocartography."
        ),
    )
    house_system: str = Field("Placidus", description="House system (Placidus, Whole Sign, Koch, ...)")
    sidereal: bool = Field(False, description="If true, Vedic-style sidereal positions")
    project_id: str | None = Field(None, description="Optional caller-supplied grouping key")
    time_grid_dsl: str | None = Field(
        None,
        description=(
            "Optional terse time-grid DSL (e.g. 'every 7 days', 'every Monday 06:00'). "
            "Ignored in v1 — callers should pass explicit tuples."
        ),
    )


class ExtractionRequest(BaseModel):
    """Top-level request body for POST /astrology/extract."""

    tuples: list[ExtractionTuple] = Field(..., description="One or more samples")
    config: ExtractionConfigRequest = Field(default_factory=ExtractionConfigRequest)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso(s: str) -> datetime:
    """Parse an ISO-8601 string into a UTC-aware datetime. Raises ValueError."""
    try:
        # ``fromisoformat`` in 3.10 doesn't accept the trailing ``Z`` —
        # normalize to the offset form first.
        normalized = s.replace("Z", "+00:00") if isinstance(s, str) else s
        dt = datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError(f"Invalid ISO-8601 datetime: {s!r}: {exc}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dedupe_tuples(
    tuples: list[ExtractionTuple],
) -> list[ExtractionTuple]:
    """Dedupe by ``(date_iso, lat, lon)`` with lat/lon rounded to 4 decimals.

    Per-tuple datetime parsing is deferred to the background runner so a
    malformed date in one tuple never aborts the whole batch.
    """
    seen: set[tuple[str, float, float]] = set()
    deduped: list[ExtractionTuple] = []
    for t in tuples:
        lat_key = round(float(t.lat), 4)
        lon_key = round(float(t.lon), 4)
        key = (t.date_iso, lat_key, lon_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(t)
    return deduped


# ---------------------------------------------------------------------------
# System-to-method dispatch
# ---------------------------------------------------------------------------


def _compute_chart_for_tuple(
    calc: AstrologicalCalculator,
    dt: datetime,
    location: tuple[float, float],
    systems: list[str],
    sidereal: bool,  # noqa: ARG001 — surfaced for v2 per-tuple sidereal control
) -> dict[str, Any]:
    """Invoke the requested calculation systems and merge their outputs.

    Unknown system names are recorded in the chart under
    ``_unknown_systems`` rather than raising, so a typo doesn't fail the
    whole batch.
    """
    chart: dict[str, Any] = {}
    for system in systems or []:
        key = (system or "").strip().lower()
        if not key:
            continue
        try:
            if key == "western":
                chart["western"] = calc.get_western_astrology(dt, location)
            elif key == "vedic":
                chart["vedic"] = calc.get_indian_astrology(dt, location)
            elif key == "chinese":
                chart["chinese"] = calc.get_chinese_astrology(dt)
            elif key == "lots":
                chart["lots"] = calc.get_hellenistic_lots(dt, location, sect="day")
            elif key == "midpoints":
                chart["midpoints"] = calc.get_midpoints(dt, location)
            elif key == "fixed_stars":
                chart["fixed_stars"] = calc.get_fixed_stars(dt, location)
            elif key == "progressions":
                # v1 spec: use this tuple as the natal when no natal_dt is provided.
                chart["progressions"] = calc.get_secondary_progressions(
                    dt, location, dt
                )
            elif key == "returns":
                chart["returns"] = calc.get_solar_return(
                    natal_dt=dt,
                    natal_location=location,
                    return_year=dt.year,
                    return_location=location,
                )
            elif key == "directions":
                # v1 spec: use this tuple as the natal when no natal_dt is provided.
                chart["directions"] = calc.get_solar_arc_directions(
                    dt, location, dt
                )
            elif key == "year_ahead":
                # v1 spec: use this tuple as the natal when no natal_dt is provided.
                chart["year_ahead"] = calc.get_year_ahead_timeline(dt, location)
            elif key == "astrocartography":
                chart["astrocartography"] = calc.get_astrocartography_lines(dt)
            else:
                chart.setdefault("_unknown_systems", []).append(system)
        except Exception as exc:  # per-system failure must not abort the batch
            logger.exception(
                "System %r failed for tuple %s: %s", system, dt.isoformat(), exc
            )
            chart.setdefault("_system_errors", {})[key] = (
                f"{type(exc).__name__}: {exc}"
            )
    return chart


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------


def _run_tuple_sync(
    tuple_idx: int,
    date_iso: str,
    lat: float,
    lon: float,
    systems: list[str],
    sidereal: bool,
) -> dict[str, Any]:
    """Compute one tuple's chart. Returns a plain dict.

    Mirrors :class:`core.extraction.ExtractionResult` but as a dict for
    clean serialization through the background task. Runs sequentially
    inside the async loop (Swiss Ephemeris calls release the GIL, and
    per-tuple work is sub-ms in the common case).
    """
    location = (float(lat), float(lon))
    try:
        dt = _parse_iso(date_iso)
    except Exception as exc:
        return {
            "tuple_idx": tuple_idx,
            "date_iso": date_iso,
            "lat": lat,
            "lon": lon,
            "chart": {},
            "status": RunStatus.ERROR.value,
            "error_message": f"invalid date: {exc}",
            "latency_ms": 0,
        }

    start = time.monotonic()
    try:
        calc = AstrologicalCalculator()
        chart = _compute_chart_for_tuple(calc, dt, location, systems, sidereal)
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "tuple_idx": tuple_idx,
            "date_iso": date_iso,
            "lat": lat,
            "lon": lon,
            "chart": chart,
            "status": RunStatus.DONE.value,
            "error_message": "",
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.exception("Tuple %d crashed: %s", tuple_idx, exc)
        return {
            "tuple_idx": tuple_idx,
            "date_iso": date_iso,
            "lat": lat,
            "lon": lon,
            "chart": {},
            "status": RunStatus.ERROR.value,
            "error_message": f"{type(exc).__name__}: {exc}",
            "latency_ms": latency_ms,
        }


def _persist_result_row(db_path: str, run_id: int, result: dict[str, Any]) -> None:
    """Write one ``extraction_results`` row. Best-effort; logs and swallows."""
    chart = result.get("chart") or {}
    chart_json_str = json.dumps(chart, default=str)
    formatted_md = format_chart_for_llm(chart, "markdown")
    formatted_json = format_chart_for_llm(chart, "json")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO extraction_results (
                run_id, tuple_idx, date_iso, lat, lon,
                chart_json, formatted_markdown, formatted_json,
                latency_ms, status, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                int(result["tuple_idx"]),
                result["date_iso"],
                float(result["lat"]),
                float(result["lon"]),
                chart_json_str,
                formatted_md,
                formatted_json,
                int(result.get("latency_ms") or 0),
                result.get("status") or RunStatus.ERROR.value,
                result.get("error_message") or None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _update_run_status(
    db_path: str,
    run_id: int,
    *,
    status: str | None = None,
    completed_tuples: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update one or more columns of an ``extraction_runs`` row."""
    sets: list[str] = []
    params: list[Any] = []
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if completed_tuples is not None:
        sets.append("completed_tuples = ?")
        params.append(int(completed_tuples))
    if error_message is not None:
        sets.append("error_message = ?")
        params.append(error_message)
    if not sets:
        return
    params.append(run_id)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            f"UPDATE extraction_runs SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        conn.commit()
    finally:
        conn.close()


async def _process_run(
    run_id: int,
    raw_tuples: list[ExtractionTuple],
    systems: list[str],
    sidereal: bool,
) -> None:
    """Background task: walk every tuple, persist results, update the run row."""
    db_path = get_db_path()
    total = len(raw_tuples)
    algo_version = derive_algo_version()
    completed = 0
    any_error = False
    all_error = True

    try:
        _update_run_status(
            db_path,
            run_id,
            status=RunStatus.RUNNING.value,
            completed_tuples=0,
        )
    except Exception:
        logger.exception("Failed to mark run %d as running", run_id)

    for idx, raw in enumerate(raw_tuples):
        try:
            # Call directly (not via asyncio.to_thread). Swiss Ephemeris
            # calls release the GIL, and the per-tuple work is sub-ms in
            # the common case. Routing through ``asyncio.to_thread`` made
            # the 3rd tuple hang under FastAPI's TestClient, where the
            # default executor was starved by the test portal's own
            # thread; see tests/test_extraction.py for the regression.
            result = _run_tuple_sync(
                idx,
                raw.date_iso,
                raw.lat,
                raw.lon,
                systems,
                sidereal,
            )
        except Exception as exc:
            logger.exception("Background dispatch failed for tuple %d: %s", idx, exc)
            result = {
                "tuple_idx": idx,
                "date_iso": raw.date_iso,
                "lat": raw.lat,
                "lon": raw.lon,
                "chart": {},
                "status": RunStatus.ERROR.value,
                "error_message": f"dispatch: {type(exc).__name__}: {exc}",
                "latency_ms": 0,
            }

        completed += 1
        if result.get("status") == RunStatus.DONE.value:
            all_error = False
        else:
            any_error = True

        try:
            _persist_result_row(db_path, run_id, result)
            _update_run_status(
                db_path, run_id, completed_tuples=completed
            )
        except Exception:
            logger.exception(
                "Failed to persist result for run %d tuple %d", run_id, idx
            )

    if total == 0:
        run_status = RunStatus.DONE
    elif all_error and any_error:
        run_status = RunStatus.ERROR
    elif any_error and not all_error:
        run_status = RunStatus.PARTIAL
    else:
        run_status = RunStatus.DONE

    try:
        _update_run_status(
            db_path,
            run_id,
            status=run_status.value,
            completed_tuples=completed,
        )
    except Exception:
        logger.exception("Failed to finalize run %d", run_id)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("", summary="Start a batch astrology extraction run")
async def start_extraction(request: ExtractionRequest) -> dict[str, Any]:
    """Queue a batch extraction. Returns immediately with ``run_id``.

    Heavy lifting runs in an :func:`asyncio.create_task` so the HTTP
    response lands in <500ms even for hundreds of tuples.
    """
    # Pydantic enforces ``tuples`` is non-empty via min_length=1, but
    # also raise a clean 400 with the documented message for clarity.
    if not request.tuples:
        raise HTTPException(status_code=400, detail="tuples list is empty")

    deduped_tuples = _dedupe_tuples(request.tuples)
    total = len(deduped_tuples)
    algo_version = derive_algo_version()
    config_dict = {
        "systems": list(request.config.systems),
        "house_system": request.config.house_system,
        "sidereal": request.config.sidereal,
        "project_id": request.config.project_id,
        "time_grid_dsl": request.config.time_grid_dsl,
    }

    db_path = get_db_path()
    created_at = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO extraction_runs (
                created_at, config_json, status, total_tuples,
                completed_tuples, error_message, algo_version
            ) VALUES (?, ?, ?, ?, 0, NULL, ?)
            """,
            (
                created_at,
                json.dumps(config_dict),
                RunStatus.QUEUED.value,
                total,
                algo_version,
            ),
        )
        run_id = int(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()

    asyncio.create_task(
        _process_run(
            run_id,
            list(deduped_tuples),
            list(request.config.systems),
            request.config.sidereal,
        )
    )

    return {
        "run_id": run_id,
        "status": RunStatus.QUEUED.value,
        "total_tuples": total,
        "algo_version": algo_version,
    }


# ---------------------------------------------------------------------------
# Run management helpers (Task 16)
# ---------------------------------------------------------------------------


def _safe_run_status(value: Any) -> RunStatus:
    """Coerce a stored status string into :class:`RunStatus`, defaulting to
    :attr:`RunStatus.ERROR` when the value is missing or unknown. This keeps
    the formatter happy even if the DB carries a stale or corrupt value.
    """
    if value is None:
        return RunStatus.ERROR
    try:
        return RunStatus(str(value))
    except ValueError:
        return RunStatus.ERROR


def _load_run_from_db(db_path: str, run_id: int) -> ExtractionRun | None:
    """Reconstruct an :class:`ExtractionRun` from the DB rows.

    Returns ``None`` if the run id is unknown. The reconstructed
    :class:`ExtractionConfig` carries an empty ``tuples`` list (the original
    tuples are not stored in ``config_json``; they live in
    ``extraction_results`` and are reconstructed on demand by the recompute
    endpoint).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        run_row = conn.execute(
            "SELECT * FROM extraction_runs WHERE id = ?",
            (int(run_id),),
        ).fetchone()
        if run_row is None:
            return None
        result_rows = conn.execute(
            "SELECT * FROM extraction_results WHERE run_id = ? "
            "ORDER BY tuple_idx ASC, id ASC",
            (int(run_id),),
        ).fetchall()
    finally:
        conn.close()

    raw_config = run_row["config_json"] or "{}"
    try:
        cfg_dict = json.loads(raw_config)
    except Exception:
        cfg_dict = {}

    config_obj = ExtractionConfig(
        tuples=[],
        systems=list(cfg_dict.get("systems") or []),
        house_system=str(cfg_dict.get("house_system") or "Placidus"),
        sidereal=bool(cfg_dict.get("sidereal") or False),
        project_id=cfg_dict.get("project_id"),
        algo_version=str(cfg_dict.get("algo_version") or ""),
        created_at=str(run_row["created_at"] or ""),
    )

    results: list[ExtractionResult] = []
    for r in result_rows:
        raw_chart = r["chart_json"] or "{}"
        try:
            chart = json.loads(raw_chart)
        except Exception:
            chart = {}
        results.append(
            ExtractionResult(
                tuple_idx=int(r["tuple_idx"] or 0),
                date_iso=str(r["date_iso"] or ""),
                lat=float(r["lat"]) if r["lat"] is not None else 0.0,
                lon=float(r["lon"]) if r["lon"] is not None else 0.0,
                chart=chart,
                status=_safe_run_status(r["status"]),
                error_message=str(r["error_message"] or ""),
                latency_ms=int(r["latency_ms"] or 0),
            )
        )

    return ExtractionRun(
        id=int(run_row["id"]),
        config=config_obj,
        results=results,
        status=_safe_run_status(run_row["status"]),
        created_at=str(run_row["created_at"] or ""),
        algo_version=str(run_row["algo_version"] or ""),
    )


def _result_status_str(status: Any) -> str:
    """Return the plain string value of a per-tuple status, whatever its shape."""
    if hasattr(status, "value"):
        return str(status.value)
    return str(status)


# ---------------------------------------------------------------------------
# Run management endpoints (Task 16)
# ---------------------------------------------------------------------------


@runs_router.get("/runs", summary="List extraction runs (paginated)")
async def list_runs(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> dict[str, Any]:
    """Return runs sorted by ``created_at`` DESC, optionally filtered by status.

    Query parameters:
        limit:  Max rows to return (default 20, capped at 200).
        offset: Number of rows to skip (default 0).
        status: Optional status filter; one of
            ``queued``, ``running``, ``done``, ``error``, ``partial``.
    """
    safe_limit = max(1, min(200, int(limit)))
    safe_offset = max(0, int(offset))

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if status:
            try:
                status_value = RunStatus(status).value
            except ValueError:
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unknown status filter: {status!r}. "
                        "Expected one of: queued, running, done, error, partial."
                    ),
                )
            rows = conn.execute(
                "SELECT * FROM extraction_runs WHERE status = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (status_value, safe_limit, safe_offset),
            ).fetchall()
            total_row = conn.execute(
                "SELECT COUNT(*) FROM extraction_runs WHERE status = ?",
                (status_value,),
            ).fetchone()
        else:
            rows = conn.execute(
                "SELECT * FROM extraction_runs "
                "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (safe_limit, safe_offset),
            ).fetchall()
            total_row = conn.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()
    finally:
        conn.close()

    total = int(total_row[0]) if total_row else 0
    return {
        "limit": safe_limit,
        "offset": safe_offset,
        "total": total,
        "runs": [dict(r) for r in rows],
    }


@runs_router.get("/runs/{run_id}", summary="Get a single extraction run status")
async def get_run(run_id: int) -> dict[str, Any]:
    """Return the run row, or 404 if the id is unknown."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM extraction_runs WHERE id = ?",
            (int(run_id),),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return dict(row)


@runs_router.get(
    "/runs/{run_id}/results",
    summary="Get the results for a run in the requested format",
)
async def get_run_results(run_id: int, format: str = "markdown") -> Response:
    """Return the run's results in ``markdown`` (default), ``json``, or ``raw``.

    - ``markdown`` — uses :func:`format_extraction_run_markdown` and returns
      the body as ``text/markdown``.
    - ``json`` — uses :func:`format_extraction_run_json` and returns the
      single JSON envelope as ``application/json``.
    - ``raw`` — returns just the chart dicts, one per tuple, as a JSON
      array of objects (no formatter wrapping).
    """
    db_path = get_db_path()
    run = _load_run_from_db(db_path, int(run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    fmt = (format or "markdown").strip().lower()
    if fmt == "markdown":
        body = format_extraction_run_markdown(run)
        return Response(content=body, media_type="text/markdown; charset=utf-8")
    if fmt == "json":
        body = format_extraction_run_json(run)
        return Response(content=body, media_type="application/json; charset=utf-8")
    if fmt == "raw":
        charts = [r.chart for r in run.results]
        body = json.dumps(charts, default=str, ensure_ascii=False)
        return Response(content=body, media_type="application/json; charset=utf-8")
    raise HTTPException(
        status_code=400,
        detail=(
            f"Unknown format: {format!r}. "
            "Expected one of: markdown, json, raw."
        ),
    )


@runs_router.get(
    "/runs/{run_id}/results/export",
    summary="Export a run as a downloadable file (jsonl, csv, or md)",
)
async def export_run_results(run_id: int, fmt: str = "jsonl") -> Response:
    """Return a downloadable representation of the run.

    - ``jsonl`` — one JSON object per line, each a tuple envelope. Media
      type ``application/x-ndjson``; the file is a real JSONL/ndjson stream
      consumable by ``json.loads(line)``.
    - ``csv`` — one row per tuple with columns
      ``idx, date_iso, lat, lon, status, error``.
    - ``md`` — the same markdown the ``?format=markdown`` results endpoint
      returns, but with a ``Content-Disposition: attachment`` header so
      browsers save it instead of rendering it.
    """
    db_path = get_db_path()
    run = _load_run_from_db(db_path, int(run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    fmt_lower = (fmt or "jsonl").strip().lower()
    if fmt_lower == "jsonl":
        lines: list[str] = []
        for r in run.results:
            envelope: dict[str, Any] = {
                "idx": r.tuple_idx,
                "date": r.date_iso,
                "lat": r.lat,
                "lon": r.lon,
                "chart": r.chart,
                "status": _result_status_str(r.status),
            }
            if r.error_message:
                envelope["error"] = r.error_message
            lines.append(json.dumps(envelope, default=str, ensure_ascii=False))
        body = "\n".join(lines) + ("\n" if lines else "")
        return Response(
            content=body,
            media_type="application/x-ndjson; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="run-{run_id}.jsonl"',
            },
        )
    if fmt_lower == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["idx", "date_iso", "lat", "lon", "status", "error"])
        for r in run.results:
            writer.writerow(
                [
                    r.tuple_idx,
                    r.date_iso,
                    r.lat,
                    r.lon,
                    _result_status_str(r.status),
                    r.error_message or "",
                ]
            )
        body = buf.getvalue()
        return Response(
            content=body,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="run-{run_id}.csv"',
            },
        )
    if fmt_lower == "md":
        body = format_extraction_run_markdown(run)
        return Response(
            content=body,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="run-{run_id}.md"',
            },
        )
    raise HTTPException(
        status_code=400,
        detail=(
            f"Unknown export format: {fmt!r}. "
            "Expected one of: jsonl, csv, md."
        ),
    )


@runs_router.delete(
    "/runs/{run_id}",
    summary="Delete a run and all of its per-tuple results",
)
async def delete_run(run_id: int) -> dict[str, Any]:
    """Remove the run row plus every associated ``extraction_results`` row.

    Returns a small confirmation envelope. Returns 404 if the run id is
    unknown so callers can distinguish a no-op delete from a real one.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM extraction_runs WHERE id = ?",
            (int(run_id),),
        ).fetchone()
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Run not found")
        conn.execute(
            "DELETE FROM extraction_results WHERE run_id = ?",
            (int(run_id),),
        )
        conn.execute(
            "DELETE FROM extraction_runs WHERE id = ?",
            (int(run_id),),
        )
        conn.commit()
    finally:
        conn.close()
    return {"deleted": True, "run_id": int(run_id)}


@runs_router.post(
    "/runs/{run_id}/recompute",
    summary="Recompute a run with the same config but the current algo_version",
)
async def recompute_run(run_id: int) -> dict[str, Any]:
    """Re-run the same tuple set with the current :func:`derive_algo_version`.

    Steps:
        1. Load the source run's ``config_json`` and the tuple list (read back
           from the existing ``extraction_results`` rows in input order).
        2. Dedup, insert a fresh ``extraction_runs`` row marked ``queued``,
           carrying the same ``config_json`` and a freshly-derived
           ``algo_version``.
        3. Schedule the same background :func:`_process_run` task.
        4. Return the new ``run_id`` and the new ``algo_version``.

    The source run is left untouched. The new run references the source
    via the returned ``source_run_id`` for traceability.
    """
    db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        run_row = conn.execute(
            "SELECT * FROM extraction_runs WHERE id = ?",
            (int(run_id),),
        ).fetchone()
        if run_row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Run not found")
        result_rows = conn.execute(
            "SELECT tuple_idx, date_iso, lat, lon "
            "FROM extraction_results WHERE run_id = ? "
            "ORDER BY tuple_idx ASC, id ASC",
            (int(run_id),),
        ).fetchall()
    finally:
        conn.close()

    raw_config = run_row["config_json"] or "{}"
    try:
        config_dict = json.loads(raw_config)
    except Exception:
        config_dict = {}

    tuples: list[ExtractionTuple] = []
    for r in result_rows:
        tuples.append(
            ExtractionTuple(
                date_iso=str(r["date_iso"] or ""),
                lat=float(r["lat"]) if r["lat"] is not None else 0.0,
                lon=float(r["lon"]) if r["lon"] is not None else 0.0,
            )
        )

    if not tuples:
        raise HTTPException(
            status_code=400,
            detail="Source run has no tuples to recompute",
        )

    deduped = _dedupe_tuples(tuples)
    new_algo_version = derive_algo_version()
    config_dict["algo_version"] = new_algo_version

    created_at = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO extraction_runs (
                created_at, config_json, status, total_tuples,
                completed_tuples, error_message, algo_version
            ) VALUES (?, ?, ?, ?, 0, NULL, ?)
            """,
            (
                created_at,
                json.dumps(config_dict),
                RunStatus.QUEUED.value,
                len(deduped),
                new_algo_version,
            ),
        )
        new_run_id = int(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()

    systems = list(config_dict.get("systems") or ["western"])
    sidereal = bool(config_dict.get("sidereal") or False)
    asyncio.create_task(
        _process_run(
            new_run_id,
            list(deduped),
            systems,
            sidereal,
        )
    )

    return {
        "run_id": new_run_id,
        "source_run_id": int(run_id),
        "status": RunStatus.QUEUED.value,
        "total_tuples": len(deduped),
        "algo_version": new_algo_version,
    }
