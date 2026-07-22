#!/usr/bin/env python3
"""
Wave 4 Task 26 — ``container.audio`` LLM-tool integration lock.

Behaviour lock (TDD): asserts that the project-root DI container
(``container.py:122-129``) exposes a working ``audio`` property that
returns a ``modules/audio.py:AudioService`` instance, and that this
instance is callable through the same surface the RadionicsOperator
LLM tool path uses (``modules/radionics_operator.py:511`` →
``svc = self._container.audio`` → ``svc.generate_tone(...)``).

Per ADR 001 (``docs/decisions/001-audio-subsystem-canonical.md``):

* ``modules/audio.py:AudioService`` is the **LLM-tool** audio service.
  It is intentionally kept SEPARATE from the canonical user-facing
  audio subsystem at ``backend/core/services/vajra_service.py``
  (different constructor, different delegates, different lifecycle).
* The two subsystems MUST NOT be conflated. This test guards the
  LLM-tool side of that contract.

This test does NOT exercise ``backend/core/services/vajra_service.py``;
that is the HTTP/WS surface covered by other tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is importable so `from container import Container`
# resolves to project-root container.py (NOT backend/app/container.py,
# which does not exist — see ADR 001 note).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from container import Container  # noqa: E402  (project-root container.py)
from modules.audio import AudioService  # noqa: E402


@pytest.fixture
def container() -> Container:
    """Return a freshly-reset singleton Container.

    ``tests/conftest.py`` defines a ``fresh_container`` fixture that
    re-initialises the singleton; we re-create that locally so this
    test file is self-contained and does not depend on fixture scope
    interactions with other tests.
    """
    c = Container()
    c._initialized = False
    c.__init__()
    yield c
    c.reset()


class TestContainerAudioLLMToolIntegration:
    """Lock the LLM-tool audio pathway per ADR 001."""

    # ------------------------------------------------------------------
    # ADR 001 §Decision 3: ``container.audio`` → ``AudioService``
    # ------------------------------------------------------------------

    def test_container_exposes_audio_property(self, container: Container) -> None:
        """The DI container MUST expose ``audio`` as a lazy property.

        Cites ``container.py:122-129`` (DI registration of modules.audio).
        """
        assert hasattr(container, "audio"), (
            "container.audio must exist — per ADR 001 §Decision 3 it is "
            "the LLM-tool audio provider registered at container.py:122-129."
        )

    def test_container_audio_returns_audio_service_instance(self, container: Container) -> None:
        """``container.audio`` MUST return a ``modules/audio.py:AudioService``.

        ADR 001: ``modules/audio.py:AudioService`` (instance via project-root
        ``container.py`` @ L122–129).
        """
        svc = container.audio
        assert isinstance(svc, AudioService), (
            f"container.audio must return modules.audio.AudioService, got {type(svc).__module__}.{type(svc).__name__}"
        )

    def test_container_audio_is_cached_singleton_per_container(self, container: Container) -> None:
        """The lazy property MUST cache on the container (same instance each access)."""
        first = container.audio
        second = container.audio
        assert first is second, (
            "container.audio must cache (lazy singleton) — repeated access "
            "should return the same AudioService instance."
        )

    def test_container_audio_receives_event_bus(self, container: Container) -> None:
        """ADR 001: container wires ``AudioService(event_bus=self.event_bus)``."""
        svc = container.audio
        assert svc.event_bus is container.event_bus, (
            "container.audio must be constructed with the container's event_bus "
            "(per container.py:128 — AudioService(event_bus=self.event_bus))."
        )

    # ------------------------------------------------------------------
    # LLM tool integration (RadionicsOperator.generate_audio)
    # ------------------------------------------------------------------

    def test_container_audio_supports_generate_tone_llm_tool_call(self, container: Container) -> None:
        """The LLM tool ``generate_audio`` in ``modules/radionics_operator.py:511``
        calls ``svc = self._container.audio`` then ``svc.generate_tone(...)``.

        Lock the minimum interface contract: ``container.audio`` MUST be
        callable with ``frequency=`` and ``duration=`` keyword arguments
        (the two kwargs the LLM tool path passes through that are declared
        on ``AudioService.generate_tone``).
        """
        svc = container.audio
        # generate_tone must accept frequency= and duration= kwargs.
        # On a headless / numpy-less box the underlying generator may be
        # None, in which case AudioService returns an {"error": ...} dict
        # instead of raising. Either outcome is acceptable for THIS lock;
        # what we are locking is that the call itself does not raise
        # TypeError on the LLM tool's kwarg shape.
        result = svc.generate_tone(frequency=528.0, duration=0.05)
        assert isinstance(result, dict), (
            "AudioService.generate_tone must return a dict (success or error) "
            "when called via the LLM tool kwarg shape "
            "(frequency=, duration=)."
        )

    def test_radionics_operator_generate_audio_tool_routes_to_container_audio(self, container: Container) -> None:
        """Smoke-test the actual LLM tool dispatcher path:
        ``RadionicsOperator.dispatcher.dispatch('generate_audio', {...})``
        MUST resolve ``self._container.audio`` (i.e. the AudioService
        locked above). We monkeypatch ``container.audio.generate_tone``
        to a sentinel and confirm the dispatcher actually calls it.

        Cites ``modules/radionics_operator.py:511`` (LLM tool consumer).
        """
        from modules.radionics_operator import RadionicsOperator

        operator = RadionicsOperator(container=container, llm=None)

        called: dict[str, object] = {}

        def fake_generate_tone(**kwargs):
            called["kwargs"] = kwargs
            return {"status": "success", "_mock": True}

        # Patch the instance method on the live AudioService that
        # ``container.audio`` returns; this is the same object the
        # dispatcher resolves via ``self._container.audio``
        # (radionics_operator.py:511 → ``svc = self._container.audio``).
        container.audio.generate_tone = fake_generate_tone  # type: ignore[assignment]

        result = operator.dispatcher.dispatch(
            "generate_audio",
            {"frequency_hz": 136.1, "duration_seconds": 5, "mode": "prayer_bowl"},
        )

        assert called.get("kwargs"), (
            "RadionicsOperator.dispatcher.dispatch('generate_audio', ...) must route to "
            "container.audio.generate_tone — per modules/radionics_operator.py:511."
        )
        # The dispatcher maps frequency_hz → frequency, duration_seconds → duration.
        kwargs = called["kwargs"]
        assert kwargs.get("frequency") == 136.1, (
            f"LLM tool must map arguments['frequency_hz'] → generate_tone(frequency=...); got kwargs={kwargs!r}"
        )
        assert kwargs.get("duration") == 5, (
            f"LLM tool must map arguments['duration_seconds'] → generate_tone(duration=...); got kwargs={kwargs!r}"
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# ADR 001 scope guard: ``modules/audio.py`` ≠ ``vajra_service.py``
# ---------------------------------------------------------------------------


def test_modules_audio_is_distinct_concern_from_vajra_service() -> None:
    """ADR 001 §Decision 1 vs §Decision 3: the canonical user-facing
    audio subsystem (``backend/core/services/vajra_service.py``) and the
    LLM-tool audio subsystem (``modules/audio.py``) MUST be two distinct
    modules. They must not be merged (G2 — different concerns).
    """
    root = Path(__file__).resolve().parents[2]
    modules_audio = root / "modules" / "audio.py"
    vajra_service = root / "backend" / "core" / "services" / "vajra_service.py"

    assert modules_audio.exists(), "modules/audio.py must be KEPT per ADR 001 §Decision 3 (LLM-tool path)."
    assert vajra_service.exists(), (
        "backend/core/services/vajra_service.py must be KEPT per ADR 001 §Decision 1 "
        "(canonical user-facing audio path)."
    )
    # Two distinct classes; do not merge.
    assert modules_audio != vajra_service


if __name__ == "__main__":
    # Allow direct execution for evidence-gathering outside pytest.
    raise SystemExit(pytest.main([__file__, "-v"]))
