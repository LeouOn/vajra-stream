/**
 * W2-A data tests: the three published sky data files + README-sky.md.
 *
 * Expected numbers come from the wave-0 dataset record (row W0-2) and the
 * wave-2 contract table: 8,404 stars, 338 names, 88 constellations /
 * 150 polylines / 893 vertices all resolved (Serpens Caput restored in
 * W2-A2); zeta Piscium HR 361 V 5.24 and theta Cancri HR 3357 V 5.35
 * (the faint lunar-mansion stars that motivated the V <= 6.5 limit).
 */

import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { decodeStars, type ConstellationLines, type Star } from '../lib/sky';

const read = (name: string) => readFileSync(new URL(`../data/${name}`, import.meta.url));
const starsBytes = read('stars-v65.json');
const namesBytes = read('star-names.json');
const linesBytes = read('constellation-lines.json');
const readme = readFileSync(new URL('../data/README-sky.md', import.meta.url), 'utf8');

const stars: Star[] = decodeStars(JSON.parse(starsBytes.toString('utf8')));
const names = JSON.parse(namesBytes.toString('utf8')) as { name: string; hr: number; vmag: number }[];
const lines = JSON.parse(linesBytes.toString('utf8')) as ConstellationLines;

const sha = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');

describe('published data files', () => {
  it('sizes and sha256 pins match the contract table', () => {
    expect(starsBytes.byteLength).toBe(297738);
    expect(sha(starsBytes)).toBe('fa4d28d5cde0ba294a6af804e01d36d964ea4618e3de2a0e542038bf6b0af68f');
    expect(namesBytes.byteLength).toBe(13615);
    expect(sha(namesBytes)).toBe('1edca3ae2be16c2ed4694495236dcb132d2161d9d225c31436842a3e0c25ff9e');
    expect(linesBytes.byteLength).toBe(5473);
    expect(sha(linesBytes)).toBe('9f34bb45cc3c053f34618a10d150eecee43796c185a7cc17876eaf4721fc14e3');
  });

  it('is 8,404 stars with unique HR ids and valid ranges', () => {
    expect(stars).toHaveLength(8404);
    const hrs = new Set(stars.map((s) => s.hr));
    expect(hrs.size).toBe(8404);
    for (const s of stars) {
      expect(s.ra).toBeGreaterThanOrEqual(0);
      expect(s.ra).toBeLessThan(360);
      expect(s.dec).toBeGreaterThanOrEqual(-90);
      expect(s.dec).toBeLessThanOrEqual(90);
      expect(s.v).toBeLessThanOrEqual(6.5);
      // The catalogue legitimately contains extreme red stars (carbon
      // stars, B-V up to ~3.9, e.g. HR 423); bound at 4, not 3.
      expect(s.bv === null || (s.bv >= -1 && s.bv <= 4)).toBe(true);
    }
  });

  it('contains the faint mansion stars zeta Piscium (HR 361, V 5.24) and theta Cancri (HR 3357, V 5.35)', () => {
    const zeta = stars.find((s) => s.hr === 361);
    expect(zeta).toBeDefined();
    expect(zeta!.v).toBe(5.24);
    const theta = stars.find((s) => s.hr === 3357);
    expect(theta).toBeDefined();
    expect(theta!.v).toBe(5.35);
  });

  it('names file holds 338 IAU entries that all resolve to stars', () => {
    expect(names).toHaveLength(338);
    const byHr = new Set(stars.map((s) => s.hr));
    for (const n of names) expect(byHr.has(n.hr)).toBe(true);
  });

  it('constellation lines: 88 constellations, 150 polylines, 893 vertices, every vertex resolves', () => {
    const featureCount = Object.keys(lines.constellations).length;
    // 89 d3-celestial features for 88 constellations: "Ser" appears twice
    // (Caput 9 vertices, Cauda 6) and row W2-A2 appends both polylines
    // instead of letting one overwrite the other (the wave-0 bug).
    expect(featureCount).toBe(88);
    expect(lines.constellations.Ser).toHaveLength(2);
    const byHr = new Map(stars.map((s) => [s.hr, s] as const));
    let vertices = 0;
    let segments = 0;
    let unresolved = 0;
    for (const polylines of Object.values(lines.constellations)) {
      for (const polyline of polylines) {
        segments += 1;
        for (const hr of polyline) {
          vertices += 1;
          if (!byHr.has(hr)) unresolved += 1;
        }
      }
    }
    expect(segments).toBe(150);
    expect(vertices).toBe(893);
    expect(unresolved).toBe(0);
  });

  // Source: docs/notes/earthsky/wave0/mansions/table.json (row W0-5) - the
  // unique HR numbers referenced by the lunar-mansion determinative stars
  // (every en_star/zh_star entry that carries an HR). Counted by the lead on
  // 2026-10-24: 56 rows (28 nakshatra + 28 xiu) hold 84 star references, 80 of
  // them with an HR, 52 unique HRs. One row has no HR at all (Mrigashirsha,
  // lambda Ori: SIMBAD returned no HR for the double), so that star is NOT
  // covered here. This is a presence test, not an authority on which star is
  // the classical yogatara (see the spec, Wave 0 results).
  const MANSION_HRS: number[] = [
    39, 215, 271, 361, 553, 801, 838, 1142, 1165, 1409, 1457, 1713, 1852, 1876,
    2286, 2990, 3357, 3410, 3461, 3482, 3748, 3903, 3982, 4287, 4357, 4534, 4662, 5056,
    5315, 5340, 5531, 5685, 5944, 5953, 6084, 6134, 6247, 6527, 6746, 6879, 7001, 7039,
    7121, 7557, 7776, 7906, 7950, 8232, 8414, 8698, 8775, 8781,
  ];

  it('lists all 52 unique mansion HRs', () => {
    expect(MANSION_HRS).toHaveLength(52);
    expect(new Set(MANSION_HRS).size).toBe(52);
  });

  it('every mansion determinative star is present in the catalogue', () => {
    const byHr = new Set(stars.map((s) => s.hr));
    for (const hr of MANSION_HRS) {
      expect(byHr.has(hr), `HR ${hr}`).toBe(true);
    }
  });
});

describe('README-sky.md', () => {
  it('carries the licence and credit strings', () => {
    const flat = readme.replace(/\s+/g, ' ');
    expect(flat).toMatch(/VizieR catalogue access tool, CDS, Strasbourg/);
    expect(flat).toMatch(/Hoffleit & Warren/);
    expect(flat).toMatch(/Creative Commons Attribution/);
    expect(flat).toMatch(/Olaf Frohn/);
    expect(flat).toMatch(/Sky & Telescope/);
    expect(flat).toMatch(/third-party evidence/);
    expect(flat).toMatch(/column 84/); // the V/50 parse hazard
  });
});
