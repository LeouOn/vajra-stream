import { create } from 'zustand';

export interface AudioSource {
  id: string;
  name: string;
  icon: string;
  stop: () => void;
  startedAt: number;
}

interface AudioActivityState {
  sources: AudioSource[];
  isMuted: boolean;
  register: (source: Omit<AudioSource, 'startedAt'>) => () => void;
  unregister: (id: string) => void;
  stopOne: (id: string) => void;
  stopAll: () => void;
  toggleMute: () => void;
}

export const useAudioActivity = create<AudioActivityState>((set, get) => ({
  sources: [],
  isMuted: false,

  register: (source) => {
    const fullSource: AudioSource = { ...source, startedAt: Date.now() };
    set((state) => ({
      sources: [...state.sources.filter(s => s.id !== source.id), fullSource],
    }));
    return () => get().unregister(source.id);
  },

  unregister: (id) => {
    set((state) => ({
      sources: state.sources.filter(s => s.id !== id),
    }));
  },

  stopOne: (id) => {
    const source = get().sources.find(s => s.id === id);
    if (source) {
      try { source.stop(); } catch { /* best effort */ }
      get().unregister(id);
    }
  },

  stopAll: () => {
    const { sources } = get();
    sources.forEach(s => {
      try { s.stop(); } catch { /* best effort */ }
    });
    document.querySelectorAll('audio').forEach(a => {
      try { a.pause(); a.currentTime = 0; } catch { /* best effort */ }
    });
    set({ sources: [] });
  },

  toggleMute: () => {
    set((state) => ({ isMuted: !state.isMuted }));
  },
}));
