/**
 * Unit tests for rateStore — radionics rate tuning store.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useRateStore, RATE_PRESETS } from '../stores/rateStore';

describe('useRateStore', () => {
  beforeEach(() => {
    localStorage.clear();
    useRateStore.setState({
      currentRate: {
        values: [50, 50, 50],
        name: '',
        description: '',
        category: '',
        potency: 0.5,
      },
      rateHistory: [],
      customRates: [],
      rateLibrary: {
        healing_remedies: [],
        organs_systems: [],
        chakra_rates: [],
        conditions: [],
        balancing_rates: [],
      },
      searchQuery: '',
      searchResults: [],
      comparisonRates: [],
      isTuning: false,
      tuningSessionId: null,
      autoTune: false,
      autoTuneConfidence: 0,
    });
  });

  describe('RATE_PRESETS', () => {
    it('has 8 presets', () => {
      expect(RATE_PRESETS).toHaveLength(8);
    });

    it('every preset has id, name, values, icon, category', () => {
      for (const p of RATE_PRESETS) {
        expect(p.id).toBeTruthy();
        expect(p.name).toBeTruthy();
        expect(Array.isArray(p.values)).toBe(true);
        expect(p.values.length).toBe(3);
        expect(p.icon).toBeTruthy();
        expect(p.category).toBeTruthy();
      }
    });

    it('all preset values are in the 0-100 range', () => {
      for (const p of RATE_PRESETS) {
        for (const v of p.values) {
          expect(v).toBeGreaterThanOrEqual(0);
          expect(v).toBeLessThanOrEqual(100);
        }
      }
    });
  });

  describe('currentRate mutations', () => {
    it('setCurrentRate replaces the whole object', () => {
      const newRate = { values: [10, 20, 30], name: 'Custom', category: 'test', potency: 0.3 };
      useRateStore.getState().setCurrentRate(newRate);
      expect(useRateStore.getState().currentRate).toEqual(newRate);
    });

    it('updateRateValue clamps to 0-100', () => {
      useRateStore.getState().updateRateValue(0, 150);
      expect(useRateStore.getState().currentRate.values[0]).toBe(100);
      useRateStore.getState().updateRateValue(0, -20);
      expect(useRateStore.getState().currentRate.values[0]).toBe(0);
      useRateStore.getState().updateRateValue(1, 42);
      expect(useRateStore.getState().currentRate.values[1]).toBe(42);
    });

    it('updateRateValue preserves other slots', () => {
      useRateStore.getState().updateRateValue(1, 99);
      expect(useRateStore.getState().currentRate.values).toEqual([50, 99, 50]);
    });

    it('setRateName / setRateCategory / setRateDescription merge', () => {
      useRateStore.getState().setRateName('Healing Focus');
      useRateStore.getState().setRateCategory('healing');
      useRateStore.getState().setRateDescription('For the body');
      const r = useRateStore.getState().currentRate;
      expect(r.name).toBe('Healing Focus');
      expect(r.category).toBe('healing');
      expect(r.description).toBe('For the body');
    });
  });

  describe('customRates', () => {
    it('saveRate appends with id and timestamp', () => {
      useRateStore.getState().saveRate({ values: [60, 60, 60], name: 'Test' });
      const customs = useRateStore.getState().customRates;
      expect(customs).toHaveLength(1);
      expect(customs[0].id).toBeTypeOf('number');
      expect(customs[0].name).toBe('Test');
      expect(customs[0].createdAt).toBeTruthy();
    });

    it('saveRate with no arg saves currentRate', () => {
      useRateStore.getState().setRateName('AutoSaved');
      useRateStore.getState().saveRate();
      expect(useRateStore.getState().customRates[0].name).toBe('AutoSaved');
    });

    it('deleteRate removes by id', async () => {
      useRateStore.getState().saveRate({ values: [10, 10, 10], name: 'A' });
      await new Promise(r => setTimeout(r, 2));
      useRateStore.getState().saveRate({ values: [20, 20, 20], name: 'B' });
      const idA = useRateStore.getState().customRates.find(r => r.name === 'A')!.id;
      useRateStore.getState().deleteRate(idA);
      expect(useRateStore.getState().customRates).toHaveLength(1);
      expect(useRateStore.getState().customRates[0].name).toBe('B');
    });

    it('loadRate sets currentRate', () => {
      const rate = { values: [88, 88, 88], name: 'Loaded', category: 'test' };
      useRateStore.getState().loadRate(rate);
      expect(useRateStore.getState().currentRate).toEqual(rate);
    });
  });

  describe('rateHistory', () => {
    it('addToHistory prepends and caps at 100', () => {
      for (let i = 0; i < 105; i++) {
        useRateStore.getState().addToHistory({ values: [i, i, i], name: `H${i}` });
      }
      const history = useRateStore.getState().rateHistory;
      expect(history).toHaveLength(100);
      expect(history[0].name).toBe('H104');
    });
  });

  describe('searchRates', () => {
    it('matches by name', () => {
      useRateStore.setState({
        customRates: [{ id: 1, values: [10, 10, 10], name: 'Healing Boost' }],
      });
      useRateStore.getState().searchRates('healing');
      expect(useRateStore.getState().searchResults).toHaveLength(1);
    });

    it('matches by category', () => {
      useRateStore.setState({
        customRates: [{ id: 1, values: [10, 10, 10], name: 'X', category: 'love' }],
      });
      useRateStore.getState().searchRates('love');
      expect(useRateStore.getState().searchResults).toHaveLength(1);
    });

    it('matches by values', () => {
      useRateStore.setState({
        customRates: [{ id: 1, values: [44, 55, 66], name: 'X' }],
      });
      useRateStore.getState().searchRates('44-55-66');
      expect(useRateStore.getState().searchResults).toHaveLength(1);
    });

    it('returns empty for empty query', () => {
      useRateStore.getState().searchRates('');
      expect(useRateStore.getState().searchResults).toEqual([]);
    });
  });

  describe('comparison', () => {
    it('addToComparison caps at 4', () => {
      for (let i = 0; i < 6; i++) {
        useRateStore.getState().addToComparison({ id: i, name: `R${i}` });
      }
      expect(useRateStore.getState().comparisonRates).toHaveLength(4);
      expect(useRateStore.getState().comparisonRates[3].id).toBe(3);
    });

    it('removeFromComparison and clearComparison work', () => {
      useRateStore.getState().addToComparison({ id: 1, name: 'A' });
      useRateStore.getState().addToComparison({ id: 2, name: 'B' });
      useRateStore.getState().removeFromComparison(1);
      expect(useRateStore.getState().comparisonRates).toHaveLength(1);
      useRateStore.getState().clearComparison();
      expect(useRateStore.getState().comparisonRates).toEqual([]);
    });
  });

  describe('tuning sessions', () => {
    it('startTuning / stopTuning toggle state', () => {
      useRateStore.getState().startTuning('session-1');
      expect(useRateStore.getState().isTuning).toBe(true);
      expect(useRateStore.getState().tuningSessionId).toBe('session-1');
      useRateStore.getState().stopTuning();
      expect(useRateStore.getState().isTuning).toBe(false);
      expect(useRateStore.getState().tuningSessionId).toBe(null);
    });

    it('setAutoTuneConfidence clamps to 0-1', () => {
      useRateStore.getState().setAutoTuneConfidence(2);
      expect(useRateStore.getState().autoTuneConfidence).toBe(1);
      useRateStore.getState().setAutoTuneConfidence(-0.5);
      expect(useRateStore.getState().autoTuneConfidence).toBe(0);
    });
  });

  describe('isValidRate', () => {
    it('accepts a valid rate', () => {
      expect(useRateStore.getState().isValidRate({ values: [10, 20, 30] })).toBe(true);
    });

    it('rejects missing values', () => {
      expect(useRateStore.getState().isValidRate({ values: null })).toBe(false);
    });

    it('rejects too-few values', () => {
      expect(useRateStore.getState().isValidRate({ values: [50] })).toBe(false);
    });

    it('rejects out-of-range values', () => {
      expect(useRateStore.getState().isValidRate({ values: [50, 200, 30] })).toBe(false);
    });
  });

  describe('getRateStatistics', () => {
    it('returns null when no rates', () => {
      expect(useRateStore.getState().getRateStatistics()).toBe(null);
    });

    it('computes averages across custom + history', () => {
      useRateStore.setState({
        customRates: [
          { id: 1, values: [10, 20, 30], category: 'healing' },
        ],
        rateHistory: [
          { id: 2, values: [30, 40, 50], category: 'healing' },
        ],
      });
      const stats = useRateStore.getState().getRateStatistics();
      expect(stats!.totalRates).toBe(2);
      expect(stats!.avgValues[0]).toBeCloseTo(20);
      expect(stats!.avgValues[1]).toBeCloseTo(30);
      expect(stats!.avgValues[2]).toBeCloseTo(40);
      expect(stats!.mostUsedCategory).toBe('healing');
    });
  });
});
