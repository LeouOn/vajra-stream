"""
Vajra.Stream Configuration
Edit these settings to customize your setup
"""

# Audio Settings
SAMPLE_RATE = 44100  # Hz
AUDIO_DEVICE = "default"  # or specific device name

# Prayer Bowl Audio Settings (NEW)
PRAYER_BOWL_MODE = True  # Default to prayer bowl synthesis (rich harmonics)
PURE_SINE_MODE = False  # Set to True for original simple sine waves
PRAYER_BOWL_HARMONICS = True  # Enable complex harmonic series
PRAYER_BOWL_ENVELOPES = True  # Enable ADSR envelopes for natural sound
PRAYER_BOWL_MODULATION = True  # Enable subtle tremolo and vibrato effects
PRAYER_BOWL_ATTACK = 4.0  # Attack time in seconds (slower swell)
PRAYER_BOWL_DECAY = 2.0  # Decay time in seconds
PRAYER_BOWL_SUSTAIN = 0.4  # Sustain level (quieter)
PRAYER_BOWL_RELEASE = 5.0  # Release time in seconds (long natural fade)

# Hardware Configuration
HARDWARE_LEVEL = 2  # 2 = passive crystals, 3 = amplified
AMPLIFIER_CONNECTED = False
BASS_SHAKER_CONNECTED = False

# Default Frequencies (Hz)
BLESSING_FREQUENCIES = [7.83, 136.1, 528, 639, 741]

# Database
DB_PATH = "vajra_stream.db"

# Session Defaults
DEFAULT_DURATION = 300  # seconds (5 minutes)
DEFAULT_INTENTION = "May all beings be happy and free from suffering"

# Default coordinates (San Francisco) — used as fallback when user location unavailable.
# Frontend mirrors these in frontend/src/lib/geo.ts (DEFAULT_LAT / DEFAULT_LNG).
DEFAULT_LATITUDE = 37.7749
DEFAULT_LONGITUDE = -122.4194

# Crystal Grid
CRYSTAL_COUNT = 6
GRID_PATTERN = "hexagon"  # hexagon, circle, flower_of_life

# Display
VISUAL_MODE = "minimalist"  # minimalist, detailed, off
SHOW_FREQUENCIES = True
SHOW_TIMER = True

# Paths
KNOWLEDGE_PATH = "./knowledge/"
GENERATED_CONTENT_PATH = "./generated/"
SESSION_LOGS_PATH = "./logs/"

# Safety
MAX_VOLUME = 0.5  # Maximum audio volume (0.0 - 1.0) - Quieter is better
WARNING_ENABLED = True  # Warn before amplified mode

# Prayer Bowl Configuration
PRAYER_BOWL_CONFIG = {
    "harmonic_ratios": [1.0, 2.13, 3.02, 4.15, 5.26, 6.33],  # Measured from real bowls
    "inharmonic_partials": [2.89, 3.76, 4.93],  # Metallic resonances
    "tremolo_rate": 0.15,  # Very slow amplitude modulation
    "tremolo_depth": 0.08,  # Subtle
    "vibrato_rate": 0.05,  # Very slow pitch variation
    "vibrato_depth": 0.02,  # Very subtle
}
