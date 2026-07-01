# core/llm/defaults.py
"""Default model selections per Vajra.Stream use case.

Single source of truth for which model the system recommends for each
task. Used by:

* the `/api/v1/llm/models/defaults` endpoint to drive the Active Model
  Display in the frontend Model Manager;
* documentation / onboarding to make the "what should I use?" answer
  deterministic;
* the OpenRouter provider's ``KNOWN_FEATURED_MODELS`` list (kept in
  sync with the model ids referenced here).

Design goals
------------
* **Nemotron free model is the default for unlimited-cost loops.** The
  blessing loop runs forever; a $0/M model is the only sane default.
* **DeepSeek V4 Flash is the default for cheap interactive traffic**
  where low latency matters more than free pricing.
* Every entry includes a human-readable ``rationale`` so the UI can
  show *why* this model was picked.
"""

from __future__ import annotations

from typing import TypedDict


class UseCaseDefault(TypedDict):
    """A single recommended model + the reason it was chosen.

    Fields:
        model_id: The fully-qualified OpenRouter model identifier
            (e.g. ``"nvidia/nemotron-3-ultra-550b-a55b:free"``).
        display_name: Human-readable label for UI rendering.
        provider: Provider key (``"openrouter"``, ``"deepseek"`` ...).
        rationale: One-line explanation shown to the user.
    """

    model_id: str
    display_name: str
    provider: str
    rationale: str


# ---------------------------------------------------------------------------
# Use-case → default model mapping.
# Update this dict when the recommended model for any feature changes.
# ---------------------------------------------------------------------------
DEFAULT_MODELS_BY_USE_CASE: dict[str, UseCaseDefault] = {
    "outlook_narrative": {
        "model_id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "display_name": "Nemotron 3 Ultra 550B (Free)",
        "provider": "openrouter",
        "rationale": "Free, 1M context, strong reasoning — ideal for long-form blessings.",
    },
    "command_center_chat": {
        "model_id": "deepseek/deepseek-v4-flash",
        "display_name": "DeepSeek V4 Flash",
        "provider": "openrouter",
        "rationale": "Cheap, fast — best for interactive chat.",
    },
    "blessing_loop": {
        "model_id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "display_name": "Nemotron 3 Ultra 550B (Free)",
        "provider": "openrouter",
        "rationale": "Free = unlimited 24/7 loop with zero cost.",
    },
    "autonomous_operator": {
        "model_id": "deepseek/deepseek-v4-flash",
        "display_name": "DeepSeek V4 Flash",
        "provider": "openrouter",
        "rationale": "Cheap autonomous reasoning at scale.",
    },
    "tarot_divination": {
        "model_id": "deepseek/deepseek-v4-flash",
        "display_name": "DeepSeek V4 Flash",
        "provider": "openrouter",
        "rationale": "Cheap, good reasoning for symbolic interpretation.",
    },
    "practice_tts": {
        "model_id": "edge-tts",
        "display_name": "Edge TTS (local)",
        "provider": "edge",
        "rationale": "Local Microsoft Edge TTS — no LLM, no cost.",
    },
}


# ---------------------------------------------------------------------------
# Built-in featured OpenRouter models. Surfaced as "featured" in the
# /api/v1/llm/models/available response so the frontend can pin them
# to the top of the discovery list. Kept in sync with
# DEFAULT_MODELS_BY_USE_CASE so the recommended defaults are always
# discoverable even when OpenRouter's catalogue ordering shifts.
# ---------------------------------------------------------------------------
NEMOTRON_FREE_MODEL_ID = "nvidia/nemotron-3-ultra-550b-a55b:free"

KNOWN_FEATURED_MODEL_IDS: list[str] = [
    NEMOTRON_FREE_MODEL_ID,
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-chat",
    "anthropic/claude-3.5-haiku",
    "openai/gpt-4o-mini",
]
