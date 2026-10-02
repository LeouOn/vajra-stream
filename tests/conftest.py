import atexit
import os
import shutil
import sys
import tempfile

import pytest

from infrastructure.event_bus import EnhancedEventBus

# ---------------------------------------------------------------------------
# Test-suite DB isolation — the suite must NEVER touch vajra_stream.db
# ---------------------------------------------------------------------------
# `backend/app/api/v1/endpoints/outlook.py` calls `core.schema.init_db()` at
# *import* time, and `core.schema.get_db_path()` resolves
# `settings.DATABASE_URL` (default `sqlite:///./vajra_stream.db`, i.e. the
# live DB in the repo root). Several endpoints build their db_path the same
# way (`agent_suggestions.py:15`, `locations.py:53`). So merely *importing*
# the backend during a test run migrates the real database — which is how the
# live file acquired a v6 `_schema_version` row mid-cycle.
#
# Why the env var, set here, at conftest import time:
#   `backend/app/config.py` builds `settings = Settings()` at *module import*
#   time, and pydantic-settings resolves fields once, on construction. That
#   object is frozen for the life of the process — later mutations of
#   os.environ cannot move it. pytest imports tests/conftest.py before it
#   imports any test module, so setting DATABASE_URL here is early enough to
#   win that race for every backend import in the suite.
#
#   Note precisely what this does and does not do for
#   `tests/integration/test_extraction.py`, whose own DATABASE_URL assignment
#   (line 42) is silently ineffective in a full-suite run: tests/backend/
#   test_config.py imports `backend.app.config` at module level and
#   tests/backend is collected before tests/integration, so settings has
#   already frozen by the time test_extraction.py is imported. In full-suite
#   order the app therefore still uses the conftest temp DB set here — which
#   is the point: the live file is off limits either way. test_extraction.py
#   only gets its own per-module DB when it is the first thing to import the
#   backend (e.g. run on its own); this block does not restore that ordering.
#
#   Scope limit: DATABASE_URL does NOT cover every DB consumer in this repo.
#   `image_generation.py:82` and `video_generation.py:78` read a different
#   variable, VAJRA_DB_PATH, which nothing here sets. `BlessingDatabase`
#   (core/compassionate_blessings.py:275) defaults `db_path="vajra_stream.db"`
#   as a literal and opens `sqlite3.connect(self.db_path)` for every data
#   operation, bypassing get_db_path() entirely; only its schema
#   initialization routes through core.schema.init_db(). Both remain live-DB
#   reachable and are out of scope for this block.
#
# The four slashes are required, not a typo: `get_db_path()` strips the
# literal `sqlite:///` prefix and only keeps the remainder when the result is
# absolute. A three-slash URL would resolve relative to the project root and
# hand us back the live file. This matches the construction already used by
# tests/integration/test_extraction.py.
#
# The override is unconditional — a developer's or CI's own DATABASE_URL must
# not be able to point the suite at real data. Nothing in tests/ reads the
# live DB: tests/core/healing_dialogue/test_service.py monkeypatches
# `core.schema.get_db_path` to its own tmp_path, and the remainder were
# verified by grep to only *mention* vajra_stream.db in comments. So no
# opt-in escape hatch is offered; one would only weaken the guarantee.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="vajra-test-db-")
TEST_DB_PATH = os.path.join(_TEST_DB_DIR, "vajra_stream.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"


def _cleanup_test_db_dir() -> None:
    """Remove the session temp DB directory when the pytest process exits."""
    shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)


atexit.register(_cleanup_test_db_dir)


@pytest.fixture
def event_bus():
    bus = EnhancedEventBus()
    yield bus
    bus.clear()


@pytest.fixture
def fresh_container():
    from container import Container

    c = Container()
    c._initialized = False
    c.__init__()
    yield c
    c.reset()


@pytest.fixture
def tmp_output_dir(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    return out


# ---------------------------------------------------------------------------
# Deterministic geocoding for tests
# ---------------------------------------------------------------------------
# The real backend/core/services/geocoding_service.py wraps geopy.Nominatim,
# which is rate-limited (HTTP 429) by OpenStreetMap. The integration and
# e2e tests create natal charts with city names ("London", "Tokyo", ...)
# and were intermittently failing when pytest collected enough geocoding
# calls in a short window to hit the rate limit.
#
# This autouse fixture swaps the singleton's lookup method for a
# deterministic dict-based implementation. Tests that need to assert
# specific lat/lon (like the e2e workflow) get the same canonical
# coordinates on every run; tests that exercise the "city not found"
# path (e.g. test_400_on_bad_geocode) get a real "not found" reply.
# ---------------------------------------------------------------------------
_CANNED_GEOCODES: dict[str, dict] = {
    "London": {
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London",
        "address": "London, Greater London, England, UK",
    },
    "Paris": {
        "latitude": 48.8566,
        "longitude": 2.3522,
        "timezone": "Europe/Paris",
        "address": "Paris, Île-de-France, France",
    },
    "New York": {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York",
        "address": "New York, NY, USA",
    },
    "Tokyo": {
        "latitude": 35.6762,
        "longitude": 139.6503,
        "timezone": "Asia/Tokyo",
        "address": "Tokyo, Japan",
    },
    "New Delhi": {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timezone": "Asia/Kolkata",
        "address": "New Delhi, Delhi, India",
    },
    "San Francisco": {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timezone": "America/Los_Angeles",
        "address": "San Francisco, CA, USA",
    },
    "Beijing": {
        "latitude": 39.9042,
        "longitude": 116.4074,
        "timezone": "Asia/Shanghai",
        "address": "Beijing, China",
    },
    "Mumbai": {
        "latitude": 19.0760,
        "longitude": 72.8777,
        "timezone": "Asia/Kolkata",
        "address": "Mumbai, Maharashtra, India",
    },
}


def _fake_get_coordinates_and_timezone(self, location_name: str) -> dict:
    """Stand-in for GeocodingService.get_coordinates_and_timezone used
    in tests. Returns canned data for known cities, a "not found"
    error for anything that starts with Xyzzy (the convention the
    e2e test uses to assert the 400 path), and a generic UTC fallback
    for any other unknown city so that tests which only assert
    *success* still succeed without hitting the real Nominatim service.
    """
    key = (location_name or "").strip()
    if key in _CANNED_GEOCODES:
        return dict(_CANNED_GEOCODES[key])
    if key.startswith("Xyzzy"):
        return {"error": f"Location '{key}' not found."}
    return {
        "latitude": 0.0,
        "longitude": 0.0,
        "timezone": "UTC",
        "address": key or "Unknown",
    }


@pytest.fixture(autouse=True)
def _deterministic_geocoding(monkeypatch):
    """Replace GeocodingService.get_coordinates_and_timezone with a
    deterministic dict lookup. Autouse so every test that triggers a
    chart creation (and therefore a city lookup) sees the same
    canonical coordinates and never hits the real Nominatim service.

    We load geocoding_service.py by file path (bypassing the circular
    import chain in backend.core.services.__init__) and register it
    in sys.modules under its real dotted name. This ensures that when
    endpoint code does ``from backend.core.services.geocoding_service
    import geocoding_service`` at runtime, Python finds the cached
    module (with the patched class) rather than importing a fresh copy.
    """
    import importlib.util
    import os
    import sys

    mod_name = "backend.core.services.geocoding_service"
    # If the module is already loaded (e.g. by a prior import), patch it directly.
    if mod_name in sys.modules:
        gs_mod = sys.modules[mod_name]
    else:
        gs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "backend",
            "core",
            "services",
            "geocoding_service.py",
        )
        if not os.path.exists(gs_path):
            return
        spec = importlib.util.spec_from_file_location(mod_name, gs_path)
        gs_mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(gs_mod)
        except Exception as exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).debug("Skipping geocoding patch: %s: %s", type(exc).__name__, exc)
            return
        # Register in sys.modules so the endpoint's function-level import
        # resolves to THIS module object (with the patched class).
        sys.modules[mod_name] = gs_mod

    monkeypatch.setattr(
        gs_mod.GeocodingService,
        "get_coordinates_and_timezone",
        _fake_get_coordinates_and_timezone,
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast isolated tests")
    config.addinivalue_line("markers", "integration: tests wiring multiple modules")
    config.addinivalue_line("markers", "slow: tests taking more than a few seconds")


# ---------------------------------------------------------------------------
# No real external LLM spend from the test suite
# ---------------------------------------------------------------------------
# A test that reaches an external provider (openrouter/deepseek/openai/...)
# burns quota and money even when it "passes". Recording happens in
# LLMUsageTracker.record — every layer funnels there — so the guard wraps
# it and fails whichever test was running when an external record landed.
# Live external calls belong in tests/e2e/ only, which this guard exempts.
_EXTERNAL_LLM_PROVIDERS = frozenset({"openrouter", "deepseek", "openai", "anthropic", "z_ai", "minimax"})


@pytest.fixture(autouse=True)
def _no_external_llm_spend(request, monkeypatch):
    nodeid = request.node.nodeid.replace("\\", "/")
    if "/e2e/" in nodeid or request.node.get_closest_marker("e2e"):
        yield
        return

    from core.llm.usage import LLMUsageTracker

    violations: list[str] = []
    original = LLMUsageTracker.record

    def guarded_record(self, record):
        if str(getattr(record, "provider", "")).lower() in _EXTERNAL_LLM_PROVIDERS:
            violations.append(
                f"{record.provider}/{getattr(record, 'model', '?')} tok={getattr(record, 'total_tokens', '?')}"
            )
        return original(self, record)

    monkeypatch.setattr(LLMUsageTracker, "record", guarded_record)
    yield
    assert not violations, (
        f"{request.node.nodeid} made REAL external LLM call(s): {', '.join(violations)}. "
        "Mock the LLM/registry in this test — live external calls belong in tests/e2e/."
    )


# ---------------------------------------------------------------------------
# Silent audio by default — tests must not play through the speakers
# ---------------------------------------------------------------------------
# tests/unit/test_enhanced_audio.py, test_prayer_bowl_audio.py and
# test_intelligent_composition.py do `import sounddevice as sd` at module level
# and then call sd.play/sd.wait/sd.stop against the real output device. They
# scale their samples by _QUIET_GAIN (0.2), which is an attenuation, not a
# mute — on a machine with a real sound card the suite is still audible.
# (This box has six output devices; `sd.query_devices()` confirms it.)
#
# The stub replaces attributes on the sounddevice MODULE OBJECT rather than
# swapping sys.modules["sounddevice"]. That matters because every production
# caller reaches sounddevice as `import sounddevice as sd` followed by
# attribute access at call time (core/audio_generator.py:41,
# core/enhanced_audio_generator.py:27, core/buddha_recitation_loop.py:319,
# backend/core/services/vajra_service.py:201) — there is no `from sounddevice
# import play` binding anywhere in the repo, so module-attribute patching is
# sufficient and complete for those call sites.
#
# tests/core/* is unaffected: those tests inject their own MagicMock via
# `patch.dict(sys.modules, ...)` AND `patch.object(<consumer>, "sd", mock)`,
# so they never reach the real module. Their assertions on mock_sd.play are
# therefore untouched by this fixture.
#
# Only the four call-level functions are stubbed. OutputStream/Stream are
# deliberately left alone: grep found no usage in tests/ or in production, and
# substituting a plain function for a class would break isinstance() and the
# context-manager protocol for any future test that did use them.
#
# Set VAJRA_TEST_AUDIO=1 to leave sounddevice completely untouched (the tests'
# own _QUIET_GAIN then applies). That path is verified by inspection only —
# never by actually playing audio.
#
# Recorded calls describe their arguments by shape/type rather than by value:
# sd.play receives whole numpy waveforms, and retaining those would pin
# megabytes of sample data in memory for the life of the session.
_TEST_AUDIO_ENV = "VAJRA_TEST_AUDIO"
_AUDIO_STUB_CALLS: list[dict[str, object]] = []
_AUDIO_STUB_TARGETS = ("play", "playrec", "wait", "stop")


def _describe_audio_call(name: str, args: tuple, kwargs: dict) -> dict[str, object]:
    """Summarise an intercepted sounddevice call without retaining audio data."""
    described: list[object] = []
    for value in args:
        shape = getattr(value, "shape", None)
        if shape is not None:
            described.append(f"ndarray{tuple(shape)}")
        elif isinstance(value, int | float | str | bool | type(None)):
            described.append(value)
        else:
            described.append(type(value).__name__)
    return {"call": name, "args": described, "kwargs": sorted(kwargs)}


@pytest.fixture
def audio_stub_calls() -> list[dict[str, object]]:
    """Calls intercepted by _silence_test_audio so far this session.

    Empty when VAJRA_TEST_AUDIO=1 — in that mode nothing is patched and any
    playback is real, so absence of entries means "not intercepted", not
    "no audio happened".
    """
    return _AUDIO_STUB_CALLS


@pytest.fixture(autouse=True)
def _silence_test_audio(monkeypatch):
    """No-op sounddevice.play/playrec/wait/stop unless VAJRA_TEST_AUDIO=1.

    Autouse so no test can reach the speakers by accident. Restored per test
    by monkeypatch. Resolves sounddevice from sys.modules first and only falls
    back to importing it, so a missing PortAudio install (or a box without a
    sound card) degrades to doing nothing instead of failing collection.
    """
    if os.environ.get(_TEST_AUDIO_ENV) == "1":
        yield
        return

    sd = sys.modules.get("sounddevice")
    if sd is None:
        try:
            import sounddevice as sd
        except Exception:
            # No PortAudio / not installed / no sound card: nothing to silence.
            yield
            return

    for target in _AUDIO_STUB_TARGETS:
        if not hasattr(sd, target):
            continue

        def _stub(*args, __name=target, **kwargs):
            _AUDIO_STUB_CALLS.append(_describe_audio_call(__name, args, kwargs))

        _stub.__name__ = f"stub_sounddevice_{target}"
        _stub.__doc__ = f"Test stub: records and discards sounddevice.{target}()."
        monkeypatch.setattr(sd, target, _stub)

    yield
