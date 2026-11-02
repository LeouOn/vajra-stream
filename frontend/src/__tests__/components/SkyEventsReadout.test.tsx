// @vitest-environment happy-dom
/**
 * W7-3b — Sun & Moon readout behaviours. The client is mocked; the pure
 * formatting helpers and the store are real.
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';

import { validateSkyEvents, type SkyEvent, type SkyEvents } from '../../lib/skyEventsClient';
import { useSkyStore } from '../../stores/skyStore';

const FETCH = vi.hoisted(() => ({ mock: vi.fn() }));
vi.mock('../../lib/skyEventsClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/skyEventsClient')>();
  return { ...actual, fetchSkyEvents: FETCH.mock, cancelSkyEventsRequest: vi.fn() };
});

import SkyEventsReadout, {
  darkTarget,
  localTimeFor,
  nextEventOfKind,
  relativeText,
} from '../../components/UI/SkyEventsReadout';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root | null = null;

function event(body: 'sun' | 'moon', kind: SkyEvent['kind'], at: string): SkyEvent {
  return { body, kind, at, atMs: Date.parse(at) };
}

function fixture(overrides: Partial<SkyEvents> = {}): SkyEvents {
  const events = [
    event('sun', 'astronomical_dawn', '2026-06-21T07:00:00Z'),
    event('sun', 'rise', '2026-06-21T12:00:00Z'),
    event('sun', 'transit', '2026-06-21T19:30:00Z'),
    event('sun', 'set', '2026-06-22T03:00:00Z'),
    event('sun', 'civil_dusk', '2026-06-22T04:00:00Z'),
    event('sun', 'nautical_dusk', '2026-06-22T04:30:00Z'),
    event('sun', 'astronomical_dusk', '2026-06-22T05:00:00Z'),
    event('sun', 'astronomical_dawn', '2026-06-22T07:00:00Z'),
    event('sun', 'rise', '2026-06-22T12:00:00Z'),
    event('sun', 'transit', '2026-06-22T19:30:00Z'),
    event('sun', 'set', '2026-06-23T03:00:00Z'),
    event('moon', 'rise', '2026-06-21T18:30:00Z'),
    event('moon', 'transit', '2026-06-22T00:00:00Z'),
    event('moon', 'set', '2026-06-22T05:00:00Z'),
    event('moon', 'rise', '2026-06-22T19:00:00Z'),
    event('moon', 'set', '2026-06-23T06:00:00Z'),
  ].sort((a, b) => a.atMs - b.atMs);
  return {
    status: 'success',
    window: {
      from: '2026-06-20T18:00:00Z',
      to: '2026-06-23T18:00:00Z',
      fromMs: Date.parse('2026-06-20T18:00:00Z'),
      toMs: Date.parse('2026-06-23T18:00:00Z'),
    },
    observer: { latitude: 37.7749, longitude: -122.4194 },
    timezone: 'America/Los_Angeles',
    convention: 'Rise and set: upper edge of the disc. Transit: meridian passage (upper culmination).',
    events,
    always: { sun: null, moon: null },
    ...overrides,
  };
}

function mount(): void {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root!.render(<SkyEventsReadout />);
  });
}

async function flush(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function byTestId(id: string): HTMLElement | null {
  return container.querySelector<HTMLElement>(`[data-testid="${id}"]`);
}

function text(): string {
  return container.textContent ?? '';
}

const AT = '2026-06-21T18:00:00Z';

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(AT));
  useSkyStore.setState({ lat: 37.7749, lng: -122.4194, at: AT, label: undefined });
  FETCH.mock.mockReset();
  FETCH.mock.mockResolvedValue(fixture());
});

afterEach(() => {
  if (root !== null) {
    act(() => {
      root!.unmount();
    });
    root = null;
  }
  if (container !== undefined) container.remove();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('local time', () => {
  it('formats the zone with and without DST', () => {
    const summer = localTimeFor(Date.parse('2026-06-21T18:00:00Z'), 'America/Los_Angeles', -122.4194, 'en-US');
    expect(summer).toEqual({ label: 'Sunday 21 Jun', clock: '11:00', zone: 'PDT', approximate: false });
    const winter = localTimeFor(Date.parse('2026-12-21T18:00:00Z'), 'America/Los_Angeles', -122.4194, 'en-US');
    expect(winter).toEqual({ label: 'Monday 21 Dec', clock: '10:00', zone: 'PST', approximate: false });
  });

  it('falls back to labelled solar time when the zone is missing or unusable', () => {
    const fallback = localTimeFor(Date.parse('2026-06-21T18:00:00Z'), null, -122.4194, 'en-US');
    expect(fallback.approximate).toBe(true);
    expect(fallback.label).toBe('Local solar time (approximate)');
    expect(fallback.clock).toBe('09:50'); // 18:00 UTC - 8 h 09 m 41 s
    expect(fallback.zone).toBeNull();
    const unusable = localTimeFor(Date.parse('2026-06-21T18:00:00Z'), 'Not/AZone', -122.4194, 'en-US');
    expect(unusable.approximate).toBe(true);
  });
});



const TROMSO = {"status":"success","window":{"from":"2026-06-20T12:00:00Z","to":"2026-06-23T12:00:00Z"},"observer":{"latitude":69.65,"longitude":18.96},"convention":"Rise and set: upper edge of the disc at the apparent horizon, standard refraction (34 arcmin). Twilight: centre of the Sun at -6, -12 and -18 degrees, no refraction. Transit: highest point.","events":[{"body":"moon","kind":"transit","at":"2026-06-20T15:48:45Z"},{"body":"moon","kind":"set","at":"2026-06-20T22:37:42Z"},{"body":"moon","kind":"rise","at":"2026-06-21T10:17:14Z"},{"body":"sun","kind":"transit","at":"2026-06-21T10:45:58Z"},{"body":"moon","kind":"transit","at":"2026-06-21T16:32:30Z"},{"body":"moon","kind":"set","at":"2026-06-21T22:14:09Z"},{"body":"sun","kind":"transit","at":"2026-06-22T10:46:11Z"},{"body":"moon","kind":"rise","at":"2026-06-22T12:12:40Z"},{"body":"moon","kind":"transit","at":"2026-06-22T17:14:58Z"},{"body":"moon","kind":"set","at":"2026-06-22T21:49:45Z"},{"body":"sun","kind":"transit","at":"2026-06-23T10:46:24Z"}],"always":{"sun":"up","moon":null},"timezone":"Europe/Oslo","provenance":{"window":"computed","convention":"computed","events":"computed","always":"computed","timezone":"computed"}};

const AUCKLAND = { latitude: -36.8485, longitude: 174.7633 };

describe('W7-3d fixes', () => {
  it('names the day in the observer zone, not the runtime zone', async () => {
    const previous = process.env.TZ;
    process.env.TZ = 'America/Los_Angeles';
    try {
      expect(new Intl.DateTimeFormat().resolvedOptions().timeZone).toBe('America/Los_Angeles');
      useSkyStore.setState({ ...AUCKLAND_LATLNG(), at: '2026-06-23T13:00:00Z' });
      const from = Date.parse('2026-06-22T13:00:00Z');
      const to = Date.parse('2026-06-25T13:00:00Z');
      FETCH.mock.mockResolvedValue(
        fixture({
          timezone: 'Pacific/Auckland',
          window: { from: new Date(from).toISOString(), to: new Date(to).toISOString(), fromMs: from, toMs: to },
          events: [
            event('sun', 'rise', '2026-06-23T19:00:00Z'),
            event('sun', 'transit', '2026-06-24T01:00:00Z'),
            event('sun', 'set', '2026-06-25T13:00:00Z'),
          ],
        }),
      );
      mount();
      await flush();
      const sun = byTestId('sky-events-sun-row')?.textContent ?? '';
      expect(sun).toContain('on Fri');
      expect(sun).not.toContain('on Thu');
    } finally {
      if (previous === undefined) delete process.env.TZ;
      else process.env.TZ = previous;
    }
  });

  it('decides today/tomorrow at the observer midnight, not the runtime one', async () => {
    useSkyStore.setState({ ...AUCKLAND_LATLNG(), at: '2026-06-24T11:30:00Z' });
    const from = Date.parse('2026-06-23T11:30:00Z');
    const to = Date.parse('2026-06-26T11:30:00Z');
    FETCH.mock.mockResolvedValue(
      fixture({
        timezone: 'Pacific/Auckland',
        window: { from: new Date(from).toISOString(), to: new Date(to).toISOString(), fromMs: from, toMs: to },
        events: [event('sun', 'set', '2026-06-24T12:30:00Z')],
      }),
    );
    mount();
    await flush();
    const sun = byTestId('sky-events-sun-row')?.textContent ?? '';
    expect(sun).toContain('sets 00:30 tomorrow');
    expect(sun).not.toContain('(in 1 h)');
  });

  it('keeps the transits of a polar-day body with always', async () => {
    useSkyStore.setState({ lat: 69.65, lng: 18.96, at: '2026-06-21T09:00:00Z' });
    FETCH.mock.mockResolvedValue(validateSkyEvents(TROMSO));
    mount();
    await flush();
    const sun = byTestId('sky-events-sun-row')?.textContent ?? '';
    expect(sun).toContain('up all window');
    expect(sun).toContain('transits 12:45');
    const moon = byTestId('sky-events-moon-row')?.textContent ?? '';
    expect(moon).toContain('sets');
  });

  it('says approximate once on the solar fallback', async () => {
    FETCH.mock.mockRejectedValue(new Error('offline'));
    mount();
    await flush();
    const local = byTestId('sky-events-local')?.textContent ?? '';
    expect(local).toContain('Local solar time (approximate) · 09:50');
    expect((local.match(/approximate/g) ?? []).length).toBe(1);
  });
});

function AUCKLAND_LATLNG() {
  return { lat: AUCKLAND.latitude, lng: AUCKLAND.longitude };
}

describe('the readout', () => {
  it('shows the local time (UTC only in the title) and the NEXT events, never a previous->next pair', async () => {
    mount();
    await flush();
    const local = byTestId('sky-events-local');
    expect(local?.textContent).toContain('Sunday 21 Jun');
    expect(local?.textContent).toContain('11:00');
    expect(local?.textContent).toContain('PDT');
    expect(local?.getAttribute('title')).toBe('2026-06-21T18:00:00.000Z');
    expect(text()).not.toContain('2026-06-21T18:00:00Z');

    const sun = byTestId('sky-events-sun-row')?.textContent ?? '';
    expect(sun).toContain('sets 20:00 (in 9 h)');
    expect(sun).toContain('transits 12:30 (in 1 h 30 m)');
    expect(sun).toContain('rises 05:00 tomorrow');
    expect(sun).not.toContain('→');
    expect(sun).not.toContain('05:00 (in');
    const moon = byTestId('sky-events-moon-row')?.textContent ?? '';
    expect(moon).toContain('rises 11:30 (in 30 m)');
    expect(moon).toContain('sets 22:00 (in 11 h)');
    expect(moon).toContain('transits 17:00 (in 6 h)');
  });

  it('uses always for a body with no rise/set in the window', async () => {
    FETCH.mock.mockResolvedValue(fixture({ events: [], always: { sun: 'up', moon: 'down' } }));
    mount();
    await flush();
    expect(byTestId('sky-events-sun-always')?.textContent).toBe('up all window');
    expect(byTestId('sky-events-moon-always')?.textContent).toBe('below the horizon all window');
    expect(byTestId('sky-events-empty')).toBeNull();
  });

  it('shows loading, error and empty as their own polite states; a failure keeps the solar local time', async () => {
    FETCH.mock.mockReturnValue(new Promise(() => undefined));
    mount();
    expect(byTestId('sky-events-loading')?.getAttribute('role')).toBe('status');
    expect(byTestId('sky-events-local')?.textContent).toContain('Local solar time (approximate)');
    act(() => root!.unmount());
    root = null;
    container.remove();

    FETCH.mock.mockRejectedValue(new Error('offline'));
    mount();
    await flush();
    expect(byTestId('sky-events-unavailable')?.getAttribute('role')).toBe('status');
    expect(byTestId('sky-events-unavailable')?.textContent).toContain('offline');
    expect(byTestId('sky-events-local')?.textContent).toContain('Local solar time (approximate)');

    FETCH.mock.mockResolvedValue(fixture({ events: [], always: { sun: null, moon: null } }));
    mount();
    await flush();
    expect(byTestId('sky-events-empty')?.getAttribute('role')).toBe('status');
  });

  it('says which twilight way Dark means and jumps on click', async () => {
    mount();
    await flush();
    const dark = byTestId('sky-events-chip-dark') as HTMLButtonElement;
    expect(dark.getAttribute('title')).toBe('Next astronomical dusk');
    await act(async () => {
      dark.click();
    });
    expect(useSkyStore.getState().at).toBe('2026-06-22T05:00:00.000Z');
  });

  it('uses the next astronomical dawn when it is already dark', () => {
    const target = darkTarget(fixture().events, Date.parse('2026-06-22T06:00:00Z'));
    expect(target.kind).toBe('astronomical_dawn');
    expect(target.event?.at).toBe('2026-06-22T07:00:00Z');
  });

  it('enables a chip from the REAL now, not the shown instant (the m1 Moonrise bug)', async () => {
    vi.setSystemTime(new Date('2026-06-21T18:00:00Z'));
    useSkyStore.setState({ at: '2026-06-21T10:00:00Z' });
    mount();
    await flush();
    const moonrise = byTestId('sky-events-chip-moonrise') as HTMLButtonElement;
    // The next Moonrise after 10:00Z is 18:30Z, 30 minutes after the real now.
    expect(moonrise.disabled).toBe(false);
    expect(moonrise.getAttribute('title')).toBe('2026-06-21T18:30:00Z');
  });

  it('disables at the +-24 h edge from the real now, with a visible reason', async () => {
    useSkyStore.setState({ at: '2026-06-21T10:00:00Z' });
    vi.setSystemTime(new Date('2026-06-20T18:30:00Z')); // exactly 24 h before the 18:30Z Moonrise
    mount();
    await flush();
    expect((byTestId('sky-events-chip-moonrise') as HTMLButtonElement).disabled).toBe(false);

    act(() => root!.unmount());
    root = null;
    container.remove();
    vi.setSystemTime(new Date('2026-06-20T18:29:59Z'));
    mount();
    await flush();
    const disabledMoonrise = byTestId('sky-events-chip-moonrise') as HTMLButtonElement;
    expect(disabledMoonrise.disabled).toBe(true);
    expect(disabledMoonrise.getAttribute('aria-describedby')).toBe('sky-events-chip-reasons');
    const reasons = byTestId('sky-events-chip-reasons') as HTMLElement;
    expect(reasons.textContent).toContain('Moonrise: over 24 h away');
    const moonRow = byTestId('sky-events-moon-row') as HTMLElement;
    const details = byTestId('sky-events-details') as HTMLElement;
    const follows = (a: Node, b: Node): boolean =>
      (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) === Node.DOCUMENT_POSITION_FOLLOWING;
    expect(follows(moonRow, reasons)).toBe(true);
    expect(follows(reasons, details)).toBe(true);
  });

  it('lists each body next events soonest first', async () => {
    useSkyStore.setState({ at: '2026-06-21T19:00:00Z' });
    mount();
    await flush();
    const row = byTestId('sky-events-moon-row') as HTMLElement;
    const order = Array.from(row.querySelectorAll('[data-testid^="sky-events-moon-"]')).map((el) =>
      el.getAttribute('data-testid'),
    );
    expect(order).toEqual(['sky-events-moon-transit', 'sky-events-moon-set', 'sky-events-moon-rise']);
  });

  it('exposes a details/summary with the convention, the disc note and the next twilight per level', async () => {
    mount();
    await flush();
    const details = byTestId('sky-events-details') as HTMLDetailsElement;
    expect(details.hasAttribute('open')).toBe(false);
    expect(details.querySelector('summary')?.textContent).toBe('How these times are defined');
    expect(byTestId('sky-events-convention')?.textContent).toContain('meridian passage');
    expect(byTestId('sky-events-twilight-civil')?.textContent).toContain('dusk 21:00');
    expect(byTestId('sky-events-twilight-nautical')?.textContent).toContain('dusk 21:30');
    expect(byTestId('sky-events-twilight-astronomical')?.textContent).toContain('dusk 22:00');
    expect(text()).toContain('Rise and set include refraction');
  });

  it('helpers: next at/after, relative text, no previous event', () => {
    const events = fixture().events;
    expect(nextEventOfKind(events, 'moon', 'rise', Date.parse('2026-06-21T18:30:00Z'))?.at).toBe('2026-06-21T18:30:00Z');
    expect(nextEventOfKind(events, 'moon', 'rise', Date.parse('2026-06-22T18:30:00Z'))?.at).toBe('2026-06-22T19:00:00Z');
    expect(relativeText(event('sun', 'set', '2026-06-21T20:00:00Z'), Date.parse('2026-06-21T18:00:00Z'))).toBe('in 2 h');
    expect(relativeText(event('sun', 'set', '2026-06-21T18:22:00Z'), Date.parse('2026-06-21T18:00:00Z'))).toBe('in 22 m');
  });
});
