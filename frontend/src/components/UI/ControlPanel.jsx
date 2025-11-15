import React, { useState } from 'react';
import { Play, Pause, Square, Settings, Volume2 } from 'lucide-react';

const ControlPanel = ({
  isPlaying,
  frequency,
  volume,
  prayerBowlMode,
  harmonicStrength,
  modulationDepth,
  duration,
  onSettingsChange,
  onGenerateAudio,
  onPlayAudio,
  onStopAudio,
  audioStatus
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [localFrequency, setLocalFrequency] = useState(frequency);
  const [localVolume, setLocalVolume] = useState(volume);
  const [localPrayerBowlMode, setLocalPrayerBowlMode] = useState(prayerBowlMode);
  const [localHarmonicStrength, setLocalHarmonicStrength] = useState(harmonicStrength);
  const [localModulationDepth, setLocalModulationDepth] = useState(modulationDepth);
  const [localDuration, setLocalDuration] = useState(duration);

  // Update local state when props change
  React.useEffect(() => {
    setLocalFrequency(frequency);
    setLocalVolume(volume);
    setLocalPrayerBowlMode(prayerBowlMode);
    setLocalHarmonicStrength(harmonicStrength);
    setLocalModulationDepth(modulationDepth);
    setLocalDuration(duration);
  }, [frequency, volume, prayerBowlMode, harmonicStrength, modulationDepth, duration]);

  const handleGenerateAudio = async () => {
    onSettingsChange({
      frequency: localFrequency,
      volume: localVolume,
      prayerBowlMode: localPrayerBowlMode,
      harmonicStrength: localHarmonicStrength,
      modulationDepth: localModulationDepth,
      duration: localDuration
    });
    
    const success = await onGenerateAudio();
    if (success) {
      console.log('Audio generated successfully');
    }
  };

  const handlePlayAudio = async () => {
    const success = await onPlayAudio();
    if (success) {
      console.log('Audio playback started');
    }
  };

  const handleStopAudio = () => {
    onStopAudio();
    console.log('Audio playback stopped');
  };

  const loadPreset = (presetName) => {
    const presets = {
      'om-frequency': {
        frequency: 136.1,
        prayerBowlMode: true,
        harmonicStrength: 0.3,
        modulationDepth: 0.05,
        volume: 0.8,
        duration: 30
      },
      'heart-chakra': {
        frequency: 528.0,
        prayerBowlMode: true,
        harmonicStrength: 0.4,
        modulationDepth: 0.1,
        volume: 0.7,
        duration: 30
      },
      'earth-resonance': {
        frequency: 7.83,
        prayerBowlMode: true,
        harmonicStrength: 0.2,
        modulationDepth: 0.02,
        volume: 0.6,
        duration: 60
      },
      'pure-sine': {
        frequency: 440.0,
        prayerBowlMode: false,
        harmonicStrength: 0,
        modulationDepth: 0,
        volume: 0.8,
        duration: 10
      }
    };
    
    const preset = presets[presetName];
    if (preset) {
      setLocalFrequency(preset.frequency);
      setLocalVolume(preset.volume);
      setLocalPrayerBowlMode(preset.prayerBowlMode);
      setLocalHarmonicStrength(preset.harmonicStrength);
      setLocalModulationDepth(preset.modulationDepth);
      setLocalDuration(preset.duration);
      
      onSettingsChange(preset);
      console.log(`Loaded preset: ${presetName}`);
    }
  };

  const getStatusColor = () => {
    switch (audioStatus) {
      case 'generating': return 'text-yellow-400';
      case 'playing': return 'text-green-400';
      case 'error': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusText = () => {
    switch (audioStatus) {
      case 'generating': return 'Generating...';
      case 'generated': return 'Generated';
      case 'playing': return 'Playing';
      case 'stopped': return 'Stopped';
      case 'error': return 'Error';
      default: return 'Ready';
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-4 text-vajra-cyan flex items-center">
          <Settings className="w-5 h-5 mr-2" />
          Audio Controls
        </h2>
        
        {/* Status Display */}
        <div className="mb-4 p-3 bg-gray-700 rounded-lg">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">Status:</span>
            <span className={`text-sm font-bold ${getStatusColor()}`}>
              {getStatusText()}
            </span>
          </div>
        </div>

        {/* Preset Buttons */}
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">Presets</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => loadPreset('om-frequency')}
              className="vajra-button vajra-button-secondary text-sm"
            >
              OM (136.1 Hz)
            </button>
            <button
              onClick={() => loadPreset('heart-chakra')}
              className="vajra-button vajra-button-secondary text-sm"
            >
              Heart (528 Hz)
            </button>
            <button
              onClick={() => loadPreset('earth-resonance')}
              className="vajra-button vajra-button-secondary text-sm"
            >
              Earth (7.83 Hz)
            </button>
            <button
              onClick={() => loadPreset('pure-sine')}
              className="vajra-button vajra-button-secondary text-sm"
            >
              Pure Sine
            </button>
          </div>
        </div>

        {/* Basic Controls */}
        <div className="space-y-4">
          {/* Frequency Control */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Frequency: {localFrequency.toFixed(1)} Hz
            </label>
            <input
              type="range"
              min="1"
              max="1000"
              step="0.1"
              value={localFrequency}
              onChange={(e) => setLocalFrequency(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>1 Hz</span>
              <span>1000 Hz</span>
            </div>
          </div>

          {/* Volume Control */}
          <div>
            <label className="block text-sm font-medium mb-2 flex items-center">
              <Volume2 className="w-4 h-4 mr-1" />
              Volume: {Math.round(localVolume * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={localVolume}
              onChange={(e) => setLocalVolume(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Duration Control */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Duration: {localDuration}s
            </label>
            <input
              type="range"
              min="5"
              max="300"
              step="5"
              value={localDuration}
              onChange={(e) => setLocalDuration(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>5s</span>
              <span>5min</span>
            </div>
          </div>

          {/* Prayer Bowl Mode */}
          <div>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={localPrayerBowlMode}
                onChange={(e) => setLocalPrayerBowlMode(e.target.checked)}
                className="rounded text-vajra-cyan focus:ring-vajra-cyan"
              />
              <span className="text-sm font-medium">Prayer Bowl Mode</span>
            </label>
            <p className="text-xs text-gray-400 mt-1">
              Enable harmonic synthesis for authentic prayer bowl sound
            </p>
          </div>
        </div>

        {/* Advanced Settings Toggle */}
        <div className="mt-4">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-vajra-cyan hover:text-cyan-400 transition-colors"
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced Settings
          </button>
        </div>

        {/* Advanced Settings */}
        {showAdvanced && (
          <div className="space-y-4 mt-4 p-4 bg-gray-700 rounded-lg">
            <h3 className="text-sm font-semibold mb-3 text-vajra-purple">Advanced Parameters</h3>
            
            {/* Harmonic Strength */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Harmonic Strength: {(localHarmonicStrength * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={localHarmonicStrength}
                onChange={(e) => setLocalHarmonicStrength(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>

            {/* Modulation Depth */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Modulation Depth: {(localModulationDepth * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0"
                max="0.2"
                step="0.001"
                value={localModulationDepth}
                onChange={(e) => setLocalModulationDepth(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>
          </div>
        )}

        {/* Control Buttons */}
        <div className="space-y-2 mt-6">
          <button
            onClick={handleGenerateAudio}
            disabled={audioStatus === 'generating'}
            className={`w-full vajra-button vajra-button-primary flex items-center justify-center ${
              audioStatus === 'generating' ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {audioStatus === 'generating' ? (
              <>
                <div className="spinner w-4 h-4 mr-2" />
                Generating...
              </>
            ) : (
              'Generate Audio'
            )}
          </button>
          
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={handlePlayAudio}
              disabled={isPlaying || audioStatus === 'generating'}
              className={`vajra-button vajra-button-success flex items-center justify-center ${
                isPlaying || audioStatus === 'generating' ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <Play className="w-4 h-4 mr-1" />
              Play
            </button>
            
            <button
              onClick={handleStopAudio}
              disabled={!isPlaying}
              className={`vajra-button vajra-button-danger flex items-center justify-center ${
                !isPlaying ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <Square className="w-4 h-4 mr-1" />
              Stop
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;