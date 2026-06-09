import React, { useState } from 'react';
import { Hexagon, Settings, Save, RotateCcw } from 'lucide-react';

/**
 * Sacred Mandala Configuration Panel
 * Allows users to select sacred geometry patterns and chakra colors
 */
const MandalaControls = ({
  pattern: initialPattern = 'sri-yantra',
  chakra: initialChakra = 'heart',
  complexity: initialComplexity = 'medium',
  onSettingsChange
}) => {
  const [pattern, setPattern] = useState(initialPattern);
  const [chakra, setChakra] = useState(initialChakra);
  const [complexity, setComplexity] = useState(initialComplexity);
  const [showInfo, setShowInfo] = useState(false);

  // Sacred geometry patterns
  const patterns = [
    {
      id: 'sri-yantra',
      name: 'Sri Yantra',
      tradition: 'Tantric',
      description: '9 interlocking triangles representing cosmic creation',
      details: 'The supreme sacred geometry of Tantric tradition. 5 downward triangles (Shakti/feminine) + 4 upward (Shiva/masculine) with central bindu (divine point).',
      bestFor: 'Deep meditation, manifestation, cosmic connection',
      icon: '🔺'
    },
    {
      id: 'metatron',
      name: "Metatron's Cube",
      tradition: 'Hermetic',
      description: 'Contains all Platonic solids, foundation of creation',
      details: '13 circles with all points interconnected. Contains all 5 Platonic solids: tetrahedron, cube, octahedron, dodecahedron, icosahedron.',
      bestFor: 'Understanding universal structure, sacred geometry study',
      icon: '⬢'
    },
    {
      id: 'seed-of-life',
      name: 'Seed of Life',
      tradition: 'Universal',
      description: '7 circles - Genesis pattern of creation',
      details: '1 center + 6 surrounding circles. Foundation of the Flower of Life. Represents the 7 days of creation.',
      bestFor: 'New beginnings, creativity, foundation work',
      icon: '◯'
    },
    {
      id: 'tree-of-life',
      name: 'Tree of Life',
      tradition: 'Kabbalistic',
      description: '10 Sephiroth showing path of spiritual development',
      details: '10 divine attributes (Sephiroth) connected by 22 paths. Maps the journey from material to divine.',
      bestFor: 'Spiritual development, understanding divine attributes',
      icon: '🌳'
    }
  ];

  // Chakra system
  const chakras = [
    {
      id: 'root',
      name: 'Root Chakra',
      sanskrit: 'Muladhara',
      color: '#ff0000',
      location: 'Base of spine',
      element: 'Earth',
      qualities: 'Grounding, security, stability, survival',
      icon: '▼'
    },
    {
      id: 'sacral',
      name: 'Sacral Chakra',
      sanskrit: 'Svadhisthana',
      color: '#ff6600',
      location: 'Below navel',
      element: 'Water',
      qualities: 'Creativity, sexuality, emotions, pleasure',
      icon: '◐'
    },
    {
      id: 'solar-plexus',
      name: 'Solar Plexus',
      sanskrit: 'Manipura',
      color: '#ffff00',
      location: 'Above navel',
      element: 'Fire',
      qualities: 'Personal power, will, confidence, transformation',
      icon: '☀'
    },
    {
      id: 'heart',
      name: 'Heart Chakra',
      sanskrit: 'Anahata',
      color: '#00ff00',
      location: 'Center of chest',
      element: 'Air',
      qualities: 'Love, compassion, acceptance, healing',
      icon: '♥'
    },
    {
      id: 'throat',
      name: 'Throat Chakra',
      sanskrit: 'Vishuddha',
      color: '#0099ff',
      location: 'Throat',
      element: 'Ether',
      qualities: 'Communication, truth, expression, clarity',
      icon: '◯'
    },
    {
      id: 'third-eye',
      name: 'Third Eye',
      sanskrit: 'Ajna',
      color: '#6600ff',
      location: 'Between eyebrows',
      element: 'Light',
      qualities: 'Intuition, insight, wisdom, vision',
      icon: '👁'
    },
    {
      id: 'crown',
      name: 'Crown Chakra',
      sanskrit: 'Sahasrara',
      color: '#ff00ff',
      location: 'Top of head',
      element: 'Thought',
      qualities: 'Spiritual connection, enlightenment, unity',
      icon: '✺'
    }
  ];

  const handleApplySettings = () => {
    if (onSettingsChange) {
      onSettingsChange({
        pattern,
        chakra,
        complexity
      });
    }
  };

  const handleReset = () => {
    setPattern('sri-yantra');
    setChakra('heart');
    setComplexity('medium');

    if (onSettingsChange) {
      onSettingsChange({
        pattern: 'sri-yantra',
        chakra: 'heart',
        complexity: 'medium'
      });
    }
  };

  const getCurrentPattern = () => {
    return patterns.find(p => p.id === pattern) || patterns[0];
  };

  const getCurrentChakra = () => {
    return chakras.find(c => c.id === chakra) || chakras[3];
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-vajra-cyan flex items-center">
          <Hexagon className="w-5 h-5 mr-2" />
          Sacred Mandala
        </h3>
        <button
          onClick={handleReset}
          className="text-sm text-gray-400 hover:text-white flex items-center"
        >
          <RotateCcw className="w-4 h-4 mr-1" />
          Reset
        </button>
      </div>

      {/* Pattern Selection */}
      <div>
        <label className="block text-sm font-medium mb-2">Sacred Geometry Pattern</label>
        <div className="space-y-2">
          {patterns.map((p) => (
            <button
              key={p.id}
              onClick={() => setPattern(p.id)}
              className={`w-full p-3 rounded-lg border-2 transition-all text-left ${
                pattern === p.id
                  ? 'border-vajra-purple bg-vajra-purple bg-opacity-20'
                  : 'border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="flex items-start space-x-3">
                <div className="text-2xl">{p.icon}</div>
                <div className="flex-1">
                  <div className="text-sm font-medium flex items-center justify-between">
                    <span>{p.name}</span>
                    <span className="text-xs text-gray-400">{p.tradition}</span>
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{p.description}</div>
                  {showInfo && (
                    <div className="mt-2 pt-2 border-t border-gray-700">
                      <div className="text-xs text-gray-300 mb-1">{p.details}</div>
                      <div className="text-xs text-vajra-purple">Best for: {p.bestFor}</div>
                    </div>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Chakra Selection */}
      <div>
        <label className="block text-sm font-medium mb-2">Chakra Coloring</label>
        <div className="grid grid-cols-1 gap-2">
          {chakras.map((c) => (
            <button
              key={c.id}
              onClick={() => setChakra(c.id)}
              className={`w-full p-2 rounded-lg border-2 transition-all text-left ${
                chakra === c.id
                  ? 'border-vajra-cyan bg-vajra-cyan bg-opacity-10'
                  : 'border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-lg"
                  style={{
                    backgroundColor: c.color + '40',
                    color: c.color,
                    boxShadow: chakra === c.id ? `0 0 10px ${c.color}` : 'none'
                  }}
                >
                  {c.icon}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium flex items-center justify-between">
                    <span>{c.name}</span>
                    <span className="text-xs text-gray-400">{c.sanskrit}</span>
                  </div>
                  {showInfo && (
                    <div className="text-xs text-gray-400 mt-1">
                      {c.location} • {c.element} • {c.qualities}
                    </div>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Complexity Level */}
      <div>
        <label className="block text-sm font-medium mb-2">Detail Level</label>
        <div className="grid grid-cols-3 gap-2">
          {['simple', 'medium', 'complex'].map((level) => (
            <button
              key={level}
              onClick={() => setComplexity(level)}
              className={`p-2 rounded-lg border-2 transition-all ${
                complexity === level
                  ? 'border-vajra-purple bg-vajra-purple bg-opacity-20'
                  : 'border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="text-sm font-medium capitalize">{level}</div>
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Higher detail may impact performance on slower devices
        </p>
      </div>

      {/* Info Toggle */}
      <div>
        <button
          onClick={() => setShowInfo(!showInfo)}
          className="text-sm text-vajra-cyan hover:text-cyan-400 transition-colors flex items-center"
        >
          <Settings className="w-4 h-4 mr-1" />
          {showInfo ? 'Hide' : 'Show'} Detailed Information
        </button>
      </div>

      {/* Current Configuration */}
      <div className="p-4 bg-gray-700 bg-opacity-50 rounded-lg border border-gray-600">
        <h4 className="text-sm font-semibold mb-2 text-vajra-purple">Current Setup</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Pattern:</span>
            <span className="text-white">{getCurrentPattern().name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Tradition:</span>
            <span className="text-white">{getCurrentPattern().tradition}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Chakra:</span>
            <span className="text-white flex items-center">
              <span
                className="w-3 h-3 rounded-full inline-block mr-2"
                style={{ backgroundColor: getCurrentChakra().color }}
              />
              {getCurrentChakra().name}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Detail:</span>
            <span className="text-white capitalize">{complexity}</span>
          </div>
        </div>
      </div>

      {/* Apply Button */}
      <button
        onClick={handleApplySettings}
        className="w-full vajra-button vajra-button-primary flex items-center justify-center"
      >
        <Save className="w-4 h-4 mr-2" />
        Apply Mandala Settings
      </button>

      {/* Meditation Guide */}
      <div className="p-3 bg-gray-800 bg-opacity-50 rounded-lg border border-gray-700">
        <h4 className="text-xs font-semibold mb-2 text-vajra-cyan">🧘 Meditation Guide</h4>
        <div className="text-xs text-gray-400 space-y-2">
          <p><strong>{getCurrentPattern().name}:</strong> {getCurrentPattern().bestFor}</p>
          <p><strong>{getCurrentChakra().name}:</strong> {getCurrentChakra().qualities}</p>
          <p className="pt-2 border-t border-gray-700 text-vajra-purple">
            Gaze softly at the center. Let your awareness expand with the pattern.
          </p>
        </div>
      </div>
    </div>
  );
};

export default MandalaControls;
