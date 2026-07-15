import React, { useMemo } from 'react';
import { Compass } from 'lucide-react';
import {
  SIGN_GLYPHS, SIGN_NAMES, SIGN_ELEMENT, ELEMENT_COLORS,
  signName, signElement, signElementColor,
  toSvgAngle, polarToXY, describeArc, planetGlyph, PLANET_GLYPHS,
} from '../../lib/astroHelpers';

interface PointXY {
  x: number;
  y: number;
}

interface PlanetPosition {
  longitude: number;
  degree?: number;
  formatted?: string;
  is_cuspal?: boolean;
  [key: string]: unknown;
}

interface AnglePosition extends PlanetPosition {}

interface HouseInfo {
  longitude: number;
  [key: string]: unknown;
}

interface CuspSet {
  placidus?: number[];
  whole_sign?: number[];
  [key: string]: unknown;
}

interface ChartWestern {
  dominant_element?: string;
  dominant_modality?: string;
  positions?: Record<string, PlanetPosition>;
  houses?: Record<string, HouseInfo>;
  cusps?: CuspSet;
  [key: string]: unknown;
}

interface ChartData {
  western?: ChartWestern;
  cusps?: CuspSet;
  [key: string]: unknown;
}

const PLANET_COLORS: Record<string, string> = {
  sun: '#fbbf24', moon: '#e5e7eb', mercury: '#a78bfa', venus: '#f472b6',
  mars: '#ef4444', jupiter: '#fb923c', saturn: '#fde047',
  uranus: '#22d3ee', neptune: '#60a5fa', pluto: '#a855f7',
  chiron: '#94a3b8', north_node: '#64748b', south_node: '#64748b',
};

const ZODIAC_R_OUTER = 200;
const ZODIAC_R_INNER = 170;
const HOUSE_R_OUTER = 170;
const HOUSE_R_INNER = 145;
const PLANET_R = 130;
const CENTER = 200;

interface SignSegmentProps {
  signIndex: number;
  ascLon: number;
}

function SignSegment({ signIndex, ascLon }: SignSegmentProps) {
  const startLon = signIndex * 30;
  const endLon = (signIndex + 1) * 30;
  const startAngle = toSvgAngle(startLon, ascLon);
  const endAngle = toSvgAngle(endLon, ascLon);
  const midAngle = toSvgAngle(startLon + 15, ascLon);
  const midLabel = polarToXY(CENTER, CENTER, (ZODIAC_R_OUTER + ZODIAC_R_INNER) / 2, midAngle) as PointXY;
  const element = SIGN_ELEMENT[signIndex];
  const fill = ELEMENT_COLORS[element];

  return (
    <g>
      <path
        d={`${describeArc(CENTER, CENTER, ZODIAC_R_OUTER, startAngle, endAngle)} L ${(polarToXY(CENTER, CENTER, ZODIAC_R_INNER, endAngle) as PointXY).x} ${(polarToXY(CENTER, CENTER, ZODIAC_R_INNER, endAngle) as PointXY).y} ${describeArc(CENTER, CENTER, ZODIAC_R_INNER, endAngle, startAngle)} Z`}
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

interface HouseCuspProps {
  index: number;
  longitude: number;
  ascLon: number;
}

function HouseCusp({ index, longitude, ascLon }: HouseCuspProps) {
  const angle = toSvgAngle(longitude, ascLon);
  const tickInner = polarToXY(CENTER, CENTER, HOUSE_R_INNER - 4, angle) as PointXY;
  const tickOuter = polarToXY(CENTER, CENTER, HOUSE_R_OUTER, angle) as PointXY;
  const labelPos = polarToXY(CENTER, CENTER, (HOUSE_R_OUTER + HOUSE_R_INNER) / 2, angle) as PointXY;
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

interface AngleMarkProps {
  name: string;
  longitude: number;
  ascLon: number;
  label: string;
  color: string;
}

function angularDeltaSigned(a: number, b: number): number {
  return ((b - a + 180) % 360) - 180;
}

function distanceToNearestCusp(lon: number, cusps: number[]): number {
  if (!Array.isArray(cusps) || cusps.length === 0) return Number.POSITIVE_INFINITY;
  let nearest = Number.POSITIVE_INFINITY;
  for (const c of cusps) {
    if (typeof c !== 'number' || !Number.isFinite(c)) continue;
    const d = Math.abs(angularDeltaSigned(c, lon));
    if (d < nearest) nearest = d;
  }
  return nearest;
}

interface CuspLineProps {
  index: number;
  longitude: number;
  ascLon: number;
}

function CuspLine({ index, longitude, ascLon }: CuspLineProps) {
  const angle = toSvgAngle(longitude, ascLon);
  const inner = polarToXY(CENTER, CENTER, PLANET_R - 6, angle) as PointXY;
  const outer = polarToXY(CENTER, CENTER, ZODIAC_R_OUTER - 4, angle) as PointXY;
  // Cardinal cusps (1, 4, 7, 10) emphasised slightly; intermediate cusps stay subtle
  const isCardinal = index === 1 || index === 4 || index === 7 || index === 10;
  const stroke = isCardinal ? '#cbd5e1' : '#94a3b8';
  const strokeWidth = isCardinal ? 1 : 0.6;
  const opacity = isCardinal ? 0.45 : 0.25;
  const labelPos = polarToXY(CENTER, CENTER, ZODIAC_R_OUTER - 12, angle) as PointXY;
  return (
    <g>
      <line
        x1={inner.x} y1={inner.y}
        x2={outer.x} y2={outer.y}
        stroke={stroke}
        strokeWidth={strokeWidth}
        opacity={opacity}
        strokeDasharray={isCardinal ? undefined : '2 3'}
      />
      <text
        x={labelPos.x}
        y={labelPos.y}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={8}
        fill="#94a3b8"
        opacity={0.7}
        style={{ pointerEvents: 'none', fontFamily: 'monospace' }}
      >
        {index}
      </text>
    </g>
  );
}

function AngleMark({ name, longitude, ascLon, label, color }: AngleMarkProps) {
  const angle = toSvgAngle(longitude, ascLon);
  const inner = polarToXY(CENTER, CENTER, PLANET_R - 4, angle) as PointXY;
  const outer = polarToXY(CENTER, CENTER, ZODIAC_R_OUTER - 2, angle) as PointXY;
  const labelPos = polarToXY(CENTER, CENTER, ZODIAC_R_OUTER - 14, angle) as PointXY;
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

interface PlanetMarkerProps {
  name: string;
  data: PlanetPosition;
  ascLon: number;
  index: number;
  total: number;
  color: string;
}

function PlanetMarker({ name, data, ascLon, index, color }: PlanetMarkerProps) {
  const angle = toSvgAngle(data.longitude, ascLon);
  const r = PLANET_R - (index * 4);
  const pos = polarToXY(CENTER, CENTER, r, angle) as PointXY;
  const glyph = planetGlyph(name);
  const degText = `${Math.floor(data.degree || 0)}°`;
  const cuspal = data.is_cuspal === true;

  return (
    <g style={{ pointerEvents: 'none' }}>
      {cuspal && (
        <circle
          cx={pos.x}
          cy={pos.y}
          r={10}
          fill="none"
          stroke="#fde047"
          strokeWidth={1.5}
          opacity={0.9}
          style={{
            animation: 'vajra-cusp-pulse 2.4s ease-in-out infinite',
            transformOrigin: `${pos.x}px ${pos.y}px`,
            transformBox: 'fill-box',
          }}
        />
      )}
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

interface LegendProps {
  data?: ChartData | null;
}

function Legend({ data }: LegendProps) {
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

interface NatalChartWheelProps {
  data?: ChartData | string | null;
  name?: string;
}

export default function NatalChartWheel({ data, name }: NatalChartWheelProps) {
  const chart = useMemo<ChartData | null>(() => {
    if (!data || typeof data === 'string') {
      try {
        return typeof data === 'string' ? (JSON.parse(data) as ChartData) : (data as ChartData);
      } catch {
        return null;
      }
    }
    return data as ChartData;
  }, [data]);

  const western = chart?.western;
  const positions = western?.positions;
  const houses = western?.houses;
  const ascLon = positions?.ascendant?.longitude;

  // Cusps live at chart.cusps (schema-v2 export) or chart.western.cusps
  // (older cache layout). Render only when at least one system is present.
  const cuspPlacidus: number[] = useMemo(() => {
    const fromWestern = western?.cusps?.placidus;
    const fromRoot = chart?.cusps?.placidus;
    const raw = Array.isArray(fromWestern) && fromWestern.length === 12
      ? fromWestern
      : Array.isArray(fromRoot) && fromRoot.length === 12
        ? fromRoot
        : null;
    if (!raw) return [];
    return raw.filter((c) => typeof c === 'number' && Number.isFinite(c));
  }, [western?.cusps?.placidus, chart?.cusps?.placidus]);

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

  // When cusps are present, derive is_cuspal locally so the highlight works
  // even if the cached chart predates schema-v2 enrichment.
  const CUSPAL_THRESHOLD_DEG = 3.0;
  const enrichedPlanets: [string, PlanetPosition][] = cuspPlacidus.length === 12
    ? planetEntries.map(([name, info]) => {
        const d = distanceToNearestCusp(info.longitude, cuspPlacidus);
        const isCuspal = d <= CUSPAL_THRESHOLD_DEG || info.is_cuspal === true;
        return [name, { ...info, is_cuspal: isCuspal }];
      })
    : planetEntries;

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
          preserveAspectRatio="xMidYMid meet"
          style={{ maxWidth: '100%', height: 'auto', aspectRatio: '1/1' }}
          role="img"
          aria-label={`Natal chart wheel for ${name || 'chart'}`}
        >
          <style>{`@keyframes vajra-cusp-pulse {
            0%, 100% { opacity: 0.35; transform: scale(0.9); transform-origin: center; }
            50% { opacity: 1; transform: scale(1.25); transform-origin: center; }
          }`}</style>
          <circle cx={CENTER} cy={CENTER} r={ZODIAC_R_OUTER} fill="#0f172a" stroke="#1e293b" strokeWidth={1} />
          <circle cx={CENTER} cy={CENTER} r={HOUSE_R_INNER} fill="none" stroke="#1e293b" strokeWidth={1} />
          <circle cx={CENTER} cy={CENTER} r={PLANET_R} fill="none" stroke="#1e293b" strokeWidth={0.5} strokeDasharray="2 2" />

          {SIGN_GLYPHS.map((_, i) => (
            <SignSegment key={i} signIndex={i} ascLon={ascLon} />
          ))}

          {cuspPlacidus.length === 12 && cuspPlacidus.map((lon, idx) => (
            <CuspLine key={`placidus-${idx}`} index={idx + 1} longitude={lon} ascLon={ascLon} />
          ))}

          {houses && Object.entries(houses).map(([key, info]) => {
            const idx = Number(key.replace('house_', ''));
            return <HouseCusp key={key} index={idx} longitude={info.longitude} ascLon={ascLon} />;
          })}

          <AngleMark name="ascendant" longitude={positions.ascendant.longitude} ascLon={ascLon} label="ASC" color="#22d3ee" />
          {positions.midheaven && (
            <AngleMark name="midheaven" longitude={positions.midheaven.longitude} ascLon={ascLon} label="MC" color="#22d3ee" />
          )}
          <AngleMark
            name="dcs"
            longitude={(positions.ascendant.longitude + 180) % 360}
            ascLon={ascLon}
            label="DSC"
            color="#22d3ee"
          />
          {positions.midheaven && (
            <AngleMark
              name="ic"
              longitude={(positions.midheaven.longitude + 180) % 360}
              ascLon={ascLon}
              label="IC"
              color="#22d3ee"
            />
          )}

          {enrichedPlanets.map(([pname, info], idx) => {
            const ringOffset = (idx % 3);
            return (
              <PlanetMarker
                key={pname}
                name={pname}
                data={info}
                ascLon={ascLon}
                index={ringOffset}
                total={enrichedPlanets.length}
                color={PLANET_COLORS[pname] || '#94a3b8'}
              />
            );
          })}
        </svg>
      </div>

      <Legend data={chart} />
    </div>
  );
}
