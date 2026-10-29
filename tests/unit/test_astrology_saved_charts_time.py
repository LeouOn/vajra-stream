# tests/unit/test_astrology_saved_charts_time.py
"""ADP-3: the saved-chart routes must resolve a birth time to ONE honest instant.

THE DEFECT
----------
``create_saved_chart`` and its update path did::

    tz = chart.timezone or geocoding_service...[chart.city]["timezone"]
    dt = pytz.timezone(tz).localize(dt)

``pytz``'s ``localize`` defaults to ``is_dst=False``, so a fall-back overlap was
silently resolved to STANDARD time - an hour out, with the Ascendant about 11.8
degrees away - and a spring-forward gap was silently replaced. The stored
``timezone`` column and the same ``localize`` path were used by
``/charts/{id}/recalculate``, ``/charts/{id}/transits`` and the export routes.

DATABASE SAFETY (read twice)
----------------------------
These routes open SQLite through ``get_db_path()``, which can resolve to the
MAINTAINER'S LIVE ``vajra_stream.db``. The ``db`` fixture below patches
``get_db_path`` to a ``tmp_path`` file BEFORE any route is called, and asserts
that the path in use is not the repository's database. The fixture also asserts
the live file was not touched.
"""

from __future__ import annotations

import datetime
import hashlib
import pathlib

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LIVE_DB = REPO_ROOT / "vajra_stream.db"
LIVE_DB_MD5 = "9a580a8f93b048aba9b46c06e398d5e9"

CITIES = {
    "Paris": {"latitude": 48.86, "longitude": 2.35, "timezone": "Europe/Paris"},
    "New York": {"latitude": 40.71, "longitude": -74.01, "timezone": "America/New_York"},
    "Tokyo": {"latitude": 35.68, "longitude": 139.69, "timezone": "Asia/Tokyo"},
}


def _md5(path: pathlib.Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A throwaway SQLite file, and a hard guarantee it is not the live one."""
    from backend.app.api.v1.endpoints import astrology as ep
    from core import schema as schema_mod

    target = tmp_path / "saved_charts_test.db"
    # Both resolvers must point at the scratch file: the routes use the endpoint's
    # helper, and init_db() uses core.schema's.
    monkeypatch.setattr(ep, "get_db_path", lambda: str(target))
    monkeypatch.setattr(schema_mod, "get_db_path", lambda *a, **k: str(target))

    # The path the routes will actually use must not be the maintainer's database.
    assert (
        pathlib.Path(ep.get_db_path()).resolve() != LIVE_DB.resolve()
    ), "the test would write to the maintainer's live database"
    assert (
        pathlib.Path(schema_mod.get_db_path()).resolve() != LIVE_DB.resolve()
    ), "init_db would create the schema on the maintainer's live database"
    assert LIVE_DB.name not in pathlib.Path(ep.get_db_path()).name

    schema_mod.init_db()
    assert target.exists(), "the schema was not created on the scratch database"
    return target


@pytest.fixture
def client(db, monkeypatch):
    """A client over a MINIMAL app that mounts only the astrology router.

    Deliberately not ``backend.app.main.app``: that app pulls in the whole service
    stack and its lifespan, and this test is about the saved-chart routes only.
    Mounting the router directly keeps the test hermetic and avoids touching
    anything the full app would start.
    """
    from fastapi import FastAPI

    from backend.app.api.v1.endpoints import astrology as ep
    from backend.core.services.geocoding_service import geocoding_service

    def fake(city_name: str) -> dict:
        if city_name not in CITIES:
            return {"error": "not found"}
        return dict(CITIES[city_name])

    monkeypatch.setattr(geocoding_service, "get_coordinates_and_timezone", fake)

    app = FastAPI()
    app.include_router(ep.router, prefix="/api/v1/astrology")
    return TestClient(app)


def _insert_chart(db_path, *, name="Alice", birth="1990-07-04T09:00:00", tz="Europe/Paris", city="Paris"):
    """Put a row in the saved_natal_charts table directly."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        INSERT INTO saved_natal_charts
        (name, birth_time_iso, latitude, longitude, timezone, city, description, tags,
         notes, cached_chart_data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, '', '', '', NULL, '2026-01-01T00:00:00', '2026-01-01T00:00:00')
        """,
        (name, birth, CITIES[city]["latitude"], CITIES[city]["longitude"], tz, city),
    )
    conn.commit()
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return row_id


# --------------------------------------------------------------------------- #
# 1. An ambiguous wall time is refused, not silently shifted.
# --------------------------------------------------------------------------- #
def test_an_ambiguous_birth_time_is_422_not_a_standard_time_chart(client, db):
    """2024-11-03 01:30 in New York happens twice. The old code picked the first
    (is_dst=False) and said nothing."""
    resp = client.post(
        "/api/v1/astrology/charts",
        json={
            "name": "Alice",
            "birth_time_iso": "2024-11-03T01:30:00",
            "city": "New York",
            "latitude": 40.71,
            "longitude": -74.01,
            "timezone": "America/New_York",
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert "America/New_York" in detail, detail
    assert "2024-11-03 01:30:00" in detail, detail
    # BOTH candidates must be named
    assert "2024-11-03T05:30:00+00:00" in detail, detail
    assert "2024-11-03T06:30:00+00:00" in detail, detail


def test_the_opt_in_makes_the_ambiguous_chart_possible(client, db):
    resp = client.post(
        "/api/v1/astrology/charts",
        json={
            "name": "Alice",
            "birth_time_iso": "2024-11-03T01:30:00",
            "city": "New York",
            "latitude": 40.71,
            "longitude": -74.01,
            "timezone": "America/New_York",
            "ambiguous": "later",
        },
    )
    assert resp.status_code == 200, resp.text
    resolution = resp.json()["time_resolution"]
    assert resolution["utc_iso"] == "2024-11-03T06:30:00+00:00", resolution
    assert "later" in " ".join(resolution["warnings"]), resolution


def test_a_nonexistent_birth_time_is_422(client, db):
    """2024-03-10 02:30 in New York never happened."""
    resp = client.post(
        "/api/v1/astrology/charts",
        json={
            "name": "Alice",
            "birth_time_iso": "2024-03-10T02:30:00",
            "city": "New York",
            "latitude": 40.71,
            "longitude": -74.01,
            "timezone": "America/New_York",
        },
    )
    assert resp.status_code == 422, resp.text
    assert "America/New_York" in resp.json()["detail"]


def test_the_nonexistent_opt_in_works(client, db):
    resp = client.post(
        "/api/v1/astrology/charts",
        json={
            "name": "Alice",
            "birth_time_iso": "2024-03-10T02:30:00",
            "city": "New York",
            "latitude": 40.71,
            "longitude": -74.01,
            "timezone": "America/New_York",
            "nonexistent": "shift_forward",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["time_resolution"]["utc_iso"] == "2024-03-10T07:30:00+00:00"


# --------------------------------------------------------------------------- #
# 2. A unique wall time is unchanged.
# --------------------------------------------------------------------------- #
def test_a_unique_birth_time_is_unchanged(client, db):
    resp = client.post(
        "/api/v1/astrology/charts",
        json={
            "name": "Alice",
            "birth_time_iso": "1990-07-04T09:00:00",
            "city": "Paris",
            "latitude": 48.86,
            "longitude": 2.35,
            "timezone": "Europe/Paris",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["time_resolution"]["utc_iso"] == "1990-07-04T07:00:00+00:00", body
    assert body["time_resolution"]["zone"] == "Europe/Paris"
    assert body["time_resolution"]["is_dst"] is True


def test_an_offset_birth_time_is_kept_as_an_exact_instant(client, db):
    resp = client.post(
        "/api/v1/astrology/charts",
        json={
            "name": "Alice",
            "birth_time_iso": "1990-07-04T09:00:00+05:00",
            "city": "Paris",
            "latitude": 48.86,
            "longitude": 2.35,
            "timezone": "Europe/Paris",
        },
    )
    assert resp.status_code == 200, resp.text
    resolution = resp.json()["time_resolution"]
    assert resolution["utc_iso"] == "1990-07-04T04:00:00+00:00", resolution
    warnings = " ".join(resolution["warnings"])
    assert "+05:00" in warnings, "a mismatch with the stored zone must be said"
    assert "Europe/Paris" in warnings, warnings


def test_the_existing_response_keys_are_unchanged(client, db):
    """The keys the create route returned before, all still there with the same types."""
    resp = client.post(
        "/api/v1/astrology/charts",
        json={
            "name": "Alice",
            "birth_time_iso": "1990-07-04T09:00:00",
            "city": "Paris",
            "latitude": 48.86,
            "longitude": 2.35,
            "timezone": "Europe/Paris",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in (
        "id",
        "name",
        "birth_time_iso",
        "latitude",
        "longitude",
        "timezone",
        "city",
        "description",
        "tags",
        "notes",
        "cached_chart_data",
        "created_at",
        "updated_at",
    ):
        assert key in body, f"the response lost {key!r}: {sorted(body)}"
    assert isinstance(body["id"], int)
    assert isinstance(body["name"], str)
    assert isinstance(body["birth_time_iso"], str)
    assert isinstance(body["latitude"], float)
    assert isinstance(body["timezone"], str)
    assert isinstance(body["cached_chart_data"], str)
    # and the new one is additive
    assert isinstance(body["time_resolution"], dict)


# --------------------------------------------------------------------------- #
# 3. /recalculate is strict and does NOT change the stored chart.
# --------------------------------------------------------------------------- #
def test_recalculate_of_an_ambiguous_stored_chart_is_422_and_changes_nothing(client, db):
    chart_id = _insert_chart(db, birth="2024-11-03T01:30:00", tz="America/New_York")

    import sqlite3

    before = (
        sqlite3.connect(str(db))
        .execute(
            "SELECT birth_time_iso, cached_chart_data FROM saved_natal_charts WHERE id = ?",
            (chart_id,),
        )
        .fetchone()
    )

    resp = client.post(f"/api/v1/astrology/charts/{chart_id}/recalculate")
    assert resp.status_code == 422, resp.text
    assert "America/New_York" in resp.json()["detail"]

    after = (
        sqlite3.connect(str(db))
        .execute(
            "SELECT birth_time_iso, cached_chart_data FROM saved_natal_charts WHERE id = ?",
            (chart_id,),
        )
        .fetchone()
    )
    assert after == before, "a refused recalculation must not change the stored row"


def test_recalculate_of_a_unique_stored_chart_still_works(client, db):
    chart_id = _insert_chart(db, birth="1990-07-04T09:00:00", tz="Europe/Paris")
    resp = client.post(f"/api/v1/astrology/charts/{chart_id}/recalculate")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["time_resolution"]["utc_iso"] == "1990-07-04T07:00:00+00:00"


# --------------------------------------------------------------------------- #
# 4. The transits route resolves the stored birth time strictly too.
# --------------------------------------------------------------------------- #
def test_transits_of_an_ambiguous_stored_chart_is_422(client, db):
    chart_id = _insert_chart(db, birth="2024-11-03T01:30:00", tz="America/New_York")
    resp = client.post(f"/api/v1/astrology/charts/{chart_id}/transits", json={})
    assert resp.status_code == 422, resp.text
    assert "America/New_York" in resp.json()["detail"]


# --------------------------------------------------------------------------- #
# 5. Compare can now opt in, and reports a policy error as 422.
# --------------------------------------------------------------------------- #
def test_compare_of_an_ambiguous_chart_is_422(client, db):
    """The compare route re-geocodes the chart's CITY, so the stored zone is not
    what decides the instant - the city's zone is. For a chart saved for New York
    that is America/New_York, and the ambiguous wall time is refused."""
    a = _insert_chart(db, name="A", birth="2024-11-03T01:30:00", tz="America/New_York", city="New York")
    b = _insert_chart(db, name="B", birth="1990-07-04T09:00:00", tz="Europe/Paris")
    resp = client.post("/api/v1/astrology/charts/compare", json={"chart_id_a": a, "chart_id_b": b})
    assert resp.status_code == 422, resp.text
    assert "America/New_York" in resp.json()["detail"]


def test_compare_accepts_the_opt_in(client, db):
    a = _insert_chart(db, name="A", birth="2024-11-03T01:30:00", tz="America/New_York", city="New York")
    b = _insert_chart(db, name="B", birth="1990-07-04T09:00:00", tz="Europe/Paris")
    resp = client.post(
        "/api/v1/astrology/charts/compare",
        json={"chart_id_a": a, "chart_id_b": b, "ambiguous": "later"},
    )
    assert resp.status_code == 200, resp.text


def test_compare_accepts_a_per_person_opt_in_for_the_second_chart(client, db):
    """The ambiguity is in chart B, so only ``ambiguous_b`` can answer it.

    The shared ``ambiguous`` reaches both people, and A is unique so it would be
    harmless - but the POINT is that the _b override is what the route must
    forward. Without it this request is a 422.
    """
    a = _insert_chart(db, name="A", birth="1990-07-04T09:00:00", tz="Europe/Paris")
    b = _insert_chart(db, name="B", birth="2024-11-03T01:30:00", tz="America/New_York", city="New York")
    resp = client.post(
        "/api/v1/astrology/charts/compare",
        json={"chart_id_a": a, "chart_id_b": b, "ambiguous_b": "later"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["time_resolution_b"]["utc_iso"] == "2024-11-03T06:30:00+00:00", body


# --------------------------------------------------------------------------- #
# 6. The database really was a scratch file, and the live one is untouched.
# --------------------------------------------------------------------------- #
def test_the_live_database_is_untouched(client, db):
    if not LIVE_DB.exists():
        pytest.skip("the repository has no vajra_stream.db to fingerprint")
    assert _md5(LIVE_DB) == LIVE_DB_MD5, "the maintainer's live database changed"
    assert str(db) not in str(LIVE_DB), "the scratch path points at the live database"
    assert db.exists() and db.stat().st_size >= 0


def test_the_scratch_database_is_the_one_that_was_written(client, db):
    import sqlite3

    _insert_chart(db, name="Zed", birth="1990-07-04T09:00:00", tz="Europe/Paris")
    conn = sqlite3.connect(str(db))
    names = {row[0] for row in conn.execute("SELECT name FROM saved_natal_charts")}
    conn.close()
    assert "Zed" in names, "the row did not land in the scratch database"


# --------------------------------------------------------------------------- #
# 7. A bad zone is the same on both paths.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("zone", ["", "Not/AZone"], ids=["empty", "unknown"])
def test_a_bad_stored_zone_is_422(client, db, zone):
    """A stored zone the IANA database does not know is a 422, not a crash.

    ``None`` is not in the list because the column is NOT NULL: a stored row
    cannot hold a null zone. The ADP-2 chart service covers the None case for the
    birth and transit paths.
    """
    chart_id = _insert_chart(db, birth="1990-07-04T09:00:00", tz=zone)
    resp = client.post(f"/api/v1/astrology/charts/{chart_id}/recalculate")
    assert resp.status_code == 422, resp.text
    assert "Unknown IANA time zone" in resp.json()["detail"], resp.text


# --------------------------------------------------------------------------- #
# ADP-3b: the transit routes must USE the ambiguous/nonexistent opt-in.
#
# The fields were added to the two transit request models, but the routes
# resolved the transit time without them: a parameter that is accepted,
# documented, and silently ignored is worse than no parameter, because the 422
# message tells the user to pass it.
#
# Dates are independent probe dates, hand-checked:
#   2026-11-01 01:30 New York  -> earlier 05:30Z, later 06:30Z
#   2026-03-08 02:30 New York  -> a gap; shift_forward gives 07:30Z
# --------------------------------------------------------------------------- #
TRANSIT_ROUTES = [
    ("/transits", lambda c, body: c.post(f"{body[0]}/transits", json=body[1])),
    ("/transit-export", lambda c, body: c.post(f"{body[0]}/transit-export", json=body[1])),
]


def _utc(iso: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(iso).astimezone(datetime.timezone.utc)


def _transit_request(client, db, *, transit_iso, extra=None, birth="1990-07-04T09:00:00"):
    """A stored chart plus a request body for one of the two transit routes."""
    chart_id = _insert_chart(db, birth=birth, tz="America/New_York", city="New York")
    body = {"transit_time_iso": transit_iso}
    if extra:
        body.update(extra)
    return f"/api/v1/astrology/charts/{chart_id}", body


@pytest.mark.parametrize("route", ["/transits", "/transit-export"])
def test_transit_overlap_without_an_opt_in_is_422(client, db, route):
    path, body = _transit_request(client, db, transit_iso="2026-11-01T01:30:00")
    resp = client.post(f"{path}{route}", json=body)
    assert resp.status_code == 422, resp.text
    assert "America/New_York" in resp.json()["detail"], resp.text


@pytest.mark.parametrize("route", ["/transits", "/transit-export"])
def test_transit_overlap_earlier_uses_the_earlier_instant(client, db, route):
    path, body = _transit_request(client, db, transit_iso="2026-11-01T01:30:00", extra={"ambiguous": "earlier"})
    resp = client.post(f"{path}{route}", json=body)
    assert resp.status_code == 200, resp.text
    transit_time = resp.json()["data"]["transit_time"]
    assert _utc(transit_time) == datetime.datetime(2026, 11, 1, 5, 30, tzinfo=datetime.timezone.utc), transit_time
    assert transit_time.endswith("-04:00"), f"the earlier fold is still daylight time: {transit_time}"


@pytest.mark.parametrize("route", ["/transits", "/transit-export"])
def test_transit_overlap_later_uses_the_later_instant(client, db, route):
    path, body = _transit_request(client, db, transit_iso="2026-11-01T01:30:00", extra={"ambiguous": "later"})
    resp = client.post(f"{path}{route}", json=body)
    assert resp.status_code == 200, resp.text
    transit_time = resp.json()["data"]["transit_time"]
    assert _utc(transit_time) == datetime.datetime(2026, 11, 1, 6, 30, tzinfo=datetime.timezone.utc), transit_time
    assert transit_time.endswith("-05:00"), f"the later fold is standard time: {transit_time}"


@pytest.mark.parametrize("route", ["/transits", "/transit-export"])
def test_earlier_and_later_are_different_instants(client, db, route):
    """Pin that the two answers differ, not merely that both return 200."""
    path, body = _transit_request(client, db, transit_iso="2026-11-01T01:30:00", extra={"ambiguous": "earlier"})
    earlier = client.post(f"{path}{route}", json=body).json()["data"]["transit_time"]
    path, body = _transit_request(client, db, transit_iso="2026-11-01T01:30:00", extra={"ambiguous": "later"})
    later = client.post(f"{path}{route}", json=body).json()["data"]["transit_time"]
    assert _utc(earlier) != _utc(later)
    assert _utc(later) - _utc(earlier) == datetime.timedelta(hours=1)


@pytest.mark.parametrize("route", ["/transits", "/transit-export"])
def test_transit_gap_with_shift_forward_uses_the_shifted_instant(client, db, route):
    path, body = _transit_request(
        client,
        db,
        transit_iso="2026-03-08T02:30:00",
        extra={"nonexistent": "shift_forward"},
    )
    resp = client.post(f"{path}{route}", json=body)
    assert resp.status_code == 200, resp.text
    transit_time = resp.json()["data"]["transit_time"]
    assert _utc(transit_time) == datetime.datetime(2026, 3, 8, 7, 30, tzinfo=datetime.timezone.utc), transit_time


@pytest.mark.parametrize("route", ["/transits", "/transit-export"])
def test_a_transit_opt_in_does_not_leak_to_the_stored_birth(client, db, route):
    """The stored BIRTH time keeps the strict rule with no opt-in.

    A chart saved with an ambiguous birth time must still be refused, even when
    the request carries a transit opt-in: the opt-in is for transit_time_iso
    only. The way to fix such a chart is PUT /charts/{id}.
    """
    path, body = _transit_request(
        client,
        db,
        transit_iso="2026-10-01T12:00:00",
        extra={"ambiguous": "later"},
        birth="2026-11-01T01:30:00",
    )
    resp = client.post(f"{path}{route}", json=body)
    assert resp.status_code == 422, resp.text
    assert "America/New_York" in resp.json()["detail"], resp.text
