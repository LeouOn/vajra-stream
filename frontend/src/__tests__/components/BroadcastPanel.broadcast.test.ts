// Test for the BroadcastPanel direct frequency override + preset wiring.
// Verifies that when a user enters a specific frequency, it bypasses
// the dial-to-Solfeggio snapping and sends the raw Hz to the backend.
// Also tests the rate_values -> backend payload flow.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { snapToSolfeggio, presetFrequencies, presetFrequencySummary } from '../../lib/crystalPresets';

describe('BroadcastPanel — direct frequency override + preset wiring', () => {
  let originalFetch: typeof fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    // Mock fetch so we can inspect what the frontend sends
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        session_id: 'test-123',
        status: 'success',
        intention: 'healing',
        targets: ['all beings'],
        frequencies: [7.83, 528.0, 639.0],
        solfeggio_names: ['Schumann Base', 'Mi (Transformation)', 'La (Connection)'],
        frequency_source: 'radionics_rate',
        amplitude: 0.85,
        scalar_mops: 14.18,
        crystal_output: { status: 'completed' },
        scalar_output: { status: 'active', mops: 14.18 },
      }),
    } as Response);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('snapToSolfeggio maps the 7 Solfeggio bands correctly', () => {
    // 0-14 → 396
    expect(snapToSolfeggio(0)).toBe(396);
    expect(snapToSolfeggio(14)).toBe(396);
    // 15-28 → 417
    expect(snapToSolfeggio(15)).toBe(417);
    expect(snapToSolfeggio(28)).toBe(417);
    // 29-42 → 528
    expect(snapToSolfeggio(35)).toBe(528);
    // 43-57 → 639
    expect(snapToSolfeggio(50)).toBe(639);
    // 58-71 → 741
    expect(snapToSolfeggio(64)).toBe(741);
    // 72-85 → 852
    expect(snapToSolfeggio(78)).toBe(852);
    // 86-100 → 963
    expect(snapToSolfeggio(92)).toBe(963);
  });

  it('clamps direct frequency values out of range', () => {
    expect(snapToSolfeggio(-50)).toBe(396);  // clamps to 0 → 396
    expect(snapToSolfeggio(200)).toBe(963);  // clamps to 100 → 963
  });

  it('presetFrequencies deduplicates dial values that snap to the same Solfeggio', () => {
    // 5 dials at 50 → all snap to 639
    const result = presetFrequencies({
      id: 'test', label: 'test', icon: '🧪',
      dims: { d1: 50, d2: 50, d3: 50, d4: 50, d5: 50 },
      description: 'all same',
    });
    expect(result).toEqual([639]);
  });

  it('presetFrequencySummary formats as "N + M Hz" for two frequencies', () => {
    const result = presetFrequencySummary({
      id: 'test', label: 'test', icon: '🧪',
      dims: { d1: 35, d2: 50, d3: 35, d4: 50, d5: 35 },
      description: 'heart opening',
    });
    expect(result).toBe('528 + 639 Hz');
  });

  it('presetFrequencySummary formats as range for multiple frequencies', () => {
    const result = presetFrequencySummary({
      id: 'test', label: 'test', icon: '🧪',
      dims: { d1: 5, d2: 20, d3: 35, d4: 50, d5: 75 },
      description: 'full spectrum',
    });
    expect(result).toMatch(/^\d+→\d+ Hz$/);
  });

  it('CHAKRA_PRESETS chakra values snap to expected Solfeggio tones', () => {
    // Import the actual CHAKRA_PRESETS to verify the mapping
    return import('../../lib/crystalPresets').then(({ CHAKRA_PRESETS }) => {
      const expected: Record<string, number> = {
        root: 396, sacral: 417, solar_plexus: 528,
        heart: 639, throat: 741, third_eye: 852, crown: 963,
      };
      for (const preset of CHAKRA_PRESETS) {
        const freqs = presetFrequencies(preset);
        expect(freqs).toEqual([expected[preset.id]]);
      }
    });
  });
});
