# Vajra.Stream - Complete Usage Guide

## 🙏 Welcome

This guide covers all features of the Vajra.Stream digital dharma technology system.

## Quick Start

### 1. Installation

```bash
# Navigate to project
cd vajra-steam

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Basic Prayer Session

```bash
# Generate and broadcast a prayer (5 minutes)
python scripts/vajra_orchestrator.py prayer --intention "May all beings be happy"
```

## All Features Overview

### 1. Astrological Timing (Kalachakra)

View current astrological energetics and recommended frequencies:

```bash
# Show current astrology
python scripts/vajra_orchestrator.py astrology

# With your location (for sunrise/sunset times)
python scripts/vajra_orchestrator.py astrology --latitude 37.7749 --longitude -122.4194
```

Features:
- Planetary positions
- Moon phases and lunar mansions (Nakshatras)
- Auspicious times (Brahma Muhurta, sunrise, solar noon)
- Recommended frequencies based on current energetics
- Dharma calendar events

### 2. LLM Prayer Generation

The system can generate prayers using AI (both API and local models).

#### Using API Models

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-key-here"
# OR
export OPENAI_API_KEY="your-key-here"

# Generate prayer
python scripts/vajra_orchestrator.py prayer --intention "healing for all beings"
```

#### Using Local GGUF Models

1. Download a GGUF model (see `models/README.md`)
2. Place it in the `models/` directory
3. Run normally - will auto-detect:

```bash
python scripts/vajra_orchestrator.py prayer --intention "wisdom"
```

### 3. Prayer Wheel Interface

Digital prayer wheel that generates and broadcasts prayers continuously.

```bash
# Single prayer broadcast (5 minutes)
python scripts/vajra_orchestrator.py prayer --intention "peace" --duration 300

# Continuous mode (runs until Ctrl+C)
python scripts/vajra_orchestrator.py continuous --intention "compassion" --duration 300
```

Features:
- Traditional mantras and aspirations
- AI-generated prayers (if LLM enabled)
- Continuous rotation mode (24/7 blessing stream)
- Session tracking and statistics

### 4. Text-to-Speech (Spoken Prayers)

Speaks prayers, mantras, and teachings aloud.

```bash
# Prayer with voice
python scripts/vajra_orchestrator.py prayer --intention "loving-kindness" --duration 60
```

The system will:
- Generate a prayer
- Speak it aloud with appropriate pacing
- Broadcast carrier frequencies
- Display visual meditation aid

### 5. Mark Rothko Visual Meditation

Generates contemplative color field images for meditation.

```bash
# Generate chakra visualization series
python scripts/vajra_orchestrator.py chakra-visuals

# Generated with prayers automatically
python scripts/vajra_orchestrator.py prayer --intention "peace"
```

Images saved to: `generated/rothko/`

Themes:
- Compassion (pinks, reds)
- Wisdom (blues, purples)
- Peace (soft blues, greens)
- Awakening (golds, oranges)
- Emptiness (grays)
- Earth (browns, ochres)
- Transcendence (reds, blacks, golds)
- Rainbow Body (full spectrum)

### 6. Guided Meditation

AI-generated guided meditation sessions with voice and audio.

```bash
# Guided meditation (5 minutes)
python scripts/vajra_orchestrator.py meditation --intention "loving_kindness" --duration 300

# Other meditation types
python scripts/vajra_orchestrator.py meditation --intention "breath_awareness"
python scripts/vajra_orchestrator.py meditation --intention "vipassana"
python scripts/vajra_orchestrator.py meditation --intention "shamatha"
```

Includes:
- Introduction and settling
- Main practice instructions
- Closing and dedication
- Background binaural beats/frequencies

### 7. Dharma Teachings

Generate teachings on dharma topics.

```bash
# Generate teaching
python scripts/vajra_orchestrator.py teaching --intention "impermanence"
python scripts/vajra_orchestrator.py teaching --intention "compassion"
python scripts/vajra_orchestrator.py teaching --intention "emptiness"
```

Will generate a teaching and offer to speak it aloud.

### 8. Frequency Broadcasting

All modes include sacred frequency generation:
- 7.83 Hz - Schumann resonance (Earth)
- 136.1 Hz - OM frequency (Earth year)
- 528 Hz - "Love frequency" (DNA repair)
- 639 Hz - Connection/relationships
- 741 Hz - Awakening/intuition

Frequencies are automatically selected based on:
- Intention/practice
- Current astrological conditions
- Moon phase and planetary positions

## Complete Session Examples

### Morning Practice

```bash
# Check auspicious times for your location
python scripts/vajra_orchestrator.py astrology \
  --latitude 37.7749 --longitude -122.4194

# Generate morning aspiration
python scripts/vajra_orchestrator.py prayer \
  --intention "May this day benefit all beings" \
  --duration 300
```

### Healing Session

```bash
# 10-minute healing session
python scripts/vajra_orchestrator.py prayer \
  --intention "healing for all who suffer" \
  --duration 600
```

### Continuous Background Blessing (24/7 Mode)

```bash
# Run continuously, generating new prayer every 5 minutes
python scripts/vajra_orchestrator.py continuous \
  --intention "peace for all beings" \
  --duration 300
```

### Full Moon Practice

```bash
# Check if it's full moon
python scripts/vajra_orchestrator.py astrology

# Special full moon dedication
python scripts/vajra_orchestrator.py prayer \
  --intention "Dedicating merit on this full moon to all beings" \
  --duration 900
```

## Configuration Options

All modes support these flags:

```bash
--no-audio      # Disable frequency generation
--no-llm        # Use traditional prayers only (no AI generation)
--no-tts        # Disable voice/speech
--no-visuals    # Disable Rothko image generation
--duration N    # Duration in seconds
```

Examples:

```bash
# Silent mode (no audio)
python scripts/vajra_orchestrator.py prayer --intention "peace" --no-audio

# Traditional prayers only (no AI)
python scripts/vajra_orchestrator.py prayer --intention "compassion" --no-llm

# Just frequencies, no voice
python scripts/vajra_orchestrator.py prayer --intention "healing" --no-tts
```

## Hardware Integration

### Level 2: Passive Crystal Grid

1. Arrange 6 quartz crystals in hexagon
2. Place in front of speakers
3. Run blessing:

```bash
python scripts/vajra_orchestrator.py prayer --intention "Your intention" --duration 300
```

### Level 3: Amplified (Bass Shaker)

1. Connect amplifier and bass shaker
2. Set volume to 25-40%
3. Run with amplified frequencies

See original `README.md` for hardware setup details.

## Advanced Usage

### Testing All Systems

```bash
python scripts/vajra_orchestrator.py test
```

This will:
- Show astrological report
- Generate chakra visualizations
- Test prayer generation
- Verify all systems working

### Generate Content Library

```bash
# Create chakra series
python scripts/vajra_orchestrator.py chakra-visuals

# Generate multiple prayers
for intent in peace wisdom healing compassion; do
  python scripts/vajra_orchestrator.py prayer --intention "$intent" --duration 60
done
```

## File Locations

- **Generated Images**: `generated/rothko/`
- **Audio Files**: `generated/audio/`
- **Session Logs**: `logs/`
- **Local Models**: `models/` (place GGUF files here)

## Environment Variables

```bash
# For Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# For OpenAI
export OPENAI_API_KEY="sk-..."

# System will try local models first, then fall back to API
```

## Troubleshooting

### No LLM Available
- Add GGUF model to `models/` directory
- OR set ANTHROPIC_API_KEY or OPENAI_API_KEY
- OR use `--no-llm` flag for traditional prayers only

### Audio Not Working
- Check `sounddevice` installation: `pip install sounddevice`
- List audio devices: `python -c "import sounddevice; print(sounddevice.query_devices())"`
- Use `--no-audio` flag to disable

### TTS Not Working
- May not work in headless environments
- Use `--no-tts` flag to disable voice
- Install system TTS: `sudo apt-get install espeak` (Linux)

### Out of Memory (Local LLM)
- Download a smaller model (3B instead of 7B)
- Use more compressed quantization (Q4 instead of Q6)
- Fall back to API: set ANTHROPIC_API_KEY

## Philosophy of Use

This technology is **upaya** (skillful means). The computer doesn't generate compassion or wisdom - you do. This system:

- Amplifies and structures your intention
- Provides continuous support for practice
- Makes dharma accessible through modern means
- Serves all beings without discrimination

From the Cittamatra view: all of this is mind - empty yet functional. We work with conventional reality while maintaining ultimate view.

## Dedication

_May all merit arising from this practice flow to all beings._

_May all beings be happy and free from suffering._

_May all beings awaken to their true nature._

_Gate gate pāragate pārasaṃgate bodhi svāhā_ 🙏

---

For more details see:
- `README.md` - Project overview
- `models/README.md` - Local LLM setup
- `START_HERE.md` - Quick start guide
