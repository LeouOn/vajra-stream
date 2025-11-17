"""
Pytest configuration for Vajra Stream tests

Handles mocking of system dependencies that may not be available in test environment.
"""

import sys
from unittest.mock import MagicMock

# Mock sounddevice if not available
try:
    import sounddevice
except (OSError, ImportError):
    sys.modules['sounddevice'] = MagicMock()

# Mock opencv if needed
try:
    import cv2
except (OSError, ImportError):
    sys.modules['cv2'] = MagicMock()

# Ensure proper Python path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
