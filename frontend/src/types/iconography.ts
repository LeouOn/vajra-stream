/**
 * Deity iconography contract — mirrors backend/app/api/v1/endpoints/iconography.py
 * and the curated data in knowledge/iconography.json (core/iconography.py).
 *
 * Every curated field may be `null`: the references do not settle it, and the
 * dataset records nothing rather than guess. The UI must say so, not hide it.
 */

export interface DeityNames {
  english: string;
  sanskrit?: string | null;
  tibetan?: string | null;
  chinese?: string | null;
}

/** One hand (or pair) and what it does. `hand` is a label such as "right", "principal pair", "left (third)". */
export interface DeityHand {
  hand: string;
  position?: string | null;
  mudra?: string | null;
  holds?: string | null;
}

export interface DeityForm {
  id: string;
  label: string;
  aliases?: string[];
  descriptor?: string | null;
  body_colour?: string | null;
  faces?: number | null;
  arms?: number | null;
  eyes?: string | null;
  posture?: string | null;
  seat?: string | null;
  hands?: DeityHand[] | null;
  other_hands?: string | null;
  features?: string | null;
  /** A key into the detail response's `ornament_sets`. */
  ornaments?: string | null;
  ornament_details?: string | null;
  halo?: string | null;
  notes?: string | null;
}

export interface DeityEntry {
  id: string;
  kind?: string | null;
  generic?: boolean;
  names: DeityNames;
  aliases?: string[];
  practice_ids?: string[];
  art_style?: string | null;
  default_form: string;
  forms: DeityForm[];
  sources?: string[];
  notes?: string | null;
  /** Set (to null) on generic entries whose members have no individual iconography. */
  individual_iconography?: string | null;
  individual_iconography_note?: string | null;
}

/** A deity's pinned thangka reference (`available` is false when the image is no longer stored). */
export interface DeityReferencePin {
  reference_id: string;
  set_at?: string | null;
  available?: boolean;
}

/** `GET /iconography` item. */
export interface DeitySummary {
  id: string;
  name: string;
  names: DeityNames;
  generic: boolean;
  default_form: string;
  forms: { id: string; label: string }[];
  /** Full citations. */
  sources: string[];
  reference: DeityReferencePin | null;
}

/** `GET /iconography/{deity}?form=`. */
export interface DeityDetail {
  deity: DeityEntry;
  form: string;
  prompt_clause: string;
  caption_facts: { label: string; value: string; provenance?: string }[];
  /** Full citations. */
  sources: string[];
  /** The pinned reference id when its image is still stored, else null. */
  reference_id: string | null;
  /** Ornament-set key -> text, for the sets this deity's forms name. */
  ornament_sets?: Record<string, string>;
  reference?: DeityReferencePin | null;
}
