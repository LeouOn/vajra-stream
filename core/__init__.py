"""
Vajra.Stream Core Package
Core audio, visual, and database systems
"""

# Conditional imports to avoid hard dependencies. The `audio_generator`
# module imports `sounddevice` which can raise BOTH ImportError (package
# missing) and OSError (PortAudio native lib missing), so we catch both.
try:
    from .audio_generator import BLESSING_FREQUENCIES, INTENTION_TO_FREQUENCY, ScalarWaveGenerator

    __all__ = ["ScalarWaveGenerator", "BLESSING_FREQUENCIES", "INTENTION_TO_FREQUENCY"]
except (ImportError, OSError):
    __all__ = []
