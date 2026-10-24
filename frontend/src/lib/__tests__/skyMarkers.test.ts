import { describe, expect, it } from 'vitest';
import {
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
      expect(Math.hypot(p.x - BOUNDS.cx, p.y - BOUNDS.cy) + items[a].radius).toBeLessThanOrEqual(
        BOUNDS.radius - 2 + 1e-9,
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

  it('Tokyo night rim stack: Moon/Saturn/Neptune end up at least 16 px apart', () => {
    // Real alt/az at 2026-10-24T18:29:36Z, observer 35.68/139.69, 309 px dome.
    const project = (alt: number, az: number) => {
      const r = ((90 - Math.max(0, alt)) / 90) * (309 * 0.42);
      const rad = (az * Math.PI) / 180;
      return { x: 309 / 2 - r * Math.sin(rad), y: 309 / 2 - r * Math.cos(rad) };
    };
    const moon = project(12.44, 270.69);
    const saturn = project(9.0, 265.5);
    const neptune = project(1.9, 267.5);
    const items = [
      { ...item('moon', moon.x, moon.y, 39) },
      { ...item('saturn', saturn.x, saturn.y) },
      { ...item('neptune', neptune.x, neptune.y) },
    ];
    const placements = declutterMarkers(items, BOUNDS);
    expect(placements.find((p) => p.id === 'moon')?.displaced).toBe(false);
    expect(placements.filter((p) => p.displaced).length).toBeGreaterThanOrEqual(1);
    assertSpread(items, placements);
  });
});
