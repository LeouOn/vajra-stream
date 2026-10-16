"""
Image Generation API — thin adapter around the modular ImageGenerationService.

The service itself lives at backend/core/services/image_generation_service.py
and has zero project dependencies — it can be extracted to a standalone repo
by copying just that file plus `pip install httpx`.

This module is the only place that touches the rest of the Vajra.Stream
codebase: it reads/writes the DB-backed config and exposes the public
HTTP surface under /api/v1/images/*.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.services.image_generation_service import ImageGenerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# ── Module-level singleton ─────────────────────────────────────────────
_service: ImageGenerationService | None = None


def get_service() -> ImageGenerationService:
    """Lazy-init the service singleton. Pulls persisted config from DB.

    Falls back to project-level settings / env vars for API keys not
    explicitly stored in the image-generation config table. This avoids
    requiring the user to enter the same OpenRouter key twice (once for
    LLM, once for image generation).
    """
    global _service
    if _service is None:
        _service = ImageGenerationService()
        _load_config_from_db(_service)
        _inject_fallback_keys(_service)
        _anchor_output_dir(_service)
    return _service


def hosted_output_dir() -> Path:
    """Where hosted generations are saved: ``image_output_dir``, anchored at the project root.

    The standalone service resolves a relative directory against the process
    cwd; this adapter never lets that happen (:func:`_anchor_output_dir`), so
    saving and the gallery that lists the saves agree whatever the cwd is.
    """
    return _anchored(get_service().config.get("image_output_dir") or "generated/images")


def _anchored(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    from core.schema import get_project_root

    return get_project_root() / path


def _anchor_output_dir(service: ImageGenerationService) -> None:
    """Rewrite a relative ``image_output_dir`` (the default) as an absolute project-root path."""
    raw = str(service.config.get("image_output_dir") or "generated/images")
    if not Path(raw).is_absolute():
        service.update_config({"image_output_dir": str(_anchored(raw))})


def _inject_fallback_keys(service: ImageGenerationService) -> None:
    """Fill empty API key slots from project settings or env vars."""
    fallbacks: dict[str, str] = {}
    if not service.config.get("openrouter_api_key"):
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            from config.backend_settings import backend_settings

            key = getattr(backend_settings, "OPENROUTER_API_KEY", "")
        if key:
            fallbacks["openrouter_api_key"] = key
    if not service.config.get("minimax_api_key"):
        key = os.environ.get("MINIMAX_API_KEY", "")
        if key:
            fallbacks["minimax_api_key"] = key
    if fallbacks:
        service.update_config(fallbacks)


# ── DB helpers ─────────────────────────────────────────────────────────


def _db_path() -> str:
    """Locate the SQLite database file via core.schema.get_db_path."""
    from core.schema import get_db_path

    return get_db_path()


def _connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_config_table() -> None:
    conn = _connect_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image_generation_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _load_config_from_db(service: ImageGenerationService) -> None:
    """Load persisted config from SQLite into the service."""
    try:
        _ensure_config_table()
        conn = _connect_db()
        try:
            rows = conn.execute("SELECT key, value FROM image_generation_config").fetchall()
        finally:
            conn.close()
        if not rows:
            return
        updates: dict[str, Any] = {}
        for row in rows:
            key, value = row["key"], row["value"]
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
        try:
            service.update_config(updates)
        except ValueError as exc:
            logger.warning("Skipping unknown persisted image-gen keys: %s", exc)
    except Exception as exc:  # noqa: BLE001 — DB never blocks service startup
        logger.warning("Could not load image generation config from DB: %s", exc)


def _save_config_to_db(updates: dict[str, Any]) -> None:
    _ensure_config_table()
    conn = _connect_db()
    try:
        for key, value in updates.items():
            conn.execute(
                """
                INSERT INTO image_generation_config (key, value)
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
    prompt: str = Field(..., min_length=1, max_length=4000, description="Image description (max 1000 tokens)")
    provider: str | None = Field(default=None, description="openrouter or minimax")
    model: str | None = Field(default=None, description="Model slug")
    size: str = Field(default="1024x1024", description="1024x1024, 1792x1024, 1024x1792")
    quality: str = Field(default="standard", description="standard or hd")
    n: int = Field(default=1, ge=1, le=10, description="Number of images (1-10)")
    aspect_ratio: str | None = Field(default=None, description="MiniMax only: 1:1, 16:9, etc.")
    subject_reference: str | None = Field(default=None, description="MiniMax only: URL of reference image")


class GenerateResponse(BaseModel):
    image_data_url: str
    model: str
    cost_usd: float
    provider_used: str
    cached: bool
    revised_prompt: str | None = None
    prompt_tokens: int = 0
    image_file_path: str | None = None


class ConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    default_provider: str | None = None
    default_model: str | None = None
    daily_cost_cap_usd: float | None = Field(default=None, gt=0)
    max_images_per_call: int | None = Field(default=None, ge=1, le=10)
    max_per_hour: int | None = Field(default=None, ge=1, le=1000)
    cache_ttl_seconds: int | None = Field(default=None, ge=0, le=86400)
    max_prompt_tokens: int | None = Field(default=None, ge=100, le=4000)
    prompt_style_prefix: str | None = Field(default=None, max_length=500)
    prompt_negative: str | None = Field(default=None, max_length=500)
    image_output_dir: str | None = Field(default=None, max_length=255)
    model_lock: bool | None = None
    default_aspect_ratio: str | None = Field(default=None, max_length=10)
    openrouter_api_key: str | None = None
    minimax_api_key: str | None = None


# ── Routes ─────────────────────────────────────────────────────────────


@router.post("/generate", response_model=GenerateResponse)
async def generate_image(request: GenerateRequest) -> GenerateResponse:
    """Generate an image using the configured provider.

    The service enforces prompt-length, daily-cost, and per-hour caps.
    """
    try:
        service = get_service()
        result = await service.generate(
            prompt=request.prompt,
            provider=request.provider,
            model=request.model,
            size=request.size,
            quality=request.quality,
            n=request.n,
            aspect_ratio=request.aspect_ratio,
            subject_reference=request.subject_reference,
        )
        return GenerateResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — last-resort 500
        logger.exception("Image generation failed")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {exc}") from exc


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Return current config (API keys masked) plus live cost stats."""
    service = get_service()
    cfg = dict(service.config)
    for key_field in ("openrouter_api_key", "minimax_api_key"):
        cfg[key_field] = _mask_key(cfg.get(key_field))  # type: ignore[assignment]
    return {"config": cfg, "cost_stats": service.get_cost_stats()}


@router.post("/config")
async def update_config(request: ConfigUpdateRequest) -> dict[str, Any]:
    """Update one or more config keys. Persists to SQLite."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")
    try:
        service = get_service()
        service.update_config(updates)
        _anchor_output_dir(service)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _save_config_to_db(updates)
    cfg = dict(service.config)
    for key_field in ("openrouter_api_key", "minimax_api_key"):
        cfg[key_field] = _mask_key(cfg.get(key_field))  # type: ignore[assignment]
    return {"status": "ok", "config": cfg, "cost_stats": service.get_cost_stats()}


@router.get("/models")
async def list_models() -> dict[str, list[dict[str, Any]]]:
    """List supported models per provider with cost estimates and capabilities."""
    from backend.core.services.image_generation_service import MODEL_CAPABILITIES

    def _model_entry(model_id: str, cost: float, label: str) -> dict[str, Any]:
        caps = MODEL_CAPABILITIES.get(model_id, {})
        return {
            "id": model_id,
            "cost_usd": cost,
            "label": label,
            "aspect_ratios": caps.get("aspect_ratios", ["1:1"]),
            "resolutions": caps.get("resolutions", ["1K"]),
        }

    return {
        "openrouter": [
            _model_entry("google/gemini-3.1-flash-lite-image", 0.008, "Gemini 3.1 Flash Lite (cheap)"),
            _model_entry("black-forest-labs/flux.2-klein-4b", 0.014, "FLUX.2 Klein 4B (premium)"),
            _model_entry("krea/krea-2-large", 0.06, "Krea 2 Large (artistic)"),
            _model_entry("microsoft/mai-image-2.5-pro", 0.10, "MAI Image 2.5 Pro (top)"),
        ],
        "minimax": [
            _model_entry("image-01", 0.02, "MiniMax image-01 (subject reference)"),
        ],
    }


@router.post("/validate_prompt")
async def validate_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    """Check if a prompt fits the configured token budget."""
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise HTTPException(status_code=400, detail="prompt must be a string")
    return get_service().validate_prompt(prompt)


# ``GET /images/saved`` was retired on 2026-10-15: it had no caller, returned
# filesystem paths it could not serve, and stopped at 50 files. Saved hosted
# images are listed by ``GET /gallery?source=hosted`` and served by
# ``GET /gallery/hosted/{filename}`` (backend/app/api/v1/endpoints/gallery.py).
