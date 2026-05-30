/**
 * Audio Store — Zustand state for audio generation and playback.
 */
import { create } from 'zustand';
import { API_BASE } from '../utils/api';

interface AudioSettings {
  frequency: number;
  volume: number;
  prayerBowlMode: boolean;
  harmonicStrength: number;
  modulationDepth: number;
  duration: number;
}

interface AudioState extends AudioSettings {
  isPlaying: boolean;
  audioStatus: 'idle' | 'generating' | 'generated' | 'playing' | 'error';
  errorMessage: string | null;
  lastGeneratedAudio: Record<string, unknown> | null;
  updateSettings: (newSettings: Partial<AudioState>) => void;
  generateAudio: () => Promise<boolean>;
  playAudio: (hardwareLevel?: number) => Promise<boolean>;
  stopAudio: () => Promise<boolean>;
  resetAudio: () => void;
  setFrequency: (freq: number | string) => void;
  setVolume: (vol: number | string) => void;
  setPrayerBowlMode: (enabled: boolean | string) => void;
  setHarmonicStrength: (strength: number | string) => void;
  setModulationDepth: (depth: number | string) => void;
  setDuration: (duration: number | string) => void;
  loadPreset: (presetName: string) => void;
  getSettings: () => AudioSettings;
}

export const useAudioStore = create<AudioState>((set, get) => ({
  isPlaying: false,
  frequency: 136.1,
  volume: 0.8,
  prayerBowlMode: true,
  harmonicStrength: 0.3,
  modulationDepth: 0.05,
  duration: 30.0,
  audioStatus: 'idle',
  errorMessage: null,
  lastGeneratedAudio: null,

  updateSettings: (newSettings) => set((state) => ({ ...state, ...newSettings })),

  generateAudio: async () => {
    try {
      set({ audioStatus: 'generating', errorMessage: null });
      const { frequency, volume, prayerBowlMode, harmonicStrength, modulationDepth, duration } = get();
      const response = await fetch(`${API_BASE}/audio/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          frequency, duration, volume,
          prayer_bowl_mode: prayerBowlMode,
          harmonic_strength: harmonicStrength,
          modulation_depth: modulationDepth,
        }),
      });
      const result = await response.json();
      if (result.status === 'success') {
        set({ audioStatus: 'generated', lastGeneratedAudio: result, errorMessage: null });
        return true;
      }
      throw new Error(result.detail || 'Failed to generate audio');
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to generate audio';
      console.error('Error generating audio:', error);
      set({ audioStatus: 'error', errorMessage: msg, lastGeneratedAudio: null });
      return false;
    }
  },

  playAudio: async (hardwareLevel = 2) => {
    try {
      const { lastGeneratedAudio, audioStatus } = get();
      if (!lastGeneratedAudio || audioStatus !== 'generated') {
        set({ audioStatus: 'error', errorMessage: 'No audio data available. Generate audio first.', isPlaying: false });
        return false;
      }
      set({ audioStatus: 'playing', errorMessage: null });
      const response = await fetch(`${API_BASE}/audio/play`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hardware_level: hardwareLevel }),
      });
      const result = await response.json();
      if (result.status === 'success') {
        set({ isPlaying: true, audioStatus: 'playing', errorMessage: null });
        return true;
      }
      throw new Error(result.detail || 'Failed to start audio playback');
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to start audio playback';
      console.error('Error playing audio:', error);
      set({ audioStatus: 'error', errorMessage: msg, isPlaying: false });
      return false;
    }
  },

  stopAudio: async () => {
    try {
      const response = await fetch(`${API_BASE}/audio/stop`, { method: 'POST' });
      if (!response.ok) throw new Error('Stop failed');
      set({ isPlaying: false, audioStatus: 'idle', errorMessage: null });
      return true;
    } catch {
      set({ isPlaying: false, audioStatus: 'idle' });
      return false;
    }
  },

  resetAudio: () => set({ isPlaying: false, audioStatus: 'idle', errorMessage: null, lastGeneratedAudio: null }),

  setFrequency: (freq) => set({ frequency: parseFloat(String(freq)) }),
  setVolume: (vol) => set({ volume: Math.max(0, Math.min(1, parseFloat(String(vol)))) }),
  setPrayerBowlMode: (enabled) => set({ prayerBowlMode: Boolean(enabled) }),
  setHarmonicStrength: (strength) => set({ harmonicStrength: Math.max(0, Math.min(1, parseFloat(String(strength)))) }),
  setModulationDepth: (depth) => set({ modulationDepth: Math.max(0, Math.min(1, parseFloat(String(depth)))) }),
  setDuration: (dur) => set({ duration: Math.max(1, Math.min(300, parseFloat(String(dur)))) }),

  loadPreset: (presetName) => {
    const presets: Record<string, Partial<AudioSettings>> = {
      'om-frequency': { frequency: 136.1, prayerBowlMode: true, harmonicStrength: 0.3, modulationDepth: 0.05, volume: 0.8 },
      'heart-chakra': { frequency: 528.0, prayerBowlMode: true, harmonicStrength: 0.4, modulationDepth: 0.1, volume: 0.7 },
      'earth-resonance': { frequency: 7.83, prayerBowlMode: true, harmonicStrength: 0.2, modulationDepth: 0.02, volume: 0.6 },
      'pure-sine': { frequency: 440.0, prayerBowlMode: false, harmonicStrength: 0, modulationDepth: 0, volume: 0.8 },
    };
    const preset = presets[presetName];
    if (preset) set((state) => ({ ...state, ...preset }));
  },

  getSettings: () => {
    const { frequency, volume, prayerBowlMode, harmonicStrength, modulationDepth, duration } = get();
    return { frequency, volume, prayerBowlMode, harmonicStrength, modulationDepth, duration };
  },
}));
