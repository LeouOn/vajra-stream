"""
Image Generation Service — provider-agnostic image generation.

Fully self-contained, zero project dependencies. Can be extracted to a standalone repo.
Constructor takes config dict; no globals, no container, no event bus.

Usage:
    from image_gen import ImageGenerationService

    service = ImageGenerationService({
        "openrouter_api_key": "sk-or-v1-...",
        "minimax_api_key": "sk-mm-...",
        "default_model": "google/gemini-3.1-flash-lite-image",
        "daily_cost_cap_usd": 0.50,
    })

    result = await service.generate(
        prompt="Heart chakra mandala, golden sacred geometry",
        provider="openrouter",
        model="google/gemini-3.1-flash-lite-image",
    )
    print(result["image_data_url"])  # data:image/png;base64,...

To extract: copy this file into a new repo with pip install httpx.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "openrouter_api_key": "",
    "minimax_api_key": "",
    "default_model": "google/gemini-3.1-flash-lite-image",
    "default_provider": "openrouter",
    "daily_cost_cap_usd": 0.50,
    "max_images_per_call": 3,
    "max_per_hour": 10,
    "cache_ttl_seconds": 3600,
    "max_prompt_tokens": 1000,
    "prompt_style_prefix": "",
    "prompt_negative": "",
    "image_output_dir": "generated/images",
    "model_lock": True,
    "default_aspect_ratio": "1:1",
}

MODEL_COST_USD: dict[str, float] = {
    # OpenRouter models — verified against live API 2026-07-29
    "google/gemini-3.1-flash-lite-image": 0.034,
    "black-forest-labs/flux.2-klein-4b": 0.014,
    "krea/krea-2-large": 0.06,
    "microsoft/mai-image-2.5-pro": 0.10,
    # MiniMax model
    "image-01": 0.02,
}

MODEL_CAPABILITIES: dict[str, dict[str, Any]] = {
    "google/gemini-3.1-flash-lite-image": {
        "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
        "resolutions": ["1K"],
        "max_n": 1,
    },
    "black-forest-labs/flux.2-klein-4b": {
        "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
        "resolutions": ["1K", "2K"],
        "max_n": 1,
    },
    "krea/krea-2-large": {
        "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
        "resolutions": ["1K", "2K"],
        "max_n": 1,
    },
    "microsoft/mai-image-2.5-pro": {
        "aspect_ratios": ["1:1", "16:9", "9:16"],
        "resolutions": ["1K", "2K"],
        "max_n": 1,
    },
    "image-01": {
        "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
        "resolutions": ["1K"],
        "max_n": 1,
    },
}


# ── Provider Interface ────────────────────────────────────────────────


@dataclass
class ProviderResult:
    image_data_url: str
    model: str
    cost_usd: float
    provider: str
    revised_prompt: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ProviderError(RuntimeError):
    """Base class for provider errors. Subclasses set ``retryable``.

    Extends ``RuntimeError`` so the LLM tool contract (which documents
    ``RuntimeError`` as the failure type) and the HTTP adapter's
    ``except RuntimeError`` clause both catch provider errors correctly.
    """

    retryable: bool = False


class RetryableProviderError(ProviderError):
    """Transient failure worth one retry: 5xx, 429, transport error, content filter, empty response."""

    retryable = True


class PermanentProviderError(ProviderError):
    """Non-retryable failure: 4xx auth/billing/bad-request, validation, disabled state."""

    retryable = False


class ImageProvider(ABC):
    """Abstract base for image generation providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        size: str,
        quality: str,
        n: int,
        **kwargs: Any,
    ) -> ProviderResult:
        """Generate an image and return ProviderResult."""


# ── OpenRouter Provider ───────────────────────────────────────────────


class OpenRouterProvider(ImageProvider):
    """Image generation via OpenRouter's unified /api/v1/images endpoint."""

    URL = "https://openrouter.ai/api/v1/images"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise RuntimeError("OpenRouter API key not configured")
        self._api_key = api_key

    async def generate(
        self,
        prompt: str,
        model: str,
        size: str,
        quality: str,
        n: int,
        **kwargs: Any,
    ) -> ProviderResult:
        aspect_ratio = kwargs.get("aspect_ratio") or self._size_to_aspect(size)
        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "resolution": self._size_to_resolution(size),
            "aspect_ratio": aspect_ratio,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    self.URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._api_key}",
                    },
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise RetryableProviderError(f"OpenRouter transport error: {exc}") from exc

        if resp.status_code >= 400:
            msg = f"OpenRouter image API error {resp.status_code}: {resp.text[:200]}"
            if resp.status_code in (401, 402, 403):
                raise PermanentProviderError(msg) from None
            if resp.status_code == 400:
                raise PermanentProviderError(msg) from None
            raise RetryableProviderError(msg) from None

        data = resp.json()
        images = data.get("images") or data.get("data") or []
        if not images:
            raise RetryableProviderError("OpenRouter returned no image data")

        first = images[0]
        data_url = await self._extract_data_url(first)
        if not data_url:
            raise RetryableProviderError("OpenRouter response had neither b64_json, data, nor url field")

        return ProviderResult(
            image_data_url=data_url,
            model=model,
            cost_usd=MODEL_COST_USD.get(model, 0.05),
            provider="openrouter",
            revised_prompt=first.get("revised_prompt"),
            raw=data,
        )

    @staticmethod
    def _size_to_resolution(size: str) -> str:
        if "2048" in size or "4K" in size.upper():
            return "4K"
        if "1792" in size or "2K" in size.upper():
            return "2K"
        return "1K"

    @staticmethod
    def _size_to_aspect(size: str) -> str:
        parts = size.split("x")
        if len(parts) == 2:
            w, h = int(parts[0]), int(parts[1])
            if w > h:
                return "16:9"
            if h > w:
                return "9:16"
        return "1:1"

    @staticmethod
    async def _extract_data_url(first: dict[str, Any]) -> str | None:
        b64 = first.get("b64_json") or first.get("data", "")
        if b64:
            if b64.startswith("data:"):
                return b64
            return f"data:image/png;base64,{b64}"
        url = first.get("url")
        if url:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    img_resp = await client.get(url)
                img_resp.raise_for_status()
                encoded = base64.b64encode(img_resp.content).decode("ascii")
                content_type = img_resp.headers.get("content-type", "image/png")
                return f"data:{content_type};base64,{encoded}"
            except httpx.HTTPError:
                return None
        return None


# ── MiniMax Provider ───────────────────────────────────────────────────


class MiniMaxProvider(ImageProvider):
    """Image generation via MiniMax's /v1/image_generation endpoint.

    Supports text-to-image and subject-reference (image-to-image) generation.
    """

    URL = "https://api.minimax.io/v1/image_generation"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise RuntimeError("MiniMax API key not configured")
        self._api_key = api_key

    async def generate(
        self,
        prompt: str,
        model: str,
        size: str,
        quality: str,
        n: int,
        **kwargs: Any,
    ) -> ProviderResult:
        aspect_ratio = kwargs.get("aspect_ratio") or self._size_to_aspect(size)
        subject_reference = kwargs.get("subject_reference")

        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "response_format": "base64",
        }

        if subject_reference:
            body["subject_reference"] = [{"type": "character", "image_file": subject_reference}]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    self.URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._api_key}",
                    },
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise RetryableProviderError(f"MiniMax transport error: {exc}") from exc

        if resp.status_code >= 400:
            msg = f"MiniMax image API error {resp.status_code}: {resp.text[:200]}"
            if resp.status_code in (400, 401, 402, 403):
                raise PermanentProviderError(msg) from None
            raise RetryableProviderError(msg) from None

        data = resp.json()
        data_url = self._extract_data_url(data)
        if not data_url:
            raise RetryableProviderError("MiniMax returned no image data")

        return ProviderResult(
            image_data_url=data_url,
            model=model,
            cost_usd=MODEL_COST_USD.get(model, 0.02),
            provider="minimax",
            raw=data,
        )

    @staticmethod
    def _extract_data_url(payload: dict[str, Any]) -> str | None:
        data_obj = payload.get("data", payload)
        b64_list = data_obj.get("image_base64") if isinstance(data_obj, dict) else None
        if b64_list and isinstance(b64_list, list) and b64_list[0]:
            return f"data:image/png;base64,{b64_list[0]}"
        url_list = data_obj.get("image_urls") if isinstance(data_obj, dict) else None
        if url_list and isinstance(url_list, list) and url_list[0]:
            return url_list[0]
        images = payload.get("images") or payload.get("data", {}).get("images")
        if images and isinstance(images, list):
            first = images[0]
            if isinstance(first, dict):
                b64 = first.get("b64_json") or first.get("data", "")
                if b64:
                    return f"data:image/png;base64,{b64}" if not b64.startswith("data:") else b64
                url = first.get("url")
                if url:
                    return url
        return None

    @staticmethod
    def _size_to_aspect(size: str) -> str:
        """Convert OpenRouter-style size to MiniMax aspect ratio."""
        ratios = {
            "1024x1024": "1:1",
            "1792x1024": "16:9",
            "1024x1792": "9:16",
        }
        return ratios.get(size, "1:1")


# ── Service ───────────────────────────────────────────────────────────


# ── Spend budget ────────────────────────────────────────────────────────
# Defined here rather than in a shared module so this file stays stdlib-only
# and independently extractable (tests/unit/test_image_generation_service.py::
# test_service_module_has_no_project_imports). backend/core/services/
# spend_budget.py re-exports these three names and owns the process-wide
# instance, which is what lets sigil and images share one dollar cap.
#
# The caps are IN-MEMORY and PER PROCESS. run.py starts one uvicorn process, so
# today there is one budget; workers=N would give N processes and therefore N
# independent budgets, multiplying every cap by N. Nothing here is persisted.

#: Seconds in the rolling hourly window.
_HOUR_SECONDS = 3600.0


@dataclass(frozen=True)
class Reservation:
    """A hold on the budget, and the token that releases or settles it.

    Attributes:
        day: UTC day the reservation is charged to, ``YYYY-MM-DD``.
        stamp: ``time.time()`` when the hourly slot was taken.
        estimated_cost_usd: What was held. ``release`` gives this back;
            ``reconcile`` adjusts by ``actual - estimated``.
    """

    day: str
    stamp: float
    estimated_cost_usd: float


class BudgetView:
    """The budget as seen from inside ``critical_section()``.

    Every method here assumes the caller already holds the budget lock, which is
    what lets a caller do its own cache lookup between the guard and the
    reservation without releasing it.
    """

    __slots__ = ("_budget",)

    def __init__(self, budget: SpendBudget) -> None:
        self._budget = budget

    @property
    def day(self) -> str:
        """The UTC day this view charges to, resolved once per section."""
        return self._budget._today()

    @property
    def daily_spend_usd(self) -> float:
        """Total reserved-or-settled spend for :attr:`day`."""
        return self._budget._daily_spend.get(self.day, 0.0)

    def prune(self, now: float) -> None:
        """Drop hourly stamps older than the rolling window.

        REBINDS the list. That is why it must share a critical section with
        :meth:`reserve`: a concurrent append to the pre-rebind list would be
        silently lost, granting an admitted call no hourly slot.
        """
        self._budget._hourly_calls = [t for t in self._budget._hourly_calls if now - t < _HOUR_SECONDS]

    @property
    def hourly_count(self) -> int:
        return len(self._budget._hourly_calls)

    def reserve(self, estimated_cost_usd: float) -> Reservation:
        """Hold ``estimated_cost_usd`` and one hourly slot.

        Raises:
            RuntimeError: If the daily cap or the hourly limit would be
                breached. The message is the byte-identical string the image
                service has always raised, so its external behaviour is unchanged.
        """
        return self._budget._reserve_locked(estimated_cost_usd)


class SpendBudget:
    """A daily USD cap plus a per-hour call limit, shared across callers."""

    def __init__(self, daily_cost_cap_usd: float, max_per_hour: int) -> None:
        self._daily_cost_cap_usd = float(daily_cost_cap_usd)
        self._max_per_hour = int(max_per_hour)
        self._daily_spend: dict[str, float] = {}
        self._hourly_calls: list[float] = []
        self._lock = threading.Lock()

    # -- limits ---------------------------------------------------------

    def configure(self, daily_cost_cap_usd: float, max_per_hour: int) -> None:
        """Replace the limits.

        Called by ``ImageGenerationService`` when its config changes. Existing
        reservations are NOT re-priced: the new limits apply to the next
        reservation, so a cap lowered below money already committed will not
        retroactively release it.
        """
        with self._lock:
            self._daily_cost_cap_usd = float(daily_cost_cap_usd)
            self._max_per_hour = int(max_per_hour)

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # -- the critical section -------------------------------------------

    @contextmanager
    def critical_section(self) -> Iterator[BudgetView]:
        """Hold the lock for a check + prune + reserve sequence.

        The paid provider call must happen OUTSIDE this block; only the
        synchronous budget bookkeeping belongs inside it.
        """
        with self._lock:
            yield BudgetView(self)

    def _reserve_locked(self, estimated_cost_usd: float) -> Reservation:
        """Reserve while the caller already holds the lock."""
        day = self._today()
        daily = self._daily_spend.get(day, 0.0)
        projected = daily + estimated_cost_usd
        if projected > self._daily_cost_cap_usd:
            raise RuntimeError(
                f"Request would breach daily cost cap (${projected:.4f} > ${self._daily_cost_cap_usd:.4f})"
            )

        now = time.time()
        self._hourly_calls = [t for t in self._hourly_calls if now - t < _HOUR_SECONDS]
        if len(self._hourly_calls) >= self._max_per_hour:
            raise RuntimeError(f"max_per_hour={self._max_per_hour} reached; try again later")

        self._hourly_calls.append(now)
        self._daily_spend[day] = projected
        return Reservation(day=day, stamp=now, estimated_cost_usd=estimated_cost_usd)

    # -- single-shot API ------------------------------------------------

    def reserve(self, estimated_cost_usd: float) -> Reservation:
        """Check and reserve in one step.

        Raises:
            RuntimeError: With the image service's historical message text when
                the daily cap or hourly limit would be breached.
        """
        with self.critical_section() as view:
            return view.reserve(estimated_cost_usd)

    def try_reserve(self, estimated_cost_usd: float) -> Reservation | None:
        """Reserve, or return ``None`` if refused.

        For callers that must not raise across a boundary -- ``SigilService``
        turns a refusal into a warning and a missing image rather than an error
        into the sigil endpoint.
        """
        try:
            return self.reserve(estimated_cost_usd)
        except RuntimeError:
            return None

    def release(self, reservation: Reservation) -> None:
        """Give back exactly one reservation.

        Removes the estimated amount and that reservation's own hourly stamp by
        value, so a concurrent call's stamp is never disturbed.
        """
        with self._lock:
            day, stamp, cost = reservation.day, reservation.stamp, reservation.estimated_cost_usd
            if day in self._daily_spend:
                self._daily_spend[day] = max(0.0, self._daily_spend[day] - cost)
            try:
                self._hourly_calls.remove(stamp)
            except ValueError:
                # The hourly window may already have pruned this stamp; the day
                # total is still corrected above, so a missing stamp is harmless.
                pass

    def reconcile(self, reservation: Reservation, actual_cost_usd: float) -> None:
        """Settle a reservation at what the provider actually charged.

        The provider's cost is the authority, so this ADJUSTS by
        ``actual - estimated``. It must not add the actual cost on top of the
        reservation, which would bill twice. The hourly stamp is kept: the call
        happened and consumed a slot.

        A non-finite or negative ``actual_cost_usd`` is treated as NOT REPORTED:
        the estimate stays and one warning is logged. That matters because this
        is a ledger, and a NaN total would poison it -- ``nan > cap`` is False,
        so the daily cap would never trip again -- while a negative total would
        hand free budget back. Both are caught here rather than trusted.

        ``0.0`` IS honoured: a genuinely free call should settle to zero, and
        the IMAGE providers may legitimately report it. Sigil is unaffected,
        because its own reader (``_reported_cost_usd``) treats a reported zero
        as "not reported" and never passes 0.0 here.

        The day total is floored at 0.0, as ``release`` does, so a rounding
        artefact can never leave the ledger negative.
        """
        with self._lock:
            day = reservation.day
            if not isfinite(actual_cost_usd) or actual_cost_usd < 0.0:
                logger.warning(
                    "SpendBudget.reconcile: ignoring a non-finite or negative actual cost "
                    "(%r) for the %s reservation; keeping the estimate of $%.4f",
                    actual_cost_usd,
                    day,
                    reservation.estimated_cost_usd,
                )
                actual = reservation.estimated_cost_usd
            else:
                actual = actual_cost_usd
            self._daily_spend[day] = max(0.0, self._daily_spend.get(day, 0.0) - reservation.estimated_cost_usd + actual)

    def stats(self) -> dict[str, Any]:
        """Current spend, matching the keys ``get_cost_stats`` publishes."""
        with self._lock:
            now = time.time()
            self._hourly_calls = [t for t in self._hourly_calls if now - t < _HOUR_SECONDS]
            return {
                "daily_spend_usd": self._daily_spend.get(self._today(), 0.0),
                "daily_cost_cap_usd": self._daily_cost_cap_usd,
                "hourly_calls": len(self._hourly_calls),
                "max_per_hour": self._max_per_hour,
            }


class ImageGenerationService:
    """Provider-agnostic image generation service.

    Wraps multiple providers (OpenRouter, MiniMax) behind a single API.
    Fully self-contained: constructor takes config dict, no globals.

    Usage:
        service = ImageGenerationService({
            "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY", ""),
            "minimax_api_key": os.environ.get("MINIMAX_API_KEY", ""),
            "default_model": "google/gemini-3.1-flash-lite-image",
            "daily_cost_cap_usd": 0.50,
        })

        result = await service.generate(
            prompt="Heart chakra mandala",
            provider="openrouter",
            model="google/gemini-3.1-flash-lite-image",
        )
    """

    def __init__(self, config: dict[str, Any] | None = None, budget: SpendBudget | None = None) -> None:
        self._config: dict[str, Any] = dict(DEFAULT_CONFIG)
        if config:
            self._config.update(config)

        # Provider instances (lazy-initialized)
        self._providers: dict[str, ImageProvider] = {}

        # Cache state (instance-local, reset on restart)
        self._cache: dict[str, tuple[float, ProviderResult]] = {}

        # Spend lives in a SpendBudget. With no budget injected this service
        # builds its OWN, from its own config, so every caller -- notably each
        # test -- gets an isolated ledger and nothing leaks between them. The
        # endpoint injects the process-wide shared budget instead, which is what
        # lets sigils and generated images draw on one cap. The limits are always
        # this service's, pushed in below either way.
        self._budget = (
            budget
            if budget is not None
            else SpendBudget(
                daily_cost_cap_usd=self._config["daily_cost_cap_usd"],
                max_per_hour=self._config["max_per_hour"],
            )
        )
        self._budget.configure(self._config["daily_cost_cap_usd"], self._config["max_per_hour"])

        # Compatibility shims for the private attributes the existing tests read.
        # They are properties, so the budget stays the single owner of the state.
        self._spend_lock = self._budget._lock

    @property
    def _daily_spend(self) -> dict[str, float]:
        """The budget's daily ledger, keyed by UTC day."""
        return self._budget._daily_spend

    @property
    def _hourly_calls(self) -> list[float]:
        """The budget's hourly stamps."""
        return self._budget._hourly_calls

    # ── Config ─────────────────────────────────────────────────────────

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        unknown = set(updates) - set(DEFAULT_CONFIG)
        if unknown:
            raise ValueError(f"unknown config key(s): {sorted(unknown)}")
        self._config.update(updates)
        # The budget owns the ledger but this service owns the limits; push them
        # so a Settings change applies to the very next reservation, including on
        # the shared budget that sigils also spend from.
        self._budget.configure(self._config["daily_cost_cap_usd"], self._config["max_per_hour"])
        return self.config

    # ── Validation ─────────────────────────────────────────────────────

    def validate_prompt(self, prompt: str) -> dict[str, Any]:
        """Validate prompt length. Returns {ok, estimated_tokens, error?, suggestion?}."""
        max_tokens = self._config["max_prompt_tokens"]
        words = len(prompt.split())
        cjk_chars = sum(1 for c in prompt if 0x4E00 <= ord(c) <= 0x9FFF)
        estimated = int(words * 1.3 + cjk_chars * 0.7)

        if estimated <= max_tokens:
            return {"ok": True, "estimated_tokens": estimated}

        words_list = prompt.split()
        suggestion = " ".join(words_list[:50])
        if len(words_list) > 50:
            suggestion += " …"
        return {
            "ok": False,
            "estimated_tokens": estimated,
            "error": f"Prompt exceeds {max_tokens} tokens (estimated {estimated}).",
            "suggestion": suggestion,
        }

    # ── Cost tracking ──────────────────────────────────────────────────

    def _reserve_spend(self, estimated_cost: float) -> Reservation:
        """Reserve this call's estimated spend against the budget."""
        return self._budget.reserve(estimated_cost)

    def _release_spend(self, reservation: Reservation) -> None:
        """Undo exactly one reservation -- a failed call costs no budget."""
        self._budget.release(reservation)

    def _reconcile_spend(self, reservation: Reservation, actual_cost: float) -> None:
        """Settle a reservation at the provider's actual cost, not our estimate."""
        self._budget.reconcile(reservation, actual_cost)

    def get_cost_stats(self) -> dict[str, Any]:
        """Current spend, under the budget's lock.

        Previously this pruned ``_hourly_calls`` by REBINDING the list outside
        any lock, which could discard a stamp appended by a concurrent caller.
        The prune now happens inside ``SpendBudget.stats()``, so that rebind is
        covered by the same lock as everything else. Keys are unchanged.

        The cap and the hourly limit are read from the BUDGET, not from this
        service's config, because the budget is what ENFORCES them: with two
        services on one shared budget the last ``configure()`` wins, and
        publishing this service's config here could announce a limit that is not
        the one in force. The budget is single-owner -- only the endpoint's
        image service configures it -- so in the normal case this service's own
        config and the enforced limit agree.
        """
        stats = self._budget.stats()
        return {
            "daily_spend_usd": stats["daily_spend_usd"],
            "daily_cost_cap_usd": stats["daily_cost_cap_usd"],
            "hourly_calls": stats["hourly_calls"],
            "max_per_hour": stats["max_per_hour"],
            "cache_entries": len(self._cache),
        }

    # ── Provider selection ─────────────────────────────────────────────

    def _get_provider(self, name: str) -> ImageProvider:
        if name in self._providers:
            return self._providers[name]

        if name == "openrouter":
            self._providers[name] = OpenRouterProvider(self._config["openrouter_api_key"])
        elif name == "minimax":
            self._providers[name] = MiniMaxProvider(self._config["minimax_api_key"])
        else:
            raise ValueError(f"Unknown image provider: {name}")

        return self._providers[name]

    # ── Main API ───────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        provider: str | None = None,
        model: str | None = None,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        caption_facts: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate an image and return a dict with image_data_url + metadata.

        Args:
            prompt: Image description (max 1000 tokens).
            provider: "openrouter" (default) or "minimax".
            model: Model slug. Defaults to config default_model.
            size: OpenRouter: "1024x1024" (default), "1792x1024", "1024x1792".
            quality: "standard" (default) or "hd".
            n: Number of images. Default 1, max per config.
            caption_facts: Real values to caption the image with
                (``[{"label", "value", "provenance"}]``, see core/image_prompts.py).
                Echoed in the result and written to a ``<image>.json`` sidecar
                beside the saved file; never sent to the provider.
            **kwargs: Provider-specific args:
                - aspect_ratio: MiniMax only, e.g. "1:1", "16:9", "4:3"
                - subject_reference: MiniMax only, URL of reference image

        Returns:
            Dict with keys: image_data_url, model, cost_usd, provider_used,
            cached, revised_prompt, prompt_tokens.
        """
        cfg = self._config

        if not cfg["enabled"]:
            raise RuntimeError("Image generation is disabled; enable it in settings.")

        style_prefix = str(cfg.get("prompt_style_prefix", "")).strip()
        full_prompt = f"{style_prefix}. {prompt}" if style_prefix else prompt

        # Validate prompt
        validation = self.validate_prompt(full_prompt)
        if not validation["ok"]:
            raise ValueError(validation["error"] + " " + validation["suggestion"])

        if n > cfg["max_images_per_call"]:
            raise RuntimeError(f"n={n} exceeds max_images_per_call={cfg['max_images_per_call']}")

        effective_n = 1
        if n > 1:
            logger.warning("n=%d requested but batch return is not implemented; generating 1 image.", n)

        if "aspect_ratio" not in kwargs:
            kwargs["aspect_ratio"] = cfg.get("default_aspect_ratio", "1:1")

        provider_name = provider or cfg["default_provider"]
        model_name = model or cfg["default_model"]

        requested_ratio = kwargs["aspect_ratio"]
        caps = MODEL_CAPABILITIES.get(model_name, {})
        supported_ratios = caps.get("aspect_ratios", ["1:1"])
        if requested_ratio not in supported_ratios:
            logger.warning(
                "Model %s doesn't support aspect_ratio %s (supported: %s); falling back to 1:1",
                model_name,
                requested_ratio,
                supported_ratios,
            )
            kwargs["aspect_ratio"] = "1:1"

        # Cost guard
        estimated_cost = MODEL_COST_USD.get(model_name, 0.05) * effective_n

        # Cost guard + hourly prune + cache lookup + spend reservation are ONE
        # critical section.
        #
        # Why all four together: the reservation only protects the budget if the
        # check that consulted it is atomic with it. Guarding only the
        # reservation left the window open in two ways -- two threads could both
        # pass the cap check and then both reserve; and the hourly prune
        # REBINDS ``_hourly_calls`` to a filtered list, so a reservation appended
        # to the old list just before the rebind was discarded, giving an
        # admitted call no hourly slot. Everything between here and the
        # reservation is synchronous, so on one event loop none of it can
        # interleave; the lock covers the two-loops case.
        #
        # The paid provider ``await`` stays OUTSIDE the lock, so network I/O is
        # never serialised. release/reconcile take the lock briefly afterwards.
        with self._budget.critical_section() as budget_view:
            projected = budget_view.daily_spend_usd + estimated_cost
            if projected > cfg["daily_cost_cap_usd"]:
                raise RuntimeError(
                    f"Request would breach daily cost cap (${projected:.4f} > ${cfg['daily_cost_cap_usd']:.4f})"
                )

            # Hourly guard
            now = time.time()
            budget_view.prune(now)
            if budget_view.hourly_count >= cfg["max_per_hour"]:
                raise RuntimeError(f"max_per_hour={cfg['max_per_hour']} reached; try again later")

            # Cache lookup
            cache_key = self._cache_key(full_prompt, provider_name, model_name, n, size, quality, kwargs)
            cached = self._cache.get(cache_key)
            if cached and cached[0] > now:
                result = dict(cached[1].__dict__)
                result["cached"] = True
                if caption_facts:
                    result["caption_facts"] = list(caption_facts)
                return result

            # RESERVE the estimated cost BEFORE the paid await, while still
            # holding the lock the guard was evaluated under. A cache hit has
            # already returned above, so it reserves and records nothing.
            reservation = budget_view.reserve(estimated_cost)

        try:
            # Call provider — 2 tries, only on technical (retryable) failure
            provider_obj = self._get_provider(provider_name)
            result: ProviderResult | None = None
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    result = await provider_obj.generate(
                        prompt=full_prompt,
                        model=model_name,
                        size=size,
                        quality=quality,
                        n=effective_n,
                        **kwargs,
                    )
                    break
                except PermanentProviderError:
                    raise
                except RetryableProviderError as exc:
                    last_error = exc
                    if attempt == 0:
                        logger.warning("Image generation attempt 1 failed (retryable): %s", exc)
                        continue
                except Exception as exc:
                    last_error = exc
                    if attempt == 0 and not isinstance(exc, ValueError | RuntimeError):
                        logger.warning("Image generation attempt 1 failed (unexpected): %s", exc)
                        continue
                    raise RuntimeError(f"Image generation failed via {provider_name}: {exc}") from exc

            if result is None:
                raise RuntimeError(f"Image generation failed after 2 tries via {provider_name}: {last_error}") from (
                    last_error
                )
        except Exception:
            # Nothing was produced, so give the budget back. Both attempts were
            # covered by the ONE reservation above, and a retry is not a second
            # charge.
            #
            # CancelledError is deliberately NOT handled: since 3.8 it derives
            # from BaseException, so it propagates past this except and KEEPS
            # its reservation. A cancelled request may already have been billed
            # by the provider, and refunding a call that was paid for would be
            # the more expensive mistake.
            self._release_spend(reservation)
            raise

        # The provider's own cost is the authority: settle the reservation at
        # what was actually charged rather than at what we guessed.
        self._reconcile_spend(reservation, result.cost_usd)

        self._cache[cache_key] = (now + cfg["cache_ttl_seconds"], result)

        saved_path = self._save_image(
            result.image_data_url,
            full_prompt,
            metadata={
                "prompt": prompt,
                "full_prompt": full_prompt,
                "provider": result.provider,
                "model": result.model,
                "size": size,
                "quality": quality,
                "aspect_ratio": kwargs.get("aspect_ratio"),
                "revised_prompt": result.revised_prompt,
                "cost_usd": result.cost_usd,
                **({"caption_facts": list(caption_facts)} if caption_facts else {}),
            },
        )

        response: dict[str, Any] = {
            "image_data_url": result.image_data_url,
            "model": result.model,
            "cost_usd": result.cost_usd,
            "provider_used": result.provider,
            "cached": False,
            "revised_prompt": result.revised_prompt,
            "prompt_tokens": validation["estimated_tokens"],
            "image_file_path": saved_path,
        }
        if caption_facts:
            response["caption_facts"] = list(caption_facts)
        return response

    # ── Internals ──────────────────────────────────────────────────────

    def _save_image(self, data_url: str, prompt: str, metadata: dict[str, Any] | None = None) -> str | None:
        """Save a base64 data URL to the configured output directory.

        Next to ``img_<ts>_<prompthash>.<ext>`` it writes ``img_<ts>_<prompthash>.json``,
        a small sidecar recording what made the image (``metadata``: prompt,
        provider, model, size, ...) plus ``created_at``, ``content_type``,
        ``bytes`` and ``sha256`` of the saved file. A sidecar that cannot be
        written is logged and does not undo the image save.

        A relative ``image_output_dir`` resolves against the current working
        directory; embedders that want a fixed location pass an absolute path.

        Returns the saved file path, or None if the image is a URL
        (not a data URL) or saving fails.
        """
        if not data_url.startswith("data:"):
            return None

        try:
            header, b64_data = data_url.split(";base64,", 1)
            img_bytes = base64.b64decode(b64_data)
        except Exception as exc:
            logger.warning("Could not decode image data URL for saving: %s", exc)
            return None

        content_type = "image/png"
        if ":" in header:
            content_type = header.split(":", 1)[1]
        ext = "png" if "png" in content_type else "webp" if "webp" in content_type else "jpg"

        out_dir = Path(self._config["image_output_dir"])
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            now = time.time()
            timestamp = int(now)
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
            filename = f"img_{timestamp}_{prompt_hash}.{ext}"
            filepath = out_dir / filename
            filepath.write_bytes(img_bytes)
            logger.info("Saved image to %s", filepath)
        except OSError as exc:
            logger.warning("Could not save image to %s: %s", out_dir, exc)
            return None

        sidecar = {
            **(metadata or {"prompt": prompt}),
            "filename": filename,
            "content_type": content_type,
            "bytes": len(img_bytes),
            "sha256": hashlib.sha256(img_bytes).hexdigest(),
            "created_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        }
        try:
            filepath.with_suffix(".json").write_text(
                json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("Saved %s but could not write its sidecar: %s", filepath, exc)
        return str(filepath)

    @staticmethod
    def _cache_key(
        prompt: str,
        provider: str,
        model: str,
        n: int,
        size: str,
        quality: str,
        extra: dict[str, Any],
    ) -> str:
        extra_str = json.dumps(extra, sort_keys=True, default=str)
        raw = f"{provider}|{model}|{n}|{size}|{quality}|{prompt}|{extra_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── Convenience factory ────────────────────────────────────────────────


def create_service_from_env(config_overrides: dict[str, Any] | None = None) -> ImageGenerationService:
    """Create an ImageGenerationService using environment variables.

    Reads OPENROUTER_API_KEY and MINIMAX_API_KEY from the environment.
    Any keys in config_overrides take precedence.
    """
    config = {
        "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY", ""),
        "minimax_api_key": os.environ.get("MINIMAX_API_KEY", ""),
    }
    if config_overrides:
        config.update(config_overrides)
    return ImageGenerationService(config)
