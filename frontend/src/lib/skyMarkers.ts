/**
 * Earth & Sky wave 5 — marker declutter for the dome (pure, deterministic).
 *
 * Planet rings are ~15 px across. When several bodies share almost the same
 * sky position (Tokyo: Moon/Saturn/Neptune within 3.5 deg) their rings overlap;
 * no label placement can fix that. The Sun and the Moon always keep their true
 * position. When neither is present, the first marker placed (highest priority,
 * then id) keeps its true position; every other marker is moved only if it
 * would come closer than `minDistance` to an already-placed ring.
 *
 * BEST EFFORT, not a guarantee: a displaced ring is put at the first candidate
 * inside the disc that meets `minDistance`. If no such candidate exists, a
 * candidate may sit up to `EDGE_OVERFLOW_PX` outside the disc edge; among the
 * valid ones the candidate that MAXIMISES its minimum distance to every
 * already-placed ring wins (deterministic). Only when even that is impossible is
 * the least-bad candidate used. Measured on 2,000 seeded crowded-rim sets at
 * 280 px, 58 still leave a non-fixed pair under 16 px (worst 11.9 px; 51 at
 * 309 px, worst 11.6); ten bodies at one point on the horizon give 9.0 px. The
 * common skies (Tokyo/Delhi/SF) reach >= 16 px at every page size.
 *
 * The caller draws a faint leader and a dot at the true position.
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
const FAN_RADII = [16, 19, 22, 25, 28, 31, 34];
/** How far a displaced ring may sit past the disc edge when nothing inside fits. */
export const EDGE_OVERFLOW_PX = 6;
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
    const edge = bounds.radius - (bounds.margin ?? 2);
    interface Candidate {
      x: number;
      y: number;
      minDistance: number;
    }
    const inside: Candidate[] = [];
    const overflow: Candidate[] = [];
    for (const radiusPx of FAN_RADII) {
      for (const offsetDeg of angleOffsets) {
        const angle = base + (offsetDeg * Math.PI) / 180;
        const x = item.x + Math.cos(angle) * radiusPx;
        const y = item.y + Math.sin(angle) * radiusPx;
        const fromCentre = Math.hypot(x - bounds.cx, y - bounds.cy) + item.radius;
        if (fromCentre > edge + EDGE_OVERFLOW_PX) continue;
        const minDistanceToPlaced = placed.reduce(
          (best, other) => Math.min(best, Math.hypot(other.x - x, other.y - y)),
          Number.POSITIVE_INFINITY,
        );
        (fromCentre <= edge ? inside : overflow).push({ x, y, minDistance: minDistanceToPlaced });
      }
    }
    // Prefer the first inside candidate that satisfies the rule (the old,
    // cheapest behaviour). Otherwise, if any candidate reaches the rule, take
    // the best-separated one; if none can, take the least-bad candidate rather
    // than silently putting the ring back on top of a higher-priority one.
    let chosen: Candidate | null =
      inside.find((candidate) => candidate.minDistance >= minDistance) ?? null;
    if (chosen === null) {
      const all = [...inside, ...overflow];
      const valid = all.filter((candidate) => candidate.minDistance >= minDistance);
      const pool = valid.length > 0 ? valid : all;
      for (const candidate of pool) {
        if (chosen === null || candidate.minDistance > chosen.minDistance + 1e-9) {
          chosen = candidate;
        }
      }
    }
    placed.push(chosen === null ? place(item, item.x, item.y, false) : place(item, chosen.x, chosen.y, true));
  }
  // Return in input order so callers can map by id predictably.
  const byId = new Map(placed.map((entry) => [entry.id, entry]));
  return items.map((item) => byId.get(item.id) as MarkerPlacement);
}
