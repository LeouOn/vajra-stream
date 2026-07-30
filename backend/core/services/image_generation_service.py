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
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
}

MODEL_COST_USD: dict[str, float] = {
    # OpenRouter models
    "google/gemini-3.1-flash-lite-image": 0.008,
    "black-forest-labs/flux.2-klein-4b": 0.014,
    "krea/krea-2-large": 0.06,
    "microsoft/mai-image-2.5-pro": 0.10,
    # MiniMax model
    "image-01": 0.02,
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
        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
            "provider": {"order": "balanced", "allow_fallbacks": True},
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

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = dict(DEFAULT_CONFIG)
        if config:
            self._config.update(config)

        # Provider instances (lazy-initialized)
        self._providers: dict[str, ImageProvider] = {}

        # Cost & cache state (instance-local, reset on restart)
        self._cache: dict[str, tuple[float, ProviderResult]] = {}
        self._daily_spend: dict[str, float] = {}
        self._hourly_calls: list[float] = []

    # ── Config ─────────────────────────────────────────────────────────

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        unknown = set(updates) - set(DEFAULT_CONFIG)
        if unknown:
            raise ValueError(f"unknown config key(s): {sorted(unknown)}")
        self._config.update(updates)
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

    def get_cost_stats(self) -> dict[str, Any]:
        now = time.time()
        self._hourly_calls = [t for t in self._hourly_calls if now - t < 3600]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {
            "daily_spend_usd": self._daily_spend.get(today, 0.0),
            "daily_cost_cap_usd": self._config["daily_cost_cap_usd"],
            "hourly_calls": len(self._hourly_calls),
            "max_per_hour": self._config["max_per_hour"],
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

        # Cost guard
        provider_name = provider or cfg["default_provider"]
        model_name = model or cfg["default_model"]
        estimated_cost = MODEL_COST_USD.get(model_name, 0.05) * effective_n

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        projected = self._daily_spend.get(today, 0.0) + estimated_cost
        if projected > cfg["daily_cost_cap_usd"]:
            raise RuntimeError(
                f"Request would breach daily cost cap (${projected:.4f} > ${cfg['daily_cost_cap_usd']:.4f})"
            )

        # Hourly guard
        now = time.time()
        self._hourly_calls = [t for t in self._hourly_calls if now - t < 3600]
        if len(self._hourly_calls) >= cfg["max_per_hour"]:
            raise RuntimeError(f"max_per_hour={cfg['max_per_hour']} reached; try again later")

        # Cache lookup
        cache_key = self._cache_key(full_prompt, provider_name, model_name, n, size, quality, kwargs)
        cached = self._cache.get(cache_key)
        if cached and cached[0] > now:
            result = dict(cached[1].__dict__)
            result["cached"] = True
            return result

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
                if attempt == 0 and not isinstance(exc, (ValueError, RuntimeError)):
                    logger.warning("Image generation attempt 1 failed (unexpected): %s", exc)
                    continue
                raise RuntimeError(f"Image generation failed via {provider_name}: {exc}") from exc

        if result is None:
            raise RuntimeError(
                f"Image generation failed after 2 tries via {provider_name}: {last_error}"
            ) from last_error

        # Update state
        self._daily_spend[today] = self._daily_spend.get(today, 0.0) + result.cost_usd
        self._hourly_calls.append(now)
        self._cache[cache_key] = (now + cfg["cache_ttl_seconds"], result)

        saved_path = self._save_image(result.image_data_url, full_prompt)

        return {
            "image_data_url": result.image_data_url,
            "model": result.model,
            "cost_usd": result.cost_usd,
            "provider_used": result.provider,
            "cached": False,
            "revised_prompt": result.revised_prompt,
            "prompt_tokens": validation["estimated_tokens"],
            "image_file_path": saved_path,
        }

    # ── Internals ──────────────────────────────────────────────────────

    def _save_image(self, data_url: str, prompt: str) -> str | None:
        """Save a base64 data URL to the configured output directory.

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
        ext = "png" if "png" in content_type else "jpg"

        out_dir = Path(self._config["image_output_dir"])
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time())
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
            filename = f"img_{timestamp}_{prompt_hash}.{ext}"
            filepath = out_dir / filename
            filepath.write_bytes(img_bytes)
            logger.info("Saved image to %s", filepath)
            return str(filepath)
        except OSError as exc:
            logger.warning("Could not save image to %s: %s", out_dir, exc)
            return None

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
