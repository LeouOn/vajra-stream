"""Draw a computed sky (``core.sky.plan_sky``) onto a rendered scene with Pillow.

The scene keeps its own file; the composite is written beside it as
``<stem>.sky.png`` with a ``<stem>.sky.json`` sidecar holding the plan and the
caption facts, so the uncomposited render is never lost and any reader of the
render directory can tell the two apart.

The Moon is drawn as a disk whose lit part is bounded by the terminator
ellipse: in disk coordinates ``u`` (toward the bright limb) and ``v``
(across it), a point is lit when ``u >= (1 - 2f) * sqrt(1 - v**2)`` for an
illuminated fraction ``f`` -- which lights exactly the fraction ``f`` of the
disk's area. Planets are small glowing points sized by magnitude. Nothing
else (no stars, no glyphs, no labels) is added.
"""

from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from core.image_prompts import caption_fact
from core.sky import MOON_SCALE, limb_unit_vector, overlay_caption_fact, plan_sky, unavailable_fact

logger = logging.getLogger(__name__)

SUPERSAMPLE = 4

# Colours (RGB). Kept muted so the drawn sky sits in a painted scene.
MOON_LIT = (246, 242, 226)
MOON_EARTHSHINE = (120, 128, 150)
PLANET_COLOURS: dict[str, tuple[int, int, int]] = {
    "Venus": (255, 252, 240),
    "Jupiter": (255, 244, 220),
    "Mars": (255, 176, 130),
    "Saturn": (250, 230, 180),
    "Mercury": (240, 230, 220),
}

# How strongly each part shows, by sky period: (lit alpha, earthshine alpha, glow alpha).
_PERIOD_STYLE: dict[str, tuple[float, float, float]] = {
    "day": (0.82, 0.0, 0.0),
    "twilight": (0.95, 0.06, 0.25),
    "night": (1.0, 0.10, 0.35),
}


def composite_paths(scene: Path) -> tuple[Path, Path]:
    """``(<stem>.sky.png, <stem>.sky.json)`` beside a scene file."""
    return scene.with_name(f"{scene.stem}.sky.png"), scene.with_name(f"{scene.stem}.sky.json")


def moon_lit_mask(size: int, illumination: float, limb_angle: float) -> np.ndarray:
    """Float mask ``size`` x ``size``: 1 where the disk is lit, 0 elsewhere (no antialiasing).

    ``illumination`` is a percentage (0-100); ``limb_angle`` is the bright
    limb's direction in degrees counter-clockwise from up. Pixels outside the
    inscribed disk are 0.
    """
    disk, lit = _moon_masks(size, illumination, limb_angle)
    return (disk & lit).astype(np.float32)


def moon_disk_mask(size: int) -> np.ndarray:
    """Float mask of the inscribed disk."""
    disk, _ = _moon_masks(size, 50.0, 0.0)
    return disk.astype(np.float32)


def _moon_masks(size: int, illumination: float, limb_angle: float) -> tuple[np.ndarray, np.ndarray]:
    r = size / 2.0
    coords = (np.arange(size, dtype=np.float64) + 0.5 - r) / r
    dx, dy = np.meshgrid(coords, coords)  # x right, y down, in disk radii
    bx, by = limb_unit_vector(limb_angle)
    u = dx * bx + dy * by  # toward the bright limb
    v = dx * -by + dy * bx  # across it
    rr = dx * dx + dy * dy
    disk = rr <= 1.0
    f = max(0.0, min(1.0, float(illumination) / 100.0))
    lit = u >= (1.0 - 2.0 * f) * np.sqrt(np.clip(1.0 - v * v, 0.0, 1.0))
    return disk, lit


def _layer(mask: np.ndarray, colour: tuple[int, int, int], alpha: float) -> Image.Image:
    a = np.clip(mask * alpha * 255.0, 0, 255).astype(np.uint8)
    rgb = np.empty((*mask.shape, 3), dtype=np.uint8)
    rgb[...] = colour
    return Image.fromarray(np.dstack([rgb, a]), "RGBA")


def moon_sprite(radius: float, illumination: float, limb_angle: float, period: str | None) -> Image.Image:
    """The Moon as an RGBA sprite (antialiased by supersampling), centred, with a soft glow margin."""
    lit_a, shine_a, glow_a = _PERIOD_STYLE.get(period or "night", _PERIOD_STYLE["night"])
    diameter = max(2, int(math.ceil(radius * 2)))
    big = diameter * SUPERSAMPLE
    disk, lit = _moon_masks(big, illumination, limb_angle)
    lit_mask = (disk & lit).astype(np.float32)
    dark_mask = (disk & ~lit).astype(np.float32)
    # gentle limb darkening on the lit side
    r = big / 2.0
    coords = (np.arange(big, dtype=np.float64) + 0.5 - r) / r
    dx, dy = np.meshgrid(coords, coords)
    shade = (0.82 + 0.18 * np.sqrt(np.clip(1.0 - dx * dx - dy * dy, 0.0, 1.0))).astype(np.float32)
    sprite = Image.alpha_composite(
        _layer(dark_mask, MOON_EARTHSHINE, shine_a), _layer(lit_mask * shade, MOON_LIT, lit_a)
    ).resize((diameter, diameter), Image.Resampling.LANCZOS)

    pad = int(math.ceil(radius * 1.2)) + 2
    canvas = Image.new("RGBA", (diameter + 2 * pad, diameter + 2 * pad), (0, 0, 0, 0))
    if glow_a > 0 and illumination > 0.5:
        glow_src = Image.new("L", canvas.size, 0)
        glow_src.paste(sprite.getchannel("A"), (pad, pad))
        glow = glow_src.filter(ImageFilter.GaussianBlur(radius * 0.6))
        glow_alpha = glow.point(lambda p: int(p * glow_a))
        halo = Image.new("RGBA", canvas.size, (*MOON_LIT, 0))
        halo.putalpha(glow_alpha)
        canvas = Image.alpha_composite(canvas, halo)
    canvas.alpha_composite(sprite, (pad, pad))
    return canvas


def planet_radius(magnitude: float) -> float:
    """Drawn core radius (px) of a planet: brighter (lower magnitude) is bigger."""
    return max(1.6, min(4.5, 2.6 - 0.45 * magnitude))


def _draw_planet(image: Image.Image, x: float, y: float, magnitude: float, colour: tuple[int, int, int]) -> None:
    core_r = planet_radius(magnitude)
    size = int(math.ceil(core_r * 8)) + 4
    big = size * SUPERSAMPLE
    glow = Image.new("L", (big, big), 0)
    ImageDraw.Draw(glow).ellipse(
        [big / 2 - core_r * SUPERSAMPLE * 2.2, big / 2 - core_r * SUPERSAMPLE * 2.2]
        + [big / 2 + core_r * SUPERSAMPLE * 2.2, big / 2 + core_r * SUPERSAMPLE * 2.2],
        fill=70,
    )
    glow = glow.filter(ImageFilter.GaussianBlur(core_r * SUPERSAMPLE * 1.4))
    ImageDraw.Draw(glow).ellipse(
        [big / 2 - core_r * SUPERSAMPLE, big / 2 - core_r * SUPERSAMPLE]
        + [big / 2 + core_r * SUPERSAMPLE, big / 2 + core_r * SUPERSAMPLE],
        fill=255,
    )
    alpha = glow.resize((size, size), Image.Resampling.LANCZOS)
    sprite = Image.new("RGBA", (size, size), (*colour, 0))
    sprite.putalpha(alpha)
    image.alpha_composite(sprite, (int(round(x - size / 2)), int(round(y - size / 2))))


def draw_sky(scene: Image.Image, plan: dict[str, Any]) -> Image.Image:
    """A copy of ``scene`` with every ``drawn`` body of ``plan`` painted on (RGB)."""
    out = scene.convert("RGBA")
    if out.size != (plan["camera"]["width"], plan["camera"]["height"]):
        raise ValueError(f"plan is for {plan['camera']['width']}x{plan['camera']['height']}, scene is {out.size}")
    for planet in plan["planets"]:
        if planet.get("drawn"):
            colour = PLANET_COLOURS.get(planet["name"], (255, 255, 255))
            _draw_planet(out, planet["x"], planet["y"], float(planet["magnitude"]), colour)
    moon = plan["moon"]
    if moon.get("drawn") and moon["illumination"] > 0.0:
        sprite = moon_sprite(
            float(moon["radius_px"]),
            float(moon["illumination"]),
            float(moon["bright_limb_from_vertical"]),
            plan.get("period"),
        )
        out.alpha_composite(
            sprite,
            (int(round(moon["x"] - sprite.width / 2)), int(round(moon["y"] - sprite.height / 2))),
        )
    return out.convert("RGB")


def composite_file(scene_path: Path, plan: dict[str, Any], caption_facts: list[dict[str, str]]) -> Path:
    """Write ``<stem>.sky.png`` (and its ``.sky.json``) beside ``scene_path``; the scene is not touched.

    Idempotent: an existing composite is reused, not redrawn. Returns the composite path.
    """
    out_png, out_json = composite_paths(scene_path)
    if not out_png.is_file():
        with Image.open(scene_path) as scene:
            drawn = draw_sky(scene, plan)
        tmp = out_png.with_name(out_png.name + ".part")
        drawn.save(tmp, format="PNG")
        os.replace(tmp, out_png)
    sidecar = {"scene": scene_path.name, "composite": out_png.name, "sky": plan, "caption_facts": caption_facts}
    out_json.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    return out_png


def read_sidecar(scene_path: Path) -> dict[str, Any] | None:
    """The ``.sky.json`` beside a scene, if a composite exists for it."""
    out_png, out_json = composite_paths(scene_path)
    if not out_png.is_file() or not out_json.is_file():
        return None
    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


# -- the folio witness ---------------------------------------------------------------

SKY_METHOD = (
    "Scene rendered with an empty sky; Sun, Moon and bright planets computed with the Swiss Ephemeris "
    "for the observer at sealed_at (core/sky.py) and drawn onto it with Pillow (core/sky_composite.py)."
)


def composite_image_url(op_id: str) -> str:
    """Where the API serves the composite of render ``op_id`` (``GET /gallery/sky/{op_id}/image``)."""
    return f"/api/v1/gallery/sky/{op_id}/image"


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def _not_drawn(block: dict[str, Any], record: dict[str, Any], reason: str) -> dict[str, Any]:
    facts = list(block.get("caption_facts") or [])
    facts.append(caption_fact("Sky overlay", f"not drawn: {reason}", "record"))
    return {**block, "caption_facts": facts, "sky": {**record, "composited": False, "reason": reason}}


def composite_witness(block: dict[str, Any], op: dict[str, Any], computed: dict[str, Any] | None) -> dict[str, Any]:
    """The witness ``block`` of a finished render with the true sky drawn on, or why it is not.

    ``computed`` is :func:`core.sky.compute_sky` for the folio (``None``: the
    ephemeris is unavailable, so the scene is kept as it is and the caption
    says the sky could not be computed). The rendered scene file is never
    modified; the composite is written beside it and ``image_url`` points at
    it, with the scene still at ``scene_image_url``.
    """
    record: dict[str, Any] = {"method": SKY_METHOD}
    if computed is None:
        facts = list(block.get("caption_facts") or [])
        if not any(f.get("label") == "Sky at sealing" for f in facts):
            facts.append(unavailable_fact())
        return {**block, "caption_facts": facts, "sky": {**record, "computed": False, "composited": False}}

    # The render engine owns where its PNG lives; core may not import backend at module level.
    from backend.core.services.render.jobs import image_file

    scene = image_file(op)
    if scene is None:
        return _not_drawn(block, {**record, **computed}, "the rendered scene file was not found")
    try:
        width = int(block.get("width") or 0)
        height = int(block.get("height") or 0)
        if width <= 0 or height <= 0:
            width, height = image_size(scene)
        plan = plan_sky(computed, width, height)
        facts = [*(block.get("caption_facts") or []), overlay_caption_fact(plan)]
        out = composite_file(scene, plan, facts)
    except Exception as exc:  # a drawing failure keeps the plain scene and says so
        logger.exception("could not draw the sky onto render %s", op.get("id"))
        return _not_drawn(block, {**record, **computed}, f"compositing failed ({type(exc).__name__})")
    sky_record = {
        **record,
        **plan,
        "computed": True,
        "composited": True,
        "moon_scale_note": f"moon drawn at {MOON_SCALE:g}× apparent size",
        "scene_image_url": block.get("image_url"),
        "composite_file": out.name,
    }
    return {
        **block,
        "image_url": composite_image_url(str(op["id"])),
        "scene_image_url": block.get("image_url"),
        "caption_facts": facts,
        "sky": sky_record,
    }
