/**
 * Typed, read-only access to the curated deity iconography in
 * `knowledge/iconography.json` (the same file `core/iconography.py` reads).
 *
 * That file is the single source of truth for what a deity looks like: body
 * colour, faces and arms, posture and seat, the gesture and held object of
 * each hand, and the five Buddha families. A field the references do not
 * settle is `null` there, and the helpers below leave it out (or say it
 * varies) rather than fill it in. Nothing in the frontend should restate
 * those attributes by hand: derive them from here.
 *
 * The JSON is imported at build time, as `rateDharma.ts` does for
 * `knowledge/frequencies.json`.
 */
import iconographyJson from '../../../knowledge/iconography.json';

export type BuddhaFamily = 'tathagata' | 'vajra' | 'ratna' | 'padma' | 'karma';
export type MandalaDirection = 'center' | 'east' | 'south' | 'west' | 'north';

export const BUDDHA_FAMILIES: readonly BuddhaFamily[] = ['tathagata', 'vajra', 'ratna', 'padma', 'karma'];

export interface IconographyHand {
  hand: string;
  position: string | null;
  mudra: string | null;
  holds: string | null;
}

export interface IconographyForm {
  id: string;
  label: string;
  aliases: string[];
  body_colour: string | null;
  faces: number | null;
  arms: number | null;
  posture: string | null;
  seat: string | null;
  hands: IconographyHand[];
  other_hands: string | null;
  notes: string | null;
}

export interface IconographyEntry {
  id: string;
  generic?: boolean;
  individual_iconography_note?: string;
  names: { english: string; sanskrit: string | null; tibetan: string | null; chinese: string | null };
  aliases: string[];
  practice_ids: string[];
  default_form: string;
  forms: IconographyForm[];
  sources: string[];
  buddha_family: string | null;
}

export interface BuddhaFamilyRecord {
  name: string;
  lord: string;
  direction: string;
  element: string;
  wisdom: string;
  poison: string;
  emblem: string;
  /** The family seed syllable (common Tibetan set; variants in the registry's variant_note). */
  seed_syllable: { iast: string; devanagari: string };
}

interface IconographyData {
  sources: Record<string, { citation: string; short: string }>;
  buddha_families: {
    variant_note: string;
    sources: string[];
    families: Record<BuddhaFamily, BuddhaFamilyRecord>;
  };
  deities: IconographyEntry[];
}

const DATA: IconographyData = iconographyJson;

export const BUDDHA_FAMILY_VARIANT_NOTE: string = DATA.buddha_families.variant_note;

export function isBuddhaFamily(value: unknown): value is BuddhaFamily {
  return typeof value === 'string' && (BUDDHA_FAMILIES as readonly string[]).includes(value);
}

export function iconographyEntries(): readonly IconographyEntry[] {
  return DATA.deities;
}

export function getIconographyEntry(id: string): IconographyEntry | undefined {
  return DATA.deities.find((entry) => entry.id === id);
}

export function getIconographyForm(entry: IconographyEntry, formId?: string): IconographyForm | undefined {
  const wanted = formId ?? entry.default_form;
  return entry.forms.find((form) => form.id === wanted);
}

export function getBuddhaFamily(family: BuddhaFamily): BuddhaFamilyRecord {
  return DATA.buddha_families.families[family];
}

/** Short citations ("Beer, Encyclopedia of Tibetan Symbols and Motifs (1999)") for an entry's sources. */
export function sourceShortNames(sourceIds: readonly string[]): string[] {
  return sourceIds.map((id) => DATA.sources[id]?.short).filter((s): s is string => Boolean(s));
}

export function buddhaFamilySources(): string[] {
  return sourceShortNames(DATA.buddha_families.sources);
}

const MANDALA_DIRECTIONS: Record<string, MandalaDirection> = {
  centre: 'center',
  east: 'east',
  south: 'south',
  west: 'west',
  north: 'north',
};

/** The dataset's direction words mapped onto the mandala layout ("centre" -> 'center'), or undefined. */
export function mandalaDirection(direction: string): MandalaDirection | undefined {
  return MANDALA_DIRECTIONS[direction];
}

// -- display summaries ------------------------------------------------------------

/** "the gesture of joined palms (anjali mudra)" -> "anjali mudra"; "the teaching gesture" -> "teaching gesture". */
export function shortGesture(mudra: string): string {
  const named = /\(([^)]*mudra)\)/i.exec(mudra);
  if (named) return named[1];
  return stripArticle(mudra.split(',')[0]);
}

function stripArticle(text: string): string {
  return text.trim().replace(/^(the|a|an)\s+/i, '');
}

const SINGLE_HAND_LABELS: Record<string, string> = {
  right: 'Right hand',
  left: 'Left hand',
  both: 'Both hands',
  'principal pair': 'Principal hands',
  'upper right': 'Upper right hand',
  'upper left': 'Upper left hand',
};

/** Shown for a hand the dataset lists but leaves entirely null (e.g. Prajnaparamita's principal pair). */
export const UNSETTLED_HAND_TEXT = 'varies by lineage';

export interface HandLine {
  label: string;
  text: string;
}

function handText(hand: IconographyHand): string {
  const bits: string[] = [];
  if (hand.mudra) bits.push(shortGesture(hand.mudra));
  if (hand.holds) bits.push(`holds ${hand.holds}`);
  return bits.length ? bits.join(', ') : UNSETTLED_HAND_TEXT;
}

/**
 * One line per hand, mirroring `core.iconography._hands_clause`: hands with a
 * unique label are listed one by one, repeated or ordinal labels ("right
 * (second)") are grouped by side.
 */
export function handLines(form: IconographyForm): HandLine[] {
  const labels = form.hands.map((h) => h.hand);
  const lines: HandLine[] = [];
  const grouped: IconographyHand[] = [];
  for (const hand of form.hands) {
    const single = SINGLE_HAND_LABELS[hand.hand];
    if (single && labels.filter((l) => l === hand.hand).length === 1) {
      lines.push({ label: single, text: handText(hand) });
    } else {
      grouped.push(hand);
    }
  }
  for (const side of ['right', 'left'] as const) {
    const sideHands = grouped.filter((h) => h.hand.startsWith(side));
    const bits = sideHands.flatMap((h) => [
      ...(h.mudra ? [shortGesture(h.mudra)] : []),
      ...(h.holds ? [h.holds] : []),
    ]);
    if (bits.length) lines.push({ label: `Other ${side} hands`, text: bits.join(', ') });
  }
  return lines;
}

export interface IconographySummary {
  deityId: string;
  formId: string;
  label: string;
  /** True for the generic Buddha form (e.g. the 88 Buddhas): no individual iconography exists. */
  generic: boolean;
  genericNote: string | null;
  bodyColour: string | null;
  /** "eleven faces, a thousand arms"-style counts, only when not the ordinary one face and two arms. */
  figure: string | null;
  hands: HandLine[];
  otherHands: string | null;
  /** The seat includes a sun disc (none of the curated forms do today). */
  seatHasSunDisc: boolean;
  buddhaFamily: BuddhaFamily | null;
  sources: string[];
}

function figureText(form: IconographyForm): string | null {
  const parts: string[] = [];
  if (form.faces !== null && form.faces !== 1) parts.push(`${form.faces} faces`);
  if (form.arms !== null && form.arms !== 2) parts.push(`${form.arms} arms`);
  return parts.length ? parts.join(', ') : null;
}

export function summarizeIconography(deityId: string, formId?: string): IconographySummary | undefined {
  const entry = getIconographyEntry(deityId);
  if (!entry) return undefined;
  const form = getIconographyForm(entry, formId);
  if (!form) return undefined;
  const generic = Boolean(entry.generic);
  return {
    deityId: entry.id,
    formId: form.id,
    label: form.label,
    generic,
    genericNote: generic
      ? 'Generic Buddha form: these Buddhas have no individually established iconography.'
      : null,
    bodyColour: generic ? null : form.body_colour,
    figure: generic ? null : figureText(form),
    hands: generic ? [] : handLines(form),
    otherHands: generic ? null : form.other_hands,
    seatHasSunDisc: /\bsun\b/i.test(form.seat ?? ''),
    buddhaFamily: isBuddhaFamily(entry.buddha_family) ? entry.buddha_family : null,
    sources: sourceShortNames(entry.sources),
  };
}

// -- free-text matching -------------------------------------------------------------

/** Lowercase, diacritics folded, punctuation to single spaces (CJK kept): `core.iconography.normalize_name`. */
export function normalizeName(text: string): string {
  const folded = text.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();
  return folded.replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

// As in core.iconography: never inferred from free text (the generic Buddha form,
// and Prajnaparamita, whose name usually means the sutra).
const TEXT_MATCH_EXCLUDED = new Set(['buddha_generic', 'prajnaparamita']);

/**
 * The curated deity a free text names first (by alias, earliest mention), or
 * undefined. Short ASCII aliases (< 4 letters) are ignored, as in
 * `core.iconography.named_deity_in_text`.
 */
export function firstNamedDeity(text: string | null | undefined): { deityId: string; formId: string } | undefined {
  if (!text) return undefined;
  const haystack = ` ${normalizeName(text)} `;
  let best: { at: number; deityId: string; formId: string } | undefined;
  for (const entry of DATA.deities) {
    if (TEXT_MATCH_EXCLUDED.has(entry.id)) continue;
    const candidates: Array<[string, string]> = [
      ...[entry.names.english, entry.names.sanskrit ?? '', ...entry.aliases].map(
        (a): [string, string] => [a, entry.default_form],
      ),
      ...entry.forms.flatMap((form) => form.aliases.map((a): [string, string] => [a, form.id])),
    ];
    for (const [alias, formId] of candidates) {
      const key = normalizeName(alias);
      if (!key) continue;
      const ascii = /^[\x20-\x7e]*$/.test(key);
      if (ascii && key.length < 4) continue;
      const at = haystack.indexOf(ascii ? ` ${key} ` : key);
      if (at < 0) continue;
      // Earliest mention wins; at the same position a named form beats the default form.
      if (!best || at < best.at || (at === best.at && formId !== entry.default_form)) {
        best = { at, deityId: entry.id, formId };
      }
    }
  }
  return best && { deityId: best.deityId, formId: best.formId };
}
