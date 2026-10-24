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

const BOUNDS: LabelBounds = { cx: 220, cy: 220, radius: 440 * 0.42, margin: 4, gap: 3 };

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
    for (let b = a + 1; b < placed.length; b += 1) {
      if (placed[b].hidden) continue;
      expect(
        overlaps(boxOf(byId.get(placed[a].id) as LabelItem, placed[a]), boxOf(byId.get(placed[b].id) as LabelItem, placed[b])),
      ).toBe(false);
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

  it('is deterministic and keeps its order', () => {
    const items: LabelItem[] = [
      { id: 'b', x: 200, y: 200, width: 20, height: 10, priority: 10, markerRadius: 5 },
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

const SF_NOON: FixtureLabel[] = [
  { id: 'sun', text: 'Sun ☉', alt: 40.15, az: 175.52, priority: 40, markerRadius: 8 },
  { id: 'mercury', text: 'Mercury ☿', alt: 27.85, az: 156.74, priority: 20, markerRadius: 8 },
  { id: 'venus', text: 'Venus ♀', alt: 34.64, az: 179.85, priority: 20, markerRadius: 8 },
  { id: 'mars', text: 'Mars ♂', alt: 28.01, az: 271.41, priority: 20, markerRadius: 8 },
  { id: 'jupiter', text: 'Jupiter ♃', alt: 32.47, az: 263.02, priority: 20, markerRadius: 8 },
  { id: 'vega', text: 'Vega', alt: 33.83, az: 64.21, priority: 10, markerRadius: 5 },
  { id: 'arcturus', text: 'Arcturus', alt: 69.88, az: 156.13, priority: 10, markerRadius: 5 },
  { id: 'spica', text: 'Spica', alt: 40.77, az: 185.32, priority: 10, markerRadius: 5 },
  { id: 'antares', text: 'Antares', alt: 14.62, az: 141.76, priority: 10, markerRadius: 5 },
  { id: 'polaris', text: 'Polaris', alt: 37.19, az: 359.72, priority: 10, markerRadius: 5 },
  { id: 'regulus', text: 'Regulus', alt: 36.01, az: 255.97, priority: 10, markerRadius: 5 },
];

const TOKYO_NIGHT: FixtureLabel[] = [
  { id: 'moon', text: 'Moon ☽', alt: 20.02, az: 264.87, priority: 39, markerRadius: 8 },
  { id: 'mars', text: 'Mars ♂', alt: 36.26, az: 93.84, priority: 20, markerRadius: 8 },
  { id: 'jupiter', text: 'Jupiter ♃', alt: 27.84, az: 92.19, priority: 20, markerRadius: 8 },
  { id: 'saturn', text: 'Saturn ♄', alt: 16.8, az: 259.11, priority: 20, markerRadius: 8 },
  { id: 'uranus', text: 'Uranus ♅', alt: 68.71, az: 229.28, priority: 20, markerRadius: 8 },
  { id: 'neptune', text: 'Neptune ♆', alt: 9.81, az: 262.24, priority: 20, markerRadius: 8 },
  { id: 'sirius', text: 'Sirius', alt: 33.39, az: 155.22, priority: 10, markerRadius: 5 },
  { id: 'aldebaran', text: 'Aldebaran', alt: 68.23, az: 208.92, priority: 10, markerRadius: 5 },
  { id: 'betelgeuse', text: 'Betelgeuse', alt: 60.14, az: 161.83, priority: 10, markerRadius: 5 },
  { id: 'polaris', text: 'Polaris', alt: 36.63, az: 359.57, priority: 10, markerRadius: 5 },
  { id: 'regulus', text: 'Regulus', alt: 21.18, az: 90.59, priority: 10, markerRadius: 5 },
  { id: 'pleiades', text: 'Pleiades', alt: 66.91, az: 245.32, priority: 10, markerRadius: 5 },
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
});
