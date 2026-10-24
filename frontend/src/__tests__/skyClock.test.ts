/**
 * W3-A tests for frontend/src/lib/skyClock.ts (pure; no React, no timers).
 *
 * The live instant is always passed in by the caller (nowMs): the module never
 * reads the clock, so every case here is deterministic.
 */
import { describe, expect, it } from 'vitest';
import {
  SCRUB_LIMIT_MS,
  clampScrub,
  effectiveInstant,
  offsetMinutes,
  parseInstant,
} from '../lib/skyClock';

const NOW = Date.parse('2026-10-24T09:00:00Z');
const HOUR = 3600_000;


describe('parseInstant (strict: explicit zone required)', () => {
  // Epoch literals from Date.UTC (UTC arithmetic only, no local getters):
  // 2026-10-24T10:00:00Z and 2026-10-24T12:00:00+02:00 are the same instant.
  const T10Z = Date.UTC(2026, 9, 24, 10, 0, 0, 0);

  it('accepts Z / z and +hh:mm / -hh:mm forms', () => {
    const accepted: Array<[string, number]> = [
      ['2026-10-24T10:00:00Z', T10Z],
      ['2026-10-24T10:00Z', T10Z], // seconds optional
      ['2026-10-24T10:00:00.000Z', T10Z],
      ['2026-10-24T12:00:00+02:00', T10Z],
      ['2026-10-24T05:00:00-05:00', T10Z],
      ['2026-10-24T10:00:00+00:00', T10Z],
      ['2026-10-24T10:00:00-00:00', T10Z],
    ];
    for (const [input, expected] of accepted) {
      expect(parseInstant(input), input).toBe(expected);
    }
  });

  it('requires uppercase T and Z (server parity: the backend 422s a lowercase z)', () => {
    // The client used to accept RFC 3339 lowercase designators; Python's
    // datetime.fromisoformat does not, so the two ends would disagree.
    expect(() => parseInstant('2026-10-24t10:00:00Z')).toThrow(TypeError);
    expect(() => parseInstant('2026-10-24T10:00:00z')).toThrow(TypeError);
    expect(() => parseInstant('2026-10-24t10:00:00z')).toThrow(TypeError);
  });

  it('rejects year 0000 (JS has a year 0; the server answers 422 year 0 is out of range)', () => {
    expect(() => parseInstant('0000-01-01T00:00:00Z')).toThrow(TypeError);
    expect(() => parseInstant('0000-12-31T23:59:59Z')).toThrow(TypeError);
    expect(() => parseInstant('0000-01-01T00:00:00+00:00')).toThrow(TypeError);
  });

  it('accepts year 0001 (the server accepts it; the boundary is year 0 only)', () => {
    const year1 = (() => {
      const d = new Date(0);
      d.setUTCFullYear(1, 0, 1);
      d.setUTCHours(0, 0, 0, 0);
      return d.getTime();
    })();
    expect(parseInstant('0001-01-01T00:00:00Z')).toBe(year1);
  });

  it('rejects five-digit and negative years (the parser must not accept one)', () => {
    expect(() => parseInstant('10000-01-01T00:00:00Z')).toThrow(TypeError);
    expect(() => parseInstant('-0001-01-01T00:00:00Z')).toThrow(TypeError);
  });

  it('pins the deliberate strictness: forms the server accepts but this clock rejects', () => {
    // Python datetime.fromisoformat accepts all of these; the client clock only
    // ever receives instants it produced (toISOString) or read from the
    // server, so these shapes mean a caller has pasted or fabricated input.
    const deliberatelyRejected = [
      '2026-10-24 10:00:00Z', // space separator
      '2026-10-24', // date only
      '20261024T100000Z', // basic format
      '2026-W43-4T10:00:00Z', // ISO week date
      ' 2026-10-24T10:00:00Z', // leading whitespace
      '2026-10-24T10:00:00Z ', // trailing whitespace
      '2026-10-24T10:00:00Z\n', // trailing newline
    ];
    for (const input of deliberatelyRejected) {
      expect(() => parseInstant(input), JSON.stringify(input)).toThrow(TypeError);
    }
  });

  it('keeps milliseconds and truncates finer fractions', () => {
    expect(parseInstant('2026-10-24T10:00:00.5Z')).toBe(T10Z + 500);
    expect(parseInstant('2026-10-24T10:00:00.25Z')).toBe(T10Z + 250);
    expect(parseInstant('2026-10-24T10:00:00.123456Z')).toBe(T10Z + 123);
  });

  it('rejects a naive date-time (Date.parse would read it as LOCAL time)', () => {
    // The exact hazard: this string is 10:00Z / 17:00Z / 01:00Z under
    // TZ=UTC / America/Los_Angeles / Asia/Tokyo.
    expect(() => parseInstant('2026-10-24T10:00:00')).toThrow(TypeError);
    expect(() => parseInstant('2026-10-24T10:00')).toThrow(TypeError);
    expect(() => parseInstant('2026-10-24')).toThrow(TypeError); // date only
    expect(() => parseInstant('2026-10-24 10:00:00Z')).toThrow(TypeError); // space
  });

  it('rejects loose strings that Date.parse tolerates', () => {
    for (const bad of ['Oct 24 2026', 'Fri Oct 24 2026 10:00:00 GMT+0000', '24/10/2026', '2026/10/24 10:00', 'now', '']) {
      expect(() => parseInstant(bad), bad).toThrow(TypeError);
    }
  });

  it('rejects invalid calendar fields and malformed zones', () => {
    const bad = [
      '2026-13-01T00:00:00Z',
      '2026-00-01T00:00:00Z',
      '2026-02-30T00:00:00Z',
      '2026-04-31T00:00:00Z',
      '2026-10-24T24:00:00Z',
      '2026-10-24T10:60:00Z',
      '2026-10-24T10:00:60Z',
      '2026-10-24T10:00:00+24:00',
      '2026-10-24T10:00:00+02:60',
      '2026-10-24T10:00:00+02',
      '2026-10-24T10:00:00+2:00',
      '2026-10-24T10:00:00.Z',
      '2026-10-24T10:00:00Z ',
      ' 2026-10-24T10:00:00Z',
    ];
    for (const badString of bad) {
      expect(() => parseInstant(badString), badString).toThrow(TypeError);
    }
  });

  it('never reads local time: local getters and setters are never called', () => {
    // Structural proof instead of a subprocess per TZ. Date.parse(naive) and
    // any construction via local components would hit these prototypes.
    const keys = [
      'getFullYear',
      'getMonth',
      'getDate',
      'getDay',
      'getHours',
      'getMinutes',
      'getSeconds',
      'getMilliseconds',
      'getTimezoneOffset',
      'setFullYear',
      'setMonth',
      'setDate',
      'setHours',
      'setMinutes',
      'setSeconds',
      'setMilliseconds',
    ] as const;
    type Locals = Record<(typeof keys)[number], () => number>;
    const proto = Date.prototype as unknown as Locals;
    const saved = new Map<string, () => number>();
    for (const key of keys) {
      saved.set(key, proto[key]);
      proto[key] = () => {
        throw new Error(`local time read via ${key}`);
      };
    }
    try {
      expect(parseInstant('2026-10-24T12:00:00+02:00')).toBe(T10Z);
      expect(parseInstant('2026-10-24T10:00:00Z')).toBe(T10Z);
      expect(effectiveInstant('2026-10-24T12:00:00+02:00', 0).getTime()).toBe(T10Z);
      expect(offsetMinutes('2026-10-24T12:00:00+02:00', T10Z)).toBe(0);
    } finally {
      for (const key of keys) proto[key] = saved.get(key)!;
    }
  });
});

describe('SCRUB_LIMIT_MS', () => {
  it('is 24 hours', () => {
    expect(SCRUB_LIMIT_MS).toBe(24 * HOUR);
  });
});

describe('effectiveInstant', () => {
  it('null means live: exactly the caller-supplied now', () => {
    const live = effectiveInstant(null, NOW);
    expect(live).toBeInstanceOf(Date);
    expect(live.getTime()).toBe(NOW);
    expect(live.toISOString()).toBe('2026-10-24T09:00:00.000Z');
  });

  it('a parsed instant is returned as given, independent of now', () => {
    const at = '2026-10-23T08:30:00Z';
    const a = effectiveInstant(at, NOW);
    const b = effectiveInstant(at, NOW + 5 * HOUR);
    expect(a.getTime()).toBe(Date.parse(at));
    expect(b.getTime()).toBe(Date.parse(at));
  });

  it('does not clamp: a caller outside +-24 h still gets that instant', () => {
    const at = '2026-10-01T00:00:00Z';
    expect(effectiveInstant(at, NOW).getTime()).toBe(Date.parse(at));
  });

  it('rejects a malformed instant with TypeError', () => {
    for (const bad of ['not-a-date', '', '2026-13-45T99:99:99Z', 'banana']) {
      expect(() => effectiveInstant(bad, NOW), bad).toThrow(TypeError);
    }
  });
});

describe('clampScrub', () => {
  it('leaves an instant inside the window untouched', () => {
    expect(clampScrub(NOW, NOW)).toBe(NOW);
    expect(clampScrub(NOW + 90 * 60_000, NOW)).toBe(NOW + 90 * 60_000);
    expect(clampScrub(NOW - 90 * 60_000, NOW)).toBe(NOW - 90 * 60_000);
  });

  it('clamps exactly at +-24 h', () => {
    expect(clampScrub(NOW + 24 * HOUR, NOW)).toBe(NOW + 24 * HOUR);
    expect(clampScrub(NOW - 24 * HOUR, NOW)).toBe(NOW - 24 * HOUR);
    expect(clampScrub(NOW + 24 * HOUR + 1, NOW)).toBe(NOW + 24 * HOUR);
    expect(clampScrub(NOW - 24 * HOUR - 1, NOW)).toBe(NOW - 24 * HOUR);
  });

  it('clamps far values at both ends', () => {
    expect(clampScrub(NOW + 365 * 24 * HOUR, NOW)).toBe(NOW + 24 * HOUR);
    expect(clampScrub(NOW - 365 * 24 * HOUR, NOW)).toBe(NOW - 24 * HOUR);
    expect(clampScrub(0, NOW)).toBe(NOW - 24 * HOUR);
  });

  it('returns a finite number for every finite input', () => {
    for (const at of [NOW, NOW + 1, NOW - 1, NOW + 1e9, NOW - 1e9]) {
      expect(Number.isFinite(clampScrub(at, NOW))).toBe(true);
    }
  });

  it('rejects non-finite inputs with TypeError', () => {
    for (const bad of [Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]) {
      expect(() => clampScrub(bad, NOW), `at=${bad}`).toThrow(TypeError);
      expect(() => clampScrub(NOW, bad), `now=${bad}`).toThrow(TypeError);
    }
  });
});

describe('offsetMinutes', () => {
  it('is 0 when live (null)', () => {
    expect(offsetMinutes(null, NOW)).toBe(0);
    expect(offsetMinutes(null, 0)).toBe(0);
  });

  it('is the signed offset of the instant from now, in minutes', () => {
    expect(offsetMinutes(new Date(NOW + 90 * 60_000).toISOString(), NOW)).toBe(90);
    expect(offsetMinutes(new Date(NOW - 2 * HOUR).toISOString(), NOW)).toBe(-120);
    expect(offsetMinutes(new Date(NOW + 90_000).toISOString(), NOW)).toBe(1.5);
    expect(offsetMinutes(new Date(NOW + 24 * HOUR).toISOString(), NOW)).toBe(1440);
  });

  it('is 0 for an instant equal to now that is not null (paused-at-now is distinguishable)', () => {
    const paused = new Date(NOW).toISOString();
    expect(paused).not.toBeNull();
    expect(offsetMinutes(paused, NOW)).toBe(0);
    expect(offsetMinutes(null, NOW)).toBe(0);
  });

  it('rejects a malformed instant with TypeError', () => {
    expect(() => offsetMinutes('nope', NOW)).toThrow(TypeError);
  });
});
