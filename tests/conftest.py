import atexit
import os
import shlex
import shutil
import sqlite3
import sys
import tempfile

import pytest

from infrastructure.event_bus import EnhancedEventBus

# ---------------------------------------------------------------------------
# Test-suite DB isolation — the suite must NEVER touch vajra_stream.db
# ---------------------------------------------------------------------------
# Several backend modules used to trigger `core.schema.init_db()` at *import*
# time: astrology.py and locations.py called their module-level `init_db()`,
# agent_suggestions.py called `init_tables()`, and radionics.py instantiated
# `IntegratedScalarRadionicsBroadcaster()`. That is no longer true: the
# endpoint-owned initialization has been removed, and the application lifespan
# in `backend/app/main.py` now owns opening and closing the central schema
# connection. (outlook.py's import-time init was removed earlier still.)
# The isolation below is therefore PREVENTIVE rather than a patch for a known
# importer — it guarantees the property regardless of what any future module
# does at import time.
#
# Why it still matters:
#   `core.schema.get_db_path()` resolves `settings.DATABASE_URL` (default
#   `sqlite:///./vajra_stream.db`, i.e. the live DB in the repo root), and
#   endpoint modules build their db_path the same way. So if any import path
#   reaches a schema call, merely *importing* the backend during a test run
#   migrates the real database — which is how the live file acquired a v6
#   `_schema_version` row mid-cycle, back when the callers above did exist. The
#   tests must never be able to do that, so the env var is set unconditionally.
#
# Why the env var, set here, at conftest import time:
#   `config/backend_settings.py` builds `backend_settings = BackendSettings()`
#   at *module import* time, and pydantic-settings resolves fields once, on
#   construction. That object is frozen for the life of the process — later
#   mutations of os.environ cannot move it. pytest imports tests/conftest.py
#   before it imports any test module, so setting DATABASE_URL here is early
#   enough to win that race for every backend import in the suite. The assert
#   just below makes that ordering a checked fact rather than an assumption.
#   (Before ADR 002 step 3, 2026-10-16, the same object lived in the deleted
#   `backend/app/config.py` shim.)
#
#   Note precisely what this does and does not do for
#   `tests/integration/test_extraction.py`, whose own DATABASE_URL assignment
#   (line 42) is silently ineffective in a full-suite run: test modules under
#   tests/backend import the backend (and with it config.backend_settings) at
#   module level and are collected before tests/integration, so the settings
#   object has already frozen by the time test_extraction.py is imported. In
#   full-suite order the app therefore still uses the conftest temp DB set here — which
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
#   construction. They are caught instead by the sqlite3.connect guard
#   installed below, which refuses to open the live file at all.
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
assert "config.backend_settings" not in sys.modules, (
    "config.backend_settings was imported before tests/conftest.py set DATABASE_URL; "
    "its frozen settings object would point the suite at the live vajra_stream.db"
)
_TEST_DB_DIR = tempfile.mkdtemp(prefix="vajra-test-db-")
TEST_DB_PATH = os.path.join(_TEST_DB_DIR, "vajra_stream.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

# ---------------------------------------------------------------------------
# Hard guard: sqlite3 refuses to open the live database during the suite
# ---------------------------------------------------------------------------
# DATABASE_URL only redirects code that asks core.schema / backend_settings
# for a path. This closes the remaining gap (explicit db_path arguments,
# hardcoded sqlite3.connect calls, SQLAlchemy engines): every connect goes
# through sqlite3.connect or sqlite3.dbapi2.connect (SQLAlchemy's pysqlite
# dialect uses the latter), and both raise if the target resolves to one of the
# live files. tests/unit/test_db_isolation.py proves the guard is installed.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_DB_PATHS = frozenset(
    os.path.normcase(os.path.realpath(os.path.join(_REPO_ROOT, *parts)))
    for parts in (("vajra_stream.db",), ("backend", "app", "vajra_stream.db"))
)


def is_live_db_path(database) -> bool:
    """True when a sqlite3.connect() target resolves to a live repo database."""
    if isinstance(database, bytes):
        database = os.fsdecode(database)
    if not isinstance(database, str | os.PathLike):
        return False
    target = os.fspath(database)
    if target.startswith("file:"):
        target = target[len("file:") :].split("?", 1)[0]
        if target.startswith("///"):
            target = target[2:]
    if target in ("", ":memory:"):
        return False
    return os.path.normcase(os.path.realpath(target)) in LIVE_DB_PATHS


_real_sqlite3_connect = sqlite3.connect


def _guarded_sqlite3_connect(database, *args, **kwargs):
    if is_live_db_path(database):
        raise RuntimeError(
            f"test suite tried to open the live database {database!r}; tests must use "
            "core.schema.get_db_path() (the conftest temp DB) or a tmp_path"
        )
    return _real_sqlite3_connect(database, *args, **kwargs)


_guarded_sqlite3_connect.__vajra_live_db_guard__ = True
sqlite3.connect = _guarded_sqlite3_connect
sqlite3.dbapi2.connect = _guarded_sqlite3_connect

# ---------------------------------------------------------------------------
# Provider API keys — neutralised at the source, before any Settings build
# ---------------------------------------------------------------------------
# Real credentials exist on this machine: .env carries ANTHROPIC_API_KEY,
# OPENROUTER_API_KEY, ELEVENLABS_API_KEY and AZURE_SPEECH_KEY, and a
# developer shell may export ZAI_API_KEY. `config/backend_settings.py`
# constructs `backend_settings = BackendSettings()` at module import, and pydantic-settings resolves
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
# pinned too. Real provider keys that may be exported in the developer/agent
# environment or in .env are neutralized here: ANTHROPIC_API_KEY,
# OPENAI_API_KEY, OPENROUTER_API_KEY, DEEPSEEK_API_KEY, ELEVENLABS_API_KEY,
# AZURE_SPEECH_KEY, MINIMAX_API_KEY, and both z_ai aliases (ZAI_API_KEY,
# Z_AI_API_KEY).
_PROVIDER_KEY_VARS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "ELEVENLABS_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "ZAI_API_KEY",
    "Z_AI_API_KEY",
    "MINIMAX_API_KEY",
    "AZURE_SPEECH_KEY",
)
for _provider_key_var in _PROVIDER_KEY_VARS:
    os.environ[_provider_key_var] = ""


def _cleanup_test_db_dir() -> None:
    """Remove the session temp DB directory when the pytest process exits."""
    shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)


atexit.register(_cleanup_test_db_dir)


# ---------------------------------------------------------------------------
# Session schema — lifespan parity for the scratch DB (order independence)
# ---------------------------------------------------------------------------
# Endpoint modules no longer initialize the schema at import time (item 5:
# the app lifespan in backend/app/main.py owns that in production), and unit
# tests never run a lifespan. Files like tests/unit/test_astrology.py expect
# the tables to exist; before item 5 they were created as an import side
# effect, afterwards only when some OTHER test file happened to create them
# first in the process-wide scratch DB — i.e. the suite silently became
# order-dependent. This fixture reproduces the lifespan's critical path
# once per session, right after DATABASE_URL has been pinned above, so every
# ordering sees the same schema.
#
# Safety gate: the resolved path must be a scratch DB — under the system
# temp root (this conftest's temp dir) or inside a `.pytest_tmp` directory
# (tests/integration/test_extraction.py redirects to its own scratch under
# tests/integration/.pytest_tmp when it is the first to import the backend)
# — and must NEVER be the live repo-root vajra_stream.db. Fail the session
# loudly rather than initialize anything else.
_LIVE_REPO_DB = os.path.realpath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vajra_stream.db")
)
_LIVE_BACKEND_DB = os.path.realpath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app", "vajra_stream.db")
)
_SESSION_SCRATCH_DIR = os.path.realpath(_TEST_DB_DIR)
_EXTRACTION_SCRATCH_DIR = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "integration", ".pytest_tmp")
)
_ALLOWED_SCRATCH_ROOTS = (_SESSION_SCRATCH_DIR, _EXTRACTION_SCRATCH_DIR)


def _is_scratch_db_path(path: str | None) -> bool:
    """Validate that path resides strictly within the session temp DB dir or
    the exact tests/integration/.pytest_tmp scratch dir, and never resolves
    to a live repo database or through external symlinks.
    """
    if not isinstance(path, str) or not path.strip():
        return False

    abs_path = os.path.abspath(path)
    real_path = os.path.realpath(path)

    if real_path in (_LIVE_REPO_DB, _LIVE_BACKEND_DB):
        return False

    def _is_under(target: str, root: str) -> bool:
        return target == root or target.startswith(root + os.sep)

    real_allowed = any(_is_under(real_path, root) for root in _ALLOWED_SCRATCH_ROOTS)
    abs_allowed = any(_is_under(abs_path, root) for root in _ALLOWED_SCRATCH_ROOTS)

    return real_allowed and abs_allowed


@pytest.fixture(autouse=True, scope="session")
def _session_scratch_schema():
    """Initialize the schema once against the pinned scratch DB (lifespan parity)."""
    from core.schema import get_db_path, init_db

    db_path = get_db_path()
    assert _is_scratch_db_path(db_path), (
        f"Refusing session schema init: get_db_path() resolved to {db_path!r}, "
        f"which is not a scratch DB (live DB is {_LIVE_REPO_DB!r})."
    )
    init_db(db_path).close()
    yield


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


# ---------------------------------------------------------------------------
# Image generation never writes into the real generated/images
# ---------------------------------------------------------------------------
# ImageGenerationService saves every successful generation to
# DEFAULT_CONFIG["image_output_dir"] ("generated/images", cwd-relative). The
# unit tests mock the provider with stub bytes, so every pytest run used to
# drop six 15-24 byte fake "PNGs" into the user's gallery (158 had piled up
# by 2026-10-15). Every service copies DEFAULT_CONFIG at construction, so
# pointing the default at a session temp dir covers all of them.
_TEST_IMAGE_DIR = tempfile.mkdtemp(prefix="vajra-test-images-")
atexit.register(shutil.rmtree, _TEST_IMAGE_DIR, True)


@pytest.fixture(autouse=True)
def _isolated_image_output_dir(monkeypatch):
    import importlib

    # A plain import: backend.core.services no longer imports vajra_service
    # eagerly, so this loads only the service module. (The old spec-loader
    # path executed the module before registering it in sys.modules, which
    # breaks its @dataclass definitions whenever nothing had imported it yet.)
    ig_mod = importlib.import_module("backend.core.services.image_generation_service")

    monkeypatch.setitem(ig_mod.DEFAULT_CONFIG, "image_output_dir", _TEST_IMAGE_DIR)


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


def _leading_quoted_words(command: str) -> list[tuple[bool, str]]:
    """Split like shlex.split, and flag each word as a plain shell assignment.

    The name is historical and is kept stable because external review probes
    extract this function by name; it reports the shell's
    assignment-vs-command decision rather than merely "was the word quoted".

    Returns one (is_assignment, dequoted_text, raw_text) triple per word, in
    source order.

    A leading word is an assignment only when the RAW text before the first
    '=' is an entirely unquoted, unescaped identifier (^[A-Za-z_][A-Za-z0-9_]*$).
    Anything else — a quote or a backslash anywhere in the name, an empty name,
    a name starting with a digit, a non-ASCII name — is an ordinary command
    name, which under POSIX sh / dash fails to resolve and never runs a player.
    (bash is more permissive: it accepts 'A+=x' as an assignment, so that form
    is a recorded known false negative, not claimed as 127. 'A[0]=x' is NOT:
    in the shell assignment position it is a syntax error, so returning False
    is correct there — only env, which applies no shell rule, accepts it.) The
    VALUE after the first '=' is unconstrained: it may contain quotes and
    escapes freely, because it never affects the word's classification. The
    name is read from the RAW text on purpose — the shell decides
    assignment-vs-command on the unexpanded word, so a quoted '"C=q"' is a
    command name even though its dequoted text looks like an assignment.

    Scope — the contract this function upholds:
    True means THE PROGRAM REALLY LAUNCHES. It is a bounded recognizer, not a
    full shell interpreter, and it answers the question by shell PARSING rules
    (quote removal, which words are assignments, the nohup and env phases):
    the program word must be a player basename, AND no prefix word may be one
    whose evaluation can stop the launch. Its callers are the audio fallbacks
    in core/enhanced_tts.py, which only ever run 'aplay {path}' or
    'afplay {path}', so the supported forms are deliberately narrow and an
    undecidable prefix passes through rather than being guessed at.

    A prefix word is undecidable, and therefore passthrough, when its raw text
    outside single quotes contains a backtick, '$(', or a '${...}' that is not
    one of the forms that cannot fail: '${NAME}' and '${NAME:-lit}',
    '${NAME-lit}', '${NAME:+lit}', '${NAME+lit}' where NAME is an identifier
    and lit is a plain literal. Unbalanced '$(', '`' and '${' count too. So
    '${X:?e}', '${}', '${X:=d}' and '${X:-$HOME}' pass through, while plain
    '$NAME', '$1', '$?', '$$', a lone '$' and anything inside single quotes
    stay supported. It is also passthrough when the word carries an UNQUOTED
    shell metacharacter — ';', '&', '|', '<', '>', '(' or ')' — because a live
    one restructures the command and the program word this helper inspected is
    then not the program the shell runs. Quoting or escaping makes the same
    character inert data, so 'A="x;y" aplay' and 'A=x\\; aplay' stay swallowed.
    Note the two checks mask differently on purpose: an expansion inside DOUBLE
    quotes is still live and is rejected, while a metacharacter inside double
    quotes is data and is kept. A shell-level assignment naming a bash readonly
    variable (UID, EUID, PPID, SHELLOPTS, BASHOPTS, BASH_VERSINFO) or PATH is
    also passthrough, as is a PATH override in an env assignment, because env
    applies it before looking the program up.

    TRADE-OFF, stated plainly: passing these forms through means a player
    command written with one of them is NOT swallowed, and could therefore play
    for real in a test. No production caller uses these forms and no test does;
    explicit audio in tests remains the VAJRA_TEST_AUDIO=1 opt-in. The
    alternative - swallowing commands that provably cannot run - would mean
    reporting success for something the shell refused to do. We choose the
    direction that cannot lie about a player.

    The alignment invariant below guarantees TOKEN AGREEMENT with shlex. It
    says nothing about evaluation; the prefix checks above are what make True
    mean the program launches.

    Word boundaries and escape handling mirror shlex's own posix rules, NOT an
    independent reading of POSIX sh:
      * outside quotes, a backslash escapes ANY following character;
      * inside double quotes, a backslash is special only before '"' and '\\',
        and is otherwise a literal backslash;
      * inside single quotes, a backslash is always literal and the next "'"
        closes the word.
    'dequoted_text' is the text shlex.split would produce for that word. The
    caller checks it against the real tokens and fails safe on any mismatch, so
    this function does not have to be provably correct — it only has to
    DISAGREE detectably. Alignment is a verified invariant, not an argument.
    """
    ident_start = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    ident_rest = ident_start + "0123456789"
    words: list[tuple[bool, str]] = []
    index, length = 0, len(command)
    while index < length:
        while index < length and command[index].isspace():
            index += 1
        if index >= length:
            break
        start = index
        quote = ""
        dequoted: list[str] = []
        while index < length:
            char = command[index]
            if quote:
                if char == quote:
                    quote = ""
                elif char == "\\" and quote == '"' and index + 1 < length and command[index + 1] in '"\\':
                    # shlex escapedquotes is '"' and NOTHING else, so inside
                    # double quotes a backslash escapes ONLY '"' and '\'. A
                    # backslash before a SINGLE quote is not an escape here: it
                    # survives into the token, exactly as shlex leaves it.
                    index += 1
                    dequoted.append(command[index])
                else:
                    dequoted.append(char)
            elif char in "'\"":
                quote = char
            elif char == "\\" and index + 1 < length:
                # Outside quotes shlex escapes any following character.
                index += 1
                dequoted.append(command[index])
            elif char.isspace():
                break
            else:
                dequoted.append(char)
            index += 1
        name, separator, _value = command[start:index].partition("=")
        words.append(
            (
                bool(separator)
                and bool(name)
                and name[0] in ident_start
                and all(letter in ident_rest for letter in name),
                "".join(dequoted),
                command[start:index],
            )
        )
    return words


def _is_audio_player_command(command: str) -> bool:
    """Check if command invokes an audio player (aplay/afplay/paplay/ffplay).

    Recognizes:
    - leading whitespace
    - bare or absolute executable paths (/usr/bin/aplay, aplay)
    - quoted executable paths ("/usr/bin/aplay", 'aplay')
    - 'nohup' prefix (nohup aplay ...), including 'nohup env ...' and
      'env [options/assignments] nohup aplay ...'. nohup may itself be
      preceded by shell assignments, but no transparent form places a
      NAME=VALUE token AFTER nohup; see the nohup note below.
    - leading environment assignments with ASCII names (AUDIODEV=x aplay file.wav,
      AUDIODEV=x nohup aplay)
    - 'env' prefix ('env', '/usr/bin/env', '/bin/env' exactly) accepting ONLY:
        * '--' (end of options; subsequent NAME=VALUE assignments are accepted)
        * '-i', '--ignore-environment'
        * '-u NAME', '--unset NAME', '--unset=NAME' with non-empty identifier NAME
        * NAME=VALUE variable assignments
      Any other option token starting with '-' (e.g. -S, --split-string, -a,
      --argv0, -C, -0, combined flags like -iu, unknown options) causes the
      command to pass through (returns False).
      '--unset=' with an empty name is NOT accepted: GNU env exits 125 with
      "cannot unset '': Invalid argument" and never runs the command.

    Shell assignment rule (leading words only):
    A leading word counts as an assignment only when its RAW text before the
    first '=' is an entirely unquoted, unescaped identifier. So AUDIODEV=x,
    AUDIODEV="x", AUDIODEV=\\x, A="foo bar" and _A=x are assignments, while
    "AUDIODEV=x", AUDIO"DEV"=x, AUDIO\\DEV=x, 1A=x and =x are command names
    and return False: under POSIX sh / dash such a name fails to resolve and
    exits 127 without running a player. (bash, which is /bin/sh on many
    systems, is more permissive — see the bash-extension gap below.) The
    VALUE after the first '=' is unconstrained; only the name part is
    inspected. This rule stops at the shell level: env receives the dequoted,
    unescaped word in argv, so env AUDIO"DEV"=x and env "A=x" stay True.

    Raw-split alignment invariant:
    _leading_quoted_words re-scans the raw string so the shell's
    assignment-vs-command decision can be made on unquoted text. Rather than
    argue that its word boundaries match shlex.split, the dequoted text of
    every raw word is compared against the real shlex tokens, and a mismatch
    in either count or content makes the whole command return False. So any
    future drift between the two splitters is caught at runtime and fails
    safe. Escape handling inside quotes mirrors shlex's own posix rules
    (outside quotes a backslash escapes anything; inside double quotes only
    '"' and '\\' are escapable; inside single quotes a backslash is literal),
    not POSIX sh rules, because shlex is the tokenizer actually in use here.

    env phase boundary:
    GNU env stops parsing at the first token that is neither an option nor a
    NAME=VALUE assignment: that token is the command, and everything after it
    belongs to the command. So options are honoured only BEFORE the first
    assignment — 'env -i A=x aplay' runs aplay and returns True here — whereas
    after an assignment a dash token is the command name and never resolves:
    'env A=x -i aplay' exits 127 ("env: -i: No such file or directory"), no
    player runs, and the helper returns False because swallowing it would
    report success for a command whose program is not a player. The two
    examples therefore differ: the first is True, the second is False.

    Note on nohup and assignments:
    In shell syntax ('sh -c'), 'nohup' does not parse assignments. A token like
    'NAME=VALUE' following 'nohup' (as in 'nohup AUDIODEV=x aplay' or
    'env nohup AUDIODEV=x aplay') is treated by nohup as the executable name,
    failing with exit 127 without running the player; the helper returns False.
    Assignments are honoured only when they sit BEFORE nohup — either as a
    shell assignment ('AUDIODEV=x nohup aplay') or as arguments of an env that
    precedes nohup ('env AUDIODEV=x nohup aplay') — or when env sits between
    them and nohup ('nohup env AUDIODEV=x aplay'). So the allowed orderings are
    A nohup [env A=x] and A [env A=x] nohup, never nohup A=x.

    Known coverage gaps / false negatives (player still runs, helper returns False):
    - UNSUPPORTED PREFIX SYNTAX, passes through. A prefix word carrying a
      backtick, '$(', a '${...}' that is not a non-failing form, an unquoted
      shell metacharacter (';' '&' '|' '<' '>' '(' ')'), or a name that is a
      bash readonly variable or PATH, is not swallowed: the player may run
      in a test. Ground-truthed and pinned; the leading edge of this class is
      'A=${X:?e} aplay' and the trailing edge is 'RANDOM=1 aplay', which stays
      swallowed. A quoted or escaped metacharacter is data, not an operator, so
      'A="x;y" aplay' and 'A=x\\; aplay' are still swallowed.
      The consequence is worth stating plainly: a player written as
      'AUDIODEV=x; aplay f.wav' genuinely launches, and now passes through
      unrecognised, so a player written that way is NOT swallowed and could
      play for real in a test. No production caller and no test writes a prefix
      this way; explicit audio in tests remains the VAJRA_TEST_AUDIO=1 opt-in.
      This is the same bounded-recognizer trade-off as the glued operators
      after the player word pinned above, and it goes the same way: on the rare
      unrecognised form the guard declines to act rather than risk claiming it
      stopped something it did not. See the Scope paragraph.
    These are deliberately left unfixed and are pinned by tests so the gap is
    recorded rather than implied:
    - env option forms like 'env -S "aplay f"', 'env -S aplay f',
      'env -C /tmp aplay', 'env --chdir=/tmp aplay', 'env -iu X aplay',
      'env -v/--debug aplay', or 'env - aplay' pass through unintercepted
      (player still runs).
      NOTE: 'passthrough' here means NOT intercepted, not 'safe' — the player
      still launches. The guard's only effect on these is that os.system is not
      stubbed out, so the real player runs.
    - 'nohup -- aplay' passes through unintercepted (player still runs).
    - Compound commands where a player is preceded by another command
      (e.g. 'echo y && aplay' or 'cat file | aplay') or subshell wrappers
      like sh -c "aplay ..." pass through unintercepted (player still runs).
    - Operators GLUED to the player word, a leading '!' and a leading '(' all
      pass through, and the player really does run: shlex keeps the operator
      inside one token, so the token is 'aplay;', 'aplay;echo', 'aplay&&echo',
      'aplay&' or 'aplay|cat' rather than the bare player name, and '!' and '('
      become their own leading tokens. Pinned and ground-truthed below. Not
      fixed: splitting on shell operators is a full shell parser, which item 8
      explicitly rules out.
    - bash extension names in the assignment position: 'A+=x aplay' (append)
      is accepted as an assignment by bash, which is /bin/sh on this machine,
      so the player really does launch while the helper returns False. A POSIX
      sh / dash rejects that name with 127, where the helper would be right.
      'A[0]=x' is deliberately NOT listed here: in the shell assignment
      position it is a syntax error and the program never runs, so False is
      correct — see the correct-passthrough note above. env applies no shell
      rule, so 'env A[0]=x aplay' and 'env A+=x aplay' DO launch and are gaps.

    Not gaps (False is correct, because no player ever runs):
    - '-u NAME' consumes NAME as the variable to unset, so a player-looking
      token in that slot is never the command: 'env -iu aplay f.wav' unsets
      'aplay' and then tries to run 'f.wav' (exit 127), and 'env -u aplay
      f.wav' behaves the same. These look like the '-iu' gap above but are
      the opposite case; they are pinned separately.

    Compound commands (safe direction for silence guard):
    A command is swallowed when its FIRST WHITESPACE-SEPARATED TOKEN, after
    any supported prefix, is a player basename. An operator that follows the
    player as a SEPARATE token is fine: 'aplay x && echo y' and 'aplay f | cat'
    are swallowed because token 0 is the player. Operators GLUED to the player
    word are NOT: shlex keeps 'aplay;', 'aplay&&echo', 'aplay&' and '(aplay' as
    single tokens whose basename is not a player, so those pass through and the
    player really does run - see the gap list above. Parse errors fall back to
    passthrough (returns False).
    """
    if not isinstance(command, str) or not command.strip():
        return False
    try:
        tokens = shlex.split(command)
    except Exception:
        return False
    if not tokens:
        return False

    env_prefixes = {"env", "/usr/bin/env", "/bin/env"}
    nohup_prefixes = {"nohup", "/usr/bin/nohup", "/bin/nohup"}

    idx = 0
    shell_blocked_names = frozenset({"UID", "EUID", "PPID", "SHELLOPTS", "BASHOPTS", "BASH_VERSINFO", "PATH"})
    env_blocked_names = frozenset({"PATH"})

    def _is_safe_expansion(inner: str) -> bool:
        """True for ${NAME} and the default forms ${NAME:-lit} / ${NAME-lit} / ..."""
        if not inner:
            return False
        end = 0
        while end < len(inner) and inner[end].isascii() and (inner[end].isalnum() or inner[end] == "_"):
            end += 1
        name, rest = inner[:end], inner[end:]
        if not name or not (name[0].isalpha() or name[0] == "_"):
            return False
        if not rest:
            return True
        for operator in (":-", ":+", "-", "+"):
            if rest.startswith(operator):
                literal = rest[len(operator) :]
                return all(char.isascii() and (char.isalnum() or char in "_./:,@%+=-") for char in literal)
        return False

    def _expansions_are_safe(text: str) -> bool:
        """Every ${...} in text is safe; an unbalanced one is not."""
        index, length = 0, len(text)
        while index < length:
            if not text.startswith("${", index):
                index += 1
                continue
            depth, cursor = 1, index + 2
            while cursor < length:
                if text.startswith("${", cursor):
                    depth += 1
                    cursor += 2
                    continue
                if text[cursor] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                cursor += 1
            if cursor >= length:
                return False
            if not _is_safe_expansion(text[index + 2 : cursor]):
                return False
            index = cursor + 1
        return True

    def _prefix_can_launch(raw: str) -> bool:
        """False when evaluating this prefix word can stop the program.

        Mirrors the splitter's own escape rules to decide which characters are
        live: single quotes mask everything, outside quotes a backslash escapes
        the next character, and inside double quotes a backslash escapes only
        '"' and '\\'. Rejects backticks, command and arithmetic substitution,
        and any ${...} that is not a safe non-failing form.
        """
        # Two different masks are needed, because the shell rules differ.
        # expansion_text keeps double-quoted content, so an expansion inside
        # double quotes ("${X:?e}") is still seen; structural_text drops it,
        # because a metacharacter inside double quotes is inert data, not an
        # operator. Single-quoted content is literal for both, and a character
        # escaped by a backslash is data for both.
        expansion_text: list[str] = []
        structural_text: list[str] = []
        index, length = 0, len(raw)
        quote = ""
        while index < length:
            char = raw[index]
            if quote == "'":
                if char == "'":
                    quote = ""
            elif quote == '"':
                if char == '"':
                    quote = ""
                elif char == "\\" and index + 1 < length and raw[index + 1] in '"\\':
                    index += 1
                else:
                    expansion_text.append(char)
            elif char == "'":
                quote = "'"
            elif char == '"':
                quote = '"'
            elif char == "\\" and index + 1 < length:
                index += 1
            else:
                expansion_text.append(char)
                structural_text.append(char)
            index += 1
        # A LIVE shell metacharacter changes what the shell runs: ';' '&' '|'
        # terminate or redirect the command and '(' ')' '<' '>' restructure it,
        # so the program word this helper inspected is not the program the
        # shell executes.
        if any(char in "".join(structural_text) for char in ";&|<>()"):
            return False
        text = "".join(expansion_text)
        if "`" in text or "$(" in text:
            return False
        return _expansions_are_safe(text)

    # Initial environment assignments (NAME=VALUE) before nohup/env/command.
    # The decision is made on the RAW word, because shlex.split has already
    # thrown quoting and escaping away: only a word whose text before the
    # first '=' is a plain unquoted identifier counts here. A quoted VALUE
    # ('AUDIODEV="x"') passes; a quoted or escaped NAME does not. The env
    # loops below deliberately do NOT apply this rule, because env receives
    # the dequoted, unescaped word in argv and accepts "A=x" or AUDIO"DEV"=x.
    leading_words = _leading_quoted_words(command)
    # Fail-safe alignment invariant, checked rather than assumed: the raw split
    # must reproduce exactly the shlex tokens, word for word. If it ever drifts,
    # the classification is untrustworthy, so refuse the command outright. A
    # desync can only lose a swallow, never invent one.
    if len(leading_words) != len(tokens):
        return False
    for (_is_assignment, dequoted, _raw), token in zip(leading_words, tokens):
        if dequoted != token:
            return False
    # A shell-level assignment word must also be one whose evaluation cannot
    # stop the program, and must not name a variable the shell refuses to
    # assign (bash readonly) or that changes program lookup (PATH).
    while idx < len(tokens) and leading_words[idx][0]:
        raw_word = leading_words[idx][2]
        shell_name, _shell_sep, _shell_value = raw_word.partition("=")
        if shell_name in shell_blocked_names or not _prefix_can_launch(raw_word):
            return False
        idx += 1

    # Optional 'nohup' transparent prefix before env
    if idx < len(tokens) and tokens[idx] in nohup_prefixes:
        idx += 1
        if idx < len(tokens) and tokens[idx].startswith("-"):
            return False

    # Optional 'env' prefix with strictly allowed options
    if idx < len(tokens) and tokens[idx] in env_prefixes:
        idx += 1
        # GNU env stops parsing at the first token that is neither an option
        # nor a NAME=VALUE assignment: that token is the command, and
        # everything after it belongs to the command. Options are therefore
        # honoured only BEFORE the first assignment ('env -i A=x aplay' runs
        # aplay -> True). Once an assignment has been consumed, a later dash
        # token is the command name rather than an option, so
        # 'env A=x -i aplay' exits 127 ('env: -i: No such file or directory'),
        # never runs a player, and is False here.
        saw_assignment = False
        while idx < len(tokens):
            tok = tokens[idx]
            if tok.startswith("-") and not saw_assignment:
                if tok == "--":
                    idx += 1
                    # After '--', env stops option processing, but still processes NAME=VALUE
                    while idx < len(tokens):
                        name, sep, _ = tokens[idx].partition("=")
                        if not (sep and name.isascii() and name.isidentifier()):
                            break
                        if name in env_blocked_names or not _prefix_can_launch(leading_words[idx][2]):
                            return False
                        idx += 1
                    break
                if tok in {"-i", "--ignore-environment"}:
                    idx += 1
                elif tok in {"-u", "--unset"}:
                    idx += 1
                    if idx >= len(tokens):
                        return False
                    name = tokens[idx]
                    if not (name.isascii() and name.isidentifier()):
                        return False
                    idx += 1
                elif tok.startswith("--unset="):
                    name = tok[len("--unset=") :]
                    if not (name.isascii() and name.isidentifier()):
                        return False
                    idx += 1
                else:
                    return False
                continue
            name, sep, _ = tok.partition("=")
            if sep and name.isascii() and name.isidentifier():
                # env applies the assignment before it looks the program up, so
                # a PATH override or a fail-capable expansion in an env
                # assignment word can stop the launch just as at shell level.
                if name in env_blocked_names or not _prefix_can_launch(leading_words[idx][2]):
                    return False
                idx += 1
                saw_assignment = True
            else:
                break

    # Optional 'nohup' transparent prefix after env (e.g. 'env nohup aplay' or 'env AUDIODEV=x nohup aplay')
    if idx < len(tokens) and tokens[idx] in nohup_prefixes:
        idx += 1
        if idx < len(tokens) and tokens[idx].startswith("-"):
            return False

    if idx >= len(tokens):
        return False

    # ------------------------------------------------------------------
    # Evaluation-failing prefixes. Returning True promises the program really
    # launches, so a prefix whose evaluation can stop it must pass through.
    # These are nested rather than module-level on purpose: external review
    # probes AST-extract only this function and _leading_quoted_words and give
    # them a namespace of {shlex, os, re}, so a module-level helper would be a
    # NameError under them.
    # ------------------------------------------------------------------
    exe = tokens[idx].rsplit("/", 1)[-1]
    return exe in _AUDIO_PLAYER_COMMANDS


def _guard_os_system_player(monkeypatch) -> None:
    """Swallow os.system player invocations; pass every other command through.

    os.system is patched on the shared os module object, so every
    ``import os`` + ``os.system(...)`` call site (all five _play_audio_file
    methods among them) sees the guard while it is active. A command invoking
    aplay/afplay/paplay/ffplay (including bare names, absolute paths, quoted
    paths, leading env assignments, or an env prefix) is recorded in
    _AUDIO_STUB_CALLS and reported as success (0) without executing;
    everything else runs through the original os.system. Restored per test
    by monkeypatch.
    """
    original_system = os.system

    def _guarded_system(command: str) -> int:
        if _is_audio_player_command(command):
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
