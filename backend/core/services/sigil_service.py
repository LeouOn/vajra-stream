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
        return {"ai_image": await self._generate_sync_image(prompt), "ai_image_render": None}

    async def _generate_sync_image(self, prompt: str) -> str | None:
        """Providers that return an image in one request (A1111 SD, OpenAI, OpenRouter).

        Their HTTP calls block for up to a minute, so they run in a worker thread.
        """
        return await asyncio.to_thread(self._request_image, prompt)

    def _request_image(self, prompt: str) -> str | None:
        """Blocking body of :meth:`_generate_sync_image`."""
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
                        return f"data:image/png;base64,{img_b64}"
            except Exception as e:
                logger.warning(f"Local Stable Diffusion generation failed or offline: {e}")

        elif self.image_provider == "openai" and self.openai_api_key:
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
                if response.status_code == 200:
                    res_json = response.json()
                    img_b64 = res_json["data"][0]["b64_json"]
                    return f"data:image/png;base64,{img_b64}"
            except Exception as e:
                logger.error(f"OpenAI DALL-E generation failed: {e}")

        elif self.image_provider == "openrouter" and self.openrouter_api_key:
            try:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.openrouter_api_key}"}
                payload = {"prompt": prompt, "model": self.openrouter_image_model}
                response = requests.post(
                    "https://openrouter.ai/api/v1/images/generations", json=payload, headers=headers, timeout=45
                )
                if response.status_code == 200:
                    res_json = response.json()
                    if "data" in res_json and len(res_json["data"]) > 0:
                        img_url = res_json["data"][0].get("url")
                        if img_url:
                            img_data = requests.get(img_url, timeout=15)
                            if img_data.status_code == 200:
                                b64_str = base64.b64encode(img_data.content).decode("utf-8")
                                return f"data:image/png;base64,{b64_str}"
            except Exception as e:
                logger.error(f"OpenRouter image generation failed: {e}")

        return None

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

        try:
            with open(self.storage_dir / f"{sigil_id}.json", "w", encoding="utf-8") as f:
                json.dump(sigil_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write sigil JSON file: {e}")

        return sigil_data


# Global instance
sigil_service = SigilService()
