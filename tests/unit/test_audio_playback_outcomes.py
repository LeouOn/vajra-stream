"""Mocked, offline coverage for the live audio-playback checks (ITEM 6).

``tests/unit/test_audio_playback.py`` contains three opt-in ``@pytest.mark.slow``
checks (``test_audio_generate``, ``test_audio_playback``, ``test_audio_status``)
plus a ``main()`` runner that hit a LIVE backend on localhost:8008. An earlier
repair cycle fixed their outcome handling (ConnectionError -> skip, non-200 /
bad body / timeout -> fail, KeyboardInterrupt/SystemExit escape ``main()``).
These tests pin that repaired behaviour OFFLINE so future edits cannot quietly
restore false passes — without a server, network or DB.

Approach:
  * the live module is imported as a MODULE OBJECT (importlib by path, never
    ``from ... import test_audio_generate``), so its live functions are not
    collected into this namespace;
  * strict network guards are active BEFORE and during all imports and tests;
    ``requests.Session.request`` and raw ``socket`` connects are forbidden outright;
  * unrestricted environment-driven overrides (``VAJRA_AUDIO_OUTCOMES_TARGET``)
    have been removed to eliminate arbitrary execution in CI;
  * success bodies match the exact wire schemas returned by
    ``backend/app/api/v1/endpoints/audio.py``.

These tests are deliberately NOT marked slow and run under ``-m "not slow"``.
"""

import importlib.util
import json
import socket
import sys
from pathlib import Path

import pytest
import requests

REPO_TARGET = Path(__file__).with_name("test_audio_playback.py").resolve()

GENERATE_URL = "http://localhost:8008/api/v1/audio/generate"
PLAY_URL = "http://localhost:8008/api/v1/audio/play"
STATUS_URL = "http://localhost:8008/api/v1/audio/status"

# Real success bodies matching backend/app/api/v1/endpoints/audio.py
# (generate ~L71-84, play ~L168-174, status ~L265-271).
GOOD_GENERATE_BODY = {
    "status": "success",
    "message": "Audio generation completed",
    "config": {
        "frequency": 528,
        "duration": 5,
        "volume": 0.8,
        "prayer_bowl_mode": True,
        "harmonic_strength": 0.3,
        "modulation_depth": 0.05,
    },
    "audio_generated": True,
    "samples": 220500,
}

GOOD_PLAY_BODY = {
    "status": "success",
    "message": "Audio playback started",
    "hardware_level": 2,
    "audio_duration": 5.0,
    "audio_samples": 220500,
}

GOOD_STATUS_BODY = {
    "status": "success",
    "has_audio": True,
    "audio_duration": 5.0,
    "spectrum_available": False,
    "timestamp": 12345.678,
}

# Valid idle status when no audio has been generated yet
GOOD_STATUS_NO_AUDIO_BODY = {
    "status": "success",
    "has_audio": False,
    "audio_duration": 0.0,
    "spectrum_available": False,
    "timestamp": 12345.678,
}

_ORIGINAL_SOCKET_CONNECT = socket.socket.connect
_ORIGINAL_SOCKET_CONNECT_EX = socket.socket.connect_ex
_ORIGINAL_SESSION_REQUEST = requests.Session.request
_ORIGINAL_POST = requests.post
_ORIGINAL_GET = requests.get


class ForbiddenNetwork(Exception):
    """Raised when an unauthorized network or socket operation is attempted."""


def _network_guards_active() -> bool:
    """Verify that socket connects and requests methods are currently intercepted."""
    return (
        socket.socket.connect is not _ORIGINAL_SOCKET_CONNECT
        and socket.socket.connect_ex is not _ORIGINAL_SOCKET_CONNECT_EX
        and requests.Session.request is not _ORIGINAL_SESSION_REQUEST
        and requests.post is not _ORIGINAL_POST
        and requests.get is not _ORIGINAL_GET
    )


def load_target(target_path: Path = REPO_TARGET) -> object:
    """Load the target module as a module object with mandatory network guards.

    Unrestricted environment-driven execution (VAJRA_AUDIO_OUTCOMES_TARGET) has been
    removed to eliminate arbitrary code execution in CI. Network guards MUST be active
    prior to any module import.
    """
    if not _network_guards_active():
        raise ForbiddenNetwork("Cannot load target module without active network guards")

    resolved_path = Path(target_path).resolve()
    assert resolved_path.is_file(), f"target path does not exist: {resolved_path}"
    assert resolved_path.suffix == ".py", f"target path must be a Python file: {resolved_path}"

    spec = importlib.util.spec_from_file_location("audio_playback_under_test", resolved_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, status_code=200, json_body=None, text="", json_exc=None):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self._json_exc = json_exc

    def json(self):
        if self._json_exc is not None:
            raise self._json_exc
        if self._json_body is not None:
            return self._json_body
        raise json.JSONDecodeError("Expecting value", self.text or "", 0)


@pytest.fixture(autouse=True)
def enforce_network_guard(monkeypatch):
    """Enforce strict network blocking for EVERY test in this module by default."""

    def _forbid_session_request(*args, **kwargs):
        raise ForbiddenNetwork("requests.Session.request reached")

    def _forbid_connect(self, address):
        raise ForbiddenNetwork(f"socket connect reached: {address}")

    def _unhandled_post(url, **kwargs):
        raise ForbiddenNetwork(f"Unhandled POST request reached: {url}")

    def _unhandled_get(url, **kwargs):
        raise ForbiddenNetwork(f"Unhandled GET request reached: {url}")

    monkeypatch.setattr(requests.Session, "request", _forbid_session_request)
    monkeypatch.setattr(socket.socket, "connect", _forbid_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _forbid_connect)
    monkeypatch.setattr(requests, "post", _unhandled_post)
    monkeypatch.setattr(requests, "get", _unhandled_get)


@pytest.fixture()
def recorded():
    """Every HTTP attempt the module under test makes, in order."""
    return []


@pytest.fixture()
def guard(recorded, monkeypatch):
    """Provide a mechanism to install mock HTTP endpoint behaviors."""

    def install(behavior):
        """behavior(url) -> FakeResponse or an exception instance to raise."""

        def fake_post(url, **kwargs):
            recorded.append(("POST", url))
            outcome = behavior(url)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        def fake_get(url, **kwargs):
            recorded.append(("GET", url))
            outcome = behavior(url)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        monkeypatch.setattr(requests, "post", fake_post)
        monkeypatch.setattr(requests, "get", fake_get)

    return install


def ok_for(url):
    """A behavior returning the documented success body for each endpoint."""
    body_by_url = {
        GENERATE_URL: GOOD_GENERATE_BODY,
        PLAY_URL: GOOD_PLAY_BODY,
        STATUS_URL: GOOD_STATUS_BODY,
    }
    return lambda u: FakeResponse(200, json_body=body_by_url[u])


CHECKS = ("generate", "playback", "status")


def target_check(module, name):
    check_func_name = {
        "generate": "test_audio_generate",
        "playback": "test_audio_playback",
        "status": "test_audio_status",
    }[name]
    return getattr(module, check_func_name)


def run_check(module, name):
    """Call the live check through a wrapper so it is never collected as ours."""
    target_check(module, name)()


class TestSuccessPaths:
    @pytest.mark.parametrize("name", CHECKS)
    def test_correct_endpoint_shaped_body_passes(self, guard, name):
        guard(ok_for(None))
        run_check(load_target(), name)  # must not raise

    def test_status_no_audio_state_passes(self, guard):
        """Valid idle status when no audio is currently loaded passes."""
        guard(lambda u: FakeResponse(200, json_body=GOOD_STATUS_NO_AUDIO_BODY) if u == STATUS_URL else None)
        run_check(load_target(), "status")

    def test_status_with_spectrum_available_passes(self, guard):
        """Valid status when spectrum is available passes."""
        body = dict(GOOD_STATUS_BODY, spectrum_available=True)
        guard(lambda u: FakeResponse(200, json_body=body) if u == STATUS_URL else None)
        run_check(load_target(), "status")

    def test_all_three_checks_hit_their_own_endpoints(self, guard, recorded):
        guard(
            lambda u: FakeResponse(
                200,
                json_body={
                    GENERATE_URL: GOOD_GENERATE_BODY,
                    PLAY_URL: GOOD_PLAY_BODY,
                    STATUS_URL: GOOD_STATUS_BODY,
                }[u],
            )
        )
        module = load_target()
        for name in CHECKS:
            run_check(module, name)
        assert [r[1] for r in recorded] == [GENERATE_URL, PLAY_URL, STATUS_URL]


class TestBodyFailures:
    """A 200 with a wrong body must FAIL, not pass."""

    BAD_BODIES = {
        "empty_object": {},
        "error_envelope": {"status": "error", "detail": "boom"},
        "detail_only": {"detail": "not found"},
        "non_object_json_array": [1, 2, 3],
    }

    @pytest.mark.parametrize("name", CHECKS)
    @pytest.mark.parametrize("body_name", list(BAD_BODIES))
    def test_bad_body_fails(self, guard, name, body_name):
        url = {"generate": GENERATE_URL, "playback": PLAY_URL, "status": STATUS_URL}[name]
        guard(lambda u: FakeResponse(200, json_body=self.BAD_BODIES[body_name]) if u == url else None)
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), name)

    @pytest.mark.parametrize("name", CHECKS)
    @pytest.mark.parametrize("exc_name", ["json_decode_error", "requests_decode_error"])
    def test_decode_exception_fails(self, guard, name, exc_name):
        url = {"generate": GENERATE_URL, "playback": PLAY_URL, "status": STATUS_URL}[name]
        exc = (
            json.JSONDecodeError("Expecting value", "<no body>", 0)
            if exc_name == "json_decode_error"
            else requests.exceptions.JSONDecodeError("Expecting value", "<no body>", 0)
        )
        guard(lambda u: FakeResponse(200, text="not json", json_exc=exc) if u == url else None)
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), name)

    @pytest.mark.parametrize("name", CHECKS)
    def test_http_500_fails(self, guard, name):
        url = {"generate": GENERATE_URL, "playback": PLAY_URL, "status": STATUS_URL}[name]
        guard(lambda u: FakeResponse(500, text="server error") if u == url else None)
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), name)

    @pytest.mark.parametrize("name", CHECKS)
    @pytest.mark.parametrize("status_code", [400, 404, 502, 503])
    def test_http_client_and_server_error_codes_fail(self, guard, name, status_code):
        url = {"generate": GENERATE_URL, "playback": PLAY_URL, "status": STATUS_URL}[name]
        guard(lambda u: FakeResponse(status_code, text=f"error {status_code}") if u == url else None)
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), name)


class TestSuccessFieldMismatches:
    """Well-shaped 200 bodies with wrong values must FAIL."""

    def test_generate_wrong_audio_generated(self, guard):
        body = dict(GOOD_GENERATE_BODY, audio_generated=False)
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "generate")

    def test_generate_wrong_status_value(self, guard):
        body = dict(GOOD_GENERATE_BODY, status="pending")
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "generate")

    @pytest.mark.parametrize("missing_key", ["status", "message", "config", "audio_generated", "samples"])
    def test_generate_missing_required_keys_fails(self, guard, missing_key):
        body = dict(GOOD_GENERATE_BODY)
        del body[missing_key]
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "generate")

    def test_playback_wrong_hardware_level_echo(self, guard):
        body = dict(GOOD_PLAY_BODY, hardware_level=3)  # request sent 2
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "playback")

    def test_playback_wrong_status_value(self, guard):
        body = dict(GOOD_PLAY_BODY, status="failed")
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "playback")

    @pytest.mark.parametrize("missing_key", ["status", "message", "hardware_level", "audio_duration", "audio_samples"])
    def test_playback_missing_required_keys_fails(self, guard, missing_key):
        body = dict(GOOD_PLAY_BODY)
        del body[missing_key]
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "playback")

    def test_status_wrong_status_value(self, guard):
        body = dict(GOOD_STATUS_BODY, status="error")
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "status")

    @pytest.mark.parametrize(
        "missing_key", ["status", "has_audio", "audio_duration", "spectrum_available", "timestamp"]
    )
    def test_status_missing_required_keys_fails(self, guard, missing_key):
        body = dict(GOOD_STATUS_BODY)
        del body[missing_key]
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "status")

    @pytest.mark.parametrize("field", ["has_audio", "spectrum_available"])
    @pytest.mark.parametrize("bad", ["yes", 1, None])
    def test_status_wrong_bool_types(self, guard, field, bad):
        body = dict(GOOD_STATUS_BODY, **{field: bad})
        guard(lambda u: FakeResponse(200, json_body=body))
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), "status")


class TestTransportOutcomes:
    @pytest.mark.parametrize("name", CHECKS)
    def test_connection_error_skips(self, guard, name):
        url = {"generate": GENERATE_URL, "playback": PLAY_URL, "status": STATUS_URL}[name]
        guard(lambda u: requests.exceptions.ConnectionError("refused") if u == url else None)
        with pytest.raises(pytest.skip.Exception):
            run_check(load_target(), name)

    @pytest.mark.parametrize("name", CHECKS)
    def test_timeout_fails(self, guard, name):
        url = {"generate": GENERATE_URL, "playback": PLAY_URL, "status": STATUS_URL}[name]
        guard(lambda u: requests.exceptions.Timeout("too slow") if u == url else None)
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), name)

    @pytest.mark.parametrize("name", CHECKS)
    def test_other_request_exception_fails(self, guard, name):
        url = {"generate": GENERATE_URL, "playback": PLAY_URL, "status": STATUS_URL}[name]
        guard(lambda u: requests.exceptions.InvalidURL("bad url") if u == url else None)
        with pytest.raises(pytest.fail.Exception):
            run_check(load_target(), name)


class TestMainRunner:
    def test_main_returns_0_when_all_checks_pass(self, guard):
        guard(ok_for(None))
        assert load_target().main() == 0

    def test_main_returns_1_when_a_check_fails(self, guard):
        def behavior(url):
            if url == PLAY_URL:
                return FakeResponse(500, text="boom")
            return FakeResponse(
                200,
                json_body={
                    GENERATE_URL: GOOD_GENERATE_BODY,
                    STATUS_URL: GOOD_STATUS_BODY,
                }[url],
            )

        guard(behavior)
        assert load_target().main() == 1

    def test_main_returns_1_and_labels_skip_when_backend_is_down(self, guard, capsys):
        guard(lambda u: requests.exceptions.ConnectionError("refused"))
        module = load_target()
        assert module.main() == 1  # SKIPPED is not PASSED
        out = capsys.readouterr().out
        assert "SKIPPED" in out
        assert "ALL TESTS PASSED" not in out

    def test_main_returns_1_when_one_check_skips_and_others_pass(self, guard):
        def behavior(url):
            if url == GENERATE_URL:
                return requests.exceptions.ConnectionError("refused")
            return FakeResponse(
                200,
                json_body={
                    PLAY_URL: GOOD_PLAY_BODY,
                    STATUS_URL: GOOD_STATUS_BODY,
                }[url],
            )

        guard(behavior)
        assert load_target().main() == 1

    @pytest.mark.parametrize("escape_exc", [KeyboardInterrupt, SystemExit])
    def test_keyboard_interrupt_and_system_exit_escape_main_before_later_requests(self, guard, recorded, escape_exc):
        guard(lambda u: escape_exc("interrupted") if u == GENERATE_URL else None)
        module = load_target()
        with pytest.raises(escape_exc):
            module.main()
        # Only the first check ran; playback/status requests were never made.
        assert [r[1] for r in recorded] == [GENERATE_URL]


class TestModuleIsolation:
    def test_live_functions_are_not_collected_into_this_namespace(self, guard):
        guard(lambda u: pytest.fail(f"unexpected request during isolation check: {u}"))
        module = load_target()
        # The target's functions exist on the module object...
        assert callable(module.test_audio_generate)
        assert callable(module.test_audio_playback)
        assert callable(module.test_audio_status)
        # ...but this module never exposes them at its own top level.
        for name in ("test_audio_generate", "test_audio_playback", "test_audio_status"):
            assert not hasattr(sys.modules[__name__], name)


class TestNetworkGuardEnforcement:
    """Verify that network blocking is strictly enforced before and during execution."""

    def test_load_target_fails_when_network_guard_inactive(self, monkeypatch):
        monkeypatch.setattr(requests, "post", _ORIGINAL_POST)
        with pytest.raises(ForbiddenNetwork, match="active network guards"):
            load_target()

    def test_unhandled_post_raises_forbidden_network(self):
        with pytest.raises(ForbiddenNetwork, match="Unhandled POST request"):
            requests.post("http://localhost:8008/api/v1/audio/generate", timeout=1)

    def test_unhandled_get_raises_forbidden_network(self):
        with pytest.raises(ForbiddenNetwork, match="Unhandled GET request"):
            requests.get("http://localhost:8008/api/v1/audio/status", timeout=1)

    def test_session_request_raises_forbidden_network(self):
        with pytest.raises(ForbiddenNetwork, match="Session.request reached"):
            requests.Session().request("GET", "http://localhost:8008/api/v1/audio/status")

    def test_raw_socket_connect_raises_forbidden_network(self):
        sock = socket.socket()
        try:
            with pytest.raises(ForbiddenNetwork, match="socket connect reached"):
                sock.connect(("127.0.0.1", 8008))
        finally:
            sock.close()

    def test_import_time_network_request_is_blocked(self, tmp_path):
        bad_module = tmp_path / "bad_network_module.py"
        bad_module.write_text("import requests\nrequests.get('http://localhost:8008/api/v1/audio/status')\n")
        with pytest.raises(ForbiddenNetwork, match="Unhandled GET request"):
            load_target(bad_module)

    def test_import_time_socket_connect_is_blocked(self, tmp_path):
        bad_module = tmp_path / "bad_socket_module.py"
        bad_module.write_text("import socket\nsock = socket.socket()\nsock.connect(('127.0.0.1', 8008))\n")
        with pytest.raises(ForbiddenNetwork, match="socket connect reached"):
            load_target(bad_module)


class TestDiscriminationAgainstWeakenedChecks:
    """Verify that these outcome tests discriminate against weakened implementations."""

    def test_weakened_check_returning_bool_is_rejected_by_failure_assertions(self, tmp_path):
        # A weakened implementation (like the legacy 51ca54c revision) that returns False
        # instead of raising pytest.fail.Exception must cause outcome tests to fail.
        weakened_module_path = tmp_path / "weakened_test.py"
        weakened_module_path.write_text(
            "def test_audio_generate():\n    return False\n\n"
            "def test_audio_playback():\n    return False\n\n"
            "def test_audio_status():\n    return False\n"
        )
        weakened_module = load_target(weakened_module_path)
        with pytest.raises(pytest.fail.Exception):
            # If run_check returns False without raising pytest.fail.Exception,
            # this inner pytest.raises will fail with pytest.fail.Exception ("DID NOT RAISE")
            with pytest.raises(pytest.fail.Exception):
                run_check(weakened_module, "generate")
