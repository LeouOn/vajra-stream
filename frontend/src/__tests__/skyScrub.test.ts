/**
 * W3-D2b — the pure scrub helpers.
 *
 * Fixtures are literals copied from the independent oracle
 * `docs/notes/earthsky/wave3/oracle/oracle_series.json` (equinox-2026, three
 * consecutive 600 s samples; never imported). Sacred-star live values are
 * literals from the repo's `core.celestial_sky.calculate_night_sky` at the same
 * instant/place (geocentric, GMST; the scrub path uses apparent GAST, whose
 * equation-of-the-equinoxes difference is < 0.005 deg).
 */
import { describe, expect, it } from 'vitest';
import {
  SCRUB_EDGE_MS,
  SCRUB_MAX_AGE_MS,
  SCRUB_SAMPLE_COUNT,
  SCRUB_STEP_SECONDS,
  SERIES_RANGE_END_MS,
  SERIES_RANGE_START_MS,
  localScrubLst,
  scrubWindow,
  shouldRefetchSeries,
  skyAtInstant,
} from '../lib/skyScrub';
import { bodiesAt, decodeSeries, horizontalOf, type SkySeries } from '../lib/skySeries';
import { julianDay, gmstDeg } from '../lib/sky';
import { parseInstant } from '../lib/skyClock';

const EQUINOX_THREE = [
  {"at":"2026-03-20T14:46:00+00:00","gast_deg":39.64937,"sun":{"id":"sun","lat":9.1e-05,"lon":-39.649388},"moon":{"id":"moon","lat":11.238252,"lon":-22.036433},"planets":[{"id":"mercury","lat":-7.425063,"lon":-59.916933},{"id":"venus","lat":6.096784,"lon":-23.101568},{"id":"mars","lat":-7.21454,"lon":-53.795934},{"id":"jupiter","lat":22.929005,"lon":66.92579},{"id":"saturn","lat":-0.308841,"lon":-35.018775},{"id":"uranus","lat":19.612297,"lon":16.450145},{"id":"neptune","lat":-0.493049,"lon":-37.502941},{"id":"pluto","lat":-22.80879,"lon":-91.270007}]},
  {"at":"2026-03-20T14:56:00+00:00","gast_deg":42.156215,"sun":{"id":"sun","lat":0.002837,"lon":-42.1499},"moon":{"id":"moon","lat":11.282281,"lon":-24.452152},"planets":[{"id":"mercury","lat":-7.426693,"lon":-62.423263},{"id":"venus","lat":6.100278,"lon":-25.60051},{"id":"mars","lat":-7.212421,"lon":-56.297709},{"id":"jupiter","lat":22.928987,"lon":64.419175},{"id":"saturn","lat":-0.308499,"lon":-37.524825},{"id":"uranus","lat":19.612355,"lon":13.943562},{"id":"neptune","lat":-0.492945,"lon":-40.009544},{"id":"pluto","lat":-22.808773,"lon":-93.776696}]},
  {"at":"2026-03-20T15:06:00+00:00","gast_deg":44.663059,"sun":{"id":"sun","lat":0.005583,"lon":-44.650411},"moon":{"id":"moon","lat":11.326286,"lon":-26.867837},"planets":[{"id":"mercury","lat":-7.428321,"lon":-64.929589},{"id":"venus","lat":6.103771,"lon":-28.099453},{"id":"mars","lat":-7.210302,"lon":-58.799484},{"id":"jupiter","lat":22.928968,"lon":61.91256},{"id":"saturn","lat":-0.308157,"lon":-40.030875},{"id":"uranus","lat":19.612413,"lon":11.436978},{"id":"neptune","lat":-0.492841,"lon":-42.516147},{"id":"pluto","lat":-22.808757,"lon":-96.283384}]},
];

function fixtureSeries(): SkySeries {
  return decodeSeries({
    ephemeris: 'swisseph 2.10.03',
    sidereal_time: 'apparent',
    start: EQUINOX_THREE[0].at,
    end: EQUINOX_THREE[2].at,
    step_seconds: 600,
    count: 3,
    samples: EQUINOX_THREE,
    provenance: { computed: 'computed' },
  });
}

const LAT = 37.7749;
const LNG = -122.4194;
// calculate_night_sky at 2026-03-20T14:46:00Z, (LAT,LNG), geocentric/GMST.
const LIVE_SACRED = {
  sirius: { altitude: -68.62, azimuth: 348.51 }, // alt < 0; still compare via separation
  vega: { altitude: 87.97, azimuth: 58.7 },
};
const SACRED_J2000 = [
  { id: 'sirius', ra_j2000: 101.287, dec_j2000: -16.716 },
  { id: 'vega', ra_j2000: 279.234, dec_j2000: 38.784 },
];

function separation(alt1: number, az1: number, alt2: number, az2: number): number {
  const rad = Math.PI / 180;
  const a1 = alt1 * rad;
  const a2 = alt2 * rad;
  const dz = Math.abs(((az1 - az2 + 540) % 360) - 180) * rad;
  const c = Math.sin(a1) * Math.sin(a2) + Math.cos(a1) * Math.cos(a2) * Math.cos(dz);
  return Math.acos(Math.min(1, Math.max(-1, c))) / rad;
}

describe('scrubWindow', () => {
  it('covers now-24 h to >= now+24 h at 603 s, 288 samples, on the grid', () => {
    const now = Date.UTC(2026, 9, 24, 9, 7, 42, 123); // includes seconds/ms
    const window = scrubWindow(now);
    expect(window.stepSeconds).toBe(603);
    expect(window.count).toBe(288);
    expect(window.startMs % 60_000).toBe(0); // whole minute
    expect(window.startMs).toBeLessThanOrEqual(now - 24 * 3600_000);
    expect(window.startIso).toBe(new Date(window.startMs).toISOString());
    expect(window.endIso).toBe(new Date(window.endMs).toISOString());
    expect(window.endMs - window.startMs).toBe((SCRUB_SAMPLE_COUNT - 1) * SCRUB_STEP_SECONDS * 1000);
    expect(window.endMs).toBeGreaterThanOrEqual(now + 24 * 3600_000);
    expect(window.endIso).toMatch(/Z$/);
  });

  it('centres on the shown instant when it is outside now +-24 h', () => {
    const now = Date.UTC(2026, 9, 24, 9, 0, 0);
    const shown = now + 30 * 3600_000; // a pause that drifted past the window
    const window = scrubWindow(now, shown);
    expect(window.startMs).toBe(Math.floor((shown - 24 * 3600_000) / 60_000) * 60_000);
    expect(window.endMs - window.startMs).toBe(287 * 603 * 1000);
    expect(window.startMs).toBeLessThanOrEqual(shown);
    expect(window.endMs).toBeGreaterThanOrEqual(shown);
  });

  it('clamps the window to the backend-supported 1800-2200 range, end on the grid', () => {
    const nearEnd = SERIES_RANGE_END_MS - 3600_000;
    const atEnd = scrubWindow(nearEnd, nearEnd);
    expect(atEnd.endMs).toBe(SERIES_RANGE_END_MS);
    expect(atEnd.endMs - atEnd.startMs).toBe(287 * 603 * 1000);
    expect(atEnd.startMs).toBeGreaterThanOrEqual(SERIES_RANGE_START_MS);

    const nearStart = SERIES_RANGE_START_MS + 3600_000;
    const atStart = scrubWindow(nearStart, nearStart);
    expect(atStart.startMs).toBe(SERIES_RANGE_START_MS);
    expect(atStart.endMs - atStart.startMs).toBe(287 * 603 * 1000);
  });
});

function wideSeries(): SkySeries {
  const start = parseInstant(EQUINOX_THREE[0].at);
  const samples = [0, 1, 2].map((index) => ({
    ...EQUINOX_THREE[0],
    at: new Date(start + index * 3600_000).toISOString(),
    gast_deg: (EQUINOX_THREE[0].gast_deg + index * 15.041) % 360,
  }));
  return decodeSeries({
    ephemeris: 'swisseph 2.10.03',
    sidereal_time: 'apparent',
    start: samples[0].at,
    end: samples[2].at,
    step_seconds: 3600,
    count: 3,
    samples,
    provenance: { computed: 'computed' },
  });
}

describe('shouldRefetchSeries', () => {
  const series = wideSeries();
  const first = series.samples[0].atMs;
  const last = series.samples[series.samples.length - 1].atMs;
  const now = Date.UTC(2026, 2, 20, 15, 0, 0);

  it('fetches when there is no series, it is old, or the instant is outside', () => {
    expect(shouldRefetchSeries(null, null, first, now)).toBe(true);
    expect(shouldRefetchSeries(series, now - SCRUB_MAX_AGE_MS - 1, first, now)).toBe(true);
    expect(shouldRefetchSeries(series, now, first - 1, now)).toBe(true);
    expect(shouldRefetchSeries(series, now, last + 1, now)).toBe(true);
  });

  it('never refetches for an instant outside the supported 1800-2200 range', () => {
    expect(shouldRefetchSeries(series, now, SERIES_RANGE_END_MS + 1, now)).toBe(false);
    expect(shouldRefetchSeries(series, now, SERIES_RANGE_START_MS - 1, now)).toBe(false);
  });

  it('fetches near either edge (30 min) but not in the middle when fresh', () => {
    expect(shouldRefetchSeries(series, now, first + SCRUB_EDGE_MS - 1, now)).toBe(true);
    expect(shouldRefetchSeries(series, now, last - SCRUB_EDGE_MS + 1, now)).toBe(true);
    expect(shouldRefetchSeries(series, now, first + SCRUB_EDGE_MS + 1, now)).toBe(false);
    expect(shouldRefetchSeries(series, now, last - SCRUB_EDGE_MS - 1, now)).toBe(false);
    expect(shouldRefetchSeries(series, now, (first + last) / 2, now)).toBe(false);
  });
});

describe('skyAtInstant', () => {
  it('derives GAST from the interpolated Sun and matches the series path', () => {
    const series = fixtureSeries();
    const atMs = parseInstant(EQUINOX_THREE[1].at);
    const sky = skyAtInstant(series, atMs, LAT, LNG, SACRED_J2000);

    // At a sample node the interpolation is exact, so GAST is the stored value.
    expect(sky.gast).toBeCloseTo(EQUINOX_THREE[1].gast_deg, 9);
    expect(sky.lst).toBeCloseTo((EQUINOX_THREE[1].gast_deg + LNG + 360) % 360, 9);

    const expected = bodiesAt(series, atMs);
    expect(sky.bodies.map((body) => body.id)).toEqual(expected.map((body) => body.id));
    for (const body of expected) {
      const fromSeries = horizontalOf(body, sky.gast, LAT, LNG);
      const got = sky.positions[body.id];
      expect(got.alt).toBeCloseTo(fromSeries.alt, 12);
      expect(got.az).toBeCloseTo(fromSeries.az, 12);
    }
    expect(sky.jd).toBeCloseTo(julianDay(new Date(atMs)), 12);
  });

  it('agrees with the live backend sacred-star positions within 0.02 deg', () => {
    const series = fixtureSeries();
    const atMs = parseInstant(EQUINOX_THREE[0].at);
    const sky = skyAtInstant(series, atMs, LAT, LNG, SACRED_J2000);
    expect(sky.sacredMissing).toBe(false);
    for (const position of sky.sacred) {
      const live = LIVE_SACRED[position.id as keyof typeof LIVE_SACRED];
      const sep = separation(position.alt, position.az, live.altitude, live.azimuth);
      expect(sep, position.id).toBeLessThanOrEqual(0.02);
    }
  });

  it('reports sacred stars missing (no stale positions) when J2000 coords are absent', () => {
    const series = fixtureSeries();
    const sky = skyAtInstant(series, parseInstant(EQUINOX_THREE[0].at), LAT, LNG, [
      { id: 'sirius' },
      { id: 'vega', ra_j2000: 279.234 },
    ]);
    expect(sky.sacredMissing).toBe(true);
    expect(sky.sacred).toEqual([]);
  });

  it('keeps the local GMST fallback within the equation-of-the-equinoxes bound', () => {
    const series = fixtureSeries();
    const atMs = parseInstant(EQUINOX_THREE[0].at);
    const sky = skyAtInstant(series, atMs, LAT, LNG, []);
    const local = localScrubLst(atMs, LNG);
    expect(local).toBeCloseTo((gmstDeg(sky.jd) + LNG + 720) % 360, 12);
    const delta = Math.abs(((sky.lst - local + 540) % 360) - 180);
    expect(delta).toBeLessThanOrEqual(0.02); // GAST vs GMST; measured ~0.005
  });
});
