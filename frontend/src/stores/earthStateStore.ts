/**
 * Shared earth-state for the globes. One poll of GET /astrology/earth-state
 * per minute while at least one subscriber is mounted and the tab is visible.
 */
import { useEffect, useMemo } from 'react';
import { create, type StoreApi, type UseBoundStore } from 'zustand';
import type { BodySubPoint, EarthState } from '../lib/earth';
import { parseInstant } from '../lib/skyClock';
import { SERIES_RANGE_END_MS, SERIES_RANGE_START_MS } from '../lib/skyScrub';
import { apiUrl } from '../utils/api';
import { scrubbedEarthState, useSkySeries, type SkySeriesView } from './skySeriesStore';
import { useSkyStore } from './skyStore';

export type EarthStateStatus = 'idle' | 'loading' | 'ok' | 'unavailable';

export interface EarthStateSlice {
  status: EarthStateStatus;
  state: EarthState | null;
  fetchedAt: number | null;
  error: string | null;
  /**
   * True when `state` is the sky at a scrubbed instant (W3-I), not the live poll: it must not be advanced by
   * wall-clock time. `fetchedAt` is then the shown instant itself; consumers age a state with
   * `shownNowMs(slice, now)` (lib/earth.ts), which is 0 for a frozen slice. Absent/false when live.
   */
  frozen?: boolean;
}

const POLL_MS = 60_000;

type EarthStore = EarthStateSlice & {
  refresh(): Promise<void>;
  subscribe(): () => void;
};

let subscribers = 0;
let timer: ReturnType<typeof setInterval> | null = null;
let inflight: Promise<void> | null = null;
let visibilityBound = false;

function isBody(value: unknown): value is BodySubPoint {
  if (typeof value !== 'object' || value === null) return false;
  const body = value as Record<string, unknown>;
  return (
    typeof body.id === 'string' &&
    typeof body.lat === 'number' &&
    typeof body.lon === 'number' &&
    Number.isFinite(body.lat) &&
    Number.isFinite(body.lon)
  );
}

function isEarthState(value: unknown): value is EarthState {
  if (typeof value !== 'object' || value === null) return false;
  const record = value as Record<string, unknown>;
  return isBody(record.sun) && isBody(record.moon) && Array.isArray(record.planets) && record.planets.every(isBody);
}

function stopTimer(): void {
  if (timer === null) return;
  clearInterval(timer);
  timer = null;
}

function startTimer(): void {
  if (timer !== null) return;
  if (typeof document !== 'undefined' && document.hidden) return;
  timer = setInterval(() => {
    void useEarthStateStore.getState().refresh();
  }, POLL_MS);
}

function onVisibility(): void {
  if (subscribers <= 0) return;
  if (typeof document !== 'undefined' && document.hidden) {
    stopTimer();
    return;
  }
  startTimer();
  void useEarthStateStore.getState().refresh();
}

function bindVisibility(): void {
  if (visibilityBound || typeof document === 'undefined') return;
  document.addEventListener('visibilitychange', onVisibility);
  visibilityBound = true;
}

function unbindVisibility(): void {
  if (!visibilityBound || typeof document === 'undefined') return;
  document.removeEventListener('visibilitychange', onVisibility);
  visibilityBound = false;
}

export const useEarthStateStore: UseBoundStore<StoreApi<EarthStore>> = create<EarthStore>((set, get) => ({
  status: 'idle',
  state: null,
  fetchedAt: null,
  error: null,
  async refresh() {
    if (inflight) return inflight;
    const run = (async () => {
      if (get().status !== 'ok') {
        set({ status: 'loading', error: null });
      }
      try {
        const res = await fetch(apiUrl('/astrology/earth-state'));
        if (!res.ok) {
          set({
            status: 'unavailable',
            state: null,
            fetchedAt: null,
            error: `HTTP ${res.status}`,
          });
          return;
        }
        const body: unknown = await res.json();
        if (!isEarthState(body)) {
          set({
            status: 'unavailable',
            state: null,
            fetchedAt: null,
            error: 'invalid earth-state',
          });
          return;
        }
        set({
          status: 'ok',
          state: body,
          fetchedAt: Date.now(),
          error: null,
        });
      } catch (err) {
        set({
          status: 'unavailable',
          state: null,
          fetchedAt: null,
          error: err instanceof Error ? err.message : 'ephemeris unavailable',
        });
      }
    })();
    inflight = run;
    try {
      await run;
    } finally {
      if (inflight === run) inflight = null;
    }
  },
  subscribe() {
    subscribers += 1;
    if (subscribers === 1) {
      bindVisibility();
      if (typeof document === 'undefined' || !document.hidden) {
        void get().refresh();
        startTimer();
      }
    }
    let open = true;
    return () => {
      if (!open) return;
      open = false;
      subscribers = Math.max(0, subscribers - 1);
      if (subscribers === 0) {
        stopTimer();
        unbindVisibility();
      }
    };
  },
}));

/** The slice for a scrubbed instant: built from the shared series, or loading, or unavailable. Never the live state. */
function scrubbedSlice(at: string, view: SkySeriesView): EarthStateSlice {
  const unavailable = (error: string): EarthStateSlice => ({
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

/**
 * The earth state every globe, the strip and the mini globe draw. Live (`skyStore.at === null`): the shared poll,
 * exactly as before. Scrubbed: a frozen slice for that instant from the shared series store; the live poll is
 * unsubscribed (so its timer stops) until the sky goes live again.
 */
export function useEarthState(): EarthStateSlice {
  const at = useSkyStore((s) => s.at);
  const scrubbed = at !== null;
  const status = useEarthStateStore((s) => s.status);
  const state = useEarthStateStore((s) => s.state);
  const fetchedAt = useEarthStateStore((s) => s.fetchedAt);
  const error = useEarthStateStore((s) => s.error);
  useEffect(() => (scrubbed ? undefined : useEarthStateStore.getState().subscribe()), [scrubbed]);
  const series = useSkySeries(scrubbed);
  const { status: seriesStatus, series: seriesWindow, error: seriesError } = series;
  return useMemo<EarthStateSlice>(() => {
    if (at === null) return { status, state, fetchedAt, error };
    return scrubbedSlice(at, { status: seriesStatus, series: seriesWindow, error: seriesError, errorKind: null });
  }, [at, status, state, fetchedAt, error, seriesStatus, seriesWindow, seriesError]);
}
