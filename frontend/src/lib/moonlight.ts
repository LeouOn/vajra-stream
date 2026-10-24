/**
 * Earth & Sky wave 5 — moonlight (pure; no DOM, no randomness, deterministic).
 *
 * A high full Moon brightens the whole sky and washes the faint stars out; the dome used to draw the full night sky
 * under it. This module is the two numbers the dome needs, nothing more:
 *
 *  - `moonIlluminatedFraction`: how much of the Moon's disc is lit, from RA/Dec of the Sun and the Moon;
 *  - `moonlightPenaltyMag`: how many magnitudes the naked-eye limit falls because of it.
 *
 * Like the Sun model in `skyBrightness.ts`, the penalty is an APPROXIMATION from sightings, not a radiative-transfer
 * model, and it is continuous so the sky never pops as the Moon rises or the phase moves.
 */

/** The Moon as the sky-brightness model sees it: how high it is and how much of it is lit. */
export interface MoonLight {
  /** Altitude of the Moon's centre in degrees; at or below 0 it adds no light to the dome. */
  altDeg: number;
  /** Illuminated fraction of the disc, 0 (new) to 1 (full). */
  illuminatedFraction: number;
}

const RAD = Math.PI / 180;

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

/**
 * The illuminated fraction k = (1 - cos psi) / 2, psi being the great-circle angle between the Sun and the Moon
 * (the elongation). Written as the haversine of psi, which is the same number without the cancellation of
 * `1 - cos` for a small psi.
 *
 * Both live and scrubbed views can use it: the live `/night-sky` payload carries `right_ascension` and
 * `declination` for the Sun and the Moon, and the series gives sub-points from which `skySeries.ts` reconstructs
 * RA/Dec (use the geocentric ones: phase is a geocentric quantity, and the Moon's parallax moves psi by under a degree).
 *
 * What it ignores: the Moon's distance and the small phase-angle correction (the Sun is not infinitely far, so the
 * true phase angle is up to ~0.15 deg smaller than 180 deg - psi), and psi uses the Moon's ecliptic latitude where the
 * backend's `illumination_pct` does not. Measured against the backend's figure (ecliptic-longitude based) over June 2026
 * (6-hourly) and 61 days hourly, the largest difference is 0.23 percentage points (just after a new Moon, where the
 * Moon is up to 5 deg off the ecliptic); against swisseph's own phase-angle fraction it is 0.13. Far below anything the
 * eye or the penalty below can tell apart.
 *
 * Non-finite input gives NaN: garbage in stays visible instead of becoming a plausible phase.
 */
export function moonIlluminatedFraction(
  sunRaDeg: number,
  sunDecDeg: number,
  moonRaDeg: number,
  moonDecDeg: number,
): number {
  if (![sunRaDeg, sunDecDeg, moonRaDeg, moonDecDeg].every(Number.isFinite)) return Number.NaN;
  const sunDec = sunDecDeg * RAD;
  const moonDec = moonDecDeg * RAD;
  const haversine =
    Math.sin((moonDec - sunDec) / 2) ** 2 +
    Math.cos(sunDec) * Math.cos(moonDec) * Math.sin(((moonRaDeg - sunRaDeg) * RAD) / 2) ** 2;
  return clamp01(haversine);
}

/**
 * Magnitudes the naked-eye limiting magnitude falls under moonlight. Anchors (an APPROXIMATION from sightings):
 *
 *  - a full Moon high in the sky: 1.8 mag at the zenith, 1.75 at 60 deg, 1.5 at 30 deg (a dark-site limit of 6.5 falls
 *    to ~4.7-5.0);
 *  - a first or last quarter high: ~0.8 mag (0.7-1.0);
 *  - a thin crescent (<= 10 % lit): <= 0.15 mag;
 *  - a new Moon, or the Moon at or below the geometric horizon: exactly 0.
 *
 * The form is a product, each factor monotone:
 *
 *   penalty = 1.8 * altitudeFactor(alt) * k^1.1
 *
 * - the phase factor `k^1.1` (k the illuminated fraction): a little steeper than linear, so a quarter is ~47 % of a
 *   full Moon and a 10 % crescent ~8 %;
 * - the altitude factor is how much moonlight survives the air: the fraction of light transmitted along the path to
 *   the Moon, 10^(-0.4 * 0.2 * X) with X the Kasten & Young (1989) air mass and 0.2 mag per air mass a clear-site
 *   V-band extinction, minus the horizon value and rescaled so it is 0 at the horizon and 1 at the zenith. That
 *   gives the shape the sky shows: gradual just above the horizon (3 % at 2 deg, 18 % at 5 deg, 43 % at 10 deg, so
 *   a rising Moon does not pop), saturating high up (83 % at 30 deg, 90 % at 40 deg, 97 % at 60 deg).
 *
 * Not modelled: the angular distance between a star and the Moon (the glow is strongest near it), haze, a bright
 * city sky. A non-finite input is treated as no moonlight, the safe default of `limitingMagnitude`.
 */
export function moonlightPenaltyMag(moonAltDeg: number, illuminatedFraction: number): number {
  if (!Number.isFinite(moonAltDeg) || !Number.isFinite(illuminatedFraction)) return 0;
  if (moonAltDeg <= 0 || illuminatedFraction <= 0) return 0;
  const phase = Math.min(1, illuminatedFraction) ** PHASE_EXPONENT;
  return FULL_MOON_PENALTY_MAG * altitudeFactor(moonAltDeg) * phase;
}

/** Magnitudes lost under a full Moon at the zenith. */
const FULL_MOON_PENALTY_MAG = 1.8;
const PHASE_EXPONENT = 1.1;
/** V-band atmospheric extinction in magnitudes per air mass (clear site, 0.15-0.25). */
const EXTINCTION_MAG_PER_AIRMASS = 0.2;

/** Kasten & Young (1989) air mass for an apparent altitude in degrees (about 38 at the horizon, 1 at the zenith). */
function airMass(altDeg: number): number {
  return 1 / (Math.sin(altDeg * RAD) + 0.50572 * (altDeg + 6.07995) ** -1.6364);
}

function transmitted(altDeg: number): number {
  return 10 ** (-0.4 * EXTINCTION_MAG_PER_AIRMASS * airMass(altDeg));
}

const TRANSMITTED_AT_HORIZON = transmitted(0);
const TRANSMITTED_AT_ZENITH = transmitted(90);

/** 0 at the horizon, 1 at the zenith, increasing and saturating in between. */
function altitudeFactor(altDeg: number): number {
  const h = Math.min(90, Math.max(0, altDeg));
  const factor = (transmitted(h) - TRANSMITTED_AT_HORIZON) / (TRANSMITTED_AT_ZENITH - TRANSMITTED_AT_HORIZON);
  return Math.max(0, Math.min(1, factor));
}
