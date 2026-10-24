/**
 * Shared earth-state for the globes. One poll of GET /astrology/earth-state
 * per minute while at least one subscriber is mounted and the tab is visible.
 */
import { useEffect, useMemo } from 'react';
import { create, type StoreApi, type UseBoundStore } from 'zustand';
import type { BodySubPoint, EarthState } from '../lib/earth';
import { apiUrl } from '../utils/api';
import { useScrubGate } from './scrubGate';
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
/**
 * A live request that has not settled in this long is aborted and the slice
 * becomes `unavailable` (state null). The next poll, at most 60 s later,
 * retries; a prior success is never extrapolated indefinitely as if current.
 */
const REQUEST_TIMEOUT_MS = 15_000;

type EarthStore = EarthStateSlice & {
  refresh(): Promise<void>;
  subscribe(): () => void;
};

let subscribers = 0;
let timer: ReturnType<typeof setInterval> | null = null;
let inflight: Promise<void> | null = null;
let visibilityBound = false;
let generation = 0;
let controller: AbortController | null = null;

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

function cancelLiveRequest(): void {
  generation += 1;
  controller?.abort();
  controller = null;
  inflight = null;
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
    const myGeneration = (generation += 1);
    controller?.abort();
    const myController = new AbortController();
    controller = myController;
    const timeout = setTimeout(() => myController.abort(), REQUEST_TIMEOUT_MS);
    const run = (async () => {
      if (get().status !== 'ok') {
        set({ status: 'loading', error: null });
      }
      try {
        const res = await fetch(apiUrl('/astrology/earth-state'), { signal: myController.signal });
        if (myGeneration !== generation) return; // superseded/cancelled: never write
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
        if (myGeneration !== generation) return;
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
        if (myGeneration !== generation) return;
        const timedOut = err instanceof Error && err.name === 'AbortError';
        set({
          status: 'unavailable',
          state: null,
          fetchedAt: null,
          error: timedOut
            ? 'live earth-state request timed out after 15 s'
            : err instanceof Error
              ? err.message
              : 'ephemeris unavailable',
        });
      } finally {
        clearTimeout(timeout);
      }
    })();
    inflight = run;
    try {
      await run;
    } finally {
      if (inflight === run) inflight = null;
      if (controller === myController) controller = null;
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
        cancelLiveRequest();
      }
    };
  },
}));

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
  // The scrub machinery (series store/client/maths) is a lazy chunk; this gate
  // watches `at` and loads it only when the sky is first scrubbed.
  const gate = useScrubGate();
  return useMemo<EarthStateSlice>(() => {
    if (at === null) return { status, state, fetchedAt, error };
    if (gate.module === null) {
      return {
        status: gate.view.status === 'unavailable' ? 'unavailable' : 'loading',
        state: null,
        fetchedAt: null,
        error: gate.view.error,
        frozen: true,
      };
    }
    return gate.module.scrubEarthStateSlice(at, gate.view);
  }, [at, status, state, fetchedAt, error, gate]);
}
