import React, { useState } from 'react';
import { Gem, Settings, Save, RotateCcw } from 'lucide-react';

/**
 * Crystal Grid Configuration Panel
 * Allows users to customize crystal grid visualization settings
 */
const CrystalGridControls = ({
  gridType: initialGridType = 'hexagon',
  crystalType: initialCrystalType = 'quartz',
  showEnergyField: initialShowEnergyField = true,
  intention: initialIntention = '',
  onSettingsChange
}) => {
  const [gridType, setGridType] = useState(initialGridType);
  const [crystalType, setCrystalType] = useState(initialCrystalType);
  const [showEnergyField, setShowEnergyField] = useState(initialShowEnergyField);
  const [intention, setIntention] = useState(initialIntention);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Grid pattern configurations
  const gridPatterns = [
    {
      id: 'hexagon',
      name: 'Hexagon Grid',
      description: '6 crystals - Basic Level 2 setup',
      icon: '⬡',
      crystalCount: 6
    },
    {
      id: 'double-hexagon',
      name: 'Double Hexagon',
      description: '13 crystals - Advanced configuration',
      icon: '⬢',
      crystalCount: 13
    },
    {
      id: 'star',
      name: 'Star of David',
      description: '13 crystals - Sacred geometry',
      icon: '✡',
      crystalCount: 13
    },
    {
      id: 'grid',
      name: '3x3 Grid',
      description: '9 crystals - Structured arrangement',
      icon: '⊞',
      crystalCount: 9
    }
  ];

  // Crystal types with properties
  const crystalTypes = [
    {
      id: 'quartz',
      name: 'Clear Quartz',
      color: '#ffffff',
      properties: 'Amplification, clarity, universal healing',
      chakra: 'All',
      icon: '◇'
    },
    {
      id: 'amethyst',
      name: 'Amethyst',
      color: '#9966ff',
      properties: 'Spiritual connection, transmutation, protection',
      chakra: 'Third Eye, Crown',
      icon: '◆'
    },
    {
      id: 'rose-quartz',
      name: 'Rose Quartz',
      color: '#ffb6c1',
      properties: 'Love, heart healing, emotional balance',
      chakra: 'Heart',
      icon: '♥'
    },
    {
      id: 'citrine',
      name: 'Citrine',
      color: '#ffd700',
      properties: 'Manifestation, abundance, joy',
      chakra: 'Solar Plexus',
      icon: '☀'
    },
    {
      id: 'black-tourmaline',
      name: 'Black Tourmaline',
      color: '#222222',
      properties: 'Protection, grounding, EMF shielding',
      chakra: 'Root',
      icon: '▲'
    },
    {
      id: 'selenite',
      name: 'Selenite',
      color: '#ffffee',
      properties: 'Cleansing, angelic connection, clarity',
      chakra: 'Crown, Higher Chakras',
      icon: '✦'
    }
  ];

  const handleApplySettings = () => {
    if (onSettingsChange) {
      onSettingsChange({
        gridType,
        crystalType,
        showEnergyField,
        intention
      });
    }
  };

  const handleReset = () => {
    setGridType('hexagon');
    setCrystalType('quartz');
    setShowEnergyField(true);
    setIntention('');

    if (onSettingsChange) {
      onSettingsChange({
        gridType: 'hexagon',
        crystalType: 'quartz',
        showEnergyField: true,
        intention: ''
      });
    }
  };

  const getCurrentPattern = () => {
    return gridPatterns.find(p => p.id === gridType) || gridPatterns[0];
  };

  const getCurrentCrystal = () => {
    return crystalTypes.find(c => c.id === crystalType) || crystalTypes[0];
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-vajra-cyan flex items-center">
          <Gem className="w-5 h-5 mr-2" />
          Crystal Grid Setup
        </h3>
        <button
          onClick={handleReset}
          className="text-sm text-gray-400 hover:text-white flex items-center"
        >
          <RotateCcw className="w-4 h-4 mr-1" />
          Reset
        </button>
      </div>

      {/* Grid Pattern Selection */}
      <div>
        <label className="block text-sm font-medium mb-2">Grid Pattern</label>
        <div className="grid grid-cols-2 gap-2">
          {gridPatterns.map((pattern) => (
            <button
              key={pattern.id}
              onClick={() => setGridType(pattern.id)}
              className={`p-3 rounded-lg border-2 transition-all text-left ${
                gridType === pattern.id
                  ? 'border-vajra-cyan bg-vajra-cyan bg-opacity-20'
                  : 'border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-lg">{pattern.icon}</span>
                <span className="text-xs text-gray-400">{pattern.crystalCount} crystals</span>
              </div>
              <div className="text-sm font-medium">{pattern.name}</div>
              <div className="text-xs text-gray-400 mt-1">{pattern.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Crystal Type Selection */}
      <div>
        <label className="block text-sm font-medium mb-2">Crystal Type</label>
        <div className="space-y-2">
          {crystalTypes.map((crystal) => (
            <button
              key={crystal.id}
              onClick={() => setCrystalType(crystal.id)}
              className={`w-full p-3 rounded-lg border-2 transition-all text-left ${
                crystalType === crystal.id
                  ? 'border-vajra-cyan bg-vajra-cyan bg-opacity-10'
                  : 'border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-lg"
                  style={{ backgroundColor: crystal.color + '40', color: crystal.color }}
                >
                  {crystal.icon}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium flex items-center justify-between">
                    <span>{crystal.name}</span>
                    <span className="text-xs text-gray-400">{crystal.chakra}</span>
                  </div>
                  {showAdvanced && (
                    <div className="text-xs text-gray-400 mt-1">{crystal.properties}</div>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Energy Field Toggle */}
      <div>
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showEnergyField}
            onChange={(e) => setShowEnergyField(e.target.checked)}
            className="rounded text-vajra-cyan focus:ring-vajra-cyan"
          />
          <span className="text-sm font-medium">Show Energy Field</span>
        </label>
        <p className="text-xs text-gray-400 mt-1 ml-6">
          Display torus ring showing broadcast range
        </p>
      </div>

      {/* Intention Input */}
      <div>
        <label className="block text-sm font-medium mb-2">Intention</label>
        <textarea
          value={intention}
          onChange={(e) => setIntention(e.target.value)}
          placeholder="Enter your intention (e.g., 'May all beings be happy and free')"
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm focus:border-vajra-cyan focus:ring-1 focus:ring-vajra-cyan"
          rows={3}
        />
        <p className="text-xs text-gray-400 mt-1">
          This will be displayed in the 3D visualization
        </p>
      </div>

      {/* Advanced Settings Toggle */}
      <div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-vajra-cyan hover:text-cyan-400 transition-colors flex items-center"
        >
          <Settings className="w-4 h-4 mr-1" />
          {showAdvanced ? 'Hide' : 'Show'} Crystal Properties
        </button>
      </div>

      {/* Current Configuration Summary */}
      <div className="p-4 bg-gray-700 bg-opacity-50 rounded-lg border border-gray-600">
        <h4 className="text-sm font-semibold mb-2 text-vajra-purple">Current Setup</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Pattern:</span>
            <span className="text-white">{getCurrentPattern().name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Crystals:</span>
            <span className="text-white">{getCurrentPattern().crystalCount}x {getCurrentCrystal().name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Energy Field:</span>
            <span className="text-white">{showEnergyField ? 'Visible' : 'Hidden'}</span>
          </div>
          {intention && (
            <div className="pt-2 border-t border-gray-600">
              <span className="text-gray-400 block mb-1">Intention:</span>
              <span className="text-white text-xs italic">"{intention}"</span>
            </div>
          )}
        </div>
      </div>

      {/* Apply Button */}
      <button
        onClick={handleApplySettings}
        className="w-full vajra-button vajra-button-primary flex items-center justify-center"
      >
        <Save className="w-4 h-4 mr-2" />
        Apply Crystal Grid Settings
      </button>

      {/* Quick Tips */}
      <div className="p-3 bg-gray-800 bg-opacity-50 rounded-lg border border-gray-700">
        <h4 className="text-xs font-semibold mb-2 text-vajra-cyan">💡 Quick Tips</h4>
        <ul className="text-xs text-gray-400 space-y-1">
          <li>• Match your physical crystal grid if you have one</li>
          <li>• Use Clear Quartz for general amplification</li>
          <li>• Rose Quartz for heart healing and love</li>
          <li>• Amethyst for spiritual work</li>
          <li>• Double Hexagon for more powerful operations</li>
        </ul>
      </div>
    </div>
  );
};

export default CrystalGridControls;
