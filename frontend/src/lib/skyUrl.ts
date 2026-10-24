/**
 * W6-A — shareable sky: the URL params of the Earth & Sky card.
 *
 * Pure functions, no DOM, no store. Two directions:
 * - `parseSkyParams(search)` — read `lat`, `lng`, `at` from a search string
 *   ("?a=b" or "a=b", decoded). STRICT: an invalid parameter is DROPPED with
 *   a human reason in `problems` — never a silent default, never an
 *   exception. Unknown params are ignored, never touched, never a problem
 *   (the Operations page has its own; the hook preserves them).
 * - `buildSkySearch({lat, lng, at})` — emit the search component (no leading
 *   "?", empty string when there is nothing to say).
 *
 * Conventions, from the seams this builds on:
 * - latitude is finite in [-90, 90] (skyStore.setObserver's rule);
 * - longitude is wrapped with `wrapLon` from lib/earth.ts — the interval is
 *   [-180, 180), the store's convention (both store and strip agree);
 * - `at` goes through `parseInstant` (lib/skyClock.ts): strict ISO-8601 with
 *   an explicit zone. The +-24 h window around now is NOT checked here —
 *   that is a rule about "now" and belongs to the hook.
 * - lat and lng must appear together: a lone one cannot move an observer.
 *
 * Coordinates are printed with 4 decimals (~11 m at the equator), `-0`
 * normalised to `0`.
 */
import { wrapLon } from './earth';
import { parseInstant } from './skyClock';

/** The sky params a link can carry. */
export interface SkyUrlParams {
  /** Observer latitude, degrees, [-90, 90]. */
  lat?: number;
  /** Observer longitude, degrees, wrapped into [-180, 180). */
  lng?: number;
  /** A strict-parseable ISO-8601 instant with an explicit zone (kept verbatim;
   * the store normalises to a UTC `Z` string on restore). Live links omit it. */
  at?: string;
}

/** The parse result: the accepted params (absent when dropped) plus reasons. */
export interface SkyUrlParseResult extends SkyUrlParams {
  /** One human-readable line per dropped parameter. Empty when all is well. */
  problems: string[];
  /** Which sky KEYS appeared in the query at all (valid or not, duplicates count). */
  keys: { lat: boolean; lng: boolean; at: boolean };
}

/** 4 decimals, `-0` normalised (toFixed would print "-0.0000"). */
function formatCoord(value: number): string {
  const v = value === 0 ? 0 : value;
  return v.toFixed(4);
}

function parseNumber(raw: string, name: 'lat' | 'lng'): number | undefined {
  const value = Number(raw);
  if (raw.trim() === '' || !Number.isFinite(value)) {
    return undefined;
  }
  return value;
}

/**
 * Read the sky params from a search string. Invalid params are dropped with
 * a reason in `problems`; unknown params are ignored. `lat` and `lng` must
 * both be valid to survive: a lone one is dropped (an observer needs both).
 * A REPEATED sky key (`lat=1&lat=91`) makes that key invalid: first-wins
 * would silently hide the bad second value, so the whole key is rejected
 * with a reason instead.
 */
export function parseSkyParams(search: string): SkyUrlParseResult {
  const stripped = search.startsWith('?') ? search.slice(1) : search;
  const usp = new URLSearchParams(stripped);
  const problems: string[] = [];
  const keys = { lat: usp.has('lat'), lng: usp.has('lng'), at: usp.has('at') };

  let lat: number | undefined;
  let lng: number | undefined;

  if (keys.lat) {
    const values = usp.getAll('lat');
    if (values.length > 1) {
      problems.push(`lat appears ${values.length} times; a duplicated sky key is rejected; dropped`);
    } else {
      const value = parseNumber(values[0], 'lat');
      if (value === undefined || value < -90 || value > 90) {
        problems.push(`lat must be a finite number in [-90, 90], got ${JSON.stringify(values[0])}; dropped`);
      } else {
        lat = value;
      }
    }
  }
  if (keys.lng) {
    const values = usp.getAll('lng');
    if (values.length > 1) {
      problems.push(`lng appears ${values.length} times; a duplicated sky key is rejected; dropped`);
    } else {
      const value = parseNumber(values[0], 'lng');
      if (value === undefined) {
        problems.push(`lng must be a finite number, got ${JSON.stringify(values[0])}; dropped`);
      } else {
        // In-range values pass through untouched (wrapLon's modulo would add
        // floating-point noise to every ordinary pick — the store's own
        // wrapLongitude short-circuits for the same reason); out-of-range ones
        // wrap with the shared wrapLon into [-180, 180).
        lng = value >= -180 && value < 180 ? value : wrapLon(value);
      }
    }
  }
  if ((lat === undefined) !== (lng === undefined)) {
    const lone = lat !== undefined ? 'lat' : 'lng';
    problems.push(`lat and lng must appear together to move the observer; ignoring ${lone}`);
    lat = undefined;
    lng = undefined;
  }

  let at: string | undefined;
  if (keys.at) {
    const values = usp.getAll('at');
    if (values.length > 1) {
      problems.push(`at appears ${values.length} times; a duplicated sky key is rejected; dropped`);
    } else {
      try {
        parseInstant(values[0]);
        at = values[0];
      } catch (error) {
        const reason = error instanceof Error ? error.message : String(error);
        problems.push(`${reason}; at dropped`);
      }
    }
  }

  const result: SkyUrlParseResult = { problems, keys };
  if (lat !== undefined) result.lat = lat;
  if (lng !== undefined) result.lng = lng;
  if (at !== undefined) result.at = at;
  return result;
}

/**
 * Emit the sky search component (no leading "?"): `lat`, `lng` (4 decimals)
 * then `at` verbatim when present. Empty string when there is nothing to
 * encode. Non-finite coordinates are omitted (build is only fed store
 * values; the guard keeps a bad write from producing "NaN" in a URL).
 */
export function buildSkySearch(params: SkyUrlParams): string {
  const usp = new URLSearchParams();
  if (params.lat !== undefined && Number.isFinite(params.lat)) {
    usp.set('lat', formatCoord(params.lat));
  }
  if (params.lng !== undefined && Number.isFinite(params.lng)) {
    usp.set('lng', formatCoord(params.lng));
  }
  if (typeof params.at === 'string' && params.at !== '') {
    usp.set('at', params.at);
  }
  return usp.toString();
}
