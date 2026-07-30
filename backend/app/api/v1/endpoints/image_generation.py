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
from datetime import datetime, timezone
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
    """Lazy-init the service singleton. Pulls persisted config from DB."""
    global _service
    if _service is None:
        _service = ImageGenerationService()
        _load_config_from_db(_service)
    return _service


# ── DB helpers ─────────────────────────────────────────────────────────


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() or (parent / "vajra_stream.db").exists():
            return parent
    return here.parent


def _db_path() -> str:
    env = os.environ.get("VAJRA_DB_PATH")
    if env:
        return env
    root = _project_root()
    candidate = root / "vajra_stream.db"
    if candidate.exists():
        return str(candidate)
    mirror = root / "backend" / "app" / "vajra_stream.db"
    if mirror.exists():
        return str(mirror)
    return str(candidate)


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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _save_config_to_db(updates)
    cfg = dict(service.config)
    for key_field in ("openrouter_api_key", "minimax_api_key"):
        cfg[key_field] = _mask_key(cfg.get(key_field))  # type: ignore[assignment]
    return {"status": "ok", "config": cfg, "cost_stats": service.get_cost_stats()}


@router.get("/models")
async def list_models() -> dict[str, list[dict[str, Any]]]:
    """List supported models per provider with cost estimates."""
    return {
        "openrouter": [
            {"id": "google/gemini-3.1-flash-lite-image", "cost_usd": 0.008, "label": "Gemini 3.1 Flash Lite (cheap)"},
            {"id": "black-forest-labs/flux.2-klein-4b", "cost_usd": 0.014, "label": "FLUX.2 Klein 4B (premium)"},
            {"id": "krea/krea-2-large", "cost_usd": 0.06, "label": "Krea 2 Large (artistic)"},
            {"id": "microsoft/mai-image-2.5-pro", "cost_usd": 0.10, "label": "MAI Image 2.5 Pro (top)"},
        ],
        "minimax": [
            {"id": "image-01", "cost_usd": 0.02, "label": "MiniMax image-01 (subject reference)"},
        ],
    }


@router.post("/validate_prompt")
async def validate_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    """Check if a prompt fits the configured token budget."""
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise HTTPException(status_code=400, detail="prompt must be a string")
    return get_service().validate_prompt(prompt)


@router.get("/saved")
async def list_saved_images() -> dict[str, Any]:
    """List previously saved images from the output directory (QA / audit)."""

    service: ImageGenerationService = get_service()
    out_dir = Path(service.config.get("image_output_dir", "generated/images"))
    if not out_dir.exists():
        return {"images": [], "output_dir": str(out_dir)}

    files = sorted(out_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    images = []
    for f in files[:50]:
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            stat = f.stat()
            images.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                }
            )
    return {"images": images, "output_dir": str(out_dir)}
