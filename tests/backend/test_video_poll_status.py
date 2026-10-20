# tests/backend/test_video_poll_status.py
"""Task-status normalisation and the server-side watcher, on the REAL service.

Why the real service
--------------------
The earlier endpoint tests used a ``_FakeService`` double. That double hides exactly the
bugs this file exists for: the real ``poll_task`` does provider I/O, the real
``submit_task`` validates duration/resolution against ``MODEL_SPECS``, and the real
``_watch_video_task`` loops. Only ``httpx.AsyncClient`` is faked, so the code under test
is production code end to end.

Why status normalisation matters
--------------------------------
Every poller stops on ``done`` or ``failed``:
  * the server-side watcher in video_generation.py
  * the browser poller in frontend/src/lib/videoTaskPoll.ts:23
``poll_task`` used to merely lowercase whatever the provider sent, so a body of
``{"status": "Success"}`` produced ``"success"``, which matches neither terminal value.
The watcher then polled every 5 s until ``poll_timeout_seconds`` (600) with each error
swallowed at DEBUG, and nothing was ever downloaded: a paid video, invisible.

Offline: no network, no API key, no real task. Fake httpx only.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from backend.core.services import video_generation_service as vgs
from backend.core.services.video_generation_service import (
    VideoGenerationService,
    normalise_task_status,
)

FAKE_KEY = "test-key-not-used-offline"


# --------------------------------------------------------------------------- #
# Fake httpx
# --------------------------------------------------------------------------- #
class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Stands in for ``httpx.AsyncClient``; records every call for assertions."""

    def __init__(self, get_payloads: list[dict], post_payload: dict | None = None):
        self._get_payloads = list(get_payloads)
        self._post_payload = post_payload
        self.gets: list[dict] = []
        self.posts: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, headers=None, params=None):
        self.gets.append({"url": url, "params": params})
        payload = self._get_payloads.pop(0) if self._get_payloads else {"status": "Success"}
        return _FakeResponse(payload)

    async def post(self, url, headers=None, json=None):
        self.posts.append({"url": url, "body": json})
        payload = self._post_payload or {"task_id": "task-1"}
        return _FakeResponse(payload)


def _service(
    monkeypatch, get_payloads: list[dict], post_payload: dict | None = None, **config
) -> tuple[VideoGenerationService, _FakeClient]:
    client = _FakeClient(get_payloads, post_payload)
    monkeypatch.setattr(vgs.httpx, "AsyncClient", lambda *a, **k: client)
    svc = VideoGenerationService(
        {"minimax_api_key": FAKE_KEY, "enabled": True, "video_output_dir": "/tmp/w1/videos", **config}
    )
    return svc, client


# --------------------------------------------------------------------------- #
# 1. The normalisation table, straight off the function.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("provider_status", "expected"),
    [
        # done
        ("success", "done"),
        ("Success", "done"),
        ("SUCCESS", "done"),
        ("Success ", "done"),
        ("succeeded", "done"),
        ("done", "done"),
        ("completed", "done"),
        ("complete", "done"),
        ("finished", "done"),
        # failed
        ("fail", "failed"),
        ("Fail", "failed"),
        ("failed", "failed"),
        ("failure", "failed"),
        ("error", "failed"),
        ("cancelled", "failed"),
        ("canceled", "failed"),
        ("rejected", "failed"),
        # pending
        ("pending", "pending"),
        ("preparing", "pending"),
        ("Queueing", "pending"),
        ("queued", "pending"),
        ("submitted", "pending"),
        ("waiting", "pending"),
        # processing
        ("processing", "processing"),
        ("running", "processing"),
        ("generating", "processing"),
        ("in_progress", "processing"),
        ("in-progress", "processing"),
        # empty / missing keeps the documented default
        (None, "pending"),
        ("", "pending"),
        ("   ", "pending"),
    ],
)
def test_normalise_task_status(provider_status, expected):
    assert normalise_task_status(provider_status) == expected


def test_unknown_status_becomes_processing_and_warns_by_name(caplog):
    """Unknown must never look terminal (drops a paid video) nor vanish (polls forever)."""
    with caplog.at_level("WARNING", logger=vgs.logger.name):
        assert normalise_task_status("Sorcery-Initiated") == "processing"
    assert "Sorcery-Initiated" in caplog.text, f"the unknown value must be named in the log; got: {caplog.text!r}"


# --------------------------------------------------------------------------- #
# 2. poll_task on the REAL service, both API versions.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("model", "expected_url_fragment"),
    [("T2V-01", "/v1/query/video_generation"), ("MiniMax-H3", "/v2/query/video_generation/")],
    ids=["v1-T2V-01", "v2-MiniMax-H3"],
)
@pytest.mark.parametrize(
    ("body", "expected_status"),
    [
        # A terminal provider status with NO URL is NOT a success here: see
        # test_v1_done_with_file_id_and_no_url_is_a_honest_failure for why.
        ({"status": "Success"}, "failed"),
        ({"status": "Success", "file_id": "f1"}, "failed"),
        ({"status": "succeeded"}, "failed"),
        ({"status": "Success", "data": {"video_url": "https://x/v.mp4"}}, "done"),
        ({"status": "succeeded", "data": {"video_url": "https://x/v.mp4"}}, "done"),
        ({"status": "Fail"}, "failed"),
        ({"status": "Queueing"}, "pending"),
        ({"status": "Processing"}, "processing"),
    ],
)
def test_poll_task_normalises_provider_vocabulary(monkeypatch, model, expected_url_fragment, body, expected_status):
    svc, client = _service(monkeypatch, [body])
    status = asyncio.run(svc.poll_task("task-1", model))
    assert status.status == expected_status
    assert client.gets[0]["url"].endswith(expected_url_fragment) or expected_url_fragment in client.gets[0]["url"]


def test_poll_task_keeps_the_provider_string_and_the_url(monkeypatch):
    svc, _ = _service(monkeypatch, [{"status": "Success", "data": {"video_url": "https://x/v.mp4"}}])
    status = asyncio.run(svc.poll_task("task-1", "MiniMax-H3"))
    assert status.status == "done"
    assert status.video_url == "https://x/v.mp4"
    assert status.provider_status == "Success"
    assert status.raw == {"status": "Success", "data": {"video_url": "https://x/v.mp4"}}


def test_v1_done_with_file_id_and_no_url_is_a_honest_failure(monkeypatch, caplog):
    """A v1 success body carries file_id and no video_url.

    Reporting this as ``done`` is a lie: ``frontend/src/lib/videoTaskPoll.ts:23`` treats
    ``done`` as terminal and ``useNarrativeMedia.ts`` toasts "Video generated!" for any
    terminal status that is not ``failed``. The user is told it worked and there is no
    video anywhere, because ``/videos/status`` only sets ``local_path`` for
    ``done`` + ``video_url``.

    So: report the documented terminal FAILURE, with an error the user can act on. We do
    not invent a URL and we do not add an unverified v1 file-retrieval call.
    """
    with caplog.at_level("WARNING", logger=vgs.logger.name):
        svc, _ = _service(monkeypatch, [{"status": "Success", "file_id": "f1"}])
        status = asyncio.run(svc.poll_task("task-1", "T2V-01"))

    assert status.status == "failed", "a done-without-URL task must not look like success"
    assert status.video_url is None, "no url may be invented"
    assert status.raw["file_id"] == "f1", "the file_id stays reachable via raw"
    assert status.provider_status == "Success", "the provider string is preserved"
    assert status.error is not None, "the failure must carry an explanation"
    for fragment in ("task-1", "f1", "no download URL"):
        assert fragment in status.error, f"error must mention {fragment!r}: {status.error!r}"
    assert "Success" in status.error, f"error must quote the provider status: {status.error!r}"
    assert "file_id" in caplog.text and "no download URL" in caplog.text


def test_v2_done_with_neither_url_nor_file_id_reports_file_id_none(monkeypatch):
    """The v2 shape with no URL and no file_id must still fail honestly, and must say
    'file_id=none' rather than inventing a value."""
    svc, _ = _service(monkeypatch, [{"status": "succeeded", "data": {}}])
    status = asyncio.run(svc.poll_task("task-v2", "MiniMax-H3"))

    assert status.status == "failed"
    assert status.video_url is None
    assert status.error is not None
    assert "file_id=none" in status.error, status.error
    assert "task-v2" in status.error, status.error


@pytest.mark.parametrize(
    "body",
    [
        {"status": "Success", "video_url": "https://x/v.mp4"},
        {"status": "Success", "data": {"video_url": "https://x/v.mp4"}},
        {"status": "succeeded", "data": {"download_url": "https://x/v.mp4"}},
    ],
    ids=["v1-top-level", "v1-nested", "v2-download_url"],
)
def test_done_with_a_url_is_unchanged_and_still_successful(monkeypatch, body):
    """Requirement 3: a done WITH a URL must not be caught by the new failure rule."""
    svc, _ = _service(monkeypatch, [body])
    status = asyncio.run(svc.poll_task("task-1", "T2V-01"))

    assert status.status == "done"
    assert status.video_url == "https://x/v.mp4"
    assert status.error is None, f"a successful download must not carry an error: {status.error!r}"


def test_unknown_status_stays_processing_and_is_not_caught_by_the_failure_rule(monkeypatch):
    """Requirement 3: unknown statuses stay processing - they are not terminal at all."""
    svc, _ = _service(monkeypatch, [{"status": "Wibble"}])
    status = asyncio.run(svc.poll_task("task-1", "T2V-01"))

    assert status.status == "processing"
    assert status.error is None


def test_missing_status_field_defaults_to_pending(monkeypatch):
    svc, _ = _service(monkeypatch, [{"task_id": "t"}])
    assert asyncio.run(svc.poll_task("task-1", "T2V-01")).status == "pending"


# --------------------------------------------------------------------------- #
# 3. The watcher, on the real service.
# --------------------------------------------------------------------------- #
async def _real_sleep(_delay, *args, **kwargs):
    return None


def _watch(monkeypatch, get_payloads):
    # poll_timeout_seconds is deliberately tiny. If status normalisation is ever broken
    # again, _watch_video_task never matches a terminal value and would busy-poll for the
    # real 600 s default; the small timeout makes that failure FAST and reportable instead
    # of hanging the suite. In the correct state the watcher returns after one or two polls
    # and the timeout is never reached.
    svc, client = _service(monkeypatch, get_payloads, poll_timeout_seconds=1.0)
    downloads: list[str] = []

    async def fake_download(url, output_dir=None):
        downloads.append(url)
        return "/tmp/w1/videos/saved.mp4"

    monkeypatch.setattr(svc, "download_video", fake_download)
    monkeypatch.setattr(asyncio, "sleep", _real_sleep)
    return svc, client, downloads


def test_watcher_downloads_once_and_returns_when_the_provider_says_success(monkeypatch):
    """RED for F3: 'Success' used to normalise to 'success' and match no terminal value,
    so this looped for the full 600 s timeout and never downloaded."""
    svc, client, downloads = _watch(
        monkeypatch,
        [{"status": "Queueing"}, {"status": "Success", "data": {"video_url": "https://x/v.mp4"}}],
    )
    from backend.app.api.v1.endpoints.video_generation import _watch_video_task

    asyncio.run(_watch_video_task(svc, "task-1", "MiniMax-H3"))

    assert len(client.gets) == 2, "should have polled twice then stopped"
    assert downloads == ["https://x/v.mp4"], f"expected exactly one download, got {downloads}"


def test_watcher_returns_without_downloading_on_failure(monkeypatch):
    svc, client, downloads = _watch(monkeypatch, [{"status": "Fail"}])
    from backend.app.api.v1.endpoints.video_generation import _watch_video_task

    asyncio.run(_watch_video_task(svc, "task-1", "T2V-01"))

    assert len(client.gets) == 1
    assert downloads == [], "a failed task must not be downloaded"


def test_watcher_returns_through_the_failed_branch_when_a_done_task_has_no_url(monkeypatch):
    """A v1 'Success' carries file_id and no URL, which poll_task now reports as FAILED.

    So the watcher's ``failed`` branch matches: it returns after a SINGLE poll instead of
    spinning to the 600 s timeout, and it downloads nothing.

    Both assertions are load-bearing. If the failure rule is ever removed, this test
    regresses to 120 polls - which the tiny poll_timeout_seconds below turns into a fast
    assertion failure rather than a hung suite.
    """
    from backend.app.api.v1.endpoints.video_generation import _watch_video_task

    svc, client, downloads = _watch(monkeypatch, [{"status": "Success", "file_id": "f1"}])

    asyncio.run(_watch_video_task(svc, "task-1", "T2V-01"))

    assert (
        len(client.gets) == 1
    ), "the watcher must stop at the first poll via the failed branch, not spin to the timeout"
    assert downloads == [], "nothing may be downloaded without a URL"


# --------------------------------------------------------------------------- #
# 5. The user-visible contract: POST /videos/status through the real router.
# --------------------------------------------------------------------------- #
def test_videos_status_route_reports_failed_and_error_for_a_v1_success_without_url(monkeypatch):
    """What the BROWSER actually receives.

    ``/videos/status`` copies ``error`` into the payload and only sets ``local_path`` for
    ``done`` + ``video_url``. So with the new failure rule the payload is ``failed`` + an
    error and no local_path - which is the existing error toast path, with NO frontend
    change.
    """
    from fastapi.testclient import TestClient

    from backend.app.api.v1.endpoints import video_generation
    from backend.app.main import app

    svc, _ = _service(monkeypatch, [{"status": "Success", "file_id": "f1"}])
    monkeypatch.setattr(video_generation, "get_service", lambda: svc)
    client = TestClient(app)

    resp = client.post("/api/v1/videos/status", json={"task_id": "task-1", "model": "T2V-01"})

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "failed", payload
    assert payload.get("error"), f"the payload must carry an explanation: {payload}"
    assert "local_path" not in payload, f"no video was downloaded, so there is no local_path: {payload}"
    assert "video_url" not in payload, f"no URL may be invented: {payload}"


def test_videos_status_route_still_returns_done_and_local_path_when_a_url_exists(monkeypatch):
    """The success path must be untouched: still auto-downloads and returns local_path."""
    from fastapi.testclient import TestClient

    from backend.app.api.v1.endpoints import video_generation
    from backend.app.main import app

    svc, _ = _service(monkeypatch, [{"status": "Success", "data": {"video_url": "https://x/v.mp4"}}])

    async def fake_download(video_url, output_dir=None):
        return "/tmp/w1/videos/saved.mp4"

    monkeypatch.setattr(svc, "download_video", fake_download)
    monkeypatch.setattr(video_generation, "get_service", lambda: svc)
    client = TestClient(app)

    resp = client.post("/api/v1/videos/status", json={"task_id": "task-1", "model": "T2V-01"})

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "done", payload
    assert payload["video_url"] == "https://x/v.mp4"
    assert payload["local_path"] == "/tmp/w1/videos/saved.mp4"


# --------------------------------------------------------------------------- #
# 4. F2: prompt_optimizer is a config key, not a hardcoded True.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("configured", "expected_in_body"),
    [(True, True), (False, False)],
    ids=["optimizer-on", "optimizer-off"],
)
def test_v1_prompt_optimizer_comes_from_config(monkeypatch, configured, expected_in_body):
    svc, client = _service(monkeypatch, [], {"task_id": "task-1"}, prompt_optimizer=configured)
    asyncio.run(svc.submit_task(prompt="A slow push in through incense smoke.", model="T2V-01"))
    assert client.posts[0]["body"]["prompt_optimizer"] is expected_in_body


def test_v2_body_is_unchanged_and_carries_no_prompt_optimizer(monkeypatch):
    """The v2 body shape is untouched by F2.

    ``resolution="2K"`` is passed explicitly because the SERVICE default is 720P, which
    only T2V-01 accepts; choosing a supported resolution per model is the ENDPOINT's job
    (F1, covered in test_video_from_narrative.py). This test is about the v2 body shape,
    not about F1.
    """
    svc, client = _service(monkeypatch, [], {"task_id": "task-1"}, prompt_optimizer=False)
    asyncio.run(
        svc.submit_task(
            prompt="A slow push in through incense smoke.",
            model="MiniMax-H3",
            resolution="2K",
        )
    )
    body = client.posts[0]["body"]
    assert "prompt_optimizer" not in body
    assert body["content"][0]["type"] == "text"
    assert client.posts[0]["url"].endswith("/v2/video_generation")
