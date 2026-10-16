"""Image prompts that never ask a model to paint numbers.

The honest-instrument rule (docs/DEVELOPMENT_ROADMAP.md): every value the UI
shows is a *record*, *computed*, a *draw* or *decorative*. Image models cannot
keep that promise. Given "Moon 19.3° Scorpio (44% illuminated)" they paint
"Full Moon 90%", garbled degrees and invented glyphs. So:

* an image prompt carries **imagery only**: computed sky facts are turned into
  words ("a thin waning crescent moon"), never into digits, and every prompt
  ends with :data:`NO_TEXT_SUFFIX`;
* the computed facts themselves travel **beside** the image as
  ``caption_facts`` (``[{"label", "value", "provenance"}]``), and the UI
  overlays them with their provenance label.

This module is the one place that does that transformation. Callers:
``core/working.py`` (folio witness), ``backend/core/services/sigil_service.py``,
the Outlook illustration route, the LLM ``generate_image`` tool and the
Outlook narrative-to-video prompt.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any

from core.provenance import PROVENANCE_KINDS, Provenance

logger = logging.getLogger(__name__)

# The shared vocabulary (core/provenance.py), re-exported under the names this module used.
PROVENANCES: frozenset[str] = PROVENANCE_KINDS

#: Appended to every generated image prompt. Contains no digits, so sanitizing is idempotent.
NO_TEXT_SUFFIX = (
    "No lettering, no numerals, no glyphs, no captions, no labels, no inscriptions: "
    "the image carries no text of any kind."
)

#: The same rule phrased as an instruction to an LLM that writes an image or video prompt.
LLM_NO_TEXT_RULE = (
    "Describe imagery only. Never put numbers, degrees, percentages, dates, times, house numbers, "
    "counts, chapter or section headings, zodiac or planetary glyphs, or any words meant to be "
    "written in the picture: image models paint them as garbled text. Turn computed facts into "
    "qualitative imagery (a thin waning crescent moon, the sun low in the west) and ask for an image "
    "with no lettering, captions or labels. The interface captions the real values itself."
)

DEFAULT_MAX_CHARS = 1500


# -- caption facts -----------------------------------------------------------------


def caption_fact(label: str, value: Any, provenance: Provenance) -> dict[str, str]:
    """One ``{"label", "value", "provenance"}`` entry of an image's ``caption_facts``."""
    if provenance not in PROVENANCES:
        raise ValueError(f"unknown provenance {provenance!r}; choose one of {sorted(PROVENANCES)}")
    return {"label": str(label), "value": str(value), "provenance": provenance}


# -- the moon ----------------------------------------------------------------------


def moon_at(dt: datetime | str | None) -> dict[str, Any] | None:
    """The geocentric moon at ``dt`` (Swiss Ephemeris), or ``None`` if it cannot be computed.

    Returns ``{"illumination": 0-100 (one decimal), "phase_angle": 0-360, "waxing": bool}``.
    ISO strings are accepted. A naive time is taken as the server's local time
    (that is how ``datetime.now()`` stamps such as Outlook's ``date_generated``
    are written); the moon's phase barely moves within a few hours either way.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return None
    dt = dt.astimezone(timezone.utc)
    try:
        import swisseph as swe
    except ImportError:
        return None
    try:
        hours = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        jd = swe.julday(dt.year, dt.month, dt.day, hours)
        sun = swe.calc_ut(jd, swe.SUN)[0][0]
        moon = swe.calc_ut(jd, swe.MOON)[0][0]
    except Exception as exc:  # an ephemeris failure must not break sealing a folio
        logger.warning("moon_at(%s) failed: %s", dt, exc)
        return None
    angle = (moon - sun) % 360.0
    illumination = (1.0 - math.cos(math.radians(angle))) / 2.0 * 100.0
    return {"illumination": round(illumination, 1), "phase_angle": round(angle, 2), "waxing": angle < 180.0}


def moon_imagery(illumination: float, waxing: bool | None = None) -> str:
    """Words for a moon of ``illumination`` percent (0-100). "full" only when it is computed as full."""
    pct = max(0.0, min(100.0, float(illumination)))
    side = "" if waxing is None else ("waxing " if waxing else "waning ")
    if pct < 2.0:
        return "a moonless night sky, the new moon unseen"
    if pct < 20.0:
        return f"a thin {side}crescent moon"
    if pct < 42.0:
        return f"a {side}crescent moon"
    if pct < 58.0:
        return f"a {side}half moon"
    if pct < 97.0:
        return f"a {side}gibbous moon"
    return "a full moon"


_PHASE_NAME_IMAGERY: dict[str, str] = {
    "new": "a moonless night sky, the new moon unseen",
    "new moon": "a moonless night sky, the new moon unseen",
    "waxing crescent": "a waxing crescent moon",
    "first quarter": "a waxing half moon",
    "waxing gibbous": "a waxing gibbous moon",
    "full": "a full moon",
    "full moon": "a full moon",
    "waning gibbous": "a waning gibbous moon",
    "last quarter": "a waning half moon",
    "third quarter": "a waning half moon",
    "waning crescent": "a waning crescent moon",
}


def moon_imagery_from_phase_name(name: str | None) -> str | None:
    """Words for a named phase ("Waxing Gibbous"), or ``None`` if the name is unknown."""
    if not name:
        return None
    return _PHASE_NAME_IMAGERY.get(" ".join(str(name).lower().replace("_", " ").split()))


def moon_phase_words(moon: dict[str, Any]) -> str:
    """ "waning crescent", "full", ... for a :func:`moon_at` result (for captions, not prompts)."""
    words = moon_imagery(moon["illumination"], moon.get("waxing"))
    if words.startswith("a moonless"):
        return "new"
    return words.removeprefix("a ").removeprefix("thin ").removesuffix(" moon")


def moon_caption_fact(moon: dict[str, Any], label: str = "Moon") -> dict[str, str]:
    """The computed caption for a :func:`moon_at` result, e.g. ``44% illuminated, waning crescent``."""
    return caption_fact(label, f"{moon['illumination']:.0f}% illuminated, {moon_phase_words(moon)}", "computed")


# -- sanitizing ----------------------------------------------------------------------

_ORDINAL_WORDS = r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth"
_MONTHS = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)
_NUM = r"\d+(?:[.,]\d+)*"

# Order matters: whole patterns (dates, degrees, percents, houses) go before bare digit runs.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # markdown headings and wholly bold heading lines ("**I. Invocatio (Awakening)**")
    (re.compile(r"(?m)^\s*#{1,6}[^\n]*$"), " "),
    (re.compile(r"(?m)^\s*\*\*[^*\n]{0,120}\*\*\s*:?\s*$"), " "),
    (re.compile(r"\*\*[IVXLC]{1,6}\.[^*\n]{0,120}\*\*"), " "),
    # roman-numeral section markers: "I. Invocatio", "IV. Sigillum"
    (re.compile(r"(?<![\w.])[IVXLC]{1,6}\.(?=\s+[A-Z])"), " "),
    (re.compile(r"\b(?:chapter|part|stage|section|canto|verse)\s+(?:" + _NUM + r"|[IVXLC]{1,6})\b", re.I), " "),
    # dates and times
    (re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}(?:[T ]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?\b"), " "),
    (re.compile(r"\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b"), " "),
    (re.compile(r"\b(?:" + _MONTHS + r")\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b", re.I), " "),
    (re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:" + _MONTHS + r")\b\.?(?:,?\s+\d{4})?", re.I), " "),
    (re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]\.?m\.?|utc|gmt)?(?![\w])", re.I), " "),
    # degrees, arc minutes/seconds ("26.5°", "19° 21' 4\"", "12 degrees")
    (
        re.compile(
            r"[-+]?" + _NUM + r"\s*(?:°|º|˚|\bdeg(?:rees?)?\b)"
            r"(?:\s*\d+(?:\.\d+)?\s*['′’](?:\s*\d+(?:\.\d+)?\s*[\"″”])?)?",
            re.I,
        ),
        " ",
    ),
    # percentages, with a trailing "illuminated"/"illumination" ("44% illuminated")
    (re.compile(_NUM + r"\s*(?:%|\bper\s*cent\b|\bpercent\b)(?:\s+illuminat\w*)?", re.I), " "),
    # house numbers: "House II", "(House IV)", "10th house", "in the second house"
    (re.compile(r"\b(?:in\s+(?:the\s+)?)?(?:\d+(?:st|nd|rd|th)?|" + _ORDINAL_WORDS + r")\s+house\b", re.I), " "),
    (re.compile(r"\b(?:[Hh]ouse|HOUSE)\s+(?:[IVXLC]{1,6}|\d+)\b"), " "),
    # multipliers and counts ("×108", "x 1,000", "#3")
    (re.compile(r"[×✕✖]\s*" + _NUM), " "),
    (re.compile(r"\bx\s*" + _NUM + r"\b", re.I), " "),
    (re.compile(r"#\s*" + _NUM), " "),
    # ordinals and any remaining digit run
    (re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.I), " "),
    (re.compile(r"\d+(?:[.,:/-]\d+)*"), " "),
]

# Scripts and symbol blocks a model would paint as (garbled) lettering or glyphs:
# Indic, Tibetan, astrological/misc symbols, dingbats, CJK, Hangul, emoji.
_GLYPH_CHARS = re.compile("[" "ऀ-෿" "ༀ-࿿" "←-⇿" "☀-➿" "⺀-鿿" "가-힯" "豈-﫿" "\U0001f000-\U0001faff" "°º˚×✕✖" "]+")

_CLEANUPS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[*_#`>~|]+"), " "),
    (re.compile(r"\s+"), " "),
    (re.compile(r"[(\[{]\s*[-–—,;:./&+]*\s*[)\]}]"), " "),  # emptied brackets
    (re.compile(r"\s+([,.;:!?)\]])"), r"\1"),
    (re.compile(r"([(\[])\s+"), r"\1"),
    (re.compile(r"([,;:])(?:\s*[,;:])+"), r"\1"),
    (re.compile(r"[,;:]\s*([.!?])"), r"\1"),
    (re.compile(r"([.!?])(?:\s*[.,;:])+"), r"\1"),
    (re.compile(r"\s*[-–—]\s*([,.;:])"), r"\1"),
    (re.compile(r"\s+"), " "),
]


def sanitize_image_text(text: str | None) -> str:
    """Strip numeric chart data, headings, glyphs and markup from text bound for an image model.

    Degrees, percentages, dates, times, house numbers, multipliers, section
    numerals and every remaining digit run are removed; whitespace and
    leftover punctuation are tidied into one paragraph. Idempotent.
    """
    if not text:
        return ""
    out = str(text)
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    out = _GLYPH_CHARS.sub(" ", out)
    for pattern, repl in _CLEANUPS:
        out = pattern.sub(repl, out)
    return out.strip(" ,;:-–—")


def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:-–—")
    return cut


def finalize_image_prompt(prompt: str | None, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """The prompt as sent to any image model: sanitized, clipped, ending in :data:`NO_TEXT_SUFFIX`.

    Idempotent, so a prompt finalized by its builder can safely pass through
    a second backstop (for example the LLM ``generate_image`` tool).
    """
    body = sanitize_image_text(prompt)
    if NO_TEXT_SUFFIX in body:
        body = body.replace(NO_TEXT_SUFFIX, " ")
        body = sanitize_image_text(body)
    body = _clip(body, max(0, max_chars - len(NO_TEXT_SUFFIX) - 2))
    if not body:
        return NO_TEXT_SUFFIX
    if body[-1] not in ".!?":
        body += "."
    return f"{body} {NO_TEXT_SUFFIX}"


# -- Outlook ---------------------------------------------------------------------------

_GENRE_IMAGERY: dict[str, str] = {
    "healing": "soft lapis-blue and green light, lotus blossoms, gentle radiance",
    "victory": "golden-red light breaking through clouds, banners of light on a summit",
    "alchemist": "molten gold in a crucible, rising steam, leaden grey turning radiant",
    "dharani": "luminous abstract light-forms spiralling into a mandala, deep indigo space",
    "fun_parable": "whimsical storybook landscape, playful colour, a trickster figure dancing",
    "compassion": "rose-gold light, a heart-lotus opening, petals drifting",
    "wisdom": "blue-white clarity light cutting through mist, scrolls dissolving into stars",
    "protection": "vajra geometry forming a crystalline shield, deep blue and electric cyan",
}


def outlook_illustration_prompt(
    narrative: str,
    genre: str | None = None,
    moon: dict[str, Any] | None = None,
    excerpt_chars: int = 600,
    deity_clause: str | None = None,
) -> str:
    """Image prompt for an Outlook narrative: genre imagery, a sanitized excerpt, the computed moon.

    The narrative is LLM prose full of chart data ("Sun at 26.5° Leo (House II)")
    and section headings ("I. Invocatio"); none of that reaches the image model.
    A ``deity_clause`` (core/iconography.py) is placed at the centre of the scene.
    """
    genre_key = (genre or "healing").strip().lower()
    style = _GENRE_IMAGERY.get(genre_key, _GENRE_IMAGERY["healing"])
    excerpt = _clip(sanitize_image_text(narrative), excerpt_chars)
    parts = [f"Sacred painted illustration of a {genre_key.replace('_', ' ')} blessing: {style}."]
    if deity_clause:
        parts.append(f"At its centre: {deity_clause}")
    if moon is not None:
        parts.append(f"In the sky, {moon_imagery(moon['illumination'], moon.get('waxing'))}.")
    if excerpt:
        parts.append(f"Scene drawn from the blessing: {excerpt}")
    # The deity clause gets its own budget so the excerpt and moon still fit after it.
    return finalize_image_prompt(" ".join(parts), max_chars=DEFAULT_MAX_CHARS + len(deity_clause or ""))
