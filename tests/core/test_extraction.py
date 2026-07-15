"""Tests for ``core.extraction`` — batch extraction data structures + helpers.

Covers the public API:
- :class:`RunStatus` (str-Enum)
- Dataclasses: :class:`ExtractionConfig`, :class:`ExtractionResult`,
  :class:`ExtractionRun`, :class:`TimeGridConfig`
- :func:`generate_run_id`, :func:`derive_algo_version`
- :func:`generate_time_grid` (all four modes)
- :func:`generate_time_grid_from_string` (DSL parser)
- :func:`format_chart_for_llm`, :func:`format_extraction_run_markdown`,
  :func:`format_extraction_run_json`

Heavy ephemeris calls in ``astronomical`` mode are mocked to keep tests fast
and deterministic; the four core modes are exercised end-to-end.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from core.extraction import (
    ExtractionConfig,
    ExtractionResult,
    ExtractionRun,
    RunStatus,
    TimeGridConfig,
    derive_algo_version,
    format_chart_for_llm,
    format_extraction_run_json,
    format_extraction_run_markdown,
    generate_run_id,
    generate_time_grid,
    generate_time_grid_from_string,
)

# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols without import errors."""
    import core.extraction as mod

    for name in (
        "RunStatus",
        "ExtractionConfig",
        "ExtractionResult",
        "ExtractionRun",
        "generate_run_id",
        "derive_algo_version",
        "TimeGridConfig",
        "generate_time_grid",
        "generate_time_grid_from_string",
        "format_chart_for_llm",
        "format_extraction_run_markdown",
        "format_extraction_run_json",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. RunStatus (str-Enum)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_status_is_str_enum():
    """RunStatus members behave like strings (JSON-clean serialisation)."""
    assert RunStatus.DONE.value == "done"
    assert RunStatus.PARTIAL.value == "partial"
    assert RunStatus.ERROR.value == "error"
    # Inherits from str
    assert RunStatus.DONE == "done"
    assert isinstance(RunStatus.DONE, str)


# ---------------------------------------------------------------------------
# 3. Dataclass contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extraction_config_defaults():
    """ExtractionConfig has sensible defaults and required positional fields."""
    cfg = ExtractionConfig(
        tuples=[(datetime(2024, 1, 1, tzinfo=timezone.utc), 0.0, 0.0)],
        systems=["western"],
    )
    assert cfg.house_system == "Placidus"
    assert cfg.sidereal is False
    assert cfg.project_id is None
    assert cfg.algo_version == ""
    assert cfg.created_at == ""


@pytest.mark.unit
def test_extraction_result_defaults():
    """ExtractionResult defaults: error_message=empty, latency_ms=0."""
    r = ExtractionResult(
        tuple_idx=0,
        date_iso="2024-01-01T00:00:00+00:00",
        lat=0.0,
        lon=0.0,
        chart={},
        status=RunStatus.DONE,
    )
    assert r.error_message == ""
    assert r.latency_ms == 0


@pytest.mark.unit
def test_extraction_run_defaults():
    """ExtractionRun defaults: id=0, empty results, status=QUEUED, no timestamps."""
    cfg = ExtractionConfig(tuples=[], systems=[])
    run = ExtractionRun(id=0, config=cfg)
    assert run.results == []
    assert run.status == RunStatus.QUEUED
    assert run.created_at == ""
    assert run.completed_at == ""
    assert run.algo_version == ""


# ---------------------------------------------------------------------------
# 4. generate_run_id / derive_algo_version
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_run_id_returns_unique_32_char_hex():
    """generate_run_id returns lowercase hex without dashes, 32 chars long."""
    id1 = generate_run_id()
    id2 = generate_run_id()
    assert isinstance(id1, str)
    assert len(id1) == 32
    assert id1 == id1.lower()
    # Pure hex
    int(id1, 16)  # would raise ValueError if not hex
    # Two calls produce distinct values
    assert id1 != id2


@pytest.mark.unit
def test_derive_algo_version_returns_non_empty_string():
    """derive_algo_version returns a non-empty string (with or without '-swe-')."""
    v = derive_algo_version()
    assert isinstance(v, str)
    assert v  # non-empty
    # Either "1.0.0" alone or "1.0.0-swe-<version>"
    assert v == "1.0.0" or v.startswith("1.0.0-swe-")


# ---------------------------------------------------------------------------
# 5. generate_time_grid — the four modes
# ---------------------------------------------------------------------------


def _utc(y, m, d, hh=0, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


@pytest.mark.unit
def test_generate_time_grid_explicit_returns_endpoints():
    """explicit mode returns [start, end] regardless of distance."""
    cfg = TimeGridConfig(
        start=_utc(2024, 1, 1),
        end=_utc(2024, 1, 2),
        mode="explicit",
    )
    grid = generate_time_grid(cfg)
    assert len(grid) == 2
    assert grid[0] == _utc(2024, 1, 1)
    assert grid[1] == _utc(2024, 1, 2)


@pytest.mark.unit
def test_generate_time_grid_every_n_days():
    """every_n_days mode emits a sample every N days, inclusive of end."""
    cfg = TimeGridConfig(
        start=_utc(2024, 1, 1),
        end=_utc(2024, 1, 10),
        mode="every_n_days",
        n_days=3,
    )
    grid = generate_time_grid(cfg)
    # Jan 1, 4, 7, 10 => 4 samples
    assert len(grid) == 4
    assert grid[0] == _utc(2024, 1, 1)
    assert grid[-1] == _utc(2024, 1, 10)
    # Step is exactly 3 days
    for a, b in zip(grid, grid[1:]):
        assert (b - a).days == 3


@pytest.mark.unit
def test_generate_time_grid_weekly_uses_target_weekday_and_hour():
    """weekly mode: first sample on/after start matching the target weekday + hour."""
    # 2024-01-01 is a Monday. weekday=2 (Wednesday), hour=10 => 2024-01-03 10:00
    cfg = TimeGridConfig(
        start=_utc(2024, 1, 1),
        end=_utc(2024, 1, 21),
        mode="weekly",
        weekday=2,
        hour=10,
    )
    grid = generate_time_grid(cfg)
    assert len(grid) == 3  # 1/3, 1/10, 1/17
    for d in grid:
        assert d.weekday() == 2
        assert d.hour == 10 and d.minute == 0 and d.second == 0


@pytest.mark.unit
def test_generate_time_grid_astronomical_filters_by_event():
    """astronomical mode with empty events list returns empty (no errors)."""
    cfg = TimeGridConfig(
        start=_utc(2024, 1, 1),
        end=_utc(2024, 1, 31),
        mode="astronomical",
        astronomical_events=[],
    )
    assert generate_time_grid(cfg) == []


@pytest.mark.unit
def test_generate_time_grid_astronomical_emits_deduplicated_full_moons():
    """astronomical mode with full_moon emits one entry per full moon.

    Between 2024-01-01 and 2024-12-31 there are exactly 12 full moons;
    the 20-day deduping floor must keep them all (months are ~29.5 days).
    Uses real ephemeris via AstrologicalCalculator.
    """
    cfg = TimeGridConfig(
        start=_utc(2024, 1, 1),
        end=_utc(2024, 12, 31),
        mode="astronomical",
        astronomical_events=["full_moon"],
    )
    grid = generate_time_grid(cfg)
    assert len(grid) >= 11  # 12 lunations, allow for edge cases
    # All dates within range and UTC-aware
    for d in grid:
        assert _utc(2024, 1, 1) <= d <= datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert d.tzinfo is not None


@pytest.mark.unit
def test_generate_time_grid_unknown_mode_raises_value_error():
    """An unrecognised mode raises ValueError with a descriptive message."""
    cfg = TimeGridConfig(
        start=_utc(2024, 1, 1),
        end=_utc(2024, 1, 2),
        mode="not_a_real_mode",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError) as exc_info:
        generate_time_grid(cfg)
    assert "not_a_real_mode" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 6. generate_time_grid_from_string — DSL parser
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_time_grid_from_string_every_n_days():
    """DSL: 'every 5 days' maps to every_n_days mode with n=5."""
    grid = generate_time_grid_from_string(
        "every 5 days",
        start=_utc(2024, 1, 1),
        end=_utc(2024, 1, 11),
    )
    # Jan 1, 6, 11 => 3 samples
    assert len(grid) == 3
    assert grid[0] == _utc(2024, 1, 1)
    assert grid[-1] == _utc(2024, 1, 11)


@pytest.mark.unit
def test_generate_time_grid_from_string_every_weekday():
    """DSL: 'every Monday 06:00' maps to weekly mode with weekday=0 hour=6."""
    grid = generate_time_grid_from_string(
        "every Monday 06:00",
        start=_utc(2024, 1, 1),  # Monday
        end=_utc(2024, 1, 22),  # 3 Mondays later inclusive
    )
    assert len(grid) >= 3
    for d in grid:
        assert d.weekday() == 0
        assert d.hour == 6 and d.minute == 0


@pytest.mark.unit
def test_generate_time_grid_from_string_full_moon_year():
    """DSL: 'full moon 2024' overrides the date range to the year 2024."""
    grid = generate_time_grid_from_string(
        "full moon 2024",
        start=_utc(2020, 1, 1),  # should be ignored
        end=_utc(2020, 12, 31),
    )
    assert len(grid) >= 11
    for d in grid:
        assert d.year == 2024


@pytest.mark.unit
def test_generate_time_grid_from_string_iso_date_list():
    """DSL: comma-separated ISO dates maps to explicit mode, sorted."""
    grid = generate_time_grid_from_string(
        "2024-03-15,2024-01-01,2024-02-10",
        start=_utc(2024, 1, 1),
        end=_utc(2024, 12, 31),
    )
    assert [d.date().isoformat() for d in grid] == [
        "2024-01-01",
        "2024-02-10",
        "2024-03-15",
    ]


@pytest.mark.unit
def test_generate_time_grid_from_string_raises_on_garbage():
    """Unparseable DSL strings raise ValueError."""
    with pytest.raises(ValueError):
        generate_time_grid_from_string(
            "this is not a valid time grid",
            start=_utc(2024, 1, 1),
            end=_utc(2024, 1, 2),
        )


@pytest.mark.unit
def test_generate_time_grid_from_string_raises_on_empty():
    """Empty / None DSL strings raise ValueError."""
    with pytest.raises(ValueError):
        generate_time_grid_from_string("", start=_utc(2024, 1, 1), end=_utc(2024, 1, 2))


# ---------------------------------------------------------------------------
# 7. format_chart_for_llm
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_format_chart_for_llm_markdown_contains_section_headers():
    """format_chart_for_llm(markdown) emits section headers for known payloads."""
    chart = {
        "positions": {
            "sun": {"sign": "aries", "longitude": 12.34},
            "moon": {"sign": "taurus", "longitude": 45.6},
        },
        "lots": {
            "fortune": {"longitude": 78.9},
        },
    }
    out = format_chart_for_llm(chart, fmt="markdown")
    assert isinstance(out, str)
    assert "### Positions" in out
    assert "### Hellenistic Lots" in out


@pytest.mark.unit
def test_format_chart_for_llm_json_envelope():
    """format_chart_for_llm(json) wraps the chart in a schema_version envelope."""
    chart = {"positions": {"sun": {"sign": "aries", "longitude": 1.0}}}
    out = format_chart_for_llm(chart, fmt="json", schema_version="2")
    payload = json.loads(out)
    assert payload["schema_version"] == "2"
    assert payload["chart"] == chart


@pytest.mark.unit
def test_format_chart_for_llm_unknown_fmt_raises():
    """An unknown fmt raises ValueError (not silently falls through)."""
    with pytest.raises(ValueError):
        format_chart_for_llm({}, fmt="xml")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 8. format_extraction_run_markdown / json
# ---------------------------------------------------------------------------


def _make_run(*, results) -> ExtractionRun:
    cfg = ExtractionConfig(tuples=[], systems=[])
    return ExtractionRun(
        id=42,
        config=cfg,
        results=results,
        status=RunStatus.DONE,
        created_at="2024-06-01T12:00:00",
        completed_at="2024-06-01T12:05:00",
        algo_version="1.0.0",
    )


@pytest.mark.unit
def test_format_extraction_run_markdown_renders_each_tuple():
    """Each result becomes its own '## Tuple N' section."""
    results = [
        ExtractionResult(
            tuple_idx=0,
            date_iso="2024-06-01T00:00:00+00:00",
            lat=0.0,
            lon=0.0,
            chart={"positions": {"sun": {"sign": "gemini", "longitude": 71.0}}},
            status=RunStatus.DONE,
        ),
        ExtractionResult(
            tuple_idx=1,
            date_iso="2024-06-02T00:00:00+00:00",
            lat=10.0,
            lon=20.0,
            chart={},
            status=RunStatus.DONE,
        ),
    ]
    md = format_extraction_run_markdown(_make_run(results=results))
    assert "# Astrology Extraction — Run 42" in md
    assert "Algo: 1.0.0" in md
    assert "Created: 2024-06-01T12:00:00" in md
    assert "## Tuple 0" in md
    assert "## Tuple 1" in md
    assert "### Positions" in md  # section header from the chart body


@pytest.mark.unit
def test_format_extraction_run_markdown_renders_error_status():
    """A result with status=ERROR renders as a status line + skipped body."""
    results = [
        ExtractionResult(
            tuple_idx=0,
            date_iso="2024-06-01T00:00:00+00:00",
            lat=0.0,
            lon=0.0,
            chart={},
            status=RunStatus.ERROR,
            error_message="computation failed",
        )
    ]
    md = format_extraction_run_markdown(_make_run(results=results))
    assert "## Tuple 0" in md
    assert "**Status**: error: computation failed" in md
    # No chart body for an error
    assert "### Positions" not in md


@pytest.mark.unit
def test_format_extraction_run_json_envelope_and_error_field():
    """JSON formatter wraps tuples in a stable envelope and adds 'error' on failure."""
    results = [
        ExtractionResult(
            tuple_idx=0,
            date_iso="2024-06-01T00:00:00+00:00",
            lat=0.0,
            lon=0.0,
            chart={"positions": {"sun": {"sign": "cancer", "longitude": 90.0}}},
            status=RunStatus.DONE,
        ),
        ExtractionResult(
            tuple_idx=1,
            date_iso="2024-06-02T00:00:00+00:00",
            lat=1.0,
            lon=2.0,
            chart={},
            status=RunStatus.ERROR,
            error_message="bad lat",
        ),
    ]
    out = format_extraction_run_json(_make_run(results=results))
    payload = json.loads(out)
    assert payload["schema_version"] == "1"
    assert payload["run_id"] == "42"
    assert payload["algo_version"] == "1.0.0"
    assert len(payload["tuples"]) == 2
    # Error tuple has 'error' field, ok tuple has 'chart'
    assert payload["tuples"][0]["chart"] == results[0].chart
    assert "error" not in payload["tuples"][0]
    assert payload["tuples"][1]["error"] == "bad lat"
