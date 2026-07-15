import React, { useRef, useEffect, useMemo } from 'react';

interface SigilCoord {
  x: number;
  y: number;
  value?: number;
  letter?: string;
}

interface RateData {
  values: number[];
  name: string;
  potency?: number;
}

interface RitualVisualizationProps {
  sigil?: {
    kamea?: string;
    reduced?: string;
    coordinates?: SigilCoord[];
    svg?: string;
  };
  rates?: {
    signature?: RateData;
    balancing?: RateData[];
  };
  genre?: string;
  kameaPlanet?: string;
}

const PLANETARY_FREQUENCIES: Record<string, number> = {
  moon: 210.42, sun: 126.22, earth: 136.10, venus: 221.23,
  mercury: 281.00, mars: 289.00, jupiter: 183.58, saturn: 147.85,
};

const SOLFEGGIO = [396, 417, 528, 639, 741, 852];

const GENRE_COLORS: Record<string, string> = {
  healing: '#00A86B', victory: '#dc143c', alchemist: '#daa520',
  dharani: '#8a2be2', compassion: '#ff69b4', wisdom: '#6495ed',
  protection: '#228b22', fun_parable: '#6495ed',
};

const KAMEA_GRID_3X3: number[][] = [
  [8, 1, 6],
  [3, 5, 7],
  [4, 9, 2],
];

function WaveCanvas({ freq, color, label }: { freq: number; color: string; label: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    let phase = 0;

    const draw = () => {
      ctx.fillStyle = 'rgba(10, 5, 20, 0.15)';
      ctx.fillRect(0, 0, W, H);

      ctx.strokeStyle = 'rgba(139, 92, 246, 0.08)';
      ctx.lineWidth = 1;
      for (let i = 0; i < W; i += 20) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, H);
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.moveTo(0, H / 2);
      ctx.lineTo(W, H / 2);
      ctx.stroke();

      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.shadowBlur = 12;
      ctx.shadowColor = color;
      ctx.beginPath();

      const cycles = Math.max(2, freq / 50);
      for (let x = 0; x < W; x++) {
        const t = (x / W) * Math.PI * 2 * cycles + phase;
        const amp = H * 0.3;
        const y = H / 2 + Math.sin(t) * amp * Math.exp(-Math.abs((x - W / 2) / W) * 1.5);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      phase += 0.04;
      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [freq, color]);

  return (
    <div className="flex flex-col items-center gap-1">
      <canvas ref={canvasRef} width={280} height={70} className="w-full rounded-lg" style={{ background: 'rgba(10, 5, 20, 0.6)' }} />
      <div className="flex items-center gap-2 text-[10px] font-mono">
        <span style={{ color }}>{label}</span>
        <span className="text-gray-500">{freq.toFixed(2)} Hz</span>
      </div>
    </div>
  );
}

function RateDial({ rate, label, color }: { rate: number[]; label: string; color: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative w-16 h-16 rounded-full border-2 flex items-center justify-center" style={{ borderColor: `${color}40`, background: `radial-gradient(circle, ${color}15, transparent)` }}>
        <div className="text-center">
          <div className="text-xs font-bold font-mono" style={{ color }}>{rate.join('-')}</div>
        </div>
        <div className="absolute inset-0 rounded-full border border-transparent"
          style={{ boxShadow: `inset 0 0 12px ${color}30` }} />
      </div>
      <span className="text-[8px] text-gray-500 font-mono uppercase tracking-wider text-center max-w-[80px] leading-tight">
        {label}
      </span>
    </div>
  );
}

function KameaGrid({ coords, color }: { coords: SigilCoord[]; color: string }) {
  const cellSize = 52;
  const padding = 20;
  const svgSize = cellSize * 3 + padding * 2;

  const cellCenter = (x: number, y: number) => ({
    cx: padding + x * cellSize + cellSize / 2,
    cy: padding + y * cellSize + cellSize / 2,
  });

  const pathData = useMemo(() => {
    if (coords.length < 2) return '';
    return coords.map((c, i) => {
      const { cx, cy } = cellCenter(c.x, c.y);
      return `${i === 0 ? 'M' : 'L'} ${cx} ${cy}`;
    }).join(' ');
  }, [coords]);

  return (
    <svg viewBox={`0 0 ${svgSize} ${svgSize}`} className="w-full max-w-[220px] mx-auto">
      <defs>
        <filter id="kamea-glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {KAMEA_GRID_3X3.map((row, y) =>
        row.map((val, x) => {
          const { cx, cy } = cellCenter(x, y);
          return (
            <g key={`${x}-${y}`}>
              <rect
                x={padding + x * cellSize + 2}
                y={padding + y * cellSize + 2}
                width={cellSize - 4}
                height={cellSize - 4}
                rx={6}
                fill="rgba(15, 10, 25, 0.6)"
                stroke="rgba(139, 92, 246, 0.12)"
                strokeWidth={1}
              />
              <text
                x={cx}
                y={cy + 6}
                textAnchor="middle"
                fontSize={16}
                fontFamily="monospace"
                fontWeight="bold"
                fill="rgba(148, 163, 184, 0.5)"
              >
                {val}
              </text>
            </g>
          );
        })
      )}

      {coords.length > 1 && (
        <path
          d={pathData}
          fill="none"
          stroke={color}
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#kamea-glow)"
          opacity={0.9}
        />
      )}

      {coords.length > 0 && (() => {
        const start = cellCenter(coords[0].x, coords[0].y);
        const end = cellCenter(coords[coords.length - 1].x, coords[coords.length - 1].y);
        return (
          <>
            <circle cx={start.cx} cy={start.cy} r={6} fill="none" stroke={color} strokeWidth={2.5} filter="url(#kamea-glow)" />
            <line x1={end.cx - 5} y1={end.cy} x2={end.cx + 5} y2={end.cy} stroke="#ff00ff" strokeWidth={3} filter="url(#kamea-glow)" />
            <line x1={end.cx} y1={end.cy - 5} x2={end.cx} y2={end.cy + 5} stroke="#ff00ff" strokeWidth={3} filter="url(#kamea-glow)" />
          </>
        );
      })()}
    </svg>
  );
}

export default function RitualVisualization({ sigil, rates, genre, kameaPlanet }: RitualVisualizationProps) {
  const accentColor = GENRE_COLORS[genre || ''] || '#8b5cf6';
  const planetFreq = kameaPlanet ? PLANETARY_FREQUENCIES[kameaPlanet.toLowerCase()] || 136.10 : 136.10;
  const coords = sigil?.coordinates || [];

  return (
    <div className="space-y-4">
      <div className="text-[10px] font-mono uppercase tracking-widest text-amber-400/70">
        Ritual Visualization
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-white/5 bg-black/30 p-3 space-y-2">
          <div className="text-[9px] font-mono uppercase text-gray-500 mb-1">Carrier Waves</div>
          <WaveCanvas freq={planetFreq} color={accentColor} label={kameaPlanet ? `${kameaPlanet} freq` : 'OM'} />
          <WaveCanvas freq={528} color="#06b6d4" label="Solfeggio MI" />
        </div>

        <div className="rounded-xl border border-white/5 bg-black/30 p-3">
          <div className="text-[9px] font-mono uppercase text-gray-500 mb-2">Kamea Grid Trace</div>
          <KameaGrid coords={coords} color={accentColor} />
          {sigil?.reduced && (
            <div className="text-center mt-2 text-[9px] font-mono text-gray-500">
              Sigil: <span style={{ color: accentColor }}>{sigil.reduced}</span> on {sigil.kamea || 'moon'} grid
            </div>
          )}
        </div>
      </div>

      {rates && (rates.signature || rates.balancing) && (
        <div className="rounded-xl border border-white/5 bg-black/30 p-3">
          <div className="text-[9px] font-mono uppercase text-gray-500 mb-3">Radionic Rates</div>
          <div className="flex items-start justify-around gap-2 flex-wrap">
            {rates.signature && (
              <RateDial rate={rates.signature.values} label={rates.signature.name.slice(0, 30) + '...'} color={accentColor} />
            )}
            {rates.balancing?.map((b, i) => (
              <RateDial key={i} rate={b.values} label={`Balance-${i + 1}`} color="#06b6d4" />
            ))}
          </div>
          {rates.signature?.potency !== undefined && rates.signature.potency > 0 && (
            <div className="mt-2 text-center text-[9px] font-mono text-gray-600">
              Potency: {(rates.signature.potency * 100).toFixed(1)}%
            </div>
          )}
          {rates.balancing?.[0]?.potency !== undefined && (
            <div className="mt-1 text-center text-[9px] font-mono text-gray-600">
              Balance Potency: {(rates.balancing[0].potency * 100).toFixed(1)}%
            </div>
          )}
        </div>
      )}
    </div>
  );
}
