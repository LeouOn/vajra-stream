"""IR-1: the /divination/interpret call path works.

RED-first regression tests for a defect where ``interpret_divination`` called
``chat_interaction(chat_req)`` with ONE argument while ``chat_compat`` (which
``chat_interaction`` aliases) needs TWO, so every request raised ``TypeError``
and the surrounding handler turned it into an HTTP 500.

No LLM, no network, no server: the chat function is replaced by a recording
async fake, patched where it is looked up at call time.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import divination as divination_module


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(divination_module.router)
    return TestClient(app)


class FakeResponse:
    def __init__(self, text: str = "an interpretation") -> None:
        self.response = text
        self.tool_calls: list[Any] = []


class RecordingChat:
    """Stands in for ``chat_interaction`` and records how it was called."""

    def __init__(self, *, raises: Exception | None = None) -> None:
        self.raises = raises
        self.calls: list[tuple[list[Any], int]] = []

    async def __call__(self, *args: Any) -> FakeResponse:
        self.calls.append((list(args), len(args)))
        if self.raises is not None:
            raise self.raises
        return FakeResponse()


def _patch_chat(monkeypatch: pytest.MonkeyPatch, fake: RecordingChat) -> None:
    """Patch where the function is LOOKED UP, i.e. on the llm module."""
    from backend.app.api.v1.endpoints import llm as llm_module

    monkeypatch.setattr(llm_module, "chat_interaction", fake)


def test_interpret_returns_200_and_the_expected_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful interpretation is HTTP 200 with status/interpretation/timestamp."""
    fake = RecordingChat()
    _patch_chat(monkeypatch, fake)

    response = client.post(
        "/divination/interpret",
        json={"system": "Tarot", "question": "What now?", "details": {}},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["interpretation"] == "an interpretation"
    assert "timestamp" in body
    # The chat function must have been called with the arity chat_compat needs.
    assert fake.calls, "the chat function was never called"
    assert fake.calls[0][1] == 2, f"chat_interaction must be called with 2 args, got {fake.calls[0][1]}"


def test_timestamp_is_epoch_seconds_not_loop_time(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The timestamp is wall-clock epoch seconds, not monotonic loop time."""
    fake = RecordingChat()
    _patch_chat(monkeypatch, fake)

    before = time.time()
    body = client.post(
        "/divination/interpret",
        json={"system": "Tarot", "question": "What now?", "details": {}},
    ).json()
    after = time.time()

    assert isinstance(body["timestamp"], float)
    # A monotonic loop clock would be a small number near process start; epoch
    # seconds are ~1.7e9. Comparing to the wall clock is the honest check.
    assert before - 5 <= body["timestamp"] <= after + 5, body["timestamp"]


@pytest.mark.parametrize("key", ["cast", "iching"])
def test_iching_cast_is_accepted_under_either_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    """The UI sends details.iching; the LLM-tools path sends details.cast.

    Both must reach the prompt, so the rich I Ching section appears either way.
    """
    fake = RecordingChat()
    _patch_chat(monkeypatch, fake)

    cast = {
        "primary": {
            "name": "Qian",
            "name_english": "The Creative",
            "judgment": "The Creative works through sublime success.",
            "image": "The Creative: strong water.",
        },
        "changing": [],
        "lines": [],
    }
    response = client.post(
        "/divination/interpret",
        json={"system": "I Ching", "question": "What now?", "details": {key: cast}},
    )

    assert response.status_code == 200, response.text
    prompt = fake.calls[0][0][0].messages[0].content
    assert "Qian" in prompt, f"the I Ching section is missing from the prompt for key {key!r}"
    assert "Creative" in prompt, f"the I Ching section is missing from the prompt for key {key!r}"


def test_a_failing_chat_call_becomes_a_500_with_the_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A provider failure surfaces as HTTP 500 carrying the reason."""
    fake = RecordingChat(raises=RuntimeError("provider exploded"))
    _patch_chat(monkeypatch, fake)

    response = client.post(
        "/divination/interpret",
        json={"system": "Tarot", "question": "What now?", "details": {}},
    )

    assert response.status_code == 500
    assert "provider exploded" in response.text


def test_no_request_argument_is_injected_into_the_chat_call(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second argument is a real Request, so the provider can be resolved."""
    fake = RecordingChat()
    _patch_chat(monkeypatch, fake)

    client.post(
        "/divination/interpret",
        json={"system": "Tarot", "question": "What now?", "details": {}},
    )

    assert fake.calls[0][1] == 2
    request = fake.calls[0][0][1]
    assert hasattr(request, "app"), "the second argument must be a Request-like object"
    assert hasattr(request.app, "state")
