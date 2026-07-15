"""Generate SVG art for all 78 Rider-Waite-Smith Tarot cards.

Reads ``knowledge/tarot_deck.json`` and writes ``knowledge/tarot_card_art.json``
with one SVG string per card, keyed by the card's display name.

Style: dark indigo background (#0b132b), gold (#d4af37) and royal purple
(#7b2cbf) accents, 200x350 tarot-card aspect ratio.
"""

from __future__ import annotations

import json
import xml.sax.saxutils
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECK_PATH = ROOT / "knowledge" / "tarot_deck.json"
OUT_PATH = ROOT / "knowledge" / "tarot_card_art.json"

W, H = 200, 350

# ---------------------------------------------------------------------------
# Palette + shared SVG fragments
# ---------------------------------------------------------------------------
BG = "#0b132b"
GOLD = "#d4af37"
PURPLE = "#7b2cbf"
LIGHT = "#e8e6f5"
DIM = "#8a7d6b"
FRAME = "#3a2a5a"
FIRE = "#e85d04"
WATER = "#48cae4"
AIR = "#a0c4ff"
EARTH = "#b08968"
RED = "#9d0208"

# A small reusable defs block (gradient + filters) is shared so the per-card
# SVG bodies stay short. We embed it inside each card so the JSON is portable.
DEFS = (
    "<defs>"
    '<radialGradient id="g" cx="50%" cy="38%" r="65%">'
    f'<stop offset="0%" stop-color="#1c2541"/>'
    f'<stop offset="100%" stop-color="{BG}"/>'
    "</radialGradient>"
    '<linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0%" stop-color="#f4d35e"/>'
    f'<stop offset="100%" stop-color="{GOLD}"/>'
    "</linearGradient>"
    '<linearGradient id="purple" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0%" stop-color="#9d4edd"/>'
    f'<stop offset="100%" stop-color="{PURPLE}"/>'
    "</linearGradient>"
    "</defs>"
)


def esc(s: str) -> str:
    """HTML-escape user-supplied text for safe inclusion in SVG."""
    return xml.sax.saxutils.escape(s)


def frame(title: str, subtitle: str, body: str, footer: str) -> str:
    """Wrap a card's body in the standard 200x350 chrome."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">'
        f"{DEFS}"
        f'<rect width="{W}" height="{H}" fill="url(#g)"/>'
        # outer ornate frame
        f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="10" '
        f'fill="none" stroke="{GOLD}" stroke-width="1.5" opacity="0.85"/>'
        f'<rect x="10" y="10" width="{W - 20}" height="{H - 20}" rx="8" '
        f'fill="none" stroke="{PURPLE}" stroke-width="0.6" opacity="0.7"/>'
        # top title
        f'<text x="{W / 2}" y="28" text-anchor="middle" '
        f'font-family="Georgia,serif" font-size="13" '
        f'fill="url(#gold)" font-style="italic">{esc(title)}</text>'
        # small ornament line under title
        f'<line x1="40" y1="36" x2="{W - 40}" y2="36" '
        f'stroke="{GOLD}" stroke-width="0.4" opacity="0.5"/>'
        # subtitle (suit / arcana)
        f'<text x="{W / 2}" y="50" text-anchor="middle" '
        f'font-family="Georgia,serif" font-size="8" '
        f'fill="{PURPLE}" letter-spacing="2">{esc(subtitle)}</text>'
        # body
        f"{body}"
        # footer (number or rank)
        f'<text x="{W / 2}" y="{H - 14}" text-anchor="middle" '
        f'font-family="Georgia,serif" font-size="9" '
        f'fill="{GOLD}" letter-spacing="1.5">{esc(footer)}</text>'
        "</svg>"
    )


# ---------------------------------------------------------------------------
# Major Arcana — 22 cards, 0..21
# ---------------------------------------------------------------------------
ROMAN = [
    "0",
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "XIII",
    "XIV",
    "XV",
    "XVI",
    "XVII",
    "XVIII",
    "XIX",
    "XX",
    "XXI",
]


def _major_visual(num: int) -> str:
    """Return a ~12-line symbolic illustration for each major-arcana card."""
    # Each tuple is (title-fragment-for-decor, svg-body-fragment).
    # The body occupies roughly y=60..y=300 inside the 200x350 card.
    cx, _cy = W / 2, 175  # visual centre

    # 0 — The Fool: youth at cliff edge with sun above
    if num == 0:
        return (
            f'<circle cx="{cx}" cy="100" r="22" fill="{GOLD}" opacity="0.8"/>'
            f'<g stroke="{GOLD}" stroke-width="1.4" fill="none">'
            f'<path d="M88 230 L112 230 L120 200 L100 195 L88 230 Z" '
            f'fill="{PURPLE}"/>'
            f'<line x1="105" y1="195" x2="105" y2="170" stroke-width="1"/>'
            f'<circle cx="105" cy="165" r="6" fill="{LIGHT}"/>'
            f'<line x1="90" y1="215" x2="80" y2="205"/>'
            f'<line x1="115" y1="200" x2="135" y2="170" stroke-width="1.6"/>'
            f"</g>"
            # cliff
            f'<path d="M70 300 L70 245 L130 240 L130 300 Z" '
            f'fill="{FRAME}" stroke="{GOLD}" stroke-width="0.6"/>'
            f'<line x1="0" y1="300" x2="200" y2="300" stroke="{DIM}" '
            f'stroke-width="0.5" stroke-dasharray="2 3"/>'
        )

    # 1 — The Magician: table with four tools + infinity above head
    if num == 1:
        return (
            f'<text x="{cx}" y="105" text-anchor="middle" font-size="20" '
            f'fill="{GOLD}" font-family="Georgia">∞</text>'
            f'<rect x="60" y="220" width="80" height="8" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="0.5"/>'
            f'<g font-size="14" text-anchor="middle">'
            f'<text x="75" y="216" fill="{FIRE}">🜂</text>'
            f'<text x="95" y="216" fill="{WATER}">🜄</text>'
            f'<text x="115" y="216" fill="{AIR}">🜁</text>'
            f'<text x="135" y="216" fill="{EARTH}">🜃</text>'
            f"</g>"
            f'<line x1="{cx}" y1="115" x2="{cx}" y2="170" '
            f'stroke="{GOLD}" stroke-width="1.4"/>'
            f'<polygon points="{cx},115 96,170 104,170" fill="{PURPLE}"/>'
            f'<line x1="{cx}" y1="170" x2="{cx}" y2="215" '
            f'stroke="{GOLD}" stroke-width="1.4"/>'
            f'<circle cx="{cx}" cy="180" r="5" fill="{LIGHT}"/>'
        )

    # 2 — The High Priestess: pillars + veil + crescent moon
    if num == 2:
        return (
            f'<rect x="50" y="80" width="14" height="200" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="0.6"/>'
            f'<rect x="136" y="80" width="14" height="200" fill="{LIGHT}" '
            f'stroke="{GOLD}" stroke-width="0.6"/>'
            f'<path d="M64 80 Q100 120 64 280" fill="{PURPLE}" '
            f'opacity="0.45"/>'
            f'<path d="M136 80 Q100 120 136 280" fill="{PURPLE}" '
            f'opacity="0.45"/>'
            f'<path d="M70 170 Q100 200 130 170 Q100 220 70 170 Z" '
            f'fill="{LIGHT}" opacity="0.8"/>'
            f'<text x="{cx}" y="180" text-anchor="middle" font-size="22" '
            f'fill="{GOLD}">☽</text>'
            f'<rect x="80" y="200" width="40" height="28" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="0.5"/>'
            f'<line x1="85" y1="208" x2="115" y2="208" stroke="{GOLD}" '
            f'stroke-width="0.4"/>'
            f'<line x1="85" y1="216" x2="115" y2="216" stroke="{GOLD}" '
            f'stroke-width="0.4"/>'
            f'<line x1="85" y1="224" x2="115" y2="224" stroke="{GOLD}" '
            f'stroke-width="0.4"/>'
        )

    # 3 — The Empress: crowned figure, wheat, Venus symbol
    if num == 3:
        return (
            f'<path d="M70 100 L100 88 L130 100 L130 110 L70 110 Z" '
            f'fill="url(#gold)" stroke="{GOLD}"/>'
            f'<text x="100" y="105" text-anchor="middle" font-size="9" '
            f'fill="{BG}">♀</text>'
            f'<circle cx="{cx}" cy="170" r="32" fill="{PURPLE}" '
            f'stroke="{GOLD}" stroke-width="1"/>'
            f'<circle cx="{cx}" cy="170" r="32" fill="none" '
            f'stroke="{LIGHT}" stroke-width="0.4"/>'
            f'<text x="{cx}" y="178" text-anchor="middle" font-size="26" '
            f'fill="{LIGHT}">♀</text>'
            # wheat
            f'<g stroke="{GOLD}" stroke-width="1" fill="none">'
            f'<line x1="55" y1="300" x2="55" y2="230"/>'
            f'<line x1="50" y1="240" x2="60" y2="240"/>'
            f'<line x1="50" y1="250" x2="60" y2="250"/>'
            f'<line x1="50" y1="260" x2="60" y2="260"/>'
            f'<line x1="145" y1="300" x2="145" y2="230"/>'
            f'<line x1="140" y1="240" x2="150" y2="240"/>'
            f'<line x1="140" y1="250" x2="150" y2="250"/>'
            f'<line x1="140" y1="260" x2="150" y2="260"/>'
            f"</g>"
        )

    # 4 — The Emperor: throne + ram heads
    if num == 4:
        return (
            f'<rect x="60" y="100" width="80" height="100" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="1"/>'
            f'<text x="{cx}" y="135" text-anchor="middle" font-size="22" '
            f'fill="{LIGHT}">♈</text>'
            f'<polygon points="60,100 70,90 80,100" fill="{GOLD}"/>'
            f'<polygon points="120,100 130,90 140,100" fill="{GOLD}"/>'
            f'<circle cx="{cx}" cy="180" r="14" fill="{GOLD}"/>'
            f'<line x1="{cx}" y1="180" x2="{cx}" y2="200" '
            f'stroke="{GOLD}" stroke-width="1.5"/>'
            f'<line x1="{cx - 8}" y1="240" x2="{cx - 8}" y2="280" '
            f'stroke="{GOLD}" stroke-width="1"/>'
            f'<line x1="{cx + 8}" y1="240" x2="{cx + 8}" y2="280" '
            f'stroke="{GOLD}" stroke-width="1"/>'
            f'<rect x="40" y="280" width="120" height="6" fill="{GOLD}"/>'
        )

    # 5 — The Hierophant: triple tiara + crossed keys
    if num == 5:
        return (
            f'<g fill="url(#gold)" stroke="{GOLD}" stroke-width="0.5">'
            f'<rect x="78" y="92" width="44" height="8"/>'
            f'<rect x="82" y="100" width="36" height="6"/>'
            f'<rect x="86" y="106" width="28" height="6"/>'
            f"</g>"
            f'<line x1="60" y1="160" x2="60" y2="280" stroke="{GOLD}" '
            f'stroke-width="2.5"/>'
            f'<line x1="140" y1="160" x2="140" y2="280" stroke="{GOLD}" '
            f'stroke-width="2.5"/>'
            f'<circle cx="60" cy="160" r="5" fill="{GOLD}"/>'
            f'<circle cx="140" cy="160" r="5" fill="{GOLD}"/>'
            f'<g stroke="{GOLD}" stroke-width="1.5" fill="none">'
            f'<line x1="75" y1="190" x2="125" y2="230"/>'
            f'<line x1="125" y1="190" x2="75" y2="230"/>'
            f'<circle cx="75" cy="190" r="4" fill="{GOLD}"/>'
            f'<circle cx="125" cy="190" r="4" fill="{GOLD}"/>'
            f'<circle cx="75" cy="230" r="4" fill="{GOLD}"/>'
            f'<circle cx="125" cy="230" r="4" fill="{GOLD}"/>'
            f"</g>"
            f'<rect x="60" y="260" width="80" height="30" fill="{PURPLE}" '
            f'stroke="{GOLD}" stroke-width="0.5"/>'
        )

    # 6 — The Lovers: angel above + two figures
    if num == 6:
        return (
            f'<circle cx="{cx}" cy="95" r="18" fill="{LIGHT}" opacity="0.8"/>'
            f'<text x="{cx}" y="103" text-anchor="middle" font-size="22" '
            f'fill="{GOLD}">☼</text>'
            f'<g fill="none" stroke="{GOLD}" stroke-width="0.8" opacity="0.7">'
            f'<line x1="{cx}" y1="113" x2="{cx}" y2="135"/>'
            f'<line x1="{cx - 15}" y1="125" x2="{cx + 15}" y2="125"/>'
            f"</g>"
            f'<polygon points="80,200 95,180 95,260 80,270" '
            f'fill="{PURPLE}" stroke="{GOLD}" stroke-width="0.5"/>'
            f'<polygon points="105,200 120,180 120,270 105,260" '
            f'fill="{PURPLE}" stroke="{GOLD}" stroke-width="0.5"/>'
            f'<circle cx="87" cy="178" r="6" fill="{LIGHT}"/>'
            f'<circle cx="112" cy="178" r="6" fill="{LIGHT}"/>'
            f'<text x="{cx}" y="295" text-anchor="middle" font-size="14" '
            f'fill="{GOLD}">🜍</text>'
        )

    # 7 — The Chariot: sphinxes + canopy of stars
    if num == 7:
        return (
            f'<g fill="{GOLD}">'
            f'<circle cx="60" cy="100" r="2"/><circle cx="100" cy="92" r="2"/>'
            f'<circle cx="140" cy="100" r="2"/><circle cx="80" cy="118" r="2"/>'
            f'<circle cx="120" cy="118" r="2"/><circle cx="{cx}" cy="88" r="2"/>'
            f"</g>"
            f'<rect x="60" y="160" width="80" height="80" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="1"/>'
            f'<polygon points="55,160 100,135 145,160" fill="{PURPLE}" '
            f'stroke="{GOLD}" stroke-width="0.5"/>'
            f'<polygon points="80,240 90,225 90,290 80,290" fill="{LIGHT}"/>'
            f'<polygon points="120,240 110,225 110,290 120,290" fill="{LIGHT}"/>'
            f'<text x="{cx}" y="155" text-anchor="middle" font-size="16" '
            f'fill="{GOLD}">★</text>'
            f'<circle cx="55" cy="280" r="10" fill="{GOLD}"/>'
            f'<circle cx="145" cy="280" r="10" fill="{DIM}"/>'
        )

    # 8 — Strength: woman + lion + lemniscate
    if num == 8:
        return (
            f'<text x="{cx}" y="100" text-anchor="middle" font-size="22" '
            f'fill="{GOLD}">∞</text>'
            f'<ellipse cx="100" cy="200" rx="45" ry="30" fill="{EARTH}" '
            f'stroke="{GOLD}" stroke-width="0.8"/>'
            f'<circle cx="75" cy="195" r="14" fill="{EARTH}" stroke="{GOLD}" '
            f'stroke-width="0.6"/>'
            f'<circle cx="72" cy="192" r="2" fill="{GOLD}"/>'
            f'<circle cx="78" cy="192" r="2" fill="{GOLD}"/>'
            f'<polygon points="100,180 108,150 116,180" fill="{PURPLE}" '
            f'stroke="{GOLD}" stroke-width="0.5"/>'
            f'<circle cx="108" cy="143" r="6" fill="{LIGHT}"/>'
            f'<line x1="115" y1="180" x2="130" y2="190" stroke="{LIGHT}" '
            f'stroke-width="1.2"/>'
        )

    # 9 — The Hermit: hooded figure with lantern
    if num == 9:
        return (
            f'<polygon points="100,80 130,140 130,290 70,290 70,140" '
            f'fill="{PURPLE}" stroke="{GOLD}" stroke-width="1"/>'
            f'<ellipse cx="100" cy="138" rx="14" ry="18" fill="{FRAME}"/>'
            f'<circle cx="100" cy="140" r="6" fill="{LIGHT}"/>'
            f'<line x1="100" y1="156" x2="100" y2="170" stroke="{GOLD}" '
            f'stroke-width="1.5"/>'
            f'<polygon points="92,170 108,170 105,200 95,200" fill="{GOLD}" '
            f'stroke="{BG}" stroke-width="0.5"/>'
            f'<polygon points="100,180 96,190 104,190" fill="{FIRE}"/>'
            f'<text x="100" y="200" text-anchor="middle" font-size="6" '
            f'fill="{GOLD}">✶</text>'
            f'<line x1="130" y1="180" x2="160" y2="260" stroke="{GOLD}" '
            f'stroke-width="1.5"/>'
        )

    # 10 — Wheel of Fortune
    if num == 10:
        return (
            f'<circle cx="{cx}" cy="180" r="55" fill="none" stroke="{GOLD}" '
            f'stroke-width="2"/>'
            f'<circle cx="{cx}" cy="180" r="40" fill="none" stroke="{GOLD}" '
            f'stroke-width="0.8"/>'
            f'<circle cx="{cx}" cy="180" r="10" fill="{GOLD}"/>'
            f'<g stroke="{GOLD}" stroke-width="1.2">'
            f'<line x1="{cx}" y1="125" x2="{cx}" y2="235"/>'
            f'<line x1="{cx - 55}" y1="180" x2="{cx + 55}" y2="180"/>'
            f'<line x1="{cx - 39}" y1="141" x2="{cx + 39}" y2="219"/>'
            f'<line x1="{cx + 39}" y1="141" x2="{cx - 39}" y2="219"/>'
            f"</g>"
            f'<text x="{cx}" y="113" text-anchor="middle" font-size="12" '
            f'fill="{GOLD}">TAROT</text>'
            f'<text x="{cx}" y="252" text-anchor="middle" font-size="8" '
            f'fill="{GOLD}">ROTA</text>'
        )

    # 11 — Justice: scales + sword
    if num == 11:
        return (
            f'<line x1="{cx}" y1="100" x2="{cx}" y2="260" stroke="{GOLD}" '
            f'stroke-width="1.5"/>'
            f'<line x1="60" y1="140" x2="140" y2="140" stroke="{GOLD}" '
            f'stroke-width="1.5"/>'
            f'<line x1="55" y1="140" x2="55" y2="180" stroke="{GOLD}" '
            f'stroke-width="0.8"/>'
            f'<line x1="145" y1="140" x2="145" y2="180" stroke="{GOLD}" '
            f'stroke-width="0.8"/>'
            f'<path d="M30 180 Q55 200 80 180 Z" fill="none" stroke="{GOLD}" '
            f'stroke-width="1.2"/>'
            f'<path d="M120 180 Q145 200 170 180 Z" fill="none" '
            f'stroke="{GOLD}" stroke-width="1.2"/>'
            f'<line x1="{cx}" y1="100" x2="{cx}" y2="92" stroke="{LIGHT}" '
            f'stroke-width="2"/>'
            f'<line x1="{cx - 4}" y1="100" x2="{cx + 4}" y2="100" '
            f'stroke="{LIGHT}" stroke-width="2"/>'
            f'<polygon points="{cx - 3},260 {cx + 3},260 {cx},270" fill="{GOLD}"/>'
        )

    # 12 — The Hanged Man: figure hanging upside-down
    if num == 12:
        return (
            f'<line x1="40" y1="100" x2="160" y2="100" stroke="{GOLD}" '
            f'stroke-width="2"/>'
            f'<line x1="100" y1="100" x2="100" y2="120" stroke="{GOLD}" '
            f'stroke-width="1.2"/>'
            f'<ellipse cx="100" cy="135" rx="6" ry="8" fill="{LIGHT}"/>'
            f'<line x1="100" y1="143" x2="100" y2="220" stroke="{PURPLE}" '
            f'stroke-width="6"/>'
            f'<line x1="100" y1="160" x2="75" y2="180" stroke="{PURPLE}" '
            f'stroke-width="4"/>'
            f'<line x1="100" y1="160" x2="125" y2="180" stroke="{PURPLE}" '
            f'stroke-width="4"/>'
            f'<line x1="100" y1="220" x2="85" y2="260" stroke="{PURPLE}" '
            f'stroke-width="4"/>'
            f'<line x1="100" y1="220" x2="115" y2="260" stroke="{PURPLE}" '
            f'stroke-width="4"/>'
            f'<circle cx="100" cy="135" r="12" fill="none" stroke="{GOLD}" '
            f'stroke-width="0.6" opacity="0.7"/>'
        )

    # 13 — Death: skeleton on pale horse
    if num == 13:
        return (
            f'<rect x="40" y="230" width="120" height="6" fill="{LIGHT}"/>'
            f'<line x1="50" y1="236" x2="45" y2="270" stroke="{LIGHT}" '
            f'stroke-width="2"/>'
            f'<line x1="70" y1="236" x2="65" y2="270" stroke="{LIGHT}" '
            f'stroke-width="2"/>'
            f'<line x1="130" y1="236" x2="125" y2="270" stroke="{LIGHT}" '
            f'stroke-width="2"/>'
            f'<line x1="150" y1="236" x2="145" y2="270" stroke="{LIGHT}" '
            f'stroke-width="2"/>'
            f'<rect x="80" y="200" width="40" height="35" fill="{FRAME}" '
            f'stroke="{GOLD}"/>'
            f'<line x1="100" y1="170" x2="100" y2="200" stroke="{GOLD}" '
            f'stroke-width="1.4"/>'
            f'<line x1="100" y1="170" x2="150" y2="155" stroke="{FIRE}" '
            f'stroke-width="2"/>'
            f'<polygon points="150,155 165,150 160,165" fill="{LIGHT}" '
            f'stroke="{FIRE}"/>'
            f'<text x="60" y="185" font-size="18" fill="{LIGHT}">☠</text>'
        )

    # 14 — Temperance: angel pouring between two cups
    if num == 14:
        return (
            f'<circle cx="{cx}" cy="110" r="16" fill="{LIGHT}" opacity="0.8"/>'
            f'<text x="{cx}" y="118" text-anchor="middle" font-size="18" '
            f'fill="{GOLD}">☼</text>'
            f'<path d="M75 130 Q100 145 125 130 L120 220 L80 220 Z" '
            f'fill="{LIGHT}" stroke="{GOLD}" stroke-width="0.6"/>'
            f'<path d="M85 160 L100 140 L115 160 L100 175 Z" fill="{GOLD}"/>'
            f'<line x1="100" y1="175" x2="75" y2="220" stroke="{WATER}" '
            f'stroke-width="2"/>'
            f'<path d="M65 220 Q75 230 85 220 L80 240 L70 240 Z" '
            f'fill="{WATER}" stroke="{GOLD}" stroke-width="0.5"/>'
            f'<path d="M115 220 Q125 230 135 220 L130 240 L120 240 Z" '
            f'fill="{WATER}" stroke="{GOLD}" stroke-width="0.5"/>'
            f'<path d="M40 280 Q100 270 160 280" stroke="{WATER}" '
            f'stroke-width="1" fill="none" opacity="0.6"/>'
        )

    # 15 — The Devil: horned figure + inverted pentacle
    if num == 15:
        return (
            f'<rect x="70" y="230" width="60" height="40" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="1"/>'
            f'<polygon points="100,90 80,120 120,120" fill="{RED}" '
            f'stroke="{GOLD}" stroke-width="1"/>'
            f'<polygon points="85,95 90,80 95,95" fill="{RED}"/>'
            f'<polygon points="105,95 110,80 115,95" fill="{RED}"/>'
            f'<polygon points="80,120 100,150 120,120" fill="{RED}"/>'
            f'<polygon points="75,160 100,140 125,160 100,200 90,200" '
            f'fill="{PURPLE}" stroke="{GOLD}" stroke-width="0.6"/>'
            f'<polygon points="100,150 100,200 80,200 120,200" '
            f'fill="none" stroke="{GOLD}" stroke-width="0.5"/>'
            f'<circle cx="100" cy="180" r="2" fill="{GOLD}"/>'
            f'<line x1="100" y1="200" x2="80" y2="290" stroke="{GOLD}" '
            f'stroke-width="1.2"/>'
            f'<line x1="100" y1="200" x2="120" y2="290" stroke="{GOLD}" '
            f'stroke-width="1.2"/>'
        )

    # 16 — The Tower: tower struck by lightning
    if num == 16:
        return (
            f'<rect x="80" y="120" width="40" height="160" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="1"/>'
            f'<polygon points="75,120 100,90 125,120" fill="{GOLD}" '
            f'stroke="{BG}"/>'
            f'<rect x="86" y="140" width="10" height="14" fill="{BG}"/>'
            f'<rect x="104" y="140" width="10" height="14" fill="{BG}"/>'
            f'<rect x="86" y="170" width="10" height="14" fill="{BG}"/>'
            f'<rect x="104" y="170" width="10" height="14" fill="{BG}"/>'
            f'<rect x="86" y="200" width="10" height="14" fill="{BG}"/>'
            f'<rect x="104" y="200" width="10" height="14" fill="{BG}"/>'
            f'<polygon points="100,80 92,120 108,120" fill="{FIRE}"/>'
            f'<polygon points="100,60 100,100 92,100 100,115 108,100 100,100" '
            f'fill="{FIRE}"/>'
            f'<polygon points="70,280 90,250 80,290" fill="{GOLD}"/>'
            f'<polygon points="130,280 110,250 120,290" fill="{GOLD}"/>'
        )

    # 17 — The Star: 8-point star + maiden pouring water
    if num == 17:
        return (
            f'<g fill="{GOLD}" stroke="{GOLD}" stroke-width="0.6">'
            f'<polygon points="100,80 105,100 125,100 109,113 116,135 '
            f'100,122 84,135 91,113 75,100 95,100"/>'
            f'<line x1="100" y1="80" x2="100" y2="60" stroke-width="0.8"/>'
            f'<line x1="100" y1="80" x2="120" y2="65" stroke-width="0.6"/>'
            f'<line x1="100" y1="80" x2="135" y2="80" stroke-width="0.6"/>'
            f'<line x1="100" y1="80" x2="120" y2="95" stroke-width="0.6"/>'
            f'<line x1="100" y1="80" x2="100" y2="100" stroke-width="0.6"/>'
            f'<line x1="100" y1="80" x2="80" y2="95" stroke-width="0.6"/>'
            f'<line x1="100" y1="80" x2="65" y2="80" stroke-width="0.6"/>'
            f'<line x1="100" y1="80" x2="80" y2="65" stroke-width="0.6"/>'
            f"</g>"
            f'<circle cx="100" cy="200" r="18" fill="{LIGHT}" '
            f'stroke="{GOLD}" stroke-width="0.6"/>'
            f'<line x1="100" y1="218" x2="90" y2="250" stroke="{LIGHT}" '
            f'stroke-width="1.5"/>'
            f'<path d="M80 250 L100 240 L120 250" fill="none" '
            f'stroke="{WATER}" stroke-width="1.5"/>'
            f'<path d="M70 280 Q100 290 130 280" stroke="{WATER}" '
            f'stroke-width="1" fill="none"/>'
        )

    # 18 — The Moon: crescent + towers + path
    if num == 18:
        return (
            f'<circle cx="{cx}" cy="130" r="34" fill="{LIGHT}"/>'
            f'<circle cx="112" cy="125" r="30" fill="{BG}"/>'
            f'<circle cx="{cx}" cy="118" r="2" fill="{GOLD}"/>'
            f'<circle cx="90" cy="130" r="2" fill="{GOLD}"/>'
            f'<rect x="40" y="180" width="20" height="60" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="0.6"/>'
            f'<polygon points="35,180 50,165 65,180" fill="{GOLD}"/>'
            f'<rect x="140" y="180" width="20" height="60" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="0.6"/>'
            f'<polygon points="135,180 150,165 165,180" fill="{GOLD}"/>'
            f'<path d="M100 200 Q90 220 100 240 Q110 260 100 280" '
            f'stroke="{WATER}" stroke-width="1.5" fill="none"/>'
            f'<path d="M50 280 Q100 270 150 280" stroke="{WATER}" '
            f'stroke-width="0.8" fill="none" opacity="0.7"/>'
        )

    # 19 — The Sun: radiant sun + sunflower
    if num == 19:
        return (
            f'<circle cx="{cx}" cy="130" r="26" fill="{GOLD}"/>'
            f'<g stroke="{GOLD}" stroke-width="1.5">'
            f'<line x1="{cx}" y1="80" x2="{cx}" y2="95"/>'
            f'<line x1="{cx}" y1="165" x2="{cx}" y2="180"/>'
            f'<line x1="{cx - 50}" y1="130" x2="{cx - 35}" y2="130"/>'
            f'<line x1="{cx + 50}" y1="130" x2="{cx + 35}" y2="130"/>'
            f'<line x1="{cx - 37}" y1="93" x2="{cx - 26}" y2="104"/>'
            f'<line x1="{cx + 37}" y1="93" x2="{cx + 26}" y2="104"/>'
            f'<line x1="{cx - 37}" y1="167" x2="{cx - 26}" y2="156"/>'
            f'<line x1="{cx + 37}" y1="167" x2="{cx + 26}" y2="156"/>'
            f"</g>"
            f'<circle cx="{cx}" cy="130" r="8" fill="{BG}"/>'
            f'<rect x="40" y="240" width="120" height="40" fill="{GOLD}" '
            f'opacity="0.8"/>'
            f'<line x1="40" y1="240" x2="40" y2="280" stroke="{BG}" '
            f'stroke-width="1"/>'
            f'<line x1="70" y1="240" x2="70" y2="280" stroke="{BG}" '
            f'stroke-width="1"/>'
            f'<line x1="100" y1="240" x2="100" y2="280" stroke="{BG}" '
            f'stroke-width="1"/>'
            f'<line x1="130" y1="240" x2="130" y2="280" stroke="{BG}" '
            f'stroke-width="1"/>'
            f'<line x1="160" y1="240" x2="160" y2="280" stroke="{BG}" '
            f'stroke-width="1"/>'
        )

    # 20 — Judgement: trumpet + rising figures
    if num == 20:
        return (
            f'<text x="{cx}" y="80" text-anchor="middle" font-size="22" '
            f'fill="{GOLD}">☼</text>'
            f'<rect x="60" y="85" width="80" height="4" fill="{GOLD}"/>'
            f'<polygon points="140,87 165,82 158,95" fill="{GOLD}"/>'
            f'<rect x="50" y="90" width="10" height="30" fill="url(#gold)"/>'
            f'<polygon points="40,120 60,115 60,125" fill="{FIRE}"/>'
            f'<line x1="60" y1="125" x2="60" y2="160" stroke="{GOLD}" '
            f'stroke-width="1.2"/>'
            f'<rect x="60" y="160" width="80" height="3" fill="{FRAME}"/>'
            f'<g fill="{LIGHT}" stroke="{GOLD}" stroke-width="0.4">'
            f'<ellipse cx="80" cy="230" rx="10" ry="20"/>'
            f'<ellipse cx="100" cy="245" rx="10" ry="25"/>'
            f'<ellipse cx="120" cy="230" rx="10" ry="20"/>'
            f"</g>"
            f'<circle cx="80" cy="210" r="5" fill="{LIGHT}" '
            f'stroke="{GOLD}" stroke-width="0.4"/>'
            f'<circle cx="100" cy="220" r="5" fill="{LIGHT}" '
            f'stroke="{GOLD}" stroke-width="0.4"/>'
            f'<circle cx="120" cy="210" r="5" fill="{LIGHT}" '
            f'stroke="{GOLD}" stroke-width="0.4"/>'
        )

    # 21 — The World: dancer in wreath
    if num == 21:
        return (
            f'<ellipse cx="{cx}" cy="190" rx="70" ry="90" fill="none" '
            f'stroke="{GOLD}" stroke-width="1.5"/>'
            f'<ellipse cx="{cx}" cy="190" rx="60" ry="80" fill="none" '
            f'stroke="{GOLD}" stroke-width="0.5" opacity="0.6"/>'
            f'<g fill="{GOLD}">'
            f'<circle cx="50" cy="120" r="6"/>'
            f'<circle cx="150" cy="120" r="6"/>'
            f'<circle cx="50" cy="260" r="6"/>'
            f'<circle cx="150" cy="260" r="6"/>'
            f"</g>"
            f'<text x="50" y="124" text-anchor="middle" font-size="8" '
            f'fill="{BG}">♌</text>'
            f'<text x="150" y="124" text-anchor="middle" font-size="8" '
            f'fill="{BG}">♉</text>'
            f'<text x="50" y="264" text-anchor="middle" font-size="8" '
            f'fill="{BG}">♐</text>'
            f'<text x="150" y="264" text-anchor="middle" font-size="8" '
            f'fill="{BG}">♎</text>'
            f'<circle cx="{cx}" cy="170" r="6" fill="{LIGHT}"/>'
            f'<line x1="{cx}" y1="176" x2="{cx - 12}" y2="210" stroke="{LIGHT}" '
            f'stroke-width="1.5"/>'
            f'<line x1="{cx}" y1="176" x2="{cx + 12}" y2="210" stroke="{LIGHT}" '
            f'stroke-width="1.5"/>'
            f'<line x1="{cx - 4}" y1="210" x2="{cx - 8}" y2="245" '
            f'stroke="{LIGHT}" stroke-width="1.5"/>'
            f'<line x1="{cx + 4}" y1="210" x2="{cx + 8}" y2="245" '
            f'stroke="{LIGHT}" stroke-width="1.5"/>'
        )

    raise ValueError(f"No major-arcana visual defined for index {num}")


# ---------------------------------------------------------------------------
# Minor Arcana helpers — symbolic motifs for each suit
# ---------------------------------------------------------------------------
# Each suit has a glyph (Wand = staff, Cup = chalice, Sword = blade,
# Pentacle = coin) and a signature colour. The minor-arcana cards are
# composed by a shared renderer that combines the count/rank with the
# suit motif and a small scene.

SUIT_GLYPH = {
    "Wands": "🜂",
    "Cups": "🜄",
    "Swords": "🜁",
    "Pentacles": "🜃",
}
SUIT_COLOR = {
    "Wands": FIRE,
    "Cups": WATER,
    "Swords": AIR,
    "Pentacles": EARTH,
}
SUIT_LABEL = {
    "Wands": "WANDS · FIRE",
    "Cups": "CUPS · WATER",
    "Swords": "SWORDS · AIR",
    "Pentacles": "PENTACLES · EARTH",
}


def _wand(x: float, y: float, h: float = 60) -> str:
    """Single vertical wand with leafy tip."""
    return (
        f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + h}" '
        f'stroke="{GOLD}" stroke-width="2.5"/>'
        f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + h}" '
        f'stroke="{FIRE}" stroke-width="0.8" opacity="0.6"/>'
        f'<path d="M{x - 6} {y + 4} L{x} {y - 2} L{x + 6} {y + 4}" fill="{GOLD}"/>'
        f'<path d="M{x - 4} {y - 2} L{x} {y - 8} L{x + 4} {y - 2}" fill="{FIRE}"/>'
    )


def _cup(x: float, y: float, w: float = 28) -> str:
    """Single chalice."""
    return (
        f'<path d="M{x - w / 2} {y} L{x - w / 2} {y + 18} '
        f'Q{x} {y + 30} {x + w / 2} {y + 18} L{x + w / 2} {y} Z" '
        f'fill="url(#purple)" stroke="{GOLD}" stroke-width="1"/>'
        f'<ellipse cx="{x}" cy="{y}" rx="{w / 2}" ry="3" fill="{WATER}" '
        f'stroke="{GOLD}" stroke-width="0.6"/>'
        f'<line x1="{x}" y1="{y + 25}" x2="{x}" y2="{y + 34}" '
        f'stroke="{GOLD}" stroke-width="1.5"/>'
        f'<rect x="{x - 10}" y="{y + 34}" width="20" height="3" fill="{GOLD}"/>'
    )


def _sword(x: float, y: float, h: float = 60) -> str:
    """Single upright sword."""
    return (
        f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + h}" '
        f'stroke="{LIGHT}" stroke-width="2"/>'
        f'<polygon points="{x - 2},{y} {x + 2},{y} {x},{y - 8}" fill="{LIGHT}"/>'
        f'<line x1="{x - 10}" y1="{y + h}" x2="{x + 10}" y2="{y + h}" '
        f'stroke="{GOLD}" stroke-width="1.5"/>'
        f'<line x1="{x}" y1="{y + h}" x2="{x}" y2="{y + h + 10}" '
        f'stroke="{GOLD}" stroke-width="1.5"/>'
        f'<circle cx="{x}" cy="{y + h + 12}" r="2.5" fill="{GOLD}"/>'
    )


def _pentacle(cx: float, cy: float, r: float = 14) -> str:
    """Pentacle (5-pointed star inside a circle)."""
    pts: list[str] = []
    import math

    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return (
        f'<polygon points="{" ".join(pts)}" fill="url(#gold)" '
        f'stroke="{GOLD}" stroke-width="0.6"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
        f'stroke="{GOLD}" stroke-width="1"/>'
    )


RENDERERS: dict[str, Callable[[float, float, float], str]] = {
    "Wands": lambda x, y, h: _wand(x, y, h),
    "Cups": lambda x, y, h: _cup(x, y, h * 0.6),
    "Swords": lambda x, y, h: _sword(x, y, h),
    "Pentacles": lambda x, y, h: _pentacle(x, y + h / 2, h / 2.4),
}


def _layout_suit(suit: str, count: int) -> str:
    """Lay out 1..14 glyphs (Ace..10 + 4 court) for a given suit.

    Ace = single centred glyph, pip cards = row/grid layout,
    court cards = seated figure with glyph above.
    """
    color = SUIT_COLOR[suit]
    render = RENDERERS[suit]

    # ---- Ace: single dominant glyph with hand-from-cloud ----
    if count == 1:
        return (
            f'<ellipse cx="{W / 2}" cy="105" rx="40" ry="14" fill="{FRAME}" '
            f'stroke="{GOLD}" stroke-width="0.6" opacity="0.7"/>'
            f'<text x="{W / 2}" y="110" text-anchor="middle" font-size="14" '
            f'fill="{GOLD}">✋</text>'
            f"{render(W / 2, 150, 80)}"
            f'<g stroke="{color}" stroke-width="0.6" opacity="0.7">'
            f'<line x1="60" y1="240" x2="140" y2="240"/>'
            f'<line x1="50" y1="255" x2="150" y2="255"/>'
            f'<line x1="65" y1="270" x2="135" y2="270"/>'
            f"</g>"
        )

    # ---- Court cards ----
    if count >= 11:
        return _court(suit, count)

    # ---- Pip cards 2..10 ----
    return _pips(suit, count)


def _pips(suit: str, n: int) -> str:
    """Lay out n suit glyphs in the canonical Waite-Smith arrangement.

    Falls back to a tidy centred grid when no arrangement is specified.
    """
    SUIT_COLOR[suit]

    # Special canonical arrangements for Wands 2..10
    if suit == "Wands":
        if n == 2:
            return f"{_wand(70, 160, 70)}{_wand(130, 160, 70)}"
        if n == 3:
            return f"{_wand(60, 130, 70)}{_wand(100, 170, 70)}{_wand(140, 130, 70)}"
        if n == 4:
            return f"{_wand(55, 130, 70)}{_wand(145, 130, 70)}{_wand(55, 220, 70)}{_wand(145, 220, 70)}"
        if n == 5:
            return (
                f"{_wand(45, 120, 60)}{_wand(155, 120, 60)}"
                f"{_wand(70, 220, 60)}{_wand(130, 220, 60)}"
                f"{_wand(100, 175, 60)}"
            )
        if n == 6:
            return (
                f"{_wand(40, 115, 50)}{_wand(160, 115, 50)}"
                f"{_wand(40, 180, 50)}{_wand(160, 180, 50)}"
                f"{_wand(40, 245, 50)}{_wand(160, 245, 50)}"
            )
        if n == 7:
            return (
                f"{_wand(40, 110, 45)}{_wand(160, 110, 45)}"
                f"{_wand(40, 170, 45)}{_wand(160, 170, 45)}"
                f"{_wand(40, 230, 45)}{_wand(160, 230, 45)}"
                f"{_wand(100, 170, 45)}"
            )
        if n == 8:
            return (
                f"{_wand(35, 100, 40)}{_wand(165, 100, 40)}"
                f"{_wand(35, 150, 40)}{_wand(165, 150, 40)}"
                f"{_wand(35, 200, 40)}{_wand(165, 200, 40)}"
                f"{_wand(35, 250, 40)}{_wand(165, 250, 40)}"
            )
        if n == 9:
            return (
                f"{_wand(35, 100, 35)}{_wand(100, 100, 35)}{_wand(165, 100, 35)}"
                f"{_wand(35, 150, 35)}{_wand(165, 150, 35)}"
                f"{_wand(35, 200, 35)}{_wand(165, 200, 35)}"
                f"{_wand(35, 250, 35)}{_wand(100, 250, 35)}{_wand(165, 250, 35)}"
            )
        if n == 10:
            return (
                f"{_wand(35, 95, 30)}{_wand(100, 95, 30)}{_wand(165, 95, 30)}"
                f"{_wand(35, 135, 30)}{_wand(165, 135, 30)}"
                f"{_wand(35, 175, 30)}{_wand(165, 175, 30)}"
                f"{_wand(35, 215, 30)}{_wand(100, 215, 30)}{_wand(165, 215, 30)}"
                f"{_wand(100, 255, 30)}"
            )

    # Swords
    if suit == "Swords":
        if n == 2:
            return f"{_sword(80, 130, 80)}{_sword(120, 130, 80)}"
        if n == 3:
            return (
                f"{_sword(60, 120, 70)}{_sword(100, 140, 70)}"
                f"{_sword(140, 120, 70)}"
                f'<path d="M70 200 Q100 220 130 200 Q100 240 70 200" '
                f'fill="{RED}" stroke="{GOLD}" stroke-width="0.5"/>'
            )
        if n == 4:
            return (
                f"{_sword(50, 100, 60)}{_sword(150, 100, 60)}"
                f"{_sword(50, 180, 60)}{_sword(150, 180, 60)}"
                f'<rect x="40" y="260" width="120" height="30" fill="{FRAME}" '
                f'stroke="{GOLD}" stroke-width="0.6"/>'
                f'<ellipse cx="100" cy="275" rx="14" ry="6" fill="{PURPLE}"/>'
            )
        if n == 5:
            return (
                f"{_sword(50, 110, 50)}{_sword(150, 110, 50)}"
                f"{_sword(70, 180, 50)}{_sword(130, 180, 50)}"
                f"{_sword(100, 250, 50)}"
                f'<path d="M30 220 Q60 240 80 220" stroke="{WATER}" '
                f'stroke-width="1" fill="none" opacity="0.6"/>'
            )
        if n == 6:
            return (
                f"{_sword(45, 100, 50)}{_sword(155, 100, 50)}"
                f"{_sword(45, 160, 50)}{_sword(155, 160, 50)}"
                f"{_sword(45, 220, 50)}{_sword(155, 220, 50)}"
                f'<path d="M20 280 Q100 260 180 280" stroke="{WATER}" '
                f'stroke-width="1" fill="none"/>'
            )
        if n == 7:
            return (
                f"{_sword(40, 95, 45)}{_sword(160, 95, 45)}"
                f"{_sword(40, 155, 45)}{_sword(160, 155, 45)}"
                f"{_sword(40, 215, 45)}{_sword(160, 215, 45)}"
                f"{_sword(100, 175, 45)}"
            )
        if n == 8:
            return (
                f"{_sword(40, 90, 40)}{_sword(160, 90, 40)}"
                f"{_sword(40, 140, 40)}{_sword(160, 140, 40)}"
                f"{_sword(40, 190, 40)}{_sword(160, 190, 40)}"
                f"{_sword(40, 240, 40)}{_sword(160, 240, 40)}"
                f'<ellipse cx="100" cy="170" rx="18" ry="10" fill="{PURPLE}" '
                f'stroke="{GOLD}" stroke-width="0.4"/>'
            )
        if n == 9:
            return (
                f"{_sword(35, 90, 35)}{_sword(100, 90, 35)}{_sword(165, 90, 35)}"
                f"{_sword(35, 135, 35)}{_sword(165, 135, 35)}"
                f"{_sword(35, 180, 35)}{_sword(165, 180, 35)}"
                f"{_sword(35, 225, 35)}{_sword(100, 225, 35)}{_sword(165, 225, 35)}"
                f'<rect x="40" y="270" width="120" height="22" fill="{FRAME}" '
                f'stroke="{GOLD}" stroke-width="0.4"/>'
            )
        if n == 10:
            return (
                f"{_sword(35, 85, 28)}{_sword(100, 85, 28)}{_sword(165, 85, 28)}"
                f"{_sword(35, 120, 28)}{_sword(165, 120, 28)}"
                f"{_sword(35, 155, 28)}{_sword(165, 155, 28)}"
                f"{_sword(35, 190, 28)}{_sword(100, 190, 28)}{_sword(165, 190, 28)}"
                f"{_sword(100, 225, 28)}"
                f'<path d="M20 270 Q100 250 180 270" stroke="{GOLD}" '
                f'stroke-width="0.6" fill="none" opacity="0.7"/>'
            )

    # Cups
    if suit == "Cups":
        if n == 2:
            return (
                f"{_cup(75, 160)}{_cup(125, 160)}"
                f'<path d="M70 110 Q100 100 130 110" stroke="{GOLD}" '
                f'stroke-width="0.8" fill="none"/>'
                f'<text x="{W / 2}" y="105" text-anchor="middle" font-size="14" '
                f'fill="{GOLD}">♌</text>'
            )
        if n == 3:
            return (
                f"{_cup(60, 130)}{_cup(100, 170)}{_cup(140, 130)}"
                f'<path d="M30 240 Q100 260 170 240" stroke="{EARTH}" '
                f'stroke-width="0.8" fill="none"/>'
            )
        if n == 4:
            return (
                f"{_cup(50, 130)}{_cup(150, 130)}"
                f"{_cup(50, 220)}{_cup(150, 220)}"
                f'<polygon points="80,170 100,150 120,170 100,190" '
                f'fill="{GOLD}" stroke="{FRAME}" stroke-width="0.4"/>'
                f'<ellipse cx="100" cy="270" rx="35" ry="6" fill="{EARTH}" '
                f'stroke="{GOLD}" stroke-width="0.4"/>'
            )
        if n == 5:
            return (
                f"{_cup(40, 200, 22)}{_cup(80, 200, 22)}{_cup(120, 200, 22)}"
                f'<line x1="50" y1="240" x2="60" y2="270" stroke="{WATER}" '
                f'stroke-width="0.8"/>'
                f'<line x1="80" y1="240" x2="80" y2="270" stroke="{WATER}" '
                f'stroke-width="0.8"/>'
                f'<line x1="110" y1="240" x2="100" y2="270" stroke="{WATER}" '
                f'stroke-width="0.8"/>'
                f"{_cup(150, 130, 22)}{_cup(150, 280, 22)}"
                f'<polygon points="100,90 105,100 100,110 95,100" fill="{FRAME}"/>'
            )
        if n == 6:
            return (
                f"{_cup(40, 130)}{_cup(80, 130)}{_cup(120, 130)}{_cup(160, 130)}"
                f"{_cup(60, 220)}{_cup(140, 220)}"
                f'<g fill="{GOLD}">'
                f'<circle cx="100" cy="180" r="6"/>'
                f"</g>"
            )
        if n == 7:
            return (
                f"{_cup(35, 110)}{_cup(80, 100)}{_cup(125, 110)}{_cup(170, 100)}"
                f"{_cup(50, 180)}{_cup(105, 175)}{_cup(160, 180)}"
                f'<ellipse cx="100" cy="240" rx="60" ry="8" fill="{PURPLE}" '
                f'opacity="0.4" stroke="{GOLD}" stroke-width="0.3"/>'
            )
        if n == 8:
            return (
                f"{_cup(50, 110)}{_cup(95, 110)}{_cup(140, 110)}{_cup(155, 145)}"
                f"{_cup(45, 145)}{_cup(105, 145)}{_cup(150, 145)}{_cup(50, 180)}"
                f'<line x1="100" y1="220" x2="100" y2="270" stroke="{GOLD}" '
                f'stroke-width="1.2"/>'
                f'<polygon points="95,210 105,210 100,200" fill="{PURPLE}"/>'
            )
        if n == 9:
            return (
                f"{_cup(35, 100)}{_cup(70, 100)}{_cup(105, 100)}{_cup(135, 100)}"
                f"{_cup(165, 100)}{_cup(50, 160)}{_cup(85, 160)}{_cup(120, 160)}"
                f"{_cup(150, 160)}"
                f'<rect x="20" y="220" width="160" height="50" rx="6" '
                f'fill="none" stroke="{GOLD}" stroke-width="0.6"/>'
                f'<path d="M20 245 Q100 240 180 245" stroke="{GOLD}" '
                f'stroke-width="0.4" fill="none"/>'
            )
        if n == 10:
            return (
                f"{_cup(40, 90)}{_cup(75, 90)}{_cup(110, 90)}{_cup(145, 90)}"
                f"{_cup(175, 90)}{_cup(55, 145)}{_cup(90, 145)}{_cup(125, 145)}"
                f"{_cup(160, 145)}{_cup(100, 200)}"
                f'<path d="M10 250 Q100 230 190 250" stroke="{GOLD}" '
                f'stroke-width="0.8" fill="none"/>'
                f'<path d="M10 258 Q100 240 190 258" stroke="{GOLD}" '
                f'stroke-width="0.5" fill="none" opacity="0.6"/>'
            )

    # Pentacles
    if suit == "Pentacles":
        cols = 2 if n <= 4 else 3
        out: list[str] = []
        for i in range(n):
            col = i % cols
            row = i // cols
            x = 40 + col * 60 + (60 if cols == 3 and row == 1 else 0)
            y = 90 + row * 70
            out.append(_pentacle(x, y, 16))
        return "".join(out)

    # Fallback: straight column
    return "".join(_pentacle(W / 2, 80 + i * 22, 12) for i in range(n))


def _court(suit: str, count: int) -> str:
    """Render a court card (Page=11, Knight=12, Queen=13, King=14)."""
    color = SUIT_COLOR[suit]
    rank = {11: "PAGE", 12: "KNIGHT", 13: "QUEEN", 14: "KING"}[count]
    # Seated figure on a throne with the suit glyph above the head.
    return (
        f"{RENDERERS[suit](W / 2, 90, 40)}"
        f'<rect x="60" y="150" width="80" height="100" fill="{FRAME}" '
        f'stroke="{GOLD}" stroke-width="1"/>'
        f'<polygon points="55,150 100,135 145,150" fill="{PURPLE}" '
        f'stroke="{GOLD}" stroke-width="0.5"/>'
        f'<rect x="65" y="160" width="70" height="20" fill="{PURPLE}" '
        f'opacity="0.7" stroke="{GOLD}" stroke-width="0.3"/>'
        f'<circle cx="{W / 2}" cy="200" r="14" fill="{LIGHT}" '
        f'stroke="{GOLD}" stroke-width="0.8"/>'
        f'<text x="{W / 2}" y="205" text-anchor="middle" font-size="14" '
        f'fill="{GOLD}">{SUIT_GLYPH[suit]}</text>'
        f'<line x1="{W / 2 - 22}" y1="180" x2="{W / 2 + 22}" y2="180" '
        f'stroke="{GOLD}" stroke-width="1.5"/>'
        f'<line x1="{W / 2 - 30}" y1="200" x2="{W / 2 + 30}" y2="200" '
        f'stroke="{GOLD}" stroke-width="1.2"/>'
        f'<line x1="{W / 2 - 22}" y1="220" x2="{W / 2 + 22}" y2="220" '
        f'stroke="{GOLD}" stroke-width="1.5"/>'
        f'<text x="{W / 2}" y="280" text-anchor="middle" font-size="9" '
        f'fill="{color}">{rank}</text>'
    )


# ---------------------------------------------------------------------------
# Per-card dispatch
# ---------------------------------------------------------------------------
def render_card(card: dict) -> str:
    name = card["name"]
    arcana = card["arcana"]

    if arcana == "major":
        num = int(card["number"])
        body = _major_visual(num)
        subtitle = f"MAJOR ARCANA · {ROMAN[num]}"
        footer = ROMAN[num]
    else:
        suit = card["suit"]
        rank = str(card["rank"])
        number = int(card["number"])
        body = _layout_suit(suit, number)
        subtitle = SUIT_LABEL[suit]
        footer = f"{rank} · {SUIT_GLYPH[suit]}"

    return frame(name, subtitle, body, footer)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    deck = json.loads(DECK_PATH.read_text(encoding="utf-8"))
    cards = {c["name"]: render_card(c) for c in deck["cards"]}
    payload = {
        "version": "1.0",
        "source": "generated by scripts/generate_tarot_art.py",
        "size": {"width": W, "height": H},
        "cards": cards,
    }
    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(cards)} cards to {OUT_PATH}")


if __name__ == "__main__":
    main()
