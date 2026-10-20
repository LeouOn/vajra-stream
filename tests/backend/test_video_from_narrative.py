# tests/backend/test_video_from_narrative.py
"""POST /api/v1/videos/from-narrative — the paid-task-must-not-be-orphaned contract.

Background
----------
``VideoGenerationService.submit_task`` is ``async def (...) -> str`` and returns the
task id as a plain string. This endpoint used to build its response with ``**result``,
which raises ``TypeError: 'str' object is not a mapping``. That happened AFTER the
MiniMax task had already been submitted: the caller got HTTP 500, the task id was
discarded, and a paid generation could never be polled. The sibling ``POST
/api/v1/videos/generate`` documents returning ``task_id``; this file pins the same
contract here.

Offline: the service and the LLM registry are both fakes. No network, no real video
API, no paid task, no audio.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/videos/from-narrative"

# Comfortably over the endpoint's own 50-character minimum.
NARRATIVE = (
    "May all beings be free from suffering, and may every heart find its "
    "own quiet centre in the turning of the seasons."
)


class _FakeProvider:
    """Stands in for a core.llm provider. Never touches the network."""

    def __init__(self, content: str = "A slow push in through incense smoke over still water."):
        self._content = content
        self.calls = 0

    async def generate(self, chat_req):  # noqa: ANN001 - mirrors the provider interface
        self.calls += 1

        class _Response:
            pass

        response = _Response()
        response.content = self._content
        return response


class _FakeRegistry:
    """The endpoint requires ``len(registry) > 0`` and an awaitable ``pick_best``."""

    def __init__(self, provider: _FakeProvider):
        self._provider = provider

    def __len__(self) -> int:
        return 1

    async def pick_best(self):
        return self._provider


class _FakeService:
    """Video service double.

    ``submit_task`` is async and returns a plain string, exactly like the real
    ``VideoGenerationService.submit_task``. That is the whole point of the regression.

    ``default_model`` defaults to ``T2V-01``, NOT ``MiniMax-H3``, because that is what
    the real service ships (video_generation_service.py DEFAULT_CONFIG). Using H3 here
    would have masked the pollability bug this file also covers: ``T2V-01`` is
    ``api_version v1`` and ``MiniMax-H3`` is ``v2``, and ``poll_task`` builds a
    different URL per version, so a response that omits the model leaves the client
    guessing H3 and polling the wrong endpoint for a v1 task.
    """

    def __init__(
        self,
        task_id: str = "task-123",
        error: Exception | None = None,
        default_model: str = "T2V-01",
        default_duration: int = 6,
    ):
        self.task_id = task_id
        self.error = error
        self.config = {
            "enabled": True,
            "default_model": default_model,
            # Mirrors DEFAULT_CONFIG["default_duration"] (6), not a convenient 5:
            # T2V-01 supports durations [6] only, so a fake claiming 5 would let a
            # duration-selection bug pass unnoticed.
            "default_duration": default_duration,
            "default_resolution": "720P",
            "default_ratio": "16:9",
        }
        self.submit_calls: list[dict] = []

    async def submit_task(self, prompt: str, model=None, duration=None, resolution=None, ratio=None, **kwargs) -> str:  # noqa: ANN001
        self.submit_calls.append(
            {"prompt": prompt, "model": model, "duration": duration, "resolution": resolution, "ratio": ratio}
        )
        if self.error is not None:
            raise self.error
        return self.task_id


@pytest.fixture(autouse=True)
def _never_run_real_watcher(monkeypatch):
    """Endpoint arms a background completion watcher after every paid submission.

    The real one polls MiniMax and downloads, so it must never run under pytest.
    Patched for the whole module so no test can leak a live background task; the
    tests that assert on arming install their own recorder over the top.
    """
    from backend.app.api.v1.endpoints import video_generation

    async def _silent_watch(service, task_id, model):  # noqa: ANN001
        return None

    monkeypatch.setattr(video_generation, "_watch_video_task", _silent_watch)


def _install(monkeypatch, service: _FakeService, provider: _FakeProvider | None = None):
    from backend.app.api.v1.endpoints import video_generation
    from backend.app.main import app

    monkeypatch.setattr(video_generation, "get_service", lambda: service)
    provider = provider or _FakeProvider()
    monkeypatch.setattr(app.state, "llm_registry", _FakeRegistry(provider), raising=False)
    return TestClient(app), provider


# --------------------------------------------------------------------------- #
# The regression itself.
# --------------------------------------------------------------------------- #
def test_from_narrative_returns_task_id_instead_of_crashing(monkeypatch):
    """RED for the reported defect: ``**result`` on a str raised TypeError -> HTTP 500."""
    service = _FakeService(task_id="task-123")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE, "genre": "healing"})

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["task_id"] == "task-123", f"task id lost; the paid task is now orphaned and unpolleable: {body}"
    assert body["status"] == "success"
    assert body["narrative_genre"] == "healing"
    assert body["video_prompt"]


def test_from_narrative_never_raises_after_a_successful_submission(monkeypatch):
    """Response assembly must not be able to orphan a task that was already paid for.

    ``finalize_image_prompt`` is the seam: we hand back a hostile ``str`` subclass
    whose ``__getitem__`` raises, so ``video_prompt[:500]`` explodes *after* the task
    has been submitted.
    """
    from backend.app.api.v1.endpoints import video_generation

    class _Hostile(str):
        def __getitem__(self, item):
            raise RuntimeError("response assembly exploded after submission")

    monkeypatch.setattr(video_generation, "finalize_image_prompt", lambda *a, **k: _Hostile("x" * 200))

    service = _FakeService(task_id="task-123")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE, "genre": "healing"})

    assert (
        resp.status_code == 200
    ), f"raised after a paid submission was made; the task id is unrecoverable: {resp.text}"
    assert resp.json()["task_id"] == "task-123"


# --------------------------------------------------------------------------- #
# Happy path via narrative_id (outlook DB lookup).
# --------------------------------------------------------------------------- #
def test_from_narrative_with_narrative_id_reads_the_outlook_row(monkeypatch):
    from backend.app.api.v1.endpoints import outlook

    class _FakeCursor:
        def execute(self, *args):
            self.statement = args[0]

        def fetchone(self):
            return {
                "content": NARRATIVE,
                "genre": "protection",
                "entities_invoked": "bodhisattva of compassion",
                "divination_context": "tibetan",
            }

    class _FakeConn:
        def __init__(self):
            self.cursor_obj = _FakeCursor()
            self.closed = False

        def cursor(self):
            return self.cursor_obj

        def close(self):
            self.closed = True

    conn = _FakeConn()
    monkeypatch.setattr(outlook, "get_db_connection", lambda: conn)

    service = _FakeService(task_id="task-999")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative_id": 7})

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["task_id"] == "task-999"
    assert body["narrative_genre"] == "protection"
    assert conn.closed, "the outlook connection must be closed"


def test_from_narrative_missing_narrative_id_is_404(monkeypatch):
    from backend.app.api.v1.endpoints import outlook

    class _FakeCursor:
        def execute(self, *args):
            pass

        def fetchone(self):
            return None

    class _FakeConn:
        def cursor(self):
            return _FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(outlook, "get_db_connection", lambda: _FakeConn())
    client, _ = _install(monkeypatch, _FakeService())

    resp = client.post(ENDPOINT, json={"narrative_id": 4242})

    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Existing behaviour that must be preserved.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (RuntimeError("daily cost cap reached"), 400),
        (ValueError("duration 17 is not valid for this model"), 422),
    ],
    ids=["runtime-error-400", "value-error-422"],
)
def test_from_narrative_maps_service_errors(monkeypatch, error, expected_status):
    service = _FakeService(error=error)
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})

    assert resp.status_code == expected_status, f"got {resp.status_code}: {resp.text}"


def test_from_narrative_rejects_short_narrative_before_submitting(monkeypatch):
    service = _FakeService()
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": "too short"})

    assert resp.status_code == 400
    assert service.submit_calls == [], "nothing may be submitted for a rejected narrative"


def test_from_narrative_respects_the_disabled_config(monkeypatch):
    service = _FakeService()
    service.config = {"enabled": False}
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})

    assert resp.status_code == 400
    assert service.submit_calls == []


def test_one_submit_task_call_per_request(monkeypatch):
    """Exactly one paid submission per request.

    This does NOT prove retry safety. Two identical requests are two independent paid
    submissions, by design: deduplicating them is a learner decision, not a fact. See
    needs-learner-decision in the fix notes.
    """
    service = _FakeService(task_id="task-123")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})

    assert resp.status_code == 200
    assert len(service.submit_calls) == 1, f"expected one paid submission, got {service.submit_calls}"


# --------------------------------------------------------------------------- #
# Response-shape compatibility with the sibling /generate route.
# --------------------------------------------------------------------------- #
def test_from_narrative_returns_no_stray_unpacked_keys(monkeypatch):
    """The old ``**result`` shape is gone; the response is exactly the documented keys.

    ``model`` is here deliberately, not incidentally: the frontend polls with
    ``data.model || 'MiniMax-H3'`` (useNarrativeMedia.ts), and poll_task uses a different
    URL per api_version, so an omitted model means polling the wrong endpoint.
    """
    service = _FakeService(task_id="task-123")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE, "genre": "healing"})

    assert set(resp.json()) == {"status", "video_prompt", "narrative_genre", "task_id", "model"}


# --------------------------------------------------------------------------- #
# The response must name the model that was actually submitted, so the client polls
# the right URL. T2V-01 is api_version v1, MiniMax-H3 is v2.
# --------------------------------------------------------------------------- #
def test_response_model_matches_the_submitted_default_when_nothing_is_requested(monkeypatch):
    """The shipped default is T2V-01; the response must say so, not MiniMax-H3."""
    service = _FakeService(task_id="task-123", default_model="T2V-01")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model"] == "T2V-01", (
        f"response says {body.get('model')!r} but the task was submitted as "
        f"{service.config['default_model']!r}; the client will poll the v2 URL for a v1 task"
    )
    assert body["task_id"] == "task-123"
    assert service.submit_calls[0]["model"] == "T2V-01", "the fake must actually receive T2V-01"


def test_response_model_echoes_an_explicitly_requested_model(monkeypatch):
    """An explicit model in the payload must be echoed, not replaced by the default."""
    service = _FakeService(task_id="task-123", default_model="T2V-01")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE, "model": "MiniMax-Hailuo-2.3"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model"] == "MiniMax-Hailuo-2.3"
    assert body["task_id"] == "task-123"
    assert service.submit_calls[0]["model"] == "MiniMax-Hailuo-2.3"


def test_response_model_is_h3_when_h3_is_the_configured_default(monkeypatch):
    """The MiniMax-H3 default path still works and is reported honestly."""
    service = _FakeService(task_id="task-123", default_model="MiniMax-H3")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})

    assert resp.status_code == 200, resp.text
    assert resp.json()["model"] == "MiniMax-H3"


def test_guard_fallback_still_carries_the_model(monkeypatch):
    from backend.app.api.v1.endpoints import video_generation

    class _Hostile(str):
        def __getitem__(self, item):
            raise RuntimeError("response assembly exploded after submission")

    monkeypatch.setattr(video_generation, "finalize_image_prompt", lambda *a, **k: _Hostile("x" * 200))

    service = _FakeService(task_id="task-123", default_model="T2V-01")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["task_id"] == "task-123"
    assert body["model"] == "T2V-01", (
        "the fallback response dropped the model; a client polling this task would "
        "default to MiniMax-H3 and query the wrong api_version URL"
    )


# --------------------------------------------------------------------------- #
# Server-side watcher, like POST /videos/generate: a closed tab must not strand a
# video the learner already paid for.
# --------------------------------------------------------------------------- #
@pytest.fixture
def watcher_calls(monkeypatch):
    """Replace the background watcher with a recorder and return the call log.

    The real ``_watch_video_task`` polls MiniMax for up to ``poll_timeout_seconds``
    and calls ``service.download_video``, so it must never actually run in a test.
    The autouse fixture ``_never_run_real_watcher`` keeps that true for every test in
    the module; this fixture just hands the recorder to the tests that assert on it.
    """
    calls: list[tuple] = []

    async def _fake_watch(service, task_id, model):  # noqa: ANN001
        calls.append((task_id, model))

    from backend.app.api.v1.endpoints import video_generation

    monkeypatch.setattr(video_generation, "_watch_video_task", _fake_watch)
    return calls


def test_watcher_is_armed_with_the_task_id_and_the_submitted_model(monkeypatch, watcher_calls):
    service = _FakeService(task_id="task-123", default_model="T2V-01")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})
    assert resp.status_code == 200, resp.text

    assert watcher_calls, "no completion watcher was armed; a closed tab strands the paid video"
    task_id, watched_model = watcher_calls[0]
    assert task_id == "task-123"
    assert watched_model == "T2V-01", (
        f"watcher polls model={watched_model!r} but the task was submitted as " f"{service.submit_calls[0]['model']!r}"
    )


def test_watcher_is_armed_for_an_explicitly_requested_model(monkeypatch, watcher_calls):
    service = _FakeService(task_id="task-123", default_model="T2V-01")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE, "model": "MiniMax-H3"})
    assert resp.status_code == 200, resp.text

    assert watcher_calls, "no completion watcher was armed"
    assert watcher_calls[0] == ("task-123", "MiniMax-H3")


def test_watcher_is_not_armed_when_the_task_was_never_submitted(monkeypatch, watcher_calls):
    """A rejected request must not leave a watcher polling for a task that never existed."""
    service = _FakeService()
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": "too short"})

    assert resp.status_code == 400
    assert watcher_calls == [], f"watcher armed for a task that was never submitted: {watcher_calls}"


def test_watcher_is_not_armed_when_the_service_rejected_the_submission(monkeypatch, watcher_calls):
    service = _FakeService(error=RuntimeError("daily cost cap reached"))
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})

    assert resp.status_code == 400
    assert watcher_calls == [], f"watcher armed despite a failed submission: {watcher_calls}"


def test_duration_reaches_submit_task(monkeypatch):
    """The shipped default duration is 6; T2V-01 supports [6] only."""
    service = _FakeService(task_id="task-123")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE})

    assert resp.status_code == 200, resp.text
    assert (
        service.submit_calls[0]["duration"] == 6
    ), f"expected the configured duration 6, got {service.submit_calls[0]['duration']}"


# --------------------------------------------------------------------------- #
# F4: a model key that is PRESENT but empty must not skip the default.
# payload.get("model", default) returns None/"" in that case while submit_task
# substitutes the default internally, so the response and the watcher used to carry a
# value the client would never poll correctly.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("sent_model", [None, ""], ids=["null-model", "empty-model"])
def test_present_but_empty_model_falls_back_to_the_configured_default(monkeypatch, watcher_calls, sent_model):
    service = _FakeService(task_id="task-123", default_model="T2V-01")
    client, _ = _install(monkeypatch, service)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE, "model": sent_model})

    assert resp.status_code == 200, resp.text
    assert resp.json()["model"] == "T2V-01", (
        f"model={sent_model!r} must fall back to the configured default, " f"got {resp.json().get('model')!r}"
    )
    assert service.submit_calls[0]["model"] == "T2V-01"
    assert watcher_calls == [("task-123", "T2V-01")], f"watcher must poll the EFFECTIVE model, got {watcher_calls}"


# --------------------------------------------------------------------------- #
# F1: model-aware parameter selection, on the REAL service with a fake httpx client.
# The shipped default_resolution is 720P, which only T2V-01 accepts, so before this fix
# any model other than the default came back HTTP 400 before anything was spent.
# --------------------------------------------------------------------------- #
class _FakeHttpResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


class _FakeHttpClient:
    def __init__(self, task_id: str = "task-123"):
        self._task_id = task_id
        self.posts: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, headers=None, json=None):  # noqa: ANN002
        self.posts.append({"url": url, "body": json})
        return _FakeHttpResponse({"task_id": self._task_id})


def _install_real_service(monkeypatch, **config):
    """Patch get_service with a REAL VideoGenerationService talking to fake httpx."""
    from backend.app.api.v1.endpoints import video_generation
    from backend.app.main import app
    from backend.core.services import video_generation_service as vgs
    from backend.core.services.video_generation_service import VideoGenerationService

    http = _FakeHttpClient()
    monkeypatch.setattr(vgs.httpx, "AsyncClient", lambda *a, **k: http)
    service = VideoGenerationService(
        {
            "enabled": True,
            "minimax_api_key": "test-key-not-used-offline",
            "video_output_dir": "/tmp/w1/videos",
            **config,
        }
    )
    monkeypatch.setattr(video_generation, "get_service", lambda: service)
    # The endpoint also needs its prompt-transformation provider; reuse the doubles at
    # the top of this file rather than reaching for a real provider.
    monkeypatch.setattr(app.state, "llm_registry", _FakeRegistry(_FakeProvider()), raising=False)
    return TestClient(app), http


@pytest.mark.parametrize(
    ("requested_model", "expected_model", "expected_resolution", "expected_url_tail"),
    [
        (None, "T2V-01", "720P", "/v1/video_generation"),
        ("MiniMax-Hailuo-2.3", "MiniMax-Hailuo-2.3", "768P", "/v1/video_generation"),
        ("MiniMax-H3", "MiniMax-H3", "2K", "/v2/video_generation"),
    ],
    ids=["default-T2V-01", "explicit-Hailuo-2.3", "explicit-H3"],
)
def test_resolution_is_chosen_for_the_model_not_the_shipped_default(
    monkeypatch, watcher_calls, requested_model, expected_model, expected_resolution, expected_url_tail
):
    client, http = _install_real_service(monkeypatch)

    body = {"narrative": NARRATIVE}
    if requested_model is not None:
        body["model"] = requested_model

    resp = client.post(ENDPOINT, json=body)

    assert resp.status_code == 200, f"{resp.status_code}: {resp.text}"
    assert resp.json()["model"] == expected_model
    assert len(http.posts) == 1, "exactly one paid submission"
    sent = http.posts[0]
    assert sent["url"].endswith(expected_url_tail), sent["url"]
    assert sent["body"]["model"] == expected_model
    assert sent["body"]["resolution"] == expected_resolution, (
        f"{expected_model} must be submitted at {expected_resolution}, " f"got {sent['body']['resolution']!r}"
    )
    assert (
        sent["body"]["duration"] == 6
    ), f"shipped default duration 6 is supported by every model, got {sent['body']['duration']!r}"


def test_explicit_supported_resolution_is_respected_over_the_default(monkeypatch, watcher_calls):
    client, http = _install_real_service(monkeypatch)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE, "model": "MiniMax-Hailuo-2.3", "resolution": "1080P"})

    assert resp.status_code == 200, resp.text
    assert http.posts[0]["body"]["resolution"] == "1080P", "an explicit supported value wins"


def test_unsupported_resolution_falls_back_to_a_supported_one(monkeypatch, watcher_calls):
    client, http = _install_real_service(monkeypatch)

    resp = client.post(ENDPOINT, json={"narrative": NARRATIVE, "model": "MiniMax-Hailuo-2.3", "resolution": "720P"})

    assert resp.status_code == 200, f"{resp.status_code}: {resp.text}"
    assert (
        http.posts[0]["body"]["resolution"] == "768P"
    ), "720P is not supported by Hailuo-2.3; it must fall back, not 400"
