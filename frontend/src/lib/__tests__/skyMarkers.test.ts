import { describe, expect, it } from 'vitest';
import {
  EDGE_OVERFLOW_PX,
  MIN_RING_DISTANCE_PX,
  declutterMarkers,
  type MarkerItem,
} from '../skyMarkers';

const BOUNDS = { cx: 154.5, cy: 154.5, radius: 309 * 0.42, margin: 2 };

function item(id: string, x: number, y: number, priority = 20): MarkerItem {
  return { id, x, y, priority, radius: 8 };
}

function assertSpread(items: MarkerItem[], placements: ReturnType<typeof declutterMarkers>): void {
  for (let a = 0; a < placements.length; a += 1) {
    for (let b = a + 1; b < placements.length; b += 1) {
      const pa = placements[a];
      const pb = placements[b];
      const bothFixed = ['sun', 'moon'].includes(pa.id) && ['sun', 'moon'].includes(pb.id);
      if (bothFixed) continue;
      expect(Math.hypot(pa.x - pb.x, pa.y - pb.y), `${pa.id}/${pb.id}`).toBeGreaterThanOrEqual(
        MIN_RING_DISTANCE_PX,
      );
    }
    const p = placements[a];
    // True positions are the real sky points (already on the disc); displaced
    // ones must stay inside the ring's margin.
    if (p.displaced) {
      // W5-K: a ring may sit up to EDGE_OVERFLOW_PX past the edge when nothing
      // inside the disc can satisfy the 16 px rule.
      expect(Math.hypot(p.x - BOUNDS.cx, p.y - BOUNDS.cy) + items[a].radius).toBeLessThanOrEqual(
        BOUNDS.radius - 2 + EDGE_OVERFLOW_PX + 1e-9,
      );
    }
  }
}

describe('declutterMarkers', () => {
  it('keeps isolated markers true and displaces only the crowded ones', () => {
    const items = [item('sun', 100, 100, 40), item('jupiter', 200, 120), item('mars', 202, 123)];
    const placements = declutterMarkers(items, BOUNDS);
    expect(placements.find((p) => p.id === 'sun')).toMatchObject({ x: 100, y: 100, displaced: false });
    expect(placements.find((p) => p.id === 'jupiter')?.displaced).toBe(false);
    expect(placements.find((p) => p.id === 'mars')?.displaced).toBe(true);
    assertSpread(items, placements);
  });

  it('is deterministic and always keeps the Sun and Moon true', () => {
    const items = [
      item('sun', 150, 150, 40),
      item('moon', 152, 151, 39),
      item('neptune', 151, 152),
      item('saturn', 149, 151),
      item('uranus', 153, 150),
    ];
    const first = declutterMarkers(items, BOUNDS);
    expect(declutterMarkers(items, BOUNDS)).toEqual(first);
    for (const id of ['sun', 'moon']) {
      const p = first.find((entry) => entry.id === id);
      const source = items.find((entry) => entry.id === id);
      expect(p).toMatchObject({ x: source?.x, y: source?.y, displaced: false });
    }
    assertSpread(items, first);
  });

  it('when no inside candidate fits, the fallback maximises separation and may overhang the edge', () => {
    // A tiny disc with two fixed rings at the rim and one crowded planet: every
    // fan candidate is pushed past the edge, so the old fallback silently put
    // the planet back on top of the fixed rings. The new fallback finds the
    // best-separated overhang instead.
    const bounds = { cx: 150, cy: 150, radius: 30, margin: 2 };
    const items: MarkerItem[] = [
      { id: 'sun', x: 178, y: 150, priority: 40, radius: 8 },
      { id: 'moon', x: 176, y: 150, priority: 39, radius: 8 },
      { id: 'saturn', x: 177, y: 150, priority: 20, radius: 8 },
    ];
    const placements = declutterMarkers(items, bounds);
    const saturn = placements.find((entry) => entry.id === 'saturn');
    expect(saturn?.displaced).toBe(true);
    for (const other of placements) {
      if (other.id === 'saturn') continue;
      expect(Math.hypot((saturn?.x ?? 0) - other.x, (saturn?.y ?? 0) - other.y)).toBeGreaterThanOrEqual(
        MIN_RING_DISTANCE_PX - 1e-9,
      );
    }
    // It may overhang, but only by the documented few pixels.
    expect(Math.hypot((saturn?.x ?? 0) - bounds.cx, (saturn?.y ?? 0) - bounds.cy) + 8).toBeLessThanOrEqual(
      bounds.radius - 2 + EDGE_OVERFLOW_PX + 1e-9,
    );
    assertSpread(items, placements);
  });

  it('nine bodies on the 280 px south rim: every non-fixed pair stays >=16 px', () => {
    // c1's real RED set (KL-c1-evidence/kl-probes.txt): the OLD fallback left a
    // 2.1 px pair (sun/saturn) here; the new fallback reaches 16.6 px.
    const bounds = { cx: 140, cy: 140, radius: 280 * 0.42, margin: 2 };
    const body = (id: string, x: number, y: number, priority: number): MarkerItem => ({
      id,
      x,
      y,
      priority,
      radius: 8,
    });
    const items: MarkerItem[] = [
      body('sun', 99.8, 250.5, 40),
      body('moon', 109.1, 245.9, 39),
      body('mercury', 105.1, 250.7, 20),
      body('venus', 125.8, 256.7, 20),
      body('mars', 96.3, 247.6, 20),
      body('jupiter', 108.7, 248.1, 20),
      body('saturn', 100, 248.4, 20),
      body('uranus', 84.1, 235, 20),
      body('neptune', 109.4, 253.5, 20),
    ];
    const placements = declutterMarkers(items, bounds);
    const byId = new Map(placements.map((entry) => [entry.id, entry]));
    expect(byId.get('sun')).toMatchObject({ x: 99.8, y: 250.5, displaced: false });
    expect(byId.get('moon')).toMatchObject({ x: 109.1, y: 245.9, displaced: false });
    const all = [...byId.values()];
    for (let a = 0; a < all.length; a += 1) {
      for (let b = a + 1; b < all.length; b += 1) {
        const pa = all[a];
        const pb = all[b];
        if (['sun', 'moon'].includes(pa.id) && ['sun', 'moon'].includes(pb.id)) continue;
        expect(
          Math.hypot(pa.x - pb.x, pa.y - pb.y),
          `280px ${pa.id}/${pb.id}`,
        ).toBeGreaterThanOrEqual(MIN_RING_DISTANCE_PX - 1e-9);
      }
    }
  });

  it('the 309 px five-body stress set keeps every non-fixed pair >=16 px', () => {
    // The first set where the OLD declutter still overlapped in c1's 309 px
    // stress run (kl-probes.txt); OLD gave a pair under 16 px here.
    const bounds = { cx: 154.5, cy: 154.5, radius: 309 * 0.42, margin: 2 };
    const body = (id: string, x: number, y: number, priority: number): MarkerItem => ({
      id,
      x,
      y,
      priority,
      radius: 8,
    });
    const items: MarkerItem[] = [
      body('sun', 54.4, 106.1, 40),
      body('moon', 66.6, 82.5, 39),
      body('mercury', 48.1, 100.3, 20),
      body('venus', 35.7, 112.6, 20),
      body('mars', 51.8, 103.7, 20),
    ];
    const placements = declutterMarkers(items, bounds);
    const byId = new Map(placements.map((entry) => [entry.id, entry]));
    expect(byId.get('sun')).toMatchObject({ x: 54.4, y: 106.1, displaced: false });
    expect(byId.get('moon')).toMatchObject({ x: 66.6, y: 82.5, displaced: false });
    const all = [...byId.values()];
    for (let a = 0; a < all.length; a += 1) {
      for (let b = a + 1; b < all.length; b += 1) {
        const pa = all[a];
        const pb = all[b];
        if (['sun', 'moon'].includes(pa.id) && ['sun', 'moon'].includes(pb.id)) continue;
        expect(
          Math.hypot(pa.x - pb.x, pa.y - pb.y),
          `309px ${pa.id}/${pb.id}`,
        ).toBeGreaterThanOrEqual(MIN_RING_DISTANCE_PX - 1e-9);
      }
    }
  });

  it('pins the overflow branch: a valid ring may sit just past the disc edge', () => {
    // A crowded south rim where the only 16 px-separated spot for Venus is past
    // the normal edge (the OLD inside-only search left a 6.3 px pair here).
    const bounds = { cx: 140, cy: 140, radius: 280 * 0.42, margin: 2 };
    const body = (id: string, x: number, y: number, priority: number): MarkerItem => ({
      id,
      x,
      y,
      priority,
      radius: 8,
    });
    const items: MarkerItem[] = [
      body('sun', 167.7, 240.2, 40),
      body('moon', 107.9, 237.5, 39),
      body('mercury', 97.1, 243.7, 20),
      body('venus', 105.6, 243.4, 20),
      body('mars', 234.9, 198.0, 20),
      body('jupiter', 149.7, 247.3, 20),
      body('saturn', 169.8, 242.2, 20),
      body('uranus', 108.0, 238.6, 20),
      body('neptune', 122.2, 243.0, 20),
    ];
    const placements = declutterMarkers(items, bounds);
    const edge = bounds.radius - 2;
    const all = placements;
    for (let a = 0; a < all.length; a += 1) {
      for (let b = a + 1; b < all.length; b += 1) {
        const pa = all[a];
        const pb = all[b];
        if (['sun', 'moon'].includes(pa.id) && ['sun', 'moon'].includes(pb.id)) continue;
        expect(
          Math.hypot(pa.x - pb.x, pa.y - pb.y),
          `overflow ${pa.id}/${pb.id}`,
        ).toBeGreaterThanOrEqual(MIN_RING_DISTANCE_PX - 1e-9);
      }
    }
    const overhanging = placements.filter(
      (entry) =>
        entry.displaced && Math.hypot(entry.x - bounds.cx, entry.y - bounds.cy) + 8 > edge,
    );
    expect(overhanging.length).toBeGreaterThan(0);
    for (const entry of placements) {
      if (!entry.displaced) continue;
      expect(
        Math.hypot(entry.x - bounds.cx, entry.y - bounds.cy) + 8,
        `${entry.id} overhang`,
      ).toBeLessThanOrEqual(edge + EDGE_OVERFLOW_PX + 1e-9);
    }
  });

  it('Tokyo night rim stack: every ring ends at least 16 px apart at the real page size', () => {
    // Real alt/az at 2026-10-24T18:29:36Z, observer 35.68/139.69. The real page
    // canvas measured 280-309 px (W5-V6): the earlier fixture used only three
    // markers at 309 px and passed while the page showed Moon-Saturn at 12.2 px.
    const tokyo = [
      // W5-V6 measured the page with a fixed ring at the west rim (the old
      // backend's visible Sun below the horizon); that extra fixed ring is what
      // left Saturn only 12.2 px from the Moon in the old fallback.
      ['sun', -30, 270, 40],
      ['moon', 12.18, 270.97, 39],
      ['mars', 44.43, 100.26, 20],
      ['jupiter', 36.03, 98.34, 20],
      ['saturn', 8.74, 265.4, 20],
      ['uranus', 62.01, 245.65, 20],
      ['neptune', 1.68, 268.29, 20],
    ] as const;
    for (const size of [280, 284, 309]) {
      const project = (alt: number, az: number) => {
        const r = ((90 - Math.max(0, alt)) / 90) * (size * 0.42);
        const rad = (az * Math.PI) / 180;
        return { x: size / 2 - r * Math.sin(rad), y: size / 2 - r * Math.cos(rad) };
      };
      const items = tokyo.map(([id, alt, az, priority]) => {
        const point = project(alt, az);
        return item(id, point.x, point.y, priority);
      });
      const placements = declutterMarkers(items, { cx: size / 2, cy: size / 2, radius: size * 0.42, margin: 2 });
      const byId = new Map(placements.map((entry) => [entry.id, entry]));
      const all = [...byId.values()];
      for (let a = 0; a < all.length; a += 1) {
        for (let b = a + 1; b < all.length; b += 1) {
          const pa = all[a];
          const pb = all[b];
          expect(
            Math.hypot(pa.x - pb.x, pa.y - pb.y),
            `${size}px ${pa.id}/${pb.id}`,
          ).toBeGreaterThanOrEqual(MIN_RING_DISTANCE_PX - 1e-9);
        }
      }
      const moon = byId.get('moon');
      const saturn = byId.get('saturn');
      expect(moon).toMatchObject({ displaced: false });
      expect(byId.get('sun')).toMatchObject({ displaced: false });
      expect(Math.hypot((moon?.x ?? 0) - (saturn?.x ?? 0), (moon?.y ?? 0) - (saturn?.y ?? 0))).toBeGreaterThanOrEqual(
        MIN_RING_DISTANCE_PX,
      );
      expect(placements.filter((entry) => entry.displaced).length).toBeGreaterThanOrEqual(1);
    }
  });
});
