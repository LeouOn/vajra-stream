"""
Extraction — batch astrology extraction data structures.

Pure data containers + small helpers for the batch extraction subsystem that
sweeps hundreds of ``(date, lat, lon)`` tuples through the astrology engine
and persists structured results for replay/diff.

This module is intentionally **side-effect free**:
    * No database I/O (persistence lives in ``core.extraction_store``).
    * No LLM calls.
    * No global/singleton state.
    * No stdout output.

Exports:
    RunStatus, ExtractionConfig, ExtractionResult, ExtractionRun,
    generate_run_id, derive_algo_version.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    """Lifecycle status of an :class:`ExtractionRun` or :class:`ExtractionResult`.

    Inherits from ``str`` so values serialize cleanly to JSON and persist as
    plain text in SQLite.
    """

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    PARTIAL = "partial"


@dataclass
class ExtractionConfig:
    """Configuration for a batch astrology extraction run.

    Attributes:
        tuples: Sequence of ``(datetime, latitude, longitude)`` tuples to
            sweep. Latitudes are in [-90, 90]; longitudes in [-180, 180].
            Datetimes should be timezone-aware (UTC recommended).
        systems: Names of calculation systems to run per tuple. Recognized
            values include ``"western"``, ``"vedic"``, ``"chinese"``,
            ``"lots"``, ``"midpoints"``, ``"fixed_stars"``,
            ``"progressions"``, ``"returns"``, ``"directions"``,
            ``"year_ahead"``, ``"astrocartography"``.
        house_system: House system identifier (e.g. ``"Placidus"``,
            ``"Whole Sign"``, ``"Koch"``). Default ``"Placidus"``.
        sidereal: If ``True``, compute Vedic-style sidereal positions
            (Lahiri ayanamsa) rather than tropical.
        project_id: Optional caller-supplied grouping key (e.g. an
            experiment slug or user label). ``None`` means ungrouped.
        algo_version: Pre-derived algo version string. Callers may leave
            this empty and rely on :func:`derive_algo_version` at
            persistence time.
        created_at: ISO-8601 timestamp the config was constructed. Empty
            string means "fill at persistence time".
    """

    tuples: list[tuple[datetime, float, float]]
    systems: list[str]
    house_system: str = "Placidus"
    sidereal: bool = False
    project_id: str | None = None
    algo_version: str = ""
    created_at: str = ""


@dataclass
class ExtractionResult:
    """Outcome of a single tuple within an :class:`ExtractionRun`.

    Attributes:
        tuple_idx: Zero-based position in the source ``ExtractionConfig.tuples``.
        date_iso: ISO-8601 timestamp of the tuple's datetime (preserved as
            provided, with timezone info).
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        chart: Structured chart payload (system-specific shape). Empty dict
            if computation failed.
        status: Per-tuple status. Mirrors :class:`RunStatus` but a tuple
            may be ``DONE`` while its parent run is ``PARTIAL``.
        error_message: Human-readable error if ``status`` is ``ERROR``,
            else empty.
        latency_ms: Wall-clock duration of the tuple's computation in
            milliseconds. Zero if not yet measured.
    """

    tuple_idx: int
    date_iso: str
    lat: float
    lon: float
    chart: dict
    status: RunStatus
    error_message: str = ""
    latency_ms: int = 0


@dataclass
class ExtractionRun:
    """A full batch extraction sweep: config + per-tuple results + bookkeeping.

    Attributes:
        id: Numeric primary key. ``0`` means "not yet persisted".
        config: The :class:`ExtractionConfig` this run was launched with.
        results: One :class:`ExtractionResult` per tuple, in input order.
        status: Aggregate run status (``DONE`` if all tuples succeeded,
            ``PARTIAL`` if at least one succeeded and at least one erred,
            ``ERROR`` if the runner itself crashed).
        created_at: ISO-8601 timestamp the run was created.
        completed_at: ISO-8601 timestamp the run finished. Empty string
            means "still running or not started".
        algo_version: Algorithm version snapshot at run time, used to
            detect calculation drift on replay.
    """

    id: int
    config: ExtractionConfig
    results: list[ExtractionResult] = field(default_factory=list)
    status: RunStatus = RunStatus.QUEUED
    created_at: str = ""
    completed_at: str = ""
    algo_version: str = ""


def generate_run_id() -> str:
    """Return a fresh UUID4 hex string (32 lowercase hex chars, no dashes).

    Used to tag a run before it gets a numeric database ID.
    """
    return uuid.uuid4().hex


def derive_algo_version() -> str:
    """Return a stable algorithm-version string for run tagging.

    Combines :data:`core.astrology.__version__` with the underlying Swiss
    Ephemeris version when the latter is exposed. Falls back to just the
    ``astrology`` version string if Swiss Ephemeris does not advertise one.

    Examples:
        ``"1.0.0-swe-20230604"``  (swisseph version exposed)
        ``"1.0.0"``              (swisseph version not exposed)
    """
    astro_version = "1.0.0"
    try:
        import swisseph as swe  # local import to avoid hard dep at module top
    except Exception:
        swe = None  # type: ignore[assignment]

    swe_version = getattr(swe, "__version__", None) if swe is not None else None
    if swe_version:
        return f"{astro_version}-swe-{swe_version}"
    return astro_version


__all__ = [
    "RunStatus",
    "ExtractionConfig",
    "ExtractionResult",
    "ExtractionRun",
    "generate_run_id",
    "derive_algo_version",
]
