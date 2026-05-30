/**
 * Crystal Store — Zustand state for crystal grid configuration.
 *
 * Manages crystal inventory, active grid geometry (type, radius,
 * crystal count), programming intentions, and energy-field toggles
 * for the 3D crystal grid visualisation. Persisted to localStorage.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useCrystalStore = create(
  persist(
    (set, get) => ({
      // Crystal inventory
      crystals: [],
      
      // Active grid configuration
      gridConfig: {
        type: 'double-hexagon',
        crystalType: 'quartz',
        radius: 4,
        showEnergyField: true,
        intention: 'May all beings be happy',
        crystalCount: 13
      },
      
      // Crystal programming state
      programming: {
        isActive: false,
        crystalIndex: null,
        intention: '',
        step: 0,
        startTime: null
      },
      
      // Crystal attunement state
      attunement: {
        isActive: false,
        step: 0,
        totalSteps: 7,
        chakras: ['root', 'sacral', 'solar_plexus', 'heart', 'throat', 'third_eye', 'crown'],
        currentChakra: 'root'
      },
      
      // Crystal meditation state
      meditation: {
        isActive: false,
        duration: 300,
        elapsed: 0,
        breathPhase: 'inhale',
        breathCount: 0
      },
      
      // Crystal library data
      crystalLibrary: [
        { id: 'quartz', name: 'Clear Quartz', color: '#ffffff', emissive: '#ccccff', properties: ['amplification', 'clarity', 'healing'], chakras: ['crown'], description: 'Master healer, amplifies energy and intention' },
        { id: 'amethyst', name: 'Amethyst', color: '#9966ff', emissive: '#6633cc', properties: ['protection', 'purification', 'spiritual'], chakras: ['third_eye', 'crown'], description: 'Spiritual protection and enhanced intuition' },
        { id: 'rose-quartz', name: 'Rose Quartz', color: '#ffb6c1', emissive: '#ff99aa', properties: ['love', 'compassion', 'peace'], chakras: ['heart'], description: 'Unconditional love and emotional healing' },
        { id: 'citrine', name: 'Citrine', color: '#ffd700', emissive: '#ffaa00', properties: ['abundance', 'energy', 'joy'], chakras: ['solar_plexus'], description: 'Abundance, prosperity and positive energy' },
        { id: 'black-tourmaline', name: 'Black Tourmaline', color: '#222222', emissive: '#111111', properties: ['protection', 'grounding', 'shielding'], chakras: ['root'], description: 'Powerful protection and EMF shielding' },
        { id: 'selenite', name: 'Selenite', color: '#ffffff', emissive: '#ffffee', properties: ['purification', 'connection', 'peace'], chakras: ['crown'], description: 'High vibration cleansing and connection' },
        { id: 'lapis-lazuli', name: 'Lapis Lazuli', color: '#1a3a6c', emissive: '#2244aa', properties: ['wisdom', 'truth', 'awareness'], chakras: ['third_eye', 'throat'], description: 'Deep wisdom, truth and inner awareness' },
        { id: 'carnelian', name: 'Carnelian', color: '#e04000', emissive: '#cc3300', properties: ['vitality', 'creativity', 'courage'], chakras: ['sacral'], description: 'Vitality, creativity and motivation' }
      ],
      
      // Saved grid templates
      gridTemplates: [
        { id: 'hexagon', name: 'Hexagon (6)', description: 'Basic 6-crystal grid', crystalCount: 6 },
        { id: 'double-hexagon', name: 'Double Hexagon (13)', description: 'Inner + outer hexagon with center', crystalCount: 13 },
        { id: 'star', name: 'Star of David (13)', description: 'Sacred geometry star pattern', crystalCount: 13 },
        { id: 'grid', name: '3x3 Grid (9)', description: 'Square grid arrangement', crystalCount: 9 }
      ],
      
      // Actions
      setGridConfig: (config) => {
        set((state) => ({
          gridConfig: { ...state.gridConfig, ...config }
        }));
      },
      
      setGridType: (type) => {
        set((state) => ({
          gridConfig: { ...state.gridConfig, type }
        }));
      },
      
      setCrystalType: (crystalType) => {
        set((state) => ({
          gridConfig: { ...state.gridConfig, crystalType }
        }));
      },
      
      setIntention: (intention) => {
        set((state) => ({
          gridConfig: { ...state.gridConfig, intention }
        }));
      },
      
      // Crystal inventory management
      addCrystal: (crystal) => {
        set((state) => ({
          crystals: [...state.crystals, {
            id: Date.now(),
            ...crystal,
            addedAt: new Date().toISOString(),
            programmed: false,
            lastCharged: null
          }]
        }));
      },
      
      removeCrystal: (id) => {
        set((state) => ({
          crystals: state.crystals.filter(c => c.id !== id)
        }));
      },
      
      updateCrystal: (id, updates) => {
        set((state) => ({
          crystals: state.crystals.map(c => 
            c.id === id ? { ...c, ...updates } : c
          )
        }));
      },
      
      // Programming
      startProgramming: (crystalIndex, intention) => {
        set({
          programming: {
            isActive: true,
            crystalIndex,
            intention,
            step: 0,
            startTime: new Date().toISOString()
          }
        });
      },
      
      advanceProgrammingStep: () => {
        set((state) => ({
          programming: {
            ...state.programming,
            step: state.programming.step + 1
          }
        }));
      },
      
      completeProgramming: () => {
        set({
          programming: {
            isActive: false,
            crystalIndex: null,
            intention: '',
            step: 0,
            startTime: null
          }
        });
      },
      
      // Attunement
      startAttunement: () => {
        set({
          attunement: {
            ...get().attunement,
            isActive: true,
            step: 0,
            currentChakra: 'root'
          }
        });
      },
      
      advanceAttunementStep: () => {
        const state = get();
        const nextStep = state.attunement.step + 1;
        if (nextStep >= state.attunement.totalSteps) {
          set({
            attunement: {
              ...state.attunement,
              isActive: false,
              step: 0
            }
          });
        } else {
          set({
            attunement: {
              ...state.attunement,
              step: nextStep,
              currentChakra: state.attunement.chakras[nextStep]
            }
          });
        }
      },
      
      stopAttunement: () => {
        set({
          attunement: {
            ...get().attunement,
            isActive: false,
            step: 0
          }
        });
      },
      
      // Meditation
      startMeditation: (duration = 300) => {
        set({
          meditation: {
            isActive: true,
            duration,
            elapsed: 0,
            breathPhase: 'inhale',
            breathCount: 0
          }
        });
      },
      
      updateMeditation: (elapsed) => {
        set((state) => {
          const breathCycle = 12; // seconds per breath cycle
          const totalBreaths = Math.floor(elapsed / breathCycle);
          const phase = (elapsed % breathCycle) < 4 ? 'inhale' : 
                        (elapsed % breathCycle) < 8 ? 'hold' : 'exhale';
          return {
            meditation: {
              ...state.meditation,
              elapsed,
              breathPhase: phase,
              breathCount: totalBreaths
            }
          };
        });
      },
      
      stopMeditation: () => {
        set({
          meditation: {
            ...get().meditation,
            isActive: false,
            elapsed: 0
          }
        });
      },
      
      // Get crystal by type
      getCrystalByType: (typeId) => {
        return get().crystalLibrary.find(c => c.id === typeId);
      },
      
      // Get crystals by chakra
      getCrystalsByChakra: (chakra) => {
        return get().crystalLibrary.filter(c => c.chakras.includes(chakra));
      },
      
      // Get crystals by property
      getCrystalsByProperty: (property) => {
        return get().crystalLibrary.filter(c => c.properties.includes(property));
      },

      fetchCrystalGrid: async () => {
        try {
          const response = await fetch('/api/v1/radionics/crystal/grid');
          if (!response.ok) throw new Error('Failed to fetch crystal grid');
          const data = await response.json();
          return data;
        } catch (error) {
          console.warn('Crystal grid fetch failed:', error);
          return null;
        }
      },

      programCrystal: async (crystalId, intention) => {
        try {
          const response = await fetch('/api/v1/radionics/crystal/program', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ crystal_id: crystalId, intention }),
          });
          if (!response.ok) throw new Error('Failed to program crystal');
          return await response.json();
        } catch (error) {
          console.error('Crystal programming failed:', error);
          return null;
        }
      },

      broadcastCrystal: async (duration = 3600, hardwareLevel = 2) => {
        try {
          const response = await fetch('/api/v1/radionics/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ duration_minutes: duration / 60, hardware_level: hardwareLevel }),
          });
          if (!response.ok) throw new Error('Failed to broadcast');
          return await response.json();
        } catch (error) {
          console.error('Crystal broadcast failed:', error);
          return null;
        }
      },
    }),
    {
      name: 'crystal-storage',
      partialize: (state) => ({
        crystals: state.crystals,
        gridConfig: state.gridConfig
      })
    }
  )
);
