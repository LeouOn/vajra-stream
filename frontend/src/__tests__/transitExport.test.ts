import { describe, it, expect } from 'vitest';
import { formatTransitExportMarkdown, formatTransitExportJSON } from '../lib/transitExport';

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
    jupiter: { gochara_house: 5, formatted: 'House 5 (Leo)' },
    saturn: { gochara_house: 10, formatted: 'House 10 (Capricorn)' },
  },
  bazi_clashes: {
    interactions: [
      { pillar: 'Day', type: 'Clash', description: 'Fire clashes with Metal' },
    ],
  },
};

describe('formatTransitExportMarkdown', () => {
  it('with valid data produces 7 sections', () => {
    const result = formatTransitExportMarkdown(mockData);
    expect(result).toContain('# Transit Report: Test Chart');
    expect(result).toContain('## Natal Planetary Placements');
    expect(result).toContain('## Current Transit Placements');
    expect(result).toContain('## Top 10 Harmonious Transits');
    expect(result).toContain('## Top 10 Challenging Transits');
    expect(result).toContain('## BaZi Transit Interactions');
    expect(result).toContain('## Vedic Gochara (from Natal Moon)');
    const headerCount = (result.match(/^#{1,2} /gm) || []).length;
    expect(headerCount).toBeGreaterThanOrEqual(6);
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

  it('includes planet glyphs', () => {
    const result = formatTransitExportMarkdown(mockData);
    expect(result).toContain('\u2609'); // sun ☉
    expect(result).toContain('\u263D'); // moon ☽
    expect(result).toContain('\u25B3'); // trine △
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
