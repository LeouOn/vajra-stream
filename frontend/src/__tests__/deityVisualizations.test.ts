/**
 * deityVisualizations.ts must not contradict the curated iconography in
 * knowledge/iconography.json (read here straight from disk, independently of
 * the build-time import): every iconographic field is derived from it, and
 * the presentation that remains local (hex colours, element correspondences)
 * is checked against it.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import {
  DEITY_VISUALIZATIONS,
  DHYANI_BUDDHAS,
  getDeityFromEntityText,
  getDeityVisualization,
  shortWisdom,
  type DeityVisualization,
} from '../lib/deityVisualizations';
import { handLines, normalizeName, shortGesture, UNSETTLED_HAND_TEXT, type IconographyForm } from '../lib/curatedIconography';

interface RawEntry {
  id: string;
  generic?: boolean;
  default_form: string;
  buddha_family: string | null;
  forms: IconographyForm[];
}
interface RawFamily {
  lord: string;
  direction: string;
  element: string;
  wisdom: string;
  poison: string;
  emblem: string;
}
interface RawData {
  deities: RawEntry[];
  buddha_families: { families: Record<string, RawFamily> };
}

const RAW: RawData = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '..', '..', '..', 'knowledge', 'iconography.json'), 'utf8'),
);

function rawEntry(id: string): RawEntry {
  const entry = RAW.deities.find((d) => d.id === id);
  if (!entry) throw new Error(`no ${id} in iconography.json`);
  return entry;
}

function rawForm(id: string, formId?: string): IconographyForm {
  const entry = rawEntry(id);
  const form = entry.forms.find((f) => f.id === (formId ?? entry.default_form));
  if (!form) throw new Error(`no ${id}:${formId}`);
  return form;
}

function hsl(hex: string): { h: number; s: number; l: number } {
  const n = Number.parseInt(hex.slice(1), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => v / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return { h: 0, s: 0, l };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h = (h * 60 + 360) % 360;
  return { h, s, l };
}

/** Does a UI hex colour render the curated body colour word? (Ordered: the first matching word decides.) */
function hexMatchesColour(hex: string, colour: string): boolean {
  const { h, l } = hsl(hex);
  const c = colour.toLowerCase();
  if (c.includes('yellowish white')) return l >= 0.85 && (h >= 30 && h <= 65);
  if (c.includes('white')) return l >= 0.9;
  if (c.includes('green')) return h >= 90 && h <= 170;
  if (c.includes('blue')) return h >= 200 && h <= 260;
  if (c.includes('red')) return h <= 15 || h >= 340;
  if (c.includes('yellow') || c.includes('golden')) return h >= 35 && h <= 60;
  throw new Error(`no hue rule for body colour "${colour}"`);
}

const HAND_WRITTEN_ICONOGRAPHY_KEYS = [
  'mudra',
  'rightHandAttribute',
  'leftHandAttribute',
  'bodyColorName',
  'hasMoonDisk',
  'hasSunDisk',
  'sunDiskPosition',
  'pureLand',
  'vowEssence',
];

function handText(viz: DeityVisualization): string {
  return viz.iconography.hands.map((h) => `${h.label}: ${h.text}`).join(' | ');
}

describe('deity visualizations derive iconography from knowledge/iconography.json', () => {
  const entries = Object.values(DEITY_VISUALIZATIONS);

  it('covers the nine practices, each tied to a curated deity and form', () => {
    expect(Object.keys(DEITY_VISUALIZATIONS).sort()).toEqual(
      ['88_buddhas', 'amitabha', 'avalokiteshvara', 'green_tara', 'heart_sutra', 'medicine_buddha', 'vajrasattva', 'white_tara', 'zhunti'].sort(),
    );
    for (const viz of entries) {
      const form = rawForm(viz.iconographyId, viz.iconographyForm);
      expect(viz.iconography.formId).toBe(form.id);
      expect(viz.iconography.bodyColour).toBe(rawEntry(viz.iconographyId).generic ? null : form.body_colour);
    }
  });

  it('keeps no hand-written iconographic fields', () => {
    for (const viz of entries) {
      for (const key of HAND_WRITTEN_ICONOGRAPHY_KEYS) {
        expect(Object.keys(viz), `${viz.id}.${key}`).not.toContain(key);
      }
    }
  });

  it('renders each body colour with a hex of the right hue', () => {
    for (const viz of entries) {
      const colour = rawForm(viz.iconographyId, viz.iconographyForm).body_colour;
      expect(colour, viz.id).not.toBeNull();
      expect(hexMatchesColour(viz.bodyColor, colour ?? ''), `${viz.id}: ${viz.bodyColor} vs ${colour}`).toBe(true);
    }
  });

  it('takes the Buddha family and its element from the dataset', () => {
    for (const viz of entries) {
      const family = rawEntry(viz.iconographyId).buddha_family;
      expect(viz.buddhaFamily, viz.id).toBe(family);
      if (family) expect(viz.element, viz.id).toBe(RAW.buddha_families.families[family].element);
      else expect(viz.element, viz.id).toBe(viz.appElement);
    }
    // Unsettled memberships are not asserted.
    for (const id of ['white_tara', 'medicine_buddha', 'heart_sutra', 'zhunti', '88_buddhas']) {
      expect(DEITY_VISUALIZATIONS[id].buddhaFamily, id).toBeNull();
    }
  });

  it('every hand line matches a curated hand', () => {
    for (const viz of entries) {
      const form = rawForm(viz.iconographyId, viz.iconographyForm);
      if (viz.iconography.generic) continue;
      expect(viz.iconography.hands).toEqual(handLines(form));
      for (const hand of form.hands) {
        if (hand.mudra) expect(handText(viz)).toContain(shortGesture(hand.mudra));
      }
    }
  });

  it('Green Tara: right hand varada, left hand the refuge gesture with the utpala (not abhaya)', () => {
    const text = handText(getDeityVisualization('green_tara')!);
    expect(text).toContain('Right hand: varada mudra');
    expect(text).toMatch(/Left hand: refuge-granting gesture, holds the stem of a blue utpala/);
    expect(text).not.toMatch(/abhaya/i);
  });

  it('White Tara: varada is the right hand (not both hands at the heart)', () => {
    const text = handText(getDeityVisualization('white_tara')!);
    expect(text).toContain('Right hand: varada mudra');
    expect(text).toMatch(/Left hand: refuge-granting gesture, holds the stem of a white utpala/);
    expect(getDeityVisualization('white_tara')!.iconography.figure).toBeNull();
  });

  it('Vajrasattva: vajra and bell, no invented gesture name', () => {
    const text = handText(getDeityVisualization('vajrasattva')!);
    expect(text).toBe('Right hand: holds a golden vajra | Left hand: holds a bell');
  });

  it('Prajnaparamita: the principal hands vary by lineage and are not asserted', () => {
    const text = handText(getDeityVisualization('heart_sutra')!);
    expect(text).toContain(`Principal hands: ${UNSETTLED_HAND_TEXT}`);
    expect(text).not.toMatch(/dharmac?h?akra/i);
  });

  it('88 Buddhas: generic form, no per-Buddha iconography and no seat claim', () => {
    const viz = getDeityVisualization('88_buddhas')!;
    expect(viz.iconography.generic).toBe(true);
    expect(viz.iconography.hands).toEqual([]);
    expect(viz.iconography.bodyColour).toBeNull();
    expect(viz.iconography.genericNote).toMatch(/no individually established iconography/);
  });

  it('no curated seat has a sun disc, so none is drawn', () => {
    for (const viz of entries) expect(viz.iconography.seatHasSunDisc, viz.id).toBe(false);
  });

  it('the avalokiteshvara practice shows the thousand-armed form it visualises', () => {
    const viz = getDeityVisualization('avalokiteshvara')!;
    expect(viz.iconography.formId).toBe('thousand_armed');
    expect(viz.iconography.figure).toBe('11 faces, 1000 arms');
    expect(viz.iconography.otherHands).toMatch(/eye in the palm/);
  });
});

describe('getDeityFromEntityText', () => {
  it.each([
    ['Green Tara, swift protectress', 'green_tara', 'standard'],
    ['Avalokiteshvara (Chenrezig)', 'avalokiteshvara', 'four_armed'],
    ['Thousand-armed Chenrezig', 'avalokiteshvara', 'thousand_armed'],
    ['Medicine Buddha (Bhaisajyaguru)', 'medicine_buddha', 'standard'],
    ['Zhunti (Cundi) Buddha Mother', 'zhunti', 'eighteen_armed'],
    ['Amitābha and the Pure Land', 'amitabha', 'standard'],
    ['Vajrasattva purification', 'vajrasattva', 'solitary'],
  ])('%s -> %s (%s)', (text, id, form) => {
    const viz = getDeityFromEntityText(text);
    expect(viz?.id).toBe(id);
    expect(viz?.iconography.formId).toBe(form);
  });

  it('a four-armed Chenrezig carries the mala in the upper right hand', () => {
    const text = handText(getDeityFromEntityText('Chenrezig')!);
    expect(text).toContain('Principal hands: anjali mudra, holds a wish-fulfilling jewel');
    expect(text).toContain('Upper right hand: holds a crystal mala');
    expect(text).toContain('Upper left hand: holds the stem of a white lotus');
  });

  it('the first deity named wins', () => {
    expect(getDeityFromEntityText('White Tara and Green Tara')?.id).toBe('white_tara');
  });

  it.each([
    // Previously mis-mapped: Manjushri to Prajnaparamita, Maitreya to the 88 Buddhas.
    'Manjushri',
    'Maitreya',
    // Never inferred from text (the sutra, and the generic form), as in core.iconography.
    'Prajñāpāramitā',
    'the 88 Buddhas repentance',
    'Tara',
    'a dharma talk',
    '',
    null,
    undefined,
  ])('%s -> no visualization', (text) => {
    expect(getDeityFromEntityText(text)).toBeUndefined();
  });

  it('normalizes names like core.iconography.normalize_name', () => {
    expect(normalizeName('Mikyöpa')).toBe('mikyopa');
    expect(normalizeName('Avalokiteśvara (Chenrezig)')).toBe('avalokitesvara chenrezig');
    expect(normalizeName('千手觀音')).toBe('千手觀音');
  });
});

describe('DHYANI_BUDDHAS come from the five-family records', () => {
  it('one lord per family, with the curated direction, element, wisdom, poison and emblem', () => {
    expect(DHYANI_BUDDHAS.map((b) => b.family)).toEqual(['tathagata', 'vajra', 'ratna', 'padma', 'karma']);
    for (const buddha of DHYANI_BUDDHAS) {
      const family = RAW.buddha_families.families[buddha.family];
      expect(buddha.iconographyId).toBe(family.lord);
      expect(buddha.direction).toBe(family.direction === 'centre' ? 'center' : family.direction);
      expect(buddha.element).toBe(family.element);
      expect(buddha.wisdom).toBe(family.wisdom);
      expect(buddha.poison).toBe(family.poison);
      expect(buddha.emblem).toBe(family.emblem);
      expect(rawEntry(family.lord).buddha_family).toBe(buddha.family);
    }
  });

  it('colours and gestures match each lord', () => {
    const expected: Record<string, [string, RegExp]> = {
      tathagata: ['white', /Both hands: dharmachakra mudra/],
      vajra: ['blue', /Right hand: bhumisparsha mudra · Left hand: dhyana mudra/],
      ratna: ['yellow', /Right hand: varada mudra · Left hand: dhyana mudra/],
      padma: ['red', /Both hands: dhyana mudra, holds an alms bowl/],
      karma: ['green', /Right hand: abhaya mudra · Left hand: dhyana mudra/],
    };
    for (const buddha of DHYANI_BUDDHAS) {
      const [colour, gesture] = expected[buddha.family];
      expect(buddha.bodyColour).toBe(colour);
      expect(buddha.gesture).toMatch(gesture);
      expect(hexMatchesColour(buddha.color, colour), `${buddha.family}: ${buddha.color}`).toBe(true);
    }
  });

  it('short wisdom labels', () => {
    expect(DHYANI_BUDDHAS.map((b) => b.wisdomShort)).toEqual([
      'dharmadhatu',
      'mirror-like',
      'equality',
      'discriminating',
      'all-accomplishing',
    ]);
    expect(shortWisdom('wisdom')).toBe('wisdom');
  });
});

describe('five Buddha seed syllables', () => {
  it('come from the curated registry (the common Tibetan set)', () => {
    expect(DHYANI_BUDDHAS.map((b) => b.bijaRomaji)).toEqual(['OṂ', 'HŪṂ', 'TRAṂ', 'HRĪḤ', 'ĀḤ']);
    expect(DHYANI_BUDDHAS.every((b) => b.bija.length > 0)).toBe(true);
  });
});
