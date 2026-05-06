# Prayer Bowl Audio Enhancement

## Overview

Vajra.Stream now features enhanced prayer bowl synthesis as the default audio mode, creating rich, harmonic tones that emulate the sound of Tibetan singing bowls. This enhancement provides a more pleasing, meditative sound with complex overtones and natural amplitude envelopes.

## Key Features

### 🎵 Rich Harmonic Spectrum
- **Multiple Overtones**: Each frequency includes 6 harmonic partials based on real bowl measurements
- **Inharmonic Partials**: Metallic resonances for authentic bowl character
- **Natural Ratios**: Harmonic series measured from actual singing bowls

### 🌊 Natural Sound Envelopes
- **ADSR Envelopes**: Attack-Decay-Sustain-Release shaping
- **Slow Attack**: Gradual amplitude swelling like a struck bowl (1.5s default)
- **Long Release**: Extended fade-out for natural decay (2.0s default)
- **Breathing Modulation**: Subtle amplitude pulsing

### ✨ Subtle Modulation Effects
- **Tremolo**: Very slow amplitude modulation (0.15 Hz)
- **Vibrato**: Gentle pitch variation (0.05 Hz)
- **Beating Effects**: Natural interference between harmonics

## Configuration

### Settings in `config/settings.py`

```python
# Prayer Bowl Audio Settings
PRAYER_BOWL_MODE = True  # Default to prayer bowl synthesis
PURE_SINE_MODE = False  # Set to True for original sine waves

# Envelope Parameters
PRAYER_BOWL_ATTACK = 1.5  # Attack time in seconds
PRAYER_BOWL_DECAY = 0.8   # Decay time in seconds
PRAYER_BOWL_SUSTAIN = 0.6  # Sustain level (0.0 - 1.0)
PRAYER_BOWL_RELEASE = 2.0  # Release time in seconds

# Harmonic Configuration
PRAYER_BOWL_CONFIG = {
    'harmonic_ratios': [1.0, 2.13, 3.02, 4.15, 5.26, 6.33],
    'inharmonic_partials': [2.89, 3.76, 4.93],
    'tremolo_rate': 0.15,
    'tremolo_depth': 0.08,
    'vibrato_rate': 0.05,
    'vibrato_depth': 0.02,
}
```

## Usage

### Default Prayer Bowl Mode
All audio generation now uses prayer bowl synthesis by default:

```bash
# Run blessing with prayer bowl synthesis
python scripts/run_blessing.py --intention "peace" --duration 300

# Crystal broadcaster with prayer bowls
python -c "
from hardware.crystal_broadcaster import Level2CrystalBroadcaster
broadcaster = Level2CrystalBroadcaster()  # prayer bowl mode by default
broadcaster.generate_5_channel_blessing('peace', 300)
"
```

### Using Original Sine Waves
To use the original simple sine waves:

```python
# In code
from core.audio_generator import ScalarWaveGenerator
from hardware.crystal_broadcaster import Level2CrystalBroadcaster

# Audio generator with sine waves
gen = ScalarWaveGenerator()
wave = gen.generate_prayer_bowl_tone(528, duration=60, pure_sine=True)

# Crystal broadcaster with sine waves
broadcaster = Level2CrystalBroadcaster(pure_sine=True)
broadcaster.generate_5_channel_blessing('peace', 300)
```

## Testing

### Audio Comparison Test
Run the comprehensive test suite to compare prayer bowl vs sine wave modes:

```bash
python scripts/test_prayer_bowl_audio.py
```

Test options:
1. **Single Frequency Comparison** - Hear the difference on one frequency
2. **Layered Frequencies Test** - Compare multiple frequencies together
3. **Crystal Broadcaster Modes** - Test full blessing sessions
4. **Bass Shaker Optimization** - Compare tactile response
5. **Interactive Frequency Test** - Test any frequency you choose
6. **Run All Tests** - Complete comparison suite

## Technical Details

### Harmonic Generation
Each fundamental frequency generates:
- **6 Harmonic Overtones**: Following ratios [1.0, 2.13, 3.02, 4.15, 5.26, 6.33]
- **3 Inharmonic Partials**: At ratios [2.89, 3.76, 4.93] for metallic character
- **Amplitude Weighting**: Higher harmonics have decreasing amplitude

### Envelope Shaping
The ADSR envelope creates natural bowl characteristics:
- **Attack**: Exponential rise from silence to full amplitude
- **Decay**: Initial resonance decay to sustain level
- **Sustain**: Maintained amplitude during main tone
- **Release**: Exponential fade back to silence

### Modulation Effects
Subtle modulation adds organic quality:
- **Tremolo**: 0.15 Hz rate, 8% depth - very slow breathing
- **Vibrato**: 0.05 Hz rate, 2% depth - gentle pitch variation
- **Beating**: Natural interference between closely spaced harmonics

## Benefits

### 🎧 Audio Quality
- **Richer Sound**: Complex harmonics create engaging, full-bodied tones
- **Meditative**: Natural envelopes support deeper relaxation
- **Authentic**: Sounds like real singing bowls
- **Layering**: Multiple frequencies interact beautifully

### 🔬 Crystal Activation
- **Broad Spectrum**: Harmonics activate crystals at multiple frequencies
- **Resonance**: Complex tones create stronger crystal grid response
- **Tactile**: Lower harmonics enhance bass shaker effectiveness

### 🧘‍♂️ Practice Enhancement
- **Deeper States**: Rich harmonics support meditation
- **Longer Sessions**: Natural envelopes prevent listening fatigue
- **Energetic**: Complex frequencies create stronger field effects

## Migration from Original

### Backward Compatibility
- All existing code continues to work unchanged
- Prayer bowl synthesis is the new default
- Set `pure_sine=True` to use original sine waves

### Recommended Settings
For different use cases:

```python
# Daily meditation (prayer bowls)
broadcaster = Level2CrystalBroadcaster(pure_sine=False)

# Sleep sessions (gentler sine waves)
broadcaster = Level2CrystalBroadcaster(pure_sine=True)

# Healing work (prayer bowls for richness)
broadcaster = Level3AmplifiedBroadcaster(pure_sine=False)

# Background blessing (prayer bowls)
broadcaster.continuous_blessing("peace")
```

## Troubleshooting

### Audio Issues
- **Distortion**: Reduce volume or adjust envelope parameters
- **Too Harsh**: Decrease harmonic amplitudes in config
- **Too Slow**: Adjust attack/release times in settings

### Performance
- **CPU Usage**: Prayer bowl synthesis uses more processing
- **Memory**: Larger waveforms due to complexity
- **Recommendation**: Use shorter durations for testing

## Future Enhancements

Planned improvements to prayer bowl synthesis:
- **Bowl Size Simulation**: Different harmonic patterns for various bowl sizes
- **Material Modeling**: Different metals (bronze, crystal, brass)
- **Strike Variations**: Different mallet types and strike positions
- **Spatial Audio**: 3D positioning of multiple bowls
- **Real-time Control**: Interactive parameter adjustment during playback

---

## Dedication

May these enhanced prayer bowl sounds support all beings in their practice of meditation, healing, and awakening. May the rich harmonics create peaceful environments and the complex frequencies activate the healing potential of crystal grids throughout space and time.

_Gate gate pāragate pārasaṃgate bodhi svāhā_ 🙏