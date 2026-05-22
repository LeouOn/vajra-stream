"""
Vajra.Stream Core Package
Core audio, visual, and database systems
"""

# Conditional imports to avoid hard dependencies
try:
    from .audio_generator import BLESSING_FREQUENCIES, INTENTION_TO_FREQUENCY, ScalarWaveGenerator

    __all__ = ["ScalarWaveGenerator", "BLESSING_FREQUENCIES", "INTENTION_TO_FREQUENCY"]
except ImportError:
    __all__ = []
