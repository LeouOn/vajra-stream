/**
 * W6-A — lib/skyUrl: parsing and building the shareable-sky query params.
 *
 * Pure functions, no DOM: `parseSkyParams` reads a search string
 * ("?a=b" or "a=b"), `buildSkySearch` emits one (no leading "?", empty string
 * when there is nothing to say).
 *
 * Rules under test (from the W6-A row):
 * - lat: finite, in [-90, 90]; anything else is DROPPED with a reason.
 * - lng: finite, then wrapped with wrapLon ([-180, 180)); anything else dropped.
 * - lat and lng must appear together; a lone one is dropped with a reason.
 * - at: strict parseInstant; malformed dropped with the parser's reason.
 * - unknown params are never touched (and never a problem).
 * - build prints coordinates with 4 decimals and keeps `at` verbatim.
 */
import { describe, expect, it } from 'vitest';

import { buildSkySearch, parseSkyParams } from '../../lib/skyUrl';
import { parseInstant } from '../../lib/skyClock';

describe('parseSkyParams', () => {
  it('parses a valid observer and instant', () => {
    const got = parseSkyParams('?lat=48.85&lng=2.35&at=2026-10-24T10:00:00Z');
    expect(got.lat).toBe(48.85);
    expect(got.lng).toBe(2.35);
    expect(got.at).toBe('2026-10-24T10:00:00Z');
    expect(got.problems).toEqual([]);
  });

  it('accepts a search string without the leading "?"', () => {
    const got = parseSkyParams('lat=-33.87&lng=151.21');
    expect(got.lat).toBe(-33.87);
    expect(got.lng).toBe(151.21);
    expect(got.at).toBeUndefined();
    expect(got.problems).toEqual([]);
  });

  it('accepts an empty search', () => {
    expect(parseSkyParams('')).toEqual({ problems: [], keys: { lat: false, lng: false, at: false } });
    expect(parseSkyParams('?')).toEqual({ problems: [], keys: { lat: false, lng: false, at: false } });
  });

  it('decodes percent-encoded instants (a URLSearchParams round trip)', () => {
    const built = buildSkySearch({ lat: 1, lng: 2, at: '2026-10-24T10:00:00.000Z' });
    const got = parseSkyParams(built);
    expect(got.problems).toEqual([]);
    expect(got.at).toBe('2026-10-24T10:00:00.000Z');
  });

  it('drops lat out of range with a reason', () => {
    const got = parseSkyParams('?lat=91&lng=0');
    expect(got.lat).toBeUndefined();
    // lng was valid on its own but lat+lng must appear together, so both drop.
    expect(got.lng).toBeUndefined();
    expect(got.problems.length).toBe(2);
    expect(got.problems[0]).toMatch(/lat/);
    expect(got.problems.some((p) => p.includes('together'))).toBe(true);
  });

  it('accepts the poles ±90', () => {
    expect(parseSkyParams('?lat=90&lng=0').lat).toBe(90);
    expect(parseSkyParams('?lat=-90&lng=0').lat).toBe(-90);
  });

  it('drops a non-numeric lng with a reason', () => {
    const got = parseSkyParams('?lat=10&lng=NaN');
    expect(got.lng).toBeUndefined();
    expect(got.problems[0]).toMatch(/lng/);
    expect(got.problems.some((p) => p.includes('together'))).toBe(true);
  });

  it('drops a lone lat (lng missing) with a together-reason', () => {
    const got = parseSkyParams('?lat=48.85');
    expect(got.lat).toBeUndefined();
    expect(got.problems).toEqual([expect.stringMatching(/together/)]);
  });

  it('drops a lone lng too', () => {
    const got = parseSkyParams('?lng=2.35');
    expect(got.lng).toBeUndefined();
    expect(got.problems).toEqual([expect.stringMatching(/together/)]);
  });

  it('drops a garbage instant with the parser reason, keeping valid lat/lng', () => {
    const got = parseSkyParams('?lat=1.5&lng=2.5&at=garbage');
    expect(got.at).toBeUndefined();
    expect(got.lat).toBe(1.5);
    expect(got.lng).toBe(2.5);
    expect(got.problems.length).toBe(1);
    expect(got.problems[0]).toMatch(/at/);
  });

  it('rejects the loose ISO shapes parseInstant rejects (space separator, naive)', () => {
    for (const at of ['2026-10-24 10:00:00Z', '2026-10-24T10:00:00', '20261024T100000Z']) {
      const got = parseSkyParams(`?at=${at}`);
      expect(got.at, at).toBeUndefined();
      expect(got.problems.length, at).toBe(1);
    }
  });

  it('accepts an instant with a numeric zone offset verbatim (the + is %2B in a link)', () => {
    const got = parseSkyParams(`?at=${encodeURIComponent('2026-10-24T12:00:00+02:00')}`);
    expect(got.at).toBe('2026-10-24T12:00:00+02:00');
    expect(parseInstant(got.at as string)).toBe(parseInstant('2026-10-24T10:00:00Z'));
  });

  it('a three-day-old instant still PARSES (the +-24 h window is the hook\'s rule)', () => {
    const old = new Date(Date.now() - 3 * 24 * 3600_000).toISOString();
    const got = parseSkyParams(`?at=${old}`);
    expect(got.at).toBe(old);
    expect(got.problems).toEqual([]);
  });

  it('wraps lng into [-180, 180)', () => {
    expect(parseSkyParams('?lat=0&lng=190').lng).toBe(-170);
    expect(parseSkyParams('?lat=0&lng=180').lng).toBe(-180);
    expect(parseSkyParams('?lat=0&lng=-180').lng).toBe(-180);
    expect(parseSkyParams('?lat=0&lng=540').lng).toBe(-180);
  });

  it('never touches or complains about unknown params', () => {
    const got = parseSkyParams('?op=42&tab=broadcast&lat=1&lng=2');
    expect(got.problems).toEqual([]);
    expect(got.lat).toBe(1);
    expect(got.lng).toBe(2);
    expect(got.keys).toEqual({ lat: true, lng: true, at: false });
  });

  it('flags keys even when their values are dropped (the link tried)', () => {
    const got = parseSkyParams('?lat=91&at=garbage');
    expect(got.keys).toEqual({ lat: true, lng: false, at: true });
  });
});

describe('parseSkyParams — duplicated sky keys (W6-A2)', () => {
  it('a duplicated lat makes lat invalid (first-wins would hide the bad value)', () => {
    const got = parseSkyParams('?lat=1&lat=91&lng=2');
    expect(got.lat).toBeUndefined();
    // lng was valid alone but the pair rule drops it too.
    expect(got.lng).toBeUndefined();
    expect(got.problems.some((p) => p.includes('lat appears 2 times'))).toBe(true);
    expect(got.problems.some((p) => p.includes('together'))).toBe(true);
    expect(got.keys.lat).toBe(true);
  });

  it('a duplicated lng is invalid', () => {
    const got = parseSkyParams('?lat=1&lng=2&lng=190');
    expect(got.lat).toBeUndefined();
    expect(got.lng).toBeUndefined();
    expect(got.problems.some((p) => p.includes('lng appears 2 times'))).toBe(true);
  });

  it('a duplicated at is invalid (dropped, Live-side note territory)', () => {
    const now = new Date().toISOString();
    const got = parseSkyParams(`?at=${now}&at=${now}`);
    expect(got.at).toBeUndefined();
    expect(got.problems.some((p) => p.includes('at appears 2 times'))).toBe(true);
    expect(got.keys.at).toBe(true);
  });

  it('duplicated UNKNOWN keys are not the parser\'s business', () => {
    const got = parseSkyParams('?op=1&op=2&lat=1&lng=2');
    expect(got.problems).toEqual([]);
    expect(got.lat).toBe(1);
  });
});

describe('buildSkySearch', () => {
  it('prints lat/lng with 4 decimals and keeps at verbatim', () => {
    expect(buildSkySearch({ lat: 37.77494, lng: -122.41941, at: '2026-10-24T10:00:00Z' })).toBe(
      'lat=37.7749&lng=-122.4194&at=2026-10-24T10%3A00%3A00Z',
    );
  });

  it('omits at when absent (a live link)', () => {
    expect(buildSkySearch({ lat: 0, lng: 0 })).toBe('lat=0.0000&lng=0.0000');
  });

  it('normalises -0 to 0.0000', () => {
    expect(buildSkySearch({ lat: -0, lng: 0 })).toBe('lat=0.0000&lng=0.0000');
  });

  it('returns an empty string when there is nothing to encode', () => {
    expect(buildSkySearch({})).toBe('');
  });

  it('round-trips through parseSkyParams', () => {
    const params = { lat: 48.8584, lng: 2.2945, at: '2026-12-21T20:50:00Z' };
    const back = parseSkyParams(buildSkySearch(params));
    expect(back.lat).toBe(48.8584);
    expect(back.lng).toBe(2.2945);
    expect(back.at).toBe('2026-12-21T20:50:00Z');
    expect(back.problems).toEqual([]);
  });
});
