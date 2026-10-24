/**
 * W3-I tests for stores/skySeriesStore.ts: the one shared owner of the fetched series window, and the pure
 * builder that turns a series into an EarthState for a scrubbed instant.
 *
 * Accuracy tests use LITERALS copied from the frozen independent swisseph oracle
 * docs/notes/earthsky/wave3/oracle/oracle_series.json (W3-O; the JSON is never imported). Behaviour tests use a
 * synthetic 288-sample series, because a three-sample literal window is entirely "near an edge".
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/earthSeriesClient', async () => {
  const actual = await vi.importActual<typeof import('../lib/earthSeriesClient')>('../lib/earthSeriesClient');
  return { ...actual, fetchSeries: vi.fn(), cancelSeriesRequest: vi.fn() };
});

import { drawnBodies } from '../components/3D/worldEmanationHelpers';
import { shownNowMs } from '../lib/earth';
import { EarthSeriesError, cancelSeriesRequest, fetchSeries } from '../lib/earthSeriesClient';
import { parseInstant } from '../lib/skyClock';
import { scrubWindow } from '../lib/skyScrub';
import { decodeSeries, type SkySeries } from '../lib/skySeries';
import {
  resetSkySeriesStore,
  scrubbedEarthState,
  useSkySeriesStore,
} from '../stores/skySeriesStore';
import { useSkyStore } from '../stores/skyStore';

const fetchMock = vi.mocked(fetchSeries);
const cancelMock = vi.mocked(cancelSeriesRequest);

const BODY_IDS = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];
const PLANET_IDS = BODY_IDS.slice(2);
const wrap180 = (value: number) => ((((value + 180) % 360) + 360) % 360) - 180;
const wrap360 = (value: number) => ((value % 360) + 360) % 360;
const angdiff = (a: number, b: number) => Math.abs(wrap180(a - b));

// ----------------------------------------------------------------------------------------------- oracle rows
type OracleRow = [string, number, Record<string, [number, number]>];

// Moon crossing the +-180 longitude seam: oracle samples 78, 79, 80 of moon-seam-day (600 s apart).
// Series = rows 0 and 2 (1200 s apart); row 1 is the truth at the instant between them.
const SEAM_ROWS: OracleRow[] = [
  ['2026-07-01T13:00:00Z', 114.599039, { sun: [23.081821, -14.024752], moon: [-23.626045, -175.252277], mercury: [18.321737, 3.012115], venus: [16.227267, 29.185088], mars: [20.261493, -54.688897], jupiter: [20.519525, 7.971203], saturn: [3.403886, -100.594226], uranus: [20.743423, -52.841498], neptune: [0.497346, -110.010853], pluto: [-23.145667, -166.283528] }],
  ['2026-07-01T13:10:00Z', 117.105884, { sun: [23.081338, -16.524421], moon: [-23.603698, -177.671187], mercury: [18.320128, 0.503924], venus: [16.22454, 26.685926], mars: [20.262558, -57.190605], jupiter: [20.519214, 5.465913], saturn: [3.40397, -103.100788], uranus: [20.743489, -55.34798], neptune: [0.497349, -112.517675], pluto: [-23.145717, -168.790519] }],
  ['2026-07-01T13:20:00Z', 119.612729, { sun: [23.080854, -19.024089], moon: [-23.581301, 179.90988], mercury: [18.318519, -2.00427], venus: [16.221813, 24.186765], mars: [20.263623, -59.692313], jupiter: [20.518902, 2.960623], saturn: [3.404055, -105.607351], uranus: [20.743554, -57.854462], neptune: [0.497353, -115.024497], pluto: [-23.145768, -171.297511] }],
];

// Sun right ascension wrapping 360 -> 0: oracle samples 0..4 of equinox-2026. Series = rows 0, 2, 4;
// rows 1 and 3 are the truths between them.
const EQUINOX_ROWS: OracleRow[] = [
  ['2026-03-20T14:46:00Z', 39.64937, { sun: [9.1e-05, -39.649388], moon: [11.238252, -22.036433], mercury: [-7.425063, -59.916933], venus: [6.096784, -23.101568], mars: [-7.21454, -53.795934], jupiter: [22.929005, 66.92579], saturn: [-0.308841, -35.018775], uranus: [19.612297, 16.450145], neptune: [-0.493049, -37.502941], pluto: [-22.80879, -91.270007] }],
  ['2026-03-20T14:56:00Z', 42.156215, { sun: [0.002837, -42.1499], moon: [11.282281, -24.452152], mercury: [-7.426693, -62.423263], venus: [6.100278, -25.60051], mars: [-7.212421, -56.297709], jupiter: [22.928987, 64.419175], saturn: [-0.308499, -37.524825], uranus: [19.612355, 13.943562], neptune: [-0.492945, -40.009544], pluto: [-22.808773, -93.776696] }],
  ['2026-03-20T15:06:00Z', 44.663059, { sun: [0.005583, -44.650411], moon: [11.326286, -26.867837], mercury: [-7.428321, -64.929589], venus: [6.103771, -28.099453], mars: [-7.210302, -58.799484], jupiter: [22.928968, 61.91256], saturn: [-0.308157, -40.030875], uranus: [19.612413, 11.436978], neptune: [-0.492841, -42.516147], pluto: [-22.808757, -96.283384] }],
  ['2026-03-20T15:16:00Z', 47.169904, { sun: [0.008328, -47.150922], moon: [11.370266, -29.283487], mercury: [-7.429947, -67.43591], venus: [6.107265, -30.598395], mars: [-7.208182, -61.301259], jupiter: [22.928949, 59.405946], saturn: [-0.307814, -42.536925], uranus: [19.612471, 8.930395], neptune: [-0.492737, -45.022749], pluto: [-22.808741, -98.790072] }],
  ['2026-03-20T15:26:00Z', 49.676748, { sun: [0.011074, -49.651434], moon: [11.414221, -31.699103], mercury: [-7.431571, -69.942227], venus: [6.110758, -33.097337], mars: [-7.206063, -63.803035], jupiter: [22.928931, 56.899331], saturn: [-0.307472, -45.042975], uranus: [19.612529, 6.423811], neptune: [-0.492633, -47.529352], pluto: [-22.808724, -101.296761] }],
];

function seriesFromRows(rows: OracleRow[], stepSeconds: number): SkySeries {
  const samples = rows.map(([at, gast, bodies]) => ({
    at,
    gast_deg: gast,
    sun: { id: 'sun', lat: bodies.sun[0], lon: bodies.sun[1] },
    moon: { id: 'moon', lat: bodies.moon[0], lon: bodies.moon[1] },
    planets: PLANET_IDS.map((id) => ({ id, lat: bodies[id][0], lon: bodies[id][1] })),
  }));
  return decodeSeries({
    ephemeris: 'swisseph',
    sidereal_time: 'apparent',
    start: samples[0].at,
    end: samples[samples.length - 1].at,
    step_seconds: stepSeconds,
    count: samples.length,
    samples,
    provenance: {},
  });
}

/** 288 samples at 603 s with smooth fake motion; enough for behaviour tests, never used for accuracy. */
function syntheticSeries(startIso: string, endIso: string, stepSeconds: number): SkySeries {
  const start = Date.parse(startIso);
  const count = Math.round((Date.parse(endIso) - start) / (stepSeconds * 1000)) + 1;
  const body = (id: string, i: number) => ({ id, lat: 10 + (i % 5) * 0.1, lon: wrap180(-40 - i * 0.6) });
  const samples = Array.from({ length: count }, (_, i) => ({
    at: new Date(start + i * stepSeconds * 1000).toISOString(),
    gast_deg: wrap360(30 + i * 2.5),
    sun: body('sun', i),
    moon: body('moon', i),
    planets: PLANET_IDS.map((id) => body(id, i)),
  }));
  return decodeSeries({
    ephemeris: 'swisseph',
    sidereal_time: 'apparent',
    start: samples[0].at,
    end: samples[count - 1].at,
    step_seconds: stepSeconds,
    count,
    samples,
    provenance: {},
  });
}

// --------------------------------------------------------------------------------- scrubbedEarthState
describe('scrubbedEarthState: an EarthState for a scrubbed instant, from series sub-points', () => {
  const TOLERANCE = 5e-5;

  function checkAgainstTruth(state: NonNullable<ReturnType<typeof scrubbedEarthState>>, truth: OracleRow) {
    const [, gast, bodies] = truth;
    expect(angdiff(state.gast_deg, gast)).toBeLessThanOrEqual(TOLERANCE);
    const got = [state.sun, state.moon, ...state.planets];
    expect(got.map((body) => body.id)).toEqual(BODY_IDS);
    for (const body of got) {
      const [lat, lon] = bodies[body.id];
      expect(Math.abs(body.lat - lat), `${body.id} lat`).toBeLessThanOrEqual(TOLERANCE);
      expect(angdiff(body.lon, lon), `${body.id} lon`).toBeLessThanOrEqual(TOLERANCE);
      // the documented relation: dec = lat, ra = wrap360(lon + gast), checked against the oracle's own numbers
      expect(Math.abs(body.dec_deg - lat), `${body.id} dec`).toBeLessThanOrEqual(TOLERANCE);
      expect(angdiff(body.ra_deg, wrap360(lon + gast)), `${body.id} ra`).toBeLessThanOrEqual(TOLERANCE);
    }
  }

  it('Moon straddling the +-180 longitude seam, at the instant between two samples', () => {
    const series = seriesFromRows([SEAM_ROWS[0], SEAM_ROWS[2]], 1200);
    const state = scrubbedEarthState(series, parseInstant(SEAM_ROWS[1][0]));
    expect(state).not.toBeNull();
    // the two neighbours really are on opposite sides of the seam (plain averaging would be ~180 deg out)
    expect(SEAM_ROWS[0][2].moon[1]).toBeLessThan(-170);
    expect(SEAM_ROWS[2][2].moon[1]).toBeGreaterThan(170);
    checkAgainstTruth(state!, SEAM_ROWS[1]);
  });

  it('Sun right ascension wrapping 360 -> 0, at both instants between three samples', () => {
    const series = seriesFromRows([EQUINOX_ROWS[0], EQUINOX_ROWS[2], EQUINOX_ROWS[4]], 1200);
    for (const index of [1, 3]) {
      const state = scrubbedEarthState(series, parseInstant(EQUINOX_ROWS[index][0]));
      expect(state).not.toBeNull();
      checkAgainstTruth(state!, EQUINOX_ROWS[index]);
    }
    const first = scrubbedEarthState(series, parseInstant(EQUINOX_ROWS[0][0]))!;
    expect(first.sun.ra_deg).toBeGreaterThan(359.99); // 359.99998: the wrap is real in this window
  });

  it('is exact at a sample instant', () => {
    const series = seriesFromRows([EQUINOX_ROWS[0], EQUINOX_ROWS[2], EQUINOX_ROWS[4]], 1200);
    const state = scrubbedEarthState(series, parseInstant(EQUINOX_ROWS[2][0]))!;
    expect(angdiff(state.gast_deg, EQUINOX_ROWS[2][1])).toBeLessThan(1e-9);
    expect(state.moon.lat).toBeCloseTo(EQUINOX_ROWS[2][2].moon[0], 9);
  });

  it('fills the whole EarthState shape the globes read', () => {
    const series = seriesFromRows([EQUINOX_ROWS[0], EQUINOX_ROWS[2]], 1200);
    const shown = parseInstant(EQUINOX_ROWS[1][0]);
    const state = scrubbedEarthState(series, shown)!;
    expect(state.at).toBe(new Date(shown).toISOString());
    expect(state.ephemeris).toBe('swisseph');
    expect(state.sun.name).toBe('Sun');
    expect(state.moon.name).toBe('Moon');
    expect(state.planets.map((planet) => planet.name)).toEqual([
      'Mercury',
      'Venus',
      'Mars',
      'Jupiter',
      'Saturn',
      'Uranus',
      'Neptune',
      'Pluto',
    ]);
    expect(Object.values(state.provenance).every((kind) => kind === 'computed')).toBe(true);
    expect(state.gast_deg).toBeGreaterThanOrEqual(0);
    expect(state.gast_deg).toBeLessThan(360);
  });

  it('is null (never an extrapolation) outside the series window', () => {
    const series = seriesFromRows([EQUINOX_ROWS[0], EQUINOX_ROWS[2]], 1200);
    expect(scrubbedEarthState(series, parseInstant(EQUINOX_ROWS[0][0]) - 1000)).toBeNull();
    expect(scrubbedEarthState(series, parseInstant(EQUINOX_ROWS[2][0]) + 1000)).toBeNull();
    expect(scrubbedEarthState(series, Number.NaN)).toBeNull();
  });
});

// ------------------------------------------------------------------------------------ frozen = no drift
describe('shownNowMs: a scrubbed state does not drift with the wall clock', () => {
  const series = seriesFromRows([EQUINOX_ROWS[0], EQUINOX_ROWS[2], EQUINOX_ROWS[4]], 1200);
  const shown = parseInstant(EQUINOX_ROWS[1][0]);
  const state = scrubbedEarthState(series, shown)!;
  const frozen = { frozen: true, fetchedAt: shown };
  const live = { fetchedAt: shown };

  it('returns the wall clock for a live slice and the shown instant for a frozen one', () => {
    expect(shownNowMs(live, 5_000_000)).toBe(5_000_000);
    expect(shownNowMs({ frozen: false, fetchedAt: shown }, 5_000_000)).toBe(5_000_000);
    expect(shownNowMs(frozen, 5_000_000)).toBe(shown);
    expect(shownNowMs({ frozen: true, fetchedAt: null }, 5_000_000)).toBe(5_000_000);
  });

  it('draws the same positions 60 s apart when frozen, and drifts 0.25 deg when live', () => {
    const t0 = shown + 123_000;
    const frozenA = drawnBodies(state, shown, shownNowMs(frozen, t0));
    const frozenB = drawnBodies(state, shown, shownNowMs(frozen, t0 + 60_000));
    expect(frozenB).toEqual(frozenA);
    const liveA = drawnBodies(state, shown, shownNowMs(live, t0));
    const liveB = drawnBodies(state, shown, shownNowMs(live, t0 + 60_000));
    const sunA = liveA.find((body) => body.id === 'sun')!;
    const sunB = liveB.find((body) => body.id === 'sun')!;
    expect(angdiff(sunA.lon, sunB.lon)).toBeCloseTo((360.9856 / 86400) * 60, 6);
  });
});

// ------------------------------------------------------------------------------------------ the store
const NOW = '2026-10-24T09:00:00.000Z';
const NOW_MS = Date.parse(NOW);
const SCRUB_A = '2026-10-24T11:00:00Z';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
const flush = () => vi.advanceTimersByTimeAsync(0);
const store = () => useSkySeriesStore.getState();
const subscribe = () => store().subscribe();
const scrubTo = (iso: string) => useSkyStore.getState().setAt(iso);

/** The arguments the store should pass to fetchSeries for a shown instant at NOW. */
function windowArgs(shownIso: string): [string, string, number] {
  const win = scrubWindow(NOW_MS, Date.parse(shownIso));
  return [win.startIso, win.endIso, win.stepSeconds];
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(NOW));
  fetchMock.mockReset();
  cancelMock.mockReset();
  fetchMock.mockImplementation((start, end, step) => Promise.resolve(syntheticSeries(start, end, step)));
  resetSkySeriesStore();
  useSkyStore.setState({ at: null });
});

afterEach(() => {
  resetSkySeriesStore();
  useSkyStore.setState({ at: null });
  vi.useRealTimers();
});

describe('skySeriesStore: when it fetches', () => {
  it('makes no request while the sky is live, even with subscribers', async () => {
    const unsubscribe = subscribe();
    await flush();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(store().status).toBe('idle');
    unsubscribe();
  });

  it('makes no request while scrubbed if nobody is subscribed', async () => {
    scrubTo(SCRUB_A);
    await flush();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('requests the window scrubWindow gives, once, and holds the decoded series', async () => {
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    expect(store().status).toBe('loading');
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(...windowArgs(SCRUB_A));
    expect(store().status).toBe('ready');
    expect(store().series?.count).toBe(288);
    unsubscribe();
  });

  it('three subscribers produce ONE request', async () => {
    const unsubscribers = [subscribe(), subscribe(), subscribe()];
    scrubTo(SCRUB_A);
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    unsubscribers.push(subscribe()); // a fourth one arriving later: the window is held
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    unsubscribers.forEach((unsubscribe) => unsubscribe());
  });

  it('subscribers that arrive after the scrub began share the in-flight request', async () => {
    const pending = deferred<SkySeries>();
    fetchMock.mockReturnValue(pending.promise);
    scrubTo(SCRUB_A);
    const a = subscribe();
    const b = subscribe();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    pending.resolve(syntheticSeries(...windowArgs(SCRUB_A)));
    await flush();
    expect(store().status).toBe('ready');
    a();
    b();
  });

  it('does not ask again while the scrub moves inside the held window', async () => {
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush();
    for (const iso of ['2026-10-24T13:00:00Z', '2026-10-24T04:00:00Z', '2026-10-25T02:00:00Z', NOW]) {
      scrubTo(iso);
      await flush();
    }
    expect(fetchMock).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it('reuses a held window after goLive and a new scrub within 30 minutes', async () => {
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush();
    useSkyStore.getState().goLive();
    await vi.advanceTimersByTimeAsync(10 * 60_000);
    scrubTo('2026-10-24T12:00:00Z');
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it('refetches once when the shown instant nears the window edge, not again for the same instant', async () => {
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    // real time moves on, so a fresh window would be a different one; then the extreme of the scrub range
    await vi.advanceTimersByTimeAsync(5 * 60_000);
    scrubTo('2026-10-25T08:50:00Z');
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const another = subscribe(); // sync again for the very same shown instant
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    another();
    unsubscribe();
  });

  it('never asks twice for the identical window', async () => {
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush();
    scrubTo('2026-10-25T08:50:00Z'); // near the edge, but the clock has not moved: the same window would come back
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it('centres the window on the shown instant when it is outside now +- 24 h', async () => {
    const unsubscribe = subscribe();
    const shown = NOW_MS + 30 * 3600_000;
    scrubTo(new Date(shown).toISOString());
    await flush();
    const [startIso, endIso] = fetchMock.mock.calls[0];
    expect(Date.parse(startIso)).toBeLessThan(shown);
    expect(Date.parse(endIso)).toBeGreaterThan(shown);
    unsubscribe();
  });

  it('makes no request for an instant outside 1800-2200, and says so instead of staying "idle"', async () => {
    const unsubscribe = subscribe();
    scrubTo('1799-12-31T23:59:59Z');
    await flush();
    expect(store().status).toBe('unavailable');
    expect(store().error).toMatch(/1800/);
    scrubTo('2201-01-01T00:00:00Z');
    await flush();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(store().status).toBe('unavailable');
    unsubscribe();
  });

  it('clears the out-of-range notice when the scrub comes back inside the supported range', async () => {
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush(); // a window is held
    scrubTo('2201-01-01T00:00:00Z');
    expect(store().status).toBe('unavailable');
    scrubTo('2026-10-24T12:00:00Z'); // back inside the held window
    await flush();
    expect(store().status).toBe('ready');
    expect(store().error).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    useSkyStore.getState().goLive();
    scrubTo('1700-01-01T00:00:00Z');
    expect(store().status).toBe('unavailable');
    useSkyStore.getState().goLive(); // live again: nothing to complain about
    expect(store().status).toBe('ready');
    unsubscribe();
  });
});

describe('skySeriesStore: cancelling', () => {
  it('aborts the in-flight request when the sky returns to live, and ignores its late answer', async () => {
    const pending = deferred<SkySeries>();
    fetchMock.mockReturnValue(pending.promise);
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    expect(store().status).toBe('loading');
    useSkyStore.getState().goLive();
    expect(cancelMock).toHaveBeenCalledTimes(1);
    expect(store().status).toBe('idle');
    pending.resolve(syntheticSeries(...windowArgs(SCRUB_A)));
    await flush();
    expect(store().series).toBeNull();
    expect(store().status).toBe('idle');
    unsubscribe();
  });

  it('aborts when the LAST subscriber goes away, not before', async () => {
    fetchMock.mockReturnValue(deferred<SkySeries>().promise);
    const a = subscribe();
    const b = subscribe();
    scrubTo(SCRUB_A);
    a();
    expect(cancelMock).not.toHaveBeenCalled();
    b();
    expect(cancelMock).toHaveBeenCalledTimes(1);
    b(); // a second call of the same unsubscribe is harmless
    expect(cancelMock).toHaveBeenCalledTimes(1);
  });

  it('does not cancel the client when nothing of its own is in flight', async () => {
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush(); // finished
    useSkyStore.getState().goLive();
    unsubscribe();
    expect(cancelMock).not.toHaveBeenCalled();
  });

  it('a new subscriber after the last one left finds the window still held and fresh', async () => {
    const first = subscribe();
    scrubTo(SCRUB_A);
    await flush();
    first();
    const second = subscribe();
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    second();
  });
});

describe('skySeriesStore: failures', () => {
  it('a failed request is unavailable with the reason, never a silently stale series', async () => {
    fetchMock.mockRejectedValue(new EarthSeriesError('unavailable', 'ephemeris unavailable', 503));
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush();
    expect(store().status).toBe('unavailable');
    expect(store().series).toBeNull();
    expect(store().error).toBe('ephemeris unavailable');
    expect(store().errorKind).toBe('unavailable');
    unsubscribe();
  });

  it('does not retry on every scrub tick: it backs off for 10 s, then tries again', async () => {
    fetchMock.mockRejectedValue(new EarthSeriesError('network', 'down'));
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush();
    for (const minute of [1, 2, 3, 4, 5]) {
      scrubTo(`2026-10-24T11:0${minute}:00Z`);
      await flush();
    }
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(10_000);
    fetchMock.mockImplementation((start, end, step) => Promise.resolve(syntheticSeries(start, end, step)));
    scrubTo('2026-10-24T11:10:00Z');
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(store().status).toBe('ready');
    unsubscribe();
  });

  it('retries a request that another caller of the client took over, a bounded number of times', async () => {
    const stale = () => new EarthSeriesError('stale', 'A newer series request replaced this one.');
    fetchMock.mockRejectedValueOnce(stale());
    const unsubscribe = subscribe();
    scrubTo(SCRUB_A);
    await flush();
    expect(store().status).toBe('loading'); // not an error: it asks again shortly
    await vi.advanceTimersByTimeAsync(500);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(store().status).toBe('ready');
    unsubscribe();

    resetSkySeriesStore();
    fetchMock.mockReset();
    fetchMock.mockRejectedValue(stale());
    const again = subscribe();
    scrubTo('2026-10-24T12:00:00Z');
    await vi.advanceTimersByTimeAsync(5_000);
    expect(fetchMock.mock.calls.length).toBeLessThanOrEqual(4); // first try + 3 retries, then it gives up
    expect(store().status).toBe('unavailable');
    again();
  });
});
