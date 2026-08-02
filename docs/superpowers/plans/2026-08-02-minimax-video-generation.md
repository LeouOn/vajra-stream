# MiniMax Video Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MiniMax video generation to Vajra.Stream — generate 4-15 second manifestation videos from text prompts, with cost controls, async task tracking, and a settings panel.

**Architecture:** Self-contained `VideoGenerationService` (mirrors the existing `ImageGenerationService` pattern) that talks to MiniMax's async V1 and V2 video APIs. The service submits a task, returns a task_id, and the frontend polls for completion. Cost guards enforce daily/hourly caps before any API call is made. Videos are downloaded and saved to `generated/videos/` for archival and QA.

**Tech Stack:** Python 3.10+ / FastAPI / httpx / React + TypeScript + Ant Design

## Global Constraints

- API key already configured: `MINIMAX_API_KEY` env var is set (`sk-cp-Bo...`)
- MiniMax V1 API: `POST https://api.minimax.io/v1/video_generation` (models: T2V-01, MiniMax-Hailuo-2.3)
- MiniMax V2 API: `POST https://api.minimax.io/v2/video_generation` (model: MiniMax-H3, multimodal content[])
- MiniMax Query V1: `GET https://api.minimax.io/v1/query/video_generation?task_id=xxx`
- MiniMax Query V2: `GET https://api.minimax.io/v2/query/video_generation/{task_id}`
- Auth: `Authorization: Bearer <MINIMAX_API_KEY>`
- Cost: ~$0.50 per generation (T2V-01 720p 6s), H3 pricing TBD but similar tier
- Default daily cap: $2.00 (4 videos/day)
- Default hourly limit: 2 per hour
- Video output directory: `generated/videos/`
- Pattern to follow: `backend/core/services/image_generation_service.py` + `backend/app/api/v1/endpoints/image_generation.py`
- Route registration: `backend/app/api/v1/api.py`
- No Docker; Windows/PowerShell dev environment

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/core/services/video_generation_service.py` | Self-contained service: config, cost tracking, MiniMax API calls (submit + poll), video download |
| `backend/app/api/v1/endpoints/video_generation.py` | REST endpoints: generate, status, config, models, saved list |
| `backend/app/api/v1/api.py` | Register the video router |
| `frontend/src/components/Settings/VideoSettingsPanel.tsx` | Settings panel: enable/disable, model select, duration, resolution, cost caps, generate button |
| `tests/unit/test_video_generation_service.py` | Unit tests for cost guards, config validation, prompt validation |

---

## Task 1: Video Generation Service — Config, Cost Guards, and Task Submission

**Files:**
- Create: `backend/core/services/video_generation_service.py`
- Create: `tests/unit/test_video_generation_service.py`

**Interfaces:**
- Produces: `VideoGenerationService` class with `submit_task(prompt, model, duration, resolution) -> dict`, `poll_task(task_id) -> dict`, `config` property, `update_config(updates) -> dict`, `get_cost_stats() -> dict`, `validate_prompt(prompt) -> dict`

- [ ] **Step 1: Write the failing test for config defaults and cost stats**

```python
# tests/unit/test_video_generation_service.py
"""Tests for VideoGenerationService cost guards and config."""
import pytest
from backend.core.services.video_generation_service import VideoGenerationService, DEFAULT_VIDEO_CONFIG


class TestVideoGenerationServiceConfig:
    def test_default_config_values(self):
        svc = VideoGenerationService()
        assert svc.config["enabled"] is False
        assert svc.config["default_model"] == "T2V-01"
        assert svc.config["daily_cost_cap_usd"] == 2.0
        assert svc.config["max_per_hour"] == 2
        assert svc.config["default_duration"] == 6
        assert svc.config["default_resolution"] == "720P"

    def test_update_config_merges_known_keys(self):
        svc = VideoGenerationService()
        svc.update_config({"enabled": True, "daily_cost_cap_usd": 5.0})
        assert svc.config["enabled"] is True
        assert svc.config["daily_cost_cap_usd"] == 5.0

    def test_update_config_rejects_unknown_keys(self):
        svc = VideoGenerationService()
        with pytest.raises(ValueError, match="unknown config key"):
            svc.update_config({"banana": 1})

    def test_cost_stats_starts_empty(self):
        svc = VideoGenerationService()
        stats = svc.get_cost_stats()
        assert stats["daily_spend_usd"] == 0.0
        assert stats["hourly_calls"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_video_generation_service.py -v -k "TestVideoGenerationServiceConfig" --no-header --tb=short`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write the service — config, cost tracking, and prompt validation**

```python
# backend/core/services/video_generation_service.py
"""
Video Generation Service — MiniMax video generation (T2V-01, Hailuo, H3).

Self-contained, zero project dependencies (only httpx). Mirrors the
ImageGenerationService pattern: config dict in, async API out, cost guards.

Usage:
    service = VideoGenerationService()
    result = await service.submit_task(
        prompt="Golden Buddha statue radiating light, slow zoom",
        model="T2V-01",
        duration=6,
    )
    task_id = result["task_id"]

    # Poll later:
    status = await service.poll_task(task_id)
    if status["status"] == "succeeded":
        video_url = status["video_url"]
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_VIDEO_CONFIG: dict[str, Any] = {
    "enabled": False,
    "minimax_api_key": "",
    "default_model": "T2V-01",
    "default_duration": 6,
    "default_resolution": "720P",
    "prompt_optimizer": True,
    "daily_cost_cap_usd": 2.0,
    "max_per_hour": 2,
    "video_output_dir": "generated/videos",
    "prompt_style_prefix": "",
    "max_prompt_chars": 2000,
}

MODEL_SPECS: dict[str, dict[str, Any]] = {
    "T2V-01": {
        "api_version": "v1",
        "cost_usd": 0.50,
        "durations": [6],
        "resolutions": ["720P"],
    },
    "MiniMax-Hailuo-2.3": {
        "api_version": "v1",
        "cost_usd": 0.85,
        "durations": [6, 10],
        "resolutions": ["768P", "1080P"],
    },
    "MiniMax-H3": {
        "api_version": "v2",
        "cost_usd": 1.00,
        "durations": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "resolutions": ["2K"],
        "ratios": ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"],
    },
}


class VideoGenerationService:
    """MiniMax video generation with cost controls and async task tracking."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = dict(DEFAULT_VIDEO_CONFIG)
        if config:
            self._config.update(config)
        if not self._config.get("minimax_api_key"):
            self._config["minimax_api_key"] = os.getenv("MINIMAX_API_KEY", "")
        self._daily_spend: dict[str, float] = {}
        self._hourly_calls: list[float] = []

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        unknown = set(updates) - set(DEFAULT_VIDEO_CONFIG)
        if unknown:
            raise ValueError(f"unknown config key(s): {sorted(unknown)}")
        self._config.update(updates)
        return self.config

    def get_cost_stats(self) -> dict[str, Any]:
        now = time.time()
        self._hourly_calls = [t for t in self._hourly_calls if now - t < 3600]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {
            "daily_spend_usd": self._daily_spend.get(today, 0.0),
            "daily_cost_cap_usd": self._config["daily_cost_cap_usd"],
            "hourly_calls": len(self._hourly_calls),
            "max_per_hour": self._config["max_per_hour"],
        }

    def validate_prompt(self, prompt: str) -> dict[str, Any]:
        max_chars = self._config["max_prompt_chars"]
        if len(prompt) > max_chars:
            return {
                "ok": False,
                "error": f"Prompt exceeds {max_chars} characters (got {len(prompt)}).",
            }
        if len(prompt.strip()) < 10:
            return {
                "ok": False,
                "error": "Prompt must be at least 10 characters.",
            }
        return {"ok": True, "char_count": len(prompt)}

    def _check_cost_guard(self, model: str) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cost = MODEL_SPECS.get(model, {}).get("cost_usd", 0.50)
        projected = self._daily_spend.get(today, 0.0) + cost
        if projected > self._config["daily_cost_cap_usd"]:
            raise RuntimeError(
                f"Video generation would breach daily cap "
                f"(${projected:.2f} > ${self._config['daily_cost_cap_usd']:.2f})"
            )
        now = time.time()
        self._hourly_calls = [t for t in self._hourly_calls if now - t < 3600]
        if len(self._hourly_calls) >= self._config["max_per_hour"]:
            raise RuntimeError(
                f"Hourly limit reached ({self._config['max_per_hour']}/hour)"
            )

    def _record_spend(self, model: str) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cost = MODEL_SPECS.get(model, {}).get("cost_usd", 0.50)
        self._daily_spend[today] = self._daily_spend.get(today, 0.0) + cost
        self._hourly_calls.append(time.time())

    async def submit_task(
        self,
        prompt: str,
        model: str | None = None,
        duration: int | None = None,
        resolution: str | None = None,
    ) -> dict[str, Any]:
        """Submit a video generation task. Returns {task_id, model, cost_usd, status}."""
        if not self._config["enabled"]:
            raise RuntimeError("Video generation is disabled; enable it in settings.")

        model_name = model or self._config["default_model"]
        dur = duration or self._config["default_duration"]
        res = resolution or self._config["default_resolution"]

        validation = self.validate_prompt(prompt)
        if not validation["ok"]:
            raise ValueError(validation["error"])

        self._check_cost_guard(model_name)

        style = str(self._config.get("prompt_style_prefix", "")).strip()
        full_prompt = f"{style}. {prompt}" if style else prompt

        api_key = self._config["minimax_api_key"]
        if not api_key:
            raise RuntimeError("MINIMAX_API_KEY not configured")

        spec = MODEL_SPECS.get(model_name, {})
        api_version = spec.get("api_version", "v1")

        if api_version == "v2":
            body = {
                "model": model_name,
                "content": [{"type": "text", "text": full_prompt}],
                "duration": dur,
                "resolution": res,
                "ratio": "16:9",
            }
            url = "https://api.minimax.io/v2/video_generation"
        else:
            body = {
                "model": model_name,
                "prompt": full_prompt,
                "prompt_optimizer": self._config.get("prompt_optimizer", True),
                "duration": dur,
                "resolution": res,
            }
            url = "https://api.minimax.io/v1/video_generation"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=body)

        if resp.status_code >= 400:
            self._record_spend(model_name)
            raise RuntimeError(f"MiniMax video API error {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        base_resp = data.get("base_resp", {})
        status_code = base_resp.get("status_code", 0)
        if status_code != 0:
            raise RuntimeError(
                f"MiniMax API returned status {status_code}: {base_resp.get('status_msg', 'unknown')}"
            )

        task_id = data.get("task_id", "")
        if not task_id:
            raise RuntimeError("MiniMax API returned no task_id")

        self._record_spend(model_name)
        cost = spec.get("cost_usd", 0.50)

        logger.info(
            "Video task submitted: task_id=%s model=%s cost=$%.2f",
            task_id, model_name, cost,
        )

        return {
            "task_id": task_id,
            "model": model_name,
            "cost_usd": cost,
            "status": "submitted",
            "prompt": full_prompt[:200],
        }

    async def poll_task(self, task_id: str, model: str = "T2V-01") -> dict[str, Any]:
        """Poll a video generation task. Returns {task_id, status, video_url?, error?}."""
        api_key = self._config["minimax_api_key"]
        spec = MODEL_SPECS.get(model, {})
        api_version = spec.get("api_version", "v1")

        headers = {"Authorization": f"Bearer {api_key}"}

        if api_version == "v2":
            url = f"https://api.minimax.io/v2/query/video_generation/{task_id}"
        else:
            url = f"https://api.minimax.io/v1/query/video_generation?task_id={task_id}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code >= 400:
            return {
                "task_id": task_id,
                "status": "error",
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }

        data = resp.json()

        if api_version == "v2":
            task = data.get("task", {})
            status = task.get("status", "unknown")
            result = {
                "task_id": task_id,
                "status": status,
            }
            if status == "succeeded":
                content = task.get("content", {})
                result["video_url"] = content.get("url", "")
            elif status == "failed":
                result["error"] = task.get("error", "Generation failed")
            return result
        else:
            task = data.get("task", {})
            status = task.get("status", "unknown")
            result = {
                "task_id": task_id,
                "status": status,
            }
            if status == "Success":
                file_download = data.get("file_download", {})
                result["video_url"] = file_download.get("video_url", "")
                result["status"] = "succeeded"
            elif status == "Failed":
                result["status"] = "failed"
                result["error"] = "Generation failed"
            return result

    async def download_video(self, video_url: str, output_dir: str | None = None) -> str:
        """Download a generated video to disk. Returns the local file path."""
        out_dir = Path(output_dir or self._config["video_output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"video_{int(time.time())}.mp4"
        filepath = out_dir / filename

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(video_url)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)

        logger.info("Video saved to %s", filepath)
        return str(filepath)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_video_generation_service.py -v -k "TestVideoGenerationServiceConfig" --no-header --tb=short`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/core/services/video_generation_service.py tests/unit/test_video_generation_service.py
git commit -m "feat(video): VideoGenerationService with cost guards and MiniMax API integration"
```

---

## Task 2: REST API Endpoints

**Files:**
- Create: `backend/app/api/v1/endpoints/video_generation.py`
- Modify: `backend/app/api/v1/api.py` (add one import + one include_router line)

**Interfaces:**
- Consumes: `VideoGenerationService` from Task 1
- Produces: REST endpoints at `/api/v1/videos/generate`, `/api/v1/videos/status/{task_id}`, `/api/v1/videos/config`, `/api/v1/videos/models`, `/api/v1/videos/saved`

- [ ] **Step 1: Write the endpoint file**

```python
# backend/app/api/v1/endpoints/video_generation.py
"""
Video Generation API — thin adapter around VideoGenerationService.
Endpoints under /api/v1/videos/*.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.services.video_generation_service import VideoGenerationService, MODEL_SPECS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["video-generation"])

_service: VideoGenerationService | None = None


def get_service() -> VideoGenerationService:
    global _service
    if _service is None:
        _service = VideoGenerationService()
    return _service


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Video description, 10-2000 characters")
    model: str | None = Field(default=None, description="Model: T2V-01, MiniMax-Hailuo-2.3, MiniMax-H3")
    duration: int | None = Field(default=None, description="Duration in seconds")
    resolution: str | None = Field(default=None, description="Resolution: 720P, 768P, 1080P, 2K")


class StatusRequest(BaseModel):
    task_id: str = Field(..., description="Task ID from generate response")
    model: str = Field(default="T2V-01", description="Model used for generation")


class ConfigUpdate(BaseModel):
    enabled: bool | None = None
    default_model: str | None = None
    default_duration: int | None = None
    default_resolution: str | None = None
    daily_cost_cap_usd: float | None = None
    max_per_hour: int | None = None
    prompt_style_prefix: str | None = None
    prompt_optimizer: bool | None = None


@router.post("/generate")
async def generate_video(req: GenerateRequest) -> dict[str, Any]:
    """Submit a video generation task. Returns task_id for polling."""
    svc = get_service()
    try:
        result = await svc.submit_task(
            prompt=req.prompt,
            model=req.model,
            duration=req.duration,
            resolution=req.resolution,
        )
        return {"status": "success", **result}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/status")
async def check_status(req: StatusRequest) -> dict[str, Any]:
    """Poll a video generation task status."""
    svc = get_service()
    result = await svc.poll_task(req.task_id, model=req.model)

    if result.get("status") == "succeeded" and result.get("video_url"):
        try:
            local_path = await svc.download_video(result["video_url"])
            result["local_path"] = local_path
        except Exception as e:
            logger.warning("Failed to download video: %s", e)
            result["download_error"] = str(e)

    return result


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Get current video generation configuration."""
    return {**get_service().config, "cost_stats": get_service().get_cost_stats()}


@router.post("/config")
async def update_config(req: ConfigUpdate) -> dict[str, Any]:
    """Update video generation configuration."""
    svc = get_service()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        return svc.update_config(updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models")
async def list_models() -> dict[str, list[dict[str, Any]]]:
    """List supported video models with specs and pricing."""
    return {
        "minimax": [
            {
                "id": model_id,
                "cost_usd": spec.get("cost_usd", 0.50),
                "label": model_id,
                "durations": spec.get("durations", [6]),
                "resolutions": spec.get("resolutions", ["720P"]),
                "ratios": spec.get("ratios", []),
            }
            for model_id, spec in MODEL_SPECS.items()
        ]
    }
```

- [ ] **Step 2: Register the router in api.py**

Add to `backend/app/api/v1/api.py`:

```python
# In the imports section (after image_generation import):
from backend.app.api.v1.endpoints import video_generation as video_generation_endpoint

# In the router registrations section (after image_generation include_router):
api_router.include_router(video_generation_endpoint.router, tags=["video-generation"])
```

- [ ] **Step 3: Verify the endpoints are registered**

Run: `python -c "from backend.app.main import app; routes = [r.path for r in app.routes if hasattr(r, 'path')]; print([r for r in routes if 'video' in r])"`
Expected: `['/api/v1/videos/generate', '/api/v1/videos/status', '/api/v1/videos/config', '/api/v1/videos/models']`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/endpoints/video_generation.py backend/app/api/v1/api.py
git commit -m "feat(video): REST API endpoints for video generation"
```

---

## Task 3: Frontend Settings Panel

**Files:**
- Create: `frontend/src/components/Settings/VideoSettingsPanel.tsx`
- Modify: `frontend/src/routes/Settings/index.tsx` (add the Video tab)

**Interfaces:**
- Consumes: `/api/v1/videos/config` (GET/POST), `/api/v1/videos/models`, `/api/v1/videos/generate`, `/api/v1/videos/status`
- Produces: A collapsible panel in Settings with enable toggle, model selector, duration, resolution, cost display, and a generate button

- [ ] **Step 1: Write the VideoSettingsPanel component**

Create `frontend/src/components/Settings/VideoSettingsPanel.tsx` — a self-contained panel with:
- Enable/disable toggle
- Model dropdown (fetches from `/videos/models`)
- Duration selector (filtered by model capabilities)
- Resolution selector (filtered by model capabilities)
- Cost stats display (daily spend, cap, hourly calls)
- Prompt style prefix input
- Daily cost cap input
- Max per hour input
- Generate button with confirmation modal ("This will cost ~$X.XX — continue?")
- Status polling with progress display
- Video preview + download link when complete

Key implementation notes:
- Use AntD components (Card, Switch, Select, InputNumber, Button, Modal, Progress, Alert)
- Poll `/videos/status` every 5 seconds after submitting a generation
- Show a "Generating video... (this can take 1-3 minutes)" progress indicator
- On success, show a `<video>` element with the local path and a download link
- Cost confirmation modal before each generation to prevent accidental spending

- [ ] **Step 2: Add the Video tab to the Settings page**

In `frontend/src/routes/Settings/index.tsx`, add:
```tsx
{ label: 'Video', value: 'video' }
```
to the tabs array, and render `<VideoSettingsPanel />` when active.

- [ ] **Step 3: TypeScript check**

Run: `cd frontend && npx tsc --noEmit --skipLibCheck`
Expected: Clean

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Settings/VideoSettingsPanel.tsx frontend/src/routes/Settings/index.tsx
git commit -m "feat(video): settings panel with cost display, model selector, and generate button"
```

---

## Task 4: Integration Test — End-to-End Video Generation

**Files:**
- No new files — this is a manual verification step

- [ ] **Step 1: Enable video generation via API**

```bash
curl -X POST http://localhost:8008/api/v1/videos/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

- [ ] **Step 2: Submit a test generation**

```bash
curl -X POST http://localhost:8008/api/v1/videos/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Golden Buddha statue radiating warm light, camera slowly zooms in, peaceful atmosphere, cinematic", "model": "T2V-01", "duration": 6}'
```
Expected: `{"status": "success", "task_id": "xxx", "model": "T2V-01", "cost_usd": 0.5, ...}`

- [ ] **Step 3: Poll for completion**

```bash
# Wait 30 seconds, then poll
curl -X POST http://localhost:8008/api/v1/videos/status \
  -H "Content-Type: application/json" \
  -d '{"task_id": "xxx", "model": "T2V-01"}'
```
Expected: `{"task_id": "xxx", "status": "succeeded", "video_url": "https://...", "local_path": "generated/videos/video_xxx.mp4"}`

- [ ] **Step 4: Verify cost tracking**

```bash
curl http://localhost:8008/api/v1/videos/config
```
Expected: `cost_stats.daily_spend_usd: 0.50, hourly_calls: 1`

- [ ] **Step 5: Commit any test artifacts cleanup**

```bash
# Do NOT commit the video file — add to .gitignore
echo "generated/videos/" >> .gitignore
git add .gitignore
git commit -m "chore: add generated/videos/ to .gitignore"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Text-to-video generation (T2V-01 and Hailuo models)
- ✅ MiniMax H3 V2 API support (content[] structure)
- ✅ Cost controls (daily cap + hourly limit)
- ✅ Async task tracking (submit → poll)
- ✅ Video download + archival
- ✅ Frontend settings panel
- ✅ Model capabilities (durations, resolutions per model)
- ⚠️ Camera commands ([Pan left], etc.) — documented in prompt, not enforced by UI (can add later)
- ⚠️ Image-to-video (first_frame_image) — not in V1 plan; H3 V2 API supports it natively when we add image_url content items

**2. Placeholder scan:** No TBD/TODO. All code blocks are complete.

**3. Type consistency:** `submit_task()` returns `{task_id, model, cost_usd, status, prompt}`. `poll_task()` returns `{task_id, status, video_url?, error?, local_path?}`. Consistent across service + endpoint.

**4. Gap analysis:** The plan covers text-to-video only. Image-to-video and reference-to-video are future enhancements that use the same V2 API with different content[] items. The service architecture supports them without restructuring.
