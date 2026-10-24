/**
 * Earth & Sky wave 5 — naked-eye planet visibility.
 *
 * The backend carries no planetary magnitudes, so these are TYPICAL apparent
 * magnitudes (not ephemeris values; Mercury varies about -2..+5 and Mars about
 * -3..+2). The Sun and the Moon are never dimmed.
 *
 * The night limit is the same star limit the sky uses (so a bright Moon dims
 * the faint planets too). In daylight planets are easier than stars against a
 * blue sky, so a small piecewise planet limit applies:
 *   - Sun 0..+10 deg:  -3.0  (Venus only; Mercury/Mars/Saturn need darkness)
 *   - Sun >= +10 deg:  -1.5  (Jupiter joins Venus; the classic daylight sighting)
 * The limit is never below -4.6 (a documented bound); Venus (mag -4.0) stays
 * inside it at every Sun altitude.
 */
import { limitingMagnitude } from './skyBrightness';
import type { MoonLight } from './moonlight';

/** Typical apparent magnitudes (not ephemeris values). */
export const PLANET_MAGNITUDES: Readonly<Record<string, number>> = {
  mercury: -0.4,
  venus: -4.0,
  mars: 0.7,
  jupiter: -2.2,
  saturn: 0.7,
  uranus: 5.7,
  neptune: 7.8,
  pluto: 14.2,
};

/** Planet limit for Sun 0..+10 deg: Venus only. */
export const DAY_PLANET_LIMIT_MAG = -3.0;
/** Planet limit for Sun >= +10 deg: Venus and Jupiter. */
export const HIGH_DAY_PLANET_LIMIT_MAG = -1.5;
/** The planet limit is never allowed below this value. */
export const PLANET_LIMIT_FLOOR_MAG = -4.6;

/**
 * The faintest planet magnitude treated as naked-eye visible now.
 * Night/twilight use the star limit (Moon penalty included); daylight uses the
 * more generous planet piecewise limit described above.
 */
export function planetLimitingMagnitude(sunAltDeg: number, moon?: MoonLight): number {
  const starLimit = limitingMagnitude(sunAltDeg, moon);
  let limit: number;
  if (!Number.isFinite(sunAltDeg) || sunAltDeg < 0) {
    limit = starLimit;
  } else if (sunAltDeg >= 10) {
    // Deliberate daylight planet limit (Venus + Jupiter), independent of the
    // star limit which is far stricter by day; this is the step at solar noon.
    limit = HIGH_DAY_PLANET_LIMIT_MAG;
  } else {
    // Venus only; Jupiter must wait for the Sun to climb past +10 deg.
    limit = DAY_PLANET_LIMIT_MAG;
  }
  return Math.max(limit, PLANET_LIMIT_FLOOR_MAG);
}

/** True when a planet of this (typical) magnitude is inside the naked-eye limit. */
export function planetVisible(magnitude: number, sunAltDeg: number, moon?: MoonLight): boolean {
  if (!Number.isFinite(magnitude)) return true; // unknown brightness: do not dim
  return magnitude <= planetLimitingMagnitude(sunAltDeg, moon);
}

/**
 * The dome's dimming decision: the Sun and Moon are never dimmed, the x-ray
 * view shows everything at full strength, and a planet beyond the limit is
 * drawn dimmed (but never hidden).
 */
export function isDimmedPlanet(
  id: string,
  magnitude: number | undefined,
  sunAltDeg: number,
  moon: MoonLight | undefined,
  seeThrough: boolean,
): boolean {
  if (id === 'sun' || id === 'moon') return false;
  if (seeThrough) return false;
  if (magnitude === undefined) return false;
  return !planetVisible(magnitude, sunAltDeg, moon);
}

/** "+7.8" / "-2.2" for the honesty notes. */
export function formatPlanetMagnitude(magnitude: number): string {
  const rounded = magnitude.toFixed(1);
  return magnitude >= 0 ? `+${rounded}` : rounded;
}
