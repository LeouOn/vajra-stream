/**
 * Earth & Sky wave 3 — the one shared owner of the fetched sub-point series (row W3-I).
 *
 * While the sky is scrubbed (`skyStore.at !== null`) the dome, the globes and the flat strip must all show the
 * SAME instant. That instant comes from one decoded `/astrology/earth-state/series` window, fetched once and
 * shared by every subscriber, instead of each component asking for its own.
 *
 * - **Ref-counted.** It fetches only while `at !== null` AND at least one subscriber exists. The last
 *   unsubscribe, and `at` returning to null (live), cancel its own in-flight request.
 * - **One request per window.** Several subscribers share a request; a window it already holds (fresh, covering
 *   the shown instant, not at the edge) is never fetched again; the identical window is never requested twice;
 *   an instant near the edge triggers one refetch per shown instant (the rules are `lib/skyScrub`'s).
 * - **Honest failure.** A failed request is `unavailable` with the reason; it does not retry on every scrub tick
 *   (10 s back-off). A request taken over by another caller of the single-flight client (`stale` that this store
 *   did not cause) is retried a few times, then given up.
 * - No component code, no timers except the two retry delays above.
 *
 * `scrubbedEarthState` turns a series into the `EarthState` shape the globes already read: dec = lat,
 * ra = wrap360(lon + gast), all labelled computed. It is `null` outside the series window, never an extrapolation.
 */
import { useEffect } from 'react';
import { create, type StoreApi, type UseBoundStore } from 'zustand';
import type { BodySubPoint, EarthState } from '../lib/earth';
import {
  EarthSeriesError,
  cancelSeriesRequest,
  fetchSeries,
  type EarthSeriesErrorKind,
} from '../lib/earthSeriesClient';
import { parseInstant } from '../lib/skyClock';
import {
  SCRUB_MAX_AGE_MS,
  SERIES_RANGE_END_MS,
  SERIES_RANGE_START_MS,
  scrubWindow,
  shouldRefetchSeries,
  type ScrubWindow,
} from '../lib/skyScrub';
import { bodiesAt, type InterpolatedBody, type SkySeries } from '../lib/skySeries';
import { useSkyStore } from './skyStore';

export type SkySeriesStatus = 'idle' | 'loading' | 'ready' | 'unavailable';

export interface SkySeriesState {
  status: SkySeriesStatus;
  /** The decoded window last fetched, kept while it stays valid; null before the first success. */
  series: SkySeries | null;
  /** Wall-clock time (ms) at which `series` arrived. */
  fetchedAtMs: number | null;
  error: string | null;
  errorKind: EarthSeriesErrorKind | null;
}

interface SkySeriesActions {
  /** Count one subscriber; returns its unsubscribe (idempotent). */
  subscribe(): () => void;
}

export type SkySeriesStore = SkySeriesState & SkySeriesActions;

/** After a failure, wait this long before asking again (a scrub drag must not become a request storm). */
const RETRY_AFTER_MS = 10_000;
/** A request that another caller of the single-flight client took over is asked again after this delay... */
const STALE_RETRY_MS = 500;
/** ...at most this many times. */
const STALE_RETRIES = 3;

const INITIAL: SkySeriesState = {
  status: 'idle',
  series: null,
  fetchedAtMs: null,
  error: null,
  errorKind: null,
};

let subscribers = 0;
let unsubscribeSky: (() => void) | null = null;
let lastShownMs: number | null = null;
let inflightKey: string | null = null;
let heldKey: string | null = null;
let requestSeq = 0;
let lastFailureMs = Number.NEGATIVE_INFINITY;
let staleRetries = 0;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
/** True while `unavailable` is the "outside the supported range" notice rather than a failed request. */
let rangeNotice = false;

const RANGE_MESSAGE = 'The shown instant is outside the supported range (1800-2200).';

function windowKey(win: ScrubWindow): string {
  return `${win.startIso}|${win.endIso}`;
}

/** Cancel what this store has in flight (and any pending retry). Leaves a request that is not ours alone. */
function stopRequest(): void {
  const hadTimer = retryTimer !== null;
  if (retryTimer !== null) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }
  const hadRequest = inflightKey !== null;
  if (!hadRequest && !hadTimer) return;
  if (hadRequest) {
    requestSeq += 1; // its answer, if it still comes, is ignored
    cancelSeriesRequest();
  }
  inflightKey = null;
  staleRetries = 0;
  useSkySeriesStore.setState({ status: useSkySeriesStore.getState().series !== null ? 'ready' : 'idle' });
}

function startFetch(win: ScrubWindow, key: string): void {
  stopRequest(); // a different window in flight is superseded
  inflightKey = key;
  const id = (requestSeq += 1);
  useSkySeriesStore.setState({ status: 'loading', error: null, errorKind: null });
  fetchSeries(win.startIso, win.endIso, win.stepSeconds).then(
    (series) => {
      if (id !== requestSeq) return;
      inflightKey = null;
      heldKey = key;
      staleRetries = 0;
      useSkySeriesStore.setState({
        status: 'ready',
        series,
        fetchedAtMs: Date.now(),
        error: null,
        errorKind: null,
      });
    },
    (error: unknown) => {
      if (id !== requestSeq) return;
      inflightKey = null;
      const kind: EarthSeriesErrorKind = error instanceof EarthSeriesError ? error.kind : 'network';
      if (kind === 'stale' && staleRetries < STALE_RETRIES) {
        // Not our cancel (that would have bumped requestSeq): someone else used the single-flight client.
        staleRetries += 1;
        retryTimer = setTimeout(() => {
          retryTimer = null;
          sync();
        }, STALE_RETRY_MS);
        return; // status stays 'loading'
      }
      staleRetries = 0;
      lastFailureMs = Date.now();
      useSkySeriesStore.setState({
        status: 'unavailable',
        error: error instanceof Error ? error.message : 'The time series is unavailable.',
        errorKind: kind,
      });
    },
  );
}

function clearRangeNotice(): void {
  if (!rangeNotice) return;
  rangeNotice = false;
  useSkySeriesStore.setState({
    status: useSkySeriesStore.getState().series !== null ? 'ready' : 'idle',
    error: null,
    errorKind: null,
  });
}

/** Decide, from the current `at` and subscribers, whether to fetch, keep, or cancel. */
function sync(): void {
  const at = useSkyStore.getState().at;
  if (subscribers === 0 || at === null) {
    stopRequest();
    clearRangeNotice();
    lastShownMs = null;
    return;
  }
  let shownMs: number;
  try {
    shownMs = parseInstant(at);
  } catch {
    return; // the sky store normalises on write; defensive only
  }
  // No window can cover an instant outside the backend's range: say so (a reader must not wait on "idle").
  if (shownMs < SERIES_RANGE_START_MS || shownMs > SERIES_RANGE_END_MS) {
    stopRequest();
    rangeNotice = true;
    useSkySeriesStore.setState({ status: 'unavailable', error: RANGE_MESSAGE, errorKind: 'invalid-input' });
    return;
  }
  clearRangeNotice();
  const { series, fetchedAtMs, status } = useSkySeriesStore.getState();
  const nowMs = Date.now();
  const moved = lastShownMs !== shownMs;
  lastShownMs = shownMs;

  // Not needed: a window it already holds (fresh, covering, not at the edge), or an instant no window can cover.
  if (!shouldRefetchSeries(series, fetchedAtMs, shownMs, nowMs)) return;

  const covers =
    series !== null && shownMs >= series.samples[0].atMs && shownMs <= series.samples[series.samples.length - 1].atMs;
  const fresh = fetchedAtMs !== null && nowMs - fetchedAtMs < SCRUB_MAX_AGE_MS;
  // An instant near the edge asks for ONE refetch (which re-centres the window); the extreme of the scrub range
  // stays "near the edge" forever, so the same instant must not ask again until the window ages out.
  if (covers && !moved && fresh) return;

  const win = scrubWindow(nowMs, shownMs);
  const key = windowKey(win);
  if (key === inflightKey) return; // already on its way, shared by every subscriber
  if (series !== null && key === heldKey && fresh) return; // it already holds exactly this window
  if (status === 'unavailable' && nowMs - lastFailureMs < RETRY_AFTER_MS) return; // back off
  startFetch(win, key);
}

export const useSkySeriesStore: UseBoundStore<StoreApi<SkySeriesStore>> = create<SkySeriesStore>(() => ({
  ...INITIAL,
  subscribe() {
    subscribers += 1;
    if (subscribers === 1) {
      unsubscribeSky = useSkyStore.subscribe((state, previous) => {
        if (state.at !== previous.at) sync();
      });
    }
    sync();
    let open = true;
    return () => {
      if (!open) return;
      open = false;
      subscribers = Math.max(0, subscribers - 1);
      if (subscribers === 0) {
        unsubscribeSky?.();
        unsubscribeSky = null;
        stopRequest();
        lastShownMs = null;
      }
    };
  },
}));

/** Back to a pristine store, for tests only: drops subscribers, listeners, timers and the held window. */
export function resetSkySeriesStore(): void {
  unsubscribeSky?.();
  unsubscribeSky = null;
  if (retryTimer !== null) clearTimeout(retryTimer);
  retryTimer = null;
  subscribers = 0;
  lastShownMs = null;
  inflightKey = null;
  heldKey = null;
  rangeNotice = false;
  requestSeq += 1;
  lastFailureMs = Number.NEGATIVE_INFINITY;
  staleRetries = 0;
  useSkySeriesStore.setState({ ...INITIAL });
}

export interface SkySeriesView {
  status: SkySeriesStatus;
  series: SkySeries | null;
  error: string | null;
  errorKind: EarthSeriesErrorKind | null;
}

/**
 * Subscribe to the shared series while mounted (and `enabled`). The store itself decides whether anything is
 * fetched: nothing is while the sky is live. This is the one call a component needs.
 */
export function useSkySeries(enabled = true): SkySeriesView {
  useEffect(() => (enabled ? useSkySeriesStore.getState().subscribe() : undefined), [enabled]);
  const status = useSkySeriesStore((s) => s.status);
  const series = useSkySeriesStore((s) => s.series);
  const error = useSkySeriesStore((s) => s.error);
  const errorKind = useSkySeriesStore((s) => s.errorKind);
  return { status, series, error, errorKind };
}

// ---------------------------------------------------------------------------------------------------------------

function wrap360(deg: number): number {
  const wrapped = deg % 360;
  return wrapped < 0 ? wrapped + 360 : wrapped;
}

function displayName(id: string): string {
  return id.length === 0 ? id : id[0].toUpperCase() + id.slice(1);
}

function toSubPoint(body: InterpolatedBody): BodySubPoint {
  return { id: body.id, name: displayName(body.id), ra_deg: body.ra, dec_deg: body.dec, lat: body.lat, lon: body.lon };
}

/**
 * The earth state at `shownMs` from a series: the Sun, the Moon and the eight planets interpolated between the two
 * bracketing samples, the interpolated apparent GAST, RA = wrap360(lon + gast), Dec = lat. `null` when the
 * instant is outside the series window (or not finite): the caller shows "unavailable", never an extrapolation.
 */
export function scrubbedEarthState(series: SkySeries, shownMs: number): EarthState | null {
  // One entry is enough: every consumer of one scrub position asks for the same (series, instant), and they
  // should all hold the very same object (callers must not mutate it).
  if (memo !== null && memo.series === series && memo.shownMs === shownMs) return memo.state;
  const state = buildEarthState(series, shownMs);
  memo = { series, shownMs, state };
  return state;
}

let memo: { series: SkySeries; shownMs: number; state: EarthState | null } | null = null;

function buildEarthState(series: SkySeries, shownMs: number): EarthState | null {
  let bodies: InterpolatedBody[];
  try {
    bodies = bodiesAt(series, shownMs);
  } catch {
    return null;
  }
  const sun = bodies.find((body) => body.id === 'sun');
  const moon = bodies.find((body) => body.id === 'moon');
  if (!sun || !moon) return null;
  return {
    at: new Date(shownMs).toISOString(),
    ephemeris: series.ephemeris,
    // every body's RA is wrap360(lon + gast), so the Sun recovers the interpolated GAST exactly
    gast_deg: wrap360(sun.ra - sun.lon),
    sun: toSubPoint(sun),
    moon: toSubPoint(moon),
    planets: bodies.filter((body) => body.id !== 'sun' && body.id !== 'moon').map(toSubPoint),
    provenance: { at: 'computed', gast_deg: 'computed', sun: 'computed', moon: 'computed', planets: 'computed' },
  };
}

/**
 * The scrub-aware `EarthStateSlice` (W3-K moved it here so `earthStateStore.ts`
 * never imports the scrub machinery at module load). Same rules as before:
 * a valid shown instant builds a frozen slice from the shared series; an
 * out-of-range/malformed instant or an unavailable series is `unavailable`;
 * a series that is still loading (or does not cover the instant yet) is
 * `loading`. Never the live state.
 */
export interface ScrubEarthStateSlice {
  status: 'loading' | 'ok' | 'unavailable';
  state: EarthState | null;
  fetchedAt: number | null;
  error: string | null;
  frozen: true;
}

export function scrubEarthStateSlice(at: string, view: SkySeriesView): ScrubEarthStateSlice {
  const unavailable = (error: string): ScrubEarthStateSlice => ({
    status: 'unavailable',
    state: null,
    fetchedAt: null,
    error,
    frozen: true,
  });
  let shownMs: number;
  try {
    shownMs = parseInstant(at);
  } catch (error) {
    return unavailable(error instanceof Error ? error.message : 'The shown instant is not valid.');
  }
  if (shownMs < SERIES_RANGE_START_MS || shownMs > SERIES_RANGE_END_MS) {
    return unavailable('The shown instant is outside the supported range (1800-2200).');
  }
  const state = view.series === null ? null : scrubbedEarthState(view.series, shownMs);
  if (state !== null) return { status: 'ok', state, fetchedAt: shownMs, error: null, frozen: true };
  if (view.status === 'unavailable') return unavailable(view.error ?? 'The time series is unavailable.');
  return { status: 'loading', state: null, fetchedAt: null, error: null, frozen: true };
}
