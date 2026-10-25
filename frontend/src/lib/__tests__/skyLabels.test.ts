/**
 * W5-A — deterministic label placement.
 *
 * Synthetic geometry tests, then the real crowded payloads measured from the
 * backend for San Francisco noon (2026-10-24T19:39:50Z) and Tokyo night
 * (2026-10-24T17:50:28.652Z, observer 36.1111,139.3818), projected at a
 * 440 px dome. Positions are literals from core/celestial_sky; the labels use
 * the dome's text strings and a plausible 5 px/char, 10 px box.
 */
import { describe, expect, it } from 'vitest';
import { placeLabels, type LabelItem, type LabelBounds } from '../skyLabels';

const BOUNDS: LabelBounds = {
  cx: 220,
  cy: 220,
  radius: 440 * 0.42,
  margin: 4,
  gap: 3,
  // Altitude ticks and compass letters, as the dome draws them (440 px disc).
  obstacles: [
    { x1: 213, y1: 98.8, x2: 227, y2: 107.8 }, // 30 deg tick
    { x1: 213, y1: 160.4, x2: 227, y2: 169.4 }, // 60 deg tick
    { x1: 215, y1: 16.2, x2: 225, y2: 26.2 }, // N
    { x1: 16.2, y1: 215, x2: 26.2, y2: 225 }, // E
    { x1: 215, y1: 393.8, x2: 225, y2: 403.8 }, // S
    { x1: 393.8, y1: 215, x2: 403.8, y2: 225 }, // W
  ],
};

interface FixtureLabel {
  id: string;
  text: string;
  alt: number;
  az: number;
  priority: number;
  markerRadius: number;
}

function item(label: FixtureLabel): LabelItem {
  const r = ((90 - Math.max(0, label.alt)) / 90) * 440 * 0.42;
  const rad = (label.az * Math.PI) / 180;
  return {
    id: label.id,
    x: 220 - r * Math.sin(rad),
    y: 220 - r * Math.cos(rad),
    width: label.text.length * 5 + 2,
    height: 10,
    priority: label.priority,
    markerRadius: label.markerRadius,
  };
}

function boxOf(item: LabelItem, placed: ReturnType<typeof placeLabels>[number]): [number, number, number, number] {
  const left =
    placed.anchor === 'left' ? placed.x : placed.anchor === 'right' ? placed.x - item.width : placed.x - item.width / 2;
  return [left, placed.y - item.height, left + item.width, placed.y];
}

function circleDistance(box: number[], x: number, y: number): number {
  const nearestX = Math.max(box[0], Math.min(x, box[2]));
  const nearestY = Math.max(box[1], Math.min(y, box[3]));
  return Math.hypot(nearestX - x, nearestY - y);
}

function overlaps(a: number[], b: number[]): boolean {
  return a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
}

function assertPlacementSuccess(items: LabelItem[]): void {
  const placed = placeLabels(items, BOUNDS);
  const byId = new Map(items.map((i) => [i.id, i]));
  for (const label of placed) {
    if (label.hidden) continue;
    const box = boxOf(byId.get(label.id) as LabelItem, label);
    for (const [x, y] of [
      [box[0], box[1]],
      [box[2], box[1]],
      [box[0], box[3]],
      [box[2], box[3]],
    ]) {
      expect(Math.hypot(x - BOUNDS.cx, y - BOUNDS.cy)).toBeLessThanOrEqual(BOUNDS.radius - 4 + 1e-9);
    }
  }
  for (let a = 0; a < placed.length; a += 1) {
    if (placed[a].hidden) continue;
    for (const obstacle of BOUNDS.obstacles ?? []) {
      expect(overlaps(boxOf(byId.get(placed[a].id) as LabelItem, placed[a]), [obstacle.x1, obstacle.y1, obstacle.x2, obstacle.y2])).toBe(false);
    }
    for (let b = a + 1; b < placed.length; b += 1) {
      if (placed[b].hidden) continue;
      expect(
        overlaps(boxOf(byId.get(placed[a].id) as LabelItem, placed[a]), boxOf(byId.get(placed[b].id) as LabelItem, placed[b])),
      ).toBe(false);
    }
    // W5-K: a real 1 px margin from EVERY drawn marker footprint, not a
    // sub-pixel touch. V6 measured 0.06 / 0.55 px intrusions into 14.5 px.
    for (const marker of items) {
      expect(
        circleDistance(boxOf(byId.get(placed[a].id) as LabelItem, placed[a]), marker.x, marker.y),
        `${placed[a].id}/${marker.id}`,
      ).toBeGreaterThanOrEqual(marker.markerRadius + 1 - 1e-6);
    }
  }
}

describe('placeLabels geometry', () => {
  it('places a lone label at the first candidate (right-up of its marker)', () => {
    const item: LabelItem = { id: 'sun', x: 200, y: 200, width: 30, height: 10, priority: 40, markerRadius: 8 };
    const [label] = placeLabels([item], BOUNDS);
    expect(label.hidden).toBe(false);
    expect(label.anchor).toBe('left');
    expect(label.x).toBe(200 + 8 + 3);
    expect(label.y).toBe(200 - 3);
    expect(label.leader).toBeNull();
  });

  it('with the drawn planet footprint the lone label is still the first candidate (6.5 px farther right)', () => {
    const item: LabelItem = { id: 'mars', x: 200, y: 200, width: 30, height: 10, priority: 20, markerRadius: 14.5 };
    const [label] = placeLabels([item], BOUNDS);
    expect(label.hidden).toBe(false);
    expect(label.anchor).toBe('left');
    expect(label.x).toBe(200 + 14.5 + 3); // 217.5 (was 211 with the 8 px core)
    expect(label.y).toBe(197);
  });

  it('never covers a fixed obstacle (altitude ticks / compass letters)', () => {
    const item: LabelItem = { id: 'mars', x: 200, y: 200, width: 30, height: 10, priority: 20, markerRadius: 8 };
    // The first candidate would be [211,187,241,197]; put an obstacle there.
    const bounds: LabelBounds = { ...BOUNDS, obstacles: [{ x1: 205, y1: 185, x2: 245, y2: 199 }] };
    const [label] = placeLabels([item], bounds);
    expect(label.hidden).toBe(false);
    expect([label.x, label.y]).not.toEqual([211, 197]);
  });

  it('is deterministic and keeps its order', () => {
    const items: LabelItem[] = [
      { id: 'b', x: 200, y: 200, width: 20, height: 10, priority: 10, markerRadius: STAR_FOOTPRINT },
      { id: 'a', x: 205, y: 202, width: 20, height: 10, priority: 20, markerRadius: 5 },
    ];
    expect(placeLabels(items, BOUNDS)).toEqual(placeLabels(items, BOUNDS));
    expect(placeLabels(items, BOUNDS).map((label) => label.id)).toEqual(['b', 'a']);
  });

  it('never overlaps a box or a marker and stays inside the disc', () => {
    const items: LabelItem[] = [];
    for (let i = 0; i < 8; i += 1) {
      items.push({
        id: `p${i}`,
        x: 160 + i * 8,
        y: 190 + (i % 3) * 6,
        width: 26,
        height: 10,
        priority: i === 0 ? 40 : 20,
        markerRadius: 8,
      });
    }
    assertPlacementSuccess(items);
  });

  it('respects priority: when the ring is full the lowest priority is hidden', () => {
    const base = { x: 220, y: 220, width: 30, height: 10, markerRadius: 6 };
    const items: LabelItem[] = [
      { id: 'sun', priority: 40, ...base },
      { id: 'moon', priority: 39, ...base },
      { id: 'mars', priority: 20, ...base },
    ];
    for (let i = 0; i < 24; i += 1) items.push({ id: `star-${String(i).padStart(2, '0')}`, priority: 10, ...base });

    const placed = placeLabels(items, BOUNDS);
    const hidden = placed.filter((label) => label.hidden).map((label) => label.id);
    expect(hidden.length).toBeGreaterThan(0);
    for (const id of hidden) expect(id.startsWith('star-')).toBe(true);
    for (const id of ['sun', 'moon', 'mars']) {
      expect(placed.find((label) => label.id === id)?.hidden).toBe(false);
    }
  });
});

const PLANET_FOOTPRINT = 14.5;
const STAR_FOOTPRINT = 12;

const SF_NOON: FixtureLabel[] = [
  { id: 'sun', text: 'Sun ☉', alt: 40.15, az: 175.52, priority: 40, markerRadius: PLANET_FOOTPRINT },
  { id: 'mercury', text: 'Mercury ☿', alt: 27.85, az: 156.74, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'venus', text: 'Venus ♀', alt: 34.64, az: 179.85, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'mars', text: 'Mars ♂', alt: 28.01, az: 271.41, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'jupiter', text: 'Jupiter ♃', alt: 32.47, az: 263.02, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'vega', text: 'Vega', alt: 33.83, az: 64.21, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'arcturus', text: 'Arcturus', alt: 69.88, az: 156.13, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'spica', text: 'Spica', alt: 40.77, az: 185.32, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'antares', text: 'Antares', alt: 14.62, az: 141.76, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'polaris', text: 'Polaris', alt: 37.19, az: 359.72, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'regulus', text: 'Regulus', alt: 36.01, az: 255.97, priority: 10, markerRadius: STAR_FOOTPRINT },
];

const TOKYO_NIGHT: FixtureLabel[] = [
  // Real alt/az at 2026-10-24T18:29:36Z, observer 35.68/139.69.
  { id: 'moon', text: 'Moon ☽', alt: 12.18, az: 270.97, priority: 39, markerRadius: PLANET_FOOTPRINT },
  { id: 'mars', text: 'Mars ♂', alt: 44.43, az: 100.26, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'jupiter', text: 'Jupiter ♃', alt: 36.03, az: 98.34, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'saturn', text: 'Saturn ♄', alt: 8.74, az: 265.4, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'uranus', text: 'Uranus ♅', alt: 62.01, az: 245.65, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'neptune', text: 'Neptune ♆', alt: 1.68, az: 268.29, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'sirius', text: 'Sirius', alt: 36.49, az: 166.48, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'aldebaran', text: 'Aldebaran', alt: 63.33, az: 229.63, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'betelgeuse', text: 'Betelgeuse', alt: 61.71, az: 182.32, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'polaris', text: 'Polaris', alt: 36.13, az: 359.47, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'regulus', text: 'Regulus', alt: 29.38, az: 96.57, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'pleiades', text: 'Pleiades', alt: 59.27, az: 257.25, priority: 10, markerRadius: STAR_FOOTPRINT },
];

const DELHI_MOONLIGHT: FixtureLabel[] = [
  // Real alt/az at 2026-10-24T18:30:00Z, observer 28.61/77.21.
  { id: 'moon', text: 'Moon ☽', alt: 63.53, az: 222.46, priority: 39, markerRadius: PLANET_FOOTPRINT },
  { id: 'saturn', text: 'Saturn ♄', alt: 57.89, az: 215.2, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'uranus', text: 'Uranus ♅', alt: 57.33, az: 95.48, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'neptune', text: 'Neptune ♆', alt: 52.23, az: 224.17, priority: 20, markerRadius: PLANET_FOOTPRINT },
  { id: 'sirius', text: 'Sirius', alt: 5.62, az: 112.55, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'vega', text: 'Vega', alt: 4.81, az: 312.11, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'aldebaran', text: 'Aldebaran', alt: 50.08, az: 98.39, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'betelgeuse', text: 'Betelgeuse', alt: 28.7, az: 97.53, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'polaris', text: 'Polaris', alt: 29.2, az: 0.23, priority: 10, markerRadius: STAR_FOOTPRINT },
  { id: 'pleiades', text: 'Pleiades', alt: 63.48, az: 92.73, priority: 10, markerRadius: STAR_FOOTPRINT },
];

describe('real crowded payloads', () => {
  it('San Francisco noon: no overlaps, every planet keeps a label', () => {
    const items = SF_NOON.map(item);
    assertPlacementSuccess(items);
    const placed = placeLabels(items, BOUNDS);
    for (const id of ['sun', 'mercury', 'venus', 'mars', 'jupiter']) {
      expect(placed.find((label) => label.id === id)?.hidden, id).toBe(false);
    }
  });

  it('Tokyo night (x-ray): no overlaps, every planet keeps a label', () => {
    const items = TOKYO_NIGHT.map(item);
    assertPlacementSuccess(items);
    const placed = placeLabels(items, BOUNDS);
    for (const id of ['moon', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune']) {
      expect(placed.find((label) => label.id === id)?.hidden, id).toBe(false);
    }
  });

  it('Delhi moonlight: no overlaps, every planet keeps a label', () => {
    const items = DELHI_MOONLIGHT.map(item);
    assertPlacementSuccess(items);
    const placed = placeLabels(items, BOUNDS);
    for (const id of ['moon', 'saturn', 'uranus', 'neptune']) {
      expect(placed.find((label) => label.id === id)?.hidden, id).toBe(false);
    }
  });
});
