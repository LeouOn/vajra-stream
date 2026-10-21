"""OUT-1: consistent time handling in the outlook generator.

The three ``date or datetime.now()`` sites (``_gather_astrology_context`` and
the two ``calculate_chart`` calls in ``generate_single_outlook`` /
``generate_epic_outlook``) used a NAIVE local wall-clock ``now()`` while the
astro engine treats naive datetimes as UTC. On a UTC-7 host every default
generation computed a sky 7 hours early, and the longitude-derived
"Local Time" line printed a clock 7 hours off.

Contract pinned here (documented in ``_gather_astrology_context``):
- ``date=None``  -> aware UTC now (``datetime.now(timezone.utc)``);
- aware ``date`` -> converted to UTC before use;
- naive  ``date`` -> passed through unchanged; the engine's documented policy
  treats naive as UTC (no local-zone guessing at this layer).

Offline: a frozen clock simulates a UTC-7 host (naive wall clock 10:14,
UTC instant 17:14), and a recording engine delegates to the real calculator
so all chart shapes stay genuine. No network, no LLM, no DB writes.

OUT-3 additions: the "Local Time" line no longer claims a civil zone — it
prints the UTC instant and the local MEAN SOLAR time (UTC + lon/15 h,
continuous); an offset-less tzinfo (utcoffset() is None) is treated as naive
per the engine policy instead of being folded to the host zone by
astimezone(); non-datetime date arguments are refused with a clear typed
error; and the two endpoint date_generated writes store AWARE UTC stamps.
"""

from datetime import date, datetime, timedelta, timezone, tzinfo

import pytest

import core.outlook_generator as outlook_module
from core.astrology import AstrologicalCalculator
from core.outlook_generator import OutlookGenerator

SF_LAT = 37.7749
SF_LON = -122.4194  # round(-122.4194 / 15.0) == -8 -> "PDT (approx)" label

# A frozen instant expressed two ways, as a real PDT host would see it.
NAIVE_WALL_PDT = datetime(2026, 10, 20, 10, 14, 0)  # local wall clock, no tzinfo
UTC_INSTANT = datetime(2026, 10, 20, 17, 14, 0, tzinfo=timezone.utc)  # same moment
AWARE_PDT = datetime(2026, 10, 20, 10, 14, 0, tzinfo=timezone(timedelta(hours=-7)))
NAIVE_UTC_INPUT = datetime(2026, 10, 20, 17, 14, 0)  # genuinely-UTC naive input


class _FrozenClock(datetime):
    """Behaves like datetime on a UTC-7 host: naive wall clock vs aware UTC."""

    naive_wall = NAIVE_WALL_PDT
    utc_instant = UTC_INSTANT

    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return cls.utc_instant
        return cls.naive_wall


class RecordingEngine:
    """Delegates to the real calculator and records every datetime it receives."""

    def __init__(self):
        self.real = AstrologicalCalculator()
        self.seen: list[tuple[str, datetime]] = []

    def calculate_chart(self, date, lat, lon, name=""):
        self.seen.append(("calculate_chart", date))
        return self.real.calculate_chart(date, lat, lon)

    def get_moon_phase(self, dt):
        self.seen.append(("get_moon_phase", dt))
        return self.real.get_moon_phase(dt)

    def __getattr__(self, item):
        return getattr(self.real, item)


@pytest.fixture()
def frozen_pdt_host(monkeypatch: pytest.MonkeyPatch):
    """Freeze the module clock to a simulated UTC-7 host."""
    monkeypatch.setattr(outlook_module, "datetime", _FrozenClock)


@pytest.fixture()
def generator(monkeypatch: pytest.MonkeyPatch) -> tuple[OutlookGenerator, RecordingEngine]:
    gen = OutlookGenerator()
    engine = RecordingEngine()
    monkeypatch.setattr(gen, "astro_engine", engine)
    return gen, engine


def _local_time_line(report: str) -> str:
    for line in report.splitlines():
        if line.startswith("Local Time:"):
            return line
    return ""


class TestDefaultNowIsAwareUtc:
    def test_engine_receives_aware_utc_when_date_is_none(self, generator, frozen_pdt_host):
        gen, engine = generator
        gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=None)
        chart_dts = [dt for name, dt in engine.seen if name == "calculate_chart"]
        assert chart_dts, "engine received no calculate_chart call"
        for dt in chart_dts:
            assert dt.tzinfo is not None, f"engine received naive datetime: {dt!r}"
            assert dt == UTC_INSTANT, f"engine received {dt!r}, expected {UTC_INSTANT!r}"

    def test_local_time_line_matches_utc_instant(self, generator, frozen_pdt_host):
        gen, _ = generator
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=None)
        # OUT-3: the line is now honest — the UTC instant plus the local mean
        # solar time (UTC + lon/15 h, continuous). SF: -122.4194/15 h =
        # -8 h 09 m 41 s -> 17:14 - 8:09:41 = 09:04. No zone name is claimed.
        assert "Local Time: 2026-10-20 17:14 UTC (local solar time 09:04 at 122.42 W)" in report


class TestExplicitDateContract:
    def test_aware_date_is_converted_to_utc(self, generator):
        gen, engine = generator
        gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=AWARE_PDT)
        chart_dts = [dt for name, dt in engine.seen if name == "calculate_chart"]
        assert chart_dts
        for dt in chart_dts:
            assert dt.tzinfo is not None
            assert dt == UTC_INSTANT, f"aware PDT input not converted: {dt!r}"

    def test_naive_date_passes_through_as_utc_policy(self, generator):
        gen, engine = generator
        gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=NAIVE_UTC_INPUT)
        chart_dts = [dt for name, dt in engine.seen if name == "calculate_chart"]
        assert chart_dts
        for dt in chart_dts:
            assert dt == NAIVE_UTC_INPUT
            assert dt.tzinfo is None, "naive input must pass through (engine treats naive as UTC)"

    def test_naive_date_local_time_line_unchanged(self, generator):
        gen, _ = generator
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=NAIVE_UTC_INPUT)
        # 17:14 naive (== UTC by policy): the same UTC-labelled line — the
        # solar offset does not depend on how the instant was supplied.
        assert "Local Time: 2026-10-20 17:14 UTC (local solar time 09:04 at 122.42 W)" in report


class TestAllThreeSitesBehaveTheSame:
    def test_generate_single_outlook_chart_gets_aware_utc_now(self, generator, frozen_pdt_host):
        gen, engine = generator
        gen.generate_single_outlook(lat=SF_LAT, lon=SF_LON, languages=["English"], date=None, model=None)
        chart_dts = [dt for name, dt in engine.seen if name == "calculate_chart"]
        assert chart_dts
        for dt in chart_dts:
            assert dt.tzinfo is not None, f"site received naive datetime: {dt!r}"
            assert dt == UTC_INSTANT

    def test_generate_epic_outlook_chart_gets_aware_utc_now(self, generator, frozen_pdt_host):
        gen, engine = generator
        try:
            gen.generate_epic_outlook(lat=SF_LAT, lon=SF_LON, languages=["English"], stages=1, date=None, model=None)
        except TypeError:
            pytest.fail("generate_epic_outlook signature mismatch - adjust the call, not the module")
        chart_dts = [dt for name, dt in engine.seen if name == "calculate_chart"]
        assert chart_dts
        for dt in chart_dts:
            assert dt.tzinfo is not None, f"site received naive datetime: {dt!r}"
            assert dt == UTC_INSTANT


class _OffsetLessTZ(tzinfo):
    """A tzinfo whose utcoffset() is None: aware-by-attribute, offset-less."""

    def utcoffset(self, dt):
        return None

    def tzname(self, dt):
        return "OffsetLess"

    def dst(self, dt):
        return None


class TestOut3HonestSolarTimeLine:
    """The Local Time line: UTC instant + local mean solar time, no zone name.

    Expected strings are pre-computed LITERALS (solar = UTC + lon/15 h, then
    %H:%M) so the test pins the arithmetic independently of the code.
    Winter and summer share the same solar offset on purpose: a mean solar
    clock has no DST, which is exactly why no civil zone name is claimed.
    """

    UTC_INPUT = datetime(2026, 10, 20, 17, 14, 0, tzinfo=timezone.utc)

    @pytest.mark.parametrize(
        ("lat", "lon", "expected_line"),
        [
            # SF summer: -122.4194/15 h = -8 h 09 m 41 s -> 09:04
            (
                SF_LAT,
                SF_LON,
                "Local Time: 2026-10-20 17:14 UTC (local solar time 09:04 at 122.42 W)",
            ),
            # SF winter (same instant, January): identical solar arithmetic
            (
                SF_LAT,
                SF_LON,
                "Local Time: 2026-10-20 17:14 UTC (local solar time 09:04 at 122.42 W)",
            ),
            # Denver: -104.9903/15 h = -6 h 59 m 58 s -> 10:14 (civil MDT is 11:14)
            (
                39.7392,
                -104.9903,
                "Local Time: 2026-10-20 17:14 UTC (local solar time 10:14 at 104.99 W)",
            ),
            # -112.5: exactly -7.5 h -> 09:44 (the old round-half-even trap)
            (
                40.0,
                -112.5,
                "Local Time: 2026-10-20 17:14 UTC (local solar time 09:44 at 112.50 W)",
            ),
            # India: +77.2094/15 h = +5 h 08 m 50 s -> 22:22 (civil IST is 22:44)
            (
                28.6139,
                77.2094,
                "Local Time: 2026-10-20 17:14 UTC (local solar time 22:22 at 77.21 E)",
            ),
            # Nepal: +85.3240/15 h = +5 h 41 m 18 s -> 22:55 (civil NPT is 22:59)
            (
                27.7172,
                85.3240,
                "Local Time: 2026-10-20 17:14 UTC (local solar time 22:55 at 85.32 E)",
            ),
        ],
    )
    def test_solar_time_line_is_exact_and_zone_free(self, generator, lat, lon, expected_line):
        gen, _ = generator
        date_input = self.UTC_INPUT
        report = gen._gather_astrology_context(lat=lat, lon=lon, date=date_input)
        line = _local_time_line(report)
        assert line == expected_line
        # No civil-zone claim may survive anywhere in the line.
        for zone_token in ("PDT", "PST", "UTC+", "UTC-", "(approx)"):
            assert zone_token not in line, f"zone claim {zone_token!r} resurrected: {line!r}"

    def test_winter_and_summer_share_the_solar_offset(self, generator):
        """January vs October: the solar line differs by nothing but the date,
        documenting that no DST calendar is being claimed."""
        gen, _ = generator
        summer = _local_time_line(gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=self.UTC_INPUT))
        winter = _local_time_line(
            gen._gather_astrology_context(
                lat=SF_LAT,
                lon=SF_LON,
                date=datetime(2026, 1, 15, 17, 14, 0, tzinfo=timezone.utc),
            )
        )
        assert summer == "Local Time: 2026-10-20 17:14 UTC (local solar time 09:04 at 122.42 W)"
        assert winter == "Local Time: 2026-01-15 17:14 UTC (local solar time 09:04 at 122.42 W)"


class TestOut3bSolarDateClause:
    """OUT-3b: when the solar calendar date differs from the UTC date, the
    line carries ` on YYYY-MM-DD`; when equal, byte-identical to OUT-3.

    Expected strings are hand-computed literals (solar = UTC + lon/15 h,
    clock floored to the minute), independent of the code under test.
    """

    @pytest.mark.parametrize(
        ("utc_input", "lon", "expected_line"),
        [
            # SF, previous solar day: 02:00 - 8h09m41s = 17:50 on 2026-10-20
            (
                datetime(2026, 10, 21, 2, 0, 0, tzinfo=timezone.utc),
                -122.42,
                "Local Time: 2026-10-21 02:00 UTC (local solar time 17:50 on 2026-10-20 at 122.42 W)",
            ),
            # Tokyo, next solar day: 23:30 + 9h18m46s = 08:48 on 2026-10-22
            (
                datetime(2026, 10, 21, 23, 30, 0, tzinfo=timezone.utc),
                139.69,
                "Local Time: 2026-10-21 23:30 UTC (local solar time 08:48 on 2026-10-22 at 139.69 E)",
            ),
            # Auckland, next solar day: 23:30 + 11h39m02s = 11:09 on 2026-10-22
            (
                datetime(2026, 10, 21, 23, 30, 0, tzinfo=timezone.utc),
                174.76,
                "Local Time: 2026-10-21 23:30 UTC (local solar time 11:09 on 2026-10-22 at 174.76 E)",
            ),
            # New Year, westward: 2026-01-01 00:30 - 8h09m41s = 2025-12-31 16:20
            (
                datetime(2026, 1, 1, 0, 30, 0, tzinfo=timezone.utc),
                -122.42,
                "Local Time: 2026-01-01 00:30 UTC (local solar time 16:20 on 2025-12-31 at 122.42 W)",
            ),
            # New Year, eastward: 2025-12-31 23:30 + 9h18m46s = 2026-01-01 08:48
            (
                datetime(2025, 12, 31, 23, 30, 0, tzinfo=timezone.utc),
                139.69,
                "Local Time: 2025-12-31 23:30 UTC (local solar time 08:48 on 2026-01-01 at 139.69 E)",
            ),
            # Exactly zero offset: dates always equal, no clause, OUT-3 shape
            (
                datetime(2026, 10, 20, 17, 14, 0, tzinfo=timezone.utc),
                0.0,
                "Local Time: 2026-10-20 17:14 UTC (local solar time 17:14 at 0.00 E)",
            ),
            # Solar midnight of the SAME date (120 W is exactly -8h): no clause
            (
                datetime(2026, 10, 21, 8, 0, 0, tzinfo=timezone.utc),
                -120.0,
                "Local Time: 2026-10-21 08:00 UTC (local solar time 00:00 at 120.00 W)",
            ),
            # One minute earlier is 23:59 of the PREVIOUS date: clause
            (
                datetime(2026, 10, 21, 7, 59, 0, tzinfo=timezone.utc),
                -120.0,
                "Local Time: 2026-10-21 07:59 UTC (local solar time 23:59 on 2026-10-20 at 120.00 W)",
            ),
        ],
    )
    def test_date_clause_exactly_when_dates_differ(self, generator, utc_input, lon, expected_line):
        gen, _ = generator
        report = gen._gather_astrology_context(lat=10.0, lon=lon, date=utc_input)
        assert _local_time_line(report) == expected_line

    def test_clause_presence_tracks_date_difference_over_a_grid(self, generator):
        """Property: over a deterministic grid, the clause appears EXACTLY on
        the cases whose solar date differs, with the right date value."""
        gen, _ = generator
        lons = (-179.99, -122.4194, -120.0, -74.006, -0.01, 0.0, 15.0, 77.2094, 139.6917, 151.2093, 174.76, 179.99)
        checked = 0
        with_clause = 0
        minute = 0
        while minute <= 2 * 24 * 60:
            utc = datetime(2026, 3, 1, tzinfo=timezone.utc) + timedelta(minutes=minute)
            for lon in lons:
                solar = utc + timedelta(hours=lon / 15.0)
                expected = (
                    f"Local Time: {utc.strftime('%Y-%m-%d %H:%M')} UTC "
                    f"(local solar time {solar.strftime('%H:%M')}"
                    + (f" on {solar.strftime('%Y-%m-%d')}" if solar.date() != utc.date() else "")
                    + f" at {abs(lon):.2f} {'W' if lon < 0 else 'E'})"
                )
                report = gen._gather_astrology_context(lat=10.0, lon=lon, date=utc)
                assert _local_time_line(report) == expected, f"lon={lon} utc={utc.isoformat()}"
                checked += 1
                if solar.date() != utc.date():
                    with_clause += 1
            minute += 37
        assert checked > 200, "grid unexpectedly small"
        assert with_clause > 20, "grid should cross solar midnight in both directions"


class TestOut3OffsetLessTzinfo:
    """utcoffset() is None -> treated as naive (engine policy), never folded
    to the host zone by astimezone()."""

    def test_offset_less_tzinfo_passes_through_unchanged(self, generator):
        gen, engine = generator
        offset_less = datetime(2026, 10, 20, 17, 14, 0, tzinfo=_OffsetLessTZ())
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=offset_less)

        chart_dts = [dt for name, dt in engine.seen if name == "calculate_chart"]
        assert chart_dts, "engine received no calculate_chart call"
        for dt in chart_dts:
            assert dt.utcoffset() is None, (
                f"offset-less datetime was folded to a zone (became {dt!r}); " "policy: treat as naive UTC"
            )
            assert dt.replace(tzinfo=None) == datetime(2026, 10, 20, 17, 14), f"wall clock moved: {dt!r}"
        # The printed line must be the 17:14 UTC instant, not a folded one.
        assert "Local Time: 2026-10-20 17:14 UTC" in report


class TestOut3NonDatetimeRefusal:
    """datetime.date / str inputs get a clear typed refusal, not an
    AttributeError from deep inside the normalizer."""

    @pytest.mark.parametrize(
        ("bad_date", "type_name"),
        [(date(2026, 10, 20), "date"), ("2026-10-20", "str")],
    )
    def test_non_datetime_is_refused_with_type_name(self, generator, bad_date, type_name):
        gen, _ = generator
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=bad_date)
        assert "Astrological context unavailable" in report
        assert f"date must be a datetime, got {type_name!r}" in report, report


class TestOut3EndpointDateGeneratedIsAwareUtc:
    """The two INSERT sites store aware UTC timestamps (OUT-3).

    Offline: the app's TestClient with the outlook generator mocked (no LLM)
    and get_db_connection mocked to a capturing cursor (no DB touched).
    """

    _SINGLE_RESULT = {
        "status": "success",
        "type": "single",
        "genre": "healing",
        "languages": ["English"],
        "astrology_used": "alignment",
        "divination_used": "divination",
        "divination_raw": {},
        "entities_used": "Buddha",
        "narrative": "A peaceful deterministic test blessing.",
    }

    @staticmethod
    def _insert_args(mock_conn, call_index=0):
        cursor = mock_conn.return_value.cursor.return_value
        return cursor.execute.call_args_list[call_index].args[1]

    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from backend.app.main import app

        return TestClient(app)

    def test_default_stamp_is_aware_utc_single(self, client):
        from unittest.mock import patch

        with (
            patch("container.container.outlook.generate_single", return_value=dict(self._SINGLE_RESULT)),
            patch("backend.app.api.v1.endpoints.outlook.get_db_connection") as mock_conn,
        ):
            response = client.post("/api/v1/outlook/generate_single", json={"lat": SF_LAT, "lon": SF_LON})
        assert response.status_code == 200, response.text
        stamp = datetime.fromisoformat(self._insert_args(mock_conn)[5])
        assert stamp.tzinfo is not None and stamp.utcoffset() == timedelta(
            0
        ), f"date_generated must be aware UTC, got {stamp!r}"

    def test_supplied_aware_date_is_converted_to_utc(self, client):
        from unittest.mock import patch

        with (
            patch("container.container.outlook.generate_single", return_value=dict(self._SINGLE_RESULT)),
            patch("backend.app.api.v1.endpoints.outlook.get_db_connection") as mock_conn,
        ):
            response = client.post(
                "/api/v1/outlook/generate_single",
                json={"lat": SF_LAT, "lon": SF_LON, "date": "2026-10-20T10:14:00-07:00"},
            )
        assert response.status_code == 200, response.text
        assert self._insert_args(mock_conn)[5] == "2026-10-20T17:14:00+00:00"

    def test_supplied_naive_date_stored_as_given(self, client):
        from unittest.mock import patch

        with (
            patch("container.container.outlook.generate_single", return_value=dict(self._SINGLE_RESULT)),
            patch("backend.app.api.v1.endpoints.outlook.get_db_connection") as mock_conn,
        ):
            response = client.post(
                "/api/v1/outlook/generate_single",
                json={"lat": SF_LAT, "lon": SF_LON, "date": "2026-10-20T17:14:00"},
            )
        assert response.status_code == 200, response.text
        assert self._insert_args(mock_conn)[5] == "2026-10-20T17:14:00"

    def test_default_stamp_is_aware_utc_epic(self, client):
        from unittest.mock import patch

        epic_result = {
            "status": "success",
            "type": "epic",
            "genre": "healing",
            "languages": ["English"],
            "astrology_used": "alignment",
            "divination_used": "divination",
            "divination_raw": {},
            "entities_used": "Buddha",
            "narrative_parts": ["Part one.", "Part two."],
        }
        with (
            patch("container.container.outlook.generate_epic", return_value=epic_result),
            patch("backend.app.api.v1.endpoints.outlook.get_db_connection") as mock_conn,
        ):
            response = client.post("/api/v1/outlook/generate_epic", json={"lat": SF_LAT, "lon": SF_LON})
        assert response.status_code == 200, response.text
        stamp = datetime.fromisoformat(self._insert_args(mock_conn)[5])
        assert stamp.tzinfo is not None and stamp.utcoffset() == timedelta(
            0
        ), f"epic date_generated must be aware UTC, got {stamp!r}"
