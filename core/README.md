# core/ — Internal Implementations

This directory contains internal rendering engines, generators, and shared utilities used by the service modules. Code here is **not** directly wired into the DI container — it is consumed by `modules/` services.

## Contents

| File | Description |
|------|-------------|
| `audio_generator.py` | Low-level audio synthesis engine |
| `visual_display.py` | Terminal-based visual display |
| `visual_renderer_simple.py` | Simple image renderer |
| `tts_engine.py` | Text-to-speech engine |
| `radionics_engine.py` | Core radionics computation |
| `advanced_scalar_waves.py` | Advanced scalar wave algorithms |
| `energetic_anatomy.py` | Energetic anatomy data and logic |
| `blessing_narratives.py` | Narrative generation engine |
| `dharma_tales.py` | Dharma story generation |
| `rothko_generator.py` | Rothko-style art generation |
| `llm_integration.py` | LLM API integration layer |

## Guideline

If you're adding new functionality, create the service class in `modules/` and put internal helpers here.
