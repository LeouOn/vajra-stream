import React, { useState, useMemo } from 'react';

interface PlanetPosition {
  longitude: number;
  sign?: string;
  degree?: number;
  retrograde?: boolean;
  house?: number;
}

type AspectType = 'conjunction' | 'opposition' | 'trine' | 'square' | 'sextile';

interface Aspect {
  planet1: string;
  planet2: string;
  type: AspectType;
  orb: number;
  exact: number;
}

interface AspectChartProps {
  positions: Record<string, PlanetPosition>;
  size?: number;
}

const PLANET_GLYPHS: Record<string, string> = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂',
  jupiter: '♃', saturn: '♄', uranus: '♅', neptune: '♆', pluto: '♇',
  north_node: '☊', ascendant: 'Asc', midheaven: 'MC',
};

const PLANET_COLORS: Record<string, string> = {
  sun: '#fbbf24', moon: '#e0e7ff', mercury: '#22d3ee', venus: '#f472b6',
  mars: '#ef4444', jupiter: '#f59e0b', saturn: '#94a3b8', uranus: '#a78bfa',
  neptune: '#60a5fa', pluto: '#6b21a8', north_node: '#10b981',
  ascendant: '#fde68a', midheaven: '#fcd34d',
};

const ASPECT_CONFIG: Record<AspectType, { angle: number; orb: number; color: string; label: string; symbol: string }> = {
  conjunction: { angle: 0, orb: 8, color: '#e2e8f0', label: 'Conjunction', symbol: '☉' },
  opposition: { angle: 180, orb: 8, color: '#ef4444', label: 'Opposition', symbol: '☉' },
  trine: { angle: 120, orb: 8, color: '#3b82f6', label: 'Trine', symbol: '△' },
  square: { angle: 90, orb: 8, color: '#f97316', label: 'Square', symbol: '□' },
  sextile: { angle: 60, orb: 6, color: '#22c55e', label: 'Sextile', symbol: '✦' },
};

const ZODIAC_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
const ZODIAC_GLYPHS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];

function angularDistance(lon1: number, lon2: number): number {
  let diff = Math.abs(lon1 - lon2) % 360;
  if (diff > 180) diff = 360 - diff;
  return diff;
}

function calculateAspects(positions: Record<string, PlanetPosition>): Aspect[] {
  const planetNames = Object.keys(positions).filter(n => n !== 'ascendant' && n !== 'midheaven');
  const aspects: Aspect[] = [];

  for (let i = 0; i < planetNames.length; i++) {
    for (let j = i + 1; j < planetNames.length; j++) {
      const p1 = planetNames[i];
      const p2 = planetNames[j];
      const dist = angularDistance(positions[p1].longitude, positions[p2].longitude);

      for (const [type, config] of Object.entries(ASPECT_CONFIG)) {
        const orb = Math.abs(dist - config.angle);
        if (orb <= config.orb) {
          aspects.push({
            planet1: p1,
            planet2: p2,
            type: type as AspectType,
            orb: orb,
            exact: config.angle,
          });
          break;
        }
      }
    }
  }
  return aspects.sort((a, b) => a.orb - b.orb);
}

export default function AspectChart({ positions, size = 420 }: AspectChartProps) {
  const [visibleAspects, setVisibleAspects] = useState<Set<AspectType>>(
    new Set(['conjunction', 'opposition', 'trine', 'square', 'sextile'])
  );

  const aspects = useMemo(() => calculateAspects(positions), [positions]);

  const cx = size / 2;
  const cy = size / 2;
  const outerR = size * 0.46;
  const zodiacR = size * 0.40;
  const planetR = size * 0.33;
  const innerR = size * 0.14;

  const getPlanetPos = (longitude: number, radius: number) => {
    const angle = (longitude - 90) * (Math.PI / 180);
    return {
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    };
  };

  const toggleAspect = (type: AspectType) => {
    setVisibleAspects(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const filteredAspects = aspects.filter(a => visibleAspects.has(a.type));

  return (
    <div className="flex flex-col items-center gap-3">
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[460px]">
        <defs>
          <radialGradient id="chart-bg">
            <stop offset="0%" stopColor="#0f0a1e" stopOpacity={0.6} />
            <stop offset="100%" stopColor="#020617" stopOpacity={0.3} />
          </radialGradient>
        </defs>

        <circle cx={cx} cy={cy} r={outerR} fill="url(#chart-bg)" stroke="rgba(139, 92, 246, 0.2)" strokeWidth={1.5} />
        <circle cx={cx} cy={cy} r={zodiacR} fill="none" stroke="rgba(139, 92, 246, 0.15)" strokeWidth={1} />
        <circle cx={cx} cy={cy} r={planetR} fill="none" stroke="rgba(139, 92, 246, 0.08)" strokeWidth={1} />
        <circle cx={cx} cy={cy} r={innerR} fill="none" stroke="rgba(139, 92, 246, 0.1)" strokeWidth={1} />

        {ZODIAC_SIGNS.map((sign, i) => {
          const startAngle = (i * 30 - 90) * (Math.PI / 180);
          const endAngle = ((i + 1) * 30 - 90) * (Math.PI / 180);
          const x1 = cx + Math.cos(startAngle) * zodiacR;
          const y1 = cy + Math.sin(startAngle) * zodiacR;
          const x2 = cx + Math.cos(endAngle) * zodiacR;
          const y2 = cy + Math.sin(endAngle) * zodiacR;
          const midAngle = ((i * 30 + 15) - 90) * (Math.PI / 180);
          const labelR = (zodiacR + outerR) / 2;
          const lx = cx + Math.cos(midAngle) * labelR;
          const ly = cy + Math.sin(midAngle) * labelR;

          return (
            <g key={sign}>
              <line x1={cx + Math.cos(startAngle) * innerR} y1={cy + Math.sin(startAngle) * innerR}
                    x2={x1} y2={y1} stroke="rgba(139, 92, 246, 0.06)" strokeWidth={0.5} />
              <line x1={x1} y1={y1} x2={cx + Math.cos(startAngle) * outerR} y2={cy + Math.sin(startAngle) * outerR}
                    stroke="rgba(139, 92, 246, 0.15)" strokeWidth={1} />
              <text x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
                    fontSize={size * 0.032} fill="#94a3b8" opacity={0.5}>
                {ZODIAC_GLYPHS[i]}
              </text>
            </g>
          );
        })}

        {filteredAspects.map((aspect, i) => {
          const p1 = getPlanetPos(positions[aspect.planet1].longitude, planetR * 0.95);
          const p2 = getPlanetPos(positions[aspect.planet2].longitude, planetR * 0.95);
          const config = ASPECT_CONFIG[aspect.type];
          const opacity = Math.max(0.3, 1 - aspect.orb / config.orb);

          return (
            <line
              key={`aspect-${i}`}
              x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke={config.color}
              strokeWidth={aspect.orb < 2 ? 2 : 1.5}
              opacity={opacity * 0.7}
              strokeLinecap="round"
            />
          );
        })}

        {Object.entries(positions).map(([name, pos]) => {
          const p = getPlanetPos(pos.longitude, planetR);
          const color = PLANET_COLORS[name] || '#94a3b8';
          const glyph = PLANET_GLYPHS[name] || name[0].toUpperCase();

          return (
            <g key={name}>
              <circle cx={p.x} cy={p.y} r={size * 0.025} fill={color} opacity={0.2} />
              <text x={p.x} y={p.y + size * 0.008} textAnchor="middle"
                    fontSize={size * 0.035} fill={color} fontWeight="bold">
                {glyph}
              </text>
              {pos.retrograde && (
                <text x={p.x + size * 0.02} y={p.y - size * 0.015}
                      fontSize={size * 0.02} fill="#ef4444" opacity={0.7}>℞</text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="flex flex-wrap gap-2 justify-center">
        {(Object.keys(ASPECT_CONFIG) as AspectType[]).map(type => {
          const config = ASPECT_CONFIG[type];
          const isActive = visibleAspects.has(type);
          const count = aspects.filter(a => a.type === type).length;
          return (
            <button
              key={type}
              type="button"
              onClick={() => toggleAspect(type)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-mono transition-all border"
              style={{
                borderColor: isActive ? config.color : 'rgba(255,255,255,0.1)',
                backgroundColor: isActive ? `${config.color}15` : 'transparent',
                color: isActive ? config.color : '#64748b',
                opacity: isActive ? 1 : 0.5,
              }}
            >
              <span style={{ color: config.color }}>{config.symbol}</span>
              <span>{config.label}</span>
              <span className="text-[8px] opacity-60">({count})</span>
            </button>
          );
        })}
      </div>

      <div className="max-w-md w-full space-y-1">
        <div className="text-[9px] font-mono uppercase text-gray-500 text-center mb-1">Active Aspects</div>
        {filteredAspects.slice(0, 8).map((aspect, i) => {
          const config = ASPECT_CONFIG[aspect.type];
          return (
            <div key={i} className="flex items-center justify-between text-[10px] font-mono px-2 py-0.5 rounded"
                 style={{ backgroundColor: `${config.color}08` }}>
              <span className="flex items-center gap-1.5">
                <span style={{ color: PLANET_COLORS[aspect.planet1] }}>
                  {PLANET_GLYPHS[aspect.planet1] || aspect.planet1}
                </span>
                <span style={{ color: config.color }}>{config.symbol}</span>
                <span style={{ color: PLANET_COLORS[aspect.planet2] }}>
                  {PLANET_GLYPHS[aspect.planet2] || aspect.planet2}
                </span>
              </span>
              <span className="text-gray-500">
                {aspect.orb.toFixed(2)}° orb
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
