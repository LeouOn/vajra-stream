/**
 * VisualizationSelector — picks active visualization mode.
 *
 * Dropdown with 14 visualization types including the new Rothko color-field,
 * Chakra Body Map, and 6 Sacred Geometry patterns. Shows current selection
 * with description. Closes on outside click.
 *
 * @component
 * @param {{ currentType, onChange }} props
 */
import React, { useRef, useEffect, useState } from 'react';
import { Eye, Layers, BarChart3, Globe, Gem, Hexagon, Radio, TrendingUp, Heart, Palette, User } from 'lucide-react';

interface VizEntry {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
}

const VISUALIZATIONS: VizEntry[] = [
  { id: 'sacred-geometry',  name: 'Flower of Life',  icon: <Layers className="w-4 h-4" />,     description: '3D sacred geometry with particle fields' },
  { id: 'sacred-mandala',   name: 'Sacred Mandala',  icon: <Hexagon className="w-4 h-4" />,     description: 'Sri Yantra, Metatron\'s Cube, Tree of Life' },
  { id: 'crystal-grid',     name: 'Crystal Grid',    icon: <Gem className="w-4 h-4" />,          description: '3D crystal grid with energy fields' },
  { id: 'rothko',           name: 'Rothko Field',    icon: <Palette className="w-4 h-4" />,      description: 'Color-field meditation — Mark Rothko inspired' },
  { id: 'chakra-body',      name: 'Chakra Body Map',  icon: <User className="w-4 h-4" />,        description: 'Interactive SVG body with 7 energy centers' },
  { id: 'radionics',        name: 'Radionics',       icon: <Radio className="w-4 h-4" />,         description: 'Radionics operation visualization' },
  { id: 'audio-spectrum',   name: 'Audio Spectrum',  icon: <BarChart3 className="w-4 h-4" />,    description: 'Real-time frequency spectrum bars' },
  { id: 'live-wave',        name: 'Live Wave',       icon: <Radio className="w-4 h-4" />,         description: 'Audio-reactive waveform with spectrum' },
  { id: 'scalar-wave',      name: 'Scalar Wave',     icon: <Radio className="w-4 h-4" />,         description: 'PRNG-driven scalar noise visualization' },
  { id: 'waterfall',        name: 'Waterfall',       icon: <BarChart3 className="w-4 h-4" />,    description: 'Frequency-over-time waterfall heatmap' },
  { id: 'globe',            name: 'World Globe',     icon: <Globe className="w-4 h-4" />,         description: '3D Earth with blessing target markers' },
  { id: 'trends',           name: 'Trends',          icon: <TrendingUp className="w-4 h-4" />,   description: 'Session history and rate trends dashboard' },
  { id: 'chakra-trend',     name: 'Chakra Strip',    icon: <Heart className="w-4 h-4" />,         description: 'Live chakra alignment energy bar' },
];

interface Props {
  currentType: string;
  onChange: (type: string) => void;
}

const VisualizationSelector: React.FC<Props> = ({ currentType, onChange }) => {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const current = VISUALIZATIONS.find((v) => v.id === currentType);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        className="flex items-center space-x-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-sm"
        onClick={() => setOpen(!open)}
      >
        <Eye className="w-4 h-4 text-vajra-cyan" />
        <span className="hidden sm:inline">{current?.name || 'Visualization'}</span>
        <svg className={`w-4 h-4 ml-1 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 bg-gray-800 border border-gray-700 rounded-lg shadow-2xl z-50 max-h-[60vh] overflow-y-auto">
          <div className="p-2">
            {VISUALIZATIONS.map((viz) => (
              <button
                key={viz.id}
                onClick={() => { onChange(viz.id); setOpen(false); }}
                className={`w-full text-left px-3 py-2 rounded-md transition-colors flex items-start space-x-3 ${
                  currentType === viz.id
                    ? 'bg-vajra-cyan/20 text-vajra-cyan border border-vajra-cyan/30'
                    : 'hover:bg-gray-700 text-white'
                }`}
              >
                <div className="flex-shrink-0 mt-0.5 text-gray-400">{viz.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{viz.name}</div>
                  <div className={`text-xs mt-0.5 ${currentType === viz.id ? 'text-cyan-300/70' : 'text-gray-400'}`}>
                    {viz.description}
                  </div>
                </div>
                {currentType === viz.id && (
                  <div className="w-2 h-2 rounded-full bg-vajra-cyan mt-1.5 flex-shrink-0" />
                )}
              </button>
            ))}
          </div>
          <div className="px-3 py-2 border-t border-gray-700 text-xs text-gray-500">
            {VISUALIZATIONS.length} visualizations available
          </div>
        </div>
      )}
    </div>
  );
};

export { VISUALIZATIONS };
export default VisualizationSelector;
