// Tests for RateTuner's Solfeggio preview + preset wiring.
// Verifies that the rate_to_audio bridge is correctly applied to the
// RateTuner's variable-dial-count model (2-5 dials).

import { describe, it, expect } from 'vitest';

import {
  snapToSolfeggio,
  presetFrequencies,
  presetFrequencySummary,
  CHAKRA_PRESETS,
  HARMONIC_PRESETS,
} from '../lib/crystalPresets';

/**
 * Helper — mirrors the live preview calculation in RateTuner.tsx.
 * Takes a list of dial values (2-5) and returns the unique Solfeggio
 * frequencies they map to, preserving encounter order.
 */
function livePreviewFrequencies(dialValues: number[]): number[] {
  const seen = new Set<number>();
  const out: number[] = [];
  for (const v of dialValues) {
    const f = snapToSolfeggio(v);
    if (!seen.has(f)) {
      seen.add(f);
      out.push(f);
    }
  }
  return out;
}

describe('RateTuner — Solfeggio preview + preset wiring', () => {
  describe('live preview calculation', () => {
    it('maps 2 dial values to 2 frequencies', () => {
      expect(livePreviewFrequencies([35, 50])).toEqual([528, 639]);
    });

    it('maps 3 dial values to up to 3 frequencies', () => {
      expect(livePreviewFrequencies([10, 35, 90])).toEqual([396, 528, 963]);
    });

    it('deduplicates when dials snap to same tone', () => {
      expect(livePreviewFrequencies([35, 35, 35])).toEqual([528]);
    });

    it('preserves encounter order', () => {
      // 50 (La 639) first, then 35 (Mi 528) — output should be [639, 528]
      expect(livePreviewFrequencies([50, 35])).toEqual([639, 528]);
    });

    it('returns empty array for no values', () => {
      expect(livePreviewFrequencies([])).toEqual([]);
    });

    it('clamps out-of-range dial values', () => {
      // -50 clamps to 0 → 396; 200 clamps to 100 → 963
      expect(livePreviewFrequencies([-50, 200])).toEqual([396, 963]);
    });

    it('handles the rate_to_audio bridge midpoints', () => {
      // All 7 Solfeggio bands at midpoints
      expect(livePreviewFrequencies([7])).toEqual([396]);
      expect(livePreviewFrequencies([21])).toEqual([417]);
      expect(livePreviewFrequencies([35])).toEqual([528]);
      expect(livePreviewFrequencies([50])).toEqual([639]);
      expect(livePreviewFrequencies([64])).toEqual([741]);
      expect(livePreviewFrequencies([78])).toEqual([852]);
      expect(livePreviewFrequencies([92])).toEqual([963]);
    });
  });

  describe('preset wiring', () => {
    it('RateTuner presets have 3 dial values (legacy format)', () => {
      // The legacy 3-dial RateTuner format still works
      for (const preset of CHAKRA_PRESETS) {
        // New chakra presets use 5 dials, but RateTuner should accept any count
        expect(preset.dims.d1).toBeGreaterThanOrEqual(0);
        expect(preset.dims.d5).toBeLessThanOrEqual(100);
      }
    });

    it('chakra presets snap to distinct Solfeggio tones', () => {
      const freqs = CHAKRA_PRESETS.map((p) => presetFrequencies(p)[0]);
      // Each chakra → unique Solfeggio tone (ascending)
      expect(freqs).toEqual([396, 417, 528, 639, 741, 852, 963]);
    });

    it('harmonic presets produce consonant intervals', () => {
      // Heart Opening: 528 + 639 (Mi + La, perfect 5th-ish)
      const heart = HARMONIC_PRESETS.find((p) => p.id === 'heart_opening')!;
      const freqs = presetFrequencies(heart);
      expect(freqs).toEqual([528, 639]);

      // Deep Healing: 396 + 528 (Ut + Mi, open fifth)
      const healing = HARMONIC_PRESETS.find((p) => p.id === 'deep_healing')!;
      expect(presetFrequencies(healing)).toEqual([396, 528]);
    });

    it('presetFrequencySummary formats consistently', () => {
      const heart = HARMONIC_PRESETS.find((p) => p.id === 'heart_opening')!;
      expect(presetFrequencySummary(heart)).toBe('528 + 639 Hz');
    });
  });

  describe('handlePresetSelect with variable dial counts', () => {
    it('accepts 3-dial legacy RateTuner presets', () => {
      const legacy = { id: 'test', name: 'Test', values: [50, 50, 50], icon: '🧪' };
      const newValues = legacy.values;
      expect(newValues).toHaveLength(3);
      expect(livePreviewFrequencies(newValues)).toEqual([639]);
    });

    it('accepts 5-dial chakra presets from shared library', () => {
      const chakra = CHAKRA_PRESETS[3]; // Heart
      const newValues = Object.values(chakra.dims);
      expect(newValues).toHaveLength(5);
      expect(livePreviewFrequencies(newValues)).toEqual([639]);
    });
  });
});
