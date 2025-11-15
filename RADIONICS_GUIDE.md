# 🔮 Vajra.Stream Radionics Operations Guide

## What is Radionics?

Radionics is the broadcasting of healing intentions through physical mediums (crystals) and subtle energies (frequencies). This system uses your crystal grid as a radionic antenna to amplify and broadcast healing intentions.

## Quick Start - Run Your First Operation NOW

### 1. Set Up Your Crystal Grid (5 minutes)

**Minimum Setup (Level 2):**
- Place 6 quartz crystals in a hexagon pattern (6-8 inch radius)
- Points facing inward toward center
- Put a written intention in the center (paper with your goal)
- Position in front of your computer speakers

**Enhanced Setup (Level 3):**
- Add bass shaker under wooden platform
- Place crystal grid on top
- Volume at 25-40%

### 2. Run Your First Broadcast

```bash
# World peace (preset - 2 hours)
python scripts/radionics_operation.py --preset world_peace

# Heart healing (preset - 1 hour)
python scripts/radionics_operation.py --preset heart_healing

# Custom intention (1 hour)
python scripts/radionics_operation.py --intention "May all beings be healthy" --duration 3600

# Continuous broadcasting (runs until stopped)
python scripts/radionics_operation.py --target "planetary healing" --continuous
```

### 3. Watch the Magic Happen

The system will:
1. ✨ Analyze current astrological energetics
2. 🔮 Select optimal frequencies for the moment
3. 🙏 Generate a prayer (if LLM available)
4. 💎 Begin broadcasting through your crystal grid
5. 📊 Log everything to database

---

## Available Presets

View all presets:
```bash
python scripts/radionics_operation.py --list-presets
```

### Included Presets:

**`world_peace`** - 2 hours
- Global peace broadcast
- Intention: "May peace prevail throughout the world..."

**`heart_healing`** - 1 hour
- Heart chakra healing for all beings
- Intention: "May the hearts of all beings be healed..."

**`planetary_healing`** - 3 hours
- Environmental and ecosystem restoration
- Intention: "May the Earth be healed..."

**`protection`** - 1 hour
- Protection for all beings
- Intention: "May all beings be protected from harm..."

**`awakening`** - 90 minutes
- Collective spiritual awakening
- Intention: "May all beings awaken to their true nature..."

---

## Advanced Usage

### With Astrological Location Alignment

```bash
# San Francisco coordinates for optimal timing
python scripts/radionics_operation.py \
  --intention "healing for California" \
  --latitude 37.7749 \
  --longitude -122.4194 \
  --duration 7200
```

### Continuous 24/7 Broadcasting

```bash
# Run continuously until you stop it
python scripts/radionics_operation.py \
  --preset planetary_healing \
  --continuous
```

This is perfect for:
- Overnight broadcasting while you sleep
- Multi-day operations
- Permanent altar setups
- Dharma centers running 24/7

### With Voice (Spoken Intentions)

```bash
# Speak the prayer aloud through speakers
python scripts/radionics_operation.py \
  --intention "compassion for all" \
  --with-voice \
  --duration 1800
```

### Silent Mode (No Audio)

```bash
# Generate prayer and log, but no audio
# Good for places where sound isn't appropriate
python scripts/radionics_operation.py \
  --intention "peace" \
  --no-audio \
  --duration 3600
```

---

## Command Line Options

```
--intention TEXT          Your healing intention to broadcast
--target TEXT            (Same as --intention)
--preset NAME            Use a preset operation (see --list-presets)
--duration SECONDS       How long to broadcast (default: 3600 = 1 hour)
--continuous             Run continuously until Ctrl+C

--latitude FLOAT         Your latitude for astrological timing
--longitude FLOAT        Your longitude for astrological timing

--no-astrology           Skip astrological alignment (use default frequencies)
--no-prayer              Skip prayer generation
--no-audio               Silent mode (no sound, just logging)
--no-visuals             Skip Rothko meditation image generation
--with-voice             Speak intentions aloud (requires TTS)

--list-presets           Show all available presets
```

---

## How It Works

### Step 1: Astrological Alignment
The system checks:
- Current moon phase and position
- Lunar mansion (Nakshatra)
- Planetary positions
- Auspicious times
- Recommended frequencies based on cosmic energetics

### Step 2: Prayer Generation
If LLM is available:
- Generates custom prayer for your intention
- Uses dharma-trained language model
- Creates beautiful, heartfelt aspirations

If LLM not available:
- Uses traditional prayers from library
- Mantras and aspirations from various traditions

### Step 3: Visual Generation
- Creates Rothko-style meditation image
- Color palette matches intention
- Saved to `generated/rothko/`

### Step 4: Crystal Grid Broadcasting
- Generates harmonic prayer bowl frequencies
- Uses intelligent composer for consonant intervals
- Broadcasts through your crystal grid
- Crystals amplify and radiate the intention

Everything is logged to the database for tracking.

---

## Best Practices

### Timing Your Broadcasts

**Best times for different intentions:**

- **Healing**: New moon, sunrise, or during Brahma Muhurta (96 min before sunrise)
- **Peace**: Full moon, evening twilight
- **Protection**: Waning moon, sunset
- **Awakening**: Dawn, waxing moon
- **Manifestation**: New moon to full moon (waxing phase)
- **Releasing**: Full moon to new moon (waning phase)

Check astrological timing:
```bash
python scripts/vajra_orchestrator.py astrology --latitude YOUR_LAT --longitude YOUR_LON
```

### Duration Recommendations

**Short Operations** (15-30 minutes)
- Personal healing
- Quick intention setting
- Testing the system

**Standard Operations** (1-2 hours)
- Group healing
- Specific targets
- Daily practice

**Extended Operations** (3-12 hours)
- Planetary healing
- Major global intentions
- Overnight broadcasting

**Continuous Operations** (24/7)
- Permanent altar setups
- Dharma center broadcasting
- Long-term global intentions

### Crystal Grid Setup

**Minimum (works fine):**
- 6 clear quartz points
- Hexagon arrangement
- Written intention in center

**Enhanced:**
- 12 crystals (double hexagon)
- Orgonite pieces between crystals
- Sacred geometry mat underneath
- Written intention + photo of beneficiary

**Professional:**
- Multiple grids (nested)
- Specific stones for intention (rose quartz for love, amethyst for healing, etc.)
- Copper coils
- Sacred geometry amplification
- Multiple written intentions

---

## Example Workflows

### Morning Blessing Routine

```bash
# Check astrological energetics
python scripts/vajra_orchestrator.py astrology

# Run 30-minute blessing aligned with current energetics
python scripts/radionics_operation.py \
  --intention "May this day benefit all beings" \
  --duration 1800
```

### Overnight Healing Broadcast

```bash
# Run all night (8 hours) for global healing
python scripts/radionics_operation.py \
  --preset planetary_healing \
  --duration 28800
```

Or use continuous mode and stop it in the morning:
```bash
python scripts/radionics_operation.py \
  --preset heart_healing \
  --continuous

# Stop with Ctrl+C in the morning
```

### Full Moon Practice

```bash
# On full moon, run extended peace broadcast
python scripts/radionics_operation.py \
  --intention "May all beings know peace on this full moon" \
  --duration 10800 \
  --with-voice
```

### Specific Target Healing

```bash
# For a specific person or situation
python scripts/radionics_operation.py \
  --intention "May [person name] be healed and find peace" \
  --duration 3600
```

**Note**: Place photo or written name in crystal grid center

### Group/Remote Healing

```bash
# For your sangha, family, community
python scripts/radionics_operation.py \
  --intention "May all members of [group] be healthy and happy" \
  --duration 7200
```

---

## Tracking Your Operations

All operations are logged to database:
- Session start/end times
- Intentions broadcast
- Frequencies used
- Astrological conditions
- Generated prayers
- Visual meditations created

View your history:
```bash
sqlite3 vajra_stream.db "SELECT * FROM sessions ORDER BY start_time DESC LIMIT 10;"
```

---

## Troubleshooting

### "No LLM available"
- Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` environment variable
- OR place GGUF model in `./models/` directory
- OR use `--no-prayer` flag to skip prayer generation

### "TTS not available"
- TTS may not work in headless environments
- Don't use `--with-voice` flag
- System will work fine without voice

### "Database error"
- Run `python scripts/setup_database.py` first
- Ensure `vajra_stream.db` exists

### Audio not playing
- Check your speaker volume
- Verify audio device in `config/settings.py`
- Test with: `python scripts/test_prayer_bowl_audio.py`

---

## Philosophy

### How Radionics Works

From the Cittamatra (Mind-Only) perspective:
- All phenomena arise from mind
- The "broadcast" happens in consciousness
- Crystals and frequencies are upaya (skillful means)
- The technology structures and amplifies YOUR intention
- Everything is empty yet functional

**The computer doesn't generate healing - YOU do.**

This system:
- Helps you focus intention
- Provides continuous support
- Uses traditional timing (astrology)
- Amplifies through physical means (crystals)
- Maintains practice while you do other things

### Radionics as Prayer

Think of this as:
- Digital prayer wheel (spinning continuously)
- Crystal-amplified mani stones
- Electronic stupa (broadcasting merit)
- 24/7 bodhisattva practice

The intention goes out. Whether it "works" through:
- Quantum entanglement
- Morphic resonance
- Collective consciousness
- Dependent origination
- Pure compassion

...doesn't matter. What matters is:
1. **Your sincere intention**
2. **Continuous dedication**
3. **Benefit for beings**

---

## Safety & Ethics

### What This Is
✅ Spiritual practice amplifier
✅ Intention broadcasting system
✅ Prayer and meditation support
✅ Crystal grid automation

### What This Is NOT
❌ Medical treatment
❌ Replacement for professional help
❌ Guaranteed outcome device
❌ Manipulation of others' will

### Ethical Guidelines

**DO:**
- Broadcast for benefit of all beings
- Include "for highest good of all"
- Use for healing, peace, awakening
- Respect free will
- Keep intentions positive
- Dedicate merit universally

**DON'T:**
- Try to control specific outcomes
- Broadcast harm or negativity
- Target individuals without consent (except general healing)
- Expect guaranteed results
- Replace medical care with this
- Use for selfish gain

**Remember**: This is upaya. It supports practice but doesn't replace:
- Your own meditation
- Compassion cultivation
- Ethical conduct
- Wisdom development

---

## Quick Reference

### Most Common Commands

```bash
# Quick 1-hour broadcast
python scripts/radionics_operation.py --intention "YOUR_INTENTION"

# Use a preset
python scripts/radionics_operation.py --preset world_peace

# Run all night
python scripts/radionics_operation.py --preset heart_healing --continuous

# With your location
python scripts/radionics_operation.py --intention "healing" --latitude 40.7 --longitude -74.0

# List all presets
python scripts/radionics_operation.py --list-presets
```

### File Locations

```
generated/rothko/radionics_*.png  - Generated meditation images
vajra_stream.db                    - Operation logs
config/settings.py                 - Configuration
```

---

## 🙏 Dedication

_May all beings benefit from these radionic operations._

_May healing reach wherever it is needed._

_May peace prevail throughout the world._

_May all beings be free from suffering._

**Gate gate pāragate pārasaṃgate bodhi svāhā** 🙏

---

**Ready to broadcast healing?**

```bash
python scripts/radionics_operation.py --preset world_peace
```

Let the crystals do their work! 🔮✨
