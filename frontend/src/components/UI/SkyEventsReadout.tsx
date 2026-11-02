/**
 * W7-3b — the Sun & Moon readout.
 *
 * Sits in the card's left column between the planetary-hour readout and the
 * time controls. It answers, for the instant the card shows: what local time
 * it is at the observer, the NEXT rise/set/transit of the Sun and the Moon
 * (never a previous->next pair), and the jump targets Sunset / Moonrise /
 * Dark. Everything comes from `GET /astrology/sky-events` through the
 * validated client; nothing is estimated. The one approximation (no IANA
 * zone) is labelled as solar time.
 *
 * One answer covers the contract's 72 h window; it is re-used while the shown
 * instant stays inside that window minus a 3 h margin, so a fast Play tick
 * does not fetch. A jump chip is enabled only when its event is inside the
 * +-24 h the scrub range allows, measured from the REAL now.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { parseInstant, SCRUB_LIMIT_MS } from '../../lib/skyClock';
import {
  cancelSkyEventsRequest,
  fetchSkyEvents,
  skyEventsFetchKey,
  skyEventsWindowCovers,
  type SkyEvent,
  type SkyEventBody,
  type SkyEventKind,
  type SkyEvents,
} from '../../lib/skyEventsClient';
import { useSkyStore } from '../../stores/skyStore';
import ProvenanceTag from './ProvenanceTag';

const TICK_MS = 60_000;
const BODY_KINDS = ['rise', 'set', 'transit'] as const;
type BodyKind = (typeof BODY_KINDS)[number];
const BODY_LABELS: Record<SkyEventBody, string> = { sun: 'Sun', moon: 'Moon' };
const VERB: Record<BodyKind, string> = { rise: 'rises', set: 'sets', transit: 'transits' };
const TWILIGHTS = ['civil', 'nautical', 'astronomical'] as const;
type TwilightLevel = (typeof TWILIGHTS)[number];

function pad2(value: number): string {
  return value < 10 ? `0${value}` : String(value);
}

function utcClock(ms: number): string {
  const d = new Date(ms);
  return `${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}`;
}

export interface LocalTimeParts {
  /** "Sun 2 Nov" (weekday, day, month) or the solar-time label. */
  label: string;
  /** "09:35" at the observer. */
  clock: string;
  /** "PST" or null when the clock is the solar-time approximation. */
  zone: string | null;
  approximate: boolean;
}

/**
 * The local time at the observer. With an IANA zone: the zone's own clock
 * (weekday, day, month, 24 h, zone abbreviation). Without one (or when the
 * runtime cannot use it): the solar time UTC + longitude/15 h, labelled
 * approximate and never presented as a clock reading.
 */
export function localTimeFor(
  ms: number,
  timezone: string | null,
  longitude: number,
  locale?: string,
): LocalTimeParts {
  if (timezone !== null) {
    try {
      const date = new Intl.DateTimeFormat(locale, {
        timeZone: timezone,
        weekday: 'long',
        day: 'numeric',
        month: 'short',
      }).formatToParts(ms);
      const time = new Intl.DateTimeFormat(locale, {
        timeZone: timezone,
        hour: '2-digit',
        minute: '2-digit',
        hourCycle: 'h23',
        timeZoneName: 'short',
      }).formatToParts(ms);
      const pick = (parts: Intl.DateTimeFormatPart[], type: string): string =>
        parts.find((part) => part.type === type)?.value ?? '';
      const label = `${pick(date, 'weekday')} ${pick(date, 'day')} ${pick(date, 'month')}`.trim();
      const clock = `${pick(time, 'hour')}:${pick(time, 'minute')}`;
      const zone = pick(time, 'timeZoneName');
      if (label !== '' && clock !== ':' && zone !== '') {
        return { label, clock, zone, approximate: false };
      }
    } catch {
      /* an unusable zone falls through to the solar time */
    }
  }
  const solarMs = ms + (longitude / 15) * 3_600_000;
  return { label: 'Local solar time (approximate)', clock: utcClock(solarMs), zone: null, approximate: true };
}

/** The local clock of an event, in the zone when there is one, else the solar clock. */
export function formatEventTime(event: SkyEvent, timezone: string | null, longitude: number): string {
  if (timezone !== null) {
    try {
      const parts = new Intl.DateTimeFormat(undefined, {
        timeZone: timezone,
        hour: '2-digit',
        minute: '2-digit',
        hourCycle: 'h23',
      }).formatToParts(event.atMs);
      const hour = parts.find((part) => part.type === 'hour')?.value ?? '';
      const minute = parts.find((part) => part.type === 'minute')?.value ?? '';
      if (hour !== '' && minute !== '') return `${hour}:${minute}`;
    } catch {
      /* fall through to the solar clock */
    }
  }
  return utcClock(event.atMs + (longitude / 15) * 3_600_000);
}

/** The local calendar day of an instant (YYYY-MM-DD), zone or solar. */
function localDay(ms: number, timezone: string | null, longitude: number): string {
  if (timezone !== null) {
    try {
      return new Intl.DateTimeFormat('en-CA', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(ms);
    } catch {
      /* fall through */
    }
  }
  const d = new Date(ms + (longitude / 15) * 3_600_000);
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}`;
}

function dayDifference(day: string, other: string): number {
  return Math.round((Date.parse(`${day}T00:00:00Z`) - Date.parse(`${other}T00:00:00Z`)) / 86_400_000);
}

/** The weekday in the OBSERVER's zone (or the solar-time offset), never the runtime zone. */
function weekdayLabel(ms: number, timezone: string | null, longitude: number): string {
  const shifted = timezone === null ? ms + (longitude / 15) * 3_600_000 : ms;
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeZone: timezone ?? 'UTC',
      weekday: 'short',
    }).format(shifted);
  } catch {
    return '';
  }
}

/** "in 6 h 22 m" / "in 22 m" from the shown instant to the event. */
export function relativeText(event: SkyEvent, shownMs: number): string {
  const minutes = Math.max(0, Math.round((event.atMs - shownMs) / 60_000));
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `in ${rest} m`;
  return rest === 0 ? `in ${hours} h` : `in ${hours} h ${rest} m`;
}

/** The next event of one body/kind at or after the shown instant. */
export function nextEventOfKind(
  events: SkyEvent[],
  body: SkyEventBody,
  kind: SkyEventKind,
  shownMs: number,
): SkyEvent | null {
  for (const event of events) {
    if (event.body === body && event.kind === kind && event.atMs >= shownMs) return event;
  }
  return null;
}

/** The next dawn/dusk at a twilight level, whichever comes first. */
export function nextTwilightForLevel(
  events: SkyEvent[],
  level: TwilightLevel,
  shownMs: number,
): SkyEvent | null {
  const dawn = `${level}_dawn` as SkyEventKind;
  const dusk = `${level}_dusk` as SkyEventKind;
  let best: SkyEvent | null = null;
  for (const event of events) {
    if (event.body !== 'sun' || (event.kind !== dawn && event.kind !== dusk) || event.atMs < shownMs) continue;
    if (best === null || event.atMs < best.atMs) best = event;
  }
  return best;
}

/**
 * The Dark chip target: the next astronomical dusk, or — when the most recent
 * astronomical transition is a dusk (it is already dark) — the next
 * astronomical dawn. The kind is in the button's title.
 */
export function darkTarget(
  events: SkyEvent[],
  shownMs: number,
): { event: SkyEvent | null; kind: 'astronomical_dawn' | 'astronomical_dusk' } {
  const dawns = events.filter((event) => event.body === 'sun' && event.kind === 'astronomical_dawn');
  const dusks = events.filter((event) => event.body === 'sun' && event.kind === 'astronomical_dusk');
  const last = [...dawns, ...dusks]
    .filter((event) => event.atMs <= shownMs)
    .sort((a, b) => b.atMs - a.atMs)[0];
  const wantDawn = last?.kind === 'astronomical_dusk';
  const kind = wantDawn ? 'astronomical_dawn' : 'astronomical_dusk';
  return { event: nextEventOfKind(events, 'sun', kind, shownMs), kind };
}

/** One event as "rises 06:36 (in 6 h 22 m)" or "sets 17:09 tomorrow". */
function eventText(
  event: SkyEvent,
  verb: string,
  timezone: string | null,
  longitude: number,
  shownMs: number,
): string {
  const clock = formatEventTime(event, timezone, longitude);
  const diff = dayDifference(localDay(event.atMs, timezone, longitude), localDay(shownMs, timezone, longitude));
  if (diff === 0) return `${verb} ${clock} (${relativeText(event, shownMs)})`;
  if (diff === 1) return `${verb} ${clock} tomorrow`;
  return `${verb} ${clock} on ${weekdayLabel(event.atMs, timezone, longitude)}`;
}

function alwaysText(value: 'up' | 'down' | null): string {
  if (value === 'up') return 'up all window';
  if (value === 'down') return 'below the horizon all window';
  return 'no rise or set in this window';
}

interface Props {
  className?: string;
}

export default function SkyEventsReadout({ className = '' }: Props): React.ReactElement {
  const lat = useSkyStore((state) => state.lat);
  const lng = useSkyStore((state) => state.lng);
  const at = useSkyStore((state) => state.at);

  const [nowMs, setNowMs] = useState(() => Date.now());
  const [data, setData] = useState<SkyEvents | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const heldRef = useRef<{ key: string; data: SkyEvents } | null>(null);
  const currentKeyRef = useRef('');
  const inFlightRef = useRef<{ key: string } | null>(null);
  const aliveRef = useRef(true);

  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
      // A StrictMode remount (or an unmount) aborts the request; let the next
      // mount start its own instead of being blocked by the old token.
      inFlightRef.current = null;
      cancelSkyEventsRequest();
    };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!document.hidden) setNowMs(Date.now());
    }, TICK_MS);
    const onVisibility = () => {
      if (!document.hidden) setNowMs(Date.now());
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  const shownMs = at === null ? nowMs : parseInstant(at);
  const key = skyEventsFetchKey(lat, lng, shownMs);
  currentKeyRef.current = key;

  const load = useCallback(async () => {
    // Suppress only an identical duplicate (the same fetch key); a different
    // key must abort the in-flight request and fetch the new place/window.
    if (inFlightRef.current !== null && inFlightRef.current.key === key) return;
    const token = { key };
    inFlightRef.current = token;
    setLoading(true);
    try {
      const answer = await fetchSkyEvents(lat, lng, new Date(shownMs).toISOString());
      // The client aborts superseded requests; this guard also ignores a late
      // answer for an older bucket if the caller had already moved on.
      if (!aliveRef.current || currentKeyRef.current !== key) return;
      heldRef.current = { key, data: answer };
      setData(answer);
      setFailure(null);
    } catch (error) {
      if (!aliveRef.current || currentKeyRef.current !== key) return;
      if (error instanceof Error && (error as { kind?: string }).kind === 'stale') return;
      setFailure(error instanceof Error && error.message.length > 0 ? error.message : 'The request failed.');
    } finally {
      if (inFlightRef.current === token) inFlightRef.current = null;
      if (aliveRef.current && currentKeyRef.current === key) setLoading(false);
    }
  }, [key, lat, lng, shownMs]);

  useEffect(() => {
    const held = heldRef.current;
    if (held !== null) {
      const samePlace = held.key.split('@')[0] === key.split('@')[0];
      if (samePlace && skyEventsWindowCovers(held.data.window.fromMs, held.data.window.toMs, shownMs)) {
        return;
      }
    }
    void load();
  }, [key, load, shownMs]);

  const events = data?.events ?? [];
  const timezone = data?.timezone ?? null;
  const local = useMemo(() => localTimeFor(shownMs, timezone, lng), [shownMs, timezone, lng]);
  const utcTitle = new Date(shownMs).toISOString();

  const nowForChips = Date.now();
  const chip = (label: string, event: SkyEvent | null, missing: string, title?: string) => {
    if (event === null) return { label, event, enabled: false, reason: missing, title };
    const within = Math.abs(event.atMs - nowForChips) <= SCRUB_LIMIT_MS;
    return { label, event, enabled: within, reason: within ? '' : 'over 24 h away', title };
  };
  const dark = darkTarget(events, shownMs);
  const chips = {
    sunset: chip('Sunset', nextEventOfKind(events, 'sun', 'set', shownMs), 'none in this window'),
    moonrise: chip('Moonrise', nextEventOfKind(events, 'moon', 'rise', shownMs), 'none in this window'),
    dark: chip(
      'Dark',
      dark.event,
      'no dusk or dawn in this window',
      dark.kind === 'astronomical_dawn' ? 'Next astronomical dawn' : 'Next astronomical dusk',
    ),
  };
  const disabledChips = (['sunset', 'moonrise', 'dark'] as const).filter((name) => chips[name].reason !== '');

  const jump = (event: SkyEvent | null) => {
    if (event === null) return;
    useSkyStore.getState().setAt(new Date(event.atMs).toISOString());
  };

  const view = failure !== null ? 'unavailable' : data === null ? 'loading' : events.length === 0 && data.always.sun === null && data.always.moon === null ? 'empty' : 'ready';

  const bodyRow = (body: SkyEventBody): React.ReactElement => {
    const always = data?.always[body] ?? null;
    const nexts = BODY_KINDS.map((kind) => ({ kind, event: nextEventOfKind(events, body, kind, shownMs) }))
      .filter((row) => row.event !== null)
      .sort((a, b) => (a.event as SkyEvent).atMs - (b.event as SkyEvent).atMs);
    const none = nexts.length === 0;
    const showAlways = always !== null;
    return (
      <div key={body} data-testid={`sky-events-${body}-row`} className="min-w-0 text-[11px] leading-tight">
        <span className="font-medium text-gray-200">{BODY_LABELS[body]}</span>{' '}
        {showAlways || none ? (
          <span className="text-gray-400" data-testid={`sky-events-${body}-always`}>
            {alwaysText(always)}
          </span>
        ) : null}
        {nexts.map((row, index) => (
          <span key={row.kind} className="text-gray-300" data-testid={`sky-events-${body}-${row.kind}`} title={row.event?.at}>
            {showAlways || index > 0 ? ' · ' : ''}
            {eventText(row.event as SkyEvent, VERB[row.kind as BodyKind], timezone, lng, shownMs)}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div
      data-testid="sky-events-readout"
      data-state={view}
      className={`rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-gray-300 ${className}`.trim()}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1" data-testid="sky-events-header">
        <div className="flex items-center gap-1.5">
          <span className="font-bold tracking-wide text-gray-200">Sun &amp; Moon</span>
          {view === 'ready' && <ProvenanceTag kind="computed" />}
        </div>
        <div className="flex flex-wrap items-center gap-1.5" data-testid="sky-events-chips">
          {(['sunset', 'moonrise', 'dark'] as const).map((name) => {
            const item = chips[name];
            return (
              <button
                key={name}
                type="button"
                data-testid={`sky-events-chip-${name}`}
                disabled={!item.enabled}
                onClick={() => jump(item.event)}
                title={item.title ?? item.event?.at}
                aria-describedby={!item.enabled && disabledChips.length > 0 ? 'sky-events-chip-reasons' : undefined}
                className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      {view === 'loading' && (
        <p role="status" className="mt-1 text-gray-400" data-testid="sky-events-loading">
          Finding the Sun and Moon events…
        </p>
      )}
      {view === 'unavailable' && (
        <p role="status" className="mt-1 text-amber-300" data-testid="sky-events-unavailable">
          Sun and Moon events unavailable: {failure}
        </p>
      )}
      {view === 'empty' && (
        <p role="status" className="mt-1 text-gray-400" data-testid="sky-events-empty">
          No Sun or Moon events in this window.
        </p>
      )}

      <p className="text-[11px] text-gray-400" data-testid="sky-events-local" title={utcTitle}>
        {local.label} · <span className="font-mono text-gray-200">{local.clock}</span>
        {local.zone !== null ? ` ${local.zone}` : ''}
      </p>

      {view === 'ready' && (
        <>
          {bodyRow('sun')}
          {bodyRow('moon')}
          {disabledChips.length > 0 && (
            <p
              id="sky-events-chip-reasons"
              data-testid="sky-events-chip-reasons"
              className="mt-0.5 text-[10px] leading-tight text-gray-500"
            >
              {disabledChips.map((name) => `${chips[name].label}: ${chips[name].reason}`).join(' · ')}
            </p>
          )}
          <details className="mt-0.5" data-testid="sky-events-details">
            <summary className="cursor-pointer text-[10px] text-gray-400">How these times are defined</summary>
            <div className="mt-1 space-y-0.5 text-[10px] leading-snug text-gray-500">
            <p data-testid="sky-events-convention">{data?.convention}</p>
            <p>Rise and set include refraction and the disc&apos;s edge, so they differ from the geometric altitudes in the cards.</p>
            <p data-testid="sky-events-twilight">
              {TWILIGHTS.map((level) => {
                const event = nextTwilightForLevel(events, level, shownMs);
                const kind = event?.kind.replace(`${level}_`, '') ?? '';
                return (
                  <span key={level} className="mr-2 inline-block" data-testid={`sky-events-twilight-${level}`}>
                    {level} {event === null ? '—' : `${kind} ${formatEventTime(event, timezone, lng)}`}
                  </span>
                );
              })}
            </p>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
