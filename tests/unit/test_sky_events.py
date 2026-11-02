"""W7-2 — core.sky_events and the /astrology/sky-events route.

Contract (docs/notes/earthsky/wave7/plan.md): every Sun and Moon rise, set,
transit and Sun twilight event inside [at - 24 h, at + 48 h], sorted, whole
seconds ending in Z; ``always`` names a body that neither rises nor sets in
the window; nothing is invented for polar cases.

Route tests mount ONLY the astrology router on a bare FastAPI app — never
``backend.app.main`` (its lifespan starts the operator and streaming).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import astrology
from core.sky_events import CONVENTION, compute_sky_events

SF = (37.7749, -122.4194)
TROMSO = (69.65, 18.96)
ALERT = (82.4971, -62.3415)
UTC = timezone.utc

ALLOWED_KINDS = {
    "rise",
    "set",
    "transit",
    "civil_dawn",
    "civil_dusk",
    "nautical_dawn",
    "nautical_dusk",
    "astronomical_dawn",
    "astronomical_dusk",
}
SUN_ONLY_KINDS = ALLOWED_KINDS - {"rise", "set", "transit"}


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(astrology.router, prefix="/astrology")
    return TestClient(app)


def _events(client: TestClient, lat: float, lng: float, at: str | None = None):
    params = {"latitude": lat, "longitude": lng}
    if at is not None:
        params["datetime_str"] = at
    response = client.get("/astrology/sky-events", params=params)
    assert response.status_code == 200
    return response.json()


class TestCompute:
    def test_sun_transit_near_local_noon_san_francisco(self):
        at = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
        result = compute_sky_events(SF[0], SF[1], at)
        transits = [e for e in result["events"] if e["body"] == "sun" and e["kind"] == "transit"]
        assert len(transits) >= 1
        # local apparent noon for -122.4194 deg: about 12:00 + 8 h 09.7 min UTC,
        # plus the equation of time (within +-20 min in June). The window holds
        # ~3 transits (one per day); one of them belongs to June 21 itself.
        expected = datetime(2026, 6, 21, 12, 0, tzinfo=UTC) + timedelta(hours=-SF[1] / 15.0)
        instants = [datetime.fromisoformat(e["at"].replace("Z", "+00:00")) for e in transits]
        assert any(abs((instant - expected).total_seconds()) <= 30 * 60 for instant in instants)

    def test_events_sorted_unique_inside_window(self):
        at = datetime(2026, 11, 1, 7, 35, tzinfo=UTC)
        result = compute_sky_events(SF[0], SF[1], at)
        events = result["events"]
        assert events, "a mid-latitude 72 h window always has events"
        seen = set()
        instants = []
        for event in events:
            assert event["kind"] in ALLOWED_KINDS
            assert event["body"] in ("sun", "moon")
            if event["body"] == "moon":
                assert event["kind"] not in SUN_ONLY_KINDS
            key = (event["body"], event["kind"], event["at"])
            assert key not in seen
            seen.add(key)
            assert event["at"].endswith("Z") and "." not in event["at"]
            instants.append(datetime.fromisoformat(event["at"].replace("Z", "+00:00")))
        assert instants == sorted(instants)
        for instant in instants:
            assert at - timedelta(hours=24) <= instant <= at + timedelta(hours=48)

    def test_polar_day_no_sun_rise_or_set_and_always_up(self):
        result = compute_sky_events(TROMSO[0], TROMSO[1], datetime(2026, 6, 21, 12, 0, tzinfo=UTC))
        sun = [e for e in result["events"] if e["body"] == "sun"]
        assert all(e["kind"] not in ("rise", "set") for e in sun)
        assert result["always"]["sun"] == "up"

    def test_polar_night_no_sun_rise_or_set_and_always_down(self):
        result = compute_sky_events(TROMSO[0], TROMSO[1], datetime(2026, 12, 21, 12, 0, tzinfo=UTC))
        sun = [e for e in result["events"] if e["body"] == "sun"]
        assert all(e["kind"] not in ("rise", "set") for e in sun)
        assert result["always"]["sun"] == "down"

    def test_moon_circumpolar_at_alert_never_rises_or_sets(self):
        # 2026-01-01: the Moon's declination is ~+26.4 deg, circumpolar above
        # the horizon at 82.5 N for days (found with the same Moshier setup).
        result = compute_sky_events(ALERT[0], ALERT[1], datetime(2026, 1, 1, 0, 0, tzinfo=UTC))
        moon = [e for e in result["events"] if e["body"] == "moon"]
        assert moon, "a circumpolar Moon still transits"
        assert all(e["kind"] == "transit" for e in moon)
        assert result["always"]["moon"] == "up"
        # polar night there: the Sun neither rises nor sets either
        assert result["always"]["sun"] == "down"

    def test_moon_rises_and_sets_at_mid_latitude(self):
        at = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
        result = compute_sky_events(SF[0], SF[1], at)
        kinds = [e["kind"] for e in result["events"] if e["body"] == "moon"]
        assert "rise" in kinds and "set" in kinds
        assert result["always"]["moon"] is None

    def test_sun_twilights_surround_the_rise_and_set(self):
        at = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
        result = compute_sky_events(SF[0], SF[1], at)

        # one natural day, anchored on each civil dawn: the morning ladder
        # (astro < nautical < civil dawn) then rise, transit, set, then the
        # evening ladder (civil < nautical < astro dusk), strictly ordered.
        sun = [e for e in result["events"] if e["body"] == "sun"]
        by_kind: dict[str, list[str]] = {}
        for event in sun:
            by_kind.setdefault(event["kind"], []).append(event["at"])
        for kind in (
            "civil_dawn",
            "civil_dusk",
            "nautical_dawn",
            "nautical_dusk",
            "astronomical_dawn",
            "astronomical_dusk",
            "rise",
            "set",
            "transit",
        ):
            assert kind in by_kind, kind

        def latest_before(anchor: str, kind: str) -> str | None:
            earlier = [d for d in by_kind[kind] if d < anchor]
            return max(earlier) if earlier else None

        def earliest_after(anchor: str, kind: str) -> str | None:
            later = [d for d in by_kind[kind] if d > anchor]
            return min(later) if later else None

        complete = 0
        for anchor in by_kind["civil_dawn"]:
            chain = [
                latest_before(anchor, "astronomical_dawn"),
                latest_before(anchor, "nautical_dawn"),
                anchor,
                earliest_after(anchor, "rise"),
                earliest_after(anchor, "transit"),
                earliest_after(anchor, "set"),
                earliest_after(anchor, "civil_dusk"),
                earliest_after(anchor, "nautical_dusk"),
                earliest_after(anchor, "astronomical_dusk"),
            ]
            # window edges can truncate a chain; the pieces must still order
            pieces = [c for c in chain if c is not None]
            assert pieces == sorted(pieces), anchor
            if len(pieces) == len(chain):
                complete += 1
        assert complete >= 1, "at least one full natural day inside the window"

    def test_deterministic_same_input_same_output(self):
        at = datetime(2026, 11, 1, 7, 35, tzinfo=UTC)
        assert compute_sky_events(SF[0], SF[1], at) == compute_sky_events(SF[0], SF[1], at)

    def test_window_is_at_minus_24h_to_at_plus_48h(self):
        at = datetime(2026, 11, 2, 7, 35, tzinfo=UTC)  # the contract's example window
        result = compute_sky_events(SF[0], SF[1], at)
        assert result["window"]["from"] == "2026-11-01T07:35:00Z"
        assert result["window"]["to"] == "2026-11-04T07:35:00Z"

    def test_observer_echoed_and_convention_constant(self):
        at = datetime(2026, 11, 1, 7, 35, tzinfo=UTC)
        result = compute_sky_events(SF[0], SF[1], at)
        assert result["observer"] == {"latitude": SF[0], "longitude": SF[1]}
        assert result["convention"] == CONVENTION
        assert result["convention"].startswith("Rise and set:")

    def test_moon_transit_exists_every_day(self):
        # the Moon crosses the meridian exactly once per ~24.8 h: a 72 h
        # window at any latitude has at least two transits
        at = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
        result = compute_sky_events(SF[0], SF[1], at)
        transits = [e for e in result["events"] if e["body"] == "moon" and e["kind"] == "transit"]
        assert len(transits) >= 2


class TestRoute:
    def test_shape(self, client: TestClient):
        payload = _events(client, SF[0], SF[1], "2026-06-21T12:00:00Z")
        assert payload["status"] == "success"
        assert payload["window"] == {"from": "2026-06-20T12:00:00Z", "to": "2026-06-23T12:00:00Z"}
        assert payload["observer"] == {"latitude": SF[0], "longitude": SF[1]}
        assert payload["convention"] == CONVENTION
        assert set(payload["always"].keys()) == {"sun", "moon"}
        assert set(payload.keys()) >= {"status", "window", "observer", "timezone", "convention", "events", "always"}
        instants = [e["at"] for e in payload["events"]]
        assert instants == sorted(instants)

    def test_timezonefinder_missing_gives_null_timezone(self, client: TestClient, monkeypatch):
        import sys

        astrology._cached_timezonefinder.cache_clear()
        monkeypatch.setitem(sys.modules, "timezonefinder", None)
        payload = _events(client, SF[0], SF[1], "2026-06-21T12:00:00Z")
        assert payload["timezone"] is None
        assert payload["status"] == "success"

    def test_timezonefinder_exception_gives_null_timezone(self, client: TestClient, monkeypatch):
        import sys
        import types

        bogus = types.ModuleType("timezonefinder")

        def boom(*args, **kwargs):
            raise RuntimeError("no data")

        bogus.TimezoneFinder = boom
        astrology._cached_timezonefinder.cache_clear()
        monkeypatch.setitem(sys.modules, "timezonefinder", bogus)
        payload = _events(client, SF[0], SF[1], "2026-06-21T12:00:00Z")
        assert payload["timezone"] is None

    def test_environment_independent_timezone_value(self, client: TestClient):
        # With OR without the package installed the answer is null or a valid
        # IANA name (never an assertion about the environment itself).
        payload = _events(client, SF[0], SF[1], "2026-06-21T12:00:00Z")
        tz = payload["timezone"]
        assert tz is None or (isinstance(tz, str) and "/" in tz)

    def test_two_calls_build_one_finder(self, client: TestClient, monkeypatch):
        import sys
        import types

        built = {"n": 0}

        class FakeFinder:
            def timezone_at(self, *, lat: float, lng: float) -> str:
                return "Fake/Zone"

        def counting_factory() -> FakeFinder:
            built["n"] += 1
            return FakeFinder()

        fake = types.ModuleType("timezonefinder")
        fake.TimezoneFinder = counting_factory
        astrology._cached_timezonefinder.cache_clear()
        monkeypatch.setitem(sys.modules, "timezonefinder", fake)
        try:
            first = _events(client, SF[0], SF[1], "2026-06-21T12:00:00Z")
            second = _events(client, TROMSO[0], TROMSO[1], "2026-06-21T12:00:00Z")
            assert built["n"] == 1
            assert first["timezone"] == "Fake/Zone"
            assert second["timezone"] == "Fake/Zone"
        finally:
            # the cached FAKE must not leak into later tests (the oracle
            # feeds the returned zone straight into ZoneInfo)
            astrology._cached_timezonefinder.cache_clear()

    def test_invalid_latitude_is_422(self, client: TestClient):
        response = client.get(
            "/astrology/sky-events", params={"latitude": 91, "longitude": 0, "datetime_str": "2026-06-21T12:00:00Z"}
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "latitude must be a number between -90 and 90"

    def test_invalid_longitude_is_422(self, client: TestClient):
        response = client.get(
            "/astrology/sky-events", params={"latitude": 0, "longitude": -180.5, "datetime_str": "2026-06-21T12:00:00Z"}
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "longitude must be a number between -180 and 180"

    def test_malformed_datetime_is_422(self, client: TestClient):
        response = client.get(
            "/astrology/sky-events", params={"latitude": 0, "longitude": 0, "datetime_str": "garbage"}
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "malformed datetime_str; expected ISO-8601"

    def test_out_of_supported_range_is_422(self, client: TestClient):
        response = client.get(
            "/astrology/sky-events", params={"latitude": 0, "longitude": 0, "datetime_str": "2500-01-01T00:00:00Z"}
        )
        assert response.status_code == 422
        assert "supported range" in response.json()["detail"]

    def test_absent_datetime_is_200_now(self, client: TestClient):
        payload = _events(client, SF[0], SF[1])
        assert payload["status"] == "success"
        from_ = datetime.fromisoformat(payload["window"]["from"].replace("Z", "+00:00"))
        to = datetime.fromisoformat(payload["window"]["to"].replace("Z", "+00:00"))
        assert abs((to - from_).total_seconds() - 72 * 3600) < 1

    def test_polar_day_through_the_route(self, client: TestClient):
        payload = _events(client, TROMSO[0], TROMSO[1], "2026-06-21T12:00:00Z")
        sun = [e for e in payload["events"] if e["body"] == "sun"]
        assert all(e["kind"] not in ("rise", "set") for e in sun)
        assert payload["always"]["sun"] == "up"
        assert payload["timezone"] is None or "/" in payload["timezone"]


class TestRiseSetChainCoversTheWholeWindow:
    """W7-2b: `rise_trans` finds no next event when the gap exceeds ~24 h, so a
    `+0.01 d` chain restart silently drops later events inside the window
    (found by the W7-2o oracle at high latitudes). The chain must search the
    whole window."""

    def test_missing_moon_set_rovaniemi_march(self):
        # 66.5 N 25 E at 2026-03-20T12:00Z: oracle has 3 moon sets; the
        # broken chain returned 2. The missing set is ~2026-03-21T22:10Z,
        # between the rises at 03:39Z (03-21) and 03:09Z (03-22).
        result = compute_sky_events(66.5, 25.0, datetime.fromisoformat("2026-03-20T12:00:00+00:00"))
        sets = [
            datetime.fromisoformat(e["at"].replace("Z", "+00:00"))
            for e in result["events"]
            if e["body"] == "moon" and e["kind"] == "set"
        ]
        target = datetime.fromisoformat("2026-03-21T22:10:00+00:00")
        assert any(abs((s - target).total_seconds()) <= 180 for s in sets), sets

    def test_missing_moon_set_tromso_september(self):
        # 69.65 N 18.96 E at 2026-09-23T12:00Z: oracle 3 moon sets, the broken
        # chain returned 1. The missing set is ~2026-09-24T00:10Z.
        result = compute_sky_events(69.65, 18.96, datetime.fromisoformat("2026-09-23T12:00:00+00:00"))
        sets = [
            datetime.fromisoformat(e["at"].replace("Z", "+00:00"))
            for e in result["events"]
            if e["body"] == "moon" and e["kind"] == "set"
        ]
        target = datetime.fromisoformat("2026-09-24T00:10:00+00:00")
        assert any(abs((s - target).total_seconds()) <= 180 for s in sets), sets

    @pytest.mark.parametrize(
        ("lat", "lng", "at"),
        [
            (66.5, 25.0, "2026-03-20T12:00:00Z"),
            (69.65, 18.96, "2026-09-23T12:00:00Z"),
            (82.4971, -62.3415, "2026-01-01T00:00:00Z"),
            (82.4971, -62.3415, "2026-03-20T12:00:00Z"),
            (78.2232, 15.6469, "2026-06-21T12:00:00Z"),
            (78.2232, 15.6469, "2026-09-23T00:00:00Z"),
            (-77.85, 166.67, "2026-12-21T12:00:00Z"),
            (-77.85, 166.67, "2026-06-21T00:00:00Z"),
            (64.8378, -147.7164, "2026-06-21T12:00:00Z"),
            (64.15, -21.94, "2026-10-22T02:00:00Z"),
            (37.7749, -122.4194, "2026-11-01T07:35:00Z"),
            (-0.1807, -78.4678, "2026-02-15T09:30:00Z"),
            (-33.8688, 151.2093, "2026-05-05T06:00:00Z"),
            (1.87, -157.4, "2026-08-21T18:00:00Z"),
        ],
    )
    def test_rise_set_alternate_and_spaced(self, lat, lng, at):
        result = compute_sky_events(lat, lng, datetime.fromisoformat(at.replace("Z", "+00:00")))
        for body in ("sun", "moon"):
            horizon = [
                (e["kind"], datetime.fromisoformat(e["at"].replace("Z", "+00:00")))
                for e in result["events"]
                if e["body"] == body and e["kind"] in ("rise", "set")
            ]
            # alternation: consecutive horizon events switch kind (a repeated
            # kind means an event in between was dropped; window truncation
            # only cuts the ENDS, it never duplicates a kind)
            for (kind_a, at_a), (kind_b, at_b) in zip(horizon, horizon[1:]):
                assert kind_a != kind_b, (lat, lng, at, body, horizon)
            # spacing: two events of one kind are never < 12 h apart
            for kind in ("rise", "set"):
                stamps = [t for k, t in horizon if k == kind]
                for at_a, at_b in zip(stamps, stamps[1:]):
                    assert (at_b - at_a).total_seconds() >= 12 * 3600, (lat, lng, at, body, kind)


class TestAlwaysTopocentricFrame:
    """W7-2c: `always` must use the TOPOCENTRIC centre altitude at `at` against
    the same threshold the rise/set events use (upper edge at the apparent
    horizon), the frame `/night-sky` reports — not the geocentric altitude
    against 0."""

    def test_horizon_state_helper_injected_numbers(self):
        # the pure decision, independent of any ephemeris: a body whose
        # topocentric CENTRE is below the -(34' + semidiameter) threshold is
        # "down" even when a geocentric reading would put it above 0
        from core.sky_events import _horizon_state

        moon_horizon = 0.8255  # 34' + ~15.4' semidiameter
        assert _horizon_state(-0.5, moon_horizon) == "up"  # upper edge still above horizon
        assert _horizon_state(-0.9, moon_horizon) == "down"  # below the threshold: down
        assert _horizon_state(3.0, moon_horizon) == "up"
        assert _horizon_state(-30.0, moon_horizon) == "down"

    def test_horizon_thresholds_are_pinned(self):
        """The `always` threshold is the one the events use: the Sun 34' + 16', the Moon 34' +
        its live semidiameter (14.7' .. 16.7'). Dropping or freezing a term must fail here."""
        from core import sky_events

        assert sky_events.REFRACTION_DEG == pytest.approx(34.0 / 60.0)
        assert sky_events.SUN_HORIZON_DEG == pytest.approx(50.0 / 60.0)  # 34' + 16'
        # One lunar month sampled daily: perigee and apogee both fall inside it.
        jd0 = 2461152.5  # 2026-11-01
        samples = [sky_events._moon_horizon_deg(jd0 + day) for day in range(30)]
        floor = 34.0 / 60.0 + 14.6 / 60.0
        ceiling = 34.0 / 60.0 + 16.8 / 60.0
        assert all(floor < value < ceiling for value in samples)  # refraction alone would fail
        assert max(samples) - min(samples) > 0.02  # a frozen semidiameter would fail

    @pytest.mark.parametrize(
        ("lat", "at"),
        [
            (61.778, "2026-03-25T05:00:00Z"),
            (68.592, "2026-04-24T05:00:00Z"),
            (78.0722, "2026-05-23T05:00:00Z"),
            (88.5656, "2026-06-21T05:00:00Z"),
        ],
    )
    def test_reviewer_cases_are_null_after_the_chain_fix(self, lat, at):
        # The review (pre-W7-2b chain) saw always.moon = "up" here while
        # /night-sky showed the Moon at about -0.5 deg. That "up" came from
        # moon sets the broken chain had dropped; with the whole window
        # searched the Moon rises and sets inside it, so the verdict is null
        # and no frame question arises.
        result = compute_sky_events(lat, 18.96, datetime.fromisoformat(at.replace("Z", "+00:00")))
        kinds = [e["kind"] for e in result["events"] if e["body"] == "moon" and e["kind"] in ("rise", "set")]
        assert kinds, (lat, at)
        assert result["always"]["moon"] is None

    def test_moon_circumpolar_below_is_down_d2_case(self):
        # d2's real case (W7-2oc): no moon rise/set in the window at all and
        # the topocentric centre below the threshold -> "down" (a geocentric
        # reading agrees here; the helper test above pins the flip case).
        result = compute_sky_events(62.28, 18.96, datetime.fromisoformat("2026-03-11T05:00:00+00:00"))
        kinds = [e["kind"] for e in result["events"] if e["body"] == "moon" and e["kind"] in ("rise", "set")]
        assert kinds == []
        assert result["always"]["moon"] == "down"

    def test_public_wrapper_matches_private_topocentric(self):
        # core.celestial_sky exposes the /night-sky frame through a public
        # wrapper; it must be exactly the private Meeus-ch.40 function.
        from core.celestial_sky import _topocentric_horizontal, topocentric_horizontal

        for args in ((100.0, -16.7, 0.00257, 123.4, 37.77), (279.2, 38.8, 0.00262, 300.0, 69.65)):
            assert topocentric_horizontal(*args) == _topocentric_horizontal(*args)


class TestInclusiveWindowEdges:
    """W7-2c: an event stamped exactly at window.from or window.to is in the
    list once (the chain must search ~1 s past both edges so the rounded
    stamp, not the sub-second JD, decides)."""

    def _picks(self):
        wide = compute_sky_events(SF[0], SF[1], datetime(2026, 11, 2, 7, 35, tzinfo=UTC))
        wanted = {("sun", "rise"), ("moon", "set"), ("sun", "civil_dusk"), ("sun", "transit")}
        picks = {}
        for event in wide["events"]:
            key = (event["body"], event["kind"])
            if key in wanted and key not in picks:
                picks[key] = event["at"]
        assert set(picks) == wanted
        return picks

    @pytest.mark.parametrize("edge", ["from", "to"])
    def test_event_stamped_exactly_on_the_edge_is_present_once(self, edge):
        for (body, kind), stamp in self._picks().items():
            moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            at = moment + timedelta(hours=24) if edge == "from" else moment - timedelta(hours=48)
            result = compute_sky_events(SF[0], SF[1], at)
            expected_edge = result["window"]["from"] if edge == "from" else result["window"]["to"]
            assert expected_edge == stamp, (body, kind, edge)
            hits = [e for e in result["events"] if e["body"] == body and e["kind"] == kind and e["at"] == stamp]
            assert len(hits) == 1, (body, kind, edge, stamp, hits)

    def test_stamps_are_rounded_not_truncated(self):
        # Pick a real SF sun rise whose true (unrounded) instant has a
        # sub-second fraction ABOVE .5: its stamp must be round(jd), not
        # floor(jd) — a truncating stamp would sit one second earlier.
        import swisseph as swe

        wide = compute_sky_events(SF[0], SF[1], datetime(2026, 11, 2, 7, 35, tzinfo=UTC))
        for event in wide["events"]:
            if event["kind"] != "rise" or event["body"] != "sun":
                continue
            stamp = event["at"]
            moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            jd_start = swe.julday(
                (moment - timedelta(seconds=60)).year,
                (moment - timedelta(seconds=60)).month,
                (moment - timedelta(seconds=60)).day,
                (moment - timedelta(seconds=60)).hour
                + (moment - timedelta(seconds=60)).minute / 60
                + (moment - timedelta(seconds=60)).second / 3600,
            )
            result = swe.rise_trans(jd_start, swe.SUN, swe.CALC_RISE, [SF[1], SF[0], 0], flags=swe.FLG_MOSEPH)
            true_jd = result[1][0]
            whole_seconds = true_jd * 86400.0
            frac = whole_seconds - math.floor(whole_seconds)
            if frac > 0.5:
                rounded_jd = round(whole_seconds) / 86400.0
                year, month, day, hours = swe.revjul(rounded_jd)
                rounded = datetime(year, month, day, tzinfo=UTC) + timedelta(seconds=round(hours * 3600.0))
                assert rounded.isoformat(timespec="seconds").replace("+00:00", "Z") == stamp
                return
        pytest.fail("no sun rise with sub-second fraction > 0.5 in the sample window")
