"""
Vajra.Stream Core Package
Core audio, visual, and database systems
"""

# Conditional imports to avoid hard dependencies
try:
    from .audio_generator import ScalarWaveGenerator, BLESSING_FREQUENCIES, INTENTION_TO_FREQUENCY
    __all__ = ['ScalarWaveGenerator', 'BLESSING_FREQUENCIES', 'INTENTION_TO_FREQUENCY']
except ImportError:
    __all__ = []
