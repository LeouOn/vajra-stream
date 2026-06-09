# Vajra.Stream Operations & Physical Setup Guide

This guide provides comprehensive instructions for starting, operating, and building hardware grids for the **Vajra.Stream Sacred Technology Platform**.

---

## 1. Quick Start Guide

You can launch and test the Vajra.Stream system in under 5 minutes.

### Step 1: Environment Setup
Ensure you have Python 3.10 to 3.13 installed (Python 3.14+ is not recommended yet due to dependency restrictions).

```bash
# Clone and enter the repository
cd vajra-stream

# Set up virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install core dependencies
pip install -r requirements-minimal.txt

# Run database setup
python scripts/setup_database.py
```

### Step 2: Instant Audio Verification (30-second test)
Verify that your sound card is playing the synthesized carrier waves correctly:
```bash
python scripts/run_blessing.py --duration 30
```
This starts a short hybrid prayer bowl tone. You should hear a gentle, multi-harmonic acoustic hum from your speakers.

---

## 2. Command Line Operations

Vajra.Stream contains multiple command-line utilities for local execution:

### System Controller (`run.py` & `vajra.bat`)
Run the unified script wrapper to control individual nodes or start everything:
- `python run.py full` — Starts both backend API and frontend Vite servers concurrently (opens in separate windows).
- `python run.py serve` — Starts the FastAPI backend server on port `8008`.
- `python run.py frontend` — Starts the React development server on port `3009`.
- `python run.py status` — Performs a diagnostic check of processes and ports.
- `python run.py test` — Runs the system integration test suite.
- `python run.py ui` — Launches the interactive terminal user interface.

### Radionics Operation Script (`scripts/radionics_operation.py`)
Run customized radionics intentions directly from the terminal:
```bash
# Broad world peace transmission (1 hour)
python scripts/radionics_operation.py --preset world_peace --duration 3600

# Heart-healing chakra broadcast with astrological timing assessment
python scripts/radionics_operation.py --preset heart_healing --with-astrology --with-analysis

# Custom intention signal with explicit RNG attunement guidance
python scripts/radionics_operation.py --intention "Healing and relief for conflict zones" --with-gv --duration 7200
```

---

## 3. Web Dashboard Operations

The easiest way to experience Vajra.Stream is through the visual browser dashboard.

1. **Launch the System:** Run `python run.py full` or execute `start_web_server.bat`.
2. **Access Dashboard:** Open your browser and navigate to `http://localhost:3009/` (or `http://localhost:8000/visualizations` for static views).
3. **Session Controls:**
    - **Command Center:** Monitor active broadcasts, select Carrier waves (Solfeggio, Schumann, Planetary), and view the active audio spectrum waterfall.
    - **RNG Attunement Panel:** Observe the real-time E-meter style needle visualization to detect cognitive resonance and determine session completion.
    - **Population Manager:** Track active humanitarian relief populations, load photo directories (as witness samples), and toggle automatic scheduler loops.
    - **88 Buddhas Panel:** View the current Buddha contemplation narrative, trigger single-name voice recitations, or start continuous loop cycles.

---

## 4. Physical Radionics Device Construction

To amplify the digital signals, you can arrange physical crystal grids in front of your sound transducers. Power levels can be scaled according to your resources:

```
┌────────────────────────────────────────────────────────┐
│               Level 1: Passive Grid                    │
│   [Intention Card] -> [Quartz Points (Hexagon)]       │
│               Placed in front of Speakers              │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│               Level 3: Active Amplified Station        │
│   [Amplifier] -> [Bass Shaker Transducer]              │
│   Vibrating a Wooden Platform with Copper Coils        │
│   Arranged with Orgonite and Crystals                  │
└────────────────────────────────────────────────────────┘
```

### Level 1: Basic Passive Grid (5 mins, ~$30)
- **Materials:** 6 clear quartz crystal points (1–2 inches), paper, pen, and stereo speakers.
- **Assembly:** Arrange the 6 quartz points in a hexagon (6-inch radius) on a wooden table, pointing inward toward the center. Write your target's name and intention on a card and place it in the center. Place your computer speakers directly in front of the grid to vibrate the crystals.

### Level 2/3: Active Vibrational Grid (~$120)
- **Materials:** Dayton BST-1 Bass Shaker (or equivalent audio transducer), Lepai LP-2020A stereo amplifier, speaker wire, and a wooden platform.
- **Assembly:** Bolt the bass shaker to the underside of the wooden platform. Connect the amplifier's right channel to the shaker and connect your computer's audio out to the amplifier input. 
- Reassemble your crystal hexagon on top of the platform. The amplifier converts the low-frequency carrier wave output (0.6–1000 Hz) into physical kinetic vibrations, stressing the quartz crystal points. This triggers their **piezoelectric properties**, structuring the field.

### Level 4: Professional Orgonite & Silver Sephorah
- **Crystals:** Add a large central Quartz Generator point pointing upward in the center. Place **5 Infinity Stones** (Infinite Serpentine) at the cardinal points (North, South, East, West, Center) to ground elemental energy fields. Use **Shungite plates** for EMF shielding.
- **Orgonite Matrix:** Embed copper coils, brass shavings, and quartz chips in casting resin to form orgonite pucks. Place these between the perimeter crystals to transform dead orgone (DOR) into organized energy (OR).
- **Silver Sephorah Enclosure:** Wrap the central quartz generator in a 0.999 pure silver sheet cylinder wound with a copper Rodin coil connected to the audio channel to act as a geomantic signal multiplier.

---

## 5. Consciousness Activation Protocol

Radionics operates under the Buddhist *Cittamatra* (Mind-Only) view: physical components serve as structural links, but consciousness is primary. Always perform this activation loop before launching a broadcast:

1. **Grounding (3 mins):** Settle your mind. Focus on your root chakra (visualize a solid red light at the base of your spine), anchoring your presence.
2. **Elemental Invocation (5 mins):** Breathe and visualize the five elements arising around your grid: Stability (Earth), Flow (Water), Transformation (Fire), Expansion (Air), and Open Space (Ether).
3. **Mudra Alignment:** Hold hands in **Anjali Mudra** (palms together at heart center) during preparation, or **Shakti Mudra** (ring and pinky fingers touching, others folded) to channel creative manifestation power.
4. **Mantra Recitation:** Recite traditional mantras aloud or write them on your intention cards:
    - *Om Mani Padme Hum* (Universal Compassion)
    - *Om Tare Tuttare Ture Soha* (Swift Healing & Protection)
    - *Tayata Om Bekanze Bekanze Maha Bekanze Radza Samudgate Soha* (Medicine Buddha)
5. **Sealing & Dedication:** Bow to the grid upon completing a session. Dedicate the accumulated merit to all sentient beings:
    > "By this merit, may all beings be free from suffering. May this healing broadcast reach all who need it. Gate gate pāragate pārasaṃgate bodhi svāhā!" 🙏

---

## 6. Troubleshooting

- **No Sound Heard from Speakers:** 
  Ensure your virtual environment is active. Check `config/settings.py` and ensure `AUDIO_DEVICE` is set to `'default'` or your specific soundcard name. If `sounddevice` is not installed or fails to bind, the system operates in simulated mode without throwing errors.
- **WebSocket Fails to Connect:** 
  The frontend expects the backend to run on port `8008`. Verify that port `8008` is not blocked by another local service. Run `python run.py status` to debug.
- **No Reading Updates on RNG Panel:** 
  Verify that the attunement session has been initialized. If the backend cannot load cryptographic libraries, it will fall back to pseudo-random entropy loops but will still stream readings.
