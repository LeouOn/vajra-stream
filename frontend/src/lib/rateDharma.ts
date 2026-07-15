/**
 * Rate → Dharma Resonance Bridge
 *
 * Maps a set of radionics dial values (0-100) to their Solfeggio carrier
 * frequencies and then to the dharma knowledge stored in
 * `knowledge/frequencies.json` (the `dharma` section) and
 * `knowledge/mantras.json` (the `buddhist` section).
 *
 * This is the bridge that lets the RateTuner show not just "528 Hz" but
 * "528 Hz · Green Tara · Om Tare Tuttare Ture Svaha · heart chakra".
 *
 * Solfeggio snapping reuses `snapToSolfeggio` from `crystalPresets.ts` so
 * the UI, the audio bridge, and the dharma layer all agree on the same
 * carrier tones.
 */
import frequenciesData from '../../../knowledge/frequencies.json';
import mantrasData from '../../../knowledge/mantras.json';
import { snapToSolfeggio, solfeggioName } from './crystalPresets';

/* eslint-disable @typescript-eslint/no-explicit-any */
// The two JSON knowledge files are untyped by design; we shape them at
// the boundary via the `DharmaEntry` and `MantraEntry` interfaces below.
const DHARMA_BY_HZ: Record<string, DharmaEntry> = ((frequenciesData as any).dharma ?? {}) as Record<string, DharmaEntry>;
const MANTRAS_BY_PRACTICE: Record<string, MantraEntry> = ((mantrasData as any).buddhist ?? {}) as Record<string, MantraEntry>;
/* eslint-enable @typescript-eslint/no-explicit-any */

export interface DharmaEntry {
  name: string;
  purpose: string;
  deity: string;
  chakra: string;
  color: string;
  practice: string;
}

export interface MantraEntry {
  name: string;
  sanskrit?: string;
  tradition?: string;
  meaning?: string;
  purpose?: string;
}

export const SOLFEGGIO_NAMES: Record<number, string> = {
  396: 'Ut (Liberation)',
  417: 'Re (Change)',
  528: 'Mi (Transformation)',
  639: 'La (Connection)',
  741: 'Sol (Awakening)',
  852: 'Si (Spiritual Order)',
  963: 'Divine Consciousness',
};

/**
 * RGB tuples for the seven dharma colors. These power the inline-style
 * tint on the Resonance Panel so the panel itself takes on the deity's
 * hue.
 */
export const DHARMA_COLOR_RGB: Record<string, string> = {
  red: '239, 68, 68',
  orange: '249, 115, 22',
  yellow: '234, 179, 8',
  green: '34, 197, 94',
  blue: '59, 130, 246',
  indigo: '99, 102, 241',
  violet: '167, 139, 250',
  purple: '168, 85, 247',
  white: '243, 244, 246',
  gold: '234, 179, 8',
};

/** Snap an array of dial values (0-100) to their Solfeggio carrier tones. */
export function rateToSolfeggio(values: number[]): number[] {
  return values.map((v) => snapToSolfeggio(v));
}

export interface RateDharma {
  /** Solfeggio carriers in dial order (one per dial). */
  frequencies: number[];
  /** Highest carrier frequency (Hz) — drives the dharma lookup. */
  primaryHz: number;
  /** Solfeggio display name for the primary Hz. */
  solfeggioName: string;
  /** Dharma deity associated with the primary Hz (if mapped). */
  deity?: string;
  /** Chakra associated with the primary Hz (if mapped). */
  chakra?: string;
  /** Color name (e.g. 'green') associated with the primary Hz. */
  color?: string;
  /** `rgba(R,G,B,α)` string ready for inline-style tinting. */
  colorRgb: string;
  /** Practice key (e.g. 'green_tara') for further lookups. */
  practice?: string;
  /** Mantra Sanskrit/Devanagari for the practice (if available). */
  mantra?: string;
  /** Short human purpose/meaning string. */
  purpose?: string;
}

/**
 * Look up the dharma resonance for a set of dial values.
 *
 * The "primary" Hz is the highest carrier in the dial set — the dominant
 * tone that determines which deity/chakra/mantra the panel surfaces.
 * Lower carriers are still returned in `frequencies` so the caller can
 * render harmonic context.
 */
export function rateToDharma(values: number[]): RateDharma {
  const frequencies = rateToSolfeggio(values);
  const primaryHz = frequencies.length > 0 ? Math.max(...frequencies) : 396;

  const dharma = DHARMA_BY_HZ[String(primaryHz)];
  const mantra = dharma?.practice ? MANTRAS_BY_PRACTICE[dharma.practice] : undefined;

  const colorName = dharma?.color;
  const colorRgb = (colorName && DHARMA_COLOR_RGB[colorName]) || '168, 85, 247';

  return {
    frequencies,
    primaryHz,
    solfeggioName: SOLFEGGIO_NAMES[primaryHz] ?? solfeggioName(primaryHz),
    deity: dharma?.deity,
    chakra: dharma?.chakra,
    color: colorName,
    colorRgb,
    practice: dharma?.practice,
    mantra: mantra?.sanskrit ?? mantra?.name,
    purpose: dharma?.purpose,
  };
}