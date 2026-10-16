/**
 * Digital stick plate (BroadcastPanel). The hidden resonant node is placed by
 * a draw, the stick-pad analog; everything after that follows the hand.
 */

export const STICK_PLATE_MAX_SHIFT_HZ = 20;
export const STICK_PLATE_MIN_HZ = 20;
export const STICK_PLATE_MAX_HZ = 20000;

/**
 * Carrier frequency after one rub step. The shift grows as the hand nears
 * the node, and its direction follows the hand: rubbing right raises the
 * carrier, rubbing left lowers it, no horizontal movement leaves it alone.
 * Deterministic: the same inputs always give the same frequency.
 */
export function nudgeCarrierFrequency(currentHz: number, dist: number, maxDist: number, moveDx: number): number {
  if (moveDx === 0 || maxDist <= 0) return currentHz;
  const closeness = Math.max(0, 1 - dist / maxDist);
  const next = Math.round(currentHz + closeness * STICK_PLATE_MAX_SHIFT_HZ * Math.sign(moveDx));
  return Math.min(STICK_PLATE_MAX_HZ, Math.max(STICK_PLATE_MIN_HZ, next));
}
