import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const RATE_PRESETS = [
  { id: 'healing', name: 'Healing', values: [50, 50, 50], icon: '💚', category: 'healing' },
  { id: 'liberation', name: 'Liberation', values: [40, 60, 40], icon: '🕊️', category: 'liberation' },
  { id: 'empowerment', name: 'Empowerment', values: [60, 40, 60], icon: '⚡', category: 'empowerment' },
  { id: 'protection', name: 'Protection', values: [70, 30, 70], icon: '🛡️', category: 'protection' },
  { id: 'peace', name: 'Peace', values: [45, 55, 45], icon: '☮️', category: 'peace' },
  { id: 'love', name: 'Love', values: [55, 45, 55], icon: '❤️', category: 'love' },
  { id: 'wisdom', name: 'Wisdom', values: [65, 35, 65], icon: '🔮', category: 'wisdom' },
  { id: 'balance', name: 'Balance', values: [50, 50, 50], icon: '☯️', category: 'balancing' }
];

export const useRateStore = create(
  persist(
    (set, get) => ({
      // Current rate being tuned
      currentRate: {
        values: [50, 50, 50],
        name: '',
        description: '',
        category: '',
        potency: 0.5
      },
      
      // Rate history
      rateHistory: [],
      
      // Saved/custom rates
      customRates: [],
      
      // Rate library (from backend)
      rateLibrary: {
        healing_remedies: [],
        organs_systems: [],
        chakra_rates: [],
        conditions: [],
        balancing_rates: []
      },
      
      // Rate search
      searchQuery: '',
      searchResults: [],
      
      // Rate comparison
      comparisonRates: [],
      
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
              values: newValues
            }
          };
        });
      },
      
      setRateName: (name) => {
        set((state) => ({
          currentRate: {
            ...state.currentRate,
            name
          }
        }));
      },
      
      setRateCategory: (category) => {
        set((state) => ({
          currentRate: {
            ...state.currentRate,
            category
          }
        }));
      },
      
      setRateDescription: (description) => {
        set((state) => ({
          currentRate: {
            ...state.currentRate,
            description
          }
        }));
      },
      
      saveRate: (rate = null) => {
        const rateToSave = rate || get().currentRate;
        set((state) => ({
          customRates: [...state.customRates, {
            ...rateToSave,
            id: Date.now(),
            createdAt: new Date().toISOString()
          }]
        }));
      },
      
      deleteRate: (rateId) => {
        set((state) => ({
          customRates: state.customRates.filter(r => r.id !== rateId)
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
              timestamp: new Date().toISOString()
            },
            ...state.rateHistory
          ].slice(0, 100) // Keep last 100
        }));
      },
      
      setRateLibrary: (category, rates) => {
        set((state) => ({
          rateLibrary: {
            ...state.rateLibrary,
            [category]: rates
          }
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
        const allRates = [
          ...state.customRates,
          ...Object.values(state.rateLibrary).flat()
        ];
        
        const results = allRates.filter(rate => {
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
          comparisonRates: [...state.comparisonRates, rate].slice(0, 4) // Max 4
        }));
      },
      
      removeFromComparison: (rateId) => {
        set((state) => ({
          comparisonRates: state.comparisonRates.filter(r => r.id !== rateId)
        }));
      },
      
      clearComparison: () => {
        set({ comparisonRates: [] });
      },
      
      startTuning: (sessionId) => {
        set({
          isTuning: true,
          tuningSessionId: sessionId
        });
      },
      
      stopTuning: () => {
        set({
          isTuning: false,
          tuningSessionId: null,
          autoTune: false,
          autoTuneConfidence: 0
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
        const preset = RATE_PRESETS.find(p => p.id === presetId);
        if (preset) {
          set({
            currentRate: {
              ...get().currentRate,
              values: preset.values,
              name: preset.name,
              category: preset.category
            }
          });
        }
      },
      
      // Rate validation
      isValidRate: (rate) => {
        return rate.values && 
               Array.isArray(rate.values) && 
               rate.values.length >= 2 && 
               rate.values.every(v => v >= 0 && v <= 100);
      },
      
      // Rate statistics
      getRateStatistics: () => {
        const state = get();
        const allRates = [
          ...state.customRates,
          ...state.rateHistory
        ];
        
        if (allRates.length === 0) {
          return null;
        }
        
        const avgValues = allRates.reduce((acc, rate) => {
          rate.values.forEach((v, i) => {
            acc[i] = (acc[i] || 0) + v;
          });
          return acc;
        }, {});
        
        return {
          totalRates: allRates.length,
          avgValues: Object.values(avgValues).map((sum, i) => sum / allRates.length),
          mostUsedCategory: getMostUsedCategory(allRates),
          averagePotency: allRates.reduce((sum, r) => sum + (r.potency || 0), 0) / allRates.length
        };
      },
      
      // Clear all data
      clearAll: () => {
        set({
          currentRate: {
            values: [50, 50, 50],
            name: '',
            description: '',
            category: '',
            potency: 0.5
          },
          rateHistory: [],
          customRates: [],
          searchQuery: '',
          searchResults: [],
          comparisonRates: []
        });
      }
    }),
    {
      name: 'rate-storage',
      partialize: (state) => ({
        customRates: state.customRates,
        rateHistory: state.rateHistory.slice(0, 50) // Persist only last 50
      })
    }
  )
);

function getMostUsedCategory(rates) {
  const categories = {};
  rates.forEach(rate => {
    if (rate.category) {
      categories[rate.category] = (categories[rate.category] || 0) + 1;
    }
  });
  
  const entries = Object.entries(categories);
  if (entries.length === 0) return null;
  
  return entries.sort((a, b) => b[1] - a[1])[0][0];
}
