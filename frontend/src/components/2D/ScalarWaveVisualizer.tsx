/**
 * Scalar Wave Visualizer — Living Mandala.
 *
 * Renders PRNG-driven scalar wave interference with five selectable modes:
 *   - interference    : 3 stacked wave layers with sparks on crests (default)
 *   - spiral          : logarithmic spiral particle sweep
 *   - standing        : vertical resonance bars
 *   - particle-storm  : dense sparks tracing wave crests
 *   - living          : all ambient modes layered + breathing + reactive overlay
 *
 * "Living Mandala" features (always on in any mode, most visible in `living`):
 *   - Cosmic breath cycle (8s sine) modulating wave amplitude
 *   - Blessing ripples emanating from center
 *   - Merit particles drifting upward
 *   - Crystal-programming harmonic bands
 *   - Element-aware color palette (Fire/Water/Earth/Air/Wood/Metal/Cosmic)
 *   - Audio coupling (isPlaying, frequency, prayerBowlMode, volume)
 *
 * The 4 original ambient modes remain visually unchanged. The reactive
 * overlay is additive — when no events have been triggered, the visualization
 * still breathes and shimmers; it is intrinsically beautiful without audio.
 *
 * Imperative API (via ref):
 *   triggerBlessingRipple(hue?)
 *   triggerMeritParticle(hue?)
 *   triggerCrystalLayer(hue)
 *   setElementMood(element)
 *   setHealingMood(active)
 *
 * @component
 */
import React, {
  useRef,
  useEffect,
  useState,
  useImperativeHandle,
  forwardRef,
} from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAudioStore } from '../../stores/audioStore';

export type ScalarMode =
  | 'interference'
  | 'spiral'
  | 'standing'
  | 'particle-storm'
  | 'living';

export interface ScalarVizAPI {
  triggerBlessingRipple: (hue?: number) => void;
  triggerMeritParticle: (hue?: number) => void;
  triggerCrystalLayer: (hue: number) => void;
  setElementMood: (element: string) => void;
  setHealingMood: (active: boolean) => void;
}

export interface ScalarWaveVisualizerProps {
  /**
   * Initial render mode for uncontrolled usage. Defaults to 'interference'
   * so the legacy small dashboard embed (`SystemMonitorsCard` renders this
   * component with no props) keeps its original appearance. Hosts that want
   * the full reactive experience should pass `mode="living"` (or
   * `initialMode="living"` for uncontrolled sacred-ambience).
   */
  initialMode?: ScalarMode;
  /**
   * Controlled mode. When provided, overrides internal state — use this for
   * host-driven mode switchers (e.g. the /practice/scalar tab). When omitted,
   * the component manages its own state starting from `initialMode`.
   */
  mode?: ScalarMode;
  /** Notifies the host when the user switches mode via the in-canvas buttons. */
  onModeChange?: (mode: ScalarMode) => void;
  /** Hide the in-canvas mode selector (host provides its own). */
  showModeSelector?: boolean;
}

// ─── Element palettes (Fire/Water/Earth/Air/Wood/Metal + Cosmic default) ─
const ELEMENT_PALETTES: Record<
  string,
  { hues: number[]; glowHue: number; bgRgba: string; glowRgba: string }
> = {
  Fire: {
    hues: [10, 25, 40, 350],
    glowHue: 25,
    bgRgba: 'rgba(120, 28, 14, 0.06)',
    glowRgba: 'rgba(255, 110, 40, 0.18)',
  },
  Water: {
    hues: [185, 200, 220, 240],
    glowHue: 200,
    bgRgba: 'rgba(14, 50, 90, 0.06)',
    glowRgba: 'rgba(60, 180, 240, 0.18)',
  },
  Earth: {
    hues: [35, 50, 75, 100],
    glowHue: 60,
    bgRgba: 'rgba(80, 60, 20, 0.06)',
    glowRgba: 'rgba(220, 180, 80, 0.18)',
  },
  Air: {
    hues: [245, 265, 285, 305],
    glowHue: 270,
    bgRgba: 'rgba(40, 20, 80, 0.06)',
    glowRgba: 'rgba(160, 100, 240, 0.18)',
  },
  Wood: {
    hues: [105, 125, 145, 165],
    glowHue: 130,
    bgRgba: 'rgba(20, 70, 40, 0.06)',
    glowRgba: 'rgba(80, 220, 140, 0.18)',
  },
  Metal: {
    hues: [205, 225, 245, 265],
    glowHue: 220,
    bgRgba: 'rgba(60, 70, 90, 0.06)',
    glowRgba: 'rgba(180, 200, 230, 0.18)',
  },
  Cosmic: {
    hues: [270, 190, 320, 50],
    glowHue: 280,
    bgRgba: 'rgba(20, 10, 30, 0.06)',
    glowRgba: 'rgba(139, 92, 246, 0.18)',
  },
};

// ─── Reactive overlay particle state ─────────────────────────────
interface MeritParticle {
  x: number;
  y: number;
  vy: number;
  age: number;
  life: number;
  hue: number;
  size: number;
}

interface BlessingRipple {
  radius: number;
  age: number;
  life: number;
  hue: number;
  width: number;
}

interface CrystalLayer {
  hue: number;
  age: number;
  life: number;
  intensity: number;
}

// ─── seeded PRNG (mulberry32 variant) ───────────────────────────
function seededRandom(seed: number): () => number {
  let s = seed | 0;
  return function () {
    s |= 0;
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ─── HSL → CSS string ────────────────────────────────────────────
function hsl(h: number, s: number, l: number, a: number = 1): string {
  return `hsla(${h}, ${s}%, ${l}%, ${a})`;
}

const MODE_LABELS: Record<ScalarMode, string> = {
  interference: 'Interference',
  spiral: 'Spiral',
  standing: 'Standing',
  'particle-storm': 'Particle Storm',
  living: 'Living Mandala',
};

// ─── Modes ───────────────────────────────────────────────────────
const MODES: ScalarMode[] = [
  'living',
  'interference',
  'spiral',
  'standing',
  'particle-storm',
];

interface WaveLayer {
  seed: number;
  amp: number;
  freq: number;
  speed: number;
  hue: number;
  width: number;
}

interface BgRing {
  cx: number;
  cy: number;
  r: number;
}

const ScalarWaveVisualizer = forwardRef<ScalarVizAPI, ScalarWaveVisualizerProps>(
  function ScalarWaveVisualizer(
    { initialMode, mode: modeProp, onModeChange, showModeSelector = true },
    ref,
  ) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animRef = useRef<number | null>(null);
    const { scalarStatus } = useWebSocket();
    const frequency = useAudioStore((s) => s.frequency);
    const isPlaying = useAudioStore((s) => s.isPlaying);
    const prayerBowlMode = useAudioStore((s) => s.prayerBowlMode);
    const volume = useAudioStore((s) => s.volume);

    // Internal state used only when no controlled `mode` prop is supplied
    // (legacy embeds). Defaults to 'interference' to preserve the original
    // dashboard appearance; hosts opt into 'living' explicitly.
    const [internalMode, setInternalMode] = useState<ScalarMode>(
      initialMode ?? 'interference',
    );
    // Controlled mode takes precedence; falls back to internal state.
    const mode = modeProp ?? internalMode;
    const [hovered, setHovered] = useState(false);

    // ── refs so the draw loop reads latest values without restarting ──
    const scalarRef = useRef(scalarStatus);
    scalarRef.current = scalarStatus;
    const seedRef = useRef<number>(Date.now());

    // Live audio/store values via refs (don't trigger animation restart)
    const modeRef = useRef<ScalarMode>(mode);
    modeRef.current = mode;
    const frequencyRef = useRef(frequency);
    frequencyRef.current = frequency;
    const isPlayingRef = useRef(isPlaying);
    isPlayingRef.current = isPlaying;
    const prayerBowlModeRef = useRef(prayerBowlMode);
    prayerBowlModeRef.current = prayerBowlMode;
    const volumeRef = useRef(volume);
    volumeRef.current = volume;

    // Element mood ref (driven via imperative API)
    const elementMoodRef = useRef<string>('Cosmic');
    const healingMoodRef = useRef<boolean>(false);

    // Reactive overlay state (lives in refs to survive draw loop)
    const particlesRef = useRef<MeritParticle[]>([]);
    const ripplesRef = useRef<BlessingRipple[]>([]);
    const crystalLayersRef = useRef<CrystalLayer[]>([]);

    // Imperative API: trigger events from anywhere
    useImperativeHandle(
      ref,
      (): ScalarVizAPI => ({
        triggerBlessingRipple: (hue?: number) => {
          const palette = ELEMENT_PALETTES[elementMoodRef.current] ?? ELEMENT_PALETTES.Cosmic;
          ripplesRef.current.push({
            radius: 0,
            age: 0,
            life: 4.0, // seconds
            hue: hue ?? palette.glowHue,
            width: 1.8 + Math.random() * 1.2,
          });
          // Also drop 6-10 merit particles for the blessing
          const count = 6 + Math.floor(Math.random() * 5);
          for (let i = 0; i < count; i++) {
            particlesRef.current.push({
              x: 0.5 + (Math.random() - 0.5) * 0.1,
              y: 0.55 + (Math.random() - 0.5) * 0.05,
              vy: -0.04 - Math.random() * 0.06, // upward (in canvas-fraction units)
              age: 0,
              life: 5 + Math.random() * 2,
              hue: hue ?? palette.glowHue + (Math.random() - 0.5) * 30,
              size: 1.4 + Math.random() * 1.6,
            });
          }
        },
        triggerMeritParticle: (hue?: number) => {
          const palette = ELEMENT_PALETTES[elementMoodRef.current] ?? ELEMENT_PALETTES.Cosmic;
          particlesRef.current.push({
            x: 0.5 + (Math.random() - 0.5) * 0.6,
            y: 0.55 + (Math.random() - 0.5) * 0.15,
            vy: -0.03 - Math.random() * 0.05,
            age: 0,
            life: 4 + Math.random() * 3,
            hue: hue ?? palette.glowHue + (Math.random() - 0.5) * 20,
            size: 1.0 + Math.random() * 1.8,
          });
        },
        triggerCrystalLayer: (hue: number) => {
          crystalLayersRef.current.push({
            hue,
            age: 0,
            life: 10.0,
            intensity: 0.7,
          });
          // also add a slow ripple for ceremony
          ripplesRef.current.push({
            radius: 0,
            age: 0,
            life: 5.5,
            hue,
            width: 1.2,
          });
        },
        setElementMood: (element: string) => {
          const key = element in ELEMENT_PALETTES ? element : 'Cosmic';
          elementMoodRef.current = key;
        },
        setHealingMood: (active: boolean) => {
          healingMoodRef.current = active;
          if (active) {
            // On entering healing mood, drop a slow expanding ripple
            ripplesRef.current.push({
              radius: 0,
              age: 0,
              life: 6.0,
              hue: 165, // soft teal
              width: 1.0,
            });
          }
        },
      }),
      [],
    );

    // Only restart the animation loop on mode change.
    // Everything else is read from refs inside the loop.
    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d', { alpha: false });
      if (!ctx) return;
      let phase = 0;
      let paused = false; // Paused when tab hidden or canvas offscreen
      const s = seedRef.current;
      const startTime = performance.now();
      let lastTime = startTime;

      // ── wave layer configs ────────────────────────────────
      const layers: WaveLayer[] = [
        { seed: s, amp: 0.42, freq: 0.008, speed: 0.012, hue: 270, width: 2.5 },
        { seed: s * 3 + 1, amp: 0.28, freq: 0.013, speed: 0.018, hue: 190, width: 1.8 },
        { seed: s * 7 + 2, amp: 0.18, freq: 0.021, speed: 0.025, hue: 320, width: 1.2 },
      ];

      const prngs: Array<() => number> = layers.map((l) => seededRandom(l.seed));

      // ── background field rings (offscreen-cached, blit per frame) ──
      let bgRingsCanvas: HTMLCanvasElement | null = null;
      let bgRingsCtx: CanvasRenderingContext2D | null = null;
      let cachedW = 0;
      let cachedH = 0;
      const precomputeBg = (w: number, h: number) => {
        if (!bgRingsCanvas) {
          bgRingsCanvas = document.createElement('canvas');
          bgRingsCtx = bgRingsCanvas.getContext('2d');
        }
        if (!bgRingsCtx) return;
        bgRingsCanvas.width = w;
        bgRingsCanvas.height = h;
        bgRingsCtx.clearRect(0, 0, w, h);
        const cx = w / 2;
        const cy = h / 2;
        const maxR = Math.sqrt(cx * cx + cy * cy);
        bgRingsCtx.strokeStyle = 'rgba(88, 66, 144, 0.12)';
        bgRingsCtx.lineWidth = 0.5;
        for (let r = 30; r < maxR; r += 22) {
          bgRingsCtx.beginPath();
          bgRingsCtx.arc(cx, cy, r, 0, Math.PI * 2);
          bgRingsCtx.stroke();
        }
        cachedW = w;
        cachedH = h;
      };

      // ── radial gradient (cached, recomputed only on resize) ──
      let cachedGlowGrad: CanvasGradient | null = null;
      let cachedPaletteKey = '';
      let cachedGradSize = 0;
      const buildGlowGrad = (w: number, h: number, paletteKey: string, bgRgba: string) => {
        if (
          cachedGlowGrad &&
          cachedPaletteKey === paletteKey &&
          cachedGradSize === Math.min(w, h) * 0.45
        ) {
          return cachedGlowGrad;
        }
        const grad = ctx.createRadialGradient(
          w / 2, h / 2, 0,
          w / 2, h / 2, Math.min(w, h) * 0.45,
        );
        grad.addColorStop(0, bgRgba);
        grad.addColorStop(1, 'rgba(8, 8, 24, 0)');
        cachedGlowGrad = grad;
        cachedPaletteKey = paletteKey;
        cachedGradSize = Math.min(w, h) * 0.45;
        return grad;
      };

      // ── draw ──────────────────────────────────────────────
      const draw = () => {
        if (paused) return; // Page hidden or canvas offscreen — skip frame entirely
        const now = performance.now();
        const dt = Math.min(0.1, (now - lastTime) / 1000); // seconds, clamped
        lastTime = now;
        const t = phase;
        const currentMode = modeRef.current;
        const currentPalette =
          ELEMENT_PALETTES[elementMoodRef.current] ?? ELEMENT_PALETTES.Cosmic;
        // read latest rate from ref — no effect restart on WebSocket updates
        const rate = scalarRef.current?.rate;

        // ── breathing cycle (8s sine, slow inhale/exhale) ─
        const breathPhase = (now - startTime) / 1000 * ((2 * Math.PI) / 8);
        // breath ranges 0.82 → 1.02 (subtle but felt)
        const breath = 0.92 + 0.10 * Math.sin(breathPhase);

        // healing mood slows everything down 30%
        const tempoScale = healingMoodRef.current ? 0.7 : 1.0;

        // audio coupling: isPlaying adds slight amp + speed boost
        const audioBoost = isPlayingRef.current ? 1.15 : 1.0;
        const audioTempo = isPlayingRef.current ? 1.2 : 1.0;

        // frequency scales wave density (7 Hz → 0.5x, 136 Hz → 1.0x, 528 Hz → 1.6x)
        const freqMul = Math.max(0.3, Math.min(2.0, Math.log2(frequencyRef.current / 50 + 0.1) * 0.7 + 1.0));

        // volume affects global alpha
        const volAlpha = 0.7 + Math.max(0, Math.min(1, volumeRef.current)) * 0.3;

        // ── update reactive overlay state ──────────────────
        // particles
        const particles = particlesRef.current;
        for (let i = particles.length - 1; i >= 0; i--) {
          const p = particles[i];
          p.age += dt;
          p.y += p.vy * dt;
          if (p.age >= p.life) particles.splice(i, 1);
        }
        // ripples
        const ripples = ripplesRef.current;
        for (let i = ripples.length - 1; i >= 0; i--) {
          const r = ripples[i];
          r.age += dt;
          r.radius = (r.age / r.life) * Math.min(canvas.width, canvas.height) * 0.55;
          if (r.age >= r.life) ripples.splice(i, 1);
        }
        // crystal layers
        const crystalLayers = crystalLayersRef.current;
        for (let i = crystalLayers.length - 1; i >= 0; i--) {
          const cl = crystalLayers[i];
          cl.age += dt;
          if (cl.age >= cl.life) crystalLayers.splice(i, 1);
        }

        // phosphor fade — translucent clear for trail persistence
        ctx.fillStyle = 'rgba(8, 8, 24, 0.22)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const w = canvas.width;
        const h = canvas.height;

        // ── background field rings (offscreen-cached, blit once) ──
        if (bgRingsCanvas && bgRingsCtx && cachedW === w && cachedH === h) {
          ctx.drawImage(bgRingsCanvas, 0, 0, w, h);
        } else {
          // Fallback: stroke rings directly (resize edge case)
          ctx.strokeStyle = 'rgba(88, 66, 144, 0.12)';
          ctx.lineWidth = 0.5;
          const cx = w / 2;
          const cy = h / 2;
          const maxR = Math.sqrt(cx * cx + cy * cy);
          for (let r = 30; r < maxR; r += 22) {
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();
          }
        }

        // central subtle glow (palette-tinted, gradient cached)
        ctx.fillStyle = buildGlowGrad(w, h, currentPalette.glowHue + '', currentPalette.bgRgba);
        ctx.fillRect(0, 0, w, h);

        // ── Living mode runs all four layers stacked ──────
        const runInterference = currentMode === 'interference' || currentMode === 'living';
        const runParticleStorm =
          currentMode === 'particle-storm' || currentMode === 'living';
        const runStanding = currentMode === 'standing' || currentMode === 'living';
        const runSpiral = currentMode === 'spiral' || currentMode === 'living';

        // ── draw each wave layer (interference / living) ──
        if (runInterference) {
          for (let li = 0; li < layers.length; li++) {
            const l = layers[li];
            const prng = prngs[li];
            // use palette hue for base, layer offset adds variation
            const baseHue = currentPalette.hues[li % currentPalette.hues.length];
            const hue = (baseHue + t * 12) % 360;

            ctx.save();
            ctx.beginPath();

            // glow pass — only on the first layer to halve shadowBlur cost
            if (li === 0) {
              ctx.shadowBlur = 12;
              ctx.shadowColor = hsl(hue, 80, 55, 0.7);
            } else {
              ctx.shadowBlur = 0;
            }
            ctx.strokeStyle = hsl(hue, 80, 55, 0.85);
            ctx.lineWidth = l.width;

            for (let x = 0; x < w; x++) {
              const n1 = prng() * 2 - 1;
              const n2 = prng() * 2 - 1;
              const n3 = prng() * 2 - 1;
              const noise =
                n1 * 0.55 +
                n2 * 0.30 * Math.sin(x * l.freq * freqMul + t * l.speed * audioTempo) +
                n3 * 0.15 * Math.cos(x * l.freq * freqMul * 2.3 + t * l.speed * 0.7);
              const y =
                h / 2 + noise * h * l.amp * breath * audioBoost * tempoScale;
              if (x === 0) ctx.moveTo(x, y);
              else ctx.lineTo(x, y);
            }
            ctx.stroke();

            // bright core pass (no blur, thinner)
            ctx.shadowBlur = 0;
            ctx.strokeStyle = hsl(hue, 50, 85, 0.55);
            ctx.lineWidth = l.width * 0.45;
            ctx.stroke();

            ctx.restore();
          }
        }

        // ── particle sparks along wave crests ─────────────
        // OPTIMIZATION: shadowBlur is per-pixel expensive. Set it once per
        // batch instead of per-particle. Skip shadow on small particles.
        if (runInterference || runParticleStorm) {
          const sparkCount = currentMode === 'particle-storm' || currentMode === 'living' ? 60 : 18;
          ctx.shadowBlur = 6;
          for (let i = 0; i < sparkCount; i++) {
            const li = i % layers.length;
            const prng = prngs[li];
            const sx = prng() * w;
            const n1 = prng() * 2 - 1;
            const n2 = prng() * 2 - 1;
            const n3 = prng() * 2 - 1;
            const noise =
              n1 * 0.55 +
              n2 * 0.30 * Math.sin(sx * layers[li].freq * freqMul + t * layers[li].speed * audioTempo) +
              n3 * 0.15 * Math.cos(sx * layers[li].freq * freqMul * 2.3 + t * layers[li].speed * 0.7);
            const sy = h / 2 + noise * h * layers[li].amp * breath * audioBoost * tempoScale;
            const baseHue = currentPalette.hues[li % currentPalette.hues.length];
            const hue = (baseHue + t * 12 + i * 11) % 360;
            const alpha = (0.35 + prng() * 0.5) * volAlpha;

            ctx.shadowColor = hsl(hue, 90, 65, alpha);
            ctx.fillStyle = hsl(hue, 70, 85, alpha);
            ctx.beginPath();
            ctx.arc(sx, sy, 1.0 + prng() * 1.4, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.shadowBlur = 0;
        }

        // ── standing-wave vertical bars ────────────────────
        if (runStanding) {
          const barCount = currentMode === 'living' ? 36 : 28;
          ctx.shadowBlur = 6; // reduced from 10 — most expensive cost
          for (let i = 0; i < barCount; i++) {
            const bx = (i / barCount) * w;
            const prng = prngs[i % 3];
            const amp = Math.abs(Math.sin(bx * 0.015 * freqMul + t * 0.6 * audioTempo)) * h * 0.35 * breath * audioBoost * tempoScale;
            const baseHue = currentPalette.glowHue;
            const hue = (baseHue + i * 8 + t * 15) % 360;
            ctx.shadowColor = hsl(hue, 75, 55, 0.5 * volAlpha);
            ctx.strokeStyle = hsl(hue, 70, 60, 0.6 * volAlpha);
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.moveTo(bx, h / 2 - amp);
            ctx.lineTo(bx, h / 2 + amp);
            ctx.stroke();
          }
          ctx.shadowBlur = 0;
        }

        // ── spiral mode ───────────────────────────────────
        if (runSpiral) {
          const cx = w / 2;
          const cy = h / 2;
          const maxR = Math.min(w, h) * 0.48;
          ctx.shadowBlur = 4; // reduced from 6
          for (let a = 0; a < Math.PI * 6; a += 0.06) {
            const r = (a / (Math.PI * 6)) * maxR;
            const px = cx + Math.cos(a + t * 0.4 * audioTempo) * r;
            const py = cy + Math.sin(a + t * 0.4 * audioTempo) * r * 0.7;
            const hue = (currentPalette.glowHue + a * 20 + t * 18) % 360;
            ctx.fillStyle = hsl(hue, 80, 65, 0.5 * volAlpha);
            ctx.shadowColor = hsl(hue, 80, 55, 0.6 * volAlpha);
            ctx.beginPath();
            ctx.arc(px, py, 1.6, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.shadowBlur = 0;
        }

        // ── Prayer-bowl shimmer overlay (when bowl mode on) ──
        if (prayerBowlModeRef.current) {
          ctx.save();
          const cx = w / 2;
          const cy = h / 2;
          const r = Math.min(w, h) * 0.35 * (0.9 + 0.1 * Math.sin(breathPhase * 2));
          ctx.shadowBlur = 14; // reduced from 22 — was per-pixel expensive
          ctx.shadowColor = hsl(currentPalette.glowHue, 80, 70, 0.35);
          ctx.strokeStyle = hsl(currentPalette.glowHue, 60, 80, 0.25);
          ctx.lineWidth = 1.0;
          ctx.beginPath();
          ctx.arc(cx, cy, r, 0, Math.PI * 2);
          ctx.stroke();
          ctx.restore();
        }

        // ── Crystal programming bands ─────────────────────
        // each crystal layer adds a soft horizontal band shifting the hue mix
        for (const cl of crystalLayers) {
          const fade = 1 - cl.age / cl.life;
          ctx.save();
          ctx.globalAlpha = 0.18 * fade * cl.intensity;
          ctx.fillStyle = hsl(cl.hue, 80, 55, 0.25);
          ctx.fillRect(0, h * 0.35, w, h * 0.30);
          ctx.shadowBlur = 8; // reduced from 14
          ctx.shadowColor = hsl(cl.hue, 90, 65, 0.3 * fade);
          ctx.fillStyle = hsl(cl.hue, 70, 70, 0.2);
          ctx.fillRect(0, h * 0.48, w, h * 0.04);
          ctx.restore();
        }

        // ── Blessing ripples emanating from center ────────
        // OPTIMIZATION: set shadowBlur once per frame for all ripples instead of per-ripple
        ctx.shadowBlur = 12; // reduced from 20
        for (const ripple of ripples) {
          const fade = 1 - ripple.age / ripple.life;
          const cx = w / 2;
          const cy = h / 2;
          ctx.save();
          ctx.globalAlpha = 0.7 * fade;
          ctx.shadowColor = hsl(ripple.hue, 90, 70, 0.8 * fade);
          ctx.strokeStyle = hsl(ripple.hue, 85, 75, 0.7 * fade);
          ctx.lineWidth = ripple.width;
          ctx.beginPath();
          ctx.arc(cx, cy, ripple.radius, 0, Math.PI * 2);
          ctx.stroke();
          // Secondary inner ring for richness
          if (ripple.age > 0.4) {
            ctx.globalAlpha = 0.35 * fade;
            ctx.lineWidth = ripple.width * 0.5;
            ctx.strokeStyle = hsl((ripple.hue + 30) % 360, 90, 80, 0.5 * fade);
            ctx.beginPath();
            ctx.arc(cx, cy, ripple.radius * 0.7, 0, Math.PI * 2);
            ctx.stroke();
          }
          ctx.restore();
        }
        ctx.shadowBlur = 0;

        // ── Merit particles drifting upward ──────────────
        // OPTIMIZATION: set shadowBlur once for the whole batch
        ctx.shadowBlur = 6; // reduced from 10
        for (const p of particles) {
          const fade = Math.max(0, 1 - p.age / p.life);
          const xPx = p.x * w;
          const yPx = p.y * h;
          ctx.save();
          ctx.globalAlpha = 0.85 * fade;
          ctx.shadowColor = hsl(p.hue, 90, 70, 0.8 * fade);
          ctx.fillStyle = hsl(p.hue, 80, 80, 0.9 * fade);
          ctx.beginPath();
          ctx.arc(xPx, yPx, p.size, 0, Math.PI * 2);
          ctx.fill();
          // subtle inner glow (no shadow on this small inner pass)
          ctx.globalAlpha = 0.4 * fade;
          ctx.shadowBlur = 0;
          ctx.fillStyle = hsl((p.hue + 60) % 360, 90, 90, 0.5 * fade);
          ctx.beginPath();
          ctx.arc(xPx, yPx, p.size * 0.4, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
        ctx.shadowBlur = 0;

        // ── HUD ───────────────────────────────────────────
        ctx.shadowBlur = 0;
        ctx.globalAlpha = 1.0;
        ctx.fillStyle = 'rgba(180, 160, 220, 0.85)';
        ctx.font = `${Math.max(10, Math.round(w / 80))}px "JetBrains Mono", "Fira Code", monospace`;
        ctx.textAlign = 'left';
        const hudY = Math.max(16, Math.round(h * 0.05));
        ctx.fillText(
          `λ ${rate != null ? Number(rate).toFixed(2) : '—'} Hz · ${currentPalette.glowHue}° ${elementMoodRef.current} · ${MODE_LABELS[currentMode]}`,
          10,
          hudY,
        );
        // breath indicator (small breathing dot)
        ctx.fillStyle = hsl(currentPalette.glowHue, 80, 70, 0.6 + 0.4 * (breath - 0.92) / 0.10);
        ctx.beginPath();
        ctx.arc(w - 18, hudY - 4, 3 + (breath - 0.92) * 20, 0, Math.PI * 2);
        ctx.fill();

        // phase advance (tempo-modulated)
        phase += 0.016 * audioTempo * tempoScale;
        animRef.current = requestAnimationFrame(draw);
      };

      // ── resize handler (RAF-coalesced to avoid thrash on window drag) ──
      let resizeRaf = 0;
      const resize = () => {
        if (resizeRaf) return; // Coalesce — only one pending resize per frame
        resizeRaf = requestAnimationFrame(() => {
          resizeRaf = 0;
          // OPTIMIZATION: Cap devicePixelRatio at 2. On retina/4K displays,
          // the default 3x or 4x produces a 16K backing store that destroys
          // the per-pixel wave loops. Capping at 2 is visually indistinguishable
          // and drops pixel work by 4-9x.
          const dpr = Math.min(window.devicePixelRatio || 1, 2);
          const rect = canvas.getBoundingClientRect();
          canvas.width = rect.width * dpr;
          canvas.height = rect.height * dpr;
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          precomputeBg(rect.width, rect.height);
          // Invalidate gradient cache so it recomputes with new dimensions
          cachedGlowGrad = null;
        });
      };

      resize();
      window.addEventListener('resize', resize);

      // ── OPTIMIZATION: Pause RAF when tab hidden or canvas offscreen ──
      const handleVisibility = () => {
        if (document.hidden) {
          paused = true;
          if (animRef.current !== null) {
            cancelAnimationFrame(animRef.current);
            animRef.current = null;
          }
        } else if (paused) {
          paused = false;
          lastTime = performance.now();
          animRef.current = requestAnimationFrame(draw);
        }
      };
      document.addEventListener('visibilitychange', handleVisibility);

      // IntersectionObserver — pause when canvas fully out of viewport
      const intersectionObserver = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (!entry.isIntersecting) {
              paused = true;
              if (animRef.current !== null) {
                cancelAnimationFrame(animRef.current);
                animRef.current = null;
              }
            } else if (paused) {
              paused = false;
              lastTime = performance.now();
              animRef.current = requestAnimationFrame(draw);
            }
          }
        },
        { threshold: 0 },
      );
      intersectionObserver.observe(canvas);

      draw();

      return () => {
        if (animRef.current !== null) {
          cancelAnimationFrame(animRef.current);
        }
        if (resizeRaf) cancelAnimationFrame(resizeRaf);
        window.removeEventListener('resize', resize);
        document.removeEventListener('visibilitychange', handleVisibility);
        intersectionObserver.disconnect();
      };
    }, [mode]); // ← only mode changes restart the loop

    const handleModeClick = (m: ScalarMode) => {
      setInternalMode(m);
      onModeChange?.(m);
    };

    return (
      <div
        className="relative w-full h-full group"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <canvas ref={canvasRef} className="w-full h-full block" />

        {/* mode switcher — visible on hover (unless host renders its own) */}
        {showModeSelector && (
          <div
            className={`absolute bottom-2 right-2 flex gap-1 transition-opacity duration-300 ${
              hovered ? 'opacity-100' : 'opacity-0'
            }`}
          >
            {MODES.map((m) => (
              <button
                key={m}
                onClick={() => handleModeClick(m)}
                className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors font-mono ${
                  mode === m
                    ? 'bg-purple-600/80 text-white border-purple-400/40'
                    : 'bg-gray-900/60 text-gray-400 border-white/10 hover:border-purple-400/30 hover:text-purple-300'
                }`}
                title={MODE_LABELS[m]}
              >
                {m === 'living' ? 'Living' : m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  },
);

export default ScalarWaveVisualizer;