"""
Video Generation Service — MiniMax async video generation API.

Self-contained, zero project dependencies (only ``httpx``). Can be extracted
to a standalone repo by copying this file plus ``pip install httpx``.

The MiniMax API is asynchronous: ``submit_task`` returns a ``task_id`` that
must be polled via ``poll_task`` until the video is ready, then downloaded
via ``download_video``.

Cost guards:
    - ``daily_cost_cap_usd`` (default $2.00) — projected daily spend check.
    - ``max_per_hour`` (default 2) — rolling 1h call-rate check.

Usage:
    from video_generation_service import VideoGenerationService

    service = VideoGenerationService({
        "minimax_api_key": os.environ.get("MINIMAX_API_KEY", ""),
        "default_model": "T2V-01",
    })

    task_id = await service.submit_task(
        prompt="A gentle prayer bowl vibration in soft morning light",
        model="T2V-01",
    )
    while True:
        status = await service.poll_task(task_id, model="T2V-01")
        if status["status"] == "done":
            await service.download_video(status["video_url"], "out/videos")
            break
        await asyncio.sleep(5)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ── Config ──────────────────────────────────────────────────────────────

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "minimax_api_key": "",
    "default_model": "T2V-01",
    "daily_cost_cap_usd": 2.0,
    "max_per_hour": 2,
    "default_duration": 6,
    "default_resolution": "720P",
    "default_ratio": "16:9",
    "max_prompt_chars": 2000,
    "video_output_dir": "generated/videos",
    "poll_interval_seconds": 5,
    "poll_timeout_seconds": 600,
}

# Per-model capabilities. ``api_version`` selects the endpoint shape
# (v1 flat-body vs. v2 content-array). ``ratios`` is v2-only.
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


# ── Errors ──────────────────────────────────────────────────────────────


class VideoGenerationError(RuntimeError):
    """Base class for video generation failures."""


# ── Service ────────────────────────────────────────────────────────────


@dataclass
class TaskStatus:
    """Result of polling a MiniMax video task."""

    task_id: str
    status: str  # "pending" | "processing" | "done" | "failed"
    video_url: str | None = None
    error: str | None = None
    raw: dict[str, Any] | None = None


class VideoGenerationService:
    """MiniMax async video generation service.

    Constructor takes a config dict; no globals, no container, no event bus.
    Reads ``MINIMAX_API_KEY`` from env when not provided in config.
    """

    BASE_URL = "https://api.minimax.io"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = dict(DEFAULT_CONFIG)
        if config:
            self._config.update(config)

        # Fall back to env if still empty
        if not self._config.get("minimax_api_key"):
            self._config["minimax_api_key"] = os.environ.get("MINIMAX_API_KEY", "")

        # Cost-tracking state (instance-local, reset on restart)
        self._daily_spend: dict[str, float] = {}
        self._hourly_calls: list[float] = []

    # ── Config ─────────────────────────────────────────────────────────

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge known config keys. Raises ``ValueError`` for unknown keys."""
        unknown = set(updates) - set(DEFAULT_CONFIG)
        if unknown:
            raise ValueError(f"unknown config key(s): {sorted(unknown)}")
        self._config.update(updates)
        return self.config

    # ── Validation ─────────────────────────────────────────────────────

    def validate_prompt(self, prompt: str) -> dict[str, Any]:
        """Validate prompt length and minimum substance.

        Returns ``{"ok": bool, "error"?: str, "length": int}``.
        """
        if not prompt or not prompt.strip():
            return {"ok": False, "error": "Prompt is empty.", "length": 0}

        stripped = prompt.strip()
        if len(stripped) < 3:
            return {"ok": False, "error": "Prompt is too short (min 3 chars).", "length": len(stripped)}

        max_chars = int(self._config.get("max_prompt_chars", 2000))
        if len(prompt) > max_chars:
            return {
                "ok": False,
                "error": f"Prompt exceeds {max_chars} char limit (got {len(prompt)}).",
                "length": len(prompt),
            }

        return {"ok": True, "length": len(prompt)}

    # ── Cost tracking ──────────────────────────────────────────────────

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

    def _check_cost_guard(self, model: str) -> None:
        """Raise ``RuntimeError`` if submitting this model would breach cost/rate limits.

        Resolves the per-call cost from ``MODEL_SPECS``; unknown models use
        a $0 fallback so the guard is conservative (never over-charges).
        Callers are responsible for the ``enabled`` gate — this method always
        enforces limits so it can be unit-tested in isolation.
        """
        cost = MODEL_SPECS.get(model, {}).get("cost_usd", 0.0)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        projected = self._daily_spend.get(today, 0.0) + cost
        if projected > self._config["daily_cost_cap_usd"]:
            raise RuntimeError(
                f"Request would breach daily cost cap (${projected:.4f} > ${self._config['daily_cost_cap_usd']:.4f})"
            )

        now = time.time()
        self._hourly_calls = [t for t in self._hourly_calls if now - t < 3600]
        if len(self._hourly_calls) >= self._config["max_per_hour"]:
            raise RuntimeError(f"max_per_hour={self._config['max_per_hour']} reached; try again later")

    def _record_spend(self, model: str) -> None:
        """Add a successful submission to the cost ledger."""
        cost = MODEL_SPECS.get(model, {}).get("cost_usd", 0.0)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._daily_spend[today] = self._daily_spend.get(today, 0.0) + cost
        self._hourly_calls.append(time.time())

    # ── Public API ─────────────────────────────────────────────────────

    def _require_key(self) -> str:
        key = self._config.get("minimax_api_key", "")
        if not key:
            raise VideoGenerationError("MiniMax API key not configured")
        return key

    def _specs_for(self, model: str) -> dict[str, Any]:
        specs = MODEL_SPECS.get(model)
        if not specs:
            raise VideoGenerationError(f"Unknown model: {model!r}. Known: {sorted(MODEL_SPECS)}")
        return specs

    @staticmethod
    def _validate_within_specs(
        *,
        model: str,
        specs: dict[str, Any],
        duration: int,
        resolution: str,
        ratio: str | None = None,
    ) -> None:
        if duration not in specs.get("durations", []):
            raise VideoGenerationError(
                f"Model {model} does not support duration={duration}s (supported: {specs.get('durations', [])})"
            )
        if resolution not in specs.get("resolutions", []):
            raise VideoGenerationError(
                f"Model {model} does not support resolution={resolution} (supported: {specs.get('resolutions', [])})"
            )
        if ratio is not None:
            supported_ratios = specs.get("ratios", [])
            if supported_ratios and ratio not in supported_ratios:
                raise VideoGenerationError(
                    f"Model {model} does not support ratio={ratio} (supported: {supported_ratios})"
                )

    async def submit_task(
        self,
        prompt: str,
        model: str | None = None,
        duration: int | None = None,
        resolution: str | None = None,
        ratio: str | None = None,
    ) -> str:
        """Submit a video generation task. Returns the ``task_id`` for polling.

        Raises ``VideoGenerationError`` on validation failure or HTTP error.
        Raises ``RuntimeError`` from the cost guard if limits would be breached.
        """
        cfg = self._config
        model_name = model or cfg["default_model"]
        duration_val = int(duration if duration is not None else cfg["default_duration"])
        resolution_val = resolution or cfg["default_resolution"]
        ratio_val = ratio or cfg.get("default_ratio")

        validation = self.validate_prompt(prompt)
        if not validation["ok"]:
            raise VideoGenerationError(validation["error"])

        specs = self._specs_for(model_name)
        self._validate_within_specs(
            model=model_name,
            specs=specs,
            duration=duration_val,
            resolution=resolution_val,
            ratio=ratio_val,
        )

        self._check_cost_guard(model_name)

        api_version = specs["api_version"]
        url = f"{self.BASE_URL}/{api_version}/video_generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._require_key()}",
        }

        if api_version == "v1":
            body: dict[str, Any] = {
                "model": model_name,
                "prompt": prompt,
                "prompt_optimizer": True,
                "duration": duration_val,
                "resolution": resolution_val,
            }
        else:  # v2
            body = {
                "model": model_name,
                "content": [{"type": "text", "text": prompt}],
                "duration": duration_val,
                "resolution": resolution_val,
                "ratio": ratio_val,
            }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise VideoGenerationError(f"MiniMax transport error: {exc}") from exc

        if resp.status_code >= 400:
            raise VideoGenerationError(f"MiniMax video API error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        task_id = data.get("task_id") or data.get("data", {}).get("task_id")
        if not task_id:
            raise VideoGenerationError(f"MiniMax response missing task_id: {data}")

        self._record_spend(model_name)
        return str(task_id)

    async def poll_task(self, task_id: str, model: str) -> TaskStatus:
        """Poll MiniMax for a submitted task's status.

        Returns a ``TaskStatus`` whose ``status`` field is one of:
        ``"pending"``, ``"processing"``, ``"done"``, ``"failed"``.
        When ``status == "done"``, ``video_url`` is populated.
        """
        specs = self._specs_for(model)
        api_version = specs["api_version"]
        if api_version == "v1":
            url = f"{self.BASE_URL}/v1/query/video_generation"
            params: dict[str, Any] = {"task_id": task_id}
        else:
            url = f"{self.BASE_URL}/v2/query/video_generation/{task_id}"
            params = {}

        headers = {"Authorization": f"Bearer {self._require_key()}"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=headers, params=params)
        except httpx.HTTPError as exc:
            raise VideoGenerationError(f"MiniMax poll transport error: {exc}") from exc

        if resp.status_code >= 400:
            raise VideoGenerationError(f"MiniMax query error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        # Normalize status across the two API versions
        raw_status = data.get("status") or data.get("state") or data.get("data", {}).get("status") or "pending"
        status = str(raw_status).lower()

        video_url = (
            data.get("video_url") or data.get("data", {}).get("video_url") or data.get("data", {}).get("download_url")
        )

        return TaskStatus(
            task_id=task_id,
            status=status,
            video_url=str(video_url) if video_url else None,
            error=data.get("error") or data.get("data", {}).get("error"),
            raw=data,
        )

    async def download_video(self, video_url: str, output_dir: str | None = None) -> str:
        """Download a finished video to disk. Returns the local file path."""
        target_dir = Path(output_dir or self._config["video_output_dir"])
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.get(video_url)
        except httpx.HTTPError as exc:
            raise VideoGenerationError(f"Video download transport error: {exc}") from exc

        if resp.status_code >= 400:
            raise VideoGenerationError(f"Video download failed {resp.status_code}: {resp.text[:200]}")

        # Derive a filename from the URL path; fall back to task_id-shaped name
        url_path = video_url.split("?", 1)[0].rstrip("/")
        filename = url_path.rsplit("/", 1)[-1] or f"video_{int(time.time())}.mp4"
        if "." not in filename:
            filename = f"{filename}.mp4"

        filepath = target_dir / filename
        filepath.write_bytes(resp.content)
        logger.info("Saved video to %s", filepath)
        return str(filepath)


# ── Convenience factory ────────────────────────────────────────────────


def create_service_from_env(config_overrides: dict[str, Any] | None = None) -> VideoGenerationService:
    """Create a ``VideoGenerationService`` using the ``MINIMAX_API_KEY`` env var.

    Any keys in ``config_overrides`` take precedence over the env-derived value.
    """
    overrides: dict[str, Any] = {"minimax_api_key": os.environ.get("MINIMAX_API_KEY", "")}
    if config_overrides:
        overrides.update(config_overrides)
    return VideoGenerationService(overrides)
