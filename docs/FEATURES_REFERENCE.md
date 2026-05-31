# Vajra.Stream Features Reference & Specifications

This document serves as the master specification for all features, mathematical formulas, energetic systems, and architectural components of the **Vajra.Stream Sacred Technology Platform**. It also explicitly lists known functional gaps between the codebase and documentation.

---

## 1. RNG Attunement & E-Meter Logic

Designed to monitor quantum-random fluctuations as a proxy for consciousness attunement during rituals.

### A. Needle States
The system simulates an analog E-meter needle that fluctuates between these states:
-   **`FLOATING`:** Rhythmic, smooth, left-right swinging. Indicates energetic release, resolution, or the "End Phenomenon" (EP) of a process.
-   **`RISING`:** Continuous drift upward, indicating building resistance or tension.
-   **`FALLING`:** Drift downward, indicating release of tension or grounding.
-   **`ROCKSLAM`:** High-frequency, erratic, violent needle swings. Indicates heavy trauma or raw subconscious charging.
-   **`THETA_BOP`:** Small, rapid, rhythmic pulses. Indicates light mental activity or superficial focus.
-   **`STUCK`:** Immobile needle, indicating locked energy or heavy blockages.

### B. Math & Formulas
-   **Tone Arm (TA):** Ranges from `0` to `10`. Measures static resistance. A TA between `2.0` and `3.0` represents a clear baseline state.
-   **Needle Position:** Ranges from `-100` (far left) to `+100` (far right).
-   **Coherence Score:** Calculated as a running average of entropy deviations:
    $$\text{Coherence} = 1.0 - \text{Entropy}$$
-   **Floating Needle Score (FNS):** Measures the smoothness and rhythmicity of the needle's motion. An FNS $> 75\%$ triggers the detection of a "Floating Needle," prompting the operator to complete the session.

---

## 2. Radionics Broadcasting Engine

Amplifies intentions by converting them into rate numbers and broadcasting them through frequency carrier waves.

-   **General Vitality (GV):** A metric (measured from `0` to `100` or higher) indicating the energetic strength of the witness sample before and after a broadcast.
-   **Radionics Rates:** Coordinates derived from intention texts. Traditional 3-dial or 10-dial rates (e.g. `25.5 - 45.2 - 67.8`) map the energetic focus.
-   **Witness / Target Relationship:**
    -   **Witness:** The source representation of the recipient (e.g. hair sample, digital photo, written name).
    -   **Target:** The intent, rate, or remedy being projected (e.g. protection, homeopathic remedy, specific mantra).

---

## 3. Scalar Wave Generator

Synthesizes specific sound frequencies designed to create standing longitudinal waves.

-   **Frequency Bands:** Generates waves from `0.6 Hz` to `1000 Hz`.
-   **Key Frequencies:**
    -   **Schumann Resonance:** `7.83 Hz` (fundamental earth frequency).
    -   **Solfeggio Fones:** `396 Hz` (liberating guilt), `417 Hz` (facilitating change), `528 Hz` (transformation/DNA repair), `639 Hz` (relationships), `741 Hz` (expression/solutions), `852 Hz` (intuition), `963 Hz` (crown connection).
    -   **Planetary Frequencies:** Earth Year (Om: `136.1 Hz`), Moon (Synodic: `210.42 Hz`), Sun (`126.22 Hz`).

---

## 4. Energetic Anatomy & Subtle Body Systems

Integrates traditional Eastern healing models with visual, frequency-based stimulation.

-   **The 7 Chakras:** Muladhara (Root - Red - `228 Hz` / `396 Hz`), Svadhisthana (Sacral - Orange - `303 Hz` / `417 Hz`), Manipura (Solar Plexus - Yellow - `182 Hz` / `528 Hz`), Anahata (Heart - Green - `128 Hz` / `639 Hz`), Vishuddha (Throat - Blue - `144 Hz` / `741 Hz`), Ajna (Third Eye - Indigo - `96 Hz` / `852 Hz`), Sahasrara (Crown - Violet/White - `172 Hz` / `963 Hz`).
-   **Subtle Channels (Nadis):** Models the Ida (cooling/lunar), Pingala (heating/solar), and Sushumna (central axis) energy channels.
-   **12 Meridians:** Models the flow of Qi through major organ meridians (Lung, Large Intestine, Stomach, Spleen, Heart, Small Intestine, Bladder, Kidney, Pericardium, Triple Burner, Gallbladder, Liver).

---

## 5. LLM Narratives, Characters & Journeys

Integrates generative AI models to output customized teachings and track evolutionary paths.

-   **Dual LLM Role Assignments:**
    -   *Orchestrator:* Fast, analytical model (e.g. DeepSeek-v4, GPT-4o-mini) that interprets user commands, calls system tools, and reads sensors.
    -   *Creative:* Expressive model (e.g. Claude 3.5 Sonnet, local GGUF llama3-instruct) that generates prayers, stories, and guidance.
-   **Grimoire System:** Stores ritual configurations, carrier frequencies, and traditional correspondences.
-   **Character Journey Arcs:** Users can generate a character (with attributes, role, and element) and guide them through a 6-stage journey. Each stage represents a spiritual test, altering frequency outputs and generating narrative progression.

---

## 6. 88 Buddhas, Dharani & Saka Dawa Systems

Plumbs Tibetan and Chinese Buddhist practices into the automated broadcast layer.

-   **88 Buddhas Great Repentance Liturgy:** Cycles through the 53 Past Buddhas and 35 Confession Buddhas of the sutras.
-   **Mala Recitation Loop:** A background task that cycles names. It dedicates merits every 21 recitations, performs full dedications at 108, and counts cycles.
-   **Saka Dawa Holy Month:** The 4th Tibetan lunar month commemorating the Buddha's birth, awakening, and parinirvana. All merits accumulated during this month are multiplied:
    -   **10,000x** during the month.
    -   **100,000x** on the 15th day (Saka Dawa Duchen / Full Moon).

---

## 7. Audio & Visualization Engines

-   **Audio Output Modes:**
    -   *Pure Sine:* Clean, mathematically precise sine waves.
    -   *Prayer Bowl:* Synthesizes multi-harmonic acoustic envelopes with exponential decay, reproducing the physical striking of a Himalayan brass singing bowl.
    -   *Binaural Beats:* Plays slightly offset frequencies in left/right channels to entrain brainwaves.
-   **Visual Renderers:**
    -   *Canvas 2D:* Displays real-time audio spectrum analyzer lines and waterfall graphs.
    -   *Three.js 3D:* Renders interactive crystal hexagons, rotating wireframe prayer wheels, and geometric mandalas reacting to audio amplitudes.

---

## 8. Code vs. Documentation Gaps

The following table explicitly highlights where the codebase differs from the specifications in the documentation:

| Feature Area | Documented Behavior | Actual Codebase Implementation | Status & Impact |
| :--- | :--- | :--- | :--- |
| **TTS Audio Playback** | Continuous recitation loop recites Buddha names aloud using Edge TTS voice synthesis. | `BuddhaRecitationLoop` calls `self._tts.speak()`, which calls `edge-tts` to save an `.mp3` file to a temp directory. However, **no audio playback driver** is called in the loop to play the file out loud. | **Drift/Gap:** Audio files are successfully synthesized and saved on disk, but they are not played on backend speakers. |
| **Saka Dawa Calculations** | The system automatically calculates the 4th Tibetan month and broadcasts the 100,000x merit multiplier. | The REST endpoint `/api/v1/operator/saka-dawa` uses a static hardcoded check `now.month in (5, 6)` and returns placeholder metadata. | **Drift/Gap:** The accurate lunar logic `check_saka_dawa()` using `lunar-python` exists in `core/auspicious_timing.py` but is **not connected** to the operator endpoint. |
| **Physical Scalar Wave Hardware** | Advanced Level 3 setup with dedicated electromagnetic wave emitters and torsion field coils. | System only generates standard audio waveforms. The hardware manager simply outputs stereo signals via the standard soundcard (`sounddevice` driver). | **Simulation/Mock:** There are no specialized hardware protocols, serial drivers, or USB controllers. Physical integration is purely acoustic/vibrational. |
| **Z AI GLM 4.6 & LM Studio** | Dedicated drivers and custom integration wrappers for Z AI GLM 4.6 and local LM Studio servers. | `llm_integration.py` uses generic OpenAI-compatible APIs or Anthropic SDK connections. LM Studio is probed using a basic localhost HTTP check. | **Generic Wrapper:** No custom vendor-specific drivers exist. All models use generic API protocols. |
