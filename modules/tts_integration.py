"""
TTS Integration Module
Thin adapter wrapping core/tts_integration.py for the DI container.
"""

from typing import Any

from modules.interfaces import EventBus


class TTSService:
    """Text-to-speech service — wraps core TTSNarrator."""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self._narrator = None
        self._engine_type = "auto"

    @property
    def narrator(self):
        if self._narrator is None:
            from core.tts_integration import TTSNarrator

            self._narrator = TTSNarrator(engine=self._engine_type)
        return self._narrator

    def generate_audio(self, text: str, output_file: str = "/tmp/vajra_tts.mp3", slow: bool = False) -> dict[str, Any]:
        """Generate audio from text."""
        from core.tts_integration import SpeakingRate

        rate = SpeakingRate.SLOW if slow else SpeakingRate.NORMAL
        path = self.narrator.generate_audio(text=text, output_file=output_file, rate=rate)
        return {"output_file": path, "text_length": len(text)}

    def narrate_story(self, story: Any, output_file: str = "/tmp/vajra_story.mp3", slow: bool = True) -> dict[str, Any]:
        """Narrate a blessing story."""
        from core.tts_integration import SpeakingRate

        rate = SpeakingRate.SLOW if slow else SpeakingRate.NORMAL
        path = self.narrator.narrate_story(story=story, output_file=output_file, rate=rate)
        return {"output_file": path}

    def generate_mantra_audio(
        self, mantra: str = "Om Mani Padme Hum", repetitions: int = 21, output_file: str = "/tmp/vajra_mantra.mp3"
    ) -> dict[str, Any]:
        """Generate mantra repetition audio."""
        path = self.narrator.generate_mantra_audio(mantra=mantra, repetitions=repetitions, output_file=output_file)
        return {"output_file": path, "mantra": mantra, "repetitions": repetitions}

    def guided_meditation(self, script: str, output_file: str = "/tmp/vajra_meditation.mp3") -> dict[str, Any]:
        """Generate guided meditation audio."""
        path = self.narrator.guided_meditation(script=script, output_file=output_file)
        return {"output_file": path, "script_length": len(script)}

    def list_voices(self) -> list[dict[str, Any]]:
        """List available TTS voices."""
        voices = self.narrator.list_voices()
        return [{"id": v.id, "name": v.name, "gender": v.gender.value, "language": v.language} for v in voices]

    def get_status(self) -> dict[str, Any]:
        return {
            "available": self.narrator.engine.is_available() if self.narrator else False,
            "engine": self.narrator.engine.__class__.__name__ if self.narrator else "none",
            "voices_count": len(self.list_voices()) if self.narrator else 0,
        }
