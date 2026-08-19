/**
 * Scalar Wave Visualizer — multi-layer Living Mandala and interference pattern display.
 *
 * Renders PRNG-driven scalar wave fields with sacred geometry harmonics,
 * 8-second cosmic breathing pulsation, dynamic element mood grading,
 * crystal resonance bands, and interactive blessing ripples / merit sparks.
 *
 * Exposes the `ScalarVizAPI` imperative interface via `forwardRef` for
 * full coordination with `ScalarTab`.
 *
 * @component
 */
import React, {
  useRef,
  useEffect,
  useState,
  useImperativeHandle,
  forwardRef,
  useCallback,
} from 'react';
import { useWebSocketStable as useWebSocket } from '../../hooks/useWebSocketStable';

export type ScalarMode =
  | 'living'
  | 'interference'
  | 'spiral'
  | 'standing'
  | 'particle-storm';

export interface ScalarVizAPI {
  setElementMood: (element: string) => void;
  setHealingMood: (healing: boolean) => void;
  triggerCrystalLayer: (hue: number) => void;
  triggerBlessingRipple: (
    hue?: number,
    origin?: { x: number; y: number }
  ) => void;
  triggerMeritParticle: (hue?: number, count?: number) => void;
}

export interface ScalarVizProps {
  mode?: ScalarMode;
  initialMode?: ScalarMode;
  showModeSelector?: boolean;
  elementMood?: string;
  onModeChange?: (mode: ScalarMode) => void;
  className?: string;
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
  return `hsla(${((h % 360) + 360) % 360}, ${s}%, ${l}%, ${a})`;
}

// ─── Modes & Element Mapping ─────────────────────────────────────
export const MODES: ScalarMode[] = [
  'living',
  'interference',
  'spiral',
  'standing',
  'particle-storm',
];

export const ELEMENT_HUES: Record<string, number> = {
  Fire: 25,
  Water: 200,
  Earth: 60,
  Air: 270,
  Wood: 130,
  Metal: 220,
  Cosmic: 280,
};

interface WaveLayer {
  seed: number;
  amp: number;
  freq: number;
  speed: number;
  baseHue: number;
  width: number;
}

interface BgRing {
  cx: number;
  cy: number;
  r: number;
  sides?: number;
}

interface Ripple {
  x: number;
  y: number;
  r: number;
  maxR: number;
  hue: number;
  alpha: number;
  speed: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  hue: number;
  alpha: number;
  life: number;
  maxLife: number;
}

interface CrystalBand {
  r: number;
  maxR: number;
  hue: number;
  alpha: number;
  speed: number;
}

const ScalarWaveVisualizer = forwardRef<ScalarVizAPI, ScalarVizProps>(
  (
    {
      mode: controlledMode,
      initialMode = 'living',
      showModeSelector = false,
      elementMood: initialElement = 'Cosmic',
      onModeChange,
      className = '',
    },
    ref
  ) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animRef = useRef<number | null>(null);
    const { scalarStatus } = useWebSocket();

    const [internalMode, setInternalMode] = useState<ScalarMode>(
      controlledMode ?? initialMode
    );
    const activeMode = controlledMode ?? internalMode;

    const [hovered, setHovered] = useState(false);

    // ── dynamic reactive visual states (stored in refs for 60fps loop) ──
    const scalarRef = useRef(scalarStatus);
    scalarRef.current = scalarStatus;

    const currentHueRef = useRef<number>(ELEMENT_HUES[initialElement] ?? 280);
    const targetHueRef = useRef<number>(ELEMENT_HUES[initialElement] ?? 280);
    const isHealingRef = useRef<boolean>(false);

    const ripplesRef = useRef<Ripple[]>([]);
    const particlesRef = useRef<Particle[]>([]);
    const crystalBandsRef = useRef<CrystalBand[]>([]);
    const seedRef = useRef<number>(Date.now());

    // ── Imperative API ────────────────────────────────────────────────
    useImperativeHandle(
      ref,
      () => ({
        setElementMood: (element: string) => {
          const target = ELEMENT_HUES[element] ?? 280;
          targetHueRef.current = target;
        },
        setHealingMood: (healing: boolean) => {
          isHealingRef.current = healing;
        },
        triggerCrystalLayer: (hue: number) => {
          crystalBandsRef.current.push({
            r: 10,
            maxR: 380,
            hue: isNaN(hue) ? currentHueRef.current : hue,
            alpha: 0.9,
            speed: 2.2,
          });
        },
        triggerBlessingRipple: (hue?: number, origin?: { x: number; y: number }) => {
          const canvas = canvasRef.current;
          const cx = origin?.x ?? (canvas ? canvas.width / (window.devicePixelRatio || 1) / 2 : 300);
          const cy = origin?.y ?? (canvas ? canvas.height / (window.devicePixelRatio || 1) / 2 : 300);
          const targetHue = hue ?? targetHueRef.current;

          ripplesRef.current.push({
            x: cx,
            y: cy,
            r: 5,
            maxR: Math.max(cx, cy) * 1.6 + 100,
            hue: targetHue,
            alpha: 1.0,
            speed: 3.5,
          });
        },
        triggerMeritParticle: (hue?: number, count: number = 6) => {
          const canvas = canvasRef.current;
          const cx = canvas ? canvas.width / (window.devicePixelRatio || 1) / 2 : 300;
          const cy = canvas ? canvas.height / (window.devicePixelRatio || 1) / 2 : 300;
          const targetHue = hue ?? targetHueRef.current;

          for (let i = 0; i < count; i++) {
            const angle = Math.random() * Math.PI * 2;
            const speed = 1.2 + Math.random() * 2.8;
            particlesRef.current.push({
              x: cx + (Math.random() - 0.5) * 20,
              y: cy + (Math.random() - 0.5) * 20,
              vx: Math.cos(angle) * speed,
              vy: Math.sin(angle) * speed,
              r: 1.5 + Math.random() * 2.5,
              hue: targetHue + (Math.random() - 0.5) * 30,
              alpha: 1.0,
              life: 0,
              maxLife: 60 + Math.random() * 60,
            });
          }
        },
      }),
      []
    );

    const handleModeSwitch = useCallback(
      (m: ScalarMode) => {
        setInternalMode(m);
        onModeChange?.(m);
      },
      [onModeChange]
    );

    // ── Main Canvas Rendering Effect ─────────────────────────────────
    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas || typeof canvas.getContext !== 'function') return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      let phase = 0;
      const s = seedRef.current;

      const layers: WaveLayer[] = [
        { seed: s, amp: 0.42, freq: 0.008, speed: 0.012, baseHue: 270, width: 2.5 },
        { seed: s * 3 + 1, amp: 0.28, freq: 0.013, speed: 0.018, baseHue: 190, width: 1.8 },
        { seed: s * 7 + 2, amp: 0.18, freq: 0.021, speed: 0.025, baseHue: 320, width: 1.2 },
      ];

      const prngs: Array<() => number> = layers.map((l) => seededRandom(l.seed));

      let bgRings: BgRing[] = [];
      const precomputeBg = (w: number, h: number) => {
        bgRings = [];
        const cx = w / 2;
        const cy = h / 2;
        const maxR = Math.sqrt(cx * cx + cy * cy);
        for (let r = 24; r < maxR; r += 26) {
          bgRings.push({ cx, cy, r });
        }
      };

      const draw = () => {
        const dpr = window.devicePixelRatio || 1;
        const w = canvas.width / dpr;
        const h = canvas.height / dpr;
        const t = phase;
        const mode = activeMode;
        const rate = scalarRef.current?.rate;
        const coherence = scalarRef.current?.coherence ?? 0.85;

        // Smooth hue transition toward target
        currentHueRef.current += (targetHueRef.current - currentHueRef.current) * 0.05;
        const mainHue = currentHueRef.current;

        // 8-second cosmic breathing pulse
        const breath = Math.sin(t * 0.785) * 0.12 + 0.88;

        // Clear canvas with soft trailing fade
        ctx.fillStyle = 'rgba(8, 8, 26, 0.20)';
        ctx.fillRect(0, 0, w, h);

        const cx = w / 2;
        const cy = h / 2;

        // ── Background Geometry Rings ────────────────────────────────
        ctx.save();
        ctx.strokeStyle = hsl(mainHue, 40, 45, 0.08);
        ctx.lineWidth = 0.6;
        for (const ring of bgRings) {
          ctx.beginPath();
          ctx.arc(ring.cx, ring.cy, ring.r * breath, 0, Math.PI * 2);
          ctx.stroke();
        }
        ctx.restore();

        // ── Healing Mood Glow ────────────────────────────────────────
        if (isHealingRef.current) {
          ctx.save();
          const healingGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(w, h) * 0.55);
          healingGrad.addColorStop(0, 'rgba(16, 185, 129, 0.12)');
          healingGrad.addColorStop(0.5, 'rgba(6, 182, 212, 0.06)');
          healingGrad.addColorStop(1, 'rgba(8, 8, 26, 0)');
          ctx.fillStyle = healingGrad;
          ctx.fillRect(0, 0, w, h);
          ctx.restore();
        } else {
          // Subtle central ambient field glow
          ctx.save();
          const glowGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(w, h) * 0.48);
          glowGrad.addColorStop(0, hsl(mainHue, 70, 50, 0.08 * breath));
          glowGrad.addColorStop(1, 'rgba(8, 8, 26, 0)');
          ctx.fillStyle = glowGrad;
          ctx.fillRect(0, 0, w, h);
          ctx.restore();
        }

        // ── Mode-Specific Visualizations ─────────────────────────────
        if (mode === 'living' || mode === 'interference') {
          // Render multi-layer wave fields
          for (let li = 0; li < layers.length; li++) {
            const l = layers[li];
            const prng = prngs[li];
            const layerHue = (mainHue + (li - 1) * 35 + t * 10) % 360;

            ctx.save();
            ctx.beginPath();

            ctx.shadowBlur = 18;
            ctx.shadowColor = hsl(layerHue, 85, 55, 0.6 * coherence);
            ctx.strokeStyle = hsl(layerHue, 80, 60, 0.85);
            ctx.lineWidth = l.width * (mode === 'living' ? breath : 1);

            for (let x = 0; x < w; x += 2) {
              const n1 = prng() * 2 - 1;
              const n2 = prng() * 2 - 1;
              const n3 = prng() * 2 - 1;
              const noise =
                n1 * 0.55 +
                n2 * 0.30 * Math.sin(x * l.freq + t * l.speed) +
                n3 * 0.15 * Math.cos(x * l.freq * 2.3 + t * l.speed * 0.7);
              const y = cy + noise * h * l.amp * (mode === 'living' ? breath : 1);
              if (x === 0) ctx.moveTo(x, y);
              else ctx.lineTo(x, y);
            }
            ctx.stroke();

            // Core highlight
            ctx.shadowBlur = 0;
            ctx.strokeStyle = hsl(layerHue, 50, 90, 0.6);
            ctx.lineWidth = l.width * 0.4;
            ctx.stroke();

            ctx.restore();
          }

          // In 'living' mode, add central mandala geometry petals
          if (mode === 'living') {
            ctx.save();
            const petalCount = 8;
            const radius = Math.min(w, h) * 0.18 * breath;
            ctx.translate(cx, cy);
            ctx.rotate(t * 0.15);

            for (let i = 0; i < petalCount; i++) {
              ctx.rotate((Math.PI * 2) / petalCount);
              ctx.beginPath();
              ctx.arc(radius * 0.5, 0, radius * 0.5, 0, Math.PI * 2);
              ctx.strokeStyle = hsl(mainHue + i * 15, 75, 65, 0.35);
              ctx.lineWidth = 1.2;
              ctx.stroke();
            }
            ctx.restore();
          }
        }

        if (mode === 'spiral' || mode === 'living') {
          // Logarithmic sacred spiral
          const maxR = Math.min(w, h) * (mode === 'living' ? 0.38 : 0.48) * breath;
          ctx.save();
          for (let a = 0; a < Math.PI * (mode === 'living' ? 4 : 6); a += 0.08) {
            const r = (a / (Math.PI * (mode === 'living' ? 4 : 6))) * maxR;
            const px = cx + Math.cos(a + t * 0.35) * r;
            const py = cy + Math.sin(a + t * 0.35) * r * 0.75;
            const hue = (mainHue + a * 25 + t * 15) % 360;

            ctx.fillStyle = hsl(hue, 85, 70, mode === 'living' ? 0.4 : 0.6);
            ctx.shadowBlur = 6;
            ctx.shadowColor = hsl(hue, 85, 55, 0.5);
            ctx.beginPath();
            ctx.arc(px, py, 1.4, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.restore();
        }

        if (mode === 'standing') {
          const barCount = 32;
          for (let i = 0; i < barCount; i++) {
            const bx = (i / barCount) * w;
            const amp = Math.abs(Math.sin(bx * 0.018 + t * 0.6)) * h * 0.35 * breath;
            const hue = (mainHue + i * 8 + t * 12) % 360;

            ctx.save();
            ctx.shadowBlur = 10;
            ctx.shadowColor = hsl(hue, 75, 55, 0.5);
            ctx.strokeStyle = hsl(hue, 70, 60, 0.65);
            ctx.lineWidth = 2.2;
            ctx.beginPath();
            ctx.moveTo(bx, cy - amp);
            ctx.lineTo(bx, cy + amp);
            ctx.stroke();
            ctx.restore();
          }
        }

        if (mode === 'particle-storm') {
          const sparkCount = 70;
          for (let i = 0; i < sparkCount; i++) {
            const li = i % layers.length;
            const prng = prngs[li];
            const sx = prng() * w;
            const n1 = prng() * 2 - 1;
            const n2 = prng() * 2 - 1;
            const noise = n1 * 0.55 + n2 * 0.35 * Math.sin(sx * 0.01 + t * 0.02);
            const sy = cy + noise * h * 0.35;
            const hue = (mainHue + t * 15 + i * 9) % 360;

            ctx.save();
            ctx.shadowBlur = 8;
            ctx.shadowColor = hsl(hue, 90, 65, 0.7);
            ctx.fillStyle = hsl(hue, 80, 85, 0.8);
            ctx.beginPath();
            ctx.arc(sx, sy, 1.2 + prng() * 1.6, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
          }
        }

        // ── Crystal Bands (expanding hexagonal resonance) ─────────────
        const activeCrystalBands = crystalBandsRef.current;
        for (let i = activeCrystalBands.length - 1; i >= 0; i--) {
          const band = activeCrystalBands[i];
          band.r += band.speed;
          band.alpha *= 0.985;

          ctx.save();
          ctx.beginPath();
          ctx.strokeStyle = hsl(band.hue, 85, 70, band.alpha);
          ctx.lineWidth = 2;
          ctx.shadowBlur = 12;
          ctx.shadowColor = hsl(band.hue, 90, 60, band.alpha);

          // Hexagon shape
          const sides = 6;
          for (let sIdx = 0; sIdx < sides; sIdx++) {
            const angle = (sIdx / sides) * Math.PI * 2 + t * 0.1;
            const hx = cx + Math.cos(angle) * band.r;
            const hy = cy + Math.sin(angle) * band.r;
            if (sIdx === 0) ctx.moveTo(hx, hy);
            else ctx.lineTo(hx, hy);
          }
          ctx.closePath();
          ctx.stroke();
          ctx.restore();

          if (band.r >= band.maxR || band.alpha < 0.02) {
            activeCrystalBands.splice(i, 1);
          }
        }

        // ── Blessing Ripples ─────────────────────────────────────────
        const activeRipples = ripplesRef.current;
        for (let i = activeRipples.length - 1; i >= 0; i--) {
          const ripple = activeRipples[i];
          ripple.r += ripple.speed;
          ripple.alpha *= 0.975;

          ctx.save();
          ctx.beginPath();
          ctx.arc(ripple.x, ripple.y, ripple.r, 0, Math.PI * 2);
          ctx.strokeStyle = hsl(ripple.hue, 90, 70, ripple.alpha);
          ctx.lineWidth = 2.5;
          ctx.shadowBlur = 16;
          ctx.shadowColor = hsl(ripple.hue, 95, 60, ripple.alpha);
          ctx.stroke();
          ctx.restore();

          if (ripple.r >= ripple.maxR || ripple.alpha < 0.02) {
            activeRipples.splice(i, 1);
          }
        }

        // ── Merit Particles ──────────────────────────────────────────
        const activeParticles = particlesRef.current;
        for (let i = activeParticles.length - 1; i >= 0; i--) {
          const p = activeParticles[i];
          p.x += p.vx;
          p.y += p.vy;
          p.vx *= 0.985;
          p.vy *= 0.985;
          p.life++;
          const progress = p.life / p.maxLife;
          const alpha = (1 - progress) * p.alpha;

          ctx.save();
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r * (1 - progress * 0.4), 0, Math.PI * 2);
          ctx.fillStyle = hsl(p.hue, 95, 75, alpha);
          ctx.shadowBlur = 10;
          ctx.shadowColor = hsl(p.hue, 90, 60, alpha);
          ctx.fill();
          ctx.restore();

          if (p.life >= p.maxLife || alpha < 0.02) {
            activeParticles.splice(i, 1);
          }
        }

        // ── HUD Information ──────────────────────────────────────────
        ctx.shadowBlur = 0;
        ctx.fillStyle = 'rgba(180, 160, 220, 0.75)';
        ctx.font = `${Math.max(10, Math.round(w / 75))}px "JetBrains Mono", monospace`;
        ctx.textAlign = 'left';
        ctx.fillText(
          `λ ${rate != null ? Number(rate).toFixed(2) : '528.00'} Hz  ·  seed ${s & 0xffff}  ·  ${mode}`,
          12,
          Math.max(18, Math.round(h * 0.05))
        );

        phase += 0.016;
        animRef.current = requestAnimationFrame(draw);
      };

      const resize = () => {
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        precomputeBg(rect.width, rect.height);
      };

      resize();
      window.addEventListener('resize', resize);
      draw();

      return () => {
        if (animRef.current !== null) {
          cancelAnimationFrame(animRef.current);
        }
        window.removeEventListener('resize', resize);
      };
    }, [activeMode]);

    return (
      <div
        className={`relative w-full h-full group overflow-hidden ${className}`}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <canvas ref={canvasRef} className="w-full h-full block" />

        {/* Mode switcher (optional overlay) */}
        {showModeSelector && (
          <div
            className={`absolute bottom-2 right-2 flex gap-1 transition-opacity duration-300 ${
              hovered ? 'opacity-100' : 'opacity-0'
            }`}
          >
            {MODES.map((m) => (
              <button
                key={m}
                onClick={() => handleModeSwitch(m)}
                className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors font-mono ${
                  activeMode === m
                    ? 'bg-purple-600/80 text-white border-purple-400/40'
                    : 'bg-gray-900/60 text-gray-400 border-white/10 hover:border-purple-400/30 hover:text-purple-300'
                }`}
              >
                {m
                  .split('-')
                  .map((w) => w[0].toUpperCase() + w.slice(1))
                  .join(' ')}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }
);

ScalarWaveVisualizer.displayName = 'ScalarWaveVisualizer';

export default ScalarWaveVisualizer;
