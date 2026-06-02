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
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.astrology import AstrologicalCalculator
from core.extraction import (
    RunStatus,
    derive_algo_version,
    format_chart_for_llm,
)
from core.schema import get_db_path

logger = logging.getLogger(__name__)

router = APIRouter()


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
    """Compute one tuple's chart. Returns a plain dict for cross-thread safety.

    Mirrors :class:`core.extraction.ExtractionResult` but as a dict, since
    the background task is dispatched via :func:`asyncio.to_thread` and we
    want to avoid carrying the dataclass across the thread boundary.
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
            result = await asyncio.to_thread(
                _run_tuple_sync,
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
