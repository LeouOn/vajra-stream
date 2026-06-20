/**
 * Command Store — Zustand state for the command palette and terminal history.
 *
 * Maintains a registry of available commands (audio, sessions, radionics,
 * crystals, navigation, UI), a history stack for the CommandCenter terminal,
 * and command execution status. Persisted to localStorage.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CommandDef } from '../types';

/** A registered command (static catalogue). */
export type Command = CommandDef;

/** A command previously invoked by the user (recent history). */
export interface RecentCommand {
  id: string;
  label?: string;
  category?: string;
  icon?: string;
  [key: string]: unknown;
}

/** Search context filter for the palette. */
export type SearchContext = 'all' | 'stories' | 'rates' | 'crystals' | 'commands' | null;

/**
 * Unified search-result item. Discriminated by `type`; uses an index
 * signature because each backend entity (story / rate / crystal / command)
 * surfaces different fields and we deliberately keep the union permissive.
 */
export interface SearchResultItem {
  type: string;
  id: string | number;
  label?: string;
  name?: string;
  description?: string;
  category?: string;
  score?: number;
  values?: number[];
  [key: string]: unknown;
}

export interface CommandState {
  isOpen: boolean;
  query: string;
  selectedIndex: number;
  recentCommands: RecentCommand[];
  searchResults: SearchResultItem[];
  searchContext: SearchContext;

  setIsOpen: (open: boolean) => void;
  setQuery: (query: string) => void;
  selectResult: (index: number) => void;
  executeSelected: () => SearchResultItem | null;
  addToRecent: (command: RecentCommand) => void;
  setSearchContext: (context: Exclude<SearchContext, null>) => void;
  performSearch: (query: string) => Promise<void>;
  getScore: (query: string, text: string) => number;
}

const commandRegistry: Command[] = [
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

export const useCommandStore = create<CommandState>()(
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
          const command = commandRegistry.find(
            (cmd) =>
              cmd.id === query.toLowerCase().replace(/[^a-z0-9]/g, '') ||
              cmd.label.toLowerCase().includes(query.toLowerCase()),
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
          const filtered = state.recentCommands.filter((c) => c.id !== command.id);
          return {
            recentCommands: [command, ...filtered].slice(0, 10),
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
        const results: SearchResultItem[] = [];

        // Search commands
        if (state.searchContext === 'all' || state.searchContext === 'commands') {
          commandRegistry.forEach((cmd) => {
            const score = state.getScore(query, [cmd.label, cmd.id, cmd.category].join(' '));
            if (score > 0) {
              results.push({ type: 'command', ...cmd, score });
            }
          });
        }

        // Search stories (if backend available)
        if (state.searchContext === 'all' || state.searchContext === 'stories') {
          try {
            const response = await fetch('/api/v1/stories/search?q=' + encodeURIComponent(query));
            if (response.ok) {
              const data = await response.json();
              data.stories?.forEach((story: Record<string, unknown>) => {
                const tags = Array.isArray(story.tags) ? story.tags : [];
                const parts = [story.title, story.content, ...tags, story.theme, story.tradition]
                  .map((p) => (typeof p === 'string' ? p : ''))
                  .join(' ');
                const score = state.getScore(query, parts);
                if (score > 0) {
                  results.push({ type: 'story', ...story, id: story.id as string | number, score });
                }
              });
            }
          } catch {
            // Fallback to local stories
            const savedTales: Array<Record<string, unknown>> = JSON.parse(
              localStorage.getItem('dharma-tales') || '[]',
            );
            savedTales.forEach((story) => {
              const tale = typeof story.tale === 'string' ? story.tale : '';
              const theme = typeof story.theme === 'string' ? story.theme : '';
              const tradition = typeof story.tradition === 'string' ? story.tradition : '';
              const score = state.getScore(query, [tale, theme, tradition].join(' '));
              if (score > 0) {
                results.push({
                  type: 'story',
                  ...story,
                  id: story.id as string | number,
                  title: tale.slice(0, 50) + '...',
                  score,
                });
              }
            });
          }
        }

        // Search rates
        if (state.searchContext === 'all' || state.searchContext === 'rates') {
          try {
            const response = await fetch('/api/v1/radionics/rates/search?query=' + encodeURIComponent(query));
            if (response.ok) {
              const data = await response.json();
              data.results?.forEach((rate: Record<string, unknown>) => {
                const values = Array.isArray(rate.values) ? rate.values : [];
                const parts = [rate.name, rate.description, values.join('-'), rate.category]
                  .map((p) => (typeof p === 'string' ? p : ''))
                  .join(' ');
                const score = state.getScore(query, parts);
                if (score > 0) {
                  results.push({ type: 'rate', ...rate, id: rate.id as string | number, score });
                }
              });
            }
          } catch {
            // Fallback to local rates
            // (would need to load from rateStore)
          }
        }

        // Search crystals
        if (state.searchContext === 'all' || state.searchContext === 'crystals') {
          const crystalLibrary: Array<Record<string, unknown>> = [
            { id: 'quartz', name: 'Clear Quartz', properties: ['amplification', 'clarity', 'healing'], chakras: ['crown'], description: 'Master healer, amplifies energy and intention' },
            { id: 'amethyst', name: 'Amethyst', properties: ['protection', 'purification', 'spiritual'], chakras: ['third_eye', 'crown'], description: 'Spiritual protection and enhanced intuition' },
            { id: 'rose-quartz', name: 'Rose Quartz', properties: ['love', 'compassion', 'peace'], chakras: ['heart'], description: 'Unconditional love and emotional healing' },
            { id: 'citrine', name: 'Citrine', properties: ['abundance', 'energy', 'joy'], chakras: ['solar_plexus'], description: 'Abundance, prosperity and positive energy' },
            { id: 'black-tourmaline', name: 'Black Tourmaline', properties: ['protection', 'grounding', 'shielding'], chakras: ['root'], description: 'Powerful protection and EMF shielding' },
            { id: 'selenite', name: 'Selenite', properties: ['purification', 'connection', 'peace'], chakras: ['crown'], description: 'High vibration cleansing and connection' },
            { id: 'lapis-lazuli', name: 'Lapis Lazuli', properties: ['wisdom', 'truth', 'awareness'], chakras: ['third_eye', 'throat'], description: 'Deep wisdom, truth and inner awareness' },
            { id: 'carnelian', name: 'Carnelian', properties: ['vitality', 'creativity', 'courage'], chakras: ['sacral'], description: 'Vitality, creativity and motivation' },
          ];
          crystalLibrary.forEach((crystal) => {
            const name = typeof crystal.name === 'string' ? crystal.name : '';
            const description = typeof crystal.description === 'string' ? crystal.description : '';
            const properties = Array.isArray(crystal.properties) ? crystal.properties : [];
            const chakras = Array.isArray(crystal.chakras) ? crystal.chakras : [];
            const parts = [name, description, ...properties, ...chakras].join(' ');
            const score = state.getScore(query, parts);
            if (score > 0) {
              results.push({ type: 'crystal', ...crystal, id: crystal.id as string, score });
            }
          });
        }

        // Sort by score and remove duplicates
        const sortedResults = results
          .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
          .filter((item, index, arr) => arr.findIndex((i) => i.id === item.id) === index)
          .slice(0, 10);

        set({ searchResults: sortedResults, selectedIndex: 0 });
      },

      getScore: (query, text) => {
        if (!query || !text) return 0;

        const terms = query.toLowerCase().split(' ').filter((t) => t);
        let score = 0;

        const textLower = text.toLowerCase();

        terms.forEach((term) => {
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
      },
    }),
    {
      name: 'command-storage',
      partialize: (state) => ({
        recentCommands: state.recentCommands.slice(0, 10),
      }),
    },
  ),
);

export { commandRegistry };
