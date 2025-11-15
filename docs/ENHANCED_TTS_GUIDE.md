# 🔊 Enhanced TTS System Guide

## Overview

The Enhanced TTS Engine provides a unified interface for multiple text-to-speech providers, with automatic fallback and smart provider selection. Supports both cloud APIs and local open-source solutions.

## Architecture

```
EnhancedTTSEngine
├── Cloud Providers (API-based)
│   ├── OpenAI TTS (tts-1, tts-1-hd)
│   ├── ElevenLabs (premium natural voices)
│   ├── Azure Cognitive Services
│   └── Google Cloud TTS
├── Local Open-Source
│   ├── Coqui TTS (Mozilla TTS continuation)
│   └── Piper (fast, Raspberry Pi optimized)
└── Fallback
    └── pyttsx3 (basic offline TTS)
```

## Provider Selection

The engine automatically selects the best available provider based on:

1. **Availability**: API keys configured, packages installed
2. **Preference**: Local vs. cloud (configurable)
3. **Priority order**: Quality and performance balance

### Default Priority (Cloud-First)
1. OpenAI TTS → Best balance of quality and simplicity
2. ElevenLabs → Highest quality, most natural
3. Azure TTS → Enterprise-grade
4. Google Cloud TTS → Wide language support
5. Coqui TTS → Best local quality
6. Piper → Fast local fallback
7. pyttsx3 → Always-available fallback

### Local-First Priority
1. Coqui TTS
2. Piper
3. Cloud providers (fallback)

## Installation

### Base Installation
```bash
pip install numpy pyttsx3
```

### Cloud Provider Setup

#### OpenAI TTS
```bash
pip install openai

# Set API key
export OPENAI_API_KEY="your-key-here"
```

**Voices**: alloy, echo, fable, onyx, nova, shimmer
**Models**: `tts-1` (fast), `tts-1-hd` (high quality)
**Cost**: ~$15/million characters

#### ElevenLabs
```bash
pip install elevenlabs

# Set API key
export ELEVENLABS_API_KEY="your-key-here"
```

**Voices**: Bella, Antoni, Elli, Rachel, Domi, and more
**Quality**: Premium, very natural-sounding
**Cost**: Subscription-based

#### Azure Cognitive Services
```bash
pip install azure-cognitiveservices-speech

# Set credentials
export AZURE_SPEECH_KEY="your-key"
export AZURE_SPEECH_REGION="eastus"
```

**Voices**: en-US-JennyNeural, en-US-GuyNeural, 400+ voices
**Features**: SSML support, custom neural voices
**Cost**: Pay-as-you-go

#### Google Cloud TTS
```bash
pip install google-cloud-texttospeech

# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

**Voices**: Wavenet, Neural2, Standard voices
**Languages**: 380+ voices in 50+ languages
**Cost**: $4-16/million characters

### Local Open-Source Setup

#### Coqui TTS (Recommended Local)
```bash
pip install TTS

# First run downloads models (~500MB)
```

**Quality**: Very good, comparable to cloud
**Speed**: Medium (depends on model)
**Models**: Many pre-trained models available
**Offline**: Fully offline after model download

#### Piper (Fast Local)
```bash
# Install piper binary
# Ubuntu/Debian:
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
tar -xzf piper_amd64.tar.gz
sudo mv piper /usr/local/bin/

# Download models
mkdir -p ~/.local/share/piper/models
cd ~/.local/share/piper/models
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/voice-en-us-libritts-high.tar.gz
tar -xzf voice-en-us-libritts-high.tar.gz
```

**Quality**: Good
**Speed**: Very fast, optimized for Raspberry Pi
**Size**: Small models (~50-100MB)
**Offline**: Fully offline

## Usage

### Basic Usage

```python
from core.enhanced_tts import EnhancedTTSEngine

# Initialize (automatic provider selection)
tts = EnhancedTTSEngine()

# Speak text
tts.speak("Om Mani Padme Hum. May all beings be happy.")

# Check which provider is active
print(f"Using: {tts.get_current_provider()}")
```

### Prefer Local TTS

```python
# Initialize with local preference
tts = EnhancedTTSEngine(prefer_local=True)

# Will try Coqui → Piper → Cloud → pyttsx3
tts.speak("Running on local TTS")
```

### Manual Provider Selection

```python
tts = EnhancedTTSEngine()

# List available providers
for provider in tts.list_available_providers():
    print(f"{provider['name']}: {provider['available']}")

# Switch to specific provider
tts.set_provider("OpenAI TTS")
tts.speak("Using OpenAI TTS")
```

### Contemplative Speech (Prayers)

```python
tts = EnhancedTTSEngine()

# Speak slowly with pauses between sentences
prayer = """
May all beings be happy.
May all beings be healthy.
May all beings be at peace.
"""

tts.speak_slowly(prayer, pause_duration=2.0)
```

### Mantra Repetition

```python
tts = EnhancedTTSEngine()

# Repeat mantra 108 times
tts.speak_mantra(
    "Om Mani Padme Hum",
    repetitions=108,
    pause_duration=2.0
)
```

### Generate Audio Files

```python
tts = EnhancedTTSEngine()

# Generate and save audio
tts.generate_audio_file(
    text="Gate gate pāragate pārasaṃgate bodhi svāhā",
    output_path="output/heart_sutra_mantra.mp3"
)
```

### Provider-Specific Options

#### OpenAI TTS
```python
tts.set_provider("OpenAI TTS")

# Use different voice and model
tts.speak(
    "May all beings be free from suffering",
    voice="nova",      # alloy, echo, fable, onyx, nova, shimmer
    model="tts-1-hd"   # tts-1 or tts-1-hd
)
```

#### ElevenLabs
```python
tts.set_provider("ElevenLabs")

# Use specific voice
tts.speak(
    "Peace be upon all beings",
    voice="Bella"  # or Antoni, Elli, Rachel, etc.
)
```

#### Azure TTS
```python
tts.set_provider("Azure TTS")

# Use neural voice
tts.speak(
    "May compassion fill all hearts",
    voice="en-US-JennyNeural"
)
```

## Integration with Radionics Operations

### In radionics_operation.py

```python
from core.enhanced_tts import EnhancedTTSEngine

class RadionicsOperation:
    def __init__(self, prefer_local_tts: bool = False):
        # Initialize TTS
        self.tts = EnhancedTTSEngine(prefer_local=prefer_local_tts)

    def broadcast_with_voice(self, prayer_text: str):
        """Speak prayer during radionics operation"""

        # Generate audio file for continuous playback
        audio_path = "generated/prayer_audio.mp3"
        self.tts.generate_audio_file(prayer_text, audio_path)

        # Or speak directly
        self.tts.speak_slowly(prayer_text, pause_duration=2.0)
```

### In Prayer Wheel

```python
from core.enhanced_tts import EnhancedTTSEngine

class PrayerWheel:
    def __init__(self):
        self.tts = EnhancedTTSEngine()

    def spin_with_voice(self, mantra: str):
        """Spin prayer wheel while speaking mantra"""
        self.tts.speak_mantra(mantra, repetitions=108)
```

## Performance Comparison

| Provider | Quality | Speed | Offline | Cost | Best For |
|----------|---------|-------|---------|------|----------|
| OpenAI TTS | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | $ | Best balance |
| ElevenLabs | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | $$$ | Highest quality |
| Azure TTS | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | $$ | Enterprise |
| Google Cloud | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | $ | Many languages |
| Coqui TTS | ⭐⭐⭐ | ⭐⭐⭐ | ✅ | Free | Best local |
| Piper | ⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | Free | Fast local |
| pyttsx3 | ⭐ | ⭐⭐⭐ | ✅ | Free | Fallback |

## Recommendations

### For Radionics Operations
- **Cloud**: OpenAI TTS (best balance of quality and cost)
- **Local**: Coqui TTS (good quality, fully offline)
- **Hybrid**: Try cloud first, fallback to local if offline

### For 24/7 Broadcasting
- **Coqui TTS** or **Piper** (no API costs, always available)
- Pre-generate audio files to avoid repeated synthesis

### For High-Quality Recordings
- **ElevenLabs** (most natural, emotional depth)
- Good for guided meditations, teaching content

### For Multi-Language
- **Google Cloud TTS** (380+ voices in 50+ languages)
- Sanskrit, Tibetan, Chinese support

## Troubleshooting

### "No TTS provider available"
- At minimum, install pyttsx3: `pip install pyttsx3`
- Check API keys are set correctly
- Verify package installations

### "Provider not available" for specific provider
- Check error message: `tts.list_available_providers()`
- Install required package
- Set required environment variables

### Poor audio quality
- Try higher-quality provider (ElevenLabs, tts-1-hd)
- For local, use better Coqui models
- Check audio output device settings

### Slow generation
- Use OpenAI tts-1 (fast) instead of tts-1-hd
- Use Piper for fastest local
- Pre-generate audio files for reuse

### API costs too high
- Switch to local providers (Coqui or Piper)
- Pre-generate and cache common texts
- Use pyttsx3 for testing

## Future Enhancements

### Planned Features
- [ ] Voice cloning (Coqui TTS)
- [ ] SSML support for all providers
- [ ] Emotion/tone control
- [ ] Multi-voice dialogue
- [ ] Real-time streaming
- [ ] Language auto-detection
- [ ] Custom pronunciation dictionaries
- [ ] Batch processing optimization

### Potential Integrations
- Binaural beats during TTS playback
- Harmonic background frequencies
- Synchronized with visual animations
- Live WebSocket streaming to frontend

## Philosophy

The Enhanced TTS system embodies **upaya** (skillful means):

- **Technology as servant**: The system automatically handles complexity
- **Graceful degradation**: Always works, even offline or without API keys
- **Quality where it matters**: Premium options for important content
- **Freedom of choice**: Cloud, local, or hybrid approaches
- **Continuous practice**: Suitable for 24/7 operations

The voice is the vehicle; the intention is the driver.

## Quick Reference

```python
# Quick speak (automatic provider)
from core.enhanced_tts import speak
speak("Om Mani Padme Hum")

# Quick prayer (contemplative pacing)
from core.enhanced_tts import speak_prayer
speak_prayer("May all beings be happy and free from suffering")

# Quick mantra
from core.enhanced_tts import speak_mantra
speak_mantra("Om Tare Tuttare Ture Soha", repetitions=21)
```

---

**May these voices carry healing intentions to all beings.**
**Gate gate pāragate pārasaṃgate bodhi svāhā** 🙏
