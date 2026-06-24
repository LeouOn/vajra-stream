/**
 * Rate Store — Zustand state for radionics rate tuning.
 *
 * Tracks the current rate dial values, preset library (healing,
 * liberation, empowerment, peace, love, wisdom, balance), custom
 * rate history, and broadcast session state. Persisted to localStorage.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { RatePreset } from '../types';
import { createLogger } from '../utils/logger';

const log = createLogger('rateStore');

/** A radionics rate — three dial values plus optional metadata. */
export interface Rate {
  values: number[];
  name?: string;
  description?: string;
  category?: string;
  potency?: number;
}

/** A rate that has been persisted (custom or history) with bookkeeping fields. */
export interface SavedRate extends Rate {
  id: number;
  createdAt?: string;
  timestamp?: string;
  sessionId?: string | null;
}

/** Permissive shape for rates placed into the comparison tray. */
export interface ComparisonRate {
  id: number | string;
  values?: number[];
  name?: string;
  description?: string;
  category?: string;
  [key: string]: unknown;
}

/** Library category keys returned by the backend. */
export type RateLibraryCategory =
  | 'healing_remedies'
  | 'organs_systems'
  | 'chakra_rates'
  | 'conditions'
  | 'balancing_rates';

export type RateLibrary = Record<RateLibraryCategory, SavedRate[]>;

/** Aggregate statistics returned by getRateStatistics(). */
export interface RateStatistics {
  totalRates: number;
  avgValues: number[];
  mostUsedCategory: string | null;
  averagePotency: number;
}

/** Input contract for isValidRate() — accepts unknown shapes for runtime validation. */
export type RateCandidate = { values?: unknown } | null | undefined;

export interface RateState {
  currentRate: Rate;
  rateHistory: SavedRate[];
  customRates: SavedRate[];
  rateLibrary: RateLibrary;
  searchQuery: string;
  searchResults: SavedRate[];
  comparisonRates: ComparisonRate[];
  error: string | null;

  // Real-time tuning
  isTuning: boolean;
  tuningSessionId: string | null;

  // Auto-tune settings
  autoTune: boolean;
  autoTuneConfidence: number;

  // Rate mutations
  setCurrentRate: (rate: Rate) => void;
  updateRateValue: (index: number, value: number) => void;
  setRateName: (name: string) => void;
  setRateCategory: (category: string) => void;
  setRateDescription: (description: string) => void;

  // Custom rate lifecycle
  saveRate: (rate?: Rate | null) => void;
  deleteRate: (rateId: number) => void;
  loadRate: (rate: Rate) => void;
  addToHistory: (rate: Rate, sessionId?: string | null) => void;

  // Library + search
  setRateLibrary: (category: RateLibraryCategory, rates: SavedRate[]) => void;
  setSearchQuery: (query: string) => void;
  searchRates: (query: string) => void;

  // Comparison tray
  addToComparison: (rate: ComparisonRate) => void;
  removeFromComparison: (rateId: number | string) => void;
  clearComparison: () => void;

  // Tuning sessions
  startTuning: (sessionId: string) => void;
  stopTuning: () => void;
  setAutoTune: (enabled: boolean) => void;
  setAutoTuneConfidence: (confidence: number) => void;

  // Presets + validation
  loadPreset: (presetId: string) => void;
  isValidRate: (rate: RateCandidate) => boolean;

  // Statistics
  getRateStatistics: () => RateStatistics | null;

  // Misc
  clearAll: () => void;
  fetchRatesFromBackend: (query?: string) => Promise<unknown>;
  getRateCategories: () => Promise<unknown>;
}

export const RATE_PRESETS: RatePreset[] = [
  { id: 'healing', name: 'Healing', values: [50, 50, 50], icon: '💚', category: 'healing' },
  { id: 'liberation', name: 'Liberation', values: [40, 60, 40], icon: '🕊️', category: 'liberation' },
  { id: 'empowerment', name: 'Empowerment', values: [60, 40, 60], icon: '⚡', category: 'empowerment' },
  { id: 'protection', name: 'Protection', values: [70, 30, 70], icon: '🛡️', category: 'protection' },
  { id: 'peace', name: 'Peace', values: [45, 55, 45], icon: '☮️', category: 'peace' },
  { id: 'love', name: 'Love', values: [55, 45, 55], icon: '❤️', category: 'love' },
  { id: 'wisdom', name: 'Wisdom', values: [65, 35, 65], icon: '🔮', category: 'wisdom' },
  { id: 'balance', name: 'Balance', values: [50, 50, 50], icon: '☯️', category: 'balancing' },
];

const DEFAULT_CURRENT_RATE: Rate = {
  values: [50, 50, 50],
  name: '',
  description: '',
  category: '',
  potency: 0.5,
};

const DEFAULT_RATE_LIBRARY: RateLibrary = {
  healing_remedies: [],
  organs_systems: [],
  chakra_rates: [],
  conditions: [],
  balancing_rates: [],
};

export const useRateStore = create<RateState>()(
  persist(
    (set, get) => ({
      // Current rate being tuned
      currentRate: { ...DEFAULT_CURRENT_RATE },

      // Rate history
      rateHistory: [],

      // Saved/custom rates
      customRates: [],

      // Rate library (from backend)
      rateLibrary: { ...DEFAULT_RATE_LIBRARY },

      // Rate search
      searchQuery: '',
      searchResults: [],

      // Rate comparison
      comparisonRates: [],

      // Last error from async backend operations (consumed by UI)
      error: null,

      // Real-time tuning
      isTuning: false,
      tuningSessionId: null,

      // Auto-tune settings
      autoTune: false,
      autoTuneConfidence: 0,

      // Actions
      setCurrentRate: (rate) => {
        set({ currentRate: rate });
      },

      updateRateValue: (index, value) => {
        set((state) => {
          const newValues = [...state.currentRate.values];
          newValues[index] = Math.max(0, Math.min(100, value));
          return {
            currentRate: {
              ...state.currentRate,
              values: newValues,
            },
          };
        });
      },

      setRateName: (name) => {
        set((state) => ({
          currentRate: {
            ...state.currentRate,
            name,
          },
        }));
      },

      setRateCategory: (category) => {
        set((state) => ({
          currentRate: {
            ...state.currentRate,
            category,
          },
        }));
      },

      setRateDescription: (description) => {
        set((state) => ({
          currentRate: {
            ...state.currentRate,
            description,
          },
        }));
      },

      saveRate: (rate = null) => {
        const rateToSave = rate || get().currentRate;
        set((state) => ({
          customRates: [
            ...state.customRates,
            {
              ...rateToSave,
              id: Date.now(),
              createdAt: new Date().toISOString(),
            },
          ],
        }));
      },

      deleteRate: (rateId) => {
        set((state) => ({
          customRates: state.customRates.filter((r) => r.id !== rateId),
        }));
      },

      loadRate: (rate) => {
        set({ currentRate: rate });
      },

      addToHistory: (rate, sessionId = null) => {
        set((state) => ({
          rateHistory: [
            {
              ...rate,
              id: Date.now(),
              sessionId,
              timestamp: new Date().toISOString(),
            },
            ...state.rateHistory,
          ].slice(0, 100), // Keep last 100
        }));
      },

      setRateLibrary: (category, rates) => {
        set((state) => ({
          rateLibrary: {
            ...state.rateLibrary,
            [category]: rates,
          },
        }));
      },

      setSearchQuery: (query) => {
        set({ searchQuery: query });
        get().searchRates(query);
      },

      searchRates: (query) => {
        if (!query.trim()) {
          set({ searchResults: [] });
          return;
        }

        const state = get();
        const allRates: SavedRate[] = [
          ...state.customRates,
          ...Object.values(state.rateLibrary).flat(),
        ];

        const results = allRates.filter((rate) => {
          const searchTerm = query.toLowerCase();
          return (
            rate.name?.toLowerCase().includes(searchTerm) ||
            rate.description?.toLowerCase().includes(searchTerm) ||
            rate.category?.toLowerCase().includes(searchTerm) ||
            rate.values?.join('-').includes(searchTerm)
          );
        });

        set({ searchResults: results });
      },

      addToComparison: (rate) => {
        set((state) => ({
          comparisonRates: [...state.comparisonRates, rate].slice(0, 4), // Max 4
        }));
      },

      removeFromComparison: (rateId) => {
        set((state) => ({
          comparisonRates: state.comparisonRates.filter((r) => r.id !== rateId),
        }));
      },

      clearComparison: () => {
        set({ comparisonRates: [] });
      },

      startTuning: (sessionId) => {
        set({
          isTuning: true,
          tuningSessionId: sessionId,
        });
      },

      stopTuning: () => {
        set({
          isTuning: false,
          tuningSessionId: null,
          autoTune: false,
          autoTuneConfidence: 0,
        });
      },

      setAutoTune: (enabled) => {
        set({ autoTune: enabled });
      },

      setAutoTuneConfidence: (confidence) => {
        set({ autoTuneConfidence: Math.max(0, Math.min(1, confidence)) });
      },

      // Rate presets
      loadPreset: (presetId) => {
        const preset = RATE_PRESETS.find((p) => p.id === presetId);
        if (preset) {
          set({
            currentRate: {
              ...get().currentRate,
              values: preset.values,
              name: preset.name,
              category: preset.category,
            },
          });
        }
      },

      // Rate validation
      isValidRate: (rate) => {
        if (!rate || typeof rate !== 'object') return false;
        const values = rate.values;
        return (
          Boolean(values) &&
          Array.isArray(values) &&
          values.length >= 2 &&
          (values as number[]).every((v) => v >= 0 && v <= 100)
        );
      },

      // Rate statistics
      getRateStatistics: () => {
        const state = get();
        const allRates: SavedRate[] = [...state.customRates, ...state.rateHistory];

        if (allRates.length === 0) {
          return null;
        }

        const avgValues = allRates.reduce<Record<number, number>>((acc, rate) => {
          rate.values.forEach((v, i) => {
            acc[i] = (acc[i] || 0) + v;
          });
          return acc;
        }, {});

        return {
          totalRates: allRates.length,
          avgValues: Object.values(avgValues).map((sum) => sum / allRates.length),
          mostUsedCategory: getMostUsedCategory(allRates),
          averagePotency: allRates.reduce((sum, r) => sum + (r.potency || 0), 0) / allRates.length,
        };
      },

      // Clear all data
      clearAll: () => {
        set({
          currentRate: { ...DEFAULT_CURRENT_RATE },
          rateHistory: [],
          customRates: [],
          searchQuery: '',
          searchResults: [],
          comparisonRates: [],
        });
      },

      fetchRatesFromBackend: async (query = '') => {
        try {
          const url = query
            ? `/api/v1/radionics/rates/search?query=${encodeURIComponent(query)}`
            : '/api/v1/radionics/rates/categories';
          const response = await fetch(url);
          if (!response.ok) throw new Error('Failed to fetch rates');
          const data = await response.json();
          return data;
        } catch (error) {
          log.warn('Rate fetch failed:', error);
          set({ error: error instanceof Error ? error.message : String(error) });
          return null;
        }
      },

      getRateCategories: async () => {
        try {
          const response = await fetch('/api/v1/radionics/rates/categories');
          if (!response.ok) throw new Error('Failed to fetch categories');
          const data = await response.json();
          if (data.categories) {
            Object.entries(data.categories as Record<string, SavedRate[]>).forEach(([category, rates]) => {
              get().setRateLibrary(category as RateLibraryCategory, rates);
            });
          }
          return data;
        } catch (error) {
          log.warn('Categories fetch failed:', error);
          set({ error: error instanceof Error ? error.message : String(error) });
          return null;
        }
      },
    }),
    {
      name: 'rate-storage',
      partialize: (state) => ({
        customRates: state.customRates,
        rateHistory: state.rateHistory.slice(0, 50), // Persist only last 50
      }),
    },
  ),
);

function getMostUsedCategory(rates: SavedRate[]): string | null {
  const categories: Record<string, number> = {};
  rates.forEach((rate) => {
    if (rate.category) {
      categories[rate.category] = (categories[rate.category] || 0) + 1;
    }
  });

  const entries = Object.entries(categories);
  if (entries.length === 0) return null;

  return entries.sort((a, b) => b[1] - a[1])[0][0];
}
