# modules/ — Service Layer

This is the **canonical location** for all Vajra.Stream service modules. Each module exposes a service class that is instantiated by the DI container (`container.py`).

## Module Index

| Module | Service Class | Description |
|--------|--------------|-------------|
| `scalar_waves.py` | `ScalarWaveService` | Scalar wave generation (QRNG, Lorenz, etc.) |
| `radionics.py` | `RadionicsService` | Radionics broadcasting |
| `anatomy.py` | `AnatomyService` | Chakra and meridian systems |
| `blessings.py` | `BlessingService` | Blessing generation |
| `audio.py` | `AudioService` | Audio synthesis and TTS |
| `visualization.py` | `VisualizationService` | Sacred geometry and Rothko art |
| `astrology.py` | `AstrologyService` | Astrological calculations |
| `time_cycles.py` | `TimeCyclesService` | Kalachakra time-space healing |
| `prayer_wheel.py` | `PrayerWheelService` | Digital prayer wheel |
| `composer.py` | `ComposerService` | Healing music composition |
| `healing.py` | `HealingService` | Comprehensive healing systems |
| `llm.py` | `LLMService` | LLM integration |

## Convention

All service classes accept `event_bus` as their first constructor argument. They communicate through the event bus defined in `infrastructure/event_bus.py`.
