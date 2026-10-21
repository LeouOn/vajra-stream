"""OUT-2: cosmic weather must not fabricate a Vimshottari dasha or gochara.

Before this fix, ``_gather_astrology_context`` passed the TARGET date as the
BIRTH date to ``calculate_vimshottari_dasha`` and ``get_vedic_gochara``, then
printed ``dasha_periods[0]`` (the first period FROM BIRTH) as if it were the
current period. Both lines were true-by-construction and meaningless; a dasha
or gochara belongs to a NATAL chart. Now both blocks run only when ``natal_dt``
is provided, and the printed period is the one whose [start, end) interval
contains the target date (both sides normalised to aware UTC under the
engine's documented policy: naive == UTC).

Offline and deterministic: fake-engine argument/selection tests plus ONE
real-engine test whose expectation comes from an independent swisseph oracle
written in this file. No network, no LLM, no DB writes.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest
import swisseph as swe

from core.astrology import AstrologicalCalculator
from core.outlook_generator import OutlookGenerator

SF_LAT = 37.7749
SF_LON = -122.4194
SF_LOC = (SF_LAT, SF_LON)

TARGET = datetime(2026, 10, 20, 17, 0, 0, tzinfo=timezone.utc)
NATAL = datetime(1990, 5, 6, 14, 30, 0, tzinfo=timezone.utc)
NATAL_LOC = (51.5074, -0.1278)  # London — distinct from SF on purpose

# Hand-built period table: three contiguous [start, end) intervals.
PERIODS_NAIVE = [
    {"ruler": "Sun", "start": "2000-01-01T00:00:00", "end": "2010-01-01T00:00:00"},
    {"ruler": "Moon", "start": "2010-01-01T00:00:00", "end": "2020-01-01T00:00:00"},
    {"ruler": "Mars", "start": "2020-01-01T00:00:00", "end": "2030-01-01T00:00:00"},
]
PERIODS_AWARE = [
    {"ruler": "Sun", "start": "2000-01-01T00:00:00+00:00", "end": "2010-01-01T00:00:00+00:00"},
    {"ruler": "Moon", "start": "2010-01-01T00:00:00+00:00", "end": "2020-01-01T00:00:00+00:00"},
    {"ruler": "Mars", "start": "2020-01-01T00:00:00+00:00", "end": "2030-01-01T00:00:00+00:00"},
]
FAKE_GOCHARA = {
    "mars": {"gochara_house": 3, "transit_rashi": "Mesha (Aries)", "transit_rashi_name": "Mesha"},
    "jupiter": {"gochara_house": 7, "transit_rashi": "Karka (Cancer)", "transit_rashi_name": "Karka"},
}


class DashaRecordingEngine:
    """Real engine for chart/moon; records and stubs the two natal calls."""

    def __init__(self, periods=None, gochara=None):
        self.real = AstrologicalCalculator()
        self.periods = periods if periods is not None else PERIODS_NAIVE
        self.gochara = gochara if gochara is not None else dict(FAKE_GOCHARA)
        self.dasha_calls: list[tuple] = []
        self.gochara_calls: list[tuple] = []

    def calculate_chart(self, date, lat, lon, name=""):
        return self.real.calculate_chart(date, lat, lon)

    def get_moon_phase(self, dt):
        return self.real.get_moon_phase(dt)

    def calculate_vimshottari_dasha(self, birth_dt, location):
        self.dasha_calls.append((birth_dt, location))
        return list(self.periods)

    def get_vedic_gochara(self, natal_dt, natal_location, transit_dt=None):
        self.gochara_calls.append((natal_dt, natal_location, transit_dt))
        return dict(self.gochara)

    def __getattr__(self, item):
        return getattr(self.real, item)


@pytest.fixture()
def make_generator(monkeypatch: pytest.MonkeyPatch):
    def _make(periods=None, gochara=None) -> tuple[OutlookGenerator, DashaRecordingEngine]:
        gen = OutlookGenerator()
        engine = DashaRecordingEngine(periods=periods, gochara=gochara)
        monkeypatch.setattr(gen, "astro_engine", engine)
        return gen, engine

    return _make


def _dasha_line(report: str) -> str:
    for line in report.splitlines():
        if line.startswith("Vimshottari Dasha:"):
            return line
    return ""


def _vimshottari_oracle(natal: datetime, target: datetime):
    """Independent swisseph oracle for the current mahadasha.

    Mirrors the convention the engine documents: sidereal (Lahiri) Moon;
    nakshatra = int(sidereal_moon / (360/27)); the first mahadasha ruler is
    that nakshatra's lord (sequence Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7,
    Rahu 18, Jupiter 16, Saturn 19, Mercury 17 years); the first period's
    balance is (1 - elapsed fraction) of its years; a dasha year is 365.25
    days — the conventional vimshottari year (a mean solar year). The oracle
    uses that convention to PREDICT the engine's output; the tests pin the
    call site's selection and labelling, not the convention itself.
    """
    order = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    years = {
        "Ketu": 7,
        "Venus": 20,
        "Sun": 6,
        "Moon": 10,
        "Mars": 7,
        "Rahu": 18,
        "Jupiter": 16,
        "Saturn": 19,
        "Mercury": 17,
    }

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(natal.year, natal.month, natal.day, natal.hour + natal.minute / 60.0)
    moon_lon = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)[0][0]

    nak_width = 360.0 / 27.0
    nak_idx = int(moon_lon / nak_width)
    nak_progress = (moon_lon % nak_width) / nak_width
    first_idx = nak_idx % 9
    first_ruler = order[first_idx]
    first_remaining = years[first_ruler] * (1.0 - nak_progress)

    cursor = natal
    periods = []
    end = cursor + timedelta(days=first_remaining * 365.25)
    periods.append((first_ruler, cursor, end))
    cursor = end
    idx = (first_idx + 1) % 9
    for _ in range(9):
        ruler = order[idx]
        end = cursor + timedelta(days=years[ruler] * 365.25)
        periods.append((ruler, cursor, end))
        cursor = end
        idx = (idx + 1) % 9

    return next((r, s, e) for r, s, e in periods if s <= target < e)


class TestNoNatalDataOmitsBothBlocks:
    def test_neither_engine_method_is_called_and_no_lines(self, make_generator):
        gen, engine = make_generator()
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=TARGET, natal_dt=None)
        assert engine.dasha_calls == [], f"dasha called with: {engine.dasha_calls}"
        assert engine.gochara_calls == [], f"gochara called with: {engine.gochara_calls}"
        assert _dasha_line(report) == ""
        assert "Gochara" not in report


class TestNatalDataDrivesCorrectCalls:
    def test_dasha_receives_natal_gochara_receives_natal_and_target(self, make_generator):
        gen, engine = make_generator()
        report = gen._gather_astrology_context(
            lat=SF_LAT, lon=SF_LON, date=TARGET, natal_dt=NATAL, natal_location=NATAL_LOC
        )
        assert engine.dasha_calls == [(NATAL, NATAL_LOC)]
        assert engine.gochara_calls == [(NATAL, NATAL_LOC, TARGET)]
        assert _dasha_line(report) == "Vimshottari Dasha: Mars period (2020-01-01 to 2030-01-01)"
        assert "Gochara (Transit Houses from Moon):" in report

    def test_natal_location_falls_back_to_target_location(self, make_generator):
        gen, engine = make_generator()
        gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=TARGET, natal_dt=NATAL)
        assert engine.dasha_calls == [(NATAL, SF_LOC)]
        assert engine.gochara_calls == [(NATAL, SF_LOC, TARGET)]


class TestPeriodSelection:
    def test_target_in_second_period_naive_strings(self, make_generator):
        gen, _ = make_generator(periods=PERIODS_NAIVE)
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=TARGET, natal_dt=NATAL)
        assert _dasha_line(report) == "Vimshottari Dasha: Mars period (2020-01-01 to 2030-01-01)"

    def test_target_in_second_period_aware_strings(self, make_generator):
        gen, _ = make_generator(periods=PERIODS_AWARE)
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=TARGET, natal_dt=NATAL)
        assert _dasha_line(report) == "Vimshottari Dasha: Mars period (2020-01-01 to 2030-01-01)"

    def test_target_before_first_period_omits_line(self, make_generator):
        gen, _ = make_generator()
        early = datetime(1999, 6, 15, tzinfo=timezone.utc)
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=early, natal_dt=NATAL)
        assert _dasha_line(report) == ""

    def test_target_after_last_period_omits_line(self, make_generator):
        gen, _ = make_generator()
        late = datetime(2031, 1, 1, tzinfo=timezone.utc)
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=late, natal_dt=NATAL)
        assert _dasha_line(report) == ""

    def test_interval_is_start_inclusive_end_exclusive(self, make_generator):
        gen, _ = make_generator()
        boundary = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=boundary, natal_dt=NATAL)
        assert _dasha_line(report) == "Vimshottari Dasha: Mars period (2020-01-01 to 2030-01-01)"

    def test_naive_target_date_selects_like_utc(self, make_generator):
        gen, _ = make_generator()
        naive_target = datetime(2026, 10, 20, 17, 0, 0)  # engine policy: naive == UTC
        report = gen._gather_astrology_context(lat=SF_LAT, lon=SF_LON, date=naive_target, natal_dt=NATAL)
        assert _dasha_line(report) == "Vimshottari Dasha: Mars period (2020-01-01 to 2030-01-01)"


class TestRealEngineMatchesIndependentOracle:
    def test_report_line_matches_swisseph_oracle(self):
        expected = _vimshottari_oracle(NATAL, TARGET)
        expected_line = f"Vimshottari Dasha: {expected[0]} period ({expected[1].date().isoformat()} to {expected[2].date().isoformat()})"

        gen = OutlookGenerator()
        report = gen._gather_astrology_context(
            lat=SF_LAT, lon=SF_LON, date=TARGET, natal_dt=NATAL, natal_location=SF_LOC
        )
        assert _dasha_line(report) == expected_line
        assert "Gochara (Transit Houses from Moon):" in report


class TestFixedVectorFromIndependentReview:
    """An independent reviewer's measured vector (2026-10-21): natal 2000-01-01T12:00Z at
    San Francisco, forecast 2026-10-20T12:00Z. Correct current mahadasha:
    Saturn 2016-09-18 to 2035-09-19. Correct gochara counted from the NATAL
    Moon (inclusive forward: same sign = house 1): Sun1, Moon4, Mercury1,
    Venus1, Mars10, Jupiter10, Saturn6, Uranus8, Neptune6, Pluto4, Rahu5,
    Ketu11."""

    VECTOR_NATAL = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    VECTOR_TARGET = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
    EXPECTED_GOCHARA_HOUSES = {
        "sun": 1,
        "moon": 4,
        "mercury": 1,
        "venus": 1,
        "mars": 10,
        "jupiter": 10,
        "saturn": 6,
        "uranus": 8,
        "neptune": 6,
        "pluto": 4,
        "rahu": 5,
        "ketu": 11,
    }

    def test_dasha_and_rendered_gochara_match_review_vector(self):
        gen = OutlookGenerator()
        report = gen._gather_astrology_context(
            lat=SF_LAT, lon=SF_LON, date=self.VECTOR_TARGET, natal_dt=self.VECTOR_NATAL, natal_location=SF_LOC
        )
        assert _dasha_line(report) == "Vimshottari Dasha: Saturn period (2016-09-18 to 2035-09-19)"

        seen: dict[str, int] = {}
        in_gochara = False
        for line in report.splitlines():
            if line.startswith("Gochara"):
                in_gochara = True
                continue
            if in_gochara:
                match = re.match(r"\s+(\w+): House (\d+) from Moon", line)
                if match:
                    seen[match.group(1).lower()] = int(match.group(2))
        assert seen, "no gochara planet lines rendered"
        for planet, house in seen.items():
            assert (
                house == self.EXPECTED_GOCHARA_HOUSES[planet]
            ), f"{planet}: rendered House {house}, review vector expects {self.EXPECTED_GOCHARA_HOUSES[planet]}"

    def test_full_engine_gochara_table_matches_review_vector(self):
        calc = AstrologicalCalculator()
        gochara = calc.get_vedic_gochara(self.VECTOR_NATAL, SF_LOC, self.VECTOR_TARGET)
        for planet, expected_house in self.EXPECTED_GOCHARA_HOUSES.items():
            assert (
                gochara[planet]["gochara_house"] == expected_house
            ), f"{planet}: engine says {gochara[planet]['gochara_house']}, expects {expected_house}"

    def test_oracle_agrees_with_review_vector(self):
        ruler, start, end = _vimshottari_oracle(self.VECTOR_NATAL, self.VECTOR_TARGET)
        assert ruler == "Saturn"
        assert start.date().isoformat() == "2016-09-18"
        assert end.date().isoformat() == "2035-09-19"
