# Vajra.Stream - New Features Overview

## 🌟 What's New

This release adds comprehensive dharma technology features integrating astrology, AI, visualization, and voice.

## Feature Summary

### 1. 🔮 Astrological Timing (Kalachakra Module)
**File**: `core/astrology.py`

Calculate auspicious times and align practices with cosmic energetics:
- Planetary positions in zodiac signs
- Moon phases and illumination
- Lunar mansions (Nakshatras)
- Sunrise/sunset/Brahma Muhurta calculations
- Recommended frequencies based on astrological conditions
- Dharma calendar events (full/new moons, eclipses)

**Usage**:
```bash
python scripts/vajra_orchestrator.py astrology --latitude 37.7749 --longitude -122.4194
```

### 2. 🎨 Mark Rothko Visual Meditation Generator
**File**: `core/rothko_generator.py`

Creates contemplative color field images for meditation:
- 8 spiritual color palettes (compassion, wisdom, peace, awakening, etc.)
- Soft-edged luminous rectangles
- Chakra visualization series
- Intention-based image generation
- Suitable for visual meditation and dharma halls

**Palettes**:
- **Compassion**: Pinks, soft reds, warm whites
- **Wisdom**: Deep blues, purples, indigos
- **Peace**: Blues, soft greens, white
- **Awakening**: Golds, oranges, warm yellows
- **Emptiness**: Grays, blacks, whites
- **Earth**: Browns, ochres, earth tones
- **Transcendence**: Deep reds, blacks, golds (Tibetan thangka colors)
- **Rainbow Body**: Full spectrum

**Usage**:
```bash
# Generate chakra series
python scripts/vajra_orchestrator.py chakra-visuals

# Auto-generated with prayers
python scripts/vajra_orchestrator.py prayer --intention "peace"
```

### 3. 🤖 LLM Integration (AI Dharma Content)
**File**: `core/llm_integration.py`

Generate prayers, teachings, and meditations using AI:

**Two modes**:
1. **API Models**: Anthropic Claude, OpenAI GPT
2. **Local Models**: GGUF format models (run on your computer)

**Features**:
- Auto-detection (tries local first, then API)
- DharmaLLM specialized interface
- Generate prayers for any intention
- Create dharma teachings
- Meditation instructions
- Contemplation exercises
- Dedications and aspirations

**Local Model Support**:
- Automatically scans `./models/` directory
- Supports any GGUF format model
- Works offline, no API costs
- Full privacy

**Usage**:
```bash
# Using API (set ANTHROPIC_API_KEY or OPENAI_API_KEY)
python scripts/vajra_orchestrator.py prayer --intention "compassion"

# Using local model (place .gguf file in ./models/)
python scripts/vajra_orchestrator.py teaching --intention "emptiness"
```

### 4. 🙏 Digital Prayer Wheel
**File**: `core/prayer_wheel.py`

Continuous prayer generation and broadcasting:
- Traditional mantras library (Om Mani Padme Hum, etc.)
- Four Immeasurables cycle
- Bodhisattva vows
- AI-generated prayers (if LLM enabled)
- Mantra accumulation (108 repetitions)
- Continuous rotation mode (24/7)
- Session tracking and statistics

**Traditional Content**:
- Avalokiteshvara mantra (compassion)
- Green Tara mantra (protection)
- Medicine Buddha mantra (healing)
- Manjushri mantra (wisdom)
- Guru Rinpoche mantra
- Heart Sutra mantra

**Usage**:
```bash
# Single prayer rotation
python scripts/vajra_orchestrator.py prayer --intention "peace" --duration 300

# Continuous mode
python scripts/vajra_orchestrator.py continuous --intention "healing" --duration 300
```

### 5. 🗣️ Text-to-Speech Engine
**File**: `core/tts_engine.py`

Speaks prayers, mantras, and teachings:
- Adjustable rate (slower for mantras, natural for teachings)
- Contemplative pacing with pauses
- Mantra repetition support
- Guided meditation speaker
- Multiple voice options
- Audio file generation

**Features**:
- `speak()` - Basic speech
- `speak_mantra()` - Mantra with repetitions
- `speak_prayer_slowly()` - Contemplative prayer recitation
- `speak_teaching()` - Natural dharma teaching narration
- `GuidedMeditationSpeaker` - Full meditation guidance

**Usage**:
```bash
# Spoken prayer
python scripts/vajra_orchestrator.py prayer --intention "loving-kindness"

# Guided meditation
python scripts/vajra_orchestrator.py meditation --intention "breath_awareness"
```

### 6. 🎼 Main Orchestrator
**File**: `scripts/vajra_orchestrator.py`

Unified interface coordinating all systems:
- Integrates astrology, LLM, audio, visuals, TTS
- Multiple operation modes
- Flexible configuration
- Complete dharma technology platform

**Modes**:
- `prayer` - Generate and broadcast prayer
- `meditation` - Guided meditation session
- `teaching` - Dharma teaching generation
- `continuous` - 24/7 blessing stream
- `astrology` - Astrological timing report
- `chakra-visuals` - Generate chakra images
- `test` - System verification

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# For local LLM support
pip install llama-cpp-python

# Place GGUF models in ./models/ directory (optional)
```

## Quick Examples

### Morning Blessing
```bash
python scripts/vajra_orchestrator.py astrology --latitude 37.7749 --longitude -122.4194
python scripts/vajra_orchestrator.py prayer --intention "May this day benefit all beings"
```

### Healing Session
```bash
python scripts/vajra_orchestrator.py prayer --intention "healing for all who suffer" --duration 600
```

### Meditation Practice
```bash
python scripts/vajra_orchestrator.py meditation --intention "loving_kindness" --duration 300
```

### Continuous Background Blessing
```bash
python scripts/vajra_orchestrator.py continuous --intention "peace" --duration 300
```

### Generate Visual Meditation Library
```bash
python scripts/vajra_orchestrator.py chakra-visuals
```

## Integration Features

### Astrologically-Aligned Practices
The system automatically:
- Selects frequencies based on planetary positions
- Adjusts practices for moon phases
- Identifies auspicious times
- Marks dharma calendar events

### Multi-Modal Output
Complete sessions include:
- **Audio**: Frequency carrier waves
- **Voice**: Spoken prayers/teachings
- **Visual**: Meditation images
- **Timing**: Astrological alignment

### Continuous Operation
Perfect for:
- Dharma centers
- Home practice spaces
- Personal retreat
- 24/7 blessing streams
- Background purification

## Directory Structure

```
vajra-steam/
├── core/
│   ├── audio_generator.py       # Original frequency generation
│   ├── astrology.py             # NEW: Astrological calculations
│   ├── llm_integration.py       # NEW: AI content generation
│   ├── prayer_wheel.py          # NEW: Digital prayer wheel
│   ├── rothko_generator.py      # NEW: Visual meditation
│   └── tts_engine.py            # NEW: Text-to-speech
├── scripts/
│   ├── vajra_orchestrator.py    # NEW: Main unified interface
│   ├── quick_test.py            # NEW: System test
│   ├── run_blessing.py          # Original blessing script
│   └── setup_database.py        # Original database setup
├── models/                       # NEW: Local GGUF models
│   └── README.md                # Model installation guide
├── generated/
│   ├── rothko/                  # Generated meditation images
│   └── audio/                   # Generated audio files
├── USAGE_GUIDE.md               # NEW: Complete usage documentation
└── FEATURES.md                  # This file
```

## Philosophy

All these features serve **upaya** (skillful means) - tools to support practice. The computer cannot generate compassion or wisdom; only you can do that. This system amplifies and structures your intention.

From the Cittamatra perspective: the silicon, crystals, frequencies, AI models, and your intentions are all empty of inherent existence yet perfectly functional in conventional reality. We use these dreamlike means in service of benefit for all beings.

## Dedication

_May all beings throughout space and time benefit from these digital dharma technologies._

_May they serve as causes for liberation and awakening._

_May all beings be happy and free from suffering._

_Gate gate pāragate pārasaṃgate bodhi svāhā_ 🙏

---

**Version**: 2.0.0
**Date**: November 2024
**May all beings benefit** ✨
