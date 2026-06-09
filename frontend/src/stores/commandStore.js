/**
 * Command Store — Zustand state for the command palette and terminal history.
 *
 * Maintains a registry of available commands (audio, sessions, radionics,
 * crystals, navigation, UI), a history stack for the CommandCenter terminal,
 * and command execution status. Persisted to localStorage.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const commandRegistry = [
  // Audio & Broadcasting
  { id: 'audio.generate', label: 'Generate Audio', category: 'Audio', shortcut: 'Ctrl+G', icon: 'play' },
  { id: 'audio.play', label: 'Play Audio', category: 'Audio', shortcut: 'Ctrl+P', icon: 'play' },
  { id: 'audio.stop', label: 'Stop Audio', category: 'Audio', shortcut: 'Esc', icon: 'stop' },
  { id: 'audio.om', label: 'Set OM Frequency', category: 'Audio', icon: 'music' },
  { id: 'audio.528', label: 'Set 528 Hz (Love)', category: 'Audio', icon: 'heart' },
  { id: 'audio.7.83', label: 'Set 7.83 Hz (Earth)', category: 'Audio', icon: 'globe' },

  // Sessions
  { id: 'session.new', label: 'New Session', category: 'Sessions', shortcut: 'Ctrl+N', icon: 'plus' },
  { id: 'session.list', label: 'View All Sessions', category: 'Sessions', shortcut: 'Ctrl+L', icon: 'list' },
  { id: 'session.stop-all', label: 'Stop All Sessions', category: 'Sessions', icon: 'stop' },

  // Rate Tuner
  { id: 'rate.tuner', label: 'Open Rate Tuner', category: 'Radionics', shortcut: 'Ctrl+R', icon: 'sliders' },
  { id: 'rate.presets', label: 'View Rate Presets', category: 'Radionics', icon: 'bookmark' },
  { id: 'rate.search', label: 'Search Rates', category: 'Radionics', icon: 'search' },
  { id: 'rate.save', label: 'Save Current Rate', category: 'Radionics', shortcut: 'Ctrl+S', icon: 'save' },

  // Crystal Work
  { id: 'crystal.program', label: 'Program Crystal', category: 'Crystals', shortcut: 'Ctrl+C', icon: 'gem' },
  { id: 'crystal.attune', label: 'Attune Crystals', category: 'Crystals', icon: 'sparkles' },
  { id: 'crystal.grid', label: 'View Crystal Grid', category: 'Crystals', icon: 'grid' },

  // Dharma Tales
  { id: 'tales.new', label: 'New Dharma Tale', category: 'Dharma Tales', shortcut: 'Ctrl+T', icon: 'book-open' },
  { id: 'tales.library', label: 'Story Library', category: 'Dharma Tales', shortcut: 'Ctrl+Shift+L', icon: 'library' },
  { id: 'tales.generate', label: 'Generate Teaching Tale', category: 'Dharma Tales', shortcut: '', icon: 'sparkles' },

  // Views
  { id: 'view.dashboard', label: 'Dashboard', category: 'Views', shortcut: 'Ctrl+D', icon: 'layout-dashboard' },
  { id: 'view.visualization', label: '3D Visualization', category: 'Views', shortcut: 'Ctrl+V', icon: 'eye' },

  // Settings & Help
  { id: 'help.shortcuts', label: 'Keyboard Shortcuts', category: 'Help', shortcut: '?', icon: 'keyboard' },
  { id: 'help.tour', label: 'Start Tour', category: 'Help', icon: 'info' },
  { id: 'help.docs', label: 'Documentation', category: 'Help', icon: 'file-text' },
  { id: 'settings', label: 'Settings', category: 'Settings', shortcut: 'Ctrl+,', icon: 'settings' },
];

export const useCommandStore = create(
  persist(
    (set, get) => ({
      isOpen: false,
      query: '',
      selectedIndex: 0,
      recentCommands: [],
      searchResults: [],
      searchContext: null, // 'all', 'stories', 'rates', 'crystals', 'commands'

      setIsOpen: (open) => {
        set({ isOpen: open });
        if (open) {
          set({ query: '', selectedIndex: 0, searchResults: [], searchContext: 'all' });
        }
      },

      setQuery: (query) => {
        set({ query });
        get().performSearch(query);
      },

      selectResult: (index) => {
        set({ selectedIndex: index });
      },

      executeSelected: () => {
        const { selectedIndex, searchResults, query } = get();
        
        if (searchResults.length > 0 && selectedIndex < searchResults.length) {
          const selected = searchResults[selectedIndex];
          set({ isOpen: false, query: '' });
          return selected;
        }
        
        // If no search results and query matches a command
        if (query) {
          const command = commandRegistry.find(cmd => 
            cmd.id === query.toLowerCase().replace(/[^a-z0-9]/g, '') ||
            cmd.label.toLowerCase().includes(query.toLowerCase())
          );
          if (command) {
            set({ isOpen: false, query: '' });
            return { type: 'command', ...command };
          }
        }
        
        return null;
      },

      addToRecent: (command) => {
        set((state) => {
          const filtered = state.recentCommands.filter(c => c.id !== command.id);
          return {
            recentCommands: [command, ...filtered].slice(0, 10)
          };
        });
      },

      setSearchContext: (context) => {
        set({ searchContext: context, query: '', selectedIndex: 0 });
        if (context !== 'all') {
          get().performSearch('');
        }
      },

      performSearch: async (query) => {
        if (!query.trim()) {
          set({ searchResults: [] });
          return;
        }

        const state = get();
        const results = [];

        // Search commands
        if (state.searchContext === 'all' || state.searchContext === 'commands') {
          commandRegistry.forEach(cmd => {
            const score = state.getScore(query, [cmd.label, cmd.id, cmd.category].join(' '));
            if (score > 0) {
              results.push({ type: 'command', ...cmd, score });
            }
          });
        }

        // Search stories (if backend available)
        if ((state.searchContext === 'all' || state.searchContext === 'stories')) {
          try {
            const response = await fetch('/api/v1/stories/search?q=' + encodeURIComponent(query));
            if (response.ok) {
              const data = await response.json();
              data.stories?.forEach(story => {
                const score = state.getScore(query, [story.title, story.content, ...(story.tags || []), story.theme, story.tradition].join(' '));
                if (score > 0) {
                  results.push({ type: 'story', ...story, score });
                }
              });
            }
          } catch {
            // Fallback to local stories
            const savedTales = JSON.parse(localStorage.getItem('dharma-tales') || '[]');
            savedTales.forEach(story => {
              const score = state.getScore(query, [story.tale, story.theme, story.tradition].join(' '));
              if (score > 0) {
                results.push({ type: 'story', ...story, id: story.id, title: story.tale.slice(0, 50) + '...', score });
              }
            });
          }
        }

        // Search rates
        if ((state.searchContext === 'all' || state.searchContext === 'rates')) {
          try {
            const response = await fetch('/api/v1/radionics/rates/search?query=' + encodeURIComponent(query));
            if (response.ok) {
              const data = await response.json();
              data.results?.forEach(rate => {
                const score = state.getScore(query, [rate.name, rate.description, rate.values?.join('-'), rate.category].join(' '));
                if (score > 0) {
                  results.push({ type: 'rate', ...rate, score });
                }
              });
            }
          } catch {
            // Fallback to local rates
            // (would need to load from rateStore)
          }
        }

        // Search crystals
        if ((state.searchContext === 'all' || state.searchContext === 'crystals')) {
          const crystalLibrary = [
            { id: 'quartz', name: 'Clear Quartz', properties: ['amplification', 'clarity', 'healing'], chakras: ['crown'], description: 'Master healer, amplifies energy and intention' },
            { id: 'amethyst', name: 'Amethyst', properties: ['protection', 'purification', 'spiritual'], chakras: ['third_eye', 'crown'], description: 'Spiritual protection and enhanced intuition' },
            { id: 'rose-quartz', name: 'Rose Quartz', properties: ['love', 'compassion', 'peace'], chakras: ['heart'], description: 'Unconditional love and emotional healing' },
            { id: 'citrine', name: 'Citrine', properties: ['abundance', 'energy', 'joy'], chakras: ['solar_plexus'], description: 'Abundance, prosperity and positive energy' },
            { id: 'black-tourmaline', name: 'Black Tourmaline', properties: ['protection', 'grounding', 'shielding'], chakras: ['root'], description: 'Powerful protection and EMF shielding' },
            { id: 'selenite', name: 'Selenite', properties: ['purification', 'connection', 'peace'], chakras: ['crown'], description: 'High vibration cleansing and connection' },
            { id: 'lapis-lazuli', name: 'Lapis Lazuli', properties: ['wisdom', 'truth', 'awareness'], chakras: ['third_eye', 'throat'], description: 'Deep wisdom, truth and inner awareness' },
            { id: 'carnelian', name: 'Carnelian', properties: ['vitality', 'creativity', 'courage'], chakras: ['sacral'], description: 'Vitality, creativity and motivation' },
          ];
          crystalLibrary.forEach(crystal => {
            const score = state.getScore(query, [crystal.name, crystal.description, ...crystal.properties, ...crystal.chakras].join(' '));
            if (score > 0) {
              results.push({ type: 'crystal', ...crystal, score });
            }
          });
        }

        // Sort by score and remove duplicates
        const sortedResults = results
          .sort((a, b) => b.score - a.score)
          .filter((item, index, arr) => arr.findIndex(i => i.id === item.id) === index)
          .slice(0, 10);

        set({ searchResults: sortedResults, selectedIndex: 0 });
      },

      getScore: (query, text) => {
        if (!query || !text) return 0;
        
        const terms = query.toLowerCase().split(' ').filter(t => t);
        let score = 0;
        
        const textLower = text.toLowerCase();
        
        terms.forEach(term => {
          if (textLower.includes(term)) {
            score += 10;
          } else if (textLower.includes(term.substring(0, Math.min(3, term.length)))) {
            score += 5;
          } else if (textLower.includes(term.charAt(0))) {
            score += 2;
          }
          
          // Bonus for word match
          if (textLower === term || textLower.endsWith(' ' + term) || textLower.startsWith(term + ' ')) {
            score += 5;
          }
        });

        return score;
      }
    }),
    {
      name: 'command-storage',
      partialize: (state) => ({
        recentCommands: state.recentCommands.slice(0, 10)
      })
    }
  )
);

export { commandRegistry };
