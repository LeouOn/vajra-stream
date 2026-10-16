"""Session request models shared by the sessions API and ``VajraStreamService``.

These pydantic models used to live in ``backend/app/api/v1/endpoints/sessions.py``,
which forced ``vajra_service`` (the service layer) to import the API layer and,
through the endpoints package ``__init__``, every endpoint module. They live
here now so the dependency points downward: API -> service -> models.
"""

from pydantic import BaseModel


class AudioConfig(BaseModel):
    frequency: float = 136.1
    duration: float = 30.0
    volume: float = 0.8
    prayer_bowl_mode: bool = True
    harmonic_strength: float = 0.3
    modulation_depth: float = 0.05
    envelope_type: str = "prayer_bowl"


class SessionConfig(BaseModel):
    name: str
    intention: str
    duration: int = 3600
    audio_frequency: float = 136.1
    astrology_enabled: bool = True
    hardware_enabled: bool = True
    visuals_enabled: bool = True

    _audio_config: AudioConfig = None

    def __init__(self, **data):
        super().__init__(**data)
        self._audio_config = AudioConfig(
            frequency=self.audio_frequency,
            duration=30.0,
            volume=0.8,
            prayer_bowl_mode=True,
            harmonic_strength=0.3,
            modulation_depth=0.05,
            envelope_type="prayer_bowl",
        )

    @property
    def audio_config(self) -> AudioConfig:
        return self._audio_config
