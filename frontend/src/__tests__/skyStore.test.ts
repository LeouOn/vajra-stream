/**
 * W3-A tests for frontend/src/stores/skyStore.ts (observer + clock state).
 *
 * The store is clock-free: setAt() stores the given instant and never reads
 * Date.now(), so no fake timers are needed. scrub clamping belongs to
 * lib/skyClock.ts and the caller (see skyClock.test.ts).
 */
import { beforeEach, describe, expect, it } from 'vitest';
import { DEFAULT_LAT, DEFAULT_LNG } from '../lib/geo';
import { useSkyStore } from '../stores/skyStore';

const PAUSED = '2026-10-24T08:00:00Z';

function reset() {
  useSkyStore.setState({ lat: DEFAULT_LAT, lng: DEFAULT_LNG, label: undefined, at: null });
}

describe('skyStore defaults', () => {
  beforeEach(reset);

  it('starts at the app defaults, live, with no label', () => {
    const state = useSkyStore.getState();
    expect(state.lat).toBe(DEFAULT_LAT);
    expect(state.lng).toBe(DEFAULT_LNG);
    expect(state.label).toBeUndefined();
    expect(state.at).toBeNull();
    expect(DEFAULT_LAT).toBe(37.7749);
    expect(DEFAULT_LNG).toBe(-122.4194);
  });

  it('has no persistence middleware', () => {
    expect((useSkyStore as unknown as { persist?: unknown }).persist).toBeUndefined();
  });
});

describe('setObserver', () => {
  beforeEach(reset);

  it('sets latitude, longitude and label', () => {
    useSkyStore.getState().setObserver(51.4779, -0.0015, 'Greenwich');
    expect(useSkyStore.getState().lat).toBe(51.4779);
    expect(useSkyStore.getState().lng).toBe(-0.0015);
    expect(useSkyStore.getState().label).toBe('Greenwich');
  });

  it('clears a stale label when the new place has none', () => {
    useSkyStore.getState().setObserver(51.4779, -0.0015, 'Greenwich');
    useSkyStore.getState().setObserver(-33.8688, 151.2093);
    expect(useSkyStore.getState().label).toBeUndefined();
  });

  it('accepts the poles and the antimeridian', () => {
    useSkyStore.getState().setObserver(90, 180);
    expect(useSkyStore.getState().lat).toBe(90);
    expect(useSkyStore.getState().lng).toBe(-180);
    useSkyStore.getState().setObserver(-90, -180);
    expect(useSkyStore.getState().lat).toBe(-90);
    expect(useSkyStore.getState().lng).toBe(-180);
  });

  it('wraps longitude into [-180, 180) at both ends', () => {
    const cases: Array<[number, number]> = [
      [180, -180],
      [-180, -180],
      [181, -179],
      [-181, 179],
      [360, 0],
      [-360, 0],
      [540, -180],
      [-540, -180],
      [359.5, -0.5],
      [-359.5, 0.5],
    ];
    for (const [given, expected] of cases) {
      useSkyStore.getState().setObserver(10, given);
      expect(useSkyStore.getState().lng, `lng ${given}`).toBe(expected);
    }
  });

  it('rejects a latitude outside [-90, 90] with RangeError and leaves state unchanged', () => {
    useSkyStore.getState().setObserver(10, 20, 'before');
    for (const bad of [-90.0001, 90.0001, 180, -180, Number.NaN, Number.POSITIVE_INFINITY]) {
      expect(() => useSkyStore.getState().setObserver(bad, 20), `lat ${bad}`).toThrow(RangeError);
    }
    const state = useSkyStore.getState();
    expect(state.lat).toBe(10);
    expect(state.lng).toBe(20);
    expect(state.label).toBe('before');
  });

  it('normalises negative zero: both axes store +0', () => {
    // Object.is distinguishes -0 from +0, and -0 can leak in from a pick or a
    // wrapped longitude. The store owns the canonical value.
    useSkyStore.getState().setObserver(0, -0);
    expect(Object.is(useSkyStore.getState().lat, 0)).toBe(true);
    expect(Object.is(useSkyStore.getState().lng, 0)).toBe(true);

    useSkyStore.getState().setObserver(-0, 0);
    expect(Object.is(useSkyStore.getState().lat, 0)).toBe(true);
    expect(Object.is(useSkyStore.getState().lng, 0)).toBe(true);
  });

  it('rejects a non-finite longitude with RangeError', () => {
    for (const bad of [Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]) {
      expect(() => useSkyStore.getState().setObserver(10, bad), `lng ${bad}`).toThrow(RangeError);
    }
  });
});

describe('setAt / goLive', () => {
  beforeEach(reset);

  it('at = null means live', () => {
    useSkyStore.getState().setAt(PAUSED);
    expect(useSkyStore.getState().at).toBe('2026-10-24T08:00:00.000Z');
    useSkyStore.getState().setAt(null);
    expect(useSkyStore.getState().at).toBeNull();
  });

  it('pausing is setAt(now) and is distinct from live', () => {
    const now = Date.parse('2026-10-24T09:00:00Z');
    useSkyStore.getState().setAt(new Date(now).toISOString());
    expect(useSkyStore.getState().at).toBe('2026-10-24T09:00:00.000Z');
    expect(useSkyStore.getState().at).not.toBeNull();
  });

  it('normalises the instant to UTC ISO ending in Z', () => {
    useSkyStore.getState().setAt('2026-10-24T10:00:00+02:00');
    const at = useSkyStore.getState().at;
    expect(at).toBe('2026-10-24T08:00:00.000Z');
    expect(at!.endsWith('Z')).toBe(true);
    expect(Date.parse(at!)).toBe(Date.parse('2026-10-24T08:00:00Z'));
  });

  it('keeps sub-second precision as a valid instant', () => {
    useSkyStore.getState().setAt('2026-10-24T08:00:00.250Z');
    expect(useSkyStore.getState().at).toBe('2026-10-24T08:00:00.250Z');
  });

  it('rejects a malformed instant with TypeError and leaves state unchanged', () => {
    useSkyStore.getState().setAt(PAUSED);
    for (const bad of ['not-a-date', '', '2026-13-45T99:99:99Z', 'banana']) {
      expect(() => useSkyStore.getState().setAt(bad), bad).toThrow(TypeError);
    }
    expect(useSkyStore.getState().at).toBe('2026-10-24T08:00:00.000Z');
  });

  it('rejects naive and date-only strings (they would mean local time on the client)', () => {
    useSkyStore.getState().setAt(PAUSED);
    for (const bad of [
      '2026-10-24T10:00:00',
      '2026-10-24T10:00',
      '2026-10-24',
      'Oct 24 2026',
      '2026-10-24 10:00:00Z',
      '2026-10-24T10:00:00z',
      '0000-01-01T00:00:00Z',
    ]) {
      expect(() => useSkyStore.getState().setAt(bad), bad).toThrow(TypeError);
    }
    expect(useSkyStore.getState().at).toBe('2026-10-24T08:00:00.000Z');
  });

  it('normalises every accepted zone form to the same Z instant', () => {
    for (const good of [
      '2026-10-24T10:00:00Z',
      '2026-10-24T10:00Z',
      '2026-10-24T12:00:00+02:00',
      '2026-10-24T05:00:00-05:00',
    ]) {
      useSkyStore.getState().setAt(good);
      expect(useSkyStore.getState().at, good).toBe('2026-10-24T10:00:00.000Z');
    }
    useSkyStore.getState().setAt('2026-10-24T10:00:00.5Z');
    expect(useSkyStore.getState().at).toBe('2026-10-24T10:00:00.500Z');
  });

  it('goLive returns to live from paused', () => {
    useSkyStore.getState().setAt(PAUSED);
    useSkyStore.getState().goLive();
    expect(useSkyStore.getState().at).toBeNull();
  });

  it('goLive is a no-op when already live', () => {
    useSkyStore.getState().goLive();
    expect(useSkyStore.getState().at).toBeNull();
  });

  it('goLive only clears the instant: it must not reset place or label', () => {
    useSkyStore.getState().setObserver(51.4779, -0.0015, 'Greenwich');
    useSkyStore.getState().setAt(PAUSED);
    useSkyStore.getState().goLive();
    const state = useSkyStore.getState();
    expect(state.at).toBeNull();
    expect(state.lat).toBe(51.4779);
    expect(state.lng).toBe(-0.0015);
    expect(state.label).toBe('Greenwich');
  });
});
