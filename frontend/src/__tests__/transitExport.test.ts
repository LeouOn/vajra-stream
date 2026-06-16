import { describe, it, expect } from 'vitest';
import { formatTransitExportMarkdown, formatTransitExportJSON } from '../lib/transitExport';

// The formatter is now glyph-free (re-exported from astrologyExport.js).
// These glyphs must never appear in LLM-optimized output.
const FORBIDDEN_GLYPHS = [
  '\u2609', '\u263D', '\u263F', '\u2640', '\u2642', '\u2643', '\u2644',
  '\u2645', '\u2646', '\u2647', '\u260A', '\u260B', // planet glyphs
  '\u2648', '\u2649', '\u264A', '\u264B', '\u264C', '\u264D',
  '\u264E', '\u264F', '\u2650', '\u2651', '\u2652', '\u2653', // zodiac glyphs
  '\u25B3', '\u25A1', '\u260C', '\u26B9', '\u260D', // aspect glyphs
];

const mockData = {
  name: 'Test Chart',
  natal_houses: {
    sun: { sign: 'Aries', degree: 10.5, house_placidus: 1, house_whole_sign: 1 },
    moon: { sign: 'Cancer', degree: 120.3, house_placidus: 4, house_whole_sign: 4 },
  },
  transit_houses: {
    sun: { sign: 'Gemini', degree: 75.0, house_placidus: 3, house_whole_sign: 3 },
    mars: { sign: 'Leo', degree: 140.0, house_placidus: 5, house_whole_sign: 5 },
  },
  top_harmonious: [
    { transit_planet: 'sun', natal_planet: 'moon', aspect: 'Trine', exactness: 0.9, orb: 1.2 },
    { transit_planet: 'venus', natal_planet: 'jupiter', aspect: 'Sextile', exactness: 0.8, orb: 2.0 },
  ],
  top_challenging: [
    { transit_planet: 'mars', natal_planet: 'saturn', aspect: 'Square', exactness: 0.7, orb: 3.5 },
  ],
  gochara: {
    jupiter: { transit_rashi: 'Leo (Simha)', transit_degree: 5.0, gochara_house: 5, formatted: 'House 5 from Moon (Simha)' },
    saturn: { transit_rashi: 'Capricorn (Makara)', transit_degree: 10.0, gochara_house: 10, formatted: 'House 10 from Moon (Makara)' },
  },
  bazi_clashes: {
    interactions: [
      { pillar: 'Day', type: 'Clash', description: 'Fire clashes with Metal' },
    ],
  },
};

describe('formatTransitExportMarkdown (glyph-free LLM output)', () => {
  it('renders all six sections under the new glyph-free structure', () => {
    const result = formatTransitExportMarkdown(mockData);
    expect(result).toContain('# Transit Report: Test Chart');
    expect(result).toContain('## Natal Placements');
    expect(result).toContain('## Transit Placements');
    expect(result).toContain('## Harmonious Transits');
    expect(result).toContain('## Challenging Transits');
    expect(result).toContain('## BaZi');
    expect(result).toContain('## Gochara (from Natal Moon)');
    const headerCount = (result.match(/^#{1,2} /gm) || []).length;
    expect(headerCount).toBeGreaterThanOrEqual(6);
  });

  it('is completely glyph-free', () => {
    const result = formatTransitExportMarkdown(mockData);
    for (const g of FORBIDDEN_GLYPHS) {
      expect(result).not.toContain(g);
    }
  });

  it('renders transit aspects with plain-English aspect names and labeled orbs', () => {
    const result = formatTransitExportMarkdown(mockData);
    // Tightest-first ordering: Sun trine Moon (1.20) before Venus sextile Jupiter (2.00)
    expect(result).toContain('Transit Sun trine Natal Moon');
    expect(result).toContain('90% exact');
    expect(result).toContain('1.20\u00B0 orb');
    expect(result).toContain('Transit Mars square Natal Saturn');
  });

  it('with empty data does not crash', () => {
    const empty = {
      name: 'Empty',
      natal_houses: {},
      transit_houses: {},
      top_harmonious: [],
      top_challenging: [],
      gochara: {},
      bazi_clashes: { interactions: [] },
    };
    const result = formatTransitExportMarkdown(empty);
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain('Empty');
  });
});

describe('formatTransitExportJSON', () => {
  it('with valid data produces parseable JSON', () => {
    const result = formatTransitExportJSON(mockData);
    const parsed = JSON.parse(result);
    expect(parsed).toHaveProperty('name');
    expect(parsed).toHaveProperty('natal_houses');
    expect(parsed).toHaveProperty('transit_houses');
    expect(parsed).toHaveProperty('top_harmonious');
    expect(parsed).toHaveProperty('top_challenging');
    expect(parsed).toHaveProperty('gochara');
    expect(parsed).toHaveProperty('bazi_clashes');
  });

  it('with null input handles gracefully', () => {
    expect(() => formatTransitExportJSON(null)).not.toThrow();
    expect(() => formatTransitExportJSON(undefined)).not.toThrow();
    const result = formatTransitExportJSON(null);
    expect(typeof result).toBe('string');
  });
});
