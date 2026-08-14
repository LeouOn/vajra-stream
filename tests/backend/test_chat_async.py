"""Async chat job create / poll / cancel — no live LLM."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app.main import app

    with TestClient(app) as c:
        yield c


def test_chat_async_accepts_job_and_cancel(client, monkeypatch):
    started = asyncio.Event()

    async def fake_run(job_id, request, http_request, connection_id):
        from backend.app.api.v1.chat_job_manager import is_cancelled, update_job

        update_job(job_id, status="running")
        started.set()
        for _ in range(200):
            if is_cancelled(job_id):
                return
            await asyncio.sleep(0.05)

    monkeypatch.setattr("backend.app.api.v1.endpoints.llm._run_chat_async", fake_run)

    resp = client.post(
        "/api/v1/llm/chat/async",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    job_id = body["job_id"]
    assert job_id.startswith("chat_")

    cancel = client.post(f"/api/v1/llm/chat/jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    status = client.get(f"/api/v1/llm/chat/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "cancelled"
    assert "task" not in status.json()


def test_chat_job_unknown_is_404(client):
    assert client.get("/api/v1/llm/chat/jobs/chat_missing").status_code == 404
    assert client.post("/api/v1/llm/chat/jobs/chat_missing/cancel").status_code == 404
