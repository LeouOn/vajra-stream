/**
 * Unit tests for Zustand stores.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useAudioStore } from '../stores/audioStore';
import { useUIStore } from '../stores/uiStore';

// ---------------------------------------------------------------------------
// Audio Store
// ---------------------------------------------------------------------------

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
    expect(state.prayerBowlMode).toBe(true); // unchanged
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

// ---------------------------------------------------------------------------
// UI Store
// ---------------------------------------------------------------------------

describe('useUIStore', () => {
  beforeEach(() => {
    useUIStore.setState({
      toasts: [],
      loadingStates: {},
      progressStates: {},
      modals: {},
      sidebarOpen: true,
      sidebarSectionOpen: {},
      searchQuery: '',
      searchOpen: false,
      quickActionsOpen: false,
      keyboardShortcuts: true,
    });
  });

  it('has correct initial state', () => {
    const state = useUIStore.getState();
    expect(state.toasts).toEqual([]);
    expect(state.sidebarOpen).toBe(true);
  });

  it('addToast returns an id and adds to list', () => {
    const id = useUIStore.getState().addToast({ message: 'test', type: 'success' });
    expect(typeof id).toBe('number');
    expect(useUIStore.getState().toasts).toHaveLength(1);
    expect(useUIStore.getState().toasts[0].message).toBe('test');
  });

  it('addToast defaults type to info', () => {
    useUIStore.getState().addToast({ message: 'hello' });
    expect(useUIStore.getState().toasts[0].type).toBe('info');
  });

  it('removeToast removes by id', () => {
    const id = useUIStore.getState().addToast({ message: 'remove me' });
    useUIStore.getState().removeToast(id);
    expect(useUIStore.getState().toasts).toHaveLength(0);
  });

  it('clearToasts empties all', () => {
    useUIStore.getState().addToast({ message: 'a' });
    useUIStore.getState().addToast({ message: 'b' });
    useUIStore.getState().clearToasts();
    expect(useUIStore.getState().toasts).toHaveLength(0);
  });

  it('setLoading and isLoading work', () => {
    useUIStore.getState().setLoading('fetch', true, 'loading...');
    expect(useUIStore.getState().isLoading('fetch')).toBe(true);
    useUIStore.getState().clearLoading('fetch');
    expect(useUIStore.getState().isLoading('fetch')).toBe(false);
  });

  it('setProgress tracks progress', () => {
    useUIStore.getState().setProgress('upload', 50, 'halfway');
    const progress = useUIStore.getState().getProgress('upload');
    expect(progress.progress).toBe(50);
    expect(progress.message).toBe('halfway');
  });

  it('setProgress clamps to 0-100', () => {
    useUIStore.getState().setProgress('test', 150);
    expect(useUIStore.getState().getProgress('test').progress).toBe(100);
    useUIStore.getState().setProgress('test', -10);
    expect(useUIStore.getState().getProgress('test').progress).toBe(0);
  });

  it('openModal and isModalOpen work', () => {
    useUIStore.getState().openModal('settings', { theme: 'dark' });
    expect(useUIStore.getState().isModalOpen('settings')).toBe(true);
    expect(useUIStore.getState().getModalData('settings').theme).toBe('dark');
  });

  it('closeModal sets isOpen false', () => {
    useUIStore.getState().openModal('dialog');
    useUIStore.getState().closeModal('dialog');
    expect(useUIStore.getState().isModalOpen('dialog')).toBe(false);
  });

  it('toggleSidebar flips sidebarOpen', () => {
    expect(useUIStore.getState().sidebarOpen).toBe(true);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(false);
  });

  it('setSectionOpen tracks per-section', () => {
    useUIStore.getState().setSectionOpen('audio', true);
    useUIStore.getState().setSectionOpen('dharma', false);
    expect(useUIStore.getState().sidebarSectionOpen['audio']).toBe(true);
    expect(useUIStore.getState().sidebarSectionOpen['dharma']).toBe(false);
  });

  it('setSearchQuery updates search state', () => {
    useUIStore.getState().setSearchQuery('compassion');
    expect(useUIStore.getState().searchQuery).toBe('compassion');
  });

  it('setKeyboardShortcuts toggles', () => {
    useUIStore.getState().setKeyboardShortcuts(false);
    expect(useUIStore.getState().keyboardShortcuts).toBe(false);
  });
});
