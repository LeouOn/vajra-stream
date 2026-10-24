/**
 * Always-loaded gate for the scrub machinery (row W3-K).
 *
 * `stores/earthStateStore.ts` is imported by the always-loaded globe, so it
 * must not statically import the series store, the series client or the scrub
 * maths (they are only needed once a person scrubs time). This module is the
 * tiny bridge:
 *
 *  - it watches `skyStore.at` and, the first time `at` becomes non-null,
 *    dynamically imports `./skySeriesStore` exactly once (Rollup puts it in a
 *    lazy chunk);
 *  - while that chunk loads the view is `{status:'loading', series:null}`;
 *    a failed chunk load is `{status:'unavailable'}` with a readable reason
 *    and is retried on the next scrub;
 *  - once loaded it ref-counts one subscription to the shared series store,
 *    so a mounted globe/strip keeps the store owner alive without any
 *    component importing it.
 *
 * The hook always calls the same hooks (`useSkyStore`, `useEffect`,
 * `useSyncExternalStore`), so hook order is stable whether or not the chunk
 * has loaded.
 */
import { useEffect, useSyncExternalStore } from 'react';
import { useSkyStore } from './skyStore';
import type { SkySeriesView } from './skySeriesStore';

type SeriesModule = typeof import('./skySeriesStore');
type Loader = () => Promise<SeriesModule>;

const defaultLoader: Loader = () => import('./skySeriesStore');

const LOADING: SkySeriesView = { status: 'loading', series: null, error: null, errorKind: null };
const FAILED: SkySeriesView = {
  status: 'unavailable',
  series: null,
  error:
    'The time-series module could not be loaded; it will be retried the next time the sky is scrubbed.',
  errorKind: null,
};

export interface ScrubGateSnapshot {
  view: SkySeriesView;
  module: SeriesModule | null;
}

let loadModule: Loader = defaultLoader;
let loaded: SeriesModule | null = null;
let loadState: 'idle' | 'loading' | 'ready' | 'failed' = 'idle';
let cached: ScrubGateSnapshot = { view: LOADING, module: null };
const listeners = new Set<() => void>();
let storeChangeUnsubscribe: (() => void) | null = null;
let storeRefUnsubscribe: (() => void) | null = null;

function viewFromStore(): SkySeriesView {
  if (loaded === null) return loadState === 'failed' ? FAILED : LOADING;
  const state = loaded.useSkySeriesStore.getState();
  return { status: state.status, series: state.series, error: state.error, errorKind: state.errorKind };
}

function sameView(a: SkySeriesView, b: SkySeriesView): boolean {
  return (
    a.status === b.status &&
    a.series === b.series &&
    a.error === b.error &&
    a.errorKind === b.errorKind
  );
}

/** A referentially stable snapshot for `useSyncExternalStore`. */
function getSnapshot(): ScrubGateSnapshot {
  const view = viewFromStore();
  if (cached.module !== loaded || !sameView(cached.view, view)) {
    cached = { view, module: loaded };
  }
  return cached;
}

function publish(): void {
  const before = cached;
  getSnapshot();
  if (before === cached) return;
  for (const listener of Array.from(listeners)) listener();
}

function ensureStoreSubscription(): void {
  if (loaded === null || storeRefUnsubscribe !== null) return;
  // One ref-counted owner so the series store fetches while a consumer is mounted.
  storeRefUnsubscribe = loaded.useSkySeriesStore.getState().subscribe();
  storeChangeUnsubscribe = loaded.useSkySeriesStore.subscribe(publish);
}

function dropStoreSubscription(): void {
  storeChangeUnsubscribe?.();
  storeChangeUnsubscribe = null;
  storeRefUnsubscribe?.();
  storeRefUnsubscribe = null;
}

function ensureLoaded(): void {
  if (loadState === 'loading' || loadState === 'ready') return;
  loadState = 'loading';
  publish();
  loadModule().then(
    (module) => {
      loaded = module;
      loadState = 'ready';
      ensureStoreSubscription();
      publish();
    },
    () => {
      loadState = 'failed';
      publish();
    },
  );
}

function resetFailedLoad(): void {
  if (loadState !== 'failed') return;
  loadState = 'idle';
  publish();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (listeners.size === 1) ensureStoreSubscription();
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) dropStoreSubscription();
  };
}

/**
 * The shared series view for the current scrub state; `module` is null until
 * the lazy chunk has loaded. Calling this while live is free (nothing fetched).
 */
export function useScrubGate(): ScrubGateSnapshot {
  const at = useSkyStore((state) => state.at);
  useEffect(() => {
    if (at !== null) ensureLoaded();
    else resetFailedLoad();
  }, [at]);
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

/** Test-only: replace the loader / clear the gate so the chunk-load path can be exercised. */
export function resetScrubGateForTest(loader: Loader | null = null): void {
  dropStoreSubscription();
  loadModule = loader ?? defaultLoader;
  loaded = null;
  loadState = 'idle';
  cached = { view: LOADING, module: null };
}
