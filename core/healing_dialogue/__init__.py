# core/healing_dialogue/__init__.py
"""Healing dialogue — multi-turn LLM-guided healing container.

Public API:

* :class:`DialoguePhase` — the five-phase arc enum.
* :class:`DialogueState` — JSON-serializable session state.
* :func:`build_system_prompt` — phase-aware system prompt assembler.
* :data:`HEALING_DIALOGUE_BASE_PROMPT`, :data:`PHASE_GUIDANCE` — the prompt
  constants used by the system prompt builder.

The multi-turn LLM service (:class:`~core.llm.healing.AsyncHealingDialogue`)
and the context module (:class:`~core.context.healing_dialogue.HealingPhaseContextModule`)
live in their respective packages and import from here.
"""

from __future__ import annotations

from core.healing_dialogue.phases import DialoguePhase, DialogueState
from core.healing_dialogue.prompts import (
    HEALING_DIALOGUE_BASE_PROMPT,
    PHASE_GUIDANCE,
    build_system_prompt,
)

__all__ = [
    "DialoguePhase",
    "DialogueState",
    "HEALING_DIALOGUE_BASE_PROMPT",
    "PHASE_GUIDANCE",
    "build_system_prompt",
]
