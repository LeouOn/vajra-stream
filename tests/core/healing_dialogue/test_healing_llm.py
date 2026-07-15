# tests/core/healing_dialogue/test_healing_llm.py
"""Tests for AsyncHealingDialogue — the multi-turn LLM service.

Uses a FakeProvider that satisfies the BaseLLMProvider Protocol and returns
a canned ChatResponse. This mirrors the pattern in
``tests/core/llm/test_registry.py`` but adds a working ``generate()`` method
that returns whatever string the test injects.

Covers:
* ``respond()`` returns a dict with ``content``, ``phase_hint``,
  ``insights_update`` keys.
* Keyword-based phase hint detection (e.g. "shall we see what the stars"
  in ARRIVAL yields ``phase_hint == "seeing"``).
* Structured JSON ``phase_transition`` hint blocks win over keyword detection.
* Emotion / body-location keyword extraction populates ``insights_update``.
* No healthy provider -> RuntimeError with a clear message.
* Empty message list -> ValueError.
"""

from __future__ import annotations

import pytest

from core.healing_dialogue.phases import DialoguePhase
from core.llm.healing import AsyncHealingDialogue
from core.llm.models import ChatRequest, ChatResponse, HealthStatus
from core.llm.registry import ProviderRegistry

# ---------------------------------------------------------------------------
# FakeProvider — minimal BaseLLMProvider Protocol implementation
# ---------------------------------------------------------------------------


class FakeProvider:
    """Minimal provider stub whose generate() returns a canned ChatResponse.

    The response content is set via the ``response_content`` constructor arg,
    so each test can inject the exact text the LLM would have returned.
    """

    def __init__(
        self,
        name: str = "fake",
        priority: int = 50,
        healthy: bool = True,
        response_content: str = "I hear you.",
    ) -> None:
        self.name = name
        self.priority = priority
        self._healthy = healthy
        self.response_content = response_content
        self.generate_calls: list[ChatRequest] = []

    async def health_check(self) -> HealthStatus:
        return HealthStatus(provider=self.name, healthy=self._healthy)

    async def list_models(self):
        return []

    async def generate(self, request: ChatRequest) -> ChatResponse:
        self.generate_calls.append(request)
        return ChatResponse(
            content=self.response_content,
            provider=self.name,
            model="fake-model",
        )

    async def stream(self, request: ChatRequest):
        raise NotImplementedError
        yield  # pragma: no cover — make it an async generator for typing

    async def close(self):
        pass


def _build_dialogue(
    response_content: str,
    *,
    healthy: bool = True,
) -> tuple[AsyncHealingDialogue, FakeProvider]:
    """Build an AsyncHealingDialogue wired to a single FakeProvider.

    Returns the dialogue and the provider (so tests can inspect generate_calls).
    """
    registry = ProviderRegistry()
    provider = FakeProvider(
        response_content=response_content,
        healthy=healthy,
        priority=90,
    )
    registry.register(provider)
    return AsyncHealingDialogue(registry), provider


# ---------------------------------------------------------------------------
# respond() shape
# ---------------------------------------------------------------------------


async def test_respond_returns_dict_with_required_keys():
    """respond() returns content, phase_hint, insights_update."""
    dialogue, _ = _build_dialogue("I am here with you. Take your time.")

    result = await dialogue.respond(
        messages=[{"role": "user", "content": "I lost everything."}],
        phase=DialoguePhase.ARRIVAL,
    )

    assert isinstance(result, dict)
    assert set(result.keys()) == {"content", "phase_hint", "insights_update"}
    assert result["content"] == "I am here with you. Take your time."


async def test_respond_content_echoes_provider_output():
    """The 'content' key carries the provider's response text verbatim."""
    dialogue, _ = _build_dialogue("Reflecting back: you feel grief in your chest.")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "I feel heavy."}],
        phase=DialoguePhase.ARRIVAL,
    )
    assert result["content"] == "Reflecting back: you feel grief in your chest."


async def test_respond_passes_system_prompt_to_provider():
    """The provider receives a ChatRequest with a non-empty phase-aware system_prompt."""
    dialogue, provider = _build_dialogue("present.")
    await dialogue.respond(
        messages=[{"role": "user", "content": "hi"}],
        phase=DialoguePhase.SEEING,
    )
    assert len(provider.generate_calls) == 1
    request = provider.generate_calls[0]
    assert request.system_prompt is not None
    assert "SEEING" in request.system_prompt.upper()


async def test_respond_coerces_unknown_roles_to_user():
    """Unknown roles in the message history are coerced to 'user' (defensive)."""
    dialogue, provider = _build_dialogue("here.")
    await dialogue.respond(
        messages=[
            {"role": "weird-role", "content": "what am I"},
            {"role": "user", "content": "hello"},
        ],
        phase=DialoguePhase.ARRIVAL,
    )
    request = provider.generate_calls[0]
    roles = [m.role for m in request.messages]
    # 'weird-role' coerced to 'user'; 'user' preserved.
    assert roles == ["user", "user"]


async def test_respond_drops_system_role_from_history():
    """The 'system' role is stripped from the message list (system_prompt is separate)."""
    dialogue, provider = _build_dialogue("here.")
    await dialogue.respond(
        messages=[
            {"role": "system", "content": "you are a system"},
            {"role": "user", "content": "hi"},
        ],
        phase=DialoguePhase.ARRIVAL,
    )
    request = provider.generate_calls[0]
    roles = [m.role for m in request.messages]
    assert "system" not in roles
    assert roles == ["user"]


# ---------------------------------------------------------------------------
# Keyword-based phase hint detection
# ---------------------------------------------------------------------------


async def test_phase_hint_arrival_to_seeing_via_keyword():
    """ARRIVAL response mentioning 'shall we see what the stars' -> hint 'seeing'."""
    dialogue, _ = _build_dialogue("I hear the raw charge of this. When you're ready, shall we see what the stars say?")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "I lost everything."}],
        phase=DialoguePhase.ARRIVAL,
    )
    assert result["phase_hint"] == "seeing"


async def test_phase_hint_seeing_to_meeting_via_keyword():
    """SEEING response with 'sit with this' -> hint 'meeting'."""
    dialogue, _ = _build_dialogue("Saturn is transiting your 2nd house. Now let's sit with this together.")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "why did this happen?"}],
        phase=DialoguePhase.SEEING,
    )
    assert result["phase_hint"] == "meeting"


async def test_phase_hint_meeting_to_release_via_keyword():
    """MEETING response with 'offer a practice' -> hint 'release'."""
    dialogue, _ = _build_dialogue("Something has shifted. I can offer a practice to help release this.")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "it moved."}],
        phase=DialoguePhase.MEETING,
    )
    assert result["phase_hint"] == "release"


async def test_phase_hint_release_to_dedication_via_keyword():
    """RELEASE response with 'dedicate' -> hint 'dedication'."""
    dialogue, _ = _build_dialogue("Well done with the tonglen. Now let's dedicate the merit of this practice.")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "I did the practice."}],
        phase=DialoguePhase.RELEASE,
    )
    assert result["phase_hint"] == "dedication"


async def test_phase_hint_dedication_to_completed_via_keyword():
    """DEDICATION response with 'session is complete' -> hint 'completed'."""
    dialogue, _ = _build_dialogue("The merit is offered. This session is complete. Be well.")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "thank you."}],
        phase=DialoguePhase.DEDICATION,
    )
    assert result["phase_hint"] == "completed"


async def test_phase_hint_none_when_no_transition_cue():
    """A plain empathic response with no transition cue yields phase_hint None."""
    dialogue, _ = _build_dialogue("I hear the weight of this. Stay with the breath. You are not alone.")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "it's heavy."}],
        phase=DialoguePhase.ARRIVAL,
    )
    assert result["phase_hint"] is None


async def test_phase_hint_keyword_only_matches_current_phase():
    """A cue for a LATER phase does not fire when we're in an EARLIER phase.

    'dedicate' is a RELEASE -> DEDICATION cue. In ARRIVAL it should NOT match,
    because the keyword table is keyed to the current phase.
    """
    dialogue, _ = _build_dialogue("I hear you. (Someday we may dedicate merit, but not yet.)")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "hi"}],
        phase=DialoguePhase.ARRIVAL,
    )
    assert result["phase_hint"] is None


# ---------------------------------------------------------------------------
# Structured JSON hint blocks (win over keyword detection)
# ---------------------------------------------------------------------------


async def test_phase_hint_json_block_overrides_keywords():
    """A JSON phase_transition block wins over keyword cues."""
    # The text also contains 'dedicate' (a RELEASE cue), but we're in MEETING
    # and the JSON block explicitly suggests 'release'.
    dialogue, _ = _build_dialogue('Stay with the breath. {"phase_transition": "suggested", "next_phase": "release"}')
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "ok"}],
        phase=DialoguePhase.MEETING,
    )
    assert result["phase_hint"] == "release"


async def test_phase_hint_json_block_extracts_next_phase_value():
    """The full JSON block form extracts the value of the 'next_phase' key.

    The regex requires the literal 'phase_transition' marker to be present in
    the block; the actual next-phase value is read from the 'next_phase' key.
    """
    dialogue, _ = _build_dialogue('Present with you. {"phase_transition": "suggested", "next_phase": "meeting"}')
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "hi"}],
        phase=DialoguePhase.ARRIVAL,
    )
    # Even though ARRIVAL -> MEETING is two steps, the hint is surfaced
    # verbatim; the SERVICE layer is responsible for clamping it to one step.
    assert result["phase_hint"] == "meeting"


async def test_phase_hint_json_block_unknown_phase_returns_none():
    """A JSON block with an unknown next_phase value falls back to keyword scan."""
    dialogue, _ = _build_dialogue('{"next_phase": "not-a-phase"}')
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "hi"}],
        phase=DialoguePhase.ARRIVAL,
    )
    assert result["phase_hint"] is None


# ---------------------------------------------------------------------------
# Insight extraction
# ---------------------------------------------------------------------------


async def test_insights_update_extracts_emotions_and_body_locations():
    """Emotion + body keywords in the response populate insights_update."""
    dialogue, _ = _build_dialogue("I feel the grief and fear in your chest and throat. The terror is real.")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "it's heavy."}],
        phase=DialoguePhase.ARRIVAL,
    )
    update = result["insights_update"]
    assert "emotions" in update
    assert "grief" in update["emotions"]
    assert "fear" in update["emotions"]
    assert "terror" in update["emotions"]
    assert "body_locations" in update
    assert "chest" in update["body_locations"]
    assert "throat" in update["body_locations"]


async def test_insights_update_adds_themes_in_seeing_phase():
    """In SEEING/MEETING phases, cosmic_timing/grief/survival_fear themes tag on."""
    dialogue, _ = _build_dialogue(
        "Saturn is transiting your 2nd house — this is a fear and survival moment. The grief of the loss is here."
    )
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "why"}],
        phase=DialoguePhase.SEEING,
    )
    themes = result["insights_update"].get("themes", [])
    assert "cosmic_timing" in themes
    assert "survival_fear" in themes
    assert "grief" in themes


async def test_insights_update_empty_when_no_keywords():
    """A response with no emotion/body keywords yields an empty insights_update."""
    dialogue, _ = _build_dialogue("Take a breath. You are here. This is enough.")
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "ok"}],
        phase=DialoguePhase.ARRIVAL,
    )
    assert result["insights_update"] == {}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


async def test_respond_raises_runtime_error_when_no_healthy_provider():
    """When the registry has no effectively-healthy provider, respond() raises
    ``RuntimeError``.

    The registry applies hysteresis: a single failed health check is treated as
    a transient blip. We must trigger ``FAILURE_THRESHOLD`` consecutive
    failures before ``pick_best()`` returns ``None`` and ``respond()`` raises.
    """
    registry = ProviderRegistry()
    registry.register(FakeProvider(name="sick", healthy=False, priority=90))
    dialogue = AsyncHealingDialogue(registry)

    # Trigger FAILURE_THRESHOLD (2) consecutive failures on "sick" before
    # respond() picks, so the registry now treats it as down.
    await registry.pick_best(use_cache=False)
    await registry.pick_best(use_cache=False)

    with pytest.raises(RuntimeError, match="No healthy LLM provider"):
        await dialogue.respond(
            messages=[{"role": "user", "content": "hi"}],
            phase=DialoguePhase.ARRIVAL,
        )


async def test_respond_raises_value_error_when_no_messages():
    """An empty message list raises ValueError before touching the registry."""
    dialogue, _ = _build_dialogue("anything")
    with pytest.raises(ValueError, match="at least one message"):
        await dialogue.respond(messages=[], phase=DialoguePhase.ARRIVAL)


async def test_respond_raises_value_error_when_all_messages_empty():
    """Messages with empty content are filtered out -> empty -> ValueError."""
    dialogue, _ = _build_dialogue("anything")
    with pytest.raises(ValueError, match="at least one message"):
        await dialogue.respond(
            messages=[{"role": "user", "content": ""}],
            phase=DialoguePhase.ARRIVAL,
        )


# ---------------------------------------------------------------------------
# Custom temperature / max_tokens forwarded to provider
# ---------------------------------------------------------------------------


async def test_respond_forwards_temperature_and_max_tokens():
    """The temperature and max_tokens kwargs land on the ChatRequest."""
    dialogue, provider = _build_dialogue("present.")
    await dialogue.respond(
        messages=[{"role": "user", "content": "hi"}],
        phase=DialoguePhase.ARRIVAL,
        temperature=0.3,
        max_tokens=256,
    )
    request = provider.generate_calls[0]
    assert request.temperature == 0.3
    assert request.max_tokens == 256
