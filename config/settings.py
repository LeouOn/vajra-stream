"""
Vajra.Stream Configuration
Edit these settings to customize your setup
"""

# Audio Settings
SAMPLE_RATE = 44100  # Hz
AUDIO_DEVICE = 'default'  # or specific device name

# Hardware Configuration
HARDWARE_LEVEL = 2  # 2 = passive crystals, 3 = amplified
AMPLIFIER_CONNECTED = False
BASS_SHAKER_CONNECTED = False

# Default Frequencies (Hz)
BLESSING_FREQUENCIES = [7.83, 136.1, 528, 639, 741]

# Database
DB_PATH = 'vajra_stream.db'

# Session Defaults
DEFAULT_DURATION = 300  # seconds (5 minutes)
DEFAULT_INTENTION = "May all beings be happy and free from suffering"

# Crystal Grid
CRYSTAL_COUNT = 6
GRID_PATTERN = 'hexagon'  # hexagon, circle, flower_of_life

# Display
VISUAL_MODE = 'minimalist'  # minimalist, detailed, off
SHOW_FREQUENCIES = True
SHOW_TIMER = True

# Paths
KNOWLEDGE_PATH = './knowledge/'
GENERATED_CONTENT_PATH = './generated/'
SESSION_LOGS_PATH = './logs/'

# Safety
MAX_VOLUME = 0.8  # Maximum audio volume (0.0 - 1.0)
WARNING_ENABLED = True  # Warn before amplified mode
