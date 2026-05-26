"""
Sigil Forging & Generator Service
"""

import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

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


class SigilService:
    """
    Sigil generation engine. Combines traditional planetary Kamea grid drawing
    with AI image generation endpoints (local Stable Diffusion / ComfyUI / cloud).
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
        self.image_provider = os.getenv("IMAGE_PROVIDER", "local")  # local, comfyui, openrouter, openai, none
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.comfyui_api_url = os.getenv("COMFYUI_API_URL", "http://127.0.0.1:8188")
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

    def generate_kamea_svg(self, intention: str, kamea_name: str = "saturn") -> str:
        """Generates a glowing neon SVG sigil drawn on a planetary magic square"""
        coords = self.text_to_coordinates(intention, kamea_name)
        kamea = KAMEAS.get(kamea_name, KAMEAS["saturn"])
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

    async def generate_ai_image(self, intention: str) -> str | None:
        """Generates a high-quality AI sigil from intention. Falls back to None if unconfigured/fails."""
        import asyncio

        prompt = f"Abstract esoteric cyber-sigil, representing intention: '{intention}', sacred geometry grid, glowing cyan and magenta runes, orgone sandwiches, crystalline core structure, high-tech cyberdeck dashboard element, digital art, dark background, 8k render"

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

        elif self.image_provider == "comfyui":
            try:
                # ComfyUI Headless Execution
                workflow_path = Path("comfy_workflow.json")
                if workflow_path.exists():
                    with open(workflow_path, encoding="utf-8") as f:
                        workflow = json.load(f)
                else:
                    # Default SD 1.5 workflow graph
                    workflow = {
                        "3": {"inputs": {"text": prompt, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
                        "4": {
                            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.ckpt"},
                            "class_type": "CheckpointLoaderSimple",
                        },
                        "5": {
                            "inputs": {"width": 512, "height": 512, "batch_size": 1},
                            "class_type": "EmptyLatentImage",
                        },
                        "6": {
                            "inputs": {
                                "seed": int(time.time()) % 1000000,
                                "steps": 20,
                                "cfg": 8.0,
                                "sampler_name": "euler",
                                "scheduler": "normal",
                                "denoise": 1.0,
                                "model": ["4", 0],
                                "positive": ["3", 0],
                                "negative": ["7", 0],
                                "latent_image": ["5", 0],
                            },
                            "class_type": "KSampler",
                        },
                        "7": {
                            "inputs": {"text": "low quality, blurry, text, logo, face, human", "clip": ["4", 1]},
                            "class_type": "CLIPTextEncode",
                        },
                        "8": {"inputs": {"samples": ["6", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
                        "9": {
                            "inputs": {"filename_prefix": "VajraSigil", "images": ["8", 0]},
                            "class_type": "SaveImage",
                        },
                    }

                # Update workflow with prompt text
                if "3" in workflow and "inputs" in workflow["3"] and "text" in workflow["3"]["inputs"]:
                    workflow["3"]["inputs"]["text"] = prompt
                else:
                    for node_id, node in workflow.items():
                        if node.get("class_type") == "CLIPTextEncode" and "inputs" in node:
                            txt = node["inputs"].get("text", "")
                            if "low quality" not in txt.lower():
                                node["inputs"]["text"] = prompt
                                break

                # Queue the prompt
                response = requests.post(f"{self.comfyui_api_url}/prompt", json={"prompt": workflow}, timeout=10)
                if response.status_code == 200:
                    res_data = response.json()
                    prompt_id = res_data.get("prompt_id")

                    if prompt_id:
                        # Poll for history completion (up to 40 seconds)
                        completed = False
                        filename = None
                        subfolder = None

                        for _ in range(40):
                            await asyncio.sleep(1.0)
                            hist_res = requests.get(f"{self.comfyui_api_url}/history/{prompt_id}", timeout=5)
                            if hist_res.status_code == 200:
                                hist_data = hist_res.json()
                                if prompt_id in hist_data:
                                    outputs = hist_data[prompt_id].get("outputs", {})
                                    for node_id, output in outputs.items():
                                        if "images" in output and len(output["images"]) > 0:
                                            img_info = output["images"][0]
                                            filename = img_info.get("filename")
                                            subfolder = img_info.get("subfolder", "")
                                            completed = True
                                            break
                                    if completed:
                                        break

                        if completed and filename:
                            view_url = (
                                f"{self.comfyui_api_url}/view?filename={filename}&subfolder={subfolder}&type=output"
                            )
                            img_res = requests.get(view_url, timeout=10)
                            if img_res.status_code == 200:
                                b64_str = base64.b64encode(img_res.content).decode("utf-8")
                                return f"data:image/png;base64,{b64_str}"
            except Exception as e:
                logger.warning(f"ComfyUI headless generation failed or offline: {e}")

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
        sigil_id = f"sigil_{int(time.time())}"

        # Request AI generation in the background (if configured)
        ai_image_uri = await self.generate_ai_image(intention)

        # Save to disk
        sigil_data = {
            "id": sigil_id,
            "intention": intention,
            "reduced_letters": reduced,
            "kamea": kamea_name,
            "svg": svg_content,
            "ai_image": ai_image_uri,
            "timestamp": time.time(),
        }

        try:
            with open(self.storage_dir / f"{sigil_id}.json", "w", encoding="utf-8") as f:
                json.dump(sigil_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write sigil JSON file: {e}")

        return sigil_data


# Global instance
sigil_service = SigilService()
