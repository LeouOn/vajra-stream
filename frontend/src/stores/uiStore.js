import { create } from 'zustand';

export const useUIStore = create((set, get) => ({
  // Toast notifications
  toasts: [],
  
  addToast: (toast) => {
    const id = Date.now() + Math.random();
    const newToast = {
      id,
      type: 'info',
      title: '',
      message: '',
      duration: 4000,
      action: null,
      ...toast
    };
    
    set((state) => ({
      toasts: [...state.toasts, newToast]
    }));
    
    return id;
  },
  
  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter(toast => toast.id !== id)
    }));
  },
  
  clearToasts: () => {
    set({ toasts: [] });
  },
  
  // Loading states
  loadingStates: {},
  
  setLoading: (key, isLoading, message = '') => {
    set((state) => ({
      loadingStates: {
        ...state.loadingStates,
        [key]: { isLoading, message }
      }
    }));
  },
  
  isLoading: (key) => {
    const state = get();
    return state.loadingStates[key]?.isLoading || false;
  },
  
  clearLoading: (key) => {
    set((state) => {
      const newStates = { ...state.loadingStates };
      delete newStates[key];
      return { loadingStates: newStates };
    });
  },
  
  // Progress indicators
  progressStates: {},
  
  setProgress: (key, progress, message = '') => {
    set((state) => ({
      progressStates: {
        ...state.progressStates,
        [key]: { progress: Math.min(100, Math.max(0, progress)), message }
      }
    }));
  },
  
  getProgress: (key) => {
    const state = get();
    return state.progressStates[key] || { progress: 0, message: '' };
  },
  
  clearProgress: (key) => {
    set((state) => {
      const newStates = { ...state.progressStates };
      delete newStates[key];
      return { progressStates: newStates };
    });
  },
  
  // Modal states
  modals: {},
  
  openModal: (key, data = {}) => {
    set((state) => ({
      modals: {
        ...state.modals,
        [key]: { isOpen: true, ...data }
      }
    }));
  },
  
  closeModal: (key) => {
    set((state) => ({
      modals: {
        ...state.modals,
        [key]: { isOpen: false }
      }
    }));
  },
  
  isModalOpen: (key) => {
    const state = get();
    return state.modals[key]?.isOpen || false;
  },
  
  getModalData: (key) => {
    const state = get();
    return state.modals[key] || {};
  },
  
  // Sidebar state
  sidebarOpen: true,
  sidebarSectionOpen: {},
  
  setSidebarOpen: (open) => {
    set({ sidebarOpen: open });
  },
  
  toggleSidebar: () => {
    set((state) => ({ sidebarOpen: !state.sidebarOpen }));
  },
  
  setSectionOpen: (section, open) => {
    set((state) => ({
      sidebarSectionOpen: {
        ...state.sidebarSectionOpen,
        [section]: open
      }
    }));
  },
  
  // Accessibility preferences
  accessibility: {
    highContrast: false,
    reducedMotion: false,
    fontSize: 'normal', // small, normal, large
    screenReader: false
  },
  
  setAccessibility: (settings) => {
    set((state) => ({
      accessibility: {
        ...state.accessibility,
        ...settings
      }
    }));
  },
  
  // Keyboard shortcuts
  keyboardShortcuts: true,
  
  setKeyboardShortcuts: (enabled) => {
    set({ keyboardShortcuts: enabled });
  },
  
  // Help and onboarding
  helpOpen: false,
  onboardingComplete: false,
  onboardingStep: 0,
  
  setHelpOpen: (open) => {
    set({ helpOpen: open });
  },
  
  setOnboardingComplete: (complete) => {
    set({ onboardingComplete: complete });
  },
  
  setOnboardingStep: (step) => {
    set({ onboardingStep: step });
  },
  
  // Search state
  searchQuery: '',
  searchOpen: false,
  
  setSearchQuery: (query) => {
    set({ searchQuery: query });
  },
  
  setSearchOpen: (open) => {
    set({ searchOpen: open });
  },
  
  // Quick actions
  quickActionsOpen: false,
  
  setQuickActionsOpen: (open) => {
    set({ quickActionsOpen: open });
  }
}));
