/**
 * Scalar Wave Visualizer — multi-layer interference pattern display.
 * Renders PRNG-driven scalar wave interference with glow, particles,
 * color cycling, and mode switching. Self-contained — uses internal
 * WebSocket hook for rate data.
 * @component
 */
import React, { useRef, useEffect, useState } from 'react';
import { useWebSocketStable as useWebSocket } from '../../hooks/useWebSocketStable';

type ScalarMode = 'interference' | 'spiral' | 'standing' | 'particle-storm';

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

// ─── Modes ───────────────────────────────────────────────────────
const MODES: ScalarMode[] = ['interference', 'spiral', 'standing', 'particle-storm'];

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

const ScalarWaveVisualizer: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number | null>(null);
  const { scalarStatus } = useWebSocket();
  const [mode, setMode] = useState<ScalarMode>('interference');
  const [hovered, setHovered] = useState(false);

  // ── refs so the draw loop reads latest values without restarting ──
  const scalarRef = useRef(scalarStatus);
  scalarRef.current = scalarStatus;
  const seedRef = useRef<number>(Date.now());

  // Only restart the animation loop on mode change.
  // seed, scalarStatus, and canvas resize are read from refs inside the loop.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let phase = 0;
    const s = seedRef.current;

    // ── wave layer configs ────────────────────────────────────
    const layers: WaveLayer[] = [
      { seed: s, amp: 0.42, freq: 0.008, speed: 0.012, hue: 270, width: 2.5 },
      { seed: s * 3 + 1, amp: 0.28, freq: 0.013, speed: 0.018, hue: 190, width: 1.8 },
      { seed: s * 7 + 2, amp: 0.18, freq: 0.021, speed: 0.025, hue: 320, width: 1.2 },
    ];

    const prngs: Array<() => number> = layers.map((l) => seededRandom(l.seed));

    // ── background field rings (precomputed) ──────────────────
    let bgRings: BgRing[] = [];
    const precomputeBg = (w: number, h: number) => {
      bgRings = [];
      const cx = w / 2;
      const cy = h / 2;
      const maxR = Math.sqrt(cx * cx + cy * cy);
      for (let r = 30; r < maxR; r += 22) {
        bgRings.push({ cx, cy, r });
      }
    };

    // ── draw ──────────────────────────────────────────────────
    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      const t = phase;
      const currentMode = mode;
      // read latest rate from ref — no effect restart on WebSocket updates
      const rate = scalarRef.current?.rate;

      // phosphor fade — translucent clear for trail persistence
      ctx.fillStyle = 'rgba(8, 8, 24, 0.22)';
      ctx.fillRect(0, 0, w, h);

      // ── background field rings ───────────────────────────
      ctx.strokeStyle = 'rgba(88, 66, 144, 0.12)';
      ctx.lineWidth = 0.5;
      for (const ring of bgRings) {
        ctx.beginPath();
        ctx.arc(ring.cx, ring.cy, ring.r, 0, Math.PI * 2);
        ctx.stroke();
      }

      // central subtle glow
      const glowGrad = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.min(w, h) * 0.45);
      glowGrad.addColorStop(0, 'rgba(88, 66, 180, 0.06)');
      glowGrad.addColorStop(1, 'rgba(8, 8, 24, 0)');
      ctx.fillStyle = glowGrad;
      ctx.fillRect(0, 0, w, h);

      // ── draw each wave layer ─────────────────────────────
      for (let li = 0; li < layers.length; li++) {
        const l = layers[li];
        const prng = prngs[li];
        const hue = (l.hue + t * 12) % 360;

        ctx.save();
        ctx.beginPath();

        // glow pass
        ctx.shadowBlur = 16;
        ctx.shadowColor = hsl(hue, 80, 55, 0.7);
        ctx.strokeStyle = hsl(hue, 80, 55, 0.85);
        ctx.lineWidth = l.width;

        for (let x = 0; x < w; x++) {
          const n1 = prng() * 2 - 1;
          const n2 = prng() * 2 - 1;
          const n3 = prng() * 2 - 1;
          const noise =
            n1 * 0.55 +
            n2 * 0.30 * Math.sin(x * l.freq + t * l.speed) +
            n3 * 0.15 * Math.cos(x * l.freq * 2.3 + t * l.speed * 0.7);
          const y = h / 2 + noise * h * l.amp;
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

      // ── particle sparks along wave crests ─────────────────
      if (currentMode === 'particle-storm' || currentMode === 'interference') {
        const sparkCount = currentMode === 'particle-storm' ? 60 : 18;
        for (let i = 0; i < sparkCount; i++) {
          const li = i % layers.length;
          const prng = prngs[li];
          const sx = prng() * w;
          const n1 = prng() * 2 - 1;
          const n2 = prng() * 2 - 1;
          const n3 = prng() * 2 - 1;
          const noise =
            n1 * 0.55 +
            n2 * 0.30 * Math.sin(sx * layers[li].freq + t * layers[li].speed) +
            n3 * 0.15 * Math.cos(sx * layers[li].freq * 2.3 + t * layers[li].speed * 0.7);
          const sy = h / 2 + noise * h * layers[li].amp;
          const hue = (layers[li].hue + t * 12 + i * 11) % 360;
          const alpha = 0.35 + prng() * 0.5;

          ctx.save();
          ctx.shadowBlur = 8;
          ctx.shadowColor = hsl(hue, 90, 65, alpha);
          ctx.fillStyle = hsl(hue, 70, 85, alpha);
          ctx.beginPath();
          ctx.arc(sx, sy, 1.0 + prng() * 1.4, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
      }

      // ── standing-wave vertical bars (mode) ────────────────
      if (currentMode === 'standing') {
        const barCount = 28;
        for (let i = 0; i < barCount; i++) {
          const bx = (i / barCount) * w;
          const prng = prngs[i % 3];
          const amp = Math.abs(Math.sin(bx * 0.015 + t * 0.6)) * h * 0.35;
          const hue = (260 + i * 8 + t * 15) % 360;
          ctx.save();
          ctx.shadowBlur = 10;
          ctx.shadowColor = hsl(hue, 75, 55, 0.5);
          ctx.strokeStyle = hsl(hue, 70, 60, 0.6);
          ctx.lineWidth = 2.5;
          ctx.beginPath();
          ctx.moveTo(bx, h / 2 - amp);
          ctx.lineTo(bx, h / 2 + amp);
          ctx.stroke();
          ctx.restore();
        }
      }

      // ── spiral mode ───────────────────────────────────────
      if (currentMode === 'spiral') {
        const cx = w / 2;
        const cy = h / 2;
        const maxR = Math.min(w, h) * 0.48;
        ctx.save();
        for (let a = 0; a < Math.PI * 6; a += 0.06) {
          const r = (a / (Math.PI * 6)) * maxR;
          const px = cx + Math.cos(a + t * 0.4) * r;
          const py = cy + Math.sin(a + t * 0.4) * r * 0.7;
          const hue = (280 + a * 20 + t * 18) % 360;
          ctx.fillStyle = hsl(hue, 80, 65, 0.5);
          ctx.shadowBlur = 6;
          ctx.shadowColor = hsl(hue, 80, 55, 0.6);
          ctx.beginPath();
          ctx.arc(px, py, 1.6, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }

      // ── HUD ───────────────────────────────────────────────
      ctx.shadowBlur = 0;
      ctx.fillStyle = 'rgba(180, 160, 220, 0.85)';
      ctx.font = `${Math.max(10, Math.round(w / 70))}px "JetBrains Mono", "Fira Code", monospace`;
      ctx.textAlign = 'left';
      ctx.fillText(
        `λ ${rate != null ? Number(rate).toFixed(2) : '—'} Hz  ·  seed ${s & 0xffff}  ·  ${currentMode}`,
        10,
        Math.max(16, Math.round(h * 0.06))
      );

      phase += 0.016;
      animRef.current = requestAnimationFrame(draw);
    };

    // ── resize handler ──────────────────────────────────────
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
  }, [mode]); // ← only mode changes restart the loop

  return (
    <div
      className="relative w-full h-full group"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <canvas ref={canvasRef} className="w-full h-full block" />

      {/* mode switcher — visible on hover */}
      <div
        className={`absolute bottom-2 right-2 flex gap-1 transition-opacity duration-300 ${
          hovered ? 'opacity-100' : 'opacity-0'
        }`}
      >
        {MODES.map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors font-mono ${
              mode === m
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
    </div>
  );
};

export default ScalarWaveVisualizer;
