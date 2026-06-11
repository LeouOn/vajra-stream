/**
 * UI Store — Zustand state for global UI concerns.
 *
 * Manages toast notifications (add/remove/clear), per-key loading
 * spinners, progress bars, modal open/close state, sidebar toggle,
 * search bar, quick-actions panel, and keyboard-shortcut toggle.
 * Not persisted — all state resets on page reload.
 */
import { create } from 'zustand';
import type { Toast } from '../types';

interface LoadingState {
  isLoading: boolean;
  message: string;
}

interface ProgressState {
  progress: number;
  message: string;
}

interface ModalState {
  isOpen: boolean;
  [key: string]: unknown;
}

interface UIState {
  toasts: Toast[];
  addToast: (toast: Partial<Toast>) => number;
  removeToast: (id: number) => void;
  clearToasts: () => void;
  loadingStates: Record<string, LoadingState>;
  setLoading: (key: string, isLoading: boolean, message?: string) => void;
  isLoading: (key: string) => boolean;
  clearLoading: (key: string) => void;
  progressStates: Record<string, ProgressState>;
  setProgress: (key: string, progress: number, message?: string) => void;
  getProgress: (key: string) => ProgressState;
  clearProgress: (key: string) => void;
  modals: Record<string, ModalState>;
  openModal: (key: string, data?: Record<string, unknown>) => void;
  closeModal: (key: string) => void;
  isModalOpen: (key: string) => boolean;
  getModalData: (key: string) => ModalState;
  sidebarOpen: boolean;
  sidebarSectionOpen: Record<string, boolean>;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setSectionOpen: (section: string, open: boolean) => void;
  keyboardShortcuts: boolean;
  setKeyboardShortcuts: (enabled: boolean) => void;
  searchQuery: string;
  searchOpen: boolean;
  setSearchQuery: (query: string) => void;
  setSearchOpen: (open: boolean) => void;
  quickActionsOpen: boolean;
  setQuickActionsOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set, get) => ({
  toasts: [],

  addToast: (toast) => {
    const id = Date.now() + Math.random();
    const newToast: Toast = { id, type: 'info', title: '', message: '', duration: 4000, action: null, ...toast };
    set((state) => ({ toasts: [...state.toasts, newToast] }));
    return id;
  },

  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  clearToasts: () => set({ toasts: [] }),

  loadingStates: {},
  setLoading: (key, isLoading, message = '') =>
    set((state) => ({ loadingStates: { ...state.loadingStates, [key]: { isLoading, message } } })),
  isLoading: (key) => get().loadingStates[key]?.isLoading || false,
  clearLoading: (key) =>
    set((state) => {
      const next = { ...state.loadingStates };
      delete next[key];
      return { loadingStates: next };
    }),

  progressStates: {},
  setProgress: (key, progress, message = '') =>
    set((state) => ({
      progressStates: { ...state.progressStates, [key]: { progress: Math.min(100, Math.max(0, progress)), message } },
    })),
  getProgress: (key) => get().progressStates[key] || { progress: 0, message: '' },
  clearProgress: (key) =>
    set((state) => {
      const next = { ...state.progressStates };
      delete next[key];
      return { progressStates: next };
    }),

  modals: {},
  openModal: (key, data = {}) => set((state) => ({ modals: { ...state.modals, [key]: { isOpen: true, ...data } } })),
  closeModal: (key) => set((state) => ({ modals: { ...state.modals, [key]: { isOpen: false } } })),
  isModalOpen: (key) => get().modals[key]?.isOpen || false,
  getModalData: (key) => get().modals[key] || {},

  sidebarOpen: true,
  sidebarSectionOpen: {},
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSectionOpen: (section, open) =>
    set((state) => ({ sidebarSectionOpen: { ...state.sidebarSectionOpen, [section]: open } })),

  keyboardShortcuts: true,
  setKeyboardShortcuts: (enabled) => set({ keyboardShortcuts: enabled }),

  searchQuery: '',
  searchOpen: false,
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchOpen: (open) => set({ searchOpen: open }),

  quickActionsOpen: false,
  setQuickActionsOpen: (open) => set({ quickActionsOpen: open }),
}));
