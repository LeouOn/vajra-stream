/**
 * Unit tests for the audio store (useAudioStore from
 * stores/audioStore.js). Split out of the original
 * stores.test.ts so each store has its own dedicated test file.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useAudioStore } from '../stores/audioStore';

describe('useAudioStore', () => {
  beforeEach(() => {
    useAudioStore.setState({
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
    });
  });

  it('has correct initial state', () => {
    const state = useAudioStore.getState();
    expect(state.frequency).toBe(136.1);
    expect(state.isPlaying).toBe(false);
    expect(state.audioStatus).toBe('idle');
  });

  it('updateSettings merges partial state', () => {
    useAudioStore.getState().updateSettings({ frequency: 528, volume: 0.5 });
    const state = useAudioStore.getState();
    expect(state.frequency).toBe(528);
    expect(state.volume).toBe(0.5);
    expect(state.prayerBowlMode).toBe(true);
  });

  it('setFrequency clamps and parses', () => {
    useAudioStore.getState().setFrequency('528');
    expect(useAudioStore.getState().frequency).toBe(528);
  });

  it('setVolume clamps to 0-1', () => {
    useAudioStore.getState().setVolume(1.5);
    expect(useAudioStore.getState().volume).toBe(1);
    useAudioStore.getState().setVolume(-0.5);
    expect(useAudioStore.getState().volume).toBe(0);
  });

  it('setPrayerBowlMode toggles boolean', () => {
    useAudioStore.getState().setPrayerBowlMode(false);
    expect(useAudioStore.getState().prayerBowlMode).toBe(false);
    useAudioStore.getState().setPrayerBowlMode('true');
    expect(useAudioStore.getState().prayerBowlMode).toBe(true);
  });

  it('setDuration clamps to 1-300', () => {
    useAudioStore.getState().setDuration(500);
    expect(useAudioStore.getState().duration).toBe(300);
    useAudioStore.getState().setDuration(0);
    expect(useAudioStore.getState().duration).toBe(1);
  });

  it('resetAudio clears playback state', () => {
    useAudioStore.setState({ isPlaying: true, audioStatus: 'playing', lastGeneratedAudio: { id: 'test' } });
    useAudioStore.getState().resetAudio();
    const state = useAudioStore.getState();
    expect(state.isPlaying).toBe(false);
    expect(state.audioStatus).toBe('idle');
    expect(state.lastGeneratedAudio).toBeNull();
  });

  it('loadPreset loads known presets', () => {
    useAudioStore.getState().loadPreset('heart-chakra');
    expect(useAudioStore.getState().frequency).toBe(528);
    expect(useAudioStore.getState().prayerBowlMode).toBe(true);
  });

  it('loadPreset ignores unknown presets', () => {
    const before = useAudioStore.getState().frequency;
    useAudioStore.getState().loadPreset('nonexistent');
    expect(useAudioStore.getState().frequency).toBe(before);
  });

  it('getSettings returns current audio config', () => {
    const settings = useAudioStore.getState().getSettings();
    expect(settings).toHaveProperty('frequency');
    expect(settings).toHaveProperty('volume');
    expect(settings).toHaveProperty('prayerBowlMode');
    expect(settings).toHaveProperty('harmonicStrength');
    expect(settings).toHaveProperty('modulationDepth');
    expect(settings).toHaveProperty('duration');
  });
});
