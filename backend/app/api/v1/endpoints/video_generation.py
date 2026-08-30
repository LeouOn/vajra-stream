"""
Video Generation API — thin adapter around the modular VideoGenerationService.

The service itself lives at backend/core/services/video_generation_service.py
and has zero project dependencies — it can be extracted to a standalone repo
by copying just that file plus ``pip install httpx``.

This module is the only place that touches the rest of the Vajra.Stream
codebase: it reads/writes the DB-backed config and exposes the public
HTTP surface under /api/v1/videos/*.

The MiniMax video API is asynchronous: ``POST /generate`` submits a task and
returns a ``task_id``; clients then call ``POST /status`` to poll until the
video is ready (and we auto-download it on success).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.core.services.video_generation_service import (
    DEFAULT_CONFIG,
    MODEL_SPECS,
    VideoGenerationService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["video-generation"])

# ── Module-level singleton ─────────────────────────────────────────────
_service: VideoGenerationService | None = None


def get_service() -> VideoGenerationService:
    """Lazy-init the service singleton. Pulls persisted config from DB.

    Falls back to ``MINIMAX_API_KEY`` env var when neither DB nor service
    config has a key set. This avoids requiring the user to enter the same
    key twice (once for LLM/image, once for video).
    """
    global _service
    if _service is None:
        _service = VideoGenerationService()
        _load_config_from_db(_service)
        _inject_fallback_keys(_service)
    return _service


def _inject_fallback_keys(service: VideoGenerationService) -> None:
    """Fill empty API key slots from project settings or env vars."""
    if not service.config.get("minimax_api_key"):
        key = os.environ.get("MINIMAX_API_KEY", "")
        if not key:
            from backend.app.config import settings

            key = getattr(settings, "MINIMAX_API_KEY", "")
        if key:
            service.update_config({"minimax_api_key": key})


# ── DB helpers ─────────────────────────────────────────────────────────


def _db_path() -> str:
    """Locate the SQLite database file.

    Prefers ``VAJRA_DB_PATH`` env var if set, then a project-root
    ``vajra_stream.db``, then the mirrored backend copy.
    """
    env = os.environ.get("VAJRA_DB_PATH")
    if env:
        return env
    # Discover project root by walking parents of this file
    here = os.path.abspath(__file__)
    cursor = os.path.dirname(here)
    for _ in range(8):
        candidate = os.path.join(cursor, "vajra_stream.db")
        if os.path.exists(candidate):
            return candidate
        cursor = os.path.dirname(cursor)
    # Fall back to the conventional mirrored path
    return os.path.join(os.path.abspath(os.path.join(os.path.dirname(here), "..", "..", "..", "vajra_stream.db")))


def _connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_config_table() -> None:
    conn = _connect_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS video_generation_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _load_config_from_db(service: VideoGenerationService) -> None:
    """Load persisted config from SQLite into the service."""
    try:
        _ensure_config_table()
        conn = _connect_db()
        try:
            rows = conn.execute("SELECT key, value FROM video_generation_config").fetchall()
        finally:
            conn.close()
        if not rows:
            return
        updates: dict[str, Any] = {}
        for row in rows:
            key, value = row["key"], row["value"]
            if key not in DEFAULT_CONFIG:
                continue
            try:
                updates[key] = int(value)
            except (TypeError, ValueError):
                try:
                    updates[key] = float(value)
                except (TypeError, ValueError):
                    if value.lower() in ("true", "false"):
                        updates[key] = value.lower() == "true"
                    else:
                        updates[key] = value
        if updates:
            service.update_config(updates)
    except Exception as exc:  # noqa: BLE001 — DB never blocks service startup
        logger.warning("Could not load video generation config from DB: %s", exc)


def _save_config_to_db(updates: dict[str, Any]) -> None:
    _ensure_config_table()
    conn = _connect_db()
    try:
        for key, value in updates.items():
            conn.execute(
                """
                INSERT INTO video_generation_config (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, str(value)),
            )
        conn.commit()
    finally:
        conn.close()


def _mask_key(value: str | None) -> str | None:
    """Mask API keys for safe display."""
    if not value:
        return value
    if len(value) <= 10:
        return "***"
    return f"{value[:6]}…{value[-4:]}"


# ── Pydantic models ────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Video description")
    model: str | None = Field(default=None, description="Model slug (T2V-01, MiniMax-Hailuo-2.3, MiniMax-H3)")
    duration: int | None = Field(default=None, ge=1, le=60, description="Duration in seconds (model-dependent)")
    resolution: str | None = Field(default=None, description="Resolution (720P, 768P, 1080P, 2K)")
    ratio: str | None = Field(default=None, description="Aspect ratio (MiniMax-H3 only: 16:9, 1:1, ...)")


class StatusRequest(BaseModel):
    task_id: str = Field(..., min_length=1, description="Task ID returned from /generate")
    model: str = Field(..., description="Model used to submit the task")


class ConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    default_model: str | None = None
    default_duration: int | None = Field(default=None, ge=1, le=60)
    default_resolution: str | None = None
    daily_cost_cap_usd: float | None = Field(default=None, gt=0)
    max_per_hour: int | None = Field(default=None, ge=1, le=1000)
    prompt_style_prefix: str | None = Field(default=None, max_length=500)
    prompt_optimizer: bool | None = None


# ── Routes ─────────────────────────────────────────────────────────────


GENRE_VIDEO_PRINCIPLES: dict[str, str] = {
    "healing": "Soft greens, lapis blue water light, gentle slow camera. Lotus imagery. Warm golden particles rising. Healing energy radiating outward in concentric rings. [Push in] slowly, then [Static shot] on a luminous center.",
    "victory": "Bold dynamic camera, golden-red light breaking through clouds. A figure standing triumphant on a summit. Crackling energy shields forming. [Pan right] across a battlefield dissolved into flowers, then [Tracking shot] of a banner unfurling.",
    "alchemist": "Cinematic close-ups of molten metal transforming in a crucible. Steam rising with flecks of gold. Color grading shifting from leaden grey to radiant gold. [Pedestal up] to reveal the Philosopher's Stone glowing.",
    "dharani": "Sacred syllables materializing as luminous Sanskrit characters floating in dark space, rotating slowly. Mantric energy spiraling into a mandala pattern. [Static shot] on the mandala as it pulses with each syllable, then [Zoom out] to reveal the whole field.",
    "compassion": "Soft pink and rose-gold light, rose petals falling in slow motion. A heart-center opening like a lotus bloom. Compassion radiating as warm waves. [Push in] very slowly toward the heart of the light.",
    "wisdom": "Library of infinite scrolls dissolving into stars. An eye opening in the center of a book. Blue-white clarity light cutting through fog. [Pan left] across the scrolls, then [Tilt up] to a starfield of knowledge.",
    "protection": "Vajra (thunderbolt) geometry forming a crystalline shield around a central figure. Lightning fractals of protective energy. Deep blue and electric cyan. [Static shot] on the shield pulsing, then [Zoom out] to show the full protective dome.",
    "fun_parable": "Whimsical, colorful, storybook illustration style. A trickster figure dancing through a landscape that shifts seasons with each step. [Tracking shot] following the figure, playful and light.",
}

LOOPABLE_PRINCIPLES = (
    "LOOPABILITY: Design the motion so the ending frame visually echoes the beginning frame — "
    "a circular camera path, a returning particle, a breath cycle. The video should feel "
    "seamless when looped. Avoid hard cuts or final-frame compositions that break the cycle."
)

SACRED_AESTHETIC = (
    "SACRED AESTHETIC: Cinematic lighting with volumetric god-rays. Particles of light that "
    "behave like prayer energy. Color palette grounded in the genre's planetary frequency. "
    "Depth of field that draws the eye to a luminous focal point. Ethereal, otherworldly, "
    "meditative — never harsh or chaotic."
)


@router.post("/from-narrative")
async def generate_from_narrative(
    payload: dict[str, Any],
    http_request: Request,
) -> dict[str, Any]:
    """Transform an outlook narrative into a video generation prompt, then submit to MiniMax.

    Accepts either:
    - {"narrative_id": 123} — fetches from outlook history DB
    - {"narrative": "text...", "genre": "healing", "entities": "...", "divination": "..."} — inline

    The LLM transforms the narrative into a structured video prompt incorporating:
    - Genre-specific camera movements and visual themes
    - Loopability principles (seamless loop design)
    - Sacred aesthetic guidelines
    - MiniMax camera command syntax ([Push in], [Pan left], etc.)
    """
    service = get_service()
    if not service.config.get("enabled", False):
        raise HTTPException(status_code=400, detail="Video generation is disabled in config")

    narrative_text = ""
    genre = "healing"
    entities = ""
    divination = ""

    if "narrative_id" in payload:
        from backend.app.api.v1.endpoints.outlook import get_db_connection

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT content, genre, entities_invoked, divination_context FROM outlook_narratives WHERE id = ?",
                (payload["narrative_id"],),
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                raise HTTPException(status_code=404, detail="Narrative not found")
            narrative_text = row["content"] or ""
            genre = row["genre"] or "healing"
            entities = row["entities_invoked"] or ""
            divination = row["divination_context"] or ""
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB error: {e}")
    else:
        narrative_text = payload.get("narrative", "")
        genre = payload.get("genre", "healing")
        entities = payload.get("entities", "")
        divination = payload.get("divination", "")

    if not narrative_text or len(narrative_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Narrative too short for video prompt extraction (need 50+ chars)")

    genre_visual = GENRE_VIDEO_PRINCIPLES.get(genre, GENRE_VIDEO_PRINCIPLES["healing"])

    system_prompt = f"""You are a master film director and cinematographer specializing in sacred, contemplative video art. Your task is to transform a spiritual blessing narrative into a single, powerful video generation prompt.

## VISUAL DIRECTION FOR THIS GENUE
{genre_visual}

## {LOOPABLE_PRINCIPLES}

## {SACRED_AESTHETIC}

## RULES
1. Output ONLY the video prompt — no preamble, no explanation, no headers.
2. Keep it under 1500 characters (MiniMax limit is 2000, we leave room).
3. Use MiniMax camera commands in [brackets]: [Push in], [Pan left], [Static shot], [Zoom out], [Tracking shot], [Pedestal up], [Tilt down], [Pull out], [Truck right], etc.
4. Describe ONE continuous shot that loops seamlessly.
5. Include: setting/scene, lighting, color palette, camera movement, motion/animation of elements, and mood.
6. Ground the imagery in the narrative's actual content — don't invent unrelated scenes.
7. The prompt should be vivid enough that someone who hasn't read the narrative can picture the scene.

## NARRATIVE TO TRANSFORM
{narrative_text[:3000]}

## ADDITIONAL CONTEXT
- Entities invoked: {entities[:200] if entities else "N/A"}
- Divination/oracle: {divination[:200] if divination else "N/A"}
"""

    from core.llm.base import strip_thinking

    registry = getattr(http_request.app.state, "llm_registry", None)
    if not registry or len(registry) == 0:
        raise HTTPException(status_code=503, detail="No LLM providers available for prompt transformation")

    provider = await registry.pick_best()
    if not provider:
        raise HTTPException(status_code=503, detail="No healthy LLM provider available")

    from core.llm.models import ChatRequest

    chat_req = ChatRequest(
        messages=[{"role": "user", "content": "Transform the narrative above into a video generation prompt."}],
        system_prompt=system_prompt,
        max_tokens=800,
        temperature=0.8,
        model=None,
        stream=False,
        tools=[],
    )

    try:
        response = await provider.generate(chat_req)
        video_prompt, _ = strip_thinking(response.content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM prompt transformation failed: {e}")

    video_prompt = video_prompt.strip()
    if not video_prompt or len(video_prompt) < 20:
        raise HTTPException(status_code=500, detail="LLM produced an empty video prompt")

    model = payload.get("model", service.config.get("default_model", "MiniMax-H3"))
    duration = payload.get("duration", service.config.get("default_duration", 5))

    try:
        result = await service.submit_task(
            prompt=video_prompt,
            model=model,
            duration=duration,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "status": "success",
        "video_prompt": video_prompt[:500],
        "narrative_genre": genre,
        **result,
    }


@router.post("/generate")
async def generate_video(request: GenerateRequest) -> dict[str, Any]:
    """Submit a video generation task to MiniMax.

    Returns the ``task_id`` for polling via ``POST /status``. The service
    enforces the daily cost cap and per-hour rate limit before submitting.
    """
    service = get_service()
    if not service.config.get("enabled", False):
        raise HTTPException(status_code=400, detail="Video generation is disabled in config")

    try:
        task_id = await service.submit_task(
            prompt=request.prompt,
            model=request.model,
            duration=request.duration,
            resolution=request.resolution,
            ratio=request.ratio,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — last-resort 500
        logger.exception("Video generation submit failed")
        raise HTTPException(status_code=500, detail=f"Video generation failed: {exc}") from exc

    model_used = request.model or service.config["default_model"]
    cost_usd = MODEL_SPECS.get(model_used, {}).get("cost_usd", 0.0)

    # Server-side completion watcher — polls + downloads even if the
    # browser tab navigates away, so paid MiniMax output always lands
    # on disk at generated/videos/.
    asyncio.get_event_loop().create_task(_watch_video_task(service, task_id, model_used))

    return {
        "status": "submitted",
        "task_id": task_id,
        "model": model_used,
        "cost_usd": cost_usd,
        "prompt": request.prompt,
    }


async def _watch_video_task(service, task_id: str, model: str) -> None:
    """Poll a video task in the background until done, then auto-download.

    Interval matches the frontend poller (5 s); timeout matches the
    configured poll_timeout_seconds so runaway tasks are bounded.
    """
    import asyncio

    poll_interval = 5.0
    max_wait = service.config.get("poll_timeout_seconds", 600)
    deadline = asyncio.get_event_loop().time() + max_wait

    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(poll_interval)
        try:
            status = await service.poll_task(task_id, model)
            if status.status == "done" and status.video_url:
                try:
                    await service.download_video(status.video_url)
                    logger.info("Video %s auto-downloaded to %s", task_id, service.config["video_output_dir"])
                except RuntimeError as exc:
                    logger.warning("Auto-download failed for video %s: %s", task_id, exc)
                return
            if status.status == "failed":
                logger.warning("Video %s failed on MiniMax side", task_id)
                return
        except Exception:
            logger.debug("Background video poll error for %s", task_id, exc_info=True)


@router.post("/status")
async def poll_status(request: StatusRequest) -> dict[str, Any]:
    """Poll a previously submitted video task.

    When the task is ``done``, the video is auto-downloaded to the configured
    output directory and the local path is returned alongside ``video_url``.
    """
    service = get_service()
    try:
        status = await service.poll_task(task_id=request.task_id, model=request.model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — last-resort 500
        logger.exception("Video poll failed")
        raise HTTPException(status_code=500, detail=f"Video poll failed: {exc}") from exc

    payload: dict[str, Any] = {
        "task_id": status.task_id,
        "status": status.status,
    }
    if status.video_url:
        payload["video_url"] = status.video_url
    if status.status == "done" and status.video_url:
        try:
            local_path = await service.download_video(status.video_url)
            payload["local_path"] = local_path
        except RuntimeError as exc:
            # Don't fail the whole poll — surface the download error in the response
            logger.warning("Auto-download failed for task %s: %s", status.task_id, exc)
            payload["download_error"] = str(exc)
    if status.error:
        payload["error"] = status.error
    return payload


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Return current config (API key masked) plus live cost stats."""
    service = get_service()
    cfg = dict(service.config)
    cfg["minimax_api_key"] = _mask_key(cfg.get("minimax_api_key"))  # type: ignore[assignment]
    return {"config": cfg, "cost_stats": service.get_cost_stats()}


@router.post("/config")
async def update_config(request: ConfigUpdateRequest) -> dict[str, Any]:
    """Update one or more video-generation config keys. Persists to SQLite."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")
    service = get_service()
    try:
        service.update_config(updates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _save_config_to_db(updates)
    cfg = dict(service.config)
    cfg["minimax_api_key"] = _mask_key(cfg.get("minimax_api_key"))  # type: ignore[assignment]
    return {"status": "ok", "config": cfg, "cost_stats": service.get_cost_stats()}


@router.get("/models")
async def list_models() -> list[dict[str, Any]]:
    """List supported video models with cost, durations, resolutions, and ratios."""
    models: list[dict[str, Any]] = []
    for model_id, specs in MODEL_SPECS.items():
        entry: dict[str, Any] = {
            "id": model_id,
            "cost_usd": specs.get("cost_usd", 0.0),
            "label": model_id,
            "durations": specs.get("durations", []),
            "resolutions": specs.get("resolutions", []),
        }
        if "ratios" in specs:
            entry["ratios"] = specs["ratios"]
        models.append(entry)
    return models


@router.post("/validate_prompt")
async def validate_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    """Check if a prompt fits the configured character budget."""
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise HTTPException(status_code=400, detail="prompt must be a string")
    return get_service().validate_prompt(prompt)
