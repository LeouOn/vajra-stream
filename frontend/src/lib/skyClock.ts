/**
 * Earth & Sky wave 3 — the sky clock (pure; no React, no timers, no storage).
 *
 * One instant is shared by the dome, the globes and the flat strip. `at` is an
 * ISO-8601 UTC instant string, or `null` for **live**: the caller supplies the
 * real "now" as `nowMs`, so this module never reads the clock and stays
 * deterministic in tests.
 *
 * "Pause" is simply `at = now`; there is no separate paused flag. A scrub is
 * limited to +-24 h around the real now by `clampScrub` (the time-control
 * caller applies it before calling the store's `setAt`).
 */

/** How far a scrub may move from the real now, in milliseconds (24 h). */
export const SCRUB_LIMIT_MS = 24 * 3600_000;

/**
 * ISO-8601 date-time with an EXPLICIT zone, uppercase designators only.
 *
 * `Date.parse` is not used: for a naive date-time it reads LOCAL time, so the
 * same state would mean a different instant on every machine, while the
 * backend treats naive times as UTC.
 *
 * Deliberately stricter than the server's `datetime.fromisoformat`, whose
 * accepted grammar is wider. These are rejected here **on purpose** and
 * pinned by a test:
 *   - space separator        "2026-10-24 10:00:00Z"
 *   - date only              "2026-10-24"
 *   - basic format           "20261024T100000Z"
 *   - ISO week date          "2026-W43-4T10:00:00Z"
 *   - surrounding whitespace " 2026-10-24T10:00:00Z", "...Z\n"
 *   - lowercase designators  "2026-10-24t10:00:00z"
 *   - year 0000              "0000-01-01T00:00:00Z" (the server 422s year 0)
 * Why: this clock only ever sees instants the app produced with
 * `toISOString()` or read from the server; any other shape means pasted or
 * fabricated input, and silently reinterpreting it is the bug class we are
 * closing. Year 0001 is accepted (the server accepts it too).
 *
 * Accepted: `YYYY-MM-DDTHH:MM[:SS[.fraction]]` then `Z` or `+hh:mm`/`-hh:mm`
 * (seconds/fractions optional, fractions truncated to milliseconds).
 */
const ISO_INSTANT_WITH_ZONE =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?(?:Z|([+-])(\d{2}):(\d{2}))$/;

/**
 * Parse a strict ISO-8601 instant to epoch milliseconds; anything without an
 * explicit zone (or otherwise malformed) is a TypeError. Never reads local
 * time: the calendar is assembled with the UTC setters/getters only.
 */
export function parseInstant(at: string): number {
  if (typeof at !== 'string') {
    throw new TypeError('skyClock: expected an ISO-8601 string');
  }
  const match = ISO_INSTANT_WITH_ZONE.exec(at);
  if (match === null) {
    throw new TypeError(
      `skyClock: expected ISO-8601 with an explicit uppercase zone (Z or +hh:mm), got ${JSON.stringify(at)}`,
    );
  }
  const [, yearText, monthText, dayText, hourText, minuteText, secondText, fraction, sign, offHour, offMinute] =
    match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = secondText === undefined ? 0 : Number(secondText);
  const millisecond = fraction === undefined ? 0 : Number((fraction + '000').slice(0, 3));
  // JS Date has a year 0; the server rejects it ("year 0 is out of range").
  // Parity: year 0001 is the oldest accepted instant.
  if (year < 1) {
    throw new TypeError(`skyClock: year 0000 is out of range in ${JSON.stringify(at)}`);
  }
  if (month < 1 || month > 12 || hour > 23 || minute > 59 || second > 59) {
    throw new TypeError(`skyClock: ISO-8601 field out of range in ${JSON.stringify(at)}`);
  }
  // Assemble the wall time in UTC and let the calendar normalise; any mismatch
  // (2026-02-30 -> 2026-03-02) means the input was not a real date.
  const wall = new Date(0);
  wall.setUTCFullYear(year, month - 1, day);
  wall.setUTCHours(hour, minute, second, millisecond);
  if (
    wall.getUTCFullYear() !== year ||
    wall.getUTCMonth() !== month - 1 ||
    wall.getUTCDate() !== day ||
    wall.getUTCHours() !== hour ||
    wall.getUTCMinutes() !== minute ||
    wall.getUTCSeconds() !== second
  ) {
    throw new TypeError(`skyClock: ISO-8601 date out of range in ${JSON.stringify(at)}`);
  }
  let offsetMinutes = 0;
  if (sign !== undefined) {
    const offsetHour = Number(offHour);
    const offsetMinute = Number(offMinute);
    if (offsetHour > 23 || offsetMinute > 59) {
      throw new TypeError(`skyClock: ISO-8601 zone out of range in ${JSON.stringify(at)}`);
    }
    offsetMinutes = (sign === '-' ? -1 : 1) * (offsetHour * 60 + offsetMinute);
  }
  // local wall time = UTC + offset, so UTC = wall - offset.
  return wall.getTime() - offsetMinutes * 60_000;
}

/**
 * The instant the sky should show: the live now for `null`, otherwise the
 * stored instant. This does not clamp (see `clampScrub`); it is the honest
 * reading of the state.
 */
export function effectiveInstant(at: string | null, nowMs: number): Date {
  return new Date(at === null ? nowMs : parseInstant(at));
}

/**
 * Clamp a scrub position to `nowMs +- SCRUB_LIMIT_MS` (both ends inclusive).
 * Returns milliseconds since the epoch; non-finite input is a TypeError.
 */
export function clampScrub(atMs: number, nowMs: number): number {
  if (!Number.isFinite(atMs) || !Number.isFinite(nowMs)) {
    throw new TypeError('clampScrub: expected finite epoch milliseconds');
  }
  return Math.min(nowMs + SCRUB_LIMIT_MS, Math.max(nowMs - SCRUB_LIMIT_MS, atMs));
}

/**
 * Signed minutes from the real now to the shown instant; 0 when live (`null`).
 * An instant equal to now returns 0 but is still a paused state.
 */
export function offsetMinutes(at: string | null, nowMs: number): number {
  if (at === null) return 0;
  return (parseInstant(at) - nowMs) / 60_000;
}
