/**
 * Earth & Sky wave 3 — pure scrub helpers (row W3-D2b).
 *
 * One series covers the whole +-24 h scrub range. This module owns the window
 * arithmetic, the refetch rule, and the assembly of "where are the bodies at
 * instant T": apparent GAST from the series, RA/Dec for the sub-points, and
 * horizontal coordinates for the observer. No React, no network, no timers.
 */
import {
  equatorialToHorizontal,
  gmstDeg,
  julianDay,
  precessJ2000,
} from './sky';
import {
  bodiesAt,
  horizontalOf,
  type InterpolatedBody,
  type SkySeries,
} from './skySeries';

/** The scrub series step (a fencepost so 288 samples stay inside the cap). */
export const SCRUB_STEP_SECONDS = 603;
/** Both ends included: (288 - 1) * 603 s covers 48 h 4 m 21 s. */
export const SCRUB_SAMPLE_COUNT = 288;
/** Refetch when the shown instant is this close to either window edge. */
export const SCRUB_EDGE_MS = 30 * 60_000;
/** Refetch when the fetched window is older than this. */
export const SCRUB_MAX_AGE_MS = 30 * 60_000;

const MINUTE_MS = 60_000;
const HALF_DAY_MS = 24 * 3600_000;
const WINDOW_SPAN_MS = (SCRUB_SAMPLE_COUNT - 1) * SCRUB_STEP_SECONDS * 1000;

/** The backend's supported ephemeris range (core/earth_sky.py). */
export const SERIES_RANGE_START_MS = Date.UTC(1800, 0, 1);
export const SERIES_RANGE_END_MS = Date.UTC(2200, 11, 31, 23, 59, 59);

export interface ScrubWindow {
  startMs: number;
  endMs: number;
  startIso: string;
  endIso: string;
  stepSeconds: number;
  count: number;
}

/**
 * The window to request: normally real now - 24 h, rounded DOWN to a whole
 * minute, then 288 samples at 603 s. When the shown instant is outside
 * [now - 24 h, now + 24 h] (a pause that has drifted out of the fetched
 * window), the window is centred on that instant instead, so a long-paused
 * dashboard keeps its planets. The window is clamped to the backend's
 * supported range; the end always sits on the 603 s grid.
 */
export function scrubWindow(nowMs: number, shownMs?: number): ScrubWindow {
  const anchor =
    shownMs !== undefined && (shownMs < nowMs - HALF_DAY_MS || shownMs > nowMs + HALF_DAY_MS)
      ? shownMs
      : nowMs;
  let startMs = Math.floor((anchor - HALF_DAY_MS) / MINUTE_MS) * MINUTE_MS;
  if (startMs + WINDOW_SPAN_MS > SERIES_RANGE_END_MS) startMs = SERIES_RANGE_END_MS - WINDOW_SPAN_MS;
  if (startMs < SERIES_RANGE_START_MS) startMs = SERIES_RANGE_START_MS;
  const endMs = startMs + WINDOW_SPAN_MS;
  return {
    startMs,
    endMs,
    startIso: new Date(startMs).toISOString(),
    endIso: new Date(endMs).toISOString(),
    stepSeconds: SCRUB_STEP_SECONDS,
    count: SCRUB_SAMPLE_COUNT,
  };
}

/**
 * True when the cached series must be replaced: none yet, older than 30 min,
 * the instant is outside it, or within 30 min of either edge.
 */
export function shouldRefetchSeries(
  series: SkySeries | null,
  fetchedAtMs: number | null,
  shownMs: number,
  nowMs: number,
): boolean {
  // No window can cover an instant outside the backend's supported range;
  // asking again every 30 min would only re-download the same nothing.
  if (shownMs < SERIES_RANGE_START_MS || shownMs > SERIES_RANGE_END_MS) return false;
  if (series === null || fetchedAtMs === null) return true;
  if (nowMs - fetchedAtMs > SCRUB_MAX_AGE_MS) return true;
  const first = series.samples[0].atMs;
  const last = series.samples[series.samples.length - 1].atMs;
  if (shownMs < first || shownMs > last) return true;
  return shownMs - first <= SCRUB_EDGE_MS || last - shownMs <= SCRUB_EDGE_MS;
}

export interface SacredInput {
  id: string;
  ra_j2000?: number;
  dec_j2000?: number;
}

export interface SacredPosition {
  id: string;
  alt: number;
  az: number;
}

export interface SacredResult {
  positions: SacredPosition[];
  /** True when at least one sacred star had no J2000 coordinates to use. */
  missing: boolean;
}

export interface ScrubbedSky {
  instantMs: number;
  /** Interpolated apparent GAST, degrees [0, 360). */
  gast: number;
  /** Local sidereal time = GAST + observer longitude (east positive). */
  lst: number;
  /** Julian day of the instant (for precession / the star layer). */
  jd: number;
  bodies: InterpolatedBody[];
  /** Alt/az by body id (sun, moon, the eight planets). */
  positions: Record<string, { alt: number; az: number }>;
  sacred: SacredPosition[];
  sacredMissing: boolean;
}

function wrap360(deg: number): number {
  const wrapped = deg % 360;
  return wrapped < 0 ? wrapped + 360 : wrapped;
}

/** Precess J2000 sacred-star coordinates to the date and make them horizontal. */
export function sacredHorizontal(
  sacred: readonly SacredInput[],
  lst: number,
  observerLat: number,
  jd: number,
): SacredResult {
  const positions: SacredPosition[] = [];
  let missing = false;
  for (const star of sacred) {
    if (star.ra_j2000 === undefined || star.dec_j2000 === undefined) {
      missing = true;
      continue;
    }
    const ofDate = precessJ2000(star.ra_j2000, star.dec_j2000, jd);
    const horizontal = equatorialToHorizontal(ofDate.ra, ofDate.dec, lst, observerLat);
    positions.push({ id: star.id, alt: horizontal.alt, az: horizontal.az });
  }
  return { positions, missing };
}

/**
 * Fallback LST when the series is unavailable: mean sidereal time, not the
 * apparent GAST the series ships. The two differ by the equation of the
 * equinoxes, measured here below 0.005 deg over the supported range — far
 * inside a star's drawn size — so the catalogue still rotates honestly.
 */
export function localScrubLst(instantMs: number, observerLng: number): number {
  return wrap360(gmstDeg(julianDay(new Date(instantMs))) + observerLng);
}

/**
 * The sky at `instantMs` from the series: Sun/Moon/planets by interpolation,
 * stars/sacred stars by precession, all for one observer.
 */
export function skyAtInstant(
  series: SkySeries,
  instantMs: number,
  observerLat: number,
  observerLng: number,
  sacred: readonly SacredInput[],
): ScrubbedSky {
  const bodies = bodiesAt(series, instantMs);
  const sun = bodies.find((body) => body.id === 'sun');
  if (!sun) throw new RangeError('skyScrub: the series has no Sun');
  // RA = wrap360(lon + gast) for every body, so the Sun recovers GAST exactly.
  const gast = wrap360(sun.ra - sun.lon);
  const lst = wrap360(gast + observerLng);
  const jd = julianDay(new Date(instantMs));

  const positions: Record<string, { alt: number; az: number }> = {};
  for (const body of bodies) {
    positions[body.id] = horizontalOf(body, gast, observerLat, observerLng);
  }

  const sacredResult = sacredHorizontal(sacred, lst, observerLat, jd);
  return {
    instantMs,
    gast,
    lst,
    jd,
    bodies,
    positions,
    sacred: sacredResult.positions,
    sacredMissing: sacredResult.missing,
  };
}
