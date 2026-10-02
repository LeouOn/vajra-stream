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
# Several backend modules trigger `core.schema.init_db()` at *import* time:
# astrology.py and locations.py call their module-level `init_db()`,
# agent_suggestions.py calls `init_tables()`, and radionics.py instantiates
# `IntegratedScalarRadionicsBroadcaster()`, whose BlessingDatabase
# initializes the schema. (outlook.py used to do this too; its import-time
# init has since been removed.) `core.schema.get_db_path()` resolves
# `settings.DATABASE_URL` (default `sqlite:///./vajra_stream.db`, i.e. the
# live DB in the repo root), and endpoint modules build their db_path the
# same way (agent_suggestions and locations among them). So merely
# *importing* the backend during a test run migrates the real database —
# which is how the live file acquired a v6 `_schema_version` row mid-cycle.
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
#   Scope: DATABASE_URL now also covers the consumers that once bypassed it.
#   image_generation.py and video_generation.py resolve their DB path via
#   `_db_path()` -> `core.schema.get_db_path()`, and `BlessingDatabase`
#   (core/compassionate_blessings.py) defaults its db_path through
#   get_db_path() too, so its data operations land on the same test DB; the
#   VAJRA_DB_PATH variable those modules used to read no longer exists in
#   production code (only an unread e2e-only assignment remains). Still NOT
#   covered: callers that pass an explicit db path of their own —
#   `BlessingDatabase(db_path=...)`, direct sqlite3.connect with a hardcoded
#   path — and anything under scripts/; those bypass this override by
#   construction.
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

# ---------------------------------------------------------------------------
# Provider API keys — neutralised at the source, before any Settings build
# ---------------------------------------------------------------------------
# Real credentials exist on this machine: .env carries ANTHROPIC_API_KEY,
# OPENROUTER_API_KEY, ELEVENLABS_API_KEY and AZURE_SPEECH_KEY, and a
# developer shell may export ZAI_API_KEY. `backend/app/config.py` constructs
# `settings = Settings()` at module import, and pydantic-settings resolves
# real environment variables AHEAD of .env entries — so pinning these to ""
# here, at conftest import time (which precedes every test-module import,
# same race the DATABASE_URL block above wins), blanks the keys for every
# consumer: the Settings object itself, core/llm/bootstrap.py's plain
# `os.getenv(...)` registration gates, and core/llm/providers/*'s
# `api_key or os.getenv(...)` fallbacks. The _no_external_llm_spend guard
# below only DETECTS external spend after it happens; this prevents it at
# the source.
#
# GEMINI_API_KEY/GOOGLE_API_KEY are read by no module in this repo but are
# picked up automatically by the google-genai client library, so they are
# pinned too. Beyond the seven named keys, two obvious siblings with real
# credentials present are included: ZAI_API_KEY (may be present in a
# developer shell; gates the z_ai provider in core/llm/bootstrap.py:79 and
# core/llm/providers/z_ai.py:59) and AZURE_SPEECH_KEY (real value in .env;
# gates AzureTTS in core/enhanced_tts.py:153 and backend Settings).
# Also read by core/llm but holding no credential anywhere on this machine
# (verified: absent from .env and the environment) and therefore NOT pinned:
# MINIMAX_API_KEY, Z_AI_API_KEY, ANTHROPIC_AUTH_TOKEN — plus the LLM_-prefixed
# variants (LLM_OPENAI_API_KEY etc.), none of which exist here.
_PROVIDER_KEY_VARS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "ELEVENLABS_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "ZAI_API_KEY",
    "AZURE_SPEECH_KEY",
)
for _provider_key_var in _PROVIDER_KEY_VARS:
    os.environ[_provider_key_var] = ""


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
# Only the four sounddevice call-level functions are stubbed.
# OutputStream/Stream are deliberately left alone: grep found no usage in
# tests/ or in production, and substituting a plain function for a class
# would break isinstance() and the context-manager protocol for any future
# test that did use them.
#
# The same guard covers the other real-output path: the five
# _play_audio_file methods in core/enhanced_tts.py (lines 133, 277, 357,
# 416, 504) play through pygame.mixer(.music) when pygame is importable
# and otherwise fall back to os.system("aplay …"/"afplay …"). When pygame
# is present, exactly the attributes those methods use — mixer.init,
# music.load, music.play, music.get_busy; pygame.mixer.Sound is unused in
# this repo — are stubbed on the pygame module objects. When pygame is NOT
# importable (this venv has no pygame), that layer is skipped without
# failing and production takes the os.system fallback, which the guard
# below then catches: os.system is patched only for commands invoking a
# system player (aplay/afplay/paplay/ffplay) — recorded and swallowed with
# returncode 0 — while every other os.system command passes through to the
# original.
#
# Set VAJRA_TEST_AUDIO=1 to leave all audio output completely untouched (the
# tests' own _QUIET_GAIN then applies). That path is verified by inspection
# only — never by actually playing audio.
#
# Recorded calls describe their arguments by shape/type rather than by value:
# sd.play receives whole numpy waveforms, and retaining those would pin
# megabytes of sample data in memory for the life of the session. Arrays are
# never retained; scalar argument and keyword values (int/float/str/bool/
# None — e.g. samplerate=, loop=) are. The recorder is emptied at the start
# of each test, so its entries describe only the test currently running.
_TEST_AUDIO_ENV = "VAJRA_TEST_AUDIO"
_AUDIO_STUB_CALLS: list[dict[str, object]] = []
_AUDIO_STUB_TARGETS = ("play", "playrec", "wait", "stop")
_AUDIO_PLAYER_COMMANDS = frozenset({"aplay", "afplay", "paplay", "ffplay"})


def _describe_audio_value(value: object) -> object:
    """Summarise one argument without retaining audio data.

    Arrays are described by shape, scalars kept by value, anything else by
    type name.
    """
    shape = getattr(value, "shape", None)
    if shape is not None:
        return f"ndarray{tuple(shape)}"
    if isinstance(value, int | float | str | bool | type(None)):
        return value
    return type(value).__name__


def _describe_audio_call(name: str, args: tuple, kwargs: dict) -> dict[str, object]:
    """Summarise an intercepted audio call without retaining audio data."""
    return {
        "call": name,
        "args": [_describe_audio_value(value) for value in args],
        "kwargs": {key: _describe_audio_value(value) for key, value in kwargs.items()},
    }


def _make_audio_stub(name: str, result: object = None):
    """Build a recording no-op stand-in for one audio playback function.

    ``result`` is what the stub returns: False for pygame's get_busy (so the
    busy-wait loop in _play_audio_file exits immediately), None otherwise.
    """

    def _stub(*args, **kwargs):
        _AUDIO_STUB_CALLS.append(_describe_audio_call(name, args, kwargs))
        return result

    _stub.__name__ = f"stub_{name.replace('.', '_')}"
    _stub.__doc__ = f"Test stub: records and discards {name}()."
    return _stub


@pytest.fixture
def audio_stub_calls() -> list[dict[str, object]]:
    """Audio calls intercepted by _silence_test_audio during THIS test.

    The recorder is emptied at the start of every test (see
    _silence_test_audio), so counts and shapes are per-test, not
    session-long. Empty when VAJRA_TEST_AUDIO=1 — in that mode nothing is
    patched and any playback is real, so absence of entries means "not
    intercepted", not "no audio happened".
    """
    return _AUDIO_STUB_CALLS


def _silence_sounddevice(monkeypatch) -> None:
    """Stub sounddevice.play/playrec/wait/stop in place."""
    sd = sys.modules.get("sounddevice")
    if sd is None:
        try:
            import sounddevice as sd
        except Exception:
            # No PortAudio / not installed / no sound card: nothing to silence.
            return

    for target in _AUDIO_STUB_TARGETS:
        if not hasattr(sd, target):
            continue
        monkeypatch.setattr(sd, target, _make_audio_stub(f"sounddevice.{target}"))


def _silence_pygame_audio(monkeypatch) -> None:
    """Stub the pygame.mixer surface used by core/enhanced_tts.py.

    Only the four attributes those methods actually call are replaced — on
    the pygame module objects themselves, so the function-local
    ``import pygame`` in production code resolves to the patched attributes
    at call time. Missing pygame degrades to a no-op (production then takes
    the os.system fallback, which _guard_os_system_player covers) instead
    of failing the test.
    """
    pygame = sys.modules.get("pygame")
    if pygame is None:
        try:
            import pygame
        except Exception:
            return

    mixer = getattr(pygame, "mixer", None)
    music = getattr(mixer, "music", None) if mixer is not None else None
    for owner, attr, name, result in (
        (mixer, "init", "pygame.mixer.init", None),
        (music, "load", "pygame.mixer.music.load", None),
        (music, "play", "pygame.mixer.music.play", None),
        (music, "get_busy", "pygame.mixer.music.get_busy", False),
    ):
        if owner is None or not hasattr(owner, attr):
            continue
        monkeypatch.setattr(owner, attr, _make_audio_stub(name, result))


def _guard_os_system_player(monkeypatch) -> None:
    """Swallow os.system player invocations; pass every other command through.

    os.system is patched on the shared os module object, so every
    ``import os`` + ``os.system(...)`` call site (all five _play_audio_file
    methods among them) sees the guard while it is active. A command whose
    first word is aplay/afplay/paplay/ffplay (basename, so an absolute
    path like /usr/bin/aplay also counts) is recorded in _AUDIO_STUB_CALLS
    and reported as success (0) without executing; everything else runs
    through the original os.system. Restored per test by monkeypatch.
    """
    original_system = os.system

    def _guarded_system(command: str) -> int:
        tokens = command.split() if isinstance(command, str) else []
        if tokens and tokens[0].rsplit("/", 1)[-1] in _AUDIO_PLAYER_COMMANDS:
            _AUDIO_STUB_CALLS.append(_describe_audio_call("os.system", (command,), {}))
            return 0
        return original_system(command)

    _guarded_system.__name__ = "stub_os_system_players"
    _guarded_system.__doc__ = (
        "Test stub: records aplay/afplay/paplay/ffplay invocations, passes other commands through."
    )
    monkeypatch.setattr(os, "system", _guarded_system)


@pytest.fixture(autouse=True)
def _silence_test_audio(monkeypatch):
    """No-op real audio output paths unless VAJRA_TEST_AUDIO=1.

    Autouse so no test can reach the speakers by accident. Three layers,
    all patched through monkeypatch and restored per test: sounddevice
    play/playrec/wait/stop, the pygame.mixer calls used by
    core/enhanced_tts.py, and os.system player fallbacks. Each optional
    dependency that is missing (sounddevice without PortAudio, pygame not
    installed) degrades to skipping its layer instead of failing
    collection. The recorder is cleared here, at the start of every test,
    so _AUDIO_STUB_CALLS — and the audio_stub_calls fixture, which hands
    out that very same list — describe only the current test.

    Set VAJRA_TEST_AUDIO=1 to leave everything completely untouched (the
    tests' own _QUIET_GAIN then applies). That path is verified by
    inspection only — never by actually playing audio.
    """
    del _AUDIO_STUB_CALLS[:]

    if os.environ.get(_TEST_AUDIO_ENV) == "1":
        yield
        return

    _silence_sounddevice(monkeypatch)
    _silence_pygame_audio(monkeypatch)
    _guard_os_system_player(monkeypatch)
    yield
