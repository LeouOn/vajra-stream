/**
 * W3-D2b — the dome in scrub mode.
 *
 * One series covers the whole +-24 h range; the live /night-sky poll stops
 * while scrubbing and resumes on goLive. Series fixtures are literals copied
 * from the independent oracle (equinox-2026 samples 0,2,4,6,8,10; never
 * imported). The live sacred-star values at the scrub instant are literals from
 * `core.celestial_sky.calculate_night_sky` (geocentric/GMST).
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  fetchSeries: vi.fn(),
  cancelSeriesRequest: vi.fn(),
  buildSkyLayer: vi.fn(),
  loadStars: vi.fn(),
  loadConstellationLines: vi.fn(),
}));

vi.mock('../../lib/earthSeriesClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/earthSeriesClient')>();
  return { ...actual, fetchSeries: mocks.fetchSeries, cancelSeriesRequest: mocks.cancelSeriesRequest };
});
vi.mock('../../lib/skyLayer', () => ({ buildSkyLayer: mocks.buildSkyLayer }));
vi.mock('../../lib/sky', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/sky')>();
  return {
    ...actual,
    loadStars: mocks.loadStars,
    loadConstellationLines: mocks.loadConstellationLines,
  };
});

import CelestialSkyDome from '../../components/UI/CelestialSkyDome';
import { useSkyStore } from '../../stores/skyStore';
import { resetSkySeriesStore, useSkySeries } from '../../stores/skySeriesStore';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { EarthSeriesError } from '../../lib/earthSeriesClient';
import { decodeSeries, type SkySeries } from '../../lib/skySeries';
import { skyAtInstant, localScrubLst, scrubWindow } from '../../lib/skyScrub';
import { parseInstant } from '../../lib/skyClock';

const EQUINOX_SIX = [
  {"at":"2026-03-20T14:46:00+00:00","gast_deg":39.64937,"sun":{"id":"sun","lat":9.1e-05,"lon":-39.649388},"moon":{"id":"moon","lat":11.238252,"lon":-22.036433},"planets":[{"id":"mercury","lat":-7.425063,"lon":-59.916933},{"id":"venus","lat":6.096784,"lon":-23.101568},{"id":"mars","lat":-7.21454,"lon":-53.795934},{"id":"jupiter","lat":22.929005,"lon":66.92579},{"id":"saturn","lat":-0.308841,"lon":-35.018775},{"id":"uranus","lat":19.612297,"lon":16.450145},{"id":"neptune","lat":-0.493049,"lon":-37.502941},{"id":"pluto","lat":-22.80879,"lon":-91.270007}]},
  {"at":"2026-03-20T15:06:00+00:00","gast_deg":44.663059,"sun":{"id":"sun","lat":0.005583,"lon":-44.650411},"moon":{"id":"moon","lat":11.326286,"lon":-26.867837},"planets":[{"id":"mercury","lat":-7.428321,"lon":-64.929589},{"id":"venus","lat":6.103771,"lon":-28.099453},{"id":"mars","lat":-7.210302,"lon":-58.799484},{"id":"jupiter","lat":22.928968,"lon":61.91256},{"id":"saturn","lat":-0.308157,"lon":-40.030875},{"id":"uranus","lat":19.612413,"lon":11.436978},{"id":"neptune","lat":-0.492841,"lon":-42.516147},{"id":"pluto","lat":-22.808757,"lon":-96.283384}]},
  {"at":"2026-03-20T15:26:00+00:00","gast_deg":49.676748,"sun":{"id":"sun","lat":0.011074,"lon":-49.651434},"moon":{"id":"moon","lat":11.414221,"lon":-31.699103},"planets":[{"id":"mercury","lat":-7.431571,"lon":-69.942227},{"id":"venus","lat":6.110758,"lon":-33.097337},{"id":"mars","lat":-7.206063,"lon":-63.803035},{"id":"jupiter","lat":22.928931,"lon":56.899331},{"id":"saturn","lat":-0.307472,"lon":-45.042975},{"id":"uranus","lat":19.612529,"lon":6.423811},{"id":"neptune","lat":-0.492633,"lon":-47.529352},{"id":"pluto","lat":-22.808724,"lon":-101.296761}]},
  {"at":"2026-03-20T15:46:00+00:00","gast_deg":54.690437,"sun":{"id":"sun","lat":0.016566,"lon":-54.652457},"moon":{"id":"moon","lat":11.502054,"lon":-36.530231},"planets":[{"id":"mercury","lat":-7.434813,"lon":-74.954847},{"id":"venus","lat":6.117745,"lon":-38.095221},{"id":"mars","lat":-7.201824,"lon":-68.806585},{"id":"jupiter","lat":22.928893,"lon":51.886103},{"id":"saturn","lat":-0.306787,"lon":-50.055075},{"id":"uranus","lat":19.612644,"lon":1.410644},{"id":"neptune","lat":-0.492425,"lon":-52.542558},{"id":"pluto","lat":-22.808692,"lon":-106.310138}]},
  {"at":"2026-03-20T16:06:00+00:00","gast_deg":59.704127,"sun":{"id":"sun","lat":0.022057,"lon":-59.653481},"moon":{"id":"moon","lat":11.589786,"lon":-41.361221},"planets":[{"id":"mercury","lat":-7.438047,"lon":-79.967449},{"id":"venus","lat":6.124731,"lon":-43.093105},{"id":"mars","lat":-7.197585,"lon":-73.810136},{"id":"jupiter","lat":22.928856,"lon":46.872875},{"id":"saturn","lat":-0.306102,"lon":-55.067176},{"id":"uranus","lat":19.61276,"lon":-3.602523},{"id":"neptune","lat":-0.492217,"lon":-57.555763},{"id":"pluto","lat":-22.808659,"lon":-111.323515}]},
  {"at":"2026-03-20T16:26:00+00:00","gast_deg":64.717816,"sun":{"id":"sun","lat":0.027549,"lon":-64.654504},"moon":{"id":"moon","lat":11.677414,"lon":-46.192071},"planets":[{"id":"mercury","lat":-7.441273,"lon":-84.980034},{"id":"venus","lat":6.131716,"lon":-48.090989},{"id":"mars","lat":-7.193346,"lon":-78.813688},{"id":"jupiter","lat":22.928818,"lon":41.859648},{"id":"saturn","lat":-0.305418,"lon":-60.079276},{"id":"uranus","lat":19.612876,"lon":-8.615689},{"id":"neptune","lat":-0.492009,"lon":-62.568969},{"id":"pluto","lat":-22.808626,"lon":-116.336892}]},
];

// calculate_night_sky at 2026-03-20T15:26:00Z, (37.7749,-122.4194), GMST.
const LIVE_SACRED = {
  sirius: { altitude: -68.38, azimuth: 14.9 },
  vega: { altitude: 83.79, azimuth: 281.98 },
};
const SACRED_J2000 = [
  { id: 'sirius', ra_j2000: 101.287, dec_j2000: -16.716 },
  { id: 'vega', ra_j2000: 279.234, dec_j2000: 38.784 },
];
const SCRUB_AT = '2026-03-20T15:26:00Z';

function fixture(offsetDeg = 0): SkySeries {
  return decodeSeries({
    ephemeris: 'swisseph 2.10.03',
    sidereal_time: 'apparent',
    start: EQUINOX_SIX[0].at,
    end: EQUINOX_SIX[EQUINOX_SIX.length - 1].at,
    step_seconds: 1200,
    count: EQUINOX_SIX.length,
    samples: EQUINOX_SIX.map((sample) => ({
      ...sample,
      gast_deg: (sample.gast_deg + offsetDeg) % 360,
      sun: { ...sample.sun, lon: ((((sample.sun.lon + offsetDeg + 180) % 360) + 360) % 360) - 180 },
    })),
    provenance: { computed: 'computed' },
  });
}

function planet(id: string, sign = 'Cancer', signGlyph = '♋') {
  return {
    id,
    name: id[0].toUpperCase() + id.slice(1),
    glyph: '♃',
    altitude: 10,
    azimuth: 100,
    sign,
    sign_glyph: signGlyph,
    visible: true,
    color: '#a855f7',
    esoteric_quality: 'quality',
  };
}

function star(id: string, coords: boolean) {
  return {
    id,
    name: `${id} (test)`,
    altitude: 20,
    azimuth: 90,
    magnitude: 1,
    visible: true,
    color: '#a6d8ff',
    nakshatra: 'Ardra',
    quality: 'quality',
    ...(coords
      ? id === 'vega'
        ? { ra_j2000: 279.234, dec_j2000: 38.784 }
        : { ra_j2000: 101.287, dec_j2000: -16.716 }
      : {}),
  };
}

function livePayload(withCoords = true) {
  return {
    timestamp_utc: '2026-03-20T14:46:00Z',
    observer: {
      latitude: DEFAULT_LAT,
      longitude: DEFAULT_LNG,
      local_sidereal_time_deg: 277.23,
      local_sidereal_time_hms: '18:28:55',
    },
    moon: { phase_name: 'Waxing Crescent', illumination: 2 },
    planets: [planet('sun'), planet('jupiter')],
    visible_planets_count: 2,
    sacred_stars: [star('sirius', withCoords), star('vega', withCoords)],
    visible_stars_count: 2,
    provenance: { observer: 'computed' },
  };
}

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) } as Response;
}

const noop = () => {};
function stubCtx(): CanvasRenderingContext2D {
  return {
    globalAlpha: 1,
    clearRect: noop,
    beginPath: noop,
    arc: noop,
    fill: noop,
    stroke: noop,
    moveTo: noop,
    lineTo: noop,
    fillText: noop,
    setLineDash: noop,
    measureText: () => ({ width: 10 }) as TextMetrics,
    createRadialGradient: () => ({ addColorStop: noop }) as unknown as CanvasGradient,
    save: noop,
    restore: noop,
    setTransform: noop,
    putImageData: noop,
    drawImage: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  } as unknown as CanvasRenderingContext2D;
}

interface NightRequest {
  init: RequestInit;
  resolve: (value: Response) => void;
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let nightRequests: NightRequest[];
let intervalCalls: { id: number; callback: TimerHandler; delay?: number }[];

function flush(): Promise<void> {
  return act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function mount(): Promise<void> {
  await act(async () => {
    root.render(<CelestialSkyDome />);
  });
}

async function deliverLive(body = livePayload()): Promise<void> {
  await act(async () => {
    nightRequests[0].resolve(response(body));
  });
  await flush();
}

async function enterScrub(at = SCRUB_AT): Promise<void> {
  act(() => {
    useSkyStore.getState().setAt(at);
  });
  await flush();
}

async function resolveSeries(index: number, series: SkySeries): Promise<void> {
  await act(async () => {
    resolvers[index](series);
    await Promise.resolve();
  });
  await flush();
}

async function deliverSeries(series: SkySeries): Promise<void> {
  await resolveSeries(resolvers.length - 1, series);
}

async function rejectSeries(index: number, error: unknown): Promise<void> {
  await act(async () => {
    rejecters[index](error);
    await Promise.resolve();
  });
  await flush();
}

/** A second subscriber proves the store shares one request across consumers. */
function OtherSeriesConsumer(): null {
  useSkySeries();
  return null;
}

const resolvers: ((series: SkySeries) => void)[] = [];
const rejecters: ((error: unknown) => void)[] = [];

function canvas(): HTMLCanvasElement {
  const element = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
  if (!(element instanceof HTMLCanvasElement)) throw new Error('canvas missing');
  return element;
}

function dataset(name: string): string | undefined {
  return canvas().dataset[name];
}

function pollInterval(): { id: number; callback: TimerHandler; delay?: number } {
  const poll = intervalCalls.find((call) => call.delay === 60000);
  if (!poll) throw new Error('60 s poll interval missing');
  return poll;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  const canvasProto: { getContext(contextId: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(canvasProto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});

  intervalCalls = [];
  let intervalId = 0;
  vi.stubGlobal(
    'setInterval',
    vi.fn((callback: TimerHandler, delay?: number) => {
      intervalId += 1;
      intervalCalls.push({ id: intervalId, callback, delay });
      return intervalId;
    }),
  );
  vi.stubGlobal('clearInterval', vi.fn());

  useSkyStore.getState().setObserver(DEFAULT_LAT, DEFAULT_LNG);
  useSkyStore.getState().goLive();

  nightRequests = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((resolve) => {
          nightRequests.push({ init: init ?? {}, resolve });
        }),
    ),
  );

  mocks.loadStars.mockImplementation(() => new Promise<never>(() => {}));
  mocks.loadConstellationLines.mockImplementation(() => new Promise<never>(() => {}));
  mocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [],
  }));
  mocks.cancelSeriesRequest.mockClear();
  resolvers.length = 0;
  rejecters.length = 0;
  resetSkySeriesStore();
  mocks.fetchSeries.mockReset();
  mocks.fetchSeries.mockImplementation(
    () =>
      new Promise<SkySeries>((resolve, reject) => {
        resolvers.push(resolve);
        rejecters.push(reject);
      }),
  );
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('CelestialSkyDome scrub mode', () => {
  it('requests one +-24 h window at 603 s x 288 and shows the scrubbed sky', async () => {
    // Pin "now" two hours before the shown instant so this is the normal
    // now-centred window (the paused-outside case is the next test).
    vi.spyOn(Date, 'now').mockReturnValue(parseInstant(SCRUB_AT) - 2 * 3600_000);
    await mount();
    await deliverLive();
    expect(nightRequests).toHaveLength(1);

    await enterScrub();
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(1);
    const [startIso, endIso, step] = mocks.fetchSeries.mock.calls[0] as [string, string, number];
    const start = parseInstant(startIso);
    const end = parseInstant(endIso);
    expect(step).toBe(603);
    expect(start % 60_000).toBe(0);
    expect(start).toBeLessThanOrEqual(Date.now() - 24 * 3600_000);
    expect(end - start).toBe(287 * 603 * 1000);
    expect(end).toBeGreaterThanOrEqual(Date.now() + 24 * 3600_000);

    const series = fixture();
    await deliverSeries(series);

    expect(container.querySelector('[data-testid="sky-scrub-banner"]')).not.toBeNull();
    expect(container.textContent).toContain('Scrubbed:');
    expect(container.textContent).toContain('as of now');
    expect(dataset('scrub')).toBe('true');
    expect(dataset('scrubStatus')).toBe('ready');

    const atMs = parseInstant(SCRUB_AT);
    const expected = skyAtInstant(series, atMs, DEFAULT_LAT, DEFAULT_LNG, SACRED_J2000);
    // The live payload supplies metadata for the Sun and Jupiter only.
    const visibleCount = ['sun', 'jupiter'].filter((id) => expected.positions[id].alt > 0).length;
    expect(Number(dataset('scrubPlanets'))).toBe(visibleCount);

    const jupiter = expected.bodies.find((body) => body.id === 'jupiter');
    if (jupiter && expected.positions.jupiter.alt > 0) {
      expect(container.textContent).toContain(`Alt ${expected.positions.jupiter.alt.toFixed(2)}°`);
    }
    const visibleSacred = expected.sacred.filter((p) => p.alt > 0);
    expect(Number(dataset('scrubSacred'))).toBe(visibleSacred.length);
    const vega = expected.sacred.find((p) => p.id === 'vega');
    if (vega && vega.alt > 0) {
      expect(container.textContent).toContain(`+${vega.alt.toFixed(2)}°`);
    }
    // Parity with the live sacred-star path (geocentric/GMST vs GAST).
    const rad = Math.PI / 180;
    for (const position of expected.sacred) {
      const live = LIVE_SACRED[position.id as keyof typeof LIVE_SACRED];
      const dz = Math.abs(((position.az - live.azimuth + 540) % 360) - 180) * rad;
      const c =
        Math.sin(position.alt * rad) * Math.sin(live.altitude * rad) +
        Math.cos(position.alt * rad) * Math.cos(live.altitude * rad) * Math.cos(dz);
      const sep = Math.acos(Math.min(1, Math.max(-1, c))) / rad;
      expect(sep, position.id).toBeLessThanOrEqual(0.02);
    }
  });

  it('stops the /night-sky poll while scrubbing', async () => {
    await mount();
    await deliverLive();
    await enterScrub();
    const poll = pollInterval();
    const callback = poll.callback;
    if (typeof callback !== 'function') throw new Error('poll not callable');
    act(() => {
      callback();
    });
    expect(nightRequests).toHaveLength(1);
  });

  it('does not draw sacred stars without J2000 coords, and says so', async () => {
    await mount();
    await deliverLive(livePayload(false));
    await enterScrub();
    await deliverSeries(fixture());
    expect(container.querySelector('[data-testid="sky-scrub-sacred-unavailable"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="sky-scrub-sacred-footer"]')).not.toBeNull();
    expect(dataset('scrubSacred')).toBe('0');
  });

  it('refetches near a window edge once, not in a loop', async () => {
    await mount();
    await deliverLive();
    await enterScrub();
    const series = fixture();
    await deliverSeries(series);
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(1);

    const last = series.samples[series.samples.length - 1].atMs;
    await enterScrub(new Date(last - 10 * 60_000).toISOString());
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(2);

    // The refetched window still puts the instant near its edge; it must not loop.
    await deliverSeries(series);
    await flush();
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(2);
  });

  it('falls back to local sidereal stars when the series is unavailable', async () => {
    mocks.fetchSeries.mockRejectedValue(
      new EarthSeriesError('unavailable', 'The earth-state series is unavailable (503).'),
    );
    await mount();
    await deliverLive();
    await enterScrub();
    await flush();

    expect(container.querySelector('[data-testid="sky-scrub-unavailable"]')).not.toBeNull();
    expect(dataset('scrubStatus')).toBe('unavailable');
    expect(dataset('scrubPlanets')).toBe('0');

    const atMs = parseInstant(SCRUB_AT);
    const expectedLst = localScrubLst(atMs, DEFAULT_LNG);
    const lastCall = mocks.buildSkyLayer.mock.calls[mocks.buildSkyLayer.mock.calls.length - 1]?.[0] as {
      lstDeg: number;
    };
    expect(lastCall.lstDeg).toBeCloseTo(expectedLst, 6);
  });

  it('leaving scrub cancels the series and resumes the live poll', async () => {
    await mount();
    await deliverLive();
    await enterScrub();
    await deliverSeries(fixture());
    expect(nightRequests).toHaveLength(1);

    act(() => {
      useSkyStore.getState().goLive();
    });
    await flush();

    expect(nightRequests).toHaveLength(2); // an immediate live refresh
    expect(container.querySelector('[data-testid="sky-scrub-banner"]')).toBeNull();
    expect(dataset('scrub')).toBe('false');
  });

  it('aborts both requests on unmount', async () => {
    await mount(); // /night-sky request pending
    await enterScrub(); // series request pending
    expect(nightRequests).toHaveLength(1);
    const signal = nightRequests[0].init.signal as AbortSignal;
    expect(signal.aborted).toBe(false);

    act(() => {
      root.unmount();
    });
    expect(signal.aborted).toBe(true);
    expect(mocks.cancelSeriesRequest).toHaveBeenCalled();
    root = createRoot(container);
  });

  it('uses the store/props place in scrub mode, not the payload place', async () => {
    await mount();
    await deliverLive(); // payload is still San Francisco
    act(() => {
      useSkyStore.getState().setObserver(-33.8688, 151.2093, 'Sydney');
    });
    await flush();
    await enterScrub();
    await deliverSeries(fixture());

    const lastCall = mocks.buildSkyLayer.mock.calls[mocks.buildSkyLayer.mock.calls.length - 1]?.[0] as {
      latDeg: number;
    };
    expect(lastCall.latDeg).toBe(-33.8688);
  });

  it('does not refetch the series on a place change in scrub mode', async () => {
    await mount();
    await deliverLive();
    await enterScrub();
    await deliverSeries(fixture());
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(1);

    act(() => {
      useSkyStore.getState().setObserver(-33.8688, 151.2093, 'Sydney');
    });
    await flush();

    // Sub-points do not depend on the place: no second 213 KB download.
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(1);
    const lastCall = mocks.buildSkyLayer.mock.calls[mocks.buildSkyLayer.mock.calls.length - 1]?.[0] as {
      latDeg: number;
    };
    expect(lastCall.latDeg).toBe(-33.8688);
  });

  it('centres the series on a paused instant that drifted 30 h past the window', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(parseInstant(SCRUB_AT) - 30 * 3600_000);
    await mount();
    await deliverLive();
    await enterScrub();

    const [startIso, endIso, step] = mocks.fetchSeries.mock.calls[0] as [string, string, number];
    const start = parseInstant(startIso);
    const end = parseInstant(endIso);
    const shown = parseInstant(SCRUB_AT);
    expect(step).toBe(603);
    // 30 h after the real now -> outside now +-24 h -> the window follows it.
    expect(start).toBe(Math.floor((shown - 24 * 3600_000) / 60_000) * 60_000);
    expect(end - start).toBe(287 * 603 * 1000);
    expect(start).toBeLessThanOrEqual(shown);
    expect(end).toBeGreaterThanOrEqual(shown);

    await deliverSeries(fixture());
    expect(dataset('scrubStatus')).toBe('ready');
    expect(container.textContent).toContain('computed for that instant');
    expect(container.textContent).not.toContain('planets not drawn');
    expect(Number(dataset('scrubPlanets'))).toBeGreaterThan(0);
  });

  it('says planets are not drawn for an instant no series can cover, and makes no request', async () => {
    await mount();
    await deliverLive();
    await enterScrub('2300-06-01T00:00:00Z');

    // The shared store refuses an instant outside 1800-2200 outright.
    expect(mocks.fetchSeries).not.toHaveBeenCalled();
    expect(container.querySelector('[data-testid="sky-scrub-unavailable"]')).not.toBeNull();
    expect(container.textContent).toContain('outside the supported range');
    expect(container.textContent).toContain('planets not drawn: no series for this instant');
    expect(dataset('scrubStatus')).toBe('unavailable');
    expect(dataset('scrubPlanets')).toBe('0');
    await flush();
    expect(mocks.fetchSeries).not.toHaveBeenCalled();
  });

  it('shares ONE series request between the dome and another consumer', async () => {
    await act(async () => {
      root.render(
        <>
          <CelestialSkyDome />
          <OtherSeriesConsumer />
        </>,
      );
    });
    await deliverLive();
    await enterScrub();
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(1);
    await deliverSeries(fixture());
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(1);
    expect(dataset('scrubStatus')).toBe('ready');
  });

  it('keeps drawing a retained series after a failed refresh and labels the failure', async () => {
    await mount();
    await deliverLive();
    await enterScrub();
    const series = fixture();
    await deliverSeries(series);
    expect(dataset('scrubStatus')).toBe('ready');

    // Age the held window past 30 min, then move to another instant it covers:
    // the store refreshes and the refresh fails, but the window stays usable.
    const realNow = Date.now();
    vi.spyOn(Date, 'now').mockReturnValue(realNow + 31 * 60_000);
    await enterScrub(series.samples[3].at);
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(2);
    await rejectSeries(1, new EarthSeriesError('unavailable', 'The series is unavailable (503).'));

    const retained = container.querySelector('[data-testid="sky-scrub-retained"]');
    expect(retained).not.toBeNull();
    expect(retained?.textContent).toContain('refresh failed');
    expect(container.querySelector('[data-testid="sky-scrub-unavailable"]')).toBeNull();
    expect(dataset('scrubStatus')).toBe('ready');
    expect(container.textContent).toContain('Sun, Moon, planets, stars: computed for that instant');
    expect(Number(dataset('scrubPlanets'))).toBeGreaterThan(0);
  });

  it('banner: loading, then computed only when the held window covers the instant, then unavailable', async () => {
    await mount();
    await deliverLive();
    await enterScrub();
    // No series answer yet: loading, never a computed claim.
    expect(dataset('scrubStatus')).toBe('loading');
    expect(container.textContent).toContain('loading the series');
    expect(container.textContent).not.toContain('Sun, Moon, planets, stars: computed');

    await deliverSeries(fixture());
    expect(dataset('scrubStatus')).toBe('ready');
    expect(container.textContent).toContain('Sun, Moon, planets, stars: computed for that instant');

    // Move far outside the held window: the store starts a re-centred request,
    // and the old window must not keep claiming computed.
    await enterScrub('2026-06-01T00:00:00Z');
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(2);
    expect(dataset('scrubStatus')).toBe('loading');
    expect(container.textContent).toContain('loading the series');
    expect(container.textContent).not.toContain('Sun, Moon, planets, stars: computed');

    await rejectSeries(1, new EarthSeriesError('unavailable', 'The series is unavailable (503).'));
    expect(dataset('scrubStatus')).toBe('unavailable');
    expect(container.querySelector('[data-testid="sky-scrub-unavailable"]')).not.toBeNull();
    expect(container.textContent).toContain('planets not drawn');
    expect(container.textContent).not.toContain('Sun, Moon, planets, stars: computed');
  });

  it('uses only the newest series when entering scrub twice races an older answer', async () => {
    await mount();
    await deliverLive();
    await enterScrub(); // request A pending
    act(() => {
      useSkyStore.getState().goLive();
    });
    await flush();
    await enterScrub(); // request B pending
    expect(mocks.fetchSeries).toHaveBeenCalledTimes(2);

    const fresh = fixture(90); // +90 deg GAST, distinguishable
    await resolveSeries(1, fresh);
    const atMs = parseInstant(SCRUB_AT);
    const expected = skyAtInstant(fresh, atMs, DEFAULT_LAT, DEFAULT_LNG, SACRED_J2000);

    await resolveSeries(0, fixture(0)); // stale answer arrives last
    const lastCall = mocks.buildSkyLayer.mock.calls[mocks.buildSkyLayer.mock.calls.length - 1]?.[0] as {
      lstDeg: number;
    };
    expect(lastCall.lstDeg).toBeCloseTo(expected.lst, 6);
  });
});
