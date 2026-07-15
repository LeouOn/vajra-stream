import React, { useState } from 'react';
import { DEITY_VISUALIZATIONS, DHYANI_BUDDHAS, type DeityVisualization } from '../../lib/deityVisualizations';

const ELEMENT_MAP: Record<string, number> = {
  'Earth': 0.2, 'Water': 0.4, 'Fire': 0.6, 'Air': 0.8, 'Air (Wind)': 0.8,
  'Wind': 0.8, 'Space': 1.0, 'Space (Ākāśa)': 1.0,
};

const CHAKRA_MAP: Record<string, number> = {
  root: 1 / 7, sacral: 2 / 7, solar_plexus: 3 / 7, heart: 4 / 7,
  throat: 5 / 7, third_eye: 6 / 7, crown: 1.0,
};

const FAMILY_POWER: Record<string, number> = {
  tathagata: 0.9, vajra: 0.85, ratna: 0.7, padma: 0.6, karma: 0.75,
};

const AXES = ['Frequency', 'Element', 'Chakra', 'Family Power', 'Bīja Density'];

function getRadarValues(deity: DeityVisualization): number[] {
  const freqNorm = Math.min(1, deity.frequencyHz / 900);
  const elementNorm = ELEMENT_MAP[deity.element] ?? 0.5;
  const chakraNorm = CHAKRA_MAP[deity.chakra] ?? 0.5;
  const familyNorm = FAMILY_POWER[deity.buddhaFamily] ?? 0.5;
  const bijaNorm = Math.min(1, deity.bija.length / 3);
  return [freqNorm, elementNorm, chakraNorm, familyNorm, bijaNorm];
}

interface BijaResonanceChartProps {
  size?: number;
}

export default function BijaResonanceChart({ size = 360 }: BijaResonanceChartProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>(['green_tara', 'medicine_buddha']);
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size * 0.38;
  const axisCount = AXES.length;

  const getAxisPoint = (axisIdx: number, value: number) => {
    const angle = (axisIdx / axisCount) * Math.PI * 2 - Math.PI / 2;
    const r = maxR * value;
    return { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
  };

  const getAxisEnd = (axisIdx: number) => getAxisPoint(axisIdx, 1.0);

  const toggleDeity = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id)
        ? prev.filter(x => x !== id)
        : prev.length < 5 ? [...prev, id] : prev
    );
  };

  const selectedDeities = selectedIds
    .map(id => DEITY_VISUALIZATIONS[id])
    .filter(Boolean);

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="text-center">
        <h3 className="text-sm font-bold text-purple-300">Bīja Resonance Chart</h3>
        <p className="text-[10px] text-gray-500 mt-0.5">Toggle deities to compare their esoteric profiles</p>
      </div>

      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[400px]">
        {[0.25, 0.5, 0.75, 1.0].map((ring, i) => (
          <polygon
            key={`ring-${i}`}
            points={AXES.map((_, ai) => {
              const p = getAxisPoint(ai, ring);
              return `${p.x},${p.y}`;
            }).join(' ')}
            fill="none"
            stroke="rgba(139, 92, 246, 0.1)"
            strokeWidth={1}
          />
        ))}

        {AXES.map((axis, ai) => {
          const end = getAxisEnd(ai);
          const labelR = maxR + size * 0.06;
          const angle = (ai / axisCount) * Math.PI * 2 - Math.PI / 2;
          const labelX = cx + Math.cos(angle) * labelR;
          const labelY = cy + Math.sin(angle) * labelR;
          return (
            <g key={`axis-${ai}`}>
              <line x1={cx} y1={cy} x2={end.x} y2={end.y} stroke="rgba(139, 92, 246, 0.12)" strokeWidth={1} />
              <text
                x={labelX}
                y={labelY}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={size * 0.028}
                fontFamily="monospace"
                fill="#94a3b8"
                opacity={0.6}
              >
                {axis}
              </text>
            </g>
          );
        })}

        {selectedDeities.map((deity) => {
          const values = getRadarValues(deity);
          const points = values.map((v, ai) => {
            const p = getAxisPoint(ai, v);
            return `${p.x},${p.y}`;
          }).join(' ');
          return (
            <g key={deity.id}>
              <polygon
                points={points}
                fill={deity.bodyColor}
                fillOpacity={0.12}
                stroke={deity.bodyColor}
                strokeWidth={1.5}
                opacity={0.8}
              />
              {values.map((v, ai) => {
                const p = getAxisPoint(ai, v);
                return (
                  <circle key={`pt-${deity.id}-${ai}`} cx={p.x} cy={p.y} r={3} fill={deity.bodyColor} opacity={0.7} />
                );
              })}
            </g>
          );
        })}
      </svg>

      <div className="flex flex-wrap gap-1.5 justify-center max-w-md">
        {Object.values(DEITY_VISUALIZATIONS).map((deity) => {
          const isSelected = selectedIds.includes(deity.id);
          return (
            <button
              key={deity.id}
              type="button"
              onClick={() => toggleDeity(deity.id)}
              className="px-2 py-1 rounded text-[9px] font-mono transition-all border"
              style={{
                borderColor: isSelected ? deity.bodyColor : 'rgba(255,255,255,0.1)',
                backgroundColor: isSelected ? `${deity.bodyColor}20` : 'transparent',
                color: isSelected ? deity.bodyColor : '#64748b',
              }}
            >
              {deity.bija} {deity.name.split(' ')[0]}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-3 justify-center max-w-lg text-[10px]">
        {selectedDeities.map(d => (
          <div key={d.id} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: d.bodyColor, opacity: 0.6 }} />
            <span style={{ color: d.bodyColor }} className="font-mono">{d.bijaRomaji}</span>
            <span className="text-gray-500">{d.frequencyHz}Hz · {d.buddhaFamily}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
