import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, test } from 'vitest';

import { decodeLand } from '../lib/earth';

const DATA = path.join(__dirname, '../data/land-110m.json');
const README = path.join(__dirname, '../data/README-110m.md');

describe('land-110m.json data file (W0-1 figures)', () => {
  const raw = readFileSync(DATA);
  const text = raw.toString('utf8');

  test('size within the 110m budget (<= 70,000 bytes)', () => {
    expect(raw.byteLength).toBeLessThanOrEqual(70_000);
  });

  test('sha256 equals the one documented in README-110m.md', () => {
    const sha = createHash('sha256').update(raw).digest('hex');
    const readme = readFileSync(README, 'utf8');
    expect(readme).toContain(sha);
    expect(sha.startsWith('5a819ebb0d519434')).toBe(true);
  });

  test('decodeLand gives 127 polygons and 5,132 vertices (W0-1 figures)', () => {
    const land = decodeLand(JSON.parse(text));
    expect(land.polys.length).toBe(127);
    const vertices = land.polys.reduce(
      (n, p) => n + p.o.length / 2 + p.h.reduce((m, h) => m + h.length / 2, 0),
      0,
    );
    expect(vertices).toBe(5132);
  });

  test('every coordinate in range, one hole ring (the Caspian), decimals 3', () => {
    const land = decodeLand(JSON.parse(text));
    expect(land.decimals).toBe(3);
    let holes = 0;
    for (const poly of land.polys) {
      holes += poly.h.length;
      for (let i = 0; i < poly.o.length; i += 2) {
        expect(poly.o[i]).toBeGreaterThanOrEqual(-180);
        expect(poly.o[i]).toBeLessThanOrEqual(180);
        expect(poly.o[i + 1]).toBeGreaterThanOrEqual(-90);
        expect(poly.o[i + 1]).toBeLessThanOrEqual(90);
      }
    }
    expect(holes).toBe(1);
  });
});
