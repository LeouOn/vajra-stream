/**
 * ChakraAlignmentStrip — interactive 7-chakra energy bar with tooltips.
 *
 * Horizontal strip showing all seven chakras as luminous orbs with
 * frequency labels. Click a chakra to see its details (name, element,
 * mantra, frequency, color). Active sessions cause the relevant chakras
 * to pulse with energy glow.
 *
 * @component
 * @param {{ onSelectChakra, activeChakras }} props
 */
import React, { useState } from 'react';

interface ChakraDef {
  id: string;
  name: string;
  sanskrit: string;
  color: string;
  glow: string;
  frequency: number;
  element: string;
  mantra: string;
  location: string;
  affirmation: string;
}

const CHAKRAS: ChakraDef[] = [
  {
    id: 'root', name: 'Root', sanskrit: 'Muladhara', color: '#ef4444', glow: '#ff666680',
    frequency: 396, element: 'Earth', mantra: 'LAM', location: 'Base of spine',
    affirmation: 'I am grounded, safe, and secure.',
  },
  {
    id: 'sacral', name: 'Sacral', sanskrit: 'Svadhisthana', color: '#f97316', glow: '#ffa36680',
    frequency: 417, element: 'Water', mantra: 'VAM', location: 'Below navel',
    affirmation: 'I embrace pleasure and creativity.',
  },
  {
    id: 'solar_plexus', name: 'Solar Plexus', sanskrit: 'Manipura', color: '#eab308', glow: '#ffd70080',
    frequency: 528, element: 'Fire', mantra: 'RAM', location: 'Upper abdomen',
    affirmation: 'I am powerful and confident.',
  },
  {
    id: 'heart', name: 'Heart', sanskrit: 'Anahata', color: '#22c55e', glow: '#66ff8880',
    frequency: 639, element: 'Air', mantra: 'YAM', location: 'Center of chest',
    affirmation: 'I give and receive love freely.',
  },
  {
    id: 'throat', name: 'Throat', sanskrit: 'Vishuddha', color: '#06b6d4', glow: '#66e6ff80',
    frequency: 741, element: 'Ether', mantra: 'HAM', location: 'Throat',
    affirmation: 'I speak my truth with clarity.',
  },
  {
    id: 'third_eye', name: 'Third Eye', sanskrit: 'Ajna', color: '#8b5cf6', glow: '#b388ff80',
    frequency: 852, element: 'Light', mantra: 'OM', location: 'Between brows',
    affirmation: 'I trust my intuition and inner wisdom.',
  },
  {
    id: 'crown', name: 'Crown', sanskrit: 'Sahasrara', color: '#d946ef', glow: '#f0abfc80',
    frequency: 963, element: 'Consciousness', mantra: 'Silence', location: 'Top of head',
    affirmation: 'I am connected to the divine.',
  },
];

interface Props {
  onSelectChakra?: (chakra: ChakraDef) => void;
  activeChakras?: string[];
}

const ChakraAlignmentStrip: React.FC<Props> = ({ onSelectChakra, activeChakras = [] }) => {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const selected = CHAKRAS.find((c) => c.id === selectedId);

  return (
    <div className="relative bg-gray-900/90 border-t border-gray-700/50">
      {/* Tooltip */}
      {hoveredId && !selectedId && (
        <div
          className="absolute -top-20 left-1/2 -translate-x-1/2 bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 shadow-2xl z-50 min-w-[180px] text-center pointer-events-none"
          style={{
            borderColor: CHAKRAS.find((c) => c.id === hoveredId)?.color + '60',
          }}
        >
          <div className="text-sm font-semibold" style={{ color: CHAKRAS.find((c) => c.id === hoveredId)?.color }}>
            {CHAKRAS.find((c) => c.id === hoveredId)?.name}
          </div>
          <div className="text-xs text-gray-400">
            {CHAKRAS.find((c) => c.id === hoveredId)?.sanskrit} · {CHAKRAS.find((c) => c.id === hoveredId)?.frequency} Hz
          </div>
        </div>
      )}

      {/* Detail panel */}
      {selected && (
        <div
          className="absolute -top-52 left-1/2 -translate-x-1/2 bg-gray-800/95 border rounded-xl px-5 py-4 shadow-2xl z-50 w-64 text-center backdrop-blur-sm"
          style={{ borderColor: selected.color + '80' }}
          onClick={() => setSelectedId(null)}
        >
          <div className="text-lg font-bold mb-1" style={{ color: selected.color }}>
            {selected.name} · {selected.sanskrit}
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-left">
            <span className="text-gray-500">Element</span>
            <span className="text-white">{selected.element}</span>
            <span className="text-gray-500">Mantra</span>
            <span className="text-white font-mono">{selected.mantra}</span>
            <span className="text-gray-500">Frequency</span>
            <span className="text-white">{selected.frequency} Hz</span>
            <span className="text-gray-500">Location</span>
            <span className="text-white">{selected.location}</span>
          </div>
          <div className="text-xs italic mt-2 text-gray-400">"{selected.affirmation}"</div>
        </div>
      )}

      {/* Chakra row */}
      <div className="flex items-center justify-center gap-3 px-4 py-3">
        {CHAKRAS.map((chakra) => {
          const isActive = activeChakras.length === 0 || activeChakras.includes(chakra.id);
          const isSelected = selectedId === chakra.id;
          const isHovered = hoveredId === chakra.id;

          return (
            <button
              key={chakra.id}
              className="group flex flex-col items-center gap-1.5 relative focus:outline-none"
              onClick={() => {
                const newId = selectedId === chakra.id ? null : chakra.id;
                setSelectedId(newId);
                if (newId && onSelectChakra) onSelectChakra(chakra);
              }}
              onMouseEnter={() => setHoveredId(chakra.id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              {/* Glow ring */}
              <div
                className="absolute w-8 h-8 rounded-full transition-all duration-500"
                style={{
                  boxShadow: isActive
                    ? isSelected || isHovered
                      ? `0 0 16px ${chakra.glow}, 0 0 32px ${chakra.glow}`
                      : `0 0 6px ${chakra.glow}`
                    : 'none',
                }}
              />

              {/* Orb */}
              <div
                className={`w-6 h-6 rounded-full transition-all duration-500 ${
                  isActive ? 'animate-pulse-glow scale-100' : 'opacity-30 scale-90'
                } ${isSelected ? 'ring-2 ring-white/50 scale-125' : ''}`}
                style={{
                  backgroundColor: isActive ? chakra.color : '#333',
                  boxShadow: isActive ? `0 0 8px ${chakra.color}80` : 'none',
                }}
              />

              {/* Frequency label */}
              <span
                className={`text-[9px] font-mono transition-all duration-300 ${
                  isSelected ? 'text-white scale-110' : isHovered ? 'text-gray-300' : 'text-gray-500'
                }`}
              >
                {chakra.frequency}
              </span>
            </button>
          );
        })}
      </div>

      {/* Energy flow line */}
      <div className="absolute bottom-0 left-0 right-0 h-[1px]">
        <div
          className="h-full animate-pulse-glow"
          style={{
            background: `linear-gradient(90deg, transparent 0%, ${CHAKRAS[3].color}80 50%, transparent 100%)`,
          }}
        />
      </div>
    </div>
  );
};

export { CHAKRAS };
export default ChakraAlignmentStrip;
