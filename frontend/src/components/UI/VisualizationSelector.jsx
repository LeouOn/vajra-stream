import React from 'react';
import { Eye, Layers, BarChart3, Globe, Gem, Hexagon, Radio, TrendingUp, Heart } from 'lucide-react';

const VisualizationSelector = ({ currentType, onChange }) => {
  const visualizations = [
    {
      id: 'sacred-geometry',
      name: 'Flower of Life',
      icon: <Layers className="w-4 h-4" />,
      description: 'Sacred geometry pattern with audio reactivity'
    },
    {
      id: 'radionics',
      name: 'Radionics',
      icon: <Radio className="w-4 h-4" />,
      description: 'Radionics operation visualization'
    },
    {
      id: 'crystal-grid',
      name: 'Crystal Grid',
      icon: <Gem className="w-4 h-4" />,
      description: 'Interactive crystal grid visualization for radionics'
    },
    {
      id: 'sacred-mandala',
      name: 'Sacred Mandala',
      icon: <Hexagon className="w-4 h-4" />,
      description: 'Advanced sacred geometry (Sri Yantra, Metatron\'s Cube)'
    },
    {
      id: 'audio-spectrum',
      name: 'Audio Spectrum',
      icon: <BarChart3 className="w-4 h-4" />,
      description: 'Real-time frequency spectrum analysis'
    },
    {
      id: 'live-wave',
      name: 'Live Wave',
      icon: <Radio className="w-4 h-4" />,
      description: 'Audio-reactive sine wave with spectrum bars'
    },
    {
      id: 'scalar-wave',
      name: 'Scalar Wave',
      icon: <Radio className="w-4 h-4" />,
      description: 'PRNG-driven scalar noise visualization'
    },
    {
      id: 'globe',
      name: 'World Globe',
      icon: <Globe className="w-4 h-4" />,
      description: '3D Earth with live disaster markers and broadcast targets'
    },
    {
      id: 'waterfall',
      name: 'Frequency Waterfall',
      icon: <BarChart3 className="w-4 h-4" />,
      description: 'Real-time frequency spectrum waterfall display'
    },
    {
      id: 'radionics-panel',
      name: 'Radionics Panel',
      icon: <Radio className="w-4 h-4" />,
      description: 'Full radionics broadcast control panel'
    },
    {
      id: 'trends',
      name: 'Trends',
      icon: <TrendingUp className="w-4 h-4" />,
      description: 'Session history and rate trends'
    },
    {
      id: 'chakra-trend',
      name: 'Chakra Trends',
      icon: <Heart className="w-4 h-4" />,
      description: 'Live chakra alignment and frequency trending'
    }
  ];

  const handleVisualizationChange = (type) => {
    if (type !== 'coming-soon') {
      onChange(type);
    }
  };

  return (
    <div className="relative">
      {/* Dropdown Button */}
      <button
        className="flex items-center space-x-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-sm"
        onClick={() => {
          const dropdown = document.getElementById('visualization-dropdown');
          dropdown.classList.toggle('hidden');
        }}
      >
        <Eye className="w-4 h-4" />
        <span>Visualization</span>
        <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      <div
        id="visualization-dropdown"
        className="hidden absolute right-0 mt-2 w-64 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50"
      >
        <div className="p-2">
          {visualizations.map((viz) => (
            <button
              key={viz.id}
              onClick={() => {
                handleVisualizationChange(viz.id);
                document.getElementById('visualization-dropdown').classList.add('hidden');
              }}
              disabled={viz.id === 'coming-soon'}
              className={`w-full text-left px-3 py-2 rounded-md transition-colors flex items-start space-x-3 ${
                currentType === viz.id
                  ? 'bg-vajra-cyan text-white'
                  : viz.id === 'coming-soon'
                  ? 'text-gray-500 cursor-not-allowed'
                  : 'hover:bg-gray-700 text-white'
              }`}
            >
              <div className="flex-shrink-0 mt-0.5">
                {viz.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{viz.name}</div>
                <div className={`text-xs mt-1 ${
                  currentType === viz.id
                    ? 'text-cyan-100'
                    : viz.id === 'coming-soon'
                    ? 'text-gray-500'
                    : 'text-gray-400'
                }`}>
                  {viz.description}
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="px-3 py-2 border-t border-gray-700">
          <div className="text-xs text-gray-400">
            Current: <span className="text-vajra-cyan font-medium">
              {visualizations.find(v => v.id === currentType)?.name || 'Unknown'}
            </span>
          </div>
        </div>
      </div>

      {/* Close dropdown when clicking outside */}
      <div
        className="hidden fixed inset-0 z-40"
        onClick={() => {
          document.getElementById('visualization-dropdown').classList.add('hidden');
        }}
      />
    </div>
  );
};

export default VisualizationSelector;