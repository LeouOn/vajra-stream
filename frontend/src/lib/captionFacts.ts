/**
 * Caption facts — the real values an image is captioned with, never painted into it.
 *
 * Image models invent and garble numbers ("Full Moon 90%" for a 44% moon), so
 * the backend keeps numbers out of every image prompt (core/image_prompts.py)
 * and stores the computed/recorded facts beside the image as
 * `caption_facts: [{label, value, provenance}]` — in a folio's witness block,
 * a render operation's `params`, a sigil, or an Outlook illustration reply.
 */
import type { Provenance } from '../types/operations';

export interface CaptionFact {
  label: string;
  value: string;
  provenance: Provenance;
}

const PROVENANCES: readonly Provenance[] = ['record', 'computed', 'draw', 'decorative'];

function isProvenance(v: unknown): v is Provenance {
  return typeof v === 'string' && (PROVENANCES as readonly string[]).includes(v);
}

/** Read `caption_facts` from an untyped payload; malformed entries are dropped, never guessed. */
export function toCaptionFacts(value: unknown): CaptionFact[] {
  if (!Array.isArray(value)) return [];
  const out: CaptionFact[] = [];
  for (const item of value) {
    if (!item || typeof item !== 'object') continue;
    const { label, value: v, provenance } = item as Record<string, unknown>;
    if (typeof label !== 'string' || !label || !isProvenance(provenance)) continue;
    if (typeof v !== 'string' && typeof v !== 'number') continue;
    out.push({ label, value: String(v), provenance });
  }
  return out;
}
