/**
 * Earth & Sky wave 3 — the observer + clock store.
 *
 * One place (`lat`, `lng`, optional `label`) and one instant (`at`) that the
 * dome, the globes and the flat strip will all read, so picking a place or
 * scrubbing time moves everything together.
 *
 * - `at === null` is **live**; `at` is otherwise an ISO-8601 UTC instant
 *   ending in `Z` (normalised on write). "Pause" is `setAt(now)`; there is no
 *   separate paused flag.
 * - The store never reads the clock: the live "now" belongs to the caller
 *   (`lib/skyClock.ts`), which also clamps a scrub to +-24 h.
 * - No persistence, no network, no components, no timers.
 */
import { create, type StoreApi, type UseBoundStore } from 'zustand';
import { parseInstant } from '../lib/skyClock';
import { DEFAULT_LAT, DEFAULT_LNG } from '../lib/geo';

export interface SkyStoreState {
  /** Observer latitude in degrees, [-90, 90]. */
  lat: number;
  /** Observer longitude in degrees, wrapped into [-180, 180). */
  lng: number;
  /** Optional human place name ("Greenwich", "Tokyo"); absent when unknown. */
  label?: string;
  /** ISO-8601 UTC instant ending in `Z`, or null for live. */
  at: string | null;
}

export interface SkyStoreActions {
  /** Move the observer. Latitude out of range or non-finite throws RangeError. */
  setObserver(lat: number, lng: number, label?: string): void;
  /**
   * Pin the shown instant (null = live), normalised to a UTC `...Z` string.
   * Only ISO-8601 with an explicit zone is accepted (naive strings would mean
   * local time); anything else throws TypeError.
   */
  setAt(at: string | null): void;
  /** Return to live. */
  goLive(): void;
}

export type SkyStore = SkyStoreState & SkyStoreActions;

/**
 * Wrap a longitude into [-180, 180); -180 and 180 both map to -180.
 * `-0` is normalised to `+0` so the stored value has one canonical zero
 * (`Object.is(-0, 0)` is false and would leak into equality checks).
 */
function wrapLongitude(lng: number): number {
  // Leave an in-range value exactly as given: the modulo formula would add
  // floating-point noise (-0.0015 -> -0.0014999999999645297) to every pick.
  if (lng >= -180 && lng < 180) return lng === 0 ? 0 : lng;
  const wrapped = ((((lng + 180) % 360) + 360) % 360) - 180;
  return wrapped === 0 ? 0 : wrapped;
}

export const useSkyStore: UseBoundStore<StoreApi<SkyStore>> = create<SkyStore>((set) => ({
  lat: DEFAULT_LAT,
  lng: DEFAULT_LNG,
  label: undefined,
  at: null,

  setObserver(lat, lng, label) {
    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      throw new RangeError(`setObserver: latitude must be a finite number in [-90, 90], got ${lat}`);
    }
    if (!Number.isFinite(lng)) {
      throw new RangeError(`setObserver: longitude must be a finite number, got ${lng}`);
    }
    // Validate both before mutating, so a rejected call leaves the state intact.
    // `lat === 0 ? 0 : lat` normalises -0 (see wrapLongitude).
    set({ lat: lat === 0 ? 0 : lat, lng: wrapLongitude(lng), label: label ?? undefined });
  },

  setAt(at) {
    if (at === null) {
      set({ at: null });
      return;
    }
    if (typeof at !== 'string') {
      throw new TypeError('setAt: expected an ISO-8601 instant string or null');
    }
    // Strict, zone-explicit parsing lives in lib/skyClock (shared with the
    // clock helpers); it throws TypeError for naive/loose/malformed input.
    set({ at: new Date(parseInstant(at)).toISOString() });
  },

  goLive() {
    set({ at: null });
  },
}));
