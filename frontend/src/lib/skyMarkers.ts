/**
 * Earth & Sky wave 5 — marker declutter for the dome (pure, deterministic).
 *
 * Planet rings are ~15 px across. When several bodies share almost the same
 * sky position (Tokyo: Moon/Saturn/Neptune within 3.5 deg) their rings overlap;
 * no label placement can fix that. The Sun and the Moon always keep their true
 * position, and so does the highest-priority other marker; the rest are moved
 * along a deterministic fan (starting away from the disc centre) to the first
 * place where the ring centres are at least `minDistance` apart and inside the
 * disc. The caller draws a faint leader and a dot at the true position.
 */

export interface MarkerItem {
  id: string;
  x: number;
  y: number;
  /** Higher is more important; ties by id. */
  priority: number;
  /** Drawn ring radius (used only for the disc-edge check). */
  radius: number;
}

export interface MarkerBounds {
  cx: number;
  cy: number;
  radius: number;
  /** Pixels kept free at the disc edge. */
  margin?: number;
}

export interface MarkerPlacement {
  id: string;
  /** Displayed centre. */
  x: number;
  y: number;
  /** The real sky position (for the leader/dot). */
  trueX: number;
  trueY: number;
  displaced: boolean;
}

/** Rings closer than this (centre to centre) overlap. */
export const MIN_RING_DISTANCE_PX = 16;
/** Fan distances tried for a displaced marker. */
const FAN_RADII = [16, 19, 22];
/** Always keep their true position (the Sun and the Moon). */
const FIXED_IDS = new Set(['sun', 'moon']);

export function declutterMarkers(
  items: readonly MarkerItem[],
  bounds: MarkerBounds,
  minDistance = MIN_RING_DISTANCE_PX,
): MarkerPlacement[] {
  const order = [...items].sort((a, b) => b.priority - a.priority || a.id.localeCompare(b.id));
  const place = (item: MarkerItem, x: number, y: number, displaced: boolean): MarkerPlacement => ({
    id: item.id,
    x,
    y,
    trueX: item.x,
    trueY: item.y,
    displaced,
  });
  const placed: MarkerPlacement[] = [];
  let keptTrue = false;

  for (const item of order) {
    const mustStay = FIXED_IDS.has(item.id) || !keptTrue;
    if (mustStay || placed.every((other) => Math.hypot(other.x - item.x, other.y - item.y) >= minDistance)) {
      placed.push(place(item, item.x, item.y, false));
      keptTrue = true;
      continue;
    }

    const base = Math.atan2(item.y - bounds.cy, item.x - bounds.cx);
    const angleOffsets = [0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180];
    let found: MarkerPlacement | null = null;
    for (const radiusPx of FAN_RADII) {
      for (const offsetDeg of angleOffsets) {
        const angle = base + (offsetDeg * Math.PI) / 180;
        const x = item.x + Math.cos(angle) * radiusPx;
        const y = item.y + Math.sin(angle) * radiusPx;
        const edge = bounds.radius - (bounds.margin ?? 2);
        if (Math.hypot(x - bounds.cx, y - bounds.cy) + item.radius > edge) continue;
        if (placed.some((other) => Math.hypot(other.x - x, other.y - y) < minDistance)) continue;
        found = place(item, x, y, true);
        break;
      }
      if (found) break;
    }
    placed.push(found ?? place(item, item.x, item.y, false));
  }
  // Return in input order so callers can map by id predictably.
  const byId = new Map(placed.map((entry) => [entry.id, entry]));
  return items.map((item) => byId.get(item.id) as MarkerPlacement);
}
