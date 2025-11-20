# TTS Integration System - Specification

**Voice for the Voiceless: Text-to-Speech for Spiritual Practice**

---

## Vision

Create a comprehensive TTS (Text-to-Speech) system that gives voice to:
- **Blessing narratives** - Stories of liberation read aloud
- **Mantras** - Sacred syllables properly pronounced
- **Guided meditations** - Step-by-step practice instructions
- **Historical commemorations** - Spoken remembrance
- **Radionics intentions** - Verbal broadcasting
- **Educational content** - Teaching materials

The system should support:
- Multiple TTS engines (online and offline)
- Multiple languages
- Multiple voices (male, female, neutral)
- Emotion and pacing control
- Integration with all vajra-stream systems
- High-quality audio export

---

## TTS Engine Options

### 1. **pyttsx3** (Offline, Free)
**Pros:**
- Works offline
- Cross-platform (Windows, macOS, Linux)
- No API keys needed
- Fast generation
- Multiple voices available

**Cons:**
- Robotic quality (depends on system voices)
- Limited emotion control
- Voice quality varies by OS

**Best For:**
- Quick prototyping
- Offline operation
- Privacy-sensitive content

### 2. **gTTS** (Google Text-to-Speech, Online, Free)
**Pros:**
- Good quality
- Free (with rate limits)
- Many languages
- Easy to use
- No API key needed

**Cons:**
- Requires internet
- Rate limited
- Less control over voice characteristics
- No real-time generation

**Best For:**
- High-quality narration
- Multi-language content
- Non-real-time generation

### 3. **edge-tts** (Microsoft Edge TTS, Online, Free)
**Pros:**
- Excellent quality (neural voices)
- Free
- Many voices and languages
- Emotion/style control
- No API key needed

**Cons:**
- Requires internet
- Unofficial API (could change)
- Rate limits possible

**Best For:**
- High-quality production
- Natural-sounding speech
- Varied voice characteristics

### 4. **Amazon Polly** (Commercial, High Quality)
**Pros:**
- Excellent quality (neural voices)
- SSML support (prosody, pauses, emphasis)
- Many voices and languages
- Reliable API
- Emotion and speaking style control

**Cons:**
- Costs money (pay per character)
- Requires AWS account and API key
- Requires internet

**Best For:**
- Professional production
- Complex prosody needs
- Commercial projects

### 5. **Google Cloud TTS** (Commercial, High Quality)
**Pros:**
- Excellent quality (WaveNet/Neural2 voices)
- Many voices and languages
- SSML support
- Reliable

**Cons:**
- Costs money
- Requires API key
- Requires internet

**Best For:**
- Professional production
- High-quality narration
- Commercial projects

### 6. **Coqui TTS** (Open Source, Self-Hosted)
**Pros:**
- Open source
- Can run locally
- Voice cloning capability
- No usage limits
- High quality possible

**Cons:**
- Requires setup
- GPU recommended for quality
- More complex to use

**Best For:**
- Custom voice creation
- Privacy-critical applications
- Unlimited generation needs

---

## Recommended Stack

### Tier 1: Basic (Free, Offline)
- **Primary**: pyttsx3 (offline)
- **Fallback**: gTTS (online, free)

### Tier 2: Enhanced (Free, Online)
- **Primary**: edge-tts (high quality, free)
- **Fallback**: gTTS
- **Offline**: pyttsx3

### Tier 3: Professional (Paid)
- **Primary**: Amazon Polly or Google Cloud TTS
- **Fallback**: edge-tts
- **Offline**: pyttsx3

**Implementation Strategy**: Support all engines, allow user to choose preferred + fallback chain.

---

## Use Cases and Requirements

### 1. Blessing Story Narration

**Input**: GeneratedStory object from blessing_narratives
**Output**: Audio file (MP3/WAV) of complete story
**Duration**: 3-10 minutes typical
**Voice**: Warm, compassionate, clear
**Pacing**: Slow, meditative (100-120 WPM)
**Special**: Pause at section breaks, emphasize dedications

**Example**:
```python
narrator = TTSNarrator(engine='edge-tts', voice='compassionate_female')
audio = narrator.narrate_story(
    story=story,
    output_file='liberation_story.mp3',
    pace='slow',
    add_music=True,  # Optional background
    add_pauses=True   # Pause between sections
)
```

### 2. Mantra Repetition

**Input**: Mantra text (e.g., "Om Mani Padme Hum")
**Output**: Audio of mantra repeated N times
**Duration**: Variable (1-60 minutes)
**Voice**: Clear, reverent, steady
**Pacing**: Moderate, rhythmic
**Special**: Consistent rhythm, optional bell between repetitions

**Example**:
```python
narrator.generate_mantra_audio(
    mantra="Om Mani Padme Hum",
    repetitions=108,
    voice='neutral_calm',
    add_bell=True,
    bell_interval=21  # Every 21st repetition
)
```

### 3. Guided Meditation

**Input**: Meditation script with cues
**Output**: Guided meditation audio
**Duration**: 5-60 minutes
**Voice**: Soothing, gentle, guiding
**Pacing**: Very slow (80-100 WPM)
**Special**: Long pauses, breathing cues, gentle tone

**Example**:
```python
meditation_script = """
Begin by finding a comfortable seated position.
[PAUSE:5]
Gently close your eyes.
[PAUSE:3]
Take a deep breath in...
[PAUSE:2]
And slowly exhale.
[PAUSE:3]
"""

narrator.guided_meditation(
    script=meditation_script,
    voice='meditation_guide',
    background_sound='tibetan_bowls'
)
```

### 4. Historical Commemoration

**Input**: Event description, date, victims
**Output**: Spoken commemoration
**Duration**: 2-5 minutes
**Voice**: Solemn, respectful, clear
**Pacing**: Slow, deliberate
**Special**: Respectful pauses, emphasis on numbers and names

**Example**:
```python
narrator.commemorate_event(
    event=event_data,
    date=datetime(1994, 4, 7),
    voice='solemn_male',
    include_moment_of_silence=True
)
```

### 5. Radionics Broadcasting (Spoken Intention)

**Input**: Intention text, target description
**Output**: Spoken intention for broadcast
**Duration**: 30 seconds - 2 minutes
**Voice**: Clear, focused, intentional
**Pacing**: Moderate, clear enunciation
**Special**: Emphasis on key words, repeated if desired

**Example**:
```python
narrator.broadcast_intention(
    intention="May all beings find peace and liberation",
    target="Auschwitz, Poland, June 22, 1941",
    repetitions=3,
    voice='intention_speaker'
)
```

### 6. Educational Content

**Input**: Teaching text, explanations
**Output**: Educational narration
**Duration**: Variable
**Voice**: Clear, instructive, engaging
**Pacing**: Normal (140-160 WPM)
**Special**: Emphasis on key terms, clear pronunciation of Sanskrit/Tibetan/Chinese

---

## Voice Selection Criteria

### Voice Types Needed:

1. **Compassionate Female** - Blessing stories, healing narratives
2. **Compassionate Male** - Alternative for stories
3. **Neutral Calm** - Mantras, meditation
4. **Meditation Guide** - Guided meditations (very soothing)
5. **Solemn Speaker** - Historical commemorations
6. **Clear Teacher** - Educational content
7. **Intention Speaker** - Radionics broadcasting

### Language Requirements:

**Primary**: English
**Secondary**:
- Sanskrit (for mantras)
- Tibetan (for Tibetan practices)
- Pali (for Theravada mantras)
- Hebrew (for Jewish prayers in Holocaust context)
- Chinese (for Chinese practices)

**Implementation**: Use multi-lingual TTS or language-specific engines

---

## Audio Processing Features

### 1. SSML Support (Speech Synthesis Markup Language)

```xml
<speak>
    <prosody rate="slow" pitch="medium">
        May all beings be free from suffering.
    </prosody>
    <break time="2s"/>
    <emphasis level="strong">May all beings find peace.</emphasis>
</speak>
```

Features:
- `<break>` - Pauses
- `<prosody>` - Rate, pitch, volume
- `<emphasis>` - Stress on words
- `<say-as>` - Interpret dates, numbers, etc.

### 2. Audio Post-Processing

- **Normalization**: Consistent volume
- **Noise Reduction**: Clean audio
- **Reverb**: Add space/depth (optional)
- **Fade In/Out**: Smooth starts and ends
- **Silence Trimming**: Remove excess silence
- **Compression**: Consistent dynamics

### 3. Background Audio Mixing

Combine TTS with:
- **Tibetan singing bowls**
- **432 Hz tones**
- **Nature sounds** (flowing water, birds)
- **Binaural beats**
- **Chakra frequency tones**

---

## Integration Points

### With Blessing Narratives

```python
from core.blessing_narratives import StoryGenerator
from core.tts_integration import TTSNarrator

# Generate story
story = StoryGenerator().generate_story(
    target_name="Lost Soul",
    narrative_type=NarrativeType.PURE_LAND_ARRIVAL
)

# Narrate it
narrator = TTSNarrator(engine='edge-tts')
audio_file = narrator.narrate_story(
    story=story,
    output_file='pure_land_arrival.mp3',
    voice='compassionate_female',
    add_background='singing_bowls'
)
```

### With Time Cycle Broadcasting

```python
from core.time_cycle_broadcaster import TimeCycleBroadcaster
from core.tts_integration import TTSNarrator

broadcaster = TimeCycleBroadcaster()
narrator = TTSNarrator()

event = broadcaster.get_event_by_id('rwandan_genocide')
date = datetime(1994, 4, 7)

# Generate spoken commemoration
commemoration_text = f"""
Today we remember {event['name']}.
On {date.strftime('%B %d, %Y')}, terrible violence began.
We honor the {event['estimated_deaths']:,} souls who perished.
May they find peace. May healing reach all who suffered.
Om Mani Padme Hum.
"""

narrator.generate_audio(
    text=commemoration_text,
    output_file=f"commemoration_{date.strftime('%Y%m%d')}.mp3",
    voice='solemn_male',
    add_silence_before=2,
    add_silence_after=3
)
```

### With Meditation Guidance

```python
# Generate chakra meditation with audio guidance
from core.energetic_anatomy import EnergeticAnatomyDatabase

db = EnergeticAnatomyDatabase()
chakra = db.chakras['anahata']

script = f"""
[PAUSE:3]
We now focus on the {chakra.name}, {chakra.sanskrit_name}.
[PAUSE:2]
Located at {chakra.kosha}, this chakra governs {', '.join(chakra.open_qualities[:2])}.
[PAUSE:2]
The seed sound is {chakra.bija_mantra}.
[PAUSE:1]
Let us repeat together: {chakra.bija_mantra}.
[PAUSE:3]
{chakra.bija_mantra}.
[PAUSE:3]
{chakra.bija_mantra}.
[PAUSE:5]
"""

narrator.guided_meditation(
    script=script,
    voice='meditation_guide',
    background_frequency=chakra.frequency,
    output_file=f'{chakra.id}_meditation.mp3'
)
```

---

## File Formats

### Output Formats:
- **MP3**: Compressed, widely compatible (recommended)
- **WAV**: Uncompressed, high quality
- **OGG**: Open format, good compression
- **M4A**: Apple-friendly, good compression

### Quality Settings:
- **Low**: 64 kbps (voice-only, small files)
- **Medium**: 128 kbps (good quality, reasonable size)
- **High**: 192 kbps (very good quality)
- **Lossless**: WAV 16-bit 44.1kHz (archival)

---

## Architecture

### Core Classes

```python
class TTSEngine(ABC):
    """Base class for TTS engines"""
    @abstractmethod
    def synthesize(self, text: str, output_file: str, **kwargs) -> str

    @abstractmethod
    def get_voices(self) -> List[Voice]

    @abstractmethod
    def is_available(self) -> bool

class Pyttsx3Engine(TTSEngine):
    """Offline engine using pyttsx3"""

class GTTSEngine(TTSEngine):
    """Google TTS engine"""

class EdgeTTSEngine(TTSEngine):
    """Microsoft Edge TTS engine"""

class TTSNarrator:
    """High-level interface for narration"""
    def __init__(self, engine: str = 'auto', voice: str = 'default')

    def narrate_story(self, story: GeneratedStory, **kwargs) -> str
    def generate_mantra_audio(self, mantra: str, repetitions: int, **kwargs) -> str
    def guided_meditation(self, script: str, **kwargs) -> str
    def commemorate_event(self, event: Dict, **kwargs) -> str
    def generate_audio(self, text: str, **kwargs) -> str

class AudioProcessor:
    """Post-processing for TTS audio"""
    def normalize_volume(self, audio_file: str)
    def add_fade(self, audio_file: str, fade_in: float, fade_out: float)
    def mix_with_background(self, speech: str, background: str, speech_volume: float)
    def add_reverb(self, audio_file: str, room_size: float)
```

### Script Markup Language

Custom markers for meditation scripts:

```
[PAUSE:5]           - Pause for 5 seconds
[BREATHE]           - Breathing instruction with pause
[BELL]              - Ring meditation bell
[BACKGROUND:START]  - Start background audio
[BACKGROUND:STOP]   - Stop background audio
[VOLUME:50]         - Reduce volume to 50%
[TONE:528]          - Play 528 Hz tone for 3 seconds
```

---

## Performance Considerations

### Caching:
- Cache generated audio files
- Reuse identical text/voice/settings combinations
- Store in organized directory structure

### Batch Processing:
- Generate multiple files in one session
- Queue system for large batches
- Progress tracking

### Streaming (Future):
- Real-time TTS for interactive applications
- Low-latency engines for live use

---

## Privacy & Ethics

### Considerations:

1. **Data Privacy**:
   - Prefer offline engines for sensitive content
   - Be aware that online engines send text to external servers
   - Use local engines for confidential spiritual practice

2. **Sacred Content**:
   - Treat mantras and prayers with respect
   - Use appropriate voices and pacing
   - Consider traditional pronunciation guides

3. **Historical Content**:
   - Treat commemorations with solemnity
   - Verify historical accuracy
   - Respectful tone for all content

4. **Attribution**:
   - Credit TTS engine used
   - Note if content is synthetic speech
   - Respect voice actor rights (for commercial engines)

---

## Implementation Priorities

### Phase 1: Core TTS
- [x] Design architecture
- [ ] Implement TTSEngine base class
- [ ] Implement pyttsx3 engine (offline)
- [ ] Implement gTTS engine (online, free)
- [ ] Basic TTSNarrator class
- [ ] Simple text-to-speech generation

### Phase 2: Enhanced Features
- [ ] Implement edge-tts engine (high quality)
- [ ] SSML support
- [ ] Custom script markup parsing
- [ ] Voice selection system
- [ ] Audio post-processing

### Phase 3: Integration
- [ ] Blessing narrative narration
- [ ] Mantra audio generation
- [ ] Guided meditation scripts
- [ ] Historical commemoration
- [ ] Radionics intention broadcasting

### Phase 4: Advanced
- [ ] Background audio mixing
- [ ] Batch processing
- [ ] Caching system
- [ ] Multi-language support
- [ ] Voice cloning (Coqui TTS)

---

## Example Usage Patterns

### Quick Story Narration:
```python
narrator = TTSNarrator()
narrator.narrate_story(story, 'story.mp3')
```

### Custom Voice and Pace:
```python
narrator = TTSNarrator(engine='edge-tts', voice='en-US-AriaNeural')
narrator.generate_audio(
    text="May all beings be free from suffering.",
    output_file='blessing.mp3',
    rate='slow',
    pitch='medium'
)
```

### Mantra with Bell:
```python
narrator.generate_mantra_audio(
    mantra="Om Mani Padme Hum",
    repetitions=108,
    add_bell=True,
    bell_interval=21,
    output_file='mani_mantra_108.mp3'
)
```

### Full Meditation Session:
```python
script = load_meditation_script('chakra_meditation.txt')
narrator.guided_meditation(
    script=script,
    voice='meditation_guide',
    background_sound='singing_bowls',
    background_volume=0.3,
    output_file='chakra_meditation_30min.mp3'
)
```

---

## Future Enhancements

- **Real-time Translation**: Narrate in multiple languages
- **Voice Cloning**: Clone specific teachers/guides
- **Emotion AI**: Detect and match emotional tone
- **Binaural Audio**: 3D spatial audio for meditation
- **Adaptive Pacing**: Adjust based on content type
- **Interactive Sessions**: Respond to user input

---

May these voices carry blessings across the world.
May sacred teachings reach all who need them.
May technology serve the awakening of all beings.

**Om Ah Hum**

---

*Version: 1.0*
*Status: Specification Complete - Ready for Implementation*
*Date: 2025-11-15*
