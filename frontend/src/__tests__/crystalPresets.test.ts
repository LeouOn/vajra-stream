// Tests for the crystal bowl preset library.
// These verify the Solfeggio snapping is correct (matches core/rate_to_audio.py
// in the backend) and that presets produce the expected musical combinations.

import { describe, it, expect } from 'vitest';

import {
  CHAKRA_PRESETS,
  HARMONIC_PRESETS,
  ALL_PRESETS,
  presetFrequencies,
  presetFrequencySummary,
  snapToSolfeggio,
  solfeggioName,
  type CrystalPreset,
} from '../lib/crystalPresets';

describe('crystalPresets', () => {
  describe('snapToSolfeggio', () => {
    it('maps 0-14 to 396 (Ut - Liberation)', () => {
      expect(snapToSolfeggio(0)).toBe(396);
      expect(snapToSolfeggio(7)).toBe(396);
      expect(snapToSolfeggio(14)).toBe(396);
    });

    it('maps 15-28 to 417 (Re - Change)', () => {
      expect(snapToSolfeggio(15)).toBe(417);
      expect(snapToSolfeggio(21)).toBe(417);
      expect(snapToSolfeggio(28)).toBe(417);
    });

    it('maps 29-42 to 528 (Mi - Transformation)', () => {
      expect(snapToSolfeggio(29)).toBe(528);
      expect(snapToSolfeggio(35)).toBe(528);
      expect(snapToSolfeggio(42)).toBe(528);
    });

    it('maps 43-57 to 639 (La - Connection)', () => {
      expect(snapToSolfeggio(43)).toBe(639);
      expect(snapToSolfeggio(50)).toBe(639);
      expect(snapToSolfeggio(57)).toBe(639);
    });

    it('maps 58-71 to 741 (Sol - Awakening)', () => {
      expect(snapToSolfeggio(58)).toBe(741);
      expect(snapToSolfeggio(64)).toBe(741);
      expect(snapToSolfeggio(71)).toBe(741);
    });

    it('maps 72-85 to 852 (Si - Spiritual Order)', () => {
      expect(snapToSolfeggio(72)).toBe(852);
      expect(snapToSolfeggio(78)).toBe(852);
      expect(snapToSolfeggio(85)).toBe(852);
    });

    it('maps 86-100 to 963 (Divine Consciousness)', () => {
      expect(snapToSolfeggio(86)).toBe(963);
      expect(snapToSolfeggio(92)).toBe(963);
      expect(snapToSolfeggio(100)).toBe(963);
    });

    it('clamps out-of-range values', () => {
      expect(snapToSolfeggio(-10)).toBe(396);
      expect(snapToSolfeggio(150)).toBe(963);
    });
  });

  describe('CHAKRA_PRESETS', () => {
    it('has 7 chakra presets (one per energy center)', () => {
      expect(CHAKRA_PRESETS).toHaveLength(7);
    });

    it('each preset has 5 dial values that snap to ONE Solfeggio tone', () => {
      for (const preset of CHAKRA_PRESETS) {
        const freqs = presetFrequencies(preset);
        expect(freqs).toHaveLength(1);
        // Verify the snap matches what the preset label claims
        const expectedFreqs: Record<string, number> = {
          root: 396, sacral: 417, solar_plexus: 528,
          heart: 639, throat: 741, third_eye: 852, crown: 963,
        };
        expect(freqs[0]).toBe(expectedFreqs[preset.id]);
      }
    });

    it('all presets are in ascending Solfeggio order', () => {
      const freqs = CHAKRA_PRESETS.map((p) => presetFrequencies(p)[0]);
      const sorted = [...freqs].sort((a, b) => a - b);
      expect(freqs).toEqual(sorted);
    });
  });

  describe('HARMONIC_PRESETS', () => {
    it('heart_opening produces 528 + 639 Hz (Mi + La — consonant)', () => {
      const preset = HARMONIC_PRESETS.find((p) => p.id === 'heart_opening')!;
      const freqs = presetFrequencies(preset);
      expect(freqs.sort()).toEqual([528, 639]);
    });

    it('deep_healing produces 396 + 528 Hz (Ut + Mi — open fifth)', () => {
      const preset = HARMONIC_PRESETS.find((p) => p.id === 'deep_healing')!;
      const freqs = presetFrequencies(preset);
      expect(freqs.sort()).toEqual([396, 528]);
    });

    it('crown_activation produces 852 + 963 Hz', () => {
      const preset = HARMONIC_PRESETS.find((p) => p.id === 'crown_activation')!;
      const freqs = presetFrequencies(preset);
      expect(freqs.sort()).toEqual([852, 963]);
    });

    it('grounding produces only 396 Hz (single tone)', () => {
      const preset = HARMONIC_PRESETS.find((p) => p.id === 'grounding')!;
      expect(presetFrequencies(preset)).toEqual([396]);
    });
  });

  describe('presetFrequencies', () => {
    it('deduplicates equal dial values', () => {
      const preset: CrystalPreset = {
        id: 'test', label: 'test', icon: '🧪',
        dims: { d1: 10, d2: 10, d3: 10, d4: 10, d5: 10 },
        description: 'all same',
      };
      expect(presetFrequencies(preset)).toEqual([396]);
    });

    it('returns in encounter order (first occurrence wins)', () => {
      const preset: CrystalPreset = {
        id: 'test', label: 'test', icon: '🧪',
        dims: { d1: 7, d2: 50, d3: 7, d4: 50, d5: 7 },
        description: 'alternating',
      };
      // First occurrence is 396, then 639
      expect(presetFrequencies(preset)).toEqual([396, 639]);
    });
  });

  describe('presetFrequencySummary', () => {
    it('formats single frequency as "N Hz"', () => {
      const preset = HARMONIC_PRESETS.find((p) => p.id === 'grounding')!;
      expect(presetFrequencySummary(preset)).toBe('396 Hz');
    });

    it('formats two frequencies as "N + M Hz"', () => {
      const preset = HARMONIC_PRESETS.find((p) => p.id === 'heart_opening')!;
      expect(presetFrequencySummary(preset)).toBe('528 + 639 Hz');
    });

    it('formats multiple as range "N→M Hz"', () => {
      const preset = HARMONIC_PRESETS.find((p) => p.id === 'full_spectrum')!;
      const summary = presetFrequencySummary(preset);
      expect(summary).toMatch(/^\d+→\d+ Hz$/);
    });
  });

  describe('solfeggioName', () => {
    it('returns named tone for known frequencies', () => {
      expect(solfeggioName(396)).toBe('Ut (Liberation)');
      expect(solfeggioName(528)).toBe('Mi (Transformation)');
      expect(solfeggioName(963)).toBe('Divine Consciousness');
    });

    it('returns formatted Hz for unknown frequencies', () => {
      expect(solfeggioName(440)).toBe('440.00 Hz');
    });
  });

  describe('ALL_PRESETS', () => {
    it('combines chakra and harmonic presets', () => {
      expect(ALL_PRESETS.length).toBe(CHAKRA_PRESETS.length + HARMONIC_PRESETS.length);
    });

    it('all presets have valid structure', () => {
      for (const preset of ALL_PRESETS) {
        expect(preset.id).toBeTruthy();
        expect(preset.label).toBeTruthy();
        expect(preset.dims.d1).toBeGreaterThanOrEqual(0);
        expect(preset.dims.d1).toBeLessThanOrEqual(100);
        expect(preset.dims.d5).toBeGreaterThanOrEqual(0);
        expect(preset.dims.d5).toBeLessThanOrEqual(100);
      }
    });
  });
});
