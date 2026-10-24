"""W3-B tests for ``core.earth_sky.earth_state_series`` and GET /astrology/earth-state/series.

Phase 1 (this file): structure, validation, the RA relation and the
interpolation rule. The numbers the series is checked against come from
swisseph itself (the same primitive the function uses) only to prove the
*relation* RA = lon + GAST; independent value oracles arrive from W3-O and are
copied here as literals, never imported.

Conventions (docs/notes/earthsky/wave3/contract-w3.md, section W3-B):

* ``lon`` is the sub-point longitude, ``lat`` the declination;
* ``gast_deg`` is Greenwich *apparent* sidereal time, so for every body
  ``ra_deg == (lon + gast_deg) mod 360`` (true equator and equinox of date);
* numbers are NOT rounded to 4 decimals the way /earth-state is.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
import swisseph as swe
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import astrology
from core import earth_sky
from core.earth_sky import EphemerisUnavailable, earth_state, earth_state_series

UTC = timezone.utc
BODY_IDS = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
SWE_IDS = dict(zip(BODY_IDS, range(10)))
PLANET_ORDER = BODY_IDS[2:]

EQUINOX_MAR_2026 = datetime(2026, 3, 20, 14, 46, 0, tzinfo=UTC)
START = datetime(2026, 10, 24, 0, 0, 0, tzinfo=UTC)


def wrap180(value: float) -> float:
    return ((value + 180.0) % 360.0) - 180.0


def angdiff(a: float, b: float) -> float:
    return abs(wrap180(a - b))


def parse_z(text: str) -> datetime:
    assert text.endswith("Z"), text
    return datetime.fromisoformat(text[:-1] + "+00:00")


def iso_z(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def jd_of(moment: datetime) -> float:
    moment = moment.astimezone(UTC)
    hour = moment.hour + moment.minute / 60.0 + moment.second / 3600.0 + moment.microsecond / 3_600_000_000.0
    return swe.julday(moment.year, moment.month, moment.day, hour)


def bodies_of(sample: dict) -> dict[str, dict]:
    out = {"sun": sample["sun"], "moon": sample["moon"]}
    out.update({planet["id"]: planet for planet in sample["planets"]})
    return out


def lon_interp(a: float, b: float, fraction: float) -> float:
    """The documented client rule: step along the short way round."""
    return wrap180(a + fraction * wrap180(b - a))


def ra_interp(a: float, b: float, fraction: float) -> float:
    return (a + fraction * wrap180(b - a)) % 360.0


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(astrology.router, prefix="/astrology")
    return TestClient(app)


# W4-T2: the Moon's distance, so a client can apply the same diurnal parallax the live /night-sky applies.
# Independent literals: astropy's builtin ERFA lunar theory (moon98), in AU, 9 places
# (docs/notes/earthsky/wave4/t2/moon_distance_astropy.py). swisseph agrees with them to <= 2.4e-8 AU (3.6 km).
MOON_DISTANCE_LITERALS = (
    (datetime(2026, 3, 20, 14, 46, 0, tzinfo=UTC), 0.002465089),
    (datetime(2026, 1, 1, 13, 30, 0, tzinfo=UTC), 0.002409561),  # near a perigee
    (datetime(2026, 1, 14, 0, 0, 0, tzinfo=UTC), 0.002709888),  # near an apogee
    (datetime(2026, 10, 24, 0, 0, 0, tzinfo=UTC), 0.002531260),
    (datetime(1900, 6, 15, 12, 0, 0, tzinfo=UTC), 0.002497559),
    (datetime(2150, 2, 2, 18, 0, 0, tzinfo=UTC), 0.002526654),
)


class TestMoonDistance:
    @pytest.mark.parametrize(("instant", "au"), MOON_DISTANCE_LITERALS)
    def test_matches_an_independent_lunar_theory_in_au(self, instant, au):
        sample = earth_state_series(instant, instant, 60)["samples"][0]
        assert sample["moon_distance_au"] == pytest.approx(au, abs=1e-7)  # 15 km; the two theories differ by <= 3.6 km

    def test_is_the_distance_swisseph_returns_for_the_samples_own_julian_day(self):
        series = earth_state_series(START, START + timedelta(hours=6), 600)
        for sample in series["samples"]:
            want = swe.calc_ut(jd_of(parse_z(sample["at"])), 1, swe.FLG_EQUATORIAL)[0][2]
            assert sample["moon_distance_au"] == want

    def test_is_a_plausible_moon_distance_over_a_month_of_samples_and_at_the_range_edges(self):
        # 356,371 km (closest perigee) = 0.002382 AU; 406,720 km (farthest apogee) = 0.002719 AU
        for start in (START, datetime(1800, 1, 1, tzinfo=UTC), datetime(2200, 12, 1, tzinfo=UTC)):
            series = earth_state_series(start, start + timedelta(seconds=3600 * 287), 3600)
            distances = [sample["moon_distance_au"] for sample in series["samples"]]
            assert all(0.0023 < d < 0.0028 for d in distances), (start, min(distances), max(distances))
            assert max(distances) - min(distances) > 1e-5  # it moves: not a constant

    def test_only_the_moon_carries_a_distance(self):
        series = earth_state_series(START, START + timedelta(hours=1), 600)
        assert set(series) == {"ephemeris", "sidereal_time", "start", "end", "step_seconds", "count", "samples"}
        for sample in series["samples"]:
            assert isinstance(sample["moon_distance_au"], float)
            for body in bodies_of(sample).values():
                assert set(body) == {"id", "lat", "lon"}

    def test_the_rest_of_the_sample_is_unchanged(self):
        """Dropping the new key leaves exactly the shape (and the numbers) W3-B pinned."""
        series = earth_state_series(START, START + timedelta(hours=1), 600)
        for sample in series["samples"]:
            jd = jd_of(parse_z(sample["at"]))
            gast = swe.sidtime(jd) * 15.0
            assert sample["gast_deg"] == gast
            (pos, _) = swe.calc_ut(jd, 1, swe.FLG_EQUATORIAL)
            assert sample["moon"] == {"id": "moon", "lat": pos[1], "lon": wrap180(pos[0] - gast)}

    def test_the_payload_stays_small_at_the_cap(self):
        """288 samples: the new number must cost well under the ~213 KB the response already is."""
        end = START + timedelta(seconds=603 * 287)
        series = earth_state_series(START, end, 603)
        with_key = len(json.dumps(series))
        for sample in series["samples"]:
            del sample["moon_distance_au"]
        without = len(json.dumps(series))
        assert (with_key - without) / without < 0.06, (with_key, without)

    def test_the_route_carries_it_unchanged(self, client):
        params = {"start": "2026-03-20T14:46:00Z", "end": "2026-03-20T15:46:00Z", "step_seconds": "600"}
        body = client.get("/astrology/earth-state/series", params=params).json()
        core = earth_state_series(EQUINOX_MAR_2026, EQUINOX_MAR_2026 + timedelta(hours=1), 600)
        assert [s["moon_distance_au"] for s in body["samples"]] == [s["moon_distance_au"] for s in core["samples"]]
        assert body["samples"][0]["moon_distance_au"] == pytest.approx(0.002465089, abs=1e-7)


class TestStructure:
    def test_top_level_and_sample_key_sets(self):
        series = earth_state_series(START, START + timedelta(hours=1), 600)
        assert {"ephemeris", "sidereal_time", "start", "end", "step_seconds", "count", "samples"} <= set(series)
        assert series["ephemeris"] == "swisseph"
        assert series["sidereal_time"] == "apparent"
        assert series["step_seconds"] == 600
        assert series["count"] == 7 == len(series["samples"])
        for sample in series["samples"]:
            # W4-T2 added exactly one key, ``moon_distance_au``; every body keeps {id, lat, lon}.
            assert set(sample) == {"at", "gast_deg", "sun", "moon", "planets", "moon_distance_au"}
            assert isinstance(sample["gast_deg"], float)
            assert 0.0 <= sample["gast_deg"] < 360.0
            assert [p["id"] for p in sample["planets"]] == PLANET_ORDER
            for body in bodies_of(sample).values():
                assert set(body) == {"id", "lat", "lon"}
                assert -90.0 <= body["lat"] <= 90.0
                assert -180.0 <= body["lon"] < 180.0
        assert bodies_of(series["samples"][0]).keys() == set(BODY_IDS)

    def test_samples_are_on_the_fixed_grid_with_both_ends(self):
        end = START + timedelta(minutes=90)
        series = earth_state_series(START, end, 900)
        times = [parse_z(sample["at"]) for sample in series["samples"]]
        assert times == [START + timedelta(seconds=900 * k) for k in range(7)]
        assert parse_z(series["start"]) == START
        assert parse_z(series["end"]) == end

    def test_equal_start_and_end_is_one_sample(self):
        series = earth_state_series(EQUINOX_MAR_2026, EQUINOX_MAR_2026, 60)
        assert series["count"] == 1
        assert parse_z(series["samples"][0]["at"]) == EQUINOX_MAR_2026

    def test_naive_is_utc_and_offsets_are_converted(self):
        naive = earth_state_series(START.replace(tzinfo=None), START.replace(tzinfo=None) + timedelta(hours=1), 600)
        aware = earth_state_series(START, START + timedelta(hours=1), 600)
        shifted_start = START.astimezone(timezone(timedelta(hours=-14)))
        shifted = earth_state_series(shifted_start, shifted_start + timedelta(hours=1), 600)
        assert naive == aware == shifted

    def test_fractional_seconds_survive_in_at(self):
        start = datetime(2026, 10, 24, 0, 0, 0, 250_000, tzinfo=UTC)
        series = earth_state_series(start, start + timedelta(seconds=120), 60)
        assert [parse_z(s["at"]) for s in series["samples"]] == [start + timedelta(seconds=60 * k) for k in range(3)]

    def test_deterministic(self):
        end = START + timedelta(hours=3)
        assert earth_state_series(START, end, 300) == earth_state_series(START, end, 300)

    def test_json_round_trip_loses_nothing(self):
        series = earth_state_series(START, START + timedelta(hours=2), 600)
        assert json.loads(json.dumps(series)) == series


class TestCapAndStepValidation:
    def test_cap_is_288_both_ends_included(self):
        ok = earth_state_series(START, START + timedelta(seconds=287 * 60), 60)
        assert ok["count"] == 288 == len(ok["samples"])
        with pytest.raises(ValueError, match="288"):
            earth_state_series(START, START + timedelta(seconds=288 * 60), 60)

    def test_cap_error_names_the_count_and_the_cap(self):
        with pytest.raises(ValueError) as caught:
            earth_state_series(START, START + timedelta(seconds=300 * 60), 60)
        message = str(caught.value)
        assert "301" in message and "288" in message

    def test_the_clients_scrub_window_step_603_is_accepted_at_288_and_refused_at_289(self):
        ok = earth_state_series(START, START + timedelta(seconds=287 * 603), 603)
        assert ok["count"] == 288
        assert ok["step_seconds"] == 603
        with pytest.raises(ValueError, match="288"):
            earth_state_series(START, START + timedelta(seconds=288 * 603), 603)

    @pytest.mark.parametrize("step", [60, 61, 603, 3599, 3600])
    def test_step_bounds_inclusive(self, step):
        series = earth_state_series(START, START + timedelta(seconds=2 * step), step)
        assert series["count"] == 3

    @pytest.mark.parametrize("step", [59, 0, -60, 3601, 7200])
    def test_step_out_of_bounds_is_refused(self, step):
        with pytest.raises(ValueError, match="step_seconds"):
            earth_state_series(START, START + timedelta(hours=5), step)

    @pytest.mark.parametrize("step", [600.0, 600.5, "600", None, True])
    def test_step_must_be_an_integer_number_of_seconds(self, step):
        with pytest.raises(ValueError, match="step_seconds"):
            earth_state_series(START, START + timedelta(hours=5), step)

    def test_reversed_times_are_refused(self):
        with pytest.raises(ValueError, match="before"):
            earth_state_series(START, START - timedelta(seconds=60), 60)

    def test_end_must_land_on_the_grid(self):
        with pytest.raises(ValueError, match="whole number of steps"):
            earth_state_series(START, START + timedelta(seconds=601), 600)
        with pytest.raises(ValueError, match="whole number of steps"):
            earth_state_series(START, START + timedelta(seconds=60, microseconds=1), 60)

    def test_supported_range_edges(self):
        first = datetime(1800, 1, 1, 0, 0, 0, tzinfo=UTC)
        last = datetime(2200, 12, 31, 23, 59, 59, tzinfo=UTC)
        assert earth_state_series(first, first + timedelta(seconds=60), 60)["count"] == 2
        assert earth_state_series(last - timedelta(seconds=60), last, 60)["count"] == 2
        assert earth_state_series(last, last, 60)["count"] == 1

    @pytest.mark.parametrize(
        "start,end",
        [
            (datetime(1799, 12, 31, 23, 59, 59, tzinfo=UTC), datetime(1800, 1, 1, 0, 0, 59, tzinfo=UTC)),
            (datetime(2200, 12, 31, 23, 59, 0, tzinfo=UTC), datetime(2201, 1, 1, 0, 0, 0, tzinfo=UTC)),
            (datetime(1700, 1, 1, tzinfo=UTC), datetime(1700, 1, 1, tzinfo=UTC)),
        ],
    )
    def test_times_outside_the_supported_range_are_refused(self, start, end):
        with pytest.raises(ValueError, match="1800-01-01..2200-12-31"):
            earth_state_series(start, end, 60)

    def test_validation_comes_before_the_ephemeris_check(self, monkeypatch):
        monkeypatch.setattr(earth_sky, "swe", None)
        with pytest.raises(ValueError, match="288"):
            earth_state_series(START, START + timedelta(hours=10), 60)

    def test_without_swisseph_a_valid_request_raises_unavailable(self, monkeypatch):
        monkeypatch.setattr(earth_sky, "swe", None)
        with pytest.raises(EphemerisUnavailable):
            earth_state_series(START, START + timedelta(hours=1), 600)


class TestRightAscensionRelation:
    """RA = (lon + gast_deg) mod 360 and dec = lat, to 1e-9 degrees."""

    INSTANTS = [
        datetime(1800, 1, 1, 0, 0, 0, tzinfo=UTC),
        datetime(1900, 6, 15, 7, 30, 0, tzinfo=UTC),
        EQUINOX_MAR_2026,
        datetime(2026, 10, 24, 23, 44, 0, tzinfo=UTC),
        datetime(2200, 12, 31, 23, 59, 59, tzinfo=UTC),
    ]

    @pytest.mark.parametrize("instant", INSTANTS, ids=lambda m: m.isoformat())
    def test_reconstructed_ra_and_dec_match_the_ephemeris_to_1e9(self, instant):
        start = instant if instant.year < 2200 else instant - timedelta(seconds=120)
        series = earth_state_series(start, start + timedelta(seconds=120), 60)
        for sample in series["samples"]:
            jd = jd_of(parse_z(sample["at"]))
            for body_id, body in bodies_of(sample).items():
                (pos, _flags) = swe.calc_ut(jd, SWE_IDS[body_id], swe.FLG_EQUATORIAL)
                ra_rebuilt = (body["lon"] + sample["gast_deg"]) % 360.0
                assert angdiff(ra_rebuilt, pos[0]) < 1e-9, (sample["at"], body_id)
                assert abs(body["lat"] - pos[1]) < 1e-9, (sample["at"], body_id)

    def test_gast_is_apparent_sidereal_time(self):
        series = earth_state_series(START, START + timedelta(hours=1), 600)
        for sample in series["samples"]:
            jd = jd_of(parse_z(sample["at"]))
            assert angdiff(sample["gast_deg"], swe.sidtime(jd) * 15.0) < 1e-9

    def test_hour_angle_needs_no_sidereal_time(self):
        """H = observer east-longitude - sub-point longitude, same as LST - RA."""
        sample = earth_state_series(EQUINOX_MAR_2026, EQUINOX_MAR_2026, 60)["samples"][0]
        observer_lon = 151.21
        for body in bodies_of(sample).values():
            ra = (body["lon"] + sample["gast_deg"]) % 360.0
            via_sidereal = wrap180(sample["gast_deg"] + observer_lon - ra)
            via_subpoint = wrap180(observer_lon - body["lon"])
            assert angdiff(via_sidereal, via_subpoint) < 1e-9

    def test_agrees_with_earth_state_to_its_rounding(self):
        series = earth_state_series(START, START + timedelta(hours=2), 1200)
        for sample in series["samples"]:
            expected = earth_state(parse_z(sample["at"]))
            assert angdiff(sample["gast_deg"], expected["gast_deg"]) <= 5.1e-5
            exp_bodies = bodies_of(expected)
            for body_id, body in bodies_of(sample).items():
                assert abs(body["lat"] - exp_bodies[body_id]["lat"]) <= 5.1e-5, body_id
                assert angdiff(body["lon"], exp_bodies[body_id]["lon"]) <= 5.1e-5, body_id

    @pytest.mark.parametrize("instant", [datetime(1800, 1, 1, tzinfo=UTC), datetime(2200, 12, 31, 23, 58, tzinfo=UTC)])
    def test_agrees_with_earth_state_at_the_range_edges(self, instant):
        """earth_state carries the Wave 1 oracle literals, so this ties the series to them at 1800 and 2200."""
        series = earth_state_series(instant, instant + timedelta(seconds=60), 60)
        for sample in series["samples"]:
            expected = earth_state(parse_z(sample["at"]))
            assert angdiff(sample["gast_deg"], expected["gast_deg"]) <= 5.1e-5
            exp_bodies = bodies_of(expected)
            for body_id, body in bodies_of(sample).items():
                assert abs(body["lat"] - exp_bodies[body_id]["lat"]) <= 5.1e-5, (sample["at"], body_id)
                assert angdiff(body["lon"], exp_bodies[body_id]["lon"]) <= 5.1e-5, (sample["at"], body_id)

    def test_microseconds_enter_the_julian_day(self):
        """W3-O harness note: dropping microseconds from swe.julday costs ~0.003 degrees per 0.75 s."""
        instant = datetime(2026, 10, 24, 0, 0, 0, 750_000, tzinfo=UTC)
        sample = earth_state_series(instant, instant, 60)["samples"][0]
        jd = jd_of(instant)
        assert angdiff(sample["gast_deg"], swe.sidtime(jd) * 15.0) < 1e-9
        whole = earth_state_series(instant.replace(microsecond=0), instant.replace(microsecond=0), 60)["samples"][0]
        assert angdiff(sample["gast_deg"], whole["gast_deg"]) > 0.002  # 0.75 s of Earth rotation is 0.0031 degrees

    def test_numbers_are_not_rounded_to_four_decimals(self):
        series = earth_state_series(START, START + timedelta(hours=2), 600)
        values = [s["gast_deg"] for s in series["samples"]]
        values += [b["lon"] for s in series["samples"] for b in bodies_of(s).values()]
        assert any(round(v, 4) != v for v in values)


class TestInterpolationRule:
    """The client rule is the short way round: d = wrap180(b - a); a + f * d."""

    def _direct(self, moment: datetime) -> dict:
        return earth_state_series(moment, moment, 60)["samples"][0]

    def test_every_body_crosses_the_longitude_seam_within_26_hours_and_the_rule_survives_it(self):
        step = 600
        # 26 h: the Moon's sub-point needs about 24 h 50 min to come round to the seam again
        series = earth_state_series(START, START + timedelta(seconds=step * 156), step)
        samples = series["samples"]
        for body_id in BODY_IDS:
            crossings = [
                i
                for i in range(len(samples) - 1)
                if abs(bodies_of(samples[i])[body_id]["lon"] - bodies_of(samples[i + 1])[body_id]["lon"]) > 180.0
            ]
            assert crossings, body_id
            for i in crossings:
                a = bodies_of(samples[i])[body_id]["lon"]
                b = bodies_of(samples[i + 1])[body_id]["lon"]
                middle = parse_z(samples[i]["at"]) + timedelta(seconds=step / 2)
                truth = bodies_of(self._direct(middle))[body_id]["lon"]
                assert angdiff(lon_interp(a, b, 0.5), truth) < 1e-4, body_id
                # negative control: averaging the raw numbers is ~180 degrees out
                assert angdiff((a + b) / 2.0, truth) > 170.0, body_id

    def test_ra_wraps_at_the_equinox_and_the_rule_survives_it(self):
        step = 603
        start = EQUINOX_MAR_2026 - timedelta(seconds=step * 6)
        series = earth_state_series(start, start + timedelta(seconds=step * 12), step)
        samples = series["samples"]
        ras = [(bodies_of(s)["sun"]["lon"] + s["gast_deg"]) % 360.0 for s in samples]
        crossing = [i for i in range(len(ras) - 1) if abs(ras[i] - ras[i + 1]) > 180.0]
        assert len(crossing) == 1
        i = crossing[0]
        middle = parse_z(samples[i]["at"]) + timedelta(seconds=step / 2)
        mid_sample = self._direct(middle)
        truth = (bodies_of(mid_sample)["sun"]["lon"] + mid_sample["gast_deg"]) % 360.0
        assert angdiff(ra_interp(ras[i], ras[i + 1], 0.5), truth) < 1e-4
        assert angdiff((ras[i] + ras[i + 1]) / 2.0, truth) > 170.0

    @pytest.mark.parametrize("step", [60, 603, 3600])
    def test_midpoint_error_budget_by_step(self, step):
        """Linear interpolation of lon, lat and gast between two samples.

        Worst midpoint error in degrees over all ten bodies, measured on 4
        windows x 60 steps (2026-10-24, 2026-03-20, 1800-01-01, 2200-06-01):
        1.2e-7 at 60 s, 7.2e-6 at 603 s, 2.8e-4 at 3600 s, always the Moon.
        The bounds are about 3x those, so a regression to a cruder rule fails.
        """
        bounds = {60: 4e-7, 603: 2.5e-5, 3600: 1e-3}
        series = earth_state_series(START, START + timedelta(seconds=step * 24), step)
        samples = series["samples"]
        worst = 0.0
        for i in range(len(samples) - 1):
            middle = parse_z(samples[i]["at"]) + timedelta(seconds=step / 2)
            truth = self._direct(middle)
            truth_bodies = bodies_of(truth)
            for body_id in BODY_IDS:
                a = bodies_of(samples[i])[body_id]
                b = bodies_of(samples[i + 1])[body_id]
                worst = max(
                    worst,
                    angdiff(lon_interp(a["lon"], b["lon"], 0.5), truth_bodies[body_id]["lon"]),
                    abs((a["lat"] + b["lat"]) / 2.0 - truth_bodies[body_id]["lat"]),
                )
            gast_mid = (samples[i]["gast_deg"] + wrap180(samples[i + 1]["gast_deg"] - samples[i]["gast_deg"]) / 2) % 360
            worst = max(worst, angdiff(gast_mid, truth["gast_deg"]))
        assert worst < bounds[step], (step, worst)


class TestSeriesRoute:
    URL = "/astrology/earth-state/series"

    def _get(self, client, start=START, end=None, step=600, **extra):
        params = {"start": iso_z(start), "end": iso_z(end if end is not None else start + timedelta(hours=1))}
        if step is not None:
            params["step_seconds"] = step
        params.update(extra)
        return client.get(self.URL, params=params)

    def test_ok_shape_and_provenance(self, client):
        response = self._get(client)
        assert response.status_code == 200
        body = response.json()
        assert {"ephemeris", "sidereal_time", "start", "end", "step_seconds", "count", "samples", "provenance"} <= set(
            body
        )
        assert body["count"] == 7 == len(body["samples"])
        assert set(body["provenance"]) >= {"start", "end", "samples"}
        assert set(body["provenance"].values()) == {"computed"}

    def test_default_step_is_600(self, client):
        response = self._get(client, step=None)
        assert response.status_code == 200
        assert response.json()["step_seconds"] == 600

    def test_route_matches_the_core_function(self, client):
        body = self._get(client, step=300).json()
        core = earth_state_series(START, START + timedelta(hours=1), 300)
        assert body["samples"] == core["samples"]

    def test_cap_288_ok_289_is_422_naming_the_cap(self, client):
        ok = self._get(client, end=START + timedelta(seconds=287 * 603), step=603)
        assert ok.status_code == 200
        assert ok.json()["count"] == 288
        too_many = self._get(client, end=START + timedelta(seconds=288 * 603), step=603)
        assert too_many.status_code == 422
        assert "288" in too_many.json()["detail"]

    def test_every_422_detail_is_a_plain_string(self, client):
        good = {"start": iso_z(START), "end": iso_z(START + timedelta(hours=1)), "step_seconds": "600"}
        bad_cases = [
            {"start": None},
            {"end": None},
            {"start": "not-a-date"},
            {"end": "2026-13-45T99:99:99Z"},
            {"start": ""},
            {"end": "   "},
            {"step_seconds": "59"},
            {"step_seconds": "3601"},
            {"step_seconds": "abc"},
            {"step_seconds": "600.5"},
            {"step_seconds": "1e3"},
            {"step_seconds": "nan"},
            {"step_seconds": ""},
            {"end": iso_z(START - timedelta(seconds=60))},
            {"end": iso_z(START + timedelta(seconds=601))},
            {"start": "1799-12-31T23:59:00Z", "end": "1799-12-31T23:59:00Z"},
            {"start": "2201-01-01T00:00:00Z", "end": "2201-01-01T00:00:00Z"},
        ]
        for override in bad_cases:
            params = {**good, **override}
            params = {k: v for k, v in params.items() if v is not None}
            response = client.get(self.URL, params=params)
            assert response.status_code == 422, override
            assert isinstance(response.json()["detail"], str), override

    @pytest.mark.parametrize("extreme", ["0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00"])
    def test_extreme_offsets_are_422_not_an_overflow_500(self, client, extreme):
        response = client.get(self.URL, params={"start": extreme, "end": extreme})
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], str)

    def test_z_naive_and_offset_spellings_agree(self, client):
        z = client.get(self.URL, params={"start": "2026-10-24T00:00:00Z", "end": "2026-10-24T01:00:00Z"})
        naive = client.get(self.URL, params={"start": "2026-10-24T00:00:00", "end": "2026-10-24T01:00:00"})
        offset = client.get(self.URL, params={"start": "2026-10-23T10:00:00-14:00", "end": "2026-10-23T11:00:00-14:00"})
        assert z.status_code == naive.status_code == offset.status_code == 200
        assert z.json()["samples"] == naive.json()["samples"] == offset.json()["samples"]

    def test_unavailable_ephemeris_is_503(self, client, monkeypatch):
        monkeypatch.setattr(earth_sky, "swe", None)
        response = self._get(client)
        assert response.status_code == 503
        assert response.json() == {"detail": "ephemeris unavailable"}

    def test_input_errors_win_over_an_unavailable_ephemeris(self, client, monkeypatch):
        monkeypatch.setattr(earth_sky, "swe", None)
        assert self._get(client, step=59).status_code == 422

    def test_earth_state_itself_is_untouched(self, client):
        response = client.get("/astrology/earth-state", params={"datetime_str": "2026-03-20T14:46:00Z"})
        assert response.status_code == 200
        assert set(response.json()) >= {"at", "gast_deg", "sun", "moon", "planets"}


# fmt: off
# Copied from docs/notes/earthsky/wave3/oracle/oracle_series.json (dev-g1, W3-O): swisseph 2.10.03,
# default ephemeris, 6 decimals, step 600 s. Rule: for each of the 12 starts the first, the middle and the
# last stored sample, plus on moon-seam-day every stored sample with the Moon within 5 degrees of lon +-180.
# Row: (start label, start, index k so that at = start + 600 s * k, gast_deg, (lat, lon) x sun, moon, mercury .. pluto).
ORACLE_SERIES_ROWS = (
    ("equinox-2026", "2026-03-20T14:46:00Z", 0, 39.64937, (9.1e-05, -39.649388, 11.238252, -22.036433, -7.425063, -59.916933, 6.096784, -23.101568, -7.21454, -53.795934, 22.929005, 66.92579, -0.308841, -35.018775, 19.612297, 16.450145, -0.493049, -37.502941, -22.80879, -91.270007)),
    ("equinox-2026", "2026-03-20T14:46:00Z", 144, 40.634995, (0.395357, -39.723295, 17.253514, -9.51171, -7.63958, -60.783495, 6.598734, -22.948495, -6.908903, -54.052137, 22.926128, 65.974931, -0.259551, -35.889942, 19.62069, 15.502452, -0.478091, -38.453739, -22.806482, -92.233335)),
    ("equinox-2026", "2026-03-20T14:46:00Z", 287, 39.113792, (0.787539, -37.297153, 22.296264, 6.299083, -7.812526, -59.05706, 7.094782, -20.294825, -6.604468, -51.807716, 22.922891, 67.534043, -0.210627, -34.254975, 19.629163, 17.062033, -0.463251, -36.897974, -22.804294, -90.690361)),
    ("solstice-2026", "2026-06-21T08:24:00Z", 0, 35.553508, (23.437941, 54.446121, 0.965623, 137.534404, 21.303831, 79.905573, 19.877699, 96.595409, 18.530708, 16.840066, 20.956867, 84.759852, 3.248244, -22.035961, 20.642476, 25.650374, 0.48137, -31.025068, -23.072761, -87.03652)),
    ("solstice-2026", "2026-06-21T08:24:00Z", 144, 36.539139, (23.434463, 54.500607, -5.046951, 147.914588, 20.979566, 79.493962, 19.553426, 96.783058, 18.715118, 16.589768, 20.91579, 83.993105, 3.266292, -22.967499, 20.65278, 24.720744, 0.483913, -32.00259, -23.079773, -88.040676)),
    ("solstice-2026", "2026-06-21T08:24:00Z", 287, 35.017929, (23.424194, 57.0544, -10.673169, 160.623332, 20.659808, 81.50921, 19.223566, 99.462644, 18.895156, 18.841708, 20.874593, 85.732288, 3.283623, -21.3939, 20.662926, 26.297229, 0.486226, -30.473813, -23.086769, -86.538155)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 0, 279.065133, (23.118502, -179.050782, -25.20704, 13.349749, 18.449771, -161.360449, 16.439063, -135.881351, 20.17794, 140.444396, 20.543784, -156.616123, 3.397218, 94.917443, 20.738289, 142.664024, 0.497055, 85.52117, -23.141717, 29.261749)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 78, 114.599039, (23.081821, -14.024752, -23.626045, -175.252277, 18.321737, 3.012115, 16.227267, 29.185088, 20.261493, -54.688897, 20.519525, 7.971203, 3.403886, -100.594226, 20.743423, -52.841498, 0.497346, -110.010853, -23.145667, -166.283528)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 79, 117.105884, (23.081338, -16.524421, -23.603698, -177.671187, 18.320128, 0.503924, 16.22454, 26.685926, 20.262558, -57.190605, 20.519214, 5.465913, 3.40397, -103.100788, 20.743489, -55.34798, 0.497349, -112.517675, -23.145717, -168.790519)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 80, 119.612729, (23.080854, -19.024089, -23.581301, 179.90988, 18.318519, -2.00427, 16.221813, 24.186765, 20.263623, -59.692313, 20.518902, 2.960623, 3.404055, -105.607351, 20.743554, -57.854462, 0.497353, -115.024497, -23.145768, -171.297511)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 81, 122.119574, (23.080371, -21.523757, -23.558853, 177.490922, 18.316912, -4.512468, 16.219085, 21.687603, 20.264687, -62.194021, 20.51859, 0.455333, 3.404139, -108.113914, 20.74362, -60.360944, 0.497356, -117.531319, -23.145819, -173.804502)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 82, 124.626419, (23.079887, -24.023426, -23.536353, 175.071939, 18.315305, -7.020669, 16.216357, 19.18844, 20.265752, -64.695729, 20.518278, -2.049956, 3.404223, -110.620476, 20.743685, -62.867426, 0.497359, -120.03814, -23.14587, -176.311493)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 144, 280.050804, (23.049244, -179.002975, -22.044268, 25.046778, 18.217347, -162.536313, 16.046656, -135.760266, 20.331437, 140.198401, 20.498913, -157.377887, 3.409385, 93.972495, 20.747745, 141.730651, 0.497542, 84.538859, -23.149015, 28.25503)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 227, 128.11893, (23.006278, -26.475923, -19.765383, -175.943012, 18.091424, -10.748386, 15.817734, 16.806416, 20.418411, -67.443224, 20.472879, -5.316774, 3.416111, -114.072818, 20.753152, -66.307535, 0.497723, -123.52756, -23.153232, -179.825337)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 228, 130.625775, (23.005747, -28.9756, -19.73609, -178.365606, 18.089944, -13.257116, 15.814964, 14.307206, 20.419453, -69.94493, 20.472564, -7.822061, 3.416191, -116.579391, 20.753217, -68.81402, 0.497725, -126.034386, -23.153282, 177.66767)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 229, 133.13262, (23.005216, -31.475276, -19.706755, 179.211777, 18.088465, -15.765848, 15.812194, 11.807995, 20.420494, -72.446636, 20.47225, -10.327348, 3.416271, -119.085964, 20.753282, -71.320505, 0.497727, -128.541211, -23.153333, 175.160678)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 230, 135.639464, (23.004684, -33.974953, -19.677379, 176.789136, 18.086987, -18.274584, 15.809423, 9.308784, 20.421535, -74.948341, 20.471935, -12.832635, 3.416351, -121.592537, 20.753347, -73.82699, 0.497728, -131.048036, -23.153384, 172.653685)),
    ("moon-seam-day", "2026-07-01T00:00:00Z", 287, 278.529621, (22.973835, -176.456607, -17.935834, 38.659784, 18.004246, -161.27836, 15.651027, -133.14679, 20.480599, 142.454467, 20.453981, -155.63396, 3.420843, 95.532681, 20.75704, 143.303322, 0.497809, 86.062877, -23.156284, 29.755074)),
    ("mercury-retro", "2026-11-10T00:00:00Z", 0, 49.170482, (-17.081152, 175.966207, -24.008082, -177.189291, -12.372697, 165.279117, -11.445628, 151.299321, 15.540679, 96.79391, 13.760411, 98.669596, 1.029664, -40.068049, 20.860738, 13.214599, -0.534299, -46.856376, -23.584716, -102.582513)),
    ("mercury-retro", "2026-11-10T00:00:00Z", 144, 50.156147, (-17.36067, 175.991441, -26.430748, -165.008275, -11.945473, 163.785523, -11.164584, 150.271154, 15.406776, 96.27554, 13.7308, 97.780204, 1.012375, -41.101782, 20.853499, 12.187044, -0.540646, -47.85792, -23.581237, -103.555664)),
    ("mercury-retro", "2026-11-10T00:00:00Z", 276, 21.05968, (-17.612529, -153.982337, -27.550122, -123.620164, -11.635471, -167.42858, -10.923184, 179.361643, 15.284605, 125.796505, 13.704429, 126.962668, 0.997069, -12.048251, 20.846816, 41.244868, -0.546297, -18.775644, -23.577961, -74.447291)),
    ("range-start-1950", "1950-01-01T00:00:00Z", 0, 100.074889, (-23.070745, -179.190125, 24.152475, -41.623221, -21.471271, -158.193384, -15.151219, -140.840023, 1.425609, 82.953053, -19.219106, -151.026413, 6.02797, 71.008585, 23.689732, -7.145126, -5.311897, 96.452131, 23.293343, 42.890947)),
    ("range-start-1950", "1950-01-01T00:00:00Z", 144, 101.060568, (-22.990312, -179.07194, 26.819498, -29.295267, -21.075437, -158.144356, -14.862273, -141.553644, 1.297099, 82.309328, -19.163134, -151.780714, 6.03381, 70.020771, 23.69071, -8.177214, -5.31476, 95.476013, 23.302517, 41.888177)),
    ("range-start-1950", "1950-01-01T00:00:00Z", 276, 71.964114, (-22.909884, -148.964831, 28.142875, 12.673074, -20.710857, -128.197245, -14.601358, -112.238801, 1.181352, 111.714838, -19.111427, -122.471605, 6.039784, 99.113785, 23.691591, 20.876852, -5.317199, 124.580782, 23.310967, 70.968678)),
    ("range-end-2049", "2049-12-31T00:00:00Z", 0, 99.863937, (-23.074502, -179.279204, 5.862345, -96.947512, -20.378924, 171.298866, -23.62335, -178.950323, -16.181367, 124.981588, 20.194466, 24.302209, -20.860346, -160.296093, 4.392108, 71.93627, 16.963429, -48.166724, -20.486817, -115.65482)),
    ("range-end-2049", "2049-12-31T00:00:00Z", 144, 100.849044, (-22.996242, -179.160133, 10.450672, -84.926794, -20.295516, 169.214223, -23.559093, -178.563538, -16.366608, 124.629707, 20.22334, 23.195803, -20.838731, -161.159828, 4.3949, 70.946408, 16.959912, -49.169668, -20.477008, -116.625504)),
    ("range-end-2049", "2049-12-31T00:00:00Z", 276, 71.752551, (-22.917795, -149.052693, 14.112932, -43.864661, -20.247326, -162.551332, -23.489509, -148.210879, -16.534732, 154.307625, 20.250045, 52.179497, -20.818781, -131.951772, 4.397774, 100.037796, 16.956795, -20.089114, -20.467937, -87.515475)),
    ("reference-instant", "2026-10-22T02:00:00Z", 0, 60.525374, (-11.007857, 146.134973, -8.166358, -82.026291, -20.950958, 166.816606, -18.577703, 146.828615, 18.117215, 75.840007, 14.468023, 85.046805, 1.457574, -50.312277, 20.982867, 2.575479, -0.383032, -57.844113, -23.630336, -114.080202)),
    ("reference-instant", "2026-10-22T02:00:00Z", 144, 61.510992, (-11.359919, 146.097661, -2.181555, -71.398584, -20.959269, 166.065066, -18.223524, 145.306787, 17.982268, 75.395258, 14.424413, 84.200657, 1.430862, -51.364405, 20.977256, 1.556549, -0.392325, -58.851867, -23.628928, -115.062792)),
    ("reference-instant", "2026-10-22T02:00:00Z", 276, 32.414472, (-11.680127, 176.065926, 3.54965, -31.429894, -20.920948, -164.727852, -17.885597, 173.912688, 17.858176, 104.984461, 14.384978, 113.423232, 1.40671, -22.328255, 20.972013, 30.622012, -0.400736, -29.775418, -23.627533, -85.963058)),
    ("perihelion-season", "2026-01-02T00:00:00Z", 0, 101.647926, (-22.932671, -179.050383, 28.143502, -20.973932, -24.116873, 168.549269, -23.56618, 179.780798, -23.650874, -176.934565, 22.001963, 11.337362, -3.569895, -104.213947, 19.503852, -45.938898, -1.412945, -101.558989, -23.213531, -155.679884)),
    ("perihelion-season", "2026-01-02T00:00:00Z", 144, 102.633632, (-22.840501, -178.934701, 27.810661, -4.984545, -24.211801, 169.245865, -23.497787, -179.834045, -23.577316, -177.086715, 22.024772, 10.211606, -3.542833, -105.145239, 19.498204, -46.951986, -1.407083, -102.532759, -23.20711, -156.633328)),
    ("perihelion-season", "2026-01-02T00:00:00Z", 276, 73.53719, (-22.749382, -148.830021, 25.740868, 39.186183, -24.280347, -160.107993, -23.424449, -149.482414, -23.506005, -147.226396, 22.045668, 39.178938, -3.517523, -75.997692, 19.493165, -17.880029, -1.401524, -73.424937, -23.201219, -127.507167)),
    ("aphelion-season", "2026-07-04T00:00:00Z", 0, 282.022116, (22.890651, -178.910789, -12.975595, 46.972765, 17.807513, -165.110135, 15.244008, -135.538573, 20.628503, 139.707456, 20.408044, -158.900218, 3.431822, 92.07826, 20.766362, 139.862567, 0.497858, 82.572742, -23.163675, 26.240909)),
    ("aphelion-season", "2026-07-04T00:00:00Z", 144, 283.007756, (22.801372, -178.866555, -7.452198, 57.410737, 17.632624, -166.500625, 14.834153, -135.437882, 20.772036, 139.46246, 20.362046, -159.660824, 3.442085, 91.128954, 20.775516, 138.927836, 0.497686, 81.588936, -23.171031, 25.233522)),
    ("aphelion-season", "2026-07-04T00:00:00Z", 276, 253.911253, (22.71372, -148.827177, -2.032407, 96.90522, 17.491155, -137.830267, 14.453674, -105.351474, 20.900658, 169.238128, 20.319553, -130.35774, 3.450929, 120.257462, 20.783813, 168.070586, 0.497337, 110.686675, -23.177783, 54.309899)),
    ("j2000-noon", "2000-01-01T12:00:00Z", 0, 280.457072, (-23.032425, 0.821314, -10.900574, -58.004858, -24.418898, -8.382429, -18.448921, -40.564293, -13.182476, 50.059748, 8.594257, 103.410724, 12.614787, 118.308308, -17.020316, 37.017794, -19.213249, 24.97574, -11.394315, -29.037965)),
    ("j2000-noon", "2000-01-01T12:00:00Z", 144, 281.442726, (-22.949298, 0.939423, -14.338665, -47.297575, -24.483063, -7.654059, -18.713872, -40.305276, -12.901208, 49.816095, 8.614507, 102.463152, 12.613407, 117.302623, -17.005253, 36.082615, -19.205234, 24.026903, -11.397251, -29.988619)),
    ("j2000-noon", "2000-01-01T12:00:00Z", 276, 252.346248, (-22.8664, 31.046515, -16.963917, -7.263516, -24.522527, 23.019991, -18.949979, -10.063492, -12.641665, 79.591335, 8.634128, 131.597329, 12.612663, 146.382304, -16.99133, 65.225737, -19.197838, 53.157314, -11.399829, -0.860272)),
    ("arbitrary-a", "2026-05-05T06:30:00Z", 0, 320.649521, (16.272182, 81.673049, -28.085777, -57.684638, 11.617692, 71.779263, 23.487155, 111.260895, 6.890026, 57.805776, 22.40604, 150.545842, 1.805778, 49.049054, 20.097595, 97.740814, 0.135096, 42.987271, -22.823375, -11.703339)),
    ("arbitrary-a", "2026-05-05T06:30:00Z", 144, 321.635193, (16.554829, 81.653111, -27.699008, -45.289746, 12.419753, 72.675649, 23.672431, 111.576839, 7.184148, 57.529383, 22.385221, 149.719366, 1.846497, 48.165012, 20.109602, 96.814276, 0.146499, 42.029457, -22.826461, -12.687687)),
    ("arbitrary-a", "2026-05-05T06:30:00Z", 276, 292.538725, (16.809913, 111.636943, -26.221253, -4.089056, 13.155305, 103.529578, 23.832584, 141.868799, 7.452536, 87.276268, 22.365771, 178.963481, 1.883521, 77.354069, 20.120627, 125.965129, 0.156825, 71.151189, -22.829393, 16.409567)),
    ("arbitrary-b", "2026-08-21T18:00:00Z", 0, 240.072671, (11.924477, -89.224398, -27.800035, 14.858993, 15.568986, -94.606907, -7.643222, -47.653395, 23.644899, -142.626672, 17.817723, -105.951385, 3.183494, 134.000894, 21.07239, -176.429283, 0.259264, 124.066034, -23.495434, 67.047596)),
    ("arbitrary-b", "2026-08-21T18:00:00Z", 144, 241.058337, (11.588418, -89.288072, -28.066146, 27.273053, 14.943861, -93.608829, -8.101602, -47.845485, 23.624424, -142.905169, 17.759576, -106.718879, 3.163342, 132.976981, 21.075312, -177.397616, 0.25021, 123.060888, -23.500834, 66.040323)),
    ("arbitrary-b", "2026-08-21T18:00:00Z", 276, 211.961865, (11.277709, -59.348116, -27.167031, 68.622259, 14.34747, -62.710097, -8.518699, -18.028198, 23.603013, -113.161994, 17.706209, -77.422973, 3.144423, 162.037208, 21.077866, -148.28601, 0.241803, 152.139231, -23.505711, 95.117184)),
)
# fmt: on


@pytest.fixture(scope="module")
def oracle_series_by_start() -> dict[str, list[dict]]:
    """The backend series for each oracle start, 288 samples at 600 s (what the oracle was built from)."""
    out = {}
    for label, start_text in sorted({(row[0], row[1]) for row in ORACLE_SERIES_ROWS}):
        start = parse_z(start_text)
        out[label] = earth_state_series(start, start + timedelta(seconds=600 * 287), 600)["samples"]
    return out


def _check_against_oracle_row(sample: dict, row: tuple, tolerance: float) -> None:
    label, _start, k, gast, flat = row
    assert angdiff(sample["gast_deg"], gast) <= tolerance, (label, k, "gast_deg")
    bodies = bodies_of(sample)
    for index, body_id in enumerate(BODY_IDS):
        lat, lon = flat[2 * index], flat[2 * index + 1]
        assert abs(bodies[body_id]["lat"] - lat) <= tolerance, (label, k, body_id, "lat")
        assert angdiff(bodies[body_id]["lon"], lon) <= tolerance, (label, k, body_id, "lon")


class TestAgainstTheIndependentOracle:
    """Literals from W3-O (dev-g1's swisseph oracle; the JSON is never imported).

    The oracle rounds to 6 decimals, so a faithful implementation differs by at
    most 5e-7 degrees; over all 1,080 stored samples x 10 bodies the measured
    worst difference was 5.0e-7 for gast_deg, lat and lon alike. The bound here
    is 1e-6. Same ephemeris (Moshier fallback) on both sides: this proves the
    maths around it (declination, GAST, the lon = ra - gast wrap, the grid), not
    the ephemeris itself.
    """

    TOLERANCE = 1e-6

    def test_the_literal_table_is_the_one_the_rule_describes(self):
        labels = {row[0] for row in ORACLE_SERIES_ROWS}
        assert labels == {
            "equinox-2026",
            "solstice-2026",
            "moon-seam-day",
            "mercury-retro",
            "range-start-1950",
            "range-end-2049",
            "reference-instant",
            "perihelion-season",
            "aphelion-season",
            "j2000-noon",
            "arbitrary-a",
            "arbitrary-b",
        }
        assert len(ORACLE_SERIES_ROWS) == 45
        seam_moon_lons = [
            row[4][3] for row in ORACLE_SERIES_ROWS if row[0] == "moon-seam-day" and abs(row[4][3]) >= 175
        ]
        assert any(lon > 0 for lon in seam_moon_lons) and any(lon < 0 for lon in seam_moon_lons)

    def test_core_series_matches_every_literal_row(self, oracle_series_by_start):
        for row in ORACLE_SERIES_ROWS:
            sample = oracle_series_by_start[row[0]][row[2]]
            assert parse_z(sample["at"]) == parse_z(row[1]) + timedelta(seconds=600 * row[2]), row[:3]
            _check_against_oracle_row(sample, row, self.TOLERANCE)

    @pytest.mark.parametrize("label", ["moon-seam-day", "range-start-1950", "range-end-2049"])
    def test_the_route_matches_the_literal_rows_too(self, client, label):
        rows = [row for row in ORACLE_SERIES_ROWS if row[0] == label]
        start = parse_z(rows[0][1])
        response = client.get(
            "/astrology/earth-state/series",
            params={"start": iso_z(start), "end": iso_z(start + timedelta(seconds=600 * 287)), "step_seconds": 600},
        )
        assert response.status_code == 200
        samples = response.json()["samples"]
        for row in rows:
            _check_against_oracle_row(samples[row[2]], row, self.TOLERANCE)
