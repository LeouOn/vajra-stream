/**
 * Earth & Sky wave 5 — deterministic label placement for the sky dome.
 *
 * Pure: no DOM, no randomness. The dome measures each label with
 * `ctx.measureText`, then calls `placeLabels`; labels are placed when their
 * marker positions (rounded) or sizes change, and drawn from the cache each
 * frame.
 *
 * Rules: higher priority first (Sun/Moon > planets > sacred stars; ties by id).
 * For each label, try right-up, right-down, left-up, left-down, above, below,
 * then the same ring farther out (with a thin leader). A candidate is rejected
 * if its box overlaps a placed label, any marker circle, or leaves the dome
 * disc. If nothing fits, the lowest-priority already-placed label is hidden to
 * make room; if this label is the lowest, it is hidden. Positions are returned
 * in the input order.
 */

export interface LabelItem {
  id: string;
  /** Marker centre in dome pixels. */
  x: number;
  y: number;
  /** Measured text box (width) and nominal line height. */
  width: number;
  height: number;
  /** Higher is more important. */
  priority: number;
  /** Radius of the marker's core circle, for collision and the first offset. */
  markerRadius: number;
}

export interface Box {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface LabelBounds {
  cx: number;
  cy: number;
  radius: number;
  /** Pixels kept free at the disc edge. */
  margin?: number;
  /** Distance from the marker core to a label box. */
  gap?: number;
  /** Fixed boxes labels must not cover (altitude ticks, compass letters). */
  obstacles?: readonly Box[];
}

export interface LabelLeader {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface PlacedLabel {
  id: string;
  /** fillText anchor (baseline y; x is left/right/centre per `anchor`). */
  x: number;
  y: number;
  anchor: 'left' | 'right' | 'center';
  leader: LabelLeader | null;
  hidden: boolean;
}

interface Direction {
  vertical: 'up' | 'down';
  horizontal: 'right' | 'left' | 'center';
}

const DIRECTIONS: readonly Direction[] = [
  { horizontal: 'right', vertical: 'up' },
  { horizontal: 'right', vertical: 'down' },
  { horizontal: 'left', vertical: 'up' },
  { horizontal: 'left', vertical: 'down' },
  { horizontal: 'center', vertical: 'up' },
  { horizontal: 'center', vertical: 'down' },
];

const FAR_EXTRA_PX = 14;

function candidate(
  item: LabelItem,
  direction: Direction,
  far: boolean,
  gap: number,
  ring = 1,
): { x: number; y: number; anchor: PlacedLabel['anchor']; box: Box } {
  const extra = far ? FAR_EXTRA_PX * ring : 0;
  // `y` is the text baseline; the box occupies [y - height, y].
  const upY = item.y - gap - extra;
  const downY = item.y + item.markerRadius + gap + extra + item.height;
  const y = direction.vertical === 'up' ? upY : downY;
  if (direction.horizontal === 'center') {
    return {
      x: item.x,
      y,
      anchor: 'center',
      box: { x1: item.x - item.width / 2, y1: y - item.height, x2: item.x + item.width / 2, y2: y },
    };
  }
  if (direction.horizontal === 'right') {
    const x = item.x + item.markerRadius + gap + extra;
    return { x, y, anchor: 'left', box: { x1: x, y1: y - item.height, x2: x + item.width, y2: y } };
  }
  const x = item.x - item.markerRadius - gap - extra;
  return { x, y, anchor: 'right', box: { x1: x - item.width, y1: y - item.height, x2: x, y2: y } };
}

function boxesOverlap(a: Box, b: Box, padding = 1): boolean {
  return (
    a.x1 < b.x2 + padding &&
    a.x2 > b.x1 - padding &&
    a.y1 < b.y2 + padding &&
    a.y2 > b.y1 - padding
  );
}

function boxOverlapsCircle(box: Box, x: number, y: number, radius: number): boolean {
  const nearestX = Math.max(box.x1, Math.min(x, box.x2));
  const nearestY = Math.max(box.y1, Math.min(y, box.y2));
  return Math.hypot(nearestX - x, nearestY - y) < radius;
}

function boxInsideDisc(box: Box, bounds: LabelBounds): boolean {
  const limit = bounds.radius - (bounds.margin ?? 4);
  if (limit <= 0) return false;
  for (const [x, y] of [
    [box.x1, box.y1],
    [box.x2, box.y1],
    [box.x1, box.y2],
    [box.x2, box.y2],
  ]) {
    if (Math.hypot(x - bounds.cx, y - bounds.cy) > limit) return false;
  }
  return true;
}

function leaderFor(item: LabelItem, box: Box): LabelLeader {
  const x2 = Math.max(box.x1, Math.min(item.x, box.x2));
  const y2 = Math.max(box.y1, Math.min(item.y, box.y2));
  const dx = x2 - item.x;
  const dy = y2 - item.y;
  const length = Math.hypot(dx, dy) || 1;
  return {
    x1: item.x + (dx / length) * item.markerRadius,
    y1: item.y + (dy / length) * item.markerRadius,
    x2,
    y2,
  };
}

/**
 * Place every label, hiding the lowest-priority ones when the disc is full.
 * Deterministic: the same items and bounds always return the same result.
 */
export function placeLabels(items: readonly LabelItem[], bounds: LabelBounds): PlacedLabel[] {
  const gap = bounds.gap ?? 3;
  const order = [...items].sort((a, b) => b.priority - a.priority || a.id.localeCompare(b.id));
  const placed: { item: LabelItem; label: PlacedLabel; box: Box }[] = [];
  const hidden = new Set<string>();

  const tryPlace = (item: LabelItem): { label: PlacedLabel; box: Box } | null => {
    for (const ring of [0, 1, 2]) {
      const far = ring > 0;
      for (const direction of DIRECTIONS) {
        const candidateBox = candidate(item, direction, far, gap, ring);
        if (!boxInsideDisc(candidateBox.box, bounds)) continue;
        if (placed.some((entry) => boxesOverlap(entry.box, candidateBox.box))) continue;
        if ((bounds.obstacles ?? []).some((obstacle) => boxesOverlap(obstacle, candidateBox.box, 0))) {
          continue;
        }
        if (items.some((marker) => boxOverlapsCircle(candidateBox.box, marker.x, marker.y, marker.markerRadius))) {
          continue;
        }
        return {
          label: {
            id: item.id,
            x: candidateBox.x,
            y: candidateBox.y,
            anchor: candidateBox.anchor,
            leader: far ? leaderFor(item, candidateBox.box) : null,
            hidden: false,
          },
          box: candidateBox.box,
        };
      }
    }
    return null;
  };

  for (const item of order) {
    let result = tryPlace(item);
    while (result === null) {
      // Free the least important already-placed label with a lower priority.
      let victim = -1;
      for (let index = 0; index < placed.length; index += 1) {
        if (placed[index].item.priority >= item.priority) continue;
        if (victim === -1 || placed[index].item.priority < placed[victim].item.priority) {
          victim = index;
        }
      }
      if (victim === -1) break;
      hidden.add(placed[victim].item.id);
      placed.splice(victim, 1);
      result = tryPlace(item);
    }
    if (result === null) {
      hidden.add(item.id);
      continue;
    }
    placed.push({ item, ...result });
  }

  const byId = new Map(placed.map((entry) => [entry.item.id, entry.label]));
  return items.map((item) => {
    if (hidden.has(item.id)) {
      return { id: item.id, x: item.x, y: item.y, anchor: 'left' as const, leader: null, hidden: true };
    }
    const label = byId.get(item.id);
    if (!label) {
      return { id: item.id, x: item.x, y: item.y, anchor: 'left' as const, leader: null, hidden: true };
    }
    return label;
  });
}
