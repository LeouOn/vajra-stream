/**
 * W1-B data tests for frontend/src/data/land-50m.json + README.md.
 *
 * The file must be a byte-for-byte copy of the wave-0 dataset
 * (docs/notes/earthsky/wave0/land/land-50m.json): 688,309 bytes,
 * sha256 b5699b5db7fda498..., 1,421 polygons, 60,645 vertices, one hole
 * (the Caspian Sea), Natural Earth 50m, public domain.
 */

import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { decodeLand } from '../lib/earth';

const dataUrl = new URL('../data/land-50m.json', import.meta.url);
const readmeUrl = new URL('../data/README.md', import.meta.url);
const bytes = readFileSync(dataUrl);
const readme = readFileSync(readmeUrl, 'utf8');
const raw = JSON.parse(bytes.toString('utf8'));

describe('land-50m.json data file', () => {
  it('is within the 800,000-byte budget', () => {
    expect(bytes.byteLength).toBeLessThanOrEqual(800_000);
  });

  it('sha256 equals the one recorded in README.md', () => {
    const match = readme.match(/sha256[^0-9a-f\n]{0,10}([0-9a-f]{16,64})/i);
    expect(match).not.toBeNull();
    const digest = createHash('sha256').update(bytes).digest('hex');
    expect(digest.startsWith(match![1])).toBe(true);
    expect(match![1].length).toBeGreaterThanOrEqual(16);
  });

  it('decodes to 1,421 polygons with 60,645 vertices and one hole', () => {
    const land = decodeLand(raw);
    expect(land.polys.length).toBe(1421);
    const holes = land.polys.filter((p) => p.h.length > 0);
    expect(holes.length).toBe(1);
    const total = land.polys.reduce(
      (sum, p) => sum + p.o.length / 2 + p.h.reduce((s, h) => s + h.length / 2, 0),
      0,
    );
    expect(total).toBe(60645);
  });

  it('every integer coordinate is in range', () => {
    const lonLimit = 180 * 10 ** raw.decimals;
    const latLimit = 90 * 10 ** raw.decimals;
    for (const poly of raw.polys) {
      for (const ring of [poly.o, ...poly.h]) {
        for (let i = 0; i < ring.length; i += 2) {
          expect(ring[i]).toBeGreaterThanOrEqual(-lonLimit);
          expect(ring[i]).toBeLessThanOrEqual(lonLimit);
          expect(ring[i + 1]).toBeGreaterThanOrEqual(-latLimit);
          expect(ring[i + 1]).toBeLessThanOrEqual(latLimit);
        }
      }
    }
  });
});

describe('land data README.md', () => {
  it('names the licence and the source', () => {
    expect(readme).toMatch(/Natural Earth/i);
    expect(readme).toMatch(/public domain/i);
    expect(readme).toMatch(/convert_land\.py/);
    expect(readme).toMatch(/decimals\s*=\s*2/i);
  });
});
