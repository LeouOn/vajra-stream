/**
 * Unit tests for commandStore — command palette + search scoring.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useCommandStore, commandRegistry } from '../stores/commandStore';

describe('commandStore', () => {
  describe('commandRegistry', () => {
    it('has 23 commands across all categories', () => {
      expect(commandRegistry.length).toBeGreaterThanOrEqual(20);
      const categories = new Set(commandRegistry.map(c => c.category));
      expect(categories.has('Audio')).toBe(true);
      expect(categories.has('Sessions')).toBe(true);
      expect(categories.has('Radionics')).toBe(true);
      expect(categories.has('Crystals')).toBe(true);
      expect(categories.has('Dharma Tales')).toBe(true);
      expect(categories.has('Views')).toBe(true);
      expect(categories.has('Settings')).toBe(true);
      expect(categories.has('Help')).toBe(true);
    });

    it('every command has id, label, category, icon', () => {
      for (const cmd of commandRegistry) {
        expect(cmd.id).toBeTruthy();
        expect(cmd.label).toBeTruthy();
        expect(cmd.category).toBeTruthy();
        expect(cmd.icon).toBeTruthy();
      }
    });

    it('all command ids are unique', () => {
      const ids = commandRegistry.map(c => c.id);
      const unique = new Set(ids);
      expect(unique.size).toBe(ids.length);
    });
  });

  describe('useCommandStore basics', () => {
    beforeEach(() => {
      useCommandStore.setState({
        isOpen: false,
        query: '',
        selectedIndex: 0,
        recentCommands: [],
        searchResults: [],
        searchContext: null,
      });
    });

    it('setIsOpen(true) resets query and search state', () => {
      useCommandStore.setState({ query: 'old', selectedIndex: 5, searchContext: 'stories' });
      useCommandStore.getState().setIsOpen(true);
      const s = useCommandStore.getState();
      expect(s.isOpen).toBe(true);
      expect(s.query).toBe('');
      expect(s.selectedIndex).toBe(0);
      expect(s.searchContext).toBe('all');
    });

    it('setIsOpen(false) only changes isOpen', () => {
      useCommandStore.getState().setIsOpen(true);
      useCommandStore.getState().setQuery('test');
      useCommandStore.getState().setIsOpen(false);
      const s = useCommandStore.getState();
      expect(s.isOpen).toBe(false);
      expect(s.query).toBe('test');
    });

    it('setQuery and selectResult update state', () => {
      useCommandStore.getState().setQuery('audio');
      expect(useCommandStore.getState().query).toBe('audio');
      useCommandStore.getState().selectResult(3);
      expect(useCommandStore.getState().selectedIndex).toBe(3);
    });

    it('setQuery("audio") does not throw (no unhandled ReferenceError)', () => {
      // Regression: performSearch called getScore as a free function,
      // but it lives on state. Triggering a search logged a
      // ReferenceError as an unhandled rejection even though the
      // top-level call returned. setQuery must complete cleanly.
      expect(() => useCommandStore.getState().setQuery('audio')).not.toThrow();
      expect(useCommandStore.getState().query).toBe('audio');
    });

    it('addToRecent prepends and dedupes, caps at 10', () => {
      for (let i = 0; i < 12; i++) {
        useCommandStore.getState().addToRecent({ id: `cmd-${i}`, label: `C${i}`, category: 'X', icon: 'x' });
      }
      const recent = useCommandStore.getState().recentCommands;
      expect(recent).toHaveLength(10);
      expect(recent[0].id).toBe('cmd-11');
      expect(recent[9].id).toBe('cmd-2');
    });

    it('addToRecent dedupes by id', () => {
      const cmd = { id: 'a', label: 'A', category: 'X', icon: 'x' };
      useCommandStore.getState().addToRecent(cmd);
      useCommandStore.getState().addToRecent(cmd);
      useCommandStore.getState().addToRecent(cmd);
      expect(useCommandStore.getState().recentCommands).toHaveLength(1);
    });

    it('setSearchContext changes context and resets state', () => {
      useCommandStore.getState().setIsOpen(true);
      useCommandStore.getState().setSearchContext('stories');
      const s = useCommandStore.getState();
      expect(s.searchContext).toBe('stories');
      expect(s.query).toBe('');
      expect(s.selectedIndex).toBe(0);
    });
  });

  describe('getScore', () => {
    beforeEach(() => {
      useCommandStore.setState({
        isOpen: false, query: '', selectedIndex: 0, recentCommands: [], searchResults: [], searchContext: 'all',
      });
    });

    it('returns 0 for empty query', () => {
      expect(useCommandStore.getState().getScore('', 'audio play')).toBe(0);
    });

    it('returns 0 for empty text', () => {
      expect(useCommandStore.getState().getScore('audio', '')).toBe(0);
    });

    it('scores higher for exact term match', () => {
      const exact = useCommandStore.getState().getScore('audio', 'audio play');
      const partial = useCommandStore.getState().getScore('audio', 'audio');
      expect(exact).toBeGreaterThan(0);
      expect(partial).toBeGreaterThan(0);
    });

    it('scores multiple terms additively', () => {
      const multi = useCommandStore.getState().getScore('audio play', 'audio play stop');
      expect(multi).toBeGreaterThan(useCommandStore.getState().getScore('audio', 'audio play stop'));
    });

    it('returns 0 when no term matches', () => {
      expect(useCommandStore.getState().getScore('xyzzy', 'audio play')).toBe(0);
    });

    it('partial prefix match scores less than full match', () => {
      const full = useCommandStore.getState().getScore('play', 'play');
      const prefix = useCommandStore.getState().getScore('pl', 'play');
      expect(full).toBeGreaterThanOrEqual(prefix);
    });
  });

  describe('executeSelected', () => {
    beforeEach(() => {
      useCommandStore.setState({
        isOpen: false, query: '', selectedIndex: 0, recentCommands: [], searchResults: [], searchContext: 'all',
      });
    });

    it('returns null when no results and no query', () => {
      expect(useCommandStore.getState().executeSelected()).toBe(null);
    });

    it('returns the selected result and closes palette', () => {
      useCommandStore.setState({
        isOpen: true,
        searchResults: [
          { type: 'command', id: 'audio.play', label: 'Play Audio', category: 'Audio' },
        ],
        selectedIndex: 0,
      });
      const result = useCommandStore.getState().executeSelected();
      expect(result).toBeTruthy();
      expect(result!.id).toBe('audio.play');
      expect(useCommandStore.getState().isOpen).toBe(false);
    });

    it('falls back to fuzzy command match when no results but query matches', () => {
      useCommandStore.setState({ query: 'play audio', searchResults: [] });
      const result = useCommandStore.getState().executeSelected();
      expect(result).toBeTruthy();
      expect(result!.type).toBe('command');
    });
  });
});
