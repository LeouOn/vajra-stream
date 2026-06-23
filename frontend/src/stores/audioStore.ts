/**
 * Audio Store — Zustand state for prayer-bowl audio synthesis and playback.
 *
 * Manages the current frequency / volume / harmonic settings, the audio
 * generation status, and async actions that hit the backend audio API
 * (/api/v1/audio/{generate,play,stop}). Not persisted — all state resets
 * on page reload.
 */
import { create } from 'zustand';

/** Lifecycle status for the audio engine. */
export type AudioStatus =
  | 'idle'
  | 'generating'
  | 'generated'
  | 'playing'
  | 'stopped'
  | 'error';

/**
 * Permissive shape for backend responses. The backend returns an arbitrary
 * JSON object (status, detail, plus audio metadata) which we store verbatim
 * so UI components can read any field without tightly coupling to the API.
 */
export interface GeneratedAudioResponse {
  status?: string;
  detail?: string;
  [key: string]: unknown;
}

/** Tunable audio settings (subset of the store used by presets and getSettings). */
export interface AudioSettings {
  frequency: number;
  volume: number;
  prayerBowlMode: boolean;
  harmonicStrength: number;
  modulationDepth: number;
  duration: number;
}

export interface AudioState extends AudioSettings {
  // Playback / lifecycle
  isPlaying: boolean;
  audioStatus: AudioStatus;
  errorMessage: string | null;
  lastGeneratedAudio: GeneratedAudioResponse | null;

  // Bulk + per-field mutations
  updateSettings: (settings: Partial<AudioSettings>) => void;
  setFrequency: (frequency: number | string) => void;
  setVolume: (volume: number | string) => void;
  setPrayerBowlMode: (enabled: boolean | string) => void;
  setHarmonicStrength: (strength: number | string) => void;
  setModulationDepth: (depth: number | string) => void;
  setDuration: (duration: number | string) => void;

  // Async backend operations
  generateAudio: () => Promise<boolean>;
  playAudio: (hardwareLevel?: number) => Promise<boolean>;
  stopAudio: () => Promise<boolean>;

  // Misc
  resetAudio: () => void;
  loadPreset: (presetName: string) => void;
  getSettings: () => AudioSettings;
}

export const useAudioStore = create<AudioState>((set, get) => ({
  // State
  isPlaying: false,
  frequency: 136.1, // OM frequency in Hz
  volume: 0.8,
  prayerBowlMode: true,
  harmonicStrength: 0.3,
  modulationDepth: 0.05,
  duration: 30.0, // seconds
  audioStatus: 'idle', // idle, generating, playing, error
  errorMessage: null,
  lastGeneratedAudio: null,

  // Actions
  updateSettings: (newSettings) => {
    set((state) => ({
      ...state,
      ...newSettings,
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
          modulation_depth: modulationDepth,
        }),
      });

      const result: GeneratedAudioResponse = await response.json();

      if (result.status === 'success') {
        set({
          audioStatus: 'generated',
          lastGeneratedAudio: result,
          errorMessage: null,
        });
        return true;
      } else {
        throw new Error(result.detail || 'Failed to generate audio');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to generate audio';
      set({
        audioStatus: 'error',
        errorMessage: message,
        lastGeneratedAudio: null,
      });
      return false;
    }
  },

  playAudio: async (hardwareLevel = 2) => {
    try {
      // Check if audio has been generated
      const { lastGeneratedAudio, audioStatus } = get();

      if (!lastGeneratedAudio || audioStatus !== 'generated') {
        set({
          audioStatus: 'error',
          errorMessage: 'No audio data available. Please generate audio first.',
          isPlaying: false,
        });
        return false;
      }

      set({ audioStatus: 'playing', errorMessage: null });

      const response = await fetch('/api/v1/audio/play', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          hardware_level: hardwareLevel,
        }),
      });

      const result: GeneratedAudioResponse = await response.json();

      if (result.status === 'success') {
        set({
          isPlaying: true,
          audioStatus: 'playing',
          errorMessage: null,
        });
        return true;
      } else {
        throw new Error(result.detail || 'Failed to start audio playback');
      }
} catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to play audio';
      set({
        audioStatus: 'error',
        errorMessage: message,
      });
      return false;
    }
  },

  stopAudio: async () => {
    try {
      const response = await fetch('/api/v1/audio/stop', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const result: GeneratedAudioResponse = await response.json();

      if (result.status === 'success') {
        set({
          isPlaying: false,
          audioStatus: 'stopped',
          errorMessage: null,
        });
        return true;
      } else {
        throw new Error(result.detail || 'Failed to stop audio');
      }
} catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to stop audio';
      set({
        audioStatus: 'error',
        errorMessage: message,
      });
      return false;
    }
  },

  resetAudio: () => {
    set({
      isPlaying: false,
      audioStatus: 'idle',
      errorMessage: null,
      lastGeneratedAudio: null,
    });
  },

  setFrequency: (frequency) => {
    set({ frequency: parseFloat(String(frequency)) });
  },

  setVolume: (volume) => {
    set({ volume: Math.max(0, Math.min(1, parseFloat(String(volume)))) });
  },

  setPrayerBowlMode: (enabled) => {
    set({ prayerBowlMode: Boolean(enabled) });
  },

  setHarmonicStrength: (strength) => {
    set({ harmonicStrength: Math.max(0, Math.min(1, parseFloat(String(strength)))) });
  },

  setModulationDepth: (depth) => {
    set({ modulationDepth: Math.max(0, Math.min(1, parseFloat(String(depth)))) });
  },

  setDuration: (duration) => {
    set({ duration: Math.max(1, Math.min(300, parseFloat(String(duration)))) });
  },

  // Preset configurations
  loadPreset: (presetName) => {
    const presets: Record<string, Partial<AudioSettings>> = {
      'om-frequency': {
        frequency: 136.1,
        prayerBowlMode: true,
        harmonicStrength: 0.3,
        modulationDepth: 0.05,
        volume: 0.8,
      },
      'heart-chakra': {
        frequency: 528.0,
        prayerBowlMode: true,
        harmonicStrength: 0.4,
        modulationDepth: 0.1,
        volume: 0.7,
      },
      'earth-resonance': {
        frequency: 7.83,
        prayerBowlMode: true,
        harmonicStrength: 0.2,
        modulationDepth: 0.02,
        volume: 0.6,
      },
      'pure-sine': {
        frequency: 440.0,
        prayerBowlMode: false,
        harmonicStrength: 0,
        modulationDepth: 0,
        volume: 0.8,
      },
    };

    const preset = presets[presetName];
    if (preset) {
      set((state) => ({
        ...state,
        ...preset,
      }));
    }
    // Unknown preset name is silently ignored (caller should validate).
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
      duration,
    };
  },
}));
