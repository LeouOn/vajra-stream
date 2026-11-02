"""W7-2o: independent oracle tests for ``core.sky_events`` and ``GET .../sky-events``.

Written blind to the implementation.  The reference is NOT swisseph's
``rise_trans``: it scans the already-verified topocentric *geometric* altitude
that ``core.celestial_sky`` computes for the Sun and the Moon and finds each
crossing by bisection.  The conventions come from the Wave 7 contract:

* rise/set: the geometric centre at ``-(34 arcmin refraction + semi-diameter)``
  (Sun 16 arcmin; Moon from its distance, 1737.4 km radius);
* twilight: the Sun's centre at -6, -12 and -18 degrees, no refraction;
* transit: the upper meridian passage, i.e. the body's hour angle crossing zero
  upward (the lead's amendment; not the altitude maximum, which the Moon's
  changing declination can move by minutes near a high-latitude culmination).

The contract's time bar is 60 s up to +/-65 degrees latitude and 120 s up to
+/-75; that is the tolerance asserted per event.  The angle check at a returned
instant uses the local altitude rate measured by finite difference, so it does
not smuggle in a second fixed constant.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    import swisseph as swe
except ImportError:  # pragma: no cover - the astrology extras are optional
    pytest.skip("swisseph is not installed", allow_module_level=True)

from core import celestial_sky  # noqa: E402  (after the module-level skip)
from core.sky_events import compute_sky_events  # noqa: E402

# ── the contract's convention ────────────────────────────────────────────────
REFRACTION_DEG = 34.0 / 60.0
SUN_SEMI_DIAMETER_DEG = 16.0 / 60.0
MOON_RADIUS_KM = 1737.4
AU_KM = 149_597_870.7
TWILIGHT = (("civil", -6.0), ("nautical", -12.0), ("astronomical", -18.0))
CONVENTION = (
    "Rise and set: upper edge of the disc at the apparent horizon, standard "
    "refraction (34 arcmin). Twilight: centre of the Sun at -6, -12 and -18 "
    "degrees, no refraction. Transit: meridian passage (upper culmination)."
)
WINDOW_BEFORE = timedelta(hours=24)
WINDOW_AFTER = timedelta(hours=48)

# Oracle numerical settings.  The scan step only has to bracket each crossing;
# bisection then refines to a quarter second, well inside the contract's 60 s.
SCAN_STEP_S = 600.0
ROOT_TOL_S = 0.25
UTC = timezone.utc
ISO_SECONDS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
EVENT_KEYS = {"body", "kind", "at"}
TOP_LEVEL_KEYS = {
    "status",
    "window",
    "observer",
    "timezone",
    "convention",
    "events",
    "always",
    # The route adds `status`, `timezone` and the project's standard provenance
    # block; `compute_sky_events` itself returns only the contract fields.
    "provenance",
}
# The route adds `status`, `timezone` and `provenance` to the function result.
FUNCTION_KEYS = TOP_LEVEL_KEYS - {"status", "timezone", "provenance"}
SUN_KINDS = {
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
MOON_KINDS = {"rise", "set", "transit"}


def _jd(moment: datetime) -> float:
    """Julian day UT exactly as ``core.celestial_sky`` builds it."""
    hour = moment.hour + moment.minute / 60.0 + moment.second / 3600.0 + moment.microsecond / 3.6e9
    return swe.julday(moment.year, moment.month, moment.day, hour)


def _body_state(body: str, latitude: float, longitude: float, moment: datetime) -> tuple[float, float]:
    """Topocentric geometric altitude (degrees) and geocentric distance (AU).

    Uses the same Swiss Ephemeris call and the same topocentric correction as
    ``calculate_night_sky`` (geometric, sea level, no refraction), so the oracle
    checks the route's own altitude convention rather than a reinvented one.
    """
    jd = _jd(moment)
    xx, _ = swe.calc_ut(jd, swe.SUN if body == "sun" else swe.MOON, swe.FLG_EQUATORIAL)
    lst = (swe.sidtime(jd) * 15.0 + longitude) % 360.0
    altitude, _ = celestial_sky._topocentric_horizontal(xx[0], xx[1], xx[2], lst, latitude)
    return altitude, xx[2]


def _hour_angle(body: str, longitude: float, moment: datetime) -> float:
    """Local hour angle of the body's geocentric apparent RA, in (-180, 180].

    ``LST - RA``, from the same Swiss Ephemeris equatorial call and the same
    apparent sidereal time as ``calculate_night_sky``.  A transit is the upward
    crossing of zero (meridian passage).

    Parallax does not move this passage to first order: the topocentric RA
    correction (Meeus ch. 40) is proportional to ``sin(H)``, so at ``H = 0`` it
    is zero; diurnal parallax changes the body's declination/altitude at the
    meridian, not its hour angle.  Using the geocentric RA for the hour angle is
    therefore the correct meridian condition even for the Moon (the remaining
    second-order term vanishes at H=0 as well).
    """
    jd = _jd(moment)
    xx, _ = swe.calc_ut(jd, swe.SUN if body == "sun" else swe.MOON, swe.FLG_EQUATORIAL)
    lst = (swe.sidtime(jd) * 15.0 + longitude) % 360.0
    return ((lst - xx[0] + 180.0) % 360.0) - 180.0


def _moon_semi_diameter(distance_au: float) -> float:
    return math.degrees(math.asin(MOON_RADIUS_KM / (distance_au * AU_KM)))


def _threshold(body: str, kind: str | float, distance_au: float) -> float:
    """Altitude of the centre at which an event of ``kind`` happens."""
    if kind in ("rise", "set"):
        semi = SUN_SEMI_DIAMETER_DEG if body == "sun" else _moon_semi_diameter(distance_au)
        return -(REFRACTION_DEG + semi)
    return float(kind)


def _samples(
    body: str, latitude: float, longitude: float, start: datetime, end: datetime
) -> tuple[list[datetime], list[tuple[float, float]]]:
    count = int(round((end - start).total_seconds() / SCAN_STEP_S))
    moments = [start + timedelta(seconds=index * SCAN_STEP_S) for index in range(count + 1)]
    return moments, [_body_state(body, latitude, longitude, m) for m in moments]


def _bisect(fn, low: datetime, high: datetime) -> datetime:
    value_low = fn(low)
    while (high - low).total_seconds() > ROOT_TOL_S:
        middle = low + (high - low) / 2
        value_middle = fn(middle)
        if value_middle == 0.0:
            return middle
        if (value_low < 0.0) != (value_middle < 0.0):
            high = middle
        else:
            low, value_low = middle, value_middle
    return low + (high - low) / 2


def _crossings(
    body: str,
    kind: str | float,
    latitude: float,
    longitude: float,
    moments: list[datetime],
    samples: list[tuple[float, float]],
) -> list[tuple[datetime, str]]:
    """Every upward/downward crossing of the threshold, in time order."""
    found: list[tuple[datetime, str]] = []
    for index in range(len(moments) - 1):
        left = samples[index][0] - _threshold(body, kind, samples[index][1])
        right = samples[index + 1][0] - _threshold(body, kind, samples[index + 1][1])
        if left == 0.0:
            found.append((moments[index], "down" if right < 0.0 else "up"))
        elif left * right < 0.0:

            def residual(moment: datetime, body=body, kind=kind) -> float:
                altitude, distance = _body_state(body, latitude, longitude, moment)
                return altitude - _threshold(body, kind, distance)

            found.append((_bisect(residual, moments[index], moments[index + 1]), "up" if right > left else "down"))
    return found


def _transits(
    body: str,
    longitude: float,
    moments: list[datetime],
) -> list[datetime]:
    """Upward hour-angle zero crossings (upper meridian passages) in the window."""
    values = [_hour_angle(body, longitude, moment) for moment in moments]
    found: list[datetime] = []
    for index in range(len(moments) - 1):
        left, right = values[index], values[index + 1]
        if left < 0.0 <= right:
            found.append(
                _bisect(
                    lambda moment, body=body: _hour_angle(body, longitude, moment),
                    moments[index],
                    moments[index + 1],
                )
            )
    return found


def _oracle(
    latitude: float, longitude: float, at: datetime
) -> tuple[list[tuple[str, str, datetime]], dict[str, str | None]]:
    """The oracle's complete event list and ``always`` map for the window."""
    start, end = at - WINDOW_BEFORE, at + WINDOW_AFTER
    events: list[tuple[str, str, datetime]] = []
    always: dict[str, str | None] = {}
    for body in ("sun", "moon"):
        moments, samples = _samples(body, latitude, longitude, start, end)
        for moment, direction in _crossings(body, "rise", latitude, longitude, moments, samples):
            events.append((body, "rise" if direction == "up" else "set", moment))
        if body == "sun":
            for name, angle in TWILIGHT:
                for moment, direction in _crossings(body, angle, latitude, longitude, moments, samples):
                    suffix = "dawn" if direction == "up" else "dusk"
                    events.append((body, f"{name}_{suffix}", moment))
        for moment in _transits(body, longitude, moments):
            events.append((body, "transit", moment))
        has_rise_or_set = any(event_body == body and kind in ("rise", "set") for event_body, kind, _ in events)
        if has_rise_or_set:
            always[body] = None
        else:
            # Amended contract (2026-11-02): with no rise/set in the window the
            # verdict is the TOPOCENTRIC centre altitude at `at` against the SAME
            # rise/set threshold the events use (not the geocentric altitude and
            # not 0 degrees).  That keeps "up" consistent with a body whose
            # upper edge is still above the apparent horizon while its centre is
            # a little below 0.
            topocentric, distance = _body_state(body, latitude, longitude, at)
            always[body] = "up" if topocentric > _threshold(body, "rise", distance) else "down"
    events.sort(key=lambda event: event[2])
    return events, always


# ── case matrix ──────────────────────────────────────────────────────────────
CASES: list[tuple[str, float, float, datetime]] = []


def _case(label: str, latitude: float, longitude: float, *moments: str) -> None:
    for moment in moments:
        CASES.append((label, latitude, longitude, datetime.fromisoformat(moment.replace("Z", "+00:00"))))


# Eight places, three instants each (solstices/equinox, plus a DST change and the
# date-line side), then the high-latitude lunar-standstill place.
_case("equator", 0.0, 0.0, "2026-03-20T00:00:00Z", "2026-06-21T00:00:00Z", "2026-12-21T00:00:00Z")
_case(
    "san-francisco",
    37.7749,
    -122.4194,
    "2026-03-08T10:00:00Z",  # US DST starts at 10:00Z (02:00 PST -> 03:00 PDT)
    "2026-06-21T20:00:00Z",
    "2026-12-21T20:00:00Z",
)
_case("sydney", -33.8688, 151.2093, "2026-03-20T00:00:00Z", "2026-06-21T00:00:00Z", "2026-12-21T00:00:00Z")
_case("lat-60-north", 60.0, 10.0, "2026-03-20T12:00:00Z", "2026-06-21T12:00:00Z", "2026-12-21T12:00:00Z")
_case("lat-60-south", -60.0, -30.0, "2026-03-20T12:00:00Z", "2026-06-21T12:00:00Z", "2026-12-21T12:00:00Z")
_case("lat-66-5", 66.5, 25.0, "2026-03-20T12:00:00Z", "2026-06-21T12:00:00Z", "2026-12-21T12:00:00Z")
_case(
    "tromso",
    69.65,
    18.96,
    "2026-06-21T12:00:00Z",  # midnight sun
    "2026-09-23T12:00:00Z",
    "2026-12-21T12:00:00Z",  # polar night
)
_case(
    "date-line",
    -18.14,
    178.44,
    "2026-03-20T00:00:00Z",
    "2026-06-21T00:00:00Z",
    "2026-12-21T00:00:00Z",
)
_case(
    "lunar-standstill-high-latitude",
    65.0,
    -18.0,
    "2026-01-29T12:00:00Z",  # Moon declination about +28.2 (circumpolar here)
    "2026-02-12T00:00:00Z",
    "2026-02-12T12:00:00Z",  # Moon declination about -28.4 (never rises here)
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Only the astrology router, at the contract's path (no backend.app.main)."""
    from backend.app.api.v1.endpoints import astrology

    app = FastAPI()
    app.include_router(astrology.router, prefix="/api/v1/astrology")
    return TestClient(app)


def _parse(instant: str) -> datetime:
    return datetime.fromisoformat(instant.replace("Z", "+00:00")).astimezone(UTC)


def _seconds(first: datetime, second: datetime) -> float:
    return abs((first - second).total_seconds())


def _normalise(value):
    """JSON-ready copy for comparing the function's output with the route body."""
    if isinstance(value, dict):
        return {key: _normalise(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def _by_kind(events: list[tuple[str, str, datetime]]) -> dict[tuple[str, str], list[datetime]]:
    grouped: dict[tuple[str, str], list[datetime]] = {}
    for body, kind, moment in events:
        grouped.setdefault((body, kind), []).append(moment)
    return grouped


def _assert_contract_shape(
    payload: dict,
    latitude: float,
    longitude: float,
    at: datetime,
    keys: set[str] = TOP_LEVEL_KEYS,
) -> None:
    assert set(payload) == keys
    if "status" in keys:
        assert payload["status"] == "success"
    assert payload["observer"] == {"latitude": latitude, "longitude": longitude}
    assert payload["convention"] == CONVENTION
    window_from, window_to = _parse(payload["window"]["from"]), _parse(payload["window"]["to"])
    assert key_window(payload["window"])
    assert _seconds(window_from, at - WINDOW_BEFORE) <= 1.0
    assert _seconds(window_to, at + WINDOW_AFTER) <= 1.0
    assert set(payload["always"]) == {"sun", "moon"}
    for value in payload["always"].values():
        assert value in (None, "up", "down")
    for event in payload["events"]:
        assert set(event) == EVENT_KEYS
        assert event["body"] in ("sun", "moon")
        assert ISO_SECONDS.match(event["at"]), event["at"]
        assert _parse(event["at"]).microsecond == 0
        kinds = SUN_KINDS if event["body"] == "sun" else MOON_KINDS
        assert event["kind"] in kinds
        instant = _parse(event["at"])
        assert window_from <= instant <= window_to, (instant, window_from, window_to)
    moments = [_parse(event["at"]) for event in payload["events"]]
    assert moments == sorted(moments), "events are not sorted ascending"
    if "provenance" in keys:
        assert isinstance(payload["provenance"], dict)
    if "timezone" in keys:
        # The package is optional (a minimal install lacks it): `null`, or a valid IANA name.
        timezone_name = payload["timezone"]
        if timezone_name is not None:
            assert isinstance(timezone_name, str) and timezone_name
            ZoneInfo(timezone_name)  # raises for a non-IANA name


def key_window(window: dict) -> bool:
    return (
        set(window) == {"from", "to"}
        and ISO_SECONDS.match(window["from"]) is not None
        and ISO_SECONDS.match(window["to"]) is not None
    )


def _assert_event_accuracy(payload: dict, latitude: float, longitude: float, tolerance_s: float) -> None:
    for event in payload["events"]:
        body, kind = event["body"], event["kind"]
        moment = _parse(event["at"])
        if kind == "transit":
            # Meridian passage: the hour angle is zero.  The local HA rate turns
            # the contract's time bar into an angle bar, as for the altitudes.
            hour_angle = _hour_angle(body, longitude, moment)
            plus = _hour_angle(body, longitude, moment + timedelta(seconds=30))
            minus = _hour_angle(body, longitude, moment - timedelta(seconds=30))
            rate_deg_per_s = abs(plus - minus) / 60.0
            angle_bound = max(0.01, rate_deg_per_s * tolerance_s * 1.5)
            assert abs(hour_angle) <= angle_bound, (
                body,
                moment,
                hour_angle,
                angle_bound,
            )
            continue
        altitude, distance = _body_state(body, latitude, longitude, moment)
        if kind in ("rise", "set"):
            target = _threshold(body, kind, distance)
        else:
            target = dict(TWILIGHT)[kind.split("_")[0]]
        # The local altitude rate turns the contract's time bar into an angle bar.
        plus = _body_state(body, latitude, longitude, moment + timedelta(seconds=30))[0]
        minus = _body_state(body, latitude, longitude, moment - timedelta(seconds=30))[0]
        rate_deg_per_s = abs(plus - minus) / 60.0
        angle_bound = max(0.05, rate_deg_per_s * tolerance_s * 2.0)
        assert abs(altitude - target) <= angle_bound, (
            body,
            kind,
            moment,
            altitude,
            target,
            angle_bound,
        )


def _assert_no_missing_or_extra(
    payload: dict,
    oracle: list[tuple[str, str, datetime]],
    tolerance_s: float,
) -> None:
    oracle_by_kind = _by_kind(oracle)
    actual_by_kind: dict[tuple[str, str], list[datetime]] = {}
    for event in payload["events"]:
        actual_by_kind.setdefault((event["body"], event["kind"]), []).append(_parse(event["at"]))
    assert set(actual_by_kind) == set(oracle_by_kind), (
        "event kinds differ",
        sorted(actual_by_kind),
        sorted(oracle_by_kind),
    )
    for key, expected in oracle_by_kind.items():
        actual = actual_by_kind[key]
        assert len(actual) == len(expected), (key, actual, expected)
        for index, (actual_moment, oracle_moment) in enumerate(zip(actual, expected)):
            difference = _seconds(actual_moment, oracle_moment)
            assert difference <= tolerance_s, (
                key,
                index,
                actual_moment,
                oracle_moment,
                difference,
            )


def _assert_alternation(payload: dict) -> None:
    sequences: dict[tuple[str, str], list[str]] = {}
    for event in payload["events"]:
        body, kind = event["body"], event["kind"]
        if kind in ("rise", "set"):
            sequences.setdefault((body, "rise/set"), []).append(kind)
        if kind in (
            "civil_dawn",
            "civil_dusk",
            "nautical_dawn",
            "nautical_dusk",
            "astronomical_dawn",
            "astronomical_dusk",
        ):
            angle = kind.split("_")[0]
            sequences.setdefault((body, angle), []).append(kind.split("_")[1])
    for key, sequence in sequences.items():
        for previous, current in zip(sequence, sequence[1:]):
            assert previous != current, (key, sequence)


def _assert_always(payload: dict, oracle_always: dict[str, str | None]) -> None:
    assert payload["always"] == oracle_always


# ── W7-2oc: inclusive window edges ──────────────────────────────────────────
EDGE_PLACES = (
    ("san-francisco", 37.7749, -122.4194, datetime(2026, 6, 19, tzinfo=UTC)),
    ("equator", 0.0, 0.0, datetime(2026, 3, 20, tzinfo=UTC)),
    ("tromso", 69.65, 18.96, datetime(2026, 12, 21, 12, tzinfo=UTC)),
)
EDGE_REQUIRED = (
    ("sun", "rise"),
    ("sun", "set"),
    ("sun", "transit"),
    ("sun", "civil_dusk"),
    ("sun", "astronomical_dusk"),
    ("moon", "rise"),
    ("moon", "set"),
    ("moon", "transit"),
)


def _query_events(client: TestClient, latitude: float, longitude: float, at: datetime) -> dict:
    response = client.get(
        "/api/v1/astrology/sky-events",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "datetime_str": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_window_edges_are_inclusive(client: TestClient) -> None:
    """An event stamped exactly at window.from / window.to appears exactly once.

    The event stamp E comes from a wide query (the row allows g1's own stamp as
    the boundary instant); the two boundary queries then set `datetime_str` to
    E + 24 h (so E is window.from) and E - 48 h (so E is window.to).
    """
    selected: list[tuple[str, float, float, str, str, str]] = []
    covered_places: set[str] = set()
    for label, latitude, longitude, wide_at in EDGE_PLACES:
        payload = _query_events(client, latitude, longitude, wide_at)
        selected_here: list[tuple[str, float, float, str, str, str]] = []
        seen_keys: set[tuple[str, str]] = set()
        for event in payload["events"]:
            key = (event["body"], event["kind"])
            if key not in EDGE_REQUIRED or key in seen_keys:
                continue
            seen_keys.add(key)
            selected_here.append((label, latitude, longitude, event["at"], event["body"], event["kind"]))
            if len(selected_here) >= 4:
                break
        if selected_here:
            selected.extend(selected_here)
            covered_places.add(label)
    assert covered_places == {place[0] for place in EDGE_PLACES}, covered_places
    assert len(selected) >= 8, [entry[4:6] for entry in selected]

    for label, latitude, longitude, stamp, body, kind in selected:
        moment = _parse(stamp)
        for boundary, boundary_at in (
            ("from", moment + timedelta(hours=24)),
            ("to", moment - timedelta(hours=48)),
        ):
            payload = _query_events(client, latitude, longitude, boundary_at)
            hits = [
                event
                for event in payload["events"]
                if event["body"] == body and event["kind"] == kind and event["at"] == stamp
            ]
            assert len(hits) == 1, (
                label,
                boundary,
                stamp,
                payload["window"],
                [event for event in payload["events"] if event["body"] == body and event["kind"] == kind],
            )


# ── W7-2oc: always uses the TOPOCENTRIC centre against the rise/set threshold ─
# The reviewer's three "up" cases (check-m return §1) and a case found by
# scanning (find_always_case2.py in the notes): every day of 2026 near the
# Moon's circumpolar boundary (90 - |dec|) at 05:00Z, keeping the first where
# the Moon stays below the rise/set threshold for the whole 72 h (so no rise/set
# and the expected verdict is "down"), while the geocentric altitude at `at` is
# above -0.83 (the frame disagreement).
ALWAYS_CASES = (
    ("reviewer-61.778", 61.778, 18.96, "2026-03-25T05:00:00Z"),
    ("reviewer-78.0722", 78.0722, 18.96, "2026-05-23T05:00:00Z"),
    ("reviewer-88.5656", 88.5656, 18.96, "2026-06-21T05:00:00Z"),
    ("found-down-62.28", 62.28, 18.96, "2026-03-11T05:00:00Z"),
)


@pytest.mark.parametrize(
    "label,latitude,longitude,at",
    ALWAYS_CASES,
    ids=[case[0] for case in ALWAYS_CASES],
)
def test_always_topocentric_threshold(
    label: str,
    latitude: float,
    longitude: float,
    at: str,
    client: TestClient,
) -> None:
    moment = _parse(at)
    oracle, oracle_always = _oracle(latitude, longitude, moment)
    result = compute_sky_events(latitude, longitude, moment)
    _assert_contract_shape(result, latitude, longitude, moment, FUNCTION_KEYS)
    payload = _query_events(client, latitude, longitude, moment)
    route_core = {k: v for k, v in payload.items() if k not in ("status", "timezone", "provenance")}
    assert route_core == _normalise(result)
    assert result["always"] == oracle_always, (label, result["always"], oracle_always)
    assert payload["always"] == oracle_always, (label, payload["always"], oracle_always)

    moon_rise_set = [event for event in oracle if event[0] == "moon" and event[1] in ("rise", "set")]
    if label.startswith("reviewer"):
        # g1 reports "up" because its chain misses the Moon rise/set in these
        # windows; the oracle finds them, so the contract's verdict is null.
        assert moon_rise_set, label
        assert oracle_always["moon"] is None
    elif label == "found-down-62.28":
        assert not moon_rise_set, label
        topocentric, distance = _body_state("moon", latitude, longitude, moment)
        threshold = _threshold("moon", "rise", distance)
        assert topocentric < threshold
        assert oracle_always["moon"] == "down"


@pytest.mark.parametrize(
    "label,latitude,longitude,at", CASES, ids=[case[0] + "-" + case[3].isoformat() for case in CASES]
)
def test_sky_events_contract_and_oracle(
    label: str,
    latitude: float,
    longitude: float,
    at: datetime,
    client: TestClient,
) -> None:
    tolerance_s = 60.0 if abs(latitude) <= 65.0 else 120.0
    oracle, oracle_always = _oracle(latitude, longitude, at)

    result = compute_sky_events(latitude, longitude, at)
    _assert_contract_shape(result, latitude, longitude, at, FUNCTION_KEYS)
    _assert_event_accuracy(result, latitude, longitude, tolerance_s)
    _assert_no_missing_or_extra(result, oracle, tolerance_s)
    _assert_alternation(result)
    _assert_always(result, oracle_always)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "datetime_str": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    response = client.get("/api/v1/astrology/sky-events", params=params)
    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_contract_shape(payload, latitude, longitude, at)
    route_core = {k: v for k, v in payload.items() if k not in ("status", "timezone", "provenance")}
    assert route_core == _normalise(result), f"{label}: route JSON differs from compute_sky_events"
    # Determinism: same query, same bytes.
    again = client.get("/api/v1/astrology/sky-events", params=params)
    assert again.status_code == 200
    assert again.content == response.content, f"{label}: route is not deterministic"
    # (b) explicitly: no earlier same-kind crossing between the window start and
    # the first returned event that the oracle does not also have first.
    oracle_by_kind = _by_kind(oracle)
    actual_by_kind: dict[tuple[str, str], list[datetime]] = {}
    for event in payload["events"]:
        actual_by_kind.setdefault((event["body"], event["kind"]), []).append(_parse(event["at"]))
    for key, actual in actual_by_kind.items():
        expected = oracle_by_kind[key]
        earlier = [moment for moment in expected if moment < actual[0] - timedelta(seconds=tolerance_s)]
        assert not earlier, (label, key, "missed earlier crossing", earlier)
