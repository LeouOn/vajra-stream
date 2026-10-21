"""IR-5: naive-datetime Vedic calls and Chiron availability flags.

Covers three verified defects (docs/notes/audit-silent-failures-2026-10-08.md,
Ticket 3, Proofs 1-2):

1. ``get_indian_astrology`` (and therefore ``calculate_vimshottari_dasha`` and
   ``get_vedic_gochara``) crashes with ``TypeError`` on offset-naive datetimes
   at the sunrise comparison, so cosmic weather silently omitted both blocks.
2. Chiron is silently dropped from Western and Vedic positions when the
   Swiss Ephemeris asteroid file (``seas_18.se1``) is unavailable. The fix
   keeps the position tables shape-pure and reports the absence in a
   sibling ``"unavailable_bodies"`` key on the Western/Vedic result dicts.
3. Consumers of the positions dicts keep working: the tables contain only
   real bodies, so no consumer changes are needed.

Offline and deterministic: fixed dates, a forced Chiron ephemeris error via
monkeypatch (so the tests pass regardless of whether the host has the
asteroid files), no network, no DB writes (repo conftest active).
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
import swisseph as swe

from core.astrology import AstrologicalCalculator

SF = (37.7749, -122.4194)
NAIVE_DT = datetime(2026, 10, 20, 12, 0, 0)
AWARE_DT = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def calc() -> AstrologicalCalculator:
    return AstrologicalCalculator()


@pytest.fixture()
def forced_chiron_error(monkeypatch: pytest.MonkeyPatch):
    """Make ``swe.calc_ut`` raise the real missing-ephemeris error for Chiron.

    The error class and message mirror the field reproduction
    (``swisseph.Error: SwissEph file 'seas_18.se1' not found``). All other
    bodies pass through to the real ephemeris, keeping the test offline and
    deterministic on hosts that DO bundle the asteroid files.
    """
    real_calc_ut = swe.calc_ut
    chiron_id = getattr(swe, "CHIRON", 15)

    def fake_calc_ut(jd, ipl, flags=0):
        if ipl == chiron_id:
            raise swe.Error("SwissEph file 'seas_18.se1' not found (forced for test)")
        return real_calc_ut(jd, ipl, flags)

    monkeypatch.setattr(swe, "calc_ut", fake_calc_ut)


class TestNaiveDatetimeVedic:
    def test_vimshottari_dasha_accepts_naive_and_aware(self, calc):
        for dt in (NAIVE_DT, AWARE_DT):
            periods = calc.calculate_vimshottari_dasha(dt, SF)
            assert isinstance(periods, list)
            assert len(periods) > 0
            first = periods[0]
            assert first.get("ruler")
            assert first.get("start")

    def test_vedic_gochara_accepts_naive_and_aware(self, calc):
        for dt in (NAIVE_DT, AWARE_DT):
            gochara = calc.get_vedic_gochara(dt, SF, dt)
            assert isinstance(gochara, dict)
            assert len(gochara) > 0
            for info in gochara.values():
                assert "gochara_house" in info

    def test_indian_astrology_flags_naive_assumption(self, calc):
        naive_result = calc.get_indian_astrology(NAIVE_DT, SF)
        assert naive_result["naive_datetime_assumed_utc"] is True
        aware_result = calc.get_indian_astrology(AWARE_DT, SF)
        assert aware_result["naive_datetime_assumed_utc"] is False

    def test_cosmic_weather_with_naive_natal_contains_dasha_and_gochara(self):
        # Since OUT-2, dasha and gochara are natal-chart features: they appear
        # only with birth data and are omitted without it (pinned in
        # test_outlook_dasha_callsite.py). A NAIVE natal date still revives
        # them - the IR-5 engine-level naive-datetime fix.
        from core.outlook_generator import OutlookGenerator

        generator = OutlookGenerator()
        report = generator._gather_astrology_context(
            lat=37.7749,
            lon=-122.4194,
            date=NAIVE_DT,
            natal_dt=datetime(1990, 5, 6, 14, 30, 0),  # naive natal: engine treats as UTC
        )
        assert "Vimshottari Dasha" in report
        assert "Gochara" in report


class TestComprehensiveFlagProvenance:
    """IR-5b: an originally-naive input to get_comprehensive_astrology must
    still report naive_datetime_assumed_utc=True on the Vedic result, even
    though the comprehensive wrapper localizes before delegating."""

    def test_naive_input_keeps_flag_true_through_comprehensive(self, calc):
        result = calc.get_comprehensive_astrology(NAIVE_DT, SF)
        assert result["indian"]["naive_datetime_assumed_utc"] is True

    def test_aware_input_flag_false_through_comprehensive(self, calc):
        result = calc.get_comprehensive_astrology(AWARE_DT, SF)
        assert result["indian"]["naive_datetime_assumed_utc"] is False


class TestDashaDatesAreAbsoluteUtc:
    """IR-5b: dasha start/end must be offsets-carrying UTC instants - the
    Moon is computed for the UTC instant, so the strings must say so, and
    aware non-UTC births must not accumulate DST wall-day drift."""

    def test_naive_birth_yields_offset_carrying_strings(self, calc):
        periods = calc.calculate_vimshottari_dasha(NAIVE_DT, SF)
        assert periods
        for period in periods:
            start = datetime.fromisoformat(period["start"])
            end = datetime.fromisoformat(period["end"])
            assert start.tzinfo is not None, f"start has no offset: {period['start']}"
            assert end.tzinfo is not None, f"end has no offset: {period['end']}"
            assert start.utcoffset() == timedelta(0)
            assert end.utcoffset() == timedelta(0)

    def test_aware_non_utc_birth_is_converted_to_utc(self, calc):
        la = timezone(timedelta(hours=-7))
        birth_la = datetime(2000, 1, 1, 5, 30, 0, tzinfo=la)  # 12:30Z
        birth_utc = datetime(2000, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        periods_la = calc.calculate_vimshottari_dasha(birth_la, SF)
        periods_utc = calc.calculate_vimshottari_dasha(birth_utc, SF)
        assert [p["ruler"] for p in periods_la] == [p["ruler"] for p in periods_utc]
        for p_la, p_utc in zip(periods_la, periods_utc):
            assert datetime.fromisoformat(p_la["start"]) == datetime.fromisoformat(p_utc["start"])
            assert datetime.fromisoformat(p_la["end"]) == datetime.fromisoformat(p_utc["end"])

    def test_dst_spanning_birth_matches_absolute_time(self, calc):
        # A 19-year span crosses DST transitions in a real local zone
        # (America/Los_Angeles); UTC-normalised endpoints must match the
        # equivalent UTC birth exactly. The reviewer measured a 3600 s
        # wall-day drift per spanned transition before normalisation.
        birth_wall = datetime(1990, 5, 6, 7, 30, 0, tzinfo=ZoneInfo("America/Los_Angeles"))  # 14:30Z
        birth_utc = datetime(1990, 5, 6, 14, 30, 0, tzinfo=timezone.utc)
        periods_wall = calc.calculate_vimshottari_dasha(birth_wall, SF)
        periods_utc = calc.calculate_vimshottari_dasha(birth_utc, SF)
        for p_wall, p_utc in zip(periods_wall, periods_utc):
            assert datetime.fromisoformat(p_wall["end"]) == datetime.fromisoformat(
                p_utc["end"]
            ), f"wall-day drift: {p_wall['end']} != {p_utc['end']}"


class TestChironReasonHonesty:
    """IR-5b: the unavailability reason must cover a corrupt/unreadable
    ephemeris file, and Western/Vedic must agree when Chiron is not
    configured at all ({} in both, not a spurious 'missing')."""

    def test_reason_covers_missing_or_unreadable(self, calc, forced_chiron_error):
        western = calc.get_western_astrology(AWARE_DT, SF)
        assert western["unavailable_bodies"] == {"chiron": "ephemeris file missing or unreadable"}
        vedic = calc.get_indian_astrology(AWARE_DT, SF)
        assert vedic["unavailable_bodies"] == {"chiron": "ephemeris file missing or unreadable"}

    def test_unconfigured_chiron_reports_nothing_in_both(self, calc, monkeypatch):
        patched = dict(calc.PLANETS)
        patched["chiron"] = None
        monkeypatch.setattr(calc, "PLANETS", patched)
        western = calc.get_western_astrology(AWARE_DT, SF)
        assert western["unavailable_bodies"] == {}
        vedic = calc.get_indian_astrology(AWARE_DT, SF)
        assert vedic["unavailable_bodies"] == {}


class TestChironAvailability:
    def test_western_reports_chiron_in_sibling_key(self, calc, forced_chiron_error):
        positions = calc.get_planetary_positions(AWARE_DT, SF)
        # The planet table stays shape-pure: no pseudo-entry.
        assert "chiron" not in positions
        western = calc.get_western_astrology(AWARE_DT, SF)
        assert western["unavailable_bodies"] == {"chiron": "ephemeris file missing or unreadable"}
        assert "chiron" not in western["positions"]

    def test_vedic_reports_chiron_in_sibling_key(self, calc, forced_chiron_error):
        vedic = calc.get_indian_astrology(AWARE_DT, SF)
        assert vedic["unavailable_bodies"] == {"chiron": "ephemeris file missing or unreadable"}
        assert "chiron" not in vedic["sidereal_positions"]

    def test_pure_tables_keep_consumers_working(self, calc, forced_chiron_error):
        western = calc.get_western_astrology(AWARE_DT, SF)
        assert "chiron" not in western["positions"]
        assert isinstance(western["aspects"], list)

        natal_aspects = calc.get_natal_aspects(AWARE_DT, SF)
        assert isinstance(natal_aspects, list)

        house_map = calc.get_planet_house_map(AWARE_DT, SF)
        assert isinstance(house_map, dict)

        transits = calc.get_transits_to_natal(AWARE_DT, SF, AWARE_DT)
        assert isinstance(transits, list)

        gochara = calc.get_vedic_gochara(AWARE_DT, SF, AWARE_DT)
        assert "chiron" not in gochara

        stars = calc.get_fixed_stars(AWARE_DT)
        assert isinstance(stars, dict)

        timeline = calc.get_year_ahead_timeline(AWARE_DT, SF, start=AWARE_DT, end=AWARE_DT + timedelta(days=3))
        assert isinstance(timeline, dict)
