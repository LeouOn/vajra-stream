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
    generate_run_id, derive_algo_version,
    TimeGridConfig, generate_time_grid, generate_time_grid_from_string,
    format_chart_for_llm, format_extraction_run_markdown, format_extraction_run_json.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from core.astrology import AstrologicalCalculator


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


# =========================================================================
# TimeGrid — date-list generator (Task 3)
# =========================================================================

#: Threshold (in 0-1 illumination units) above which a daily moon reading
#: counts as a "full moon" event. ``AstrologicalCalculator.get_moon_phase``
#: returns illumination in 0-100, so we compare against 95.0 (= 0.95 * 100).
MOON_FULL_ILLUMINATION_THRESHOLD: float = 95.0

#: Threshold (in 0-1 illumination units) below which a daily moon reading
#: counts as a "new moon" event. We compare against 5.0 (= 0.05 * 100).
MOON_NEW_ILLUMINATION_THRESHOLD: float = 5.0

#: Minimum days between two emitted moon events of the same kind. The
#: synodic month is 29.53 days, so a 20-day floor safely suppresses
#: double-counting from daily sampling near the peak/trough.
MIN_DAYS_BETWEEN_SAME_MOON_EVENT: int = 20

#: Minimum days between two emitted solar events. Equinoxes are ~182.6
#: days apart; solstices likewise. A 80-day floor is safe.
MIN_DAYS_BETWEEN_SAME_SOLAR_EVENT: int = 80

#: Solar longitudes (tropical) that mark the cardinal ingresses.
SOLAR_INGRESS_LONGITUDES: dict[str, float] = {
    "vernal_equinox": 0.0,
    "summer_solstice": 90.0,
    "autumnal_equinox": 180.0,
    "winter_solstice": 270.0,
}

#: Map weekday names -> Python's ``datetime.weekday()`` index (0=Mon .. 6=Sun).
WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass
class TimeGridConfig:
    """Configuration for time-grid generation.

    Attributes:
        start: Inclusive start of the range.
        end: Inclusive end of the range.
        mode: One of ``"explicit"``, ``"every_n_days"``, ``"weekly"``,
            ``"astronomical"``.
        n_days: Step size for ``every_n_days`` mode (default 1).
        weekday: Target weekday for ``weekly`` mode, 0=Monday .. 6=Sunday
            (default 0 = Monday).
        hour: Target hour-of-day for ``weekly`` mode (default 6). Minute
            and second are zero.
        tz: Timezone name (currently informational — all output datetimes
            are returned as UTC-aware).
        astronomical_events: For ``astronomical`` mode, a list of event
            names drawn from ``{"full_moon", "new_moon", "equinox",
            "solstice"}``.
    """

    start: datetime
    end: datetime
    mode: str = "explicit"
    n_days: int = 1
    weekday: int = 0
    hour: int = 6
    tz: str = "UTC"
    astronomical_events: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_utc(dt: datetime) -> datetime:
    """Return a UTC-aware datetime. Naive datetimes are assumed UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_range(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Return ``(start, end)`` as UTC-aware datetimes with ``start <= end``."""
    s = _ensure_utc(start)
    e = _ensure_utc(end)
    if s > e:
        s, e = e, s
    return s, e


def _crosses_longitude_threshold(prev: float, curr: float, threshold: float) -> bool:
    """Return True iff solar longitude crossed ``threshold`` between samples.

    The samples are tropical longitudes in [0, 360). Handles the 360->0
    wraparound (vernal equinox) as well as forward crossings.

    Strategy: convert both samples to a coordinate relative to the
    threshold, then check whether that coordinate went from negative to
    non-negative (a forward crossing).
    """
    # Convert to "longitude since the last crossing of `threshold`".
    # The forward arc from `prev` to `curr` has length (curr - prev) mod 360.
    # The threshold is crossed iff (threshold - prev) mod 360 lies in (0, arc_len].
    arc_len = (curr - prev) % 360.0
    if arc_len == 0.0:
        return False
    gap = (threshold - prev) % 360.0
    # ``gap == 0`` means we are exactly at the threshold on the prior day.
    # ``gap <= arc_len`` means the threshold lies in the forward arc.
    # Exclude the trivial case ``gap == 0`` so we don't double-fire when
    # both samples are exactly on the threshold.
    return 0.0 < gap <= arc_len


# ---------------------------------------------------------------------------
# generate_time_grid
# ---------------------------------------------------------------------------


def generate_time_grid(cfg: TimeGridConfig) -> list[datetime]:
    """Generate a list of datetimes per the configuration.

    See :class:`TimeGridConfig` for mode semantics. Returns a sorted list
    of UTC-aware datetimes. For ``mode="explicit"`` the result is
    ``[start, end]`` (2 elements, even when they coincide).
    """
    start, end = _normalize_range(cfg.start, cfg.end)

    if cfg.mode == "explicit":
        return [start, end]

    if cfg.mode == "every_n_days":
        step = max(1, int(cfg.n_days))
        out: list[datetime] = []
        cur = start
        while cur <= end:
            out.append(cur)
            cur += timedelta(days=step)
        return out

    if cfg.mode == "weekly":
        weekday = cfg.weekday % 7
        hour = max(0, min(23, int(cfg.hour)))
        delta_days = (weekday - start.weekday()) % 7
        first = (start + timedelta(days=delta_days)).replace(hour=hour, minute=0, second=0, microsecond=0)
        if first < start:
            first += timedelta(days=7)
        out = []
        cur = first
        while cur <= end:
            out.append(cur)
            cur += timedelta(days=7)
        return out

    if cfg.mode == "astronomical":
        events = [e for e in (cfg.astronomical_events or []) if e]
        if not events:
            return []
        return _scan_astronomical_events(start, end, events)

    raise ValueError(
        f"Unknown TimeGridConfig.mode: {cfg.mode!r}. "
        f"Expected one of: 'explicit', 'every_n_days', 'weekly', 'astronomical'."
    )


# ---------------------------------------------------------------------------
# Astronomical event scanning
# ---------------------------------------------------------------------------


def _scan_astronomical_events(start: datetime, end: datetime, events: list[str]) -> list[datetime]:
    """Scan daily from ``start`` to ``end`` for the requested events.

    For moon events we look for days where the daily illumination reading
    crosses the full/new threshold, and dedupe with a 20-day floor.

    For solar events we look for days where the solar-longitude difference
    from the prior day crosses 0°/90°/180°/270° (the four cardinal
    ingresses). The "equinox" event subsumes the vernal (0°) and
    autumnal (180°) crossings; "solstice" subsumes the summer (90°)
    and winter (270°) crossings.
    """
    calc = AstrologicalCalculator()

    want_full_moon = "full_moon" in events
    want_new_moon = "new_moon" in events
    want_equinox = "equinox" in events
    want_solstice = "solstice" in events
    want_solar = want_equinox or want_solstice
    want_moon = want_full_moon or want_new_moon

    if not want_moon and not want_solar:
        return []

    out: list[datetime] = []
    last_full_moon: datetime | None = None
    last_new_moon: datetime | None = None
    last_solar: datetime | None = None

    # Sample the day BEFORE start so we can detect a threshold crossing
    # that occurs on start itself.
    prev_dt = start - timedelta(days=1)

    prev_solar: float | None = None
    if want_solar:
        prev_solar = calc.get_planetary_positions(prev_dt)["sun"]["longitude"]

    cur = start
    max_iter = (end - start).days + 2
    for _ in range(max_iter):
        if cur > end:
            break

        if want_moon:
            phase = calc.get_moon_phase(cur)
            # ``illumination`` is in 0-100 (see AstrologicalCalculator.get_moon_phase).
            illum = float(phase["illumination"])
            if want_full_moon and illum > MOON_FULL_ILLUMINATION_THRESHOLD:
                if last_full_moon is None or (cur - last_full_moon).days >= MIN_DAYS_BETWEEN_SAME_MOON_EVENT:
                    out.append(cur)
                    last_full_moon = cur
            elif want_new_moon and illum < MOON_NEW_ILLUMINATION_THRESHOLD:
                if last_new_moon is None or (cur - last_new_moon).days >= MIN_DAYS_BETWEEN_SAME_MOON_EVENT:
                    out.append(cur)
                    last_new_moon = cur

        if want_solar:
            assert prev_solar is not None
            curr_solar = calc.get_planetary_positions(cur)["sun"]["longitude"]
            targets: list[float] = []
            if want_equinox:
                targets.append(SOLAR_INGRESS_LONGITUDES["vernal_equinox"])
                targets.append(SOLAR_INGRESS_LONGITUDES["autumnal_equinox"])
            if want_solstice:
                targets.append(SOLAR_INGRESS_LONGITUDES["summer_solstice"])
                targets.append(SOLAR_INGRESS_LONGITUDES["winter_solstice"])
            for tgt in targets:
                if _crosses_longitude_threshold(prev_solar, curr_solar, tgt):
                    if last_solar is None or (cur - last_solar).days >= MIN_DAYS_BETWEEN_SAME_SOLAR_EVENT:
                        out.append(cur)
                        last_solar = cur
                        break
            prev_solar = curr_solar

        cur += timedelta(days=1)

    out.sort()
    seen_dates: set = set()
    deduped: list[datetime] = []
    for d in out:
        key = d.date()
        if key in seen_dates:
            continue
        seen_dates.add(key)
        deduped.append(d)
    return deduped


# ---------------------------------------------------------------------------
# DSL parser
# ---------------------------------------------------------------------------


#: Regex for a comma-separated list of ISO dates (YYYY-MM-DD).
_ISO_DATE_LIST_RE = re.compile(r"^\s*\d{4}-\d{2}-\d{2}(\s*,\s*\d{4}-\d{2}-\d{2})*\s*$")

#: Regex for "every N days" (N >= 1).
_EVERY_N_DAYS_RE = re.compile(r"^\s*every\s+(\d+)\s+days?\s*$", re.IGNORECASE)

#: Regex for "every <weekday> HH:MM" (weekday may be a name or number 0-6).
_EVERY_WEEKDAY_RE = re.compile(r"^\s*every\s+([A-Za-z]+|\d)\s+(\d{1,2}):(\d{2})\s*$", re.IGNORECASE)

#: Regex for an optional 4-digit year (1900-2099).
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def generate_time_grid_from_string(s: str, start: datetime, end: datetime) -> list[datetime]:
    """Parse a terse DSL string and return a generated time grid.

    Supported patterns (case-insensitive, whitespace-flexible):

    - ``"every N days"`` (e.g. ``"every 7 days"``) → ``every_n_days`` mode
    - ``"every <weekday> HH:MM"`` (e.g. ``"every Monday 06:00"``) →
      ``weekly`` mode
    - ``"full moon [year]"`` / ``"new moon [year]"`` → ``astronomical``
      with the matching lunar event(s)
    - ``"equinox [year]"`` / ``"solstice [year]"`` /
      ``"equinox solstice [year]"`` → ``astronomical`` with the matching
      solar event(s)
    - ``"YYYY-MM-DD,YYYY-MM-DD,..."`` (comma-separated ISO dates) →
      ``explicit`` mode

    For astronomical patterns that include a year (e.g. ``"full moon 2026"``),
    the year overrides the ``start``/``end`` range to
    ``YYYY-01-01 .. YYYY-12-31 23:59:59``.

    Args:
        s: The DSL string to parse.
        start: Default range start (used when the DSL doesn't constrain it).
        end: Default range end (used when the DSL doesn't constrain it).

    Returns:
        A list of UTC-aware datetimes.

    Raises:
        ValueError: If the string does not match any supported pattern.
    """
    if s is None:
        raise ValueError("DSL string is None")
    s = s.strip()
    if not s:
        raise ValueError("DSL string is empty")

    if _ISO_DATE_LIST_RE.match(s):
        parsed: list[datetime] = []
        for part in s.split(","):
            piece = part.strip()
            try:
                d = datetime.fromisoformat(piece)
            except ValueError as exc:
                raise ValueError(f"Invalid ISO date in list: {piece!r}") from exc
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            parsed.append(d)
        parsed.sort()
        return parsed

    m = _EVERY_N_DAYS_RE.match(s)
    if m:
        n = max(1, int(m.group(1)))
        cfg = TimeGridConfig(start=start, end=end, mode="every_n_days", n_days=n)
        return generate_time_grid(cfg)

    m = _EVERY_WEEKDAY_RE.match(s)
    if m:
        wd_token = m.group(1).strip().lower()
        if wd_token.isdigit():
            weekday = int(wd_token) % 7
        else:
            if wd_token not in WEEKDAY_NAMES:
                raise ValueError(
                    f"Unknown weekday {wd_token!r} in DSL: {s!r}. Expected one of: {sorted(WEEKDAY_NAMES)}."
                )
            weekday = WEEKDAY_NAMES[wd_token]
        hour = int(m.group(2))
        minute = int(m.group(3))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Invalid time {hour:02d}:{minute:02d} in DSL: {s!r}")
        cfg = TimeGridConfig(
            start=start,
            end=end,
            mode="weekly",
            weekday=weekday,
            hour=hour,
        )
        return generate_time_grid(cfg)

    s_lower = s.lower()
    astro_events: list[str] = []
    if "full moon" in s_lower or "fullmoon" in s_lower:
        astro_events.append("full_moon")
    if "new moon" in s_lower or "newmoon" in s_lower:
        astro_events.append("new_moon")
    if "equinox" in s_lower:
        astro_events.append("equinox")
    if "solstice" in s_lower:
        astro_events.append("solstice")

    if astro_events:
        ymatch = _YEAR_RE.search(s)
        if ymatch:
            year = int(ymatch.group(0))
            range_start = datetime(year, 1, 1, tzinfo=timezone.utc)
            range_end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        else:
            range_start, range_end = _normalize_range(start, end)
        cfg = TimeGridConfig(
            start=range_start,
            end=range_end,
            mode="astronomical",
            astronomical_events=astro_events,
        )
        return generate_time_grid(cfg)

    raise ValueError(f"Could not parse time grid DSL: {s!r}")


_SECTION_ORDER: list[tuple[str, tuple[str, ...]]] = [
    ("Positions", ("positions", "western", "vedic", "chinese")),
    ("Hellenistic Lots", ("lots", "hellenistic_lots")),
    ("Midpoints", ("midpoints",)),
    ("Fixed Stars", ("fixed_stars", "fixedStars")),
    ("Progressions", ("progressions", "secondary_progressions")),
    ("Returns", ("returns", "solar_return", "profection")),
    ("Directions", ("directions", "solar_arc")),
    ("Year-Ahead", ("year_ahead", "timeline")),
    ("Astrocartography", ("astrocartography", "acg")),
]


def _has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_has_content(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_content(v) for v in value)
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _find_positions_payload(chart: dict) -> tuple[str, dict] | None:
    generic = chart.get("positions")
    if isinstance(generic, dict) and any(
        isinstance(v, dict) and ("sign" in v or "longitude" in v) for v in generic.values()
    ):
        return ("", generic)

    for system_key, label in (
        ("western", " (Western)"),
        ("vedic", " (Vedic)"),
        ("chinese", " (Chinese)"),
    ):
        sys_data = chart.get(system_key)
        if not isinstance(sys_data, dict):
            continue
        nested = sys_data.get("positions")
        if isinstance(nested, dict) and any(
            isinstance(v, dict) and ("sign" in v or "longitude" in v) for v in nested.values()
        ):
            return (label, nested)
        if any(isinstance(v, dict) and ("sign" in v or "longitude" in v) for v in sys_data.values()):
            return (label, sys_data)
    return None


def _find_section_payload(chart: dict, aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        value = chart.get(key)
        if _has_content(value):
            return value
    return None


def _format_scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return f"{int(v)}.00"
        return f"{v:.4f}".rstrip("0").rstrip(".")
    if isinstance(v, (int, str)):
        return str(v)
    if isinstance(v, dict):
        inner = ", ".join(f"{k}={_format_scalar(val)}" for k, val in v.items())
        return "{" + inner + "}"
    if isinstance(v, (list, tuple)):
        inner = ", ".join(_format_scalar(x) for x in v)
        return "[" + inner + "]"
    return str(v)


def _section_bullets(data: Any, indent: str = "  ") -> list[str]:
    lines: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict) and value:
                lines.append(f"{indent}- **{key}**:")
                for k2, v2 in value.items():
                    lines.append(f"{indent}  - {k2}: {_format_scalar(v2)}")
            elif isinstance(value, list) and value:
                lines.append(f"{indent}- **{key}**:")
                for item in value:
                    if isinstance(item, dict):
                        rendered = "; ".join(f"{k}={_format_scalar(v)}" for k, v in item.items())
                        lines.append(f"{indent}  - {rendered}")
                    else:
                        lines.append(f"{indent}  - {_format_scalar(item)}")
            else:
                lines.append(f"{indent}- **{key}**: {_format_scalar(value)}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                rendered = "; ".join(f"{k}={_format_scalar(v)}" for k, v in item.items())
                lines.append(f"{indent}- {rendered}")
            else:
                lines.append(f"{indent}- {_format_scalar(item)}")
    else:
        lines.append(f"{indent}- {_format_scalar(data)}")
    return lines


def _format_positions_block(chart: dict) -> list[str]:
    found = _find_positions_payload(chart)
    if not found:
        return []
    label, payload = found
    return [f"### Positions{label}", *_section_bullets(payload, indent="  ")]


def _format_generic_section(header: str, chart: dict, aliases: tuple[str, ...]) -> list[str]:
    payload = _find_section_payload(chart, aliases)
    if payload is None:
        return []
    return [f"### {header}", *_section_bullets(payload, indent="  ")]


def format_chart_for_llm(
    chart: dict,
    fmt: str = "markdown",
    schema_version: str = "1",
) -> str:
    """Format a chart dict as LLM-friendly text (markdown or JSON)."""
    if fmt == "json":
        return json.dumps(
            {"schema_version": schema_version, "chart": chart},
            indent=2,
            sort_keys=True,
            default=str,
        )
    if fmt == "markdown":
        return _format_chart_markdown(chart)
    raise ValueError(f"Unsupported fmt={fmt!r}; expected 'markdown' or 'json'")


def _format_chart_markdown(chart: dict) -> str:
    blocks: list[list[str]] = [_format_positions_block(chart)]
    for header, aliases in _SECTION_ORDER[1:]:
        blocks.append(_format_generic_section(header, chart, aliases))
    return "\n".join(line for block in blocks if block for line in block)


def format_extraction_run_markdown(run: ExtractionRun) -> str:
    """Render an :class:`ExtractionRun` as a single markdown document.

    One ``## Tuple N`` section per :class:`ExtractionResult`. Errors get
    a ``Status: error`` line and a skipped body. Section order follows
    :data:`_SECTION_ORDER`.
    """
    lines: list[str] = []
    run_id = getattr(run, "id", 0) or 0
    algo_version = run.algo_version or ""
    created_at = run.created_at or ""
    lines.append(f"# Astrology Extraction — Run {run_id}")
    meta_bits = []
    if algo_version:
        meta_bits.append(f"Algo: {algo_version}")
    if created_at:
        meta_bits.append(f"Created: {created_at}")
    if meta_bits:
        lines.append("  ".join(meta_bits))

    for result in run.results:
        lines.append("")
        lines.append(f"## Tuple {result.tuple_idx} — {result.date_iso} @ {result.lat}, {result.lon}")
        status_value = result.status.value if hasattr(result.status, "value") else str(result.status)
        if status_value == "error" or result.error_message:
            err = result.error_message or "unknown error"
            lines.append(f"**Status**: error: {err}")
            lines.append("")
            continue
        lines.append("**Status**: ok")
        lines.append("")
        chart_md = _format_chart_markdown(result.chart or {})
        if chart_md:
            lines.append(chart_md)
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    if lines:
        lines.append("")
    return "\n".join(lines)


def format_extraction_run_json(run: ExtractionRun) -> str:
    """Render an :class:`ExtractionRun` as a single JSON envelope.

    Top-level keys: ``schema_version``, ``run_id``, ``algo_version``,
    ``created_at``, ``tuples``. Each tuple carries ``idx``, ``date``,
    ``lat``, ``lon``, ``chart``, ``status``, and (on error) ``error``.
    """
    run_id = getattr(run, "id", 0) or 0
    payload = {
        "schema_version": "1",
        "run_id": str(run_id),
        "algo_version": run.algo_version or "",
        "created_at": run.created_at or "",
        "tuples": [],
    }
    for result in run.results:
        status_value = result.status.value if hasattr(result.status, "value") else str(result.status)
        entry: dict[str, Any] = {
            "idx": result.tuple_idx,
            "date": result.date_iso,
            "lat": result.lat,
            "lon": result.lon,
            "chart": result.chart or {},
            "status": status_value,
        }
        if status_value == "error" or result.error_message:
            entry["error"] = result.error_message or "unknown error"
        payload["tuples"].append(entry)
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


__all__ = [
    "RunStatus",
    "ExtractionConfig",
    "ExtractionResult",
    "ExtractionRun",
    "generate_run_id",
    "derive_algo_version",
    "TimeGridConfig",
    "generate_time_grid",
    "generate_time_grid_from_string",
    "MOON_FULL_ILLUMINATION_THRESHOLD",
    "MOON_NEW_ILLUMINATION_THRESHOLD",
    "SOLAR_INGRESS_LONGITUDES",
    "WEEKDAY_NAMES",
    "format_chart_for_llm",
    "format_extraction_run_markdown",
    "format_extraction_run_json",
]
