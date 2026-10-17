/**
 * Deity visualizations for the sadhana display (`SadhanaVisualization`), the
 * Five Buddha mandala (`FiveBuddhaMandala`), the practice page and the Outlook
 * ritual summary.
 *
 * Two kinds of data meet here and are kept apart on purpose:
 *
 * - **Iconography** -- body colour, faces and arms, the gesture and held
 *   object of each hand, the seat, the Buddha family, and for the five
 *   Buddhas their direction, element, wisdom, poison and emblem -- is derived
 *   from the curated, sourced `knowledge/iconography.json` (via
 *   `curatedIconography.ts`) and is never written by hand in this file.
 * - **Presentation** -- UI hex colours, glow and lotus tints, the seed-syllable
 *   display, the animation frequency, and the app's own element/chakra
 *   correspondences for deities outside the five-family system -- is this
 *   app's choice and makes no iconographic claim.
 *
 * `__tests__/deityVisualizations.test.ts` checks that the presentation never
 * contradicts the dataset (for instance a hex colour of the wrong hue for the
 * curated body colour).
 */
import {
  BUDDHA_FAMILIES,
  BUDDHA_FAMILY_VARIANT_NOTE,
  firstNamedDeity,
  getBuddhaFamily,
  getIconographyEntry,
  getIconographyForm,
  handLines,
  mandalaDirection,
  summarizeIconography,
  type BuddhaFamily,
  type IconographySummary,
  type MandalaDirection,
} from './curatedIconography';

export type { BuddhaFamily, MandalaDirection } from './curatedIconography';
export { BUDDHA_FAMILY_VARIANT_NOTE };

/** Presentation for one practice's deity. No field here is an iconographic claim. */
interface DeityPresentation {
  /** Display name. */
  name: string;
  /** Deity id in knowledge/iconography.json. */
  iconographyId: string;
  /** Form id in knowledge/iconography.json; the deity's default form when omitted. */
  iconographyForm?: string;
  /** Seed syllable shown on the moon disc, and its romanization. */
  bija: string;
  bijaRomaji: string;
  /** UI hex rendering of the curated body colour (checked against it by the tests). */
  bodyColor: string;
  radianceColor: string;
  lotusColor: string;
  emissionColor: string;
  /**
   * The app's own element correspondence, shown only for a deity with no
   * curated Buddha family; a family member shows its family's element.
   */
  appElement: string;
  chakra: string;
  /** Drives the glow animation speed. */
  frequencyHz: number;
}

export interface DeityVisualization extends DeityPresentation {
  /** Practice id (knowledge/practices/*.json). */
  id: string;
  /** Sanskrit name from the dataset (null for the generic Buddha form). */
  sanskritName: string | null;
  /** Everything iconographic, derived from knowledge/iconography.json. */
  iconography: IconographySummary;
  /** The curated Buddha family, or null where the references do not settle one. */
  buddhaFamily: BuddhaFamily | null;
  /** The family's element for a family member, otherwise `appElement`. */
  element: string;
}

export type PracticePhase = 'idle' | 'invoking' | 'reciting' | 'dedicating' | 'completed';

const PRESENTATION: Record<string, DeityPresentation> = {
  green_tara: {
    name: 'Green Tārā',
    iconographyId: 'green_tara',
    bija: 'तां',
    bijaRomaji: 'TĀṂ',
    bodyColor: '#22c55e',
    radianceColor: '#4ade80',
    lotusColor: '#06b6d4',
    emissionColor: '#4ade80',
    appElement: 'air',
    chakra: 'heart',
    frequencyHz: 528,
  },
  white_tara: {
    name: 'White Tārā',
    iconographyId: 'white_tara',
    bija: 'तां',
    bijaRomaji: 'TĀṂ',
    bodyColor: '#f8fafc',
    radianceColor: '#e0f2fe',
    lotusColor: '#f1f5f9',
    emissionColor: '#e0f2fe',
    appElement: 'space',
    chakra: 'crown',
    frequencyHz: 396,
  },
  medicine_buddha: {
    name: 'Medicine Buddha',
    iconographyId: 'medicine_buddha',
    bija: 'भै',
    bijaRomaji: 'BHAI',
    bodyColor: '#1e40af',
    radianceColor: '#3b82f6',
    lotusColor: '#2563eb',
    emissionColor: '#60a5fa',
    appElement: 'water',
    chakra: 'third_eye',
    frequencyHz: 285,
  },
  vajrasattva: {
    name: 'Vajrasattva',
    iconographyId: 'vajrasattva',
    bija: 'हूँ',
    bijaRomaji: 'HŪṂ',
    bodyColor: '#f8fafc',
    radianceColor: '#e2e8f0',
    lotusColor: '#cbd5e1',
    emissionColor: '#f1f5f9',
    appElement: 'space',
    chakra: 'crown',
    frequencyHz: 396,
  },
  amitabha: {
    name: 'Amitābha',
    iconographyId: 'amitabha',
    bija: 'ह्रीः',
    bijaRomaji: 'HRĪḤ',
    bodyColor: '#dc143c',
    radianceColor: '#ef4444',
    lotusColor: '#f87171',
    emissionColor: '#fca5a5',
    appElement: 'fire',
    chakra: 'throat',
    frequencyHz: 174,
  },
  avalokiteshvara: {
    name: 'Avalokiteśvara',
    iconographyId: 'avalokiteshvara',
    // The practice visualises the thousand-armed form (see its entry notes in the dataset).
    iconographyForm: 'thousand_armed',
    bija: 'ह्रीः',
    bijaRomaji: 'HRĪḤ',
    bodyColor: '#fafafa',
    radianceColor: '#86efac',
    lotusColor: '#ffffff',
    emissionColor: '#bbf7d0',
    appElement: 'air',
    chakra: 'heart',
    frequencyHz: 639,
  },
  heart_sutra: {
    name: 'Prajñāpāramitā',
    iconographyId: 'prajnaparamita',
    bija: 'प्र',
    bijaRomaji: 'PRA',
    bodyColor: '#fbbf24',
    radianceColor: '#fcd34d',
    lotusColor: '#fde68a',
    emissionColor: '#fef3c7',
    appElement: 'space',
    chakra: 'third_eye',
    frequencyHz: 852,
  },
  zhunti: {
    name: 'Cuṇḍī Buddha Mother',
    iconographyId: 'cundi',
    bija: '准',
    bijaRomaji: 'CUNDĪ',
    bodyColor: '#fef3c7',
    radianceColor: '#fde68a',
    lotusColor: '#fef9c3',
    emissionColor: '#fef08a',
    appElement: 'fire',
    chakra: 'solar_plexus',
    frequencyHz: 417,
  },
  '88_buddhas': {
    name: '88 Buddhas',
    iconographyId: 'buddha_generic',
    bija: 'अ',
    bijaRomaji: 'A',
    bodyColor: '#fbbf24',
    radianceColor: '#fcd34d',
    lotusColor: '#fef3c7',
    emissionColor: '#fde68a',
    appElement: 'earth',
    chakra: 'root',
    frequencyHz: 396,
  },
};

function buildVisualization(id: string, presentation: DeityPresentation, formId?: string): DeityVisualization {
  const iconography = summarizeIconography(presentation.iconographyId, formId ?? presentation.iconographyForm);
  if (!iconography) {
    throw new Error(`deityVisualizations: ${presentation.iconographyId} is not in knowledge/iconography.json`);
  }
  const entry = getIconographyEntry(presentation.iconographyId);
  const family = iconography.buddhaFamily;
  return {
    ...presentation,
    iconographyForm: iconography.formId,
    id,
    sanskritName: entry?.names.sanskrit ?? null,
    iconography,
    buddhaFamily: family,
    element: family ? getBuddhaFamily(family).element : presentation.appElement,
  };
}

export const DEITY_VISUALIZATIONS: Record<string, DeityVisualization> = Object.fromEntries(
  Object.entries(PRESENTATION).map(([id, presentation]) => [id, buildVisualization(id, presentation)]),
);

// -- the five Buddhas ---------------------------------------------------------------

/**
 * Presentation for the mandala: UI colour and animation frequency. The seed
 * syllables are curated (knowledge/iconography.json buddha_families), not
 * presentation: they come from each family's record.
 */
const DHYANI_PRESENTATION: Record<BuddhaFamily, { color: string; frequencyHz: number }> = {
  tathagata: { color: '#f8fafc', frequencyHz: 136.1 },
  vajra: { color: '#1e40af', frequencyHz: 210.42 },
  ratna: { color: '#fbbf24', frequencyHz: 183.58 },
  padma: { color: '#dc143c', frequencyHz: 126.22 },
  karma: { color: '#22c55e', frequencyHz: 289.0 },
};

export interface DhyaniBuddha {
  family: BuddhaFamily;
  /** Deity id of the family's lord in knowledge/iconography.json. */
  iconographyId: string;
  name: string;
  /** Curated body colour ("white", "blue", ...). */
  bodyColour: string | null;
  /** Curated hands, e.g. "Right hand: bhumisparsha mudra · Left hand: dhyana mudra". */
  gesture: string;
  emblem: string;
  direction: MandalaDirection;
  element: string;
  wisdom: string;
  /** The wisdom without the word "wisdom", for tight labels ("mirror-like", "equality"). */
  wisdomShort: string;
  poison: string;
  /** "Anger → mirror-like wisdom". */
  defilementPurified: string;
  color: string;
  bija: string;
  bijaRomaji: string;
  frequencyHz: number;
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function shortWisdom(wisdom: string): string {
  const words = wisdom
    .replace(/\([^)]*\)/g, ' ')
    .split(/\s+/)
    .filter((w) => w && !['wisdom', 'of', 'the'].includes(w.toLowerCase()));
  return words.join(' ') || wisdom;
}

function buildDhyani(family: BuddhaFamily): DhyaniBuddha {
  const record = getBuddhaFamily(family);
  const entry = getIconographyEntry(record.lord);
  const form = entry ? getIconographyForm(entry) : undefined;
  const direction = mandalaDirection(record.direction);
  if (!entry || !form || !direction) {
    throw new Error(`deityVisualizations: incomplete five-family record for ${family}`);
  }
  return {
    family,
    iconographyId: entry.id,
    name: entry.names.sanskrit ?? entry.names.english,
    bodyColour: form.body_colour,
    gesture: handLines(form)
      .map((line) => `${line.label}: ${line.text}`)
      .join(' · '),
    emblem: record.emblem,
    direction,
    element: record.element,
    wisdom: record.wisdom,
    wisdomShort: shortWisdom(record.wisdom),
    poison: record.poison,
    defilementPurified: `${capitalize(record.poison)} → ${record.wisdom}`,
    bija: record.seed_syllable.devanagari,
    bijaRomaji: record.seed_syllable.iast,
    ...DHYANI_PRESENTATION[family],
  };
}

export const DHYANI_BUDDHAS: DhyaniBuddha[] = BUDDHA_FAMILIES.map(buildDhyani);

export function getDhyaniBuddhaByFamily(family: BuddhaFamily): DhyaniBuddha | undefined {
  return DHYANI_BUDDHAS.find((b) => b.family === family);
}

export function getDhyaniBuddhaByDirection(direction: MandalaDirection): DhyaniBuddha | undefined {
  return DHYANI_BUDDHAS.find((b) => b.direction === direction);
}

// -- lookup -------------------------------------------------------------------------

export function getDeityVisualization(id: string): DeityVisualization | undefined {
  return DEITY_VISUALIZATIONS[id];
}

/**
 * The visualization for the first curated deity a free text names (e.g. an
 * Outlook narrative's `entities_used`), using the dataset's aliases. The
 * iconography follows the form the text names: "Chenrezig" is the four-armed
 * form even though the avalokiteshvara practice visualises the thousand-armed
 * one. Undefined when no curated deity with a visualization is named.
 */
export function getDeityFromEntityText(entityText: string | undefined | null): DeityVisualization | undefined {
  const named = firstNamedDeity(entityText);
  if (!named) return undefined;
  const match = Object.entries(PRESENTATION).find(([, p]) => p.iconographyId === named.deityId);
  if (!match) return undefined;
  const [id, presentation] = match;
  return buildVisualization(id, presentation, named.formId);
}
