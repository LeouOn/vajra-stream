// frontend/src/lib/crystalPresets.ts
// Shared crystal bowl broadcast presets — used by BroadcastPanel + RateTuner.
//
// Each preset defines 5 dial values (D1-D5) that, when fed through
// core/rate_to_audio.py's Solfeggio snapping, produce a specific set of
// carrier frequencies. The Solfeggio mapping is:
//   0-14  → 396 (Ut - Liberation)
//   15-28 → 417 (Re - Change)
//   29-42 → 528 (Mi - Transformation)
//   43-57 → 639 (La - Connection)
//   58-71 → 741 (Sol - Awakening)
//   72-85 → 852 (Si - Spiritual Order)
//   86-100 → 963 (Divine Consciousness)
//
// Values are chosen so the snapped frequencies form consonant musical
// intervals (no dissonance).

import type { Dimensions } from '../components/UI/BroadcastPanel';

export interface CrystalPreset {
  id: string;
  label: string;
  icon: string;
  dims: Dimensions;
  description: string;
}

// 7 chakra presets — each maps its 3-dial value to one Solfeggio tone,
// extended to 5 dials (broadcast uses D1-D5) for the full spectrum.
export const CHAKRA_PRESETS: CrystalPreset[] = [
  {
    id: 'root',
    label: 'Root (Muladhara)',
    icon: '🔴',
    dims: { d1: 7, d2: 7, d3: 7, d4: 7, d5: 7 },
    description: 'Grounding & survival — 396 Hz',
  },
  {
    id: 'sacral',
    label: 'Sacral (Svadhisthana)',
    icon: '🟠',
    dims: { d1: 21, d2: 21, d3: 21, d4: 21, d5: 21 },
    description: 'Creativity & emotions — 417 Hz',
  },
  {
    id: 'solar_plexus',
    label: 'Solar Plexus (Manipura)',
    icon: '🟡',
    dims: { d1: 35, d2: 35, d3: 35, d4: 35, d5: 35 },
    description: 'Personal power & will — 528 Hz',
  },
  {
    id: 'heart',
    label: 'Heart (Anahata)',
    icon: '💚',
    dims: { d1: 50, d2: 50, d3: 50, d4: 50, d5: 50 },
    description: 'Love & compassion — 639 Hz',
  },
  {
    id: 'throat',
    label: 'Throat (Vishuddha)',
    icon: '🔵',
    dims: { d1: 64, d2: 64, d3: 64, d4: 64, d5: 64 },
    description: 'Communication & truth — 741 Hz',
  },
  {
    id: 'third_eye',
    label: 'Third Eye (Ajna)',
    icon: '🟣',
    dims: { d1: 78, d2: 78, d3: 78, d4: 78, d5: 78 },
    description: 'Intuition & insight — 852 Hz',
  },
  {
    id: 'crown',
    label: 'Crown (Sahasrara)',
    icon: '👑',
    dims: { d1: 92, d2: 92, d3: 92, d4: 92, d5: 92 },
    description: 'Spiritual connection — 963 Hz',
  },
];

// Harmonic combination presets — chosen so the snapped Solfeggio tones
// form consonant musical intervals.
export const HARMONIC_PRESETS: CrystalPreset[] = [
  {
    id: 'heart_opening',
    label: 'Heart Opening',
    icon: '💚',
    dims: { d1: 35, d2: 50, d3: 35, d4: 50, d5: 35 },
    description: '528 + 639 Hz — love & connection',
  },
  {
    id: 'deep_healing',
    label: 'Deep Healing',
    icon: '🩹',
    dims: { d1: 10, d2: 35, d3: 10, d4: 35, d5: 10 },
    description: '396 + 528 Hz — liberation & DNA repair',
  },
  {
    id: 'full_spectrum',
    label: 'Full Spectrum',
    icon: '🌈',
    dims: { d1: 5, d2: 20, d3: 35, d4: 50, d5: 75 },
    description: '396→852 Hz — all chakras, complete sweep',
  },
  {
    id: 'crown_activation',
    label: 'Crown Activation',
    icon: '✨',
    dims: { d1: 90, d2: 80, d3: 90, d4: 80, d5: 95 },
    description: '852 + 963 Hz — spiritual awakening',
  },
  {
    id: 'grounding',
    label: 'Grounding',
    icon: '🌳',
    dims: { d1: 5, d2: 5, d3: 10, d4: 5, d5: 10 },
    description: '396 Hz only — root anchor',
  },
  {
    id: 'intuition',
    label: 'Intuition Boost',
    icon: '🔮',
    dims: { d1: 60, d2: 60, d3: 60, d4: 65, d5: 60 },
    description: '741 Hz — awakening intuition',
  },
];

// Convenience: all presets combined
export const ALL_PRESETS: CrystalPreset[] = [...CHAKRA_PRESETS, ...HARMONIC_PRESETS];

/**
 * Snap a dial value (0-100) to the nearest Solfeggio tone.
 * Mirrors core/rate_to_audio.py:_snap_to_solfeggio.
 */
export function snapToSolfeggio(dialValue: number): number {
  const clamped = Math.max(0, Math.min(100, dialValue));
  const solfeggio = [396, 417, 528, 639, 741, 852, 963];
  const idx = Math.min(Math.floor(clamped / (100 / solfeggio.length)), solfeggio.length - 1);
  return solfeggio[idx];
}

/** Get all unique Solfeggio frequencies a preset will produce. */
export function presetFrequencies(preset: CrystalPreset): number[] {
  const seen = new Set<number>();
  const freqs: number[] = [];
  for (const v of Object.values(preset.dims)) {
    const f = snapToSolfeggio(v);
    if (!seen.has(f)) {
      seen.add(f);
      freqs.push(f);
    }
  }
  return freqs;
}

/** Human-readable frequency summary, e.g. "528 + 639 Hz". */
export function presetFrequencySummary(preset: CrystalPreset): string {
  const freqs = presetFrequencies(preset);
  if (freqs.length === 0) return '';
  if (freqs.length === 1) return `${freqs[0]} Hz`;
  if (freqs.length === 2) return `${freqs[0]} + ${freqs[1]} Hz`;
  return `${freqs[0]}→${freqs[freqs.length - 1]} Hz`;
}

/** Solfeggio tone name for a frequency. */
export function solfeggioName(hz: number): string {
  const names: Record<number, string> = {
    396: 'Ut (Liberation)',
    417: 'Re (Change)',
    528: 'Mi (Transformation)',
    639: 'La (Connection)',
    741: 'Sol (Awakening)',
    852: 'Si (Spiritual Order)',
    963: 'Divine Consciousness',
  };
  return names[hz] || `${hz.toFixed(2)} Hz`;
}
