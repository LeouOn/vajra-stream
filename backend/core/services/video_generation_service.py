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

import asyncio
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
    "prompt_style_prefix": "",
    "prompt_optimizer": True,
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
    #: The provider's own status string, before normalisation (e.g. "Success",
    #: "Queueing"). Additive: a None default keeps every existing construction site
    #: working. Use it for diagnostics, never for control flow - control flow must go
    #: through ``status``, which is always one of the four documented values.
    provider_status: str | None = None


#: MiniMax speaks more than four words for "task state", and the two API versions
#: differ. Every poller in this codebase (the server-side watcher and the browser
#: poller in frontend/src/lib/videoTaskPoll.ts) stops on "done" or "failed" only, so a
#: provider string like "Success" that is merely lower-cased to "success" never matches
#: and the task is polled every 5 s until poll_timeout_seconds expires, with nothing
#: ever downloaded. These tables collapse the provider vocabulary onto the four
#: documented values. Keys are compared case-insensitively after stripping.
_STATUS_DONE = frozenset({"success", "succeeded", "done", "completed", "complete", "finished"})
_STATUS_FAILED = frozenset({"fail", "failed", "failure", "error", "cancelled", "canceled", "rejected"})
_STATUS_PENDING = frozenset({"pending", "preparing", "queueing", "queued", "submitted", "waiting"})
_STATUS_PROCESSING = frozenset({"processing", "running", "generating", "in_progress", "in-progress"})


def normalise_task_status(raw: Any) -> str:
    """Map a provider task status onto ``pending | processing | done | failed``.

    Unknown values map to ``"processing"`` and log a warning naming the value, so a
    newly invented provider state can never look terminal (which would drop a paid
    video) and can never be silently dropped (which would poll until the timeout).
    Processing is the safe default: it keeps polling, and the timeout still bounds it.
    """
    if raw is None:
        return "pending"
    value = str(raw).strip().lower()
    if not value:
        return "pending"
    if value in _STATUS_DONE:
        return "done"
    if value in _STATUS_FAILED:
        return "failed"
    if value in _STATUS_PENDING:
        return "pending"
    if value in _STATUS_PROCESSING:
        return "processing"
    logger.warning(
        "Unrecognised MiniMax task status %r; treating as 'processing' so the task keeps "
        "polling instead of being dropped or treated as finished. Add it to the status "
        "tables in video_generation_service if the provider really uses it.",
        raw,
    )
    return "processing"


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
        # Makes check-and-reserve atomic for this instance. Created lazily on
        # first use so it binds to the running event loop and is never
        # module-level, loop-bound state.
        self._spend_lock: asyncio.Lock | None = None

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

    def _get_spend_lock(self) -> asyncio.Lock:
        """The lock that makes check-and-reserve atomic for this instance.

        Created lazily on first use, so it is bound to the running event loop.
        """
        if self._spend_lock is None:
            self._spend_lock = asyncio.Lock()
        return self._spend_lock

    def _record_spend(self, model: str) -> tuple[str, float]:
        """Reserve this call's spend and return a token that can release it.

        The reservation is taken BEFORE the paid POST, so a concurrent call
        sees the budget as already spent and is refused by the same guard
        error. If the submission then fails, the caller releases it with
        ``_release_spend`` so a failed submission costs no budget.

        Returns the (day, timestamp) pair identifying this reservation.
        """
        cost = MODEL_SPECS.get(model, {}).get("cost_usd", 0.0)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._daily_spend[today] = self._daily_spend.get(today, 0.0) + cost
        stamp = time.time()
        self._hourly_calls.append(stamp)
        return today, stamp

    def _release_spend(self, model: str, reservation: tuple[str, float]) -> None:
        """Undo exactly the reservation identified by ``reservation``.

        Used when the paid POST did not produce a task, so a failed
        submission does not consume the caller's budget.
        """
        day, stamp = reservation
        cost = MODEL_SPECS.get(model, {}).get("cost_usd", 0.0)
        if day in self._daily_spend:
            self._daily_spend[day] = max(0.0, self._daily_spend[day] - cost)
        try:
            self._hourly_calls.remove(stamp)
        except ValueError:
            pass

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

        # Check-and-reserve ATOMICALLY. The reservation is taken under the
        # lock, so a concurrent submission sees the budget as already spent and
        # is refused by the same guard error, instead of both calls passing
        # the check and then both paying. The paid POST happens OUTSIDE the
        # lock, so network I/O is never serialised across requests.
        spend_lock = self._get_spend_lock()
        async with spend_lock:
            self._check_cost_guard(model_name)
            reservation = self._record_spend(model_name)

        try:
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
                    # Configurable (Settings UI can store it); v2 does not send it.
                    "prompt_optimizer": self._config.get("prompt_optimizer", True),
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
        except Exception:
            # The submission did not produce a task, so give the budget back.
            # A cancellation is not an Exception (it derives from
            # BaseException) and the money may well have been spent, so it
            # keeps its reservation.
            async with spend_lock:
                self._release_spend(model_name, reservation)
            raise

        return str(task_id)

    async def poll_task(self, task_id: str, model: str) -> TaskStatus:
        """Poll MiniMax for a submitted task's status.

        Returns a ``TaskStatus`` whose ``status`` field is one of:
        ``"pending"``, ``"processing"``, ``"done"``, ``"failed"``.
        When ``status == "done"``, ``video_url`` is populated.

        A provider-terminal status with NO ``video_url`` is reported as ``"failed"``, not
        ``"done"``. Both consumers treat ``done`` as success: the browser poller stops and
        ``useNarrativeMedia.ts`` toasts "Video generated!", and this endpoint only sets
        ``local_path`` for ``done`` + ``video_url``. Reporting ``done`` with no URL would
        tell the user the paid video succeeded while no video exists anywhere.
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
        # Normalize the provider vocabulary onto the documented four.
        raw_status = data.get("status") or data.get("state") or data.get("data", {}).get("status") or "pending"
        status = normalise_task_status(raw_status)
        provider_status_text = str(raw_status) if raw_status is not None else None

        video_url = (
            data.get("video_url") or data.get("data", {}).get("video_url") or data.get("data", {}).get("download_url")
        )

        file_id = data.get("file_id") or data.get("data", {}).get("file_id")
        missing_url_error: str | None = None
        if status == "done" and not video_url:
            # A provider-terminal body with no video_url. A v1 success body is reported to
            # carry a file_id and no video_url; this code has never observed a real v1
            # completion payload and deliberately does not guess MiniMax's file-retrieval
            # endpoint, so the finished video cannot be downloaded from this response.
            #
            # Reporting this as "done" would be a lie the user pays for: the browser poller
            # treats done as terminal and toasts success, while there is no video to show.
            # Report the documented terminal FAILURE with an honest explanation instead.
            missing_url_error = (
                f"MiniMax reports task {task_id} finished "
                f"(provider status {provider_status_text!r}, file_id={file_id or 'none'}) "
                f"but returned no download URL; this build cannot resolve a MiniMax file "
                f"reference to a download URL, so the video was not downloaded"
            )
            logger.warning(
                "MiniMax task %s: provider reported %r but returned no download URL "
                "(file_id=%s). This build has no file-retrieval call for either API version, "
                "so the video cannot be downloaded and the task is being reported as failed "
                "rather than done. Treat the task id as unrecoverable-by-download until the "
                "real completion payload is observed.",
                task_id,
                provider_status_text,
                file_id or "none",
            )
            status = "failed"

        return TaskStatus(
            task_id=task_id,
            status=status,
            video_url=str(video_url) if video_url else None,
            error=missing_url_error or data.get("error") or data.get("data", {}).get("error"),
            raw=data,
            provider_status=provider_status_text,
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
