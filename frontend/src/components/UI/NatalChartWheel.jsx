import React, { useMemo } from 'react';
import { Compass } from 'lucide-react';

const PLANET_GLYPHS = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂',
  jupiter: '♃', saturn: '♄', uranus: '♅', neptune: '♆', pluto: '♇',
  north_node: '☊', south_node: '☋', chiron: '⚷', ascendant: '⟪', midheaven: '⟪',
};

const SIGN_GLYPHS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];
const SIGN_NAMES = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
  'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];

const ELEMENT_COLORS = {
  Fire: '#dc2626',
  Earth: '#a16207',
  Air: '#ca8a04',
  Water: '#2563eb',
};

const SIGN_ELEMENT = ['Fire', 'Earth', 'Air', 'Water', 'Fire', 'Earth',
  'Air', 'Water', 'Fire', 'Earth', 'Air', 'Water'];

const PLANET_COLORS = {
  sun: '#fbbf24', moon: '#e5e7eb', mercury: '#a78bfa', venus: '#f472b6',
  mars: '#ef4444', jupiter: '#fb923c', saturn: '#fde047',
  uranus: '#22d3ee', neptune: '#60a5fa', pluto: '#a855f7',
  chiron: '#94a3b8', north_node: '#64748b', south_node: '#64748b',
};

const toSvgAngle = (longitude, ascendant) => {
  const offset = (longitude - ascendant + 360) % 360;
  return (180 - offset + 360) % 360;
};

const polarToXY = (cx, cy, r, deg) => {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
};

const describeArc = (cx, cy, r, startDeg, endDeg) => {
  const start = polarToXY(cx, cy, r, startDeg);
  const end = polarToXY(cx, cy, r, endDeg);
  const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  const sweep = endDeg > startDeg ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} ${sweep} ${end.x} ${end.y}`;
};

const ZODIAC_R_OUTER = 200;
const ZODIAC_R_INNER = 170;
const HOUSE_R_OUTER = 170;
const HOUSE_R_INNER = 145;
const PLANET_R = 130;
const CENTER = 200;

function SignSegment({ signIndex, ascLon }) {
  const startLon = signIndex * 30;
  const endLon = (signIndex + 1) * 30;
  const startAngle = toSvgAngle(startLon, ascLon);
  const endAngle = toSvgAngle(endLon, ascLon);
  const midAngle = toSvgAngle(startLon + 15, ascLon);
  const midLabel = polarToXY(CENTER, CENTER, (ZODIAC_R_OUTER + ZODIAC_R_INNER) / 2, midAngle);
  const element = SIGN_ELEMENT[signIndex];
  const fill = ELEMENT_COLORS[element];

  return (
    <g>
      <path
        d={`${describeArc(CENTER, CENTER, ZODIAC_R_OUTER, startAngle, endAngle)} L ${polarToXY(CENTER, CENTER, ZODIAC_R_INNER, endAngle).x} ${polarToXY(CENTER, CENTER, ZODIAC_R_INNER, endAngle).y} ${describeArc(CENTER, CENTER, ZODIAC_R_INNER, endAngle, startAngle)} Z`}
        fill={fill}
        fillOpacity={0.15}
        stroke={fill}
        strokeOpacity={0.5}
        strokeWidth={0.5}
      />
      <text
        x={midLabel.x}
        y={midLabel.y}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={20}
        fill={fill}
        opacity={0.85}
        style={{ pointerEvents: 'none' }}
      >
        {SIGN_GLYPHS[signIndex]}
      </text>
    </g>
  );
}

function HouseCusp({ index, longitude, ascLon }) {
  const angle = toSvgAngle(longitude, ascLon);
  const tickInner = polarToXY(CENTER, CENTER, HOUSE_R_INNER - 4, angle);
  const tickOuter = polarToXY(CENTER, CENTER, HOUSE_R_OUTER, angle);
  const labelPos = polarToXY(CENTER, CENTER, (HOUSE_R_OUTER + HOUSE_R_INNER) / 2, angle);
  return (
    <g>
      <line
        x1={tickInner.x} y1={tickInner.y}
        x2={tickOuter.x} y2={tickOuter.y}
        stroke="#94a3b8"
        strokeWidth={1}
        opacity={0.5}
      />
      {index % 3 === 0 && (
        <text
          x={labelPos.x}
          y={labelPos.y}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={9}
          fill="#64748b"
          style={{ pointerEvents: 'none', fontFamily: 'monospace' }}
        >
          {index}
        </text>
      )}
    </g>
  );
}

function AngleMark({ name, longitude, ascLon, label, color }) {
  const angle = toSvgAngle(longitude, ascLon);
  const inner = polarToXY(CENTER, CENTER, PLANET_R - 4, angle);
  const outer = polarToXY(CENTER, CENTER, ZODIAC_R_OUTER - 2, angle);
  const labelPos = polarToXY(CENTER, CENTER, ZODIAC_R_OUTER - 14, angle);
  return (
    <g>
      <line
        x1={inner.x} y1={inner.y}
        x2={outer.x} y2={outer.y}
        stroke={color}
        strokeWidth={2}
      />
      <text
        x={labelPos.x}
        y={labelPos.y}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={10}
        fill={color}
        fontWeight="bold"
        style={{ pointerEvents: 'none', fontFamily: 'monospace' }}
      >
        {label}
      </text>
    </g>
  );
}

function PlanetMarker({ name, data, ascLon, index, total, color }) {
  const angle = toSvgAngle(data.longitude, ascLon);
  const r = PLANET_R - (index * 4);
  const pos = polarToXY(CENTER, CENTER, r, angle);
  const glyph = PLANET_GLYPHS[name] || '●';
  const degText = `${Math.floor(data.degree || 0)}°`;

  return (
    <g style={{ pointerEvents: 'none' }}>
      <circle cx={pos.x} cy={pos.y} r={7.5} fill="#0f172a" stroke={color} strokeWidth={1.5} />
      <text
        x={pos.x}
        y={pos.y + 0.5}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={9}
        fill={color}
        style={{ fontFamily: 'serif' }}
      >
        {glyph}
      </text>
      <text
        x={pos.x}
        y={pos.y + 16}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={7}
        fill="#94a3b8"
        style={{ fontFamily: 'monospace' }}
      >
        {degText}
      </text>
    </g>
  );
}

function Legend({ data }) {
  if (!data) return null;
  const western = data.western || {};
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] font-mono">
      <div className="bg-black/40 border border-white/5 rounded-lg p-2">
        <div className="text-gray-500 uppercase tracking-wider text-[8px]">Element</div>
        <div className="text-amber-300 font-bold">{western.dominant_element || '—'}</div>
      </div>
      <div className="bg-black/40 border border-white/5 rounded-lg p-2">
        <div className="text-gray-500 uppercase tracking-wider text-[8px]">Modality</div>
        <div className="text-amber-300 font-bold">{western.dominant_modality || '—'}</div>
      </div>
      <div className="bg-black/40 border border-white/5 rounded-lg p-2">
        <div className="text-gray-500 uppercase tracking-wider text-[8px]">ASC</div>
        <div className="text-cyan-300 font-bold">{western.positions?.ascendant?.formatted || '—'}</div>
      </div>
      <div className="bg-black/40 border border-white/5 rounded-lg p-2">
        <div className="text-gray-500 uppercase tracking-wider text-[8px]">MC</div>
        <div className="text-cyan-300 font-bold">{western.positions?.midheaven?.formatted || '—'}</div>
      </div>
    </div>
  );
}

export default function NatalChartWheel({ data, name }) {
  const chart = useMemo(() => {
    if (!data || typeof data === 'string') {
      try {
        return typeof data === 'string' ? JSON.parse(data) : data;
      } catch {
        return null;
      }
    }
    return data;
  }, [data]);

  const western = chart?.western;
  const positions = western?.positions;
  const houses = western?.houses;
  const ascLon = positions?.ascendant?.longitude;

  if (!western || !positions || ascLon == null) {
    return (
      <div className="bg-black/35 border border-white/5 rounded-xl p-6 text-center text-xs text-gray-500 italic font-mono">
        Chart wheel unavailable — no cached chart data.
      </div>
    );
  }

  const planetEntries = Object.entries(positions).filter(
    ([k]) => !['ascendant', 'midheaven', 'south_node'].includes(k) && k in PLANET_GLYPHS
  );

  return (
    <div className="bg-black/35 border border-white/5 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-[10px] text-gray-500 font-mono uppercase tracking-wider font-bold flex items-center gap-1.5">
          <Compass className="w-3.5 h-3.5 text-amber-400" />
          Natal Chart Wheel {name ? `— ${name}` : ''}
        </div>
        <div className="text-[9px] text-gray-600 font-mono">
          {planetEntries.length} bodies · {houses ? Object.keys(houses).length : 0} houses
        </div>
      </div>

      <div className="flex justify-center">
        <svg
          viewBox="0 0 400 400"
          width="100%"
          style={{ maxWidth: 420, maxHeight: 420, aspectRatio: '1/1' }}
          role="img"
          aria-label={`Natal chart wheel for ${name || 'chart'}`}
        >
          <circle cx={CENTER} cy={CENTER} r={ZODIAC_R_OUTER} fill="#0f172a" stroke="#1e293b" strokeWidth={1} />
          <circle cx={CENTER} cy={CENTER} r={HOUSE_R_INNER} fill="none" stroke="#1e293b" strokeWidth={1} />
          <circle cx={CENTER} cy={CENTER} r={PLANET_R} fill="none" stroke="#1e293b" strokeWidth={0.5} strokeDasharray="2 2" />

          {SIGN_GLYPHS.map((_, i) => (
            <SignSegment key={i} signIndex={i} ascLon={ascLon} />
          ))}

          {houses && Object.entries(houses).map(([key, info]) => {
            const idx = Number(key.replace('house_', ''));
            return <HouseCusp key={key} index={idx} longitude={info.longitude} ascLon={ascLon} />;
          })}

          <AngleMark name="ascendant" longitude={positions.ascendant.longitude} ascLon={ascLon} label="ASC" color="#22d3ee" />
          <AngleMark name="midheaven" longitude={positions.midheaven.longitude} ascLon={ascLon} label="MC" color="#22d3ee" />
          <AngleMark
            name="dcs"
            longitude={(positions.ascendant.longitude + 180) % 360}
            ascLon={ascLon}
            label="DSC"
            color="#22d3ee"
          />
          <AngleMark
            name="ic"
            longitude={(positions.midheaven.longitude + 180) % 360}
            ascLon={ascLon}
            label="IC"
            color="#22d3ee"
          />

          {planetEntries.map(([name, info], idx) => {
            const ringOffset = (idx % 3);
            return (
              <PlanetMarker
                key={name}
                name={name}
                data={info}
                ascLon={ascLon}
                index={ringOffset}
                total={planetEntries.length}
                color={PLANET_COLORS[name] || '#94a3b8'}
              />
            );
          })}
        </svg>
      </div>

      <Legend data={chart} />
    </div>
  );
}
