/**
 * Shared earth-state for the globes. One poll of GET /astrology/earth-state
 * per minute while at least one subscriber is mounted and the tab is visible.
 */
import { useEffect } from 'react';
import { create, type StoreApi, type UseBoundStore } from 'zustand';
import type { BodySubPoint, EarthState } from '../lib/earth';
import { apiUrl } from '../utils/api';

export type EarthStateStatus = 'idle' | 'loading' | 'ok' | 'unavailable';

export interface EarthStateSlice {
  status: EarthStateStatus;
  state: EarthState | null;
  fetchedAt: number | null;
  error: string | null;
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

/** Subscribe on mount and unsubscribe on unmount. */
export function useEarthState(): EarthStateSlice {
  const status = useEarthStateStore((s) => s.status);
  const state = useEarthStateStore((s) => s.state);
  const fetchedAt = useEarthStateStore((s) => s.fetchedAt);
  const error = useEarthStateStore((s) => s.error);
  useEffect(() => useEarthStateStore.getState().subscribe(), []);
  return { status, state, fetchedAt, error };
}
