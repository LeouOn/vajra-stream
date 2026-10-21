"""
Sigil Forging & Generator Service — intention-to-symbol encoding.

Transforms written intentions into abstract visual sigils using
multiple encoding methods (word-grid, planetary kamea, automated
drawing). Supports intention charging, sigil activation, and
persistent storage with metadata tracking.
"""

import asyncio
import base64
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import urllib3.exceptions

from backend.core.services.spend_budget import Reservation, shared_image_budget
from core.image_prompts import caption_fact, finalize_image_prompt

logger = logging.getLogger(__name__)

# Planetary Kameas (Magic Squares)
KAMEAS = {
    "saturn": {"size": 3, "grid": [[8, 1, 6], [3, 5, 7], [4, 9, 2]]},
    "jupiter": {"size": 4, "grid": [[4, 14, 15, 1], [9, 7, 6, 12], [5, 11, 10, 8], [16, 2, 3, 13]]},
    "mars": {
        "size": 5,
        "grid": [[11, 24, 7, 20, 3], [4, 12, 25, 8, 16], [17, 5, 13, 21, 9], [10, 18, 1, 14, 22], [23, 6, 19, 2, 15]],
    },
}


def sigil_image_prompt(intention: str) -> str:
    """The AI image prompt for a sigil: imagery only, no runes, numerals or lettering.

    The intention is the sigil's subject, but its words are not to be painted;
    the real values (intention, kamea, forge time) are the image's caption_facts.
    """
    return finalize_image_prompt(
        f"Abstract esoteric cyber-sigil embodying the intention: {intention[:300]}. "
        "Sacred geometry grid, glowing cyan and magenta linework, crystalline core structure, "
        "orgone layers, a high-tech cyberdeck dashboard element, digital art, dark background, "
        "highly detailed render"
    )


#: Cost ESTIMATES in USD for the two paid sigil image providers. These are
#: estimates, not quotes -- check current pricing before trusting them, and note
#: that neither provider is guaranteed to report what it actually charged.
SIGIL_IMAGE_COST_ESTIMATE_USD: dict[str, float] = {
    # OpenAI dall-e-3 at 1024x1024, standard quality, n=1, which is exactly what
    # the openai branch below sends. Published list price was $0.040/image;
    # estimate, check current pricing.
    "openai": 0.040,
    # OpenRouter: priced per model, and the openrouter branch sends NO size, so
    # this is a deliberately conservative default for any
    # OPENROUTER_IMAGE_MODEL rather than a quote for one model.
    # estimate, check current pricing.
    "openrouter": 0.05,
}

#: Used for a paid provider with no entry above, so a newly added one is never
#: silently free.
DEFAULT_IMAGE_COST_ESTIMATE_USD = 0.05


def _exception_chain(exc: BaseException) -> list[BaseException]:
    """Every exception reachable from ``exc``.

    Walks ``__cause__``, ``__context__``, the exception arguments and any
    ``reason`` attribute, because ``requests`` wraps the real cause: a DNS
    failure arrives as
    ``ConnectionError(MaxRetryError(..., reason=NewConnectionError(...)))``
    and the interesting class is two levels down.
    """
    seen: list[BaseException] = []
    pending: list[object] = [exc]
    while pending:
        item = pending.pop()
        if not isinstance(item, BaseException) or any(item is known for known in seen):
            continue
        seen.append(item)
        pending.append(item.__cause__)
        pending.append(item.__context__)
        pending.extend(arg for arg in item.args if isinstance(arg, BaseException))
        pending.append(getattr(item, "reason", None))
    return seen


def _definitely_not_billed(exc: BaseException) -> bool:
    """True only when the provider provably did NOT bill us.

    RELEASE only for:
      * ``requests.ConnectTimeout`` -- the connection was never established, so
        no request was sent;
      * a ``requests.ConnectionError`` whose cause chain contains
        ``urllib3.exceptions.NewConnectionError`` or ``NameResolutionError``,
        i.e. connection refused or DNS failure: nothing was sent.

    EVERYTHING else KEEPS the reservation: ``ReadTimeout``,
    ``ChunkedEncodingError``, ``SSLError``, ``ProxyError`` (both are
    ``ConnectionError`` SUBCLASSES, so a naive ``except ConnectionError``
    releases them, which is wrong: a TLS handshake failure or a proxy error can
    happen after the request bytes were written), a ``ConnectionError`` wrapping
    ``ProtocolError`` / ``RemoteDisconnected`` (a mid-response reset, again
    after bytes were sent), and any exception we do not recognise.

    Over-counting is the safe direction: a wrongly KEPT reservation costs the
    user a little budget they may not have spent, while a wrongly RELEASED one
    loses track of money that was already spent and lets the cap be exceeded.
    """
    if isinstance(exc, requests.ConnectTimeout):
        return True
    if isinstance(exc, requests.ConnectionError):
        for item in _exception_chain(exc):
            if isinstance(item, urllib3.exceptions.NewConnectionError | urllib3.exceptions.NameResolutionError):
                return True
    return False


def _reported_cost_usd(payload: dict[str, Any]) -> float | None:
    """The cost a provider response actually reported, or None.

    Read defensively because the shape differs by provider: some return a top
    level ``cost``, some nest it under ``usage``. Returns None rather than 0.0
    when nothing is reported, so the caller keeps its estimate instead of
    treating "no cost field" as "free".
    """
    if not isinstance(payload, dict):
        return None
    for key in ("cost", "cost_usd"):
        value = payload.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
    usage = payload.get("usage")
    if isinstance(usage, dict):
        for key in ("cost", "cost_usd", "total_cost"):
            value = usage.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
    return None


class SigilService:
    """
    Sigil generation engine. Combines traditional planetary Kamea grid drawing
    with AI image generation (local Stable Diffusion, the local render engine, or cloud).
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, storage_dir: str | None = None):
        if self._initialized:
            return

        if storage_dir is None:
            home = Path.home()
            storage_dir = str(home / ".vajra-stream" / "sigils")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Load API configurations from environment
        self.sd_api_url = os.getenv("SD_API_URL", "http://127.0.0.1:7860/sdapi/v1/txt2img")
        # local (A1111 SD), comfyui (the render engine at settings.COMFYUI_BASE_URL), openrouter, openai, none
        self.image_provider = os.getenv("IMAGE_PROVIDER", "local")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openrouter_image_model = os.getenv("OPENROUTER_IMAGE_MODEL", "stabilityai/stable-diffusion-xl")

        self._initialized = True

    def reduce_text(self, text: str) -> str:
        """Removes vowels, spaces, and duplicate characters from the intention"""
        text = text.upper().strip()
        # Remove non-alpha
        text = re.sub(r"[^A-Z]", "", text)

        # Remove vowels (A, E, I, O, U)
        reduced = ""
        vowels = set("AEIOU")
        for char in text:
            if char not in vowels:
                reduced += char

        # Remove duplicate letters
        seen = set()
        final_chars = []
        for char in reduced:
            if char not in seen:
                seen.add(char)
                final_chars.append(char)

        # If empty, fallback to the original string filtered for unique letters
        if not final_chars:
            for char in text:
                if char not in seen:
                    seen.add(char)
                    final_chars.append(char)

        return "".join(final_chars)

    def text_to_coordinates(self, text: str, kamea_name: str = "saturn") -> list[dict[str, float]]:
        """Maps letters to 2D coordinates on a planetary Kamea grid"""
        kamea_name = kamea_name.lower()
        if kamea_name not in KAMEAS:
            kamea_name = "saturn"

        kamea = KAMEAS[kamea_name]
        size = kamea["size"]
        grid = kamea["grid"]

        reduced = self.reduce_text(text)
        coords = []

        # Map values A=1, B=2, ..., Z=26
        # In case value > size^2, we wrap using modulo
        max_val = size * size

        for char in reduced:
            val = ord(char) - ord("A") + 1
            # Adjust to fit magic square scale (1 to N^2)
            wrapped_val = ((val - 1) % max_val) + 1

            # Find in grid
            found = False
            for r in range(size):
                for c in range(size):
                    if grid[r][c] == wrapped_val:
                        coords.append({"x": c, "y": r, "value": wrapped_val, "letter": char})
                        found = True
                        break
                if found:
                    break

        return coords

    def render_svg_from_coords(self, coords: list[dict], kamea_name: str = "saturn") -> str:
        """Render a kamea sigil SVG from pre-computed coordinates.

        Accepts coordinate dicts produced by :meth:`text_to_coordinates`
        (each carrying ``x``, ``y``, ``value``, ``letter``) and draws the
        glowing neon path on the appropriate planetary magic square.
        """
        kamea = KAMEAS.get(kamea_name.lower(), KAMEAS["saturn"])
        size = kamea["size"]

        # Grid parameters
        width = 400
        height = 400
        padding = 50

        # Cell size
        cell_w = (width - padding * 2) / (size - 1) if size > 1 else width - padding * 2

        # Helper to convert grid coords to pixels
        def to_pixels(gx, gy):
            px = padding + gx * cell_w
            py = padding + gy * cell_w
            return px, py

        svg_paths = []

        if len(coords) > 0:
            # Draw line segments
            px, py = to_pixels(coords[0]["x"], coords[0]["y"])
            svg_paths.append(f"M {px} {py}")
            for pt in coords[1:]:
                cx, cy = to_pixels(pt["x"], pt["y"])
                svg_paths.append(f"L {cx} {cy}")

        path_data = " ".join(svg_paths)

        # Build SVG string with glow effects
        start_circle = ""
        end_bar = ""

        if coords:
            # Start node gets a circle
            sx, sy = to_pixels(coords[0]["x"], coords[0]["y"])
            start_circle = (
                f'<circle cx="{sx}" cy="{sy}" r="7" fill="none" stroke="#00ffff" stroke-width="3" filter="url(#glow)"/>'
            )

            # End node gets a crossbar
            if len(coords) > 1:
                ex, ey = to_pixels(coords[-1]["x"], coords[-1]["y"])
                # Compute orientation from second to last point if possible
                end_bar = f'<line x1="{ex - 8}" y1="{ey}" x2="{ex + 8}" y2="{ey}" stroke="#ff00ff" stroke-width="4" filter="url(#glow)"/>'
                end_bar += f'<line x1="{ex}" y1="{ey - 8}" x2="{ex}" y2="{ey + 8}" stroke="#ff00ff" stroke-width="4" filter="url(#glow)"/>'

        # Grid background representation
        bg_grid = []
        for r in range(size):
            for c in range(size):
                gx, gy = to_pixels(c, r)
                # Small faint dots for the kamea grid points
                bg_grid.append(
                    f'<circle cx="{gx}" cy="{gy}" r="2.5" fill="#1e293b" stroke="#334155" stroke-width="1"/>'
                )

        grid_svg = "\n    ".join(bg_grid)

        svg = f"""<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background:#090d16; border-radius:12px;">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
  <!-- Kamea Grid Overlay -->
  {grid_svg}

  <!-- Sigil Line Path -->
  {f'<path d="{path_data}" fill="none" stroke="#00ffff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>' if path_data else ""}

  <!-- Start & End Terminals -->
  {start_circle}
  {end_bar}
</svg>"""
        return svg

    def generate_kamea_svg(self, intention: str, kamea_name: str = "saturn") -> str:
        """Generates a glowing neon SVG sigil drawn on a planetary magic square.

        This is a convenience wrapper that reduces the intention text to
        coordinates and delegates to :meth:`render_svg_from_coords`.
        """
        coords = self.text_to_coordinates(intention, kamea_name)
        return self.render_svg_from_coords(coords, kamea_name)

    def _submit_render(self, prompt: str, caption_facts: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """Queue the sigil image on the local render engine (ComfyUI, ``purpose="sigil"``); never blocks.

        The render takes minutes, so the forge returns the queued operation instead
        of an image; the PNG appears at the operation's ``result.image_url`` on success.
        """
        from backend.core.services.render.jobs import RenderJobRequest, submit_job

        try:
            op = submit_job(RenderJobRequest(prompt=prompt, purpose="sigil", caption_facts=caption_facts or None))
        except Exception as e:
            logger.warning(f"Local render submission for sigil failed: {e}")
            return {"operation_id": None, "status": "error", "error": str(e)[:300]}
        return {"operation_id": op["id"], "status": op["status"]}

    async def generate_ai_image(
        self, intention: str, caption_facts: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """AI image for a sigil, by ``IMAGE_PROVIDER``.

        Returns ``{"ai_image": data URI or None, "ai_image_render": queued render or None}``.
        ``comfyui`` queues a local render job (``ai_image_render`` = ``{"operation_id", "status"}``);
        the other providers answer synchronously with a data URI, or None if unconfigured/failed.
        """
        prompt = sigil_image_prompt(intention)

        if self.image_provider == "comfyui":
            return {"ai_image": None, "ai_image_render": self._submit_render(prompt, caption_facts)}

        image, skip_reason = await self._generate_sync_image(prompt)
        result: dict[str, Any] = {"ai_image": image, "ai_image_render": None}
        # Additive: existing keys and types are untouched, and the key appears
        # ONLY when something was actually skipped, so nothing that reads
        # ai_image / ai_image_render sees a new shape on the normal path.
        if skip_reason is not None:
            result["ai_image_skipped"] = skip_reason
        return result

    async def _generate_sync_image(self, prompt: str) -> tuple[str | None, str | None]:
        """Providers that return an image in one request (A1111 SD, OpenAI, OpenRouter).

        Their HTTP calls block for up to a minute, so they run in a worker thread.
        Returns ``(image, skip_reason)``; see :meth:`_request_image`.
        """
        return await asyncio.to_thread(self._request_image, prompt)

    def _request_image(self, prompt: str) -> tuple[str | None, str | None]:
        """Blocking body of :meth:`_generate_sync_image`.

        Returns ``(image_data_uri, skip_reason)``. ``skip_reason`` is ``"budget"``
        when the shared image budget refused the call; it is ``None`` otherwise.
        The local and comfyui providers are free and reserve nothing at all.

        A reservation is RELEASED only when the provider definitely did not bill:
        a connection failure before the request was sent, or a non-2xx status from
        the GENERATION request. Every other failure KEEPS the reservation at the
        estimate and logs one warning, because the spend is genuinely uncertain:
        a ReadTimeout means the request was transmitted and may have been billed,
        a 2xx body we cannot parse means the image WAS generated, and a failed
        image download means the generation itself succeeded. Refunding a call
        that was paid for is the more expensive mistake.
        """
        if self.image_provider == "local":
            try:
                # Direct SD text2img endpoint call
                payload = {
                    "prompt": prompt,
                    "negative_prompt": "low quality, text, label, watermark, blurry, realistic, photo, human, face",
                    "steps": 25,
                    "width": 512,
                    "height": 512,
                    "cfg_scale": 7.5,
                }

                response = requests.post(self.sd_api_url, json=payload, timeout=45)
                if response.status_code == 200:
                    res_json = response.json()
                    # A1111 returns images in a list of base64 strings
                    if "images" in res_json and len(res_json["images"]) > 0:
                        img_b64 = res_json["images"][0]
                        # Return base64 URI
                        return f"data:image/png;base64,{img_b64}", None
            except Exception as e:
                logger.warning(f"Local Stable Diffusion generation failed or offline: {e}")

        elif self.image_provider == "openai" and self.openai_api_key:
            reservation = self._reserve_image_budget("openai")
            if reservation is None:
                return None, "budget"
            try:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.openai_api_key}"}
                payload = {
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "response_format": "b64_json",
                }
                response = requests.post(
                    "https://api.openai.com/v1/images/generations", json=payload, headers=headers, timeout=60
                )
            except Exception as e:
                # Release ONLY when the request provably never reached the
                # provider. Everything else keeps the estimate.
                if _definitely_not_billed(e):
                    shared_image_budget().release(reservation)
                    logger.error("OpenAI DALL-E generation failed: %s", e)
                else:
                    self._keep_reservation("openai", f"{type(e).__name__}: {e}")
                    logger.error("OpenAI DALL-E generation failed: %s", e)
                return None, None
            if not (200 <= response.status_code < 300):
                # The provider answered "no", so it did not bill us.
                shared_image_budget().release(reservation)
                logger.error("OpenAI DALL-E generation failed: HTTP %s", response.status_code)
                return None, None
            # 2xx: the generation happened and was billed, whatever we make of
            # the body. Any failure from here keeps the reservation.
            try:
                res_json = response.json()
                img_b64 = res_json["data"][0]["b64_json"]
                self._settle_image_budget(reservation, res_json)
                return f"data:image/png;base64,{img_b64}", None
            except Exception as e:
                self._keep_reservation("openai", f"{type(e).__name__}: {e}")
                logger.error("OpenAI DALL-E generation failed: %s", e)
            return None, None

        elif self.image_provider == "openrouter" and self.openrouter_api_key:
            reservation = self._reserve_image_budget("openrouter")
            if reservation is None:
                return None, "budget"
            # The GENERATION request and the image DOWNLOAD are separate
            # phases. Once the generation has returned 2xx it is billed, so a
            # failure in the download must never release the reservation.
            try:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.openrouter_api_key}"}
                payload = {"prompt": prompt, "model": self.openrouter_image_model}
                response = requests.post(
                    "https://openrouter.ai/api/v1/images/generations", json=payload, headers=headers, timeout=45
                )
            except Exception as e:
                if _definitely_not_billed(e):
                    shared_image_budget().release(reservation)
                    logger.error("OpenRouter image generation failed: %s", e)
                else:
                    self._keep_reservation("openrouter", f"{type(e).__name__}: {e}")
                    logger.error("OpenRouter image generation failed: %s", e)
                return None, None
            if not (200 <= response.status_code < 300):
                shared_image_budget().release(reservation)
                logger.error("OpenRouter image generation failed: HTTP %s", response.status_code)
                return None, None
            # Billed. Everything below may fail, and every failure keeps it.
            try:
                res_json = response.json()
                rows = res_json.get("data") if isinstance(res_json, dict) else None
                if rows:
                    img_url = rows[0].get("url")
                    if img_url:
                        img_data = requests.get(img_url, timeout=15)
                        if 200 <= img_data.status_code < 300:
                            b64_str = base64.b64encode(img_data.content).decode("utf-8")
                            self._settle_image_budget(reservation, res_json)
                            return f"data:image/png;base64,{b64_str}", None
                        raise RuntimeError(f"image download returned HTTP {img_data.status_code}")
                reason = "generation succeeded but no usable image was returned"
            except Exception as e:
                reason = f"{type(e).__name__}: {e}"
            self._keep_reservation("openrouter", reason)
            logger.error("OpenRouter image generation failed: %s", reason)
            return None, None

        return None, None

    @staticmethod
    def _keep_reservation(provider_name: str, reason: str) -> None:
        """Log that a possibly-billed call is still holding its estimate."""
        logger.warning(
            "Sigil AI image: keeping the budget reservation for %s because the spend is "
            "uncertain (%s). The image may have been generated and billed, so the estimate "
            "is kept rather than refunded.",
            provider_name,
            reason,
        )

    def _reserve_image_budget(self, provider_name: str) -> "Reservation | None":
        """Hold the estimated cost of one paid sigil image, or return None.

        Sigil images and generated images share ONE daily budget, so a sigil can
        be refused because earlier images spent the cap. That is the point of the
        change rather than a failure: the caller logs one warning and returns no
        image instead of raising into the sigil endpoint.
        """
        estimate = SIGIL_IMAGE_COST_ESTIMATE_USD.get(provider_name, DEFAULT_IMAGE_COST_ESTIMATE_USD)
        reservation = shared_image_budget().try_reserve(estimate)
        if reservation is None:
            logger.warning(
                "Sigil AI image skipped: the shared image budget refused this %s call "
                "(estimated $%.4f). Sigils and generated images share one daily cap -- raise "
                "the image daily cap in Settings, or wait for the UTC day to roll over.",
                provider_name,
                estimate,
            )
        return reservation

    @staticmethod
    def _settle_image_budget(reservation: "Reservation", payload: dict[str, Any]) -> None:
        """Reconcile to the provider's reported actual cost, or keep the estimate.

        dall-e-3 normally reports no cost, so the estimate stands. When a provider
        does report one it is the authority and the estimate is ADJUSTED, rather
        than the actual being added on top of it.
        """
        actual = _reported_cost_usd(payload)
        budget_cost = reservation.estimated_cost_usd if actual is None else actual
        shared_image_budget().reconcile(reservation, budget_cost)

    async def forge_sigil(self, intention: str, kamea_name: str = "saturn") -> dict[str, Any]:
        """Forges a sigil, returning coordinates, Kamea SVG, and optional AI generated image URL/data"""
        reduced = self.reduce_text(intention)
        svg_content = self.generate_kamea_svg(intention, kamea_name)

        # Save signature log
        forged_at = time.time()
        sigil_id = f"sigil_{int(forged_at)}"

        # The real values travel beside the image as captions, never painted into it.
        caption_facts = [
            caption_fact("Intention", intention[:300], "record"),
            caption_fact("Kamea", kamea_name, "record"),
            caption_fact(
                "Forged", datetime.fromtimestamp(forged_at, timezone.utc).isoformat(timespec="seconds"), "record"
            ),
        ]

        # AI image if configured: inline for hosted providers, a queued render job for comfyui
        ai = await self.generate_ai_image(intention, caption_facts)

        # Save to disk
        sigil_data = {
            "id": sigil_id,
            "intention": intention,
            "reduced_letters": reduced,
            "kamea": kamea_name,
            "svg": svg_content,
            "ai_image": ai["ai_image"],
            # {"operation_id", "status"} of the local render job, or None (see generate_ai_image)
            "ai_image_render": ai["ai_image_render"],
            "caption_facts": caption_facts,
            "timestamp": forged_at,
        }
        # Propagated only when set (see generate_ai_image): a budget refusal is
        # visible in the stored sigil rather than looking like a provider outage.
        if "ai_image_skipped" in ai:
            sigil_data["ai_image_skipped"] = ai["ai_image_skipped"]

        try:
            with open(self.storage_dir / f"{sigil_id}.json", "w", encoding="utf-8") as f:
                json.dump(sigil_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write sigil JSON file: {e}")

        return sigil_data


# Global instance
sigil_service = SigilService()
