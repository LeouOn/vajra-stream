/**
 * Provenance labels — "the honest instrument" (docs/DEVELOPMENT_ROADMAP.md).
 *
 * Every displayed value is one of: a persisted record, a value computed from
 * real inputs, a draw (random, used as a divinatory method), or decoration.
 * A draw is legitimate, but it must read as drawn and never as a measurement.
 */
import type { Provenance } from '../types/operations';

export const PROVENANCE_LABELS: Record<Provenance, string> = {
  record: 'record',
  computed: 'computed',
  draw: 'drawn',
  decorative: 'decorative',
};

export interface PotencyLike {
  potency?: number;
  provenance?: Partial<Record<string, Provenance>>;
}

/**
 * Provenance of a rate's potency. The radionics engine only ever sets a
 * non-zero potency by drawing it, so a legacy payload without a provenance
 * map is treated as a draw rather than shown as a measurement.
 */
export function potencyProvenance(rate: PotencyLike): Provenance {
  return rate.provenance?.potency ?? 'draw';
}

/** A drawn potency in 0–1, shown plainly (two decimals, no percent sign). */
export function formatPotency(potency: number): string {
  return potency.toFixed(2);
}
