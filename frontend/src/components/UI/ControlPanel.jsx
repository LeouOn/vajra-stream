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
  audioStatus,
  onStartSession,
  attunedRate
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [localFrequency, setLocalFrequency] = useState(frequency ?? 136.1);
  const [localVolume, setLocalVolume] = useState(volume ?? 0.8);
  const [localPrayerBowlMode, setLocalPrayerBowlMode] = useState(prayerBowlMode ?? true);
  const [localHarmonicStrength, setLocalHarmonicStrength] = useState(harmonicStrength ?? 0.3);
  const [localModulationDepth, setLocalModulationDepth] = useState(modulationDepth ?? 0.05);
  const [localDuration, setLocalDuration] = useState(duration ?? 30);
  const [intention, setIntention] = useState('');
  const [sessionName, setSessionName] = useState('Healing Session');

  // Update local state when props change
  React.useEffect(() => {
    setLocalFrequency(frequency ?? 136.1);
    setLocalVolume(volume ?? 0.8);
    setLocalPrayerBowlMode(prayerBowlMode ?? true);
    setLocalHarmonicStrength(harmonicStrength ?? 0.3);
    setLocalModulationDepth(modulationDepth ?? 0.05);
    setLocalDuration(duration ?? 30);
  }, [frequency, volume, prayerBowlMode, harmonicStrength, modulationDepth, duration]);

  const handleStartSession = async () => {
    if (onStartSession) {
      await onStartSession({
        name: sessionName,
        intention,
        duration: localDuration,
        audio_frequency: localFrequency,
        astrology_enabled: true,
        hardware_enabled: true,
        visuals_enabled: true
      });
    }
  };

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
      <div className="mystical-card">
        <h2 className="text-xl font-semibold mb-6 text-vajra-cyan glow-cyan flex items-center">
          <Settings className="w-6 h-6 mr-3" />
          Audio Controls
        </h2>
        
        {/* Status Display */}
        <div className="mb-6 p-4 glassmorphism rounded-xl mystical-border">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm font-medium text-purple-300">Status:</span>
            <span className={`text-sm font-bold ${getStatusColor()} ${audioStatus === 'playing' ? 'pulse-glow' : ''}`}>
              {getStatusText()}
            </span>
          </div>
          {attunedRate && (
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-purple-300">Attuned Rate:</span>
              <span className="text-sm font-bold text-vajra-cyan glow-cyan float-animation">
                {attunedRate}
              </span>
            </div>
          )}
        </div>

        {/* Session Controls */}
        <div className="mb-8 space-y-5 border-b border-purple-800/30 pb-8">
          <h3 className="text-lg font-semibold text-vajra-purple glow-text">Session Configuration</h3>
          <div>
            <label className="block text-sm font-medium mb-2 text-purple-300">Session Name</label>
            <input
              type="text"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              placeholder="Enter session name..."
              className="w-full mystical-input text-base mb-4"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2 text-purple-300">Intention</label>
            <input
              type="text"
              value={intention}
              onChange={(e) => setIntention(e.target.value)}
              placeholder="Enter healing intention..."
              className="w-full mystical-input text-base"
            />
          </div>
          <button
            onClick={handleStartSession}
            disabled={!intention || !sessionName}
            className={`w-full vajra-button vajra-button-primary flex items-center justify-center text-lg py-4 ${
              !intention || !sessionName ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-purple-500/50'
            } ${intention && sessionName ? 'pulse-glow' : ''}`}
          >
            <span className="mr-2">✨</span>
            Start Session
            <span className="ml-2">✨</span>
          </button>
        </div>

        {/* Preset Buttons */}
        <div className="mb-8">
          <label className="block text-sm font-medium mb-4 text-purple-300 glow-text">Sacred Frequencies</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => loadPreset('om-frequency')}
              className="vajra-button vajra-button-secondary text-sm hover:shadow-purple-400/30"
            >
              <span className="mr-1">🕉️</span> OM (136.1 Hz)
            </button>
            <button
              onClick={() => loadPreset('heart-chakra')}
              className="vajra-button vajra-button-secondary text-sm hover:shadow-green-400/30"
            >
              <span className="mr-1">💚</span> Heart (528 Hz)
            </button>
            <button
              onClick={() => loadPreset('earth-resonance')}
              className="vajra-button vajra-button-secondary text-sm hover:shadow-blue-400/30"
            >
              <span className="mr-1">🌍</span> Earth (7.83 Hz)
            </button>
            <button
              onClick={() => loadPreset('pure-sine')}
              className="vajra-button vajra-button-secondary text-sm hover:shadow-cyan-400/30"
            >
              <span className="mr-1">〰️</span> Pure Sine
            </button>
          </div>
        </div>

        {/* Basic Controls */}
        <div className="space-y-6">
          {/* Frequency Control */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-purple-300 glow-text flex items-center">
              <span className="mr-2">🎵</span>
              Frequency: <span className="ml-2 frequency-display">{localFrequency.toFixed(1)} Hz</span>
            </label>
            <input
              type="range"
              min="1"
              max="1000"
              step="0.1"
              value={localFrequency}
              onChange={(e) => setLocalFrequency(parseFloat(e.target.value))}
              className="mystical-range"
            />
            <div className="flex justify-between text-xs text-purple-400 mt-2">
              <span>1 Hz</span>
              <span>1000 Hz</span>
            </div>
          </div>

          {/* Volume Control */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-purple-300 glow-text flex items-center">
              <Volume2 className="w-4 h-4 mr-2" />
              Volume: <span className="ml-2 text-vajra-cyan">{Math.round(localVolume * 100)}%</span>
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={localVolume}
              onChange={(e) => setLocalVolume(parseFloat(e.target.value))}
              className="mystical-range"
            />
          </div>

          {/* Duration Control */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-purple-300 glow-text flex items-center">
              <span className="mr-2">⏱️</span>
              Duration: <span className="ml-2 text-vajra-cyan">{localDuration}s</span>
            </label>
            <input
              type="range"
              min="5"
              max="300"
              step="5"
              value={localDuration}
              onChange={(e) => setLocalDuration(parseInt(e.target.value))}
              className="mystical-range"
            />
            <div className="flex justify-between text-xs text-purple-400 mt-2">
              <span>5s</span>
              <span>5min</span>
            </div>
          </div>

          {/* Prayer Bowl Mode */}
          <div className="glassmorphism p-4 rounded-xl mystical-border">
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={localPrayerBowlMode}
                onChange={(e) => setLocalPrayerBowlMode(e.target.checked)}
                className="w-5 h-5 rounded text-vajra-cyan focus:ring-vajra-cyan focus:ring-2"
              />
              <span className="text-sm font-medium text-purple-300">Prayer Bowl Mode</span>
            </label>
            <p className="text-xs text-purple-400 mt-2 ml-8">
              Enable harmonic synthesis for authentic prayer bowl sound
            </p>
          </div>
        </div>

        {/* Advanced Settings Toggle */}
        <div className="mt-6 text-center">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-vajra-cyan hover:text-cyan-400 transition-all duration-300 glow-cyan px-4 py-2 rounded-full glassmorphism"
          >
            {showAdvanced ? '▲ Hide' : '▼ Show'} Advanced Settings
          </button>
        </div>

        {/* Advanced Settings */}
        {showAdvanced && (
          <div className="space-y-6 mt-6 p-6 mystical-card">
            <h3 className="text-lg font-semibold mb-4 text-vajra-purple glow-text">Advanced Parameters</h3>
            
            {/* Harmonic Strength */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-purple-300 glow-text">
                Harmonic Strength: <span className="text-vajra-cyan">{(localHarmonicStrength * 100).toFixed(0)}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={localHarmonicStrength}
                onChange={(e) => setLocalHarmonicStrength(parseFloat(e.target.value))}
                className="mystical-range"
              />
            </div>

            {/* Modulation Depth */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-purple-300 glow-text">
                Modulation Depth: <span className="text-vajra-cyan">{(localModulationDepth * 100).toFixed(0)}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="0.2"
                step="0.001"
                value={localModulationDepth}
                onChange={(e) => setLocalModulationDepth(parseFloat(e.target.value))}
                className="mystical-range"
              />
            </div>
          </div>
        )}

        {/* Control Buttons */}
        <div className="space-y-4 mt-8">
          <button
            onClick={handleGenerateAudio}
            disabled={audioStatus === 'generating'}
            className={`w-full vajra-button vajra-button-primary flex items-center justify-center text-lg py-4 ${
              audioStatus === 'generating' ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-purple-500/50'
            }`}
          >
            {audioStatus === 'generating' ? (
              <>
                <div className="spinner w-5 h-5 mr-3" />
                Generating...
              </>
            ) : (
              <>
                <span className="mr-2">🎵</span>
                Generate Audio
                <span className="ml-2">🎵</span>
              </>
            )}
          </button>
          
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={handlePlayAudio}
              disabled={isPlaying || audioStatus === 'generating' || audioStatus !== 'generated'}
              className={`vajra-button vajra-button-success flex items-center justify-center ${
                isPlaying || audioStatus === 'generating' || audioStatus !== 'generated' ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-green-500/50'
              }`}
            >
              <Play className="w-5 h-5 mr-2" />
              Play
            </button>
            
            <button
              onClick={handleStopAudio}
              disabled={!isPlaying}
              className={`vajra-button vajra-button-danger flex items-center justify-center ${
                !isPlaying ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-red-500/50'
              }`}
            >
              <Square className="w-5 h-5 mr-2" />
              Stop
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;