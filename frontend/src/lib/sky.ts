/**
 * Earth & Sky wave 2 — the star-field maths behind the dome.
 *
 * Pure functions: no React, no three.js, no randomness (deterministic). Conventions from
 * docs/notes/earthsky/wave2/contract-w2.md:
 *  - star positions are J2000, precessed to date with the IAU 1976 (Lieske)
 *    precession angles only; proper motion, nutation and aberration are
 *    ignored (each below ~0.006° for 1800-2200 except a few fast stars);
 *  - azimuth is North 0°, East 90°, matching core/celestial_sky.py;
 *  - the dome projection is r = (90-alt)/90 * radius, x = cx - r sin(az),
 *    y = cy - r cos(az): zenith at the centre, north horizon at the top,
 *    east horizon on the LEFT.
 */

export interface Star {
  hr: number;
  ra: number;
  dec: number;
  v: number;
  bv: number | null;
}

export interface ConstellationLines {
  crosswalk: string;
  tolerance_arcsec: number;
  constellations: Record<string, number[][]>;
}

const RAD = Math.PI / 180;
const DEG = 180 / Math.PI;
const J2000 = 2451545.0;

/**
 * Decode and validate the star table. Besides types, every row must be a real
 * sky position and magnitude: RA in [0, 360), Dec in [-90, 90], and V in
 * [-2, 6.5]. The lower bound sits just below Sirius (V -1.46), the brightest
 * star; the upper bound is the product's own contract limit (the faded edge at
 * 6.5). A finite-but-impossible value (the probe [1, -5, 200, -100, null]) is
 * a TypeError naming the row index and the field, not a star.
 */
export function decodeStars(raw: unknown): Star[] {
  if (!Array.isArray(raw)) throw new TypeError('stars: payload must be an array');
  const stars: Star[] = [];
  for (let i = 0; i < raw.length; i += 1) {
    const row = raw[i];
    if (!Array.isArray(row) || row.length !== 5) {
      throw new TypeError(`stars[${i}]: expected [hr, ra, dec, vmag, bv]`);
    }
    const [hr, ra, dec, v, bv] = row;
    if (typeof hr !== 'number' || !Number.isInteger(hr) || hr < 1) {
      throw new TypeError(`stars[${i}]: hr must be a positive integer`);
    }
    for (const value of [ra, dec, v]) {
      if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new TypeError(`stars[${i}]: ra/dec/vmag must be finite numbers`);
      }
    }
    if (ra < 0 || ra >= 360) {
      throw new TypeError(`stars[${i}]: ra out of range [0, 360)`);
    }
    if (dec < -90 || dec > 90) {
      throw new TypeError(`stars[${i}]: dec out of range [-90, 90]`);
    }
    if (v < -2 || v > STAR_LIMIT_V) {
      throw new TypeError(`stars[${i}]: v out of range [-2, ${STAR_LIMIT_V}]`);
    }
    if (bv !== null && (typeof bv !== 'number' || !Number.isFinite(bv))) {
      throw new TypeError(`stars[${i}]: bv must be a number or null`);
    }
    stars.push({ hr, ra, dec, v, bv });
  }
  return stars;
}

export function julianDay(d: Date): number {
  // Meeus ch. 7 (UTC = UT here; sub-second accuracy is far beyond need).
  return d.getTime() / 86_400_000 + 2440587.5;
}

/**
 * Precess a J2000 position to (or from) the mean equinox of date using the
 * IAU 1976 precession angles (Lieske et al. 1977), T in Julian centuries
 * from J2000: zeta = 2306.2181"T + ...; z = 2306.2181"T + ...;
 * theta = 2004.3109"T - ...
 */
export function precessJ2000(ra: number, dec: number, jd: number): { ra: number; dec: number } {
  const t = (jd - J2000) / 36525.0;
  // The Lieske angles are published in arcseconds; they must enter the
  // rotation in DEGREES because ra is degrees. Only the trigonometry takes
  // radians. (Mixing the two here made precession ~57x too small: 0.3 deg
  // median error at 1800/2199 against the astropy oracle.)
  const zetaDeg = (2306.2181 * t + 0.30188 * t * t + 0.017998 * t * t * t) / 3600;
  const zDeg = (2306.2181 * t + 1.09468 * t * t + 0.018203 * t * t * t) / 3600;
  const thetaDeg = (2004.3109 * t - 0.42665 * t * t - 0.041833 * t * t * t) / 3600;

  const a = (ra + zetaDeg) * RAD;
  const d = dec * RAD;
  const theta = thetaDeg * RAD;
  // Explanatory Supplement rotation: a = alpha + zeta first, then rotate by
  // theta about the node and unwind by z (rigorous closed form; identity at
  // T = 0 for every ra, which the atan2-in-numerator variant is not).
  const sinDecOut = Math.min(1, Math.max(-1, Math.sin(d) * Math.cos(theta) + Math.cos(d) * Math.sin(theta) * Math.cos(a)));
  const decOut = Math.asin(sinDecOut);
  const numerator = Math.cos(d) * Math.sin(a);
  const denominator = Math.cos(theta) * Math.cos(d) * Math.cos(a) - Math.sin(theta) * Math.sin(d);
  const raOut = zDeg + Math.atan2(numerator, denominator) * DEG;
  return { ra: ((raOut % 360) + 360) % 360, dec: decOut * DEG };
}

/**
 * Greenwich mean sidereal time, IAU 1982 polynomial, degrees in [0, 360).
 *
 * Meeus, *Astronomical Algorithms* ch. 12 (12.4), in hours:
 *   18.697374558 + 24.06570982441908 D + 0.0000258622 T^2 - 1.7222e-9 T^3
 * where D = JD - 2451545.0 (days) and T = D / 36525 (Julian centuries from
 * J2000). In degrees the same polynomial is
 *   280.46061837 + 360.98564736629 D + 0.000387933 T^2 - T^3 / 38710000.
 * (This used to carry a T^4 term instead of the T^2 term, ~0.0054 deg at
 * 2199; the J2000 anchor and the day rate are unchanged.)
 */
export function gmstDeg(jd: number): number {
  const d = jd - J2000;
  const t = d / 36525.0;
  // 18.697374558 h is GMST at the J2000.0 epoch itself (JD 2451545.0, noon);
  // the day rate 24.06570982441908 h/day is 1.00273790935 x 24.
  let gmstHours =
    18.697374558 + 24.06570982441908 * d + 0.0000258622 * t * t - 1.7222e-9 * t * t * t;
  gmstHours %= 24;
  if (gmstHours < 0) gmstHours += 24;
  return (gmstHours * 15) % 360;
}

/**
 * Equatorial -> horizontal for an observer. Same formulas as
 * core/celestial_sky.py::_equatorial_to_horizontal: az from North through
 * East (atan2(-cos(dec) sin(H), sin(dec) cos(lat) - cos(dec) sin(lat) cos(H))).
 */
export function equatorialToHorizontal(
  raDeg: number,
  decDeg: number,
  lstDeg: number,
  latDeg: number,
): { alt: number; az: number } {
  const h = ((lstDeg - raDeg) % 360) * RAD;
  const dec = decDeg * RAD;
  const lat = latDeg * RAD;
  const sinAlt = Math.sin(dec) * Math.sin(lat) + Math.cos(dec) * Math.cos(lat) * Math.cos(h);
  const alt = Math.asin(Math.min(1, Math.max(-1, sinAlt))) * DEG;
  const y = -Math.cos(dec) * Math.sin(h);
  const x = Math.sin(dec) * Math.cos(lat) - Math.cos(dec) * Math.sin(lat) * Math.cos(h);
  const az = (Math.atan2(y, x) * DEG + 360) % 360;
  return { alt, az };
}

/** The dome's existing convention: r=(90-alt)/90*radius, x=cx-r*sin(az), y=cy-r*cos(az). */
export function domePoint(
  alt: number,
  az: number,
  radiusPx: number,
  cx: number,
  cy: number,
): { x: number; y: number } {
  const r = ((90 - alt) / 90) * radiusPx;
  return { x: cx - r * Math.sin(az * RAD), y: cy - r * Math.cos(az * RAD) };
}

export const STAR_LIMIT_V = 6.5;
export const STAR_FADE_V = 6.0;

/**
 * 1 for v <= 6.0, falling linearly to 0 at 6.5, 0 above (the faded edge).
 * A non-finite magnitude is not a measurement: treat it as invisible (0) so
 * NaN cannot reach the canvas (a NaN globalAlpha/arc is rejected at draw).
 */
export function starAlpha(v: number): number {
  if (!Number.isFinite(v)) return 0;
  if (v <= STAR_FADE_V) return 1;
  if (v >= STAR_LIMIT_V) return 0;
  return (STAR_LIMIT_V - v) / (STAR_LIMIT_V - STAR_FADE_V);
}

/**
 * Radius in px: monotone non-increasing in magnitude, sub-pixel when faint.
 * A non-finite magnitude uses the faint floor (0.4 px) rather than NaN.
 */
export function starRadiusPx(v: number): number {
  if (!Number.isFinite(v)) return 0.4;
  // 1.6 px at the brightest (Sirius -1.46) falling to 0.4 px at the limit:
  // radius = 0.4 + 1.2 * (STAR_LIMIT_V - v) / (STAR_LIMIT_V + 1.6), clamped.
  const span = STAR_LIMIT_V + 1.6;
  const r = 0.4 + (1.2 * (STAR_LIMIT_V - v)) / span;
  return Math.max(0.4, Math.min(1.6, r));
}

/**
 * B-V colour, with the two formulas named: B-V -> effective temperature via
 * F. Ballesteros' closed form (arXiv:1201.1809): T = 4600 *
 * (1/(0.92*BV + 1.7) + 1/(0.92*BV + 0.62)); then temperature -> sRGB with
 * Tanner Helland's black-body approximation (the piecewise 1998-2012
 * colour-temperature curves used by many star-chart tools). Smooth and
 * monotone: blue-white (BV < 0) .. white (~0.4) .. yellow (~0.8) ..
 * orange-red (> 1.5). A null B-V is neutral white.
 */
export function starRgb(bv: number | null): [number, number, number] {
  if (bv === null) return [255, 255, 255];
  const bvClamped = Math.max(-0.4, Math.min(2.0, bv));
  const kelvin = 4600 * (1 / (0.92 * bvClamped + 1.7) + 1 / (0.92 * bvClamped + 0.62));
  // Tanner Helland's temperature -> RGB (Kelvin clamped to his 1000-40000 K
  // working range).
  const t = Math.max(1000, Math.min(40000, kelvin)) / 100;
  let r: number;
  let g: number;
  let b: number;
  if (t <= 66) {
    r = 255;
    g = 99.4708025861 * Math.log(t) - 161.1195681661;
  } else {
    r = 329.698727446 * (t - 60) ** -0.1332047592;
    g = 288.1221695283 * (t - 60) ** -0.0755148492;
  }
  if (t >= 66) {
    b = 255;
  } else if (t <= 19) {
    b = 0;
  } else {
    b = 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  }
  const clamp = (x: number) => Math.max(0, Math.min(255, Math.round(x)));
  return [clamp(r), clamp(g), clamp(b)];
}

/** Mean obliquity of the ecliptic, IAU 1976 polynomial (degrees). */
function meanObliquityDeg(jd: number): number {
  const t = (jd - J2000) / 36525.0;
  return 23.439291111 - (46.815 * t + 0.00059 * t * t - 0.001813 * t * t * t) / 3600;
}

/**
 * The ecliptic of date sampled in equatorial coordinates: for ecliptic
 * longitude lambda in [0, 360), alpha = atan2(sin(lambda) cos(eps),
 * cos(lambda)), delta = asin(sin(eps) sin(lambda)), with eps from the IAU
 * 1976 mean-obliquity polynomial.
 */
export function eclipticPoints(jd: number, segments = 360): { ra: number; dec: number }[] {
  const eps = meanObliquityDeg(jd) * RAD;
  const points: { ra: number; dec: number }[] = [];
  for (let i = 0; i < segments; i += 1) {
    const lam = ((360 * i) / segments) * RAD;
    const ra = (Math.atan2(Math.sin(lam) * Math.cos(eps), Math.cos(lam)) * DEG + 360) % 360;
    const dec = Math.asin(Math.sin(eps) * Math.sin(lam)) * DEG;
    points.push({ ra, dec });
  }
  return points;
}

/**
 * Resolve constellation polylines to Star records; unresolved HR ids are
 * dropped from the polyline and counted in `droppedHr` on the returned
 * group (the caller sums them for the footer honesty note).
 */
export function constellationSegments(
  lines: ConstellationLines,
  byHr: Map<number, Star>,
): { name: string; polylines: Star[][]; droppedHr: number }[] {
  const out: { name: string; polylines: Star[][]; droppedHr: number }[] = [];
  for (const name of Object.keys(lines.constellations).sort()) {
    const polylines: Star[][] = [];
    let dropped = 0;
    for (const polyline of lines.constellations[name]) {
      const stars: Star[] = [];
      for (const hr of polyline) {
        const star = byHr.get(hr);
        if (star === undefined) dropped += 1;
        else stars.push(star);
      }
      if (stars.length >= 2) polylines.push(stars);
    }
    out.push({ name, polylines, droppedHr: dropped });
  }
  return out;
}

/** Lazy loaders: dynamic imports so Vite splits each file into its own chunk. */
export async function loadStars(): Promise<Star[]> {
  const mod = (await import('../data/stars-v65.json')) as unknown as { default?: unknown };
  return decodeStars(mod.default ?? mod);
}

export async function loadConstellationLines(): Promise<ConstellationLines> {
  const mod = (await import('../data/constellation-lines.json')) as unknown as {
    default?: ConstellationLines;
  };
  return (mod.default ?? mod) as ConstellationLines;
}
