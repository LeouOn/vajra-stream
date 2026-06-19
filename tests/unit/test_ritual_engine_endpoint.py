"""Tests for the new ritual_engine API endpoint at /ritual-engine/*.

Covers:
- RitualConfigUpdate Pydantic model (all 6 fields optional, partial
  updates work via model_dump(exclude_none=True))
- Router registration: all expected routes are mounted
"""

import pytest

from backend.app.api.v1.endpoints.ritual_engine import (
    RitualConfigUpdate,
    router,
)

EXPECTED_ROUTES = [
    ("GET", "/status"),
    ("POST", "/start"),
    ("POST", "/stop"),
    ("POST", "/trigger"),
    ("POST", "/config"),
    ("GET", "/schedule"),
    ("GET", "/merit"),
]


class TestRitualConfigUpdate:
    def test_all_fields_default_to_none(self):
        cfg = RitualConfigUpdate()
        assert cfg.enabled is None
        assert cfg.min_timing_quality is None
        assert cfg.tts_enabled is None
        assert cfg.max_per_hour is None
        assert cfg.pause_between_seconds is None
        assert cfg.favored_genres is None

    def test_partial_update(self):
        cfg = RitualConfigUpdate(enabled=True, tts_enabled=False)
        assert cfg.enabled is True
        assert cfg.tts_enabled is False
        assert cfg.min_timing_quality is None
        assert cfg.favored_genres is None

    def test_full_update(self):
        cfg = RitualConfigUpdate(
            enabled=True,
            min_timing_quality="good",
            tts_enabled=True,
            max_per_hour=5,
            pause_between_seconds=30,
            favored_genres=["healing", "compassion"],
        )
        assert cfg.enabled is True
        assert cfg.min_timing_quality == "good"
        assert cfg.tts_enabled is True
        assert cfg.max_per_hour == 5
        assert cfg.pause_between_seconds == 30
        assert cfg.favored_genres == ["healing", "compassion"]

    def test_model_dump_excludes_none(self):
        cfg = RitualConfigUpdate(enabled=True)
        dumped = cfg.model_dump(exclude_none=True)
        assert dumped == {"enabled": True}
        assert "min_timing_quality" not in dumped
        assert "favored_genres" not in dumped

    def test_max_per_hour_must_be_int(self):
        with pytest.raises(Exception):
            RitualConfigUpdate(max_per_hour="not a number")

    def test_favored_genres_accepts_list_of_strings(self):
        cfg = RitualConfigUpdate(favored_genres=["healing", "wisdom"])
        assert cfg.favored_genres == ["healing", "wisdom"]


class TestRitualEngineRoutes:
    def test_all_expected_routes_are_registered(self):
        actual_routes = [(frozenset(r.methods), r.path) for r in router.routes if hasattr(r, "methods")]
        for method, path in EXPECTED_ROUTES:
            method_set = frozenset({method} if method != "GET" else ["GET", "HEAD"])
            found = any((r_methods & method_set) and r_path == path for r_methods, r_path in actual_routes)
            assert found, f"missing route {method} {path} in ritual_engine router"

    def test_router_has_seven_routes(self):
        route_count = sum(1 for r in router.routes if hasattr(r, "methods"))
        assert route_count == len(EXPECTED_ROUTES), f"expected {len(EXPECTED_ROUTES)} routes, got {route_count}"
