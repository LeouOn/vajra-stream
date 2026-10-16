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

/** A payload's `provenance` map: field name -> kind (backend core/provenance.py). */
export type ProvenanceMap = Partial<Record<string, Provenance>>;

const PROVENANCE_KINDS: readonly Provenance[] = ['record', 'computed', 'draw', 'decorative'];

/** True for one of the four provenance kinds. */
export function isProvenance(value: unknown): value is Provenance {
  return typeof value === 'string' && (PROVENANCE_KINDS as readonly string[]).includes(value);
}

/**
 * The provenance a payload's `provenance` map gives `field`.
 *
 * `fallback` covers payloads (and saved data) from before the backend labeled
 * that field; pick it for what the field is by nature, as `potencyProvenance`
 * does for potency. A label the payload carries always wins, so a placeholder
 * the backend marks decorative reads as decorative.
 */
export function fieldProvenance(labels: unknown, field: string, fallback: Provenance): Provenance {
  if (labels && typeof labels === 'object') {
    const kind = (labels as Record<string, unknown>)[field];
    if (isProvenance(kind)) return kind;
  }
  return fallback;
}

export interface PotencyLike {
  potency?: number;
  provenance?: ProvenanceMap;
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
