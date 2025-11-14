import { create } from 'zustand';

export const useAudioStore = create((set, get) => ({
  // State
  isPlaying: false,
  frequency: 136.1,  // OM frequency in Hz
  volume: 0.8,
  prayerBowlMode: true,
  harmonicStrength: 0.3,
  modulationDepth: 0.05,
  duration: 30.0,  // seconds
  audioStatus: 'idle',  // idle, generating, playing, error
  errorMessage: null,
  lastGeneratedAudio: null,
  
  // Actions
  updateSettings: (newSettings) => {
    set((state) => ({
      ...state,
      ...newSettings
    }));
  },
  
  generateAudio: async () => {
    try {
      set({ audioStatus: 'generating', errorMessage: null });
      
      const { frequency, volume, prayerBowlMode, harmonicStrength, modulationDepth, duration } = get();
      
      const response = await fetch('/api/v1/audio/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          frequency,
          duration,
          volume,
          prayer_bowl_mode: prayerBowlMode,
          harmonic_strength: harmonicStrength,
          modulation_depth: modulationDepth
        }),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        set({ 
          audioStatus: 'generated',
          lastGeneratedAudio: result,
          errorMessage: null
        });
        console.log('Audio generated successfully:', result);
        return true;
      } else {
        throw new Error(result.detail || 'Failed to generate audio');
      }
    } catch (error) {
      console.error('Error generating audio:', error);
      set({ 
        audioStatus: 'error', 
        errorMessage: error.message || 'Failed to generate audio'
      });
      return false;
    }
  },
  
  playAudio: async (hardwareLevel = 2) => {
    try {
      set({ audioStatus: 'playing', errorMessage: null });
      
      const response = await fetch('/api/v1/audio/play', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          hardware_level: hardwareLevel
        }),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        set({ 
          isPlaying: true,
          audioStatus: 'playing',
          errorMessage: null
        });
        console.log('Audio playback started');
        return true;
      } else {
        throw new Error(result.detail || 'Failed to start audio playback');
      }
    } catch (error) {
      console.error('Error playing audio:', error);
      set({ 
        audioStatus: 'error', 
        errorMessage: error.message || 'Failed to start audio playback',
        isPlaying: false
      });
      return false;
    }
  },
  
  stopAudio: async () => {
    try {
      // Note: This would need a stop endpoint on the backend
      // For now, we'll just update the state
      set({ 
        isPlaying: false,
        audioStatus: 'stopped'
      });
      console.log('Audio playback stopped');
      return true;
    } catch (error) {
      console.error('Error stopping audio:', error);
      set({ 
        audioStatus: 'error', 
        errorMessage: error.message || 'Failed to stop audio'
      });
      return false;
    }
  },
  
  resetAudio: () => {
    set({
      isPlaying: false,
      audioStatus: 'idle',
      errorMessage: null,
      lastGeneratedAudio: null
    });
  },
  
  setFrequency: (frequency) => {
    set({ frequency: parseFloat(frequency) });
  },
  
  setVolume: (volume) => {
    set({ volume: Math.max(0, Math.min(1, parseFloat(volume))) });
  },
  
  setPrayerBowlMode: (enabled) => {
    set({ prayerBowlMode: Boolean(enabled) });
  },
  
  setHarmonicStrength: (strength) => {
    set({ harmonicStrength: Math.max(0, Math.min(1, parseFloat(strength))) });
  },
  
  setModulationDepth: (depth) => {
    set({ modulationDepth: Math.max(0, Math.min(1, parseFloat(depth))) });
  },
  
  setDuration: (duration) => {
    set({ duration: Math.max(1, Math.min(300, parseFloat(duration))) });
  },
  
  // Preset configurations
  loadPreset: (presetName) => {
    const presets = {
      'om-frequency': {
        frequency: 136.1,
        prayerBowlMode: true,
        harmonicStrength: 0.3,
        modulationDepth: 0.05,
        volume: 0.8
      },
      'heart-chakra': {
        frequency: 528.0,
        prayerBowlMode: true,
        harmonicStrength: 0.4,
        modulationDepth: 0.1,
        volume: 0.7
      },
      'earth-resonance': {
        frequency: 7.83,
        prayerBowlMode: true,
        harmonicStrength: 0.2,
        modulationDepth: 0.02,
        volume: 0.6
      },
      'pure-sine': {
        frequency: 440.0,
        prayerBowlMode: false,
        harmonicStrength: 0,
        modulationDepth: 0,
        volume: 0.8
      }
    };
    
    const preset = presets[presetName];
    if (preset) {
      set((state) => ({
        ...state,
        ...preset
      }));
      console.log(`Loaded preset: ${presetName}`, preset);
    } else {
      console.error(`Unknown preset: ${presetName}`);
    }
  },
  
  // Get current settings as object
  getSettings: () => {
    const { frequency, volume, prayerBowlMode, harmonicStrength, modulationDepth, duration } = get();
    return {
      frequency,
      volume,
      prayerBowlMode,
      harmonicStrength,
      modulationDepth,
      duration
    };
  }
}));