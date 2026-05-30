/**
 * ChakraBodyMap — interactive SVG body with chakra energy centers.
 *
 * Renders a stylized human silhouette with seven luminous chakra points
 * positioned anatomically. Each chakra pulses independently with audio
 * reactivity, shows a glowing energy column through the spine, and
 * responds to hover/click for detail display.
 *
 * Pure SVG — no Three.js, no Canvas. Works in any browser.
 *
 * @component
 * @param {{ audioSpectrum, isPlaying, activeChakras, onSelectChakra }} props
 */
import React, { useState } from 'react';

interface ChakraPoint {
  id: string;
  name: string;
  cy: number;          // SVG y-coordinate (0-100% of body height)
  color: string;
  glow: string;
  frequency: number;
  size: number;
}

const CHAKRA_POINTS: ChakraPoint[] = [
  { id: 'crown',      name: 'Crown',     cy: 8,  color: '#d946ef', glow: '#f0abfc', frequency: 963, size: 16 },
  { id: 'third_eye',  name: 'Third Eye', cy: 16, color: '#8b5cf6', glow: '#b388ff', frequency: 852, size: 14 },
  { id: 'throat',     name: 'Throat',    cy: 25, color: '#06b6d4', glow: '#66e6ff', frequency: 741, size: 14 },
  { id: 'heart',      name: 'Heart',     cy: 38, color: '#22c55e', glow: '#66ff88', frequency: 639, size: 15 },
  { id: 'solar_plexus', name: 'Solar Plexus', cy: 48, color: '#eab308', glow: '#ffd700', frequency: 528, size: 14 },
  { id: 'sacral',     name: 'Sacral',    cy: 60, color: '#f97316', glow: '#ffa366', frequency: 417, size: 13 },
  { id: 'root',       name: 'Root',      cy: 78, color: '#ef4444', glow: '#ff6666', frequency: 396, size: 13 },
];

interface Props {
  audioSpectrum?: number[];
  isPlaying?: boolean;
  activeChakras?: string[];
  onSelectChakra?: (chakra: ChakraPoint) => void;
  height?: number;
}

const ChakraBodyMap: React.FC<Props> = ({
  audioSpectrum = [],
  isPlaying = false,
  activeChakras = [],
  onSelectChakra,
  height = 400,
}) => {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const width = height * 0.5;

  const getAmplitude = (index: number): number => {
    if (!isPlaying || audioSpectrum.length === 0) return 0;
    // Each chakra maps to a different frequency band
    const bandSize = Math.floor(audioSpectrum.length / 7);
    const band = audioSpectrum.slice(index * bandSize, (index + 1) * bandSize);
    return band.reduce((a, b) => a + b, 0) / band.length;
  };

  return (
    <div className="relative flex flex-col items-center">
      {/* Title */}
      <div className="text-center mb-3">
        <h4 className="text-xs font-semibold text-vajra-purple tracking-widest uppercase">Energy Body</h4>
      </div>

      <svg
        viewBox="0 0 150 320"
        width={width}
        height={height}
        className="overflow-visible"
        style={{ filter: 'drop-shadow(0 0 10px rgba(139, 92, 246, 0.15))' }}
      >
        <defs>
          {/* Energy column gradient */}
          <linearGradient id="spine-glow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#d946ef" stopOpacity="0.15" />
            <stop offset="30%" stopColor="#06b6d4" stopOpacity="0.1" />
            <stop offset="55%" stopColor="#22c55e" stopOpacity="0.15" />
            <stop offset="80%" stopColor="#ef4444" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.05" />
          </linearGradient>

          {/* Chakra glow filter */}
          <filter id="chakra-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="chakra-glow-strong" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Subtle body silhouette */}
        <ellipse cx="75" cy="40" rx="28" ry="32" fill="none" stroke="#ffffff08" strokeWidth="0.5" />
        <ellipse cx="75" cy="40" rx="24" ry="28" fill="#ffffff03" />
        {/* Neck */}
        <rect x="68" y="68" width="14" height="10" rx="4" fill="#ffffff03" />
        {/* Torso */}
        <path
          d="M40 78 Q40 70 50 75 L50 155 Q50 165 40 165 L40 78 Z"
          fill="#ffffff04"
          stroke="#ffffff06"
          strokeWidth="0.3"
        />
        <path
          d="M110 78 Q110 70 100 75 L100 155 Q100 165 110 165 L110 78 Z"
          fill="#ffffff04"
          stroke="#ffffff06"
          strokeWidth="0.3"
        />
        {/* Central body */}
        <rect x="50" y="75" width="50" height="90" rx="20" fill="#ffffff03" stroke="#ffffff05" strokeWidth="0.3" />

        {/* Spine energy column */}
        <line
          x1="75" y1="30"
          x2="75" y2="170"
          stroke="url(#spine-glow)"
          strokeWidth="8"
          strokeLinecap="round"
          opacity={isPlaying ? 0.7 : 0.3}
        >
          {isPlaying && (
            <animate attributeName="opacity" values="0.4;0.8;0.4" dur="3s" repeatCount="indefinite" />
          )}
        </line>

        {/* Chakra points */}
        {CHAKRA_POINTS.map((chakra, index) => {
          const isActive = activeChakras.length === 0 || activeChakras.includes(chakra.id);
          const isSelected = selectedId === chakra.id;
          const amp = getAmplitude(index);
          const pulseScale = isActive && isPlaying ? 1 + amp * 0.4 : 1;
          const pulseOpacity = isActive ? 0.6 + amp * 0.4 : 0.2;

          return (
            <g key={chakra.id}>
              {/* Outer glow ring */}
              <circle
                cx="75"
                cy={`${chakra.cy}%`}
                r={isSelected ? chakra.size * 2.5 : chakra.size * 1.8}
                fill={chakra.color}
                opacity={pulseOpacity * 0.15}
                filter={isSelected ? 'url(#chakra-glow-strong)' : 'url(#chakra-glow)'}
              >
                {isActive && isPlaying && (
                  <animate attributeName="r" values={`${chakra.size * 1.5};${chakra.size * 2.2};${chakra.size * 1.5}`} dur={`${2 + index * 0.3}s`} repeatCount="indefinite" />
                )}
              </circle>

              {/* Middle ring */}
              <circle
                cx="75"
                cy={`${chakra.cy}%`}
                r={chakra.size * pulseScale * 0.9}
                fill="none"
                stroke={chakra.color}
                strokeWidth="2"
                opacity={pulseOpacity * 0.7}
                filter="url(#chakra-glow)"
              />

              {/* Core */}
              <circle
                cx="75"
                cy={`${chakra.cy}%`}
                r={chakra.size * pulseScale * 0.45}
                fill={chakra.color}
                opacity={pulseOpacity}
                filter={isSelected ? 'url(#chakra-glow-strong)' : 'url(#chakra-glow)'}
              >
                {isActive && isPlaying && (
                  <animate attributeName="opacity" values={`${pulseOpacity * 0.7};${pulseOpacity};${pulseOpacity * 0.7}`} dur={`${1.5 + index * 0.2}s`} repeatCount="indefinite" />
                )}
              </circle>

              {/* Click target (transparent, larger) */}
              <circle
                cx="75"
                cy={`${chakra.cy}%`}
                r={chakra.size * 2}
                fill="transparent"
                className="cursor-pointer"
                onClick={() => {
                  const newId = selectedId === chakra.id ? null : chakra.id;
                  setSelectedId(newId);
                  if (newId && onSelectChakra) onSelectChakra(chakra);
                }}
              />

              {/* Frequency label */}
              <text
                x="75"
                y={`${chakra.cy + 3}%`}
                textAnchor="middle"
                fill={chakra.color}
                fontSize="7"
                fontFamily="JetBrains Mono, monospace"
                opacity={isSelected ? 0.9 : 0.4}
              >
                {chakra.frequency} Hz
              </text>
            </g>
          );
        })}
      </svg>

      {/* Selected chakra detail card */}
      {selectedId && (
        <div
          className="mt-3 bg-gray-800/90 border rounded-lg px-4 py-2 text-center animate-pulse-glow"
          style={{ borderColor: CHAKRA_POINTS.find((c) => c.id === selectedId)?.color + '60' }}
        >
          <span className="text-sm font-semibold" style={{ color: CHAKRA_POINTS.find((c) => c.id === selectedId)?.color }}>
            {CHAKRA_POINTS.find((c) => c.id === selectedId)?.name}
          </span>
          <span className="text-xs text-gray-400 ml-2">
            {CHAKRA_POINTS.find((c) => c.id === selectedId)?.frequency} Hz
          </span>
        </div>
      )}
    </div>
  );
};

export { CHAKRA_POINTS };
export default ChakraBodyMap;
