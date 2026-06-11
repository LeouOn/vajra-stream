/**
 * Unit tests for the UI store (useUIStore from stores/uiStore.ts).
 * Split out of the original stores.test.ts so each store has
 * its own dedicated test file.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../stores/uiStore';

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
