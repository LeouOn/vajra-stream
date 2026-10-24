/**
 * Earth & Sky wave 3 — the planetary-hour readout (row W3-J).
 *
 * Next to the dome: which planetary hour it is at the observer's place for the SHOWN instant (ruler, day or night
 * hour, time left). Everything comes from `GET /astrology/planetary-hour` through the validated client; it is
 * labelled "computed" and nothing here is decorative or estimated.
 *
 * - One answer covers a whole hour: it is requested only when there is none for this place that contains the
 *   shown instant (first load, a new place, the live clock reaching the hour's end, or a scrub into another
 *   hour). The countdown is local: `endsAt - shown`, rounded up to the second, never negative.
 * - Live: a 1 Hz clock (paused while the tab is hidden) drives the countdown; no request per second.
 * - Scrubbed or paused: the hour of that instant, static. A request waits until the scrub has been still for
 *   250 ms, so a slider drag is not a request storm; the newest instant wins.
 * - Honest states: loading (never stale values), "no sunrise here" for polar day or night (never an invented
 *   hour), unavailable with the reason (retried every 10 s), and a payload the client refused (not computed) is
 *   unavailable, never an hour.
 * - Unmount cancels the request and clears every timer. Single-flight client: mount exactly one readout.
 */
import React, { useEffect, useRef, useState } from 'react';

import { effectiveInstant } from '../../lib/skyClock';
import {
  cancelPlanetaryHourRequest,
  fetchPlanetaryHour,
  type PlanetaryHour,
} from '../../lib/planetaryHourClient';
import { useSkyStore } from '../../stores/skyStore';
import ProvenanceTag from './ProvenanceTag';

const TICK_MS = 1000;
/** A scrub must be still this long before an hour is requested. */
const DEBOUNCE_MS = 250;
/** After a failure, ask again after this long. */
const RETRY_MS = 10_000;
/** A "no hour here" answer is for that instant only; it is reused within this distance. */
const POLAR_REUSE_MS = 60_000;

interface Held {
  placeKey: string;
  data: PlanetaryHour;
}

interface Failure {
  placeKey: string;
  shownKey: string;
  message: string;
}

interface Props {
  className?: string;
}

function pad(value: number): string {
  return value < 10 ? `0${value}` : String(value);
}

/** "1 h 05 min 07 s", "4 min 03 s", "12 s" from whole seconds. */
function formatLeft(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h} h ${pad(m)} min ${pad(s)} s`;
  if (m > 0) return `${m} min ${pad(s)} s`;
  return `${s} s`;
}

/** UTC with seconds, from the epoch — never a local-time formatter. */
function formatUtc(ms: number): string {
  const iso = new Date(ms).toISOString();
  return `${iso.slice(0, 10)} ${iso.slice(11, 19)} UTC`;
}

export default function PlanetaryHourReadout({ className = '' }: Props): React.ReactElement {
  const lat = useSkyStore((s) => s.lat);
  const lng = useSkyStore((s) => s.lng);
  const at = useSkyStore((s) => s.at);
  const scrubbed = at !== null;

  const [now, setNow] = useState(() => Date.now());
  const [held, setHeld] = useState<Held | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  const requestId = useRef(0);
  const alive = useRef(true);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const placeKey = `${lat},${lng}`;
  const shownMs = effectiveInstant(at, now).getTime();
  const shownKey = scrubbed ? String(shownMs) : 'live';

  // The live clock: one tick a second, paused while the tab is hidden, refreshed at once on return and on goLive.
  useEffect(() => {
    if (scrubbed) return undefined;
    setNow(Date.now());
    const tick = () => {
      if (!document.hidden) setNow(Date.now());
    };
    const timer = window.setInterval(tick, TICK_MS);
    const onVisibility = () => {
      if (!document.hidden) tick();
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [scrubbed]);

  const heldCovers =
    held !== null &&
    held.placeKey === placeKey &&
    (held.data.hour !== null
      ? shownMs >= held.data.hour.startsAtMs && shownMs < held.data.hour.endsAtMs
      : Math.abs(shownMs - held.data.atMs) <= POLAR_REUSE_MS);
  const failedHere = failure !== null && failure.placeKey === placeKey && failure.shownKey === shownKey;
  const needsFetch = !heldCovers && !failedHere;

  // Ask for the hour of the shown instant when none held covers it. Live asks at once; a scrub waits for stillness.
  useEffect(() => {
    if (!needsFetch) return undefined;
    const run = () => {
      const request = (requestId.current += 1);
      const atMs = scrubbed ? Number(shownKey) : Date.now(); // shownKey is the scrubbed instant in ms
      fetchPlanetaryHour(lat, lng, new Date(atMs).toISOString()).then(
        (data) => {
          if (!alive.current || request !== requestId.current) return;
          setHeld({ placeKey, data });
          setFailure(null);
        },
        (error: unknown) => {
          if (!alive.current || request !== requestId.current) return;
          const kind = typeof error === 'object' && error !== null ? (error as { kind?: unknown }).kind : undefined;
          if (kind === 'stale') return; // a newer request owns the readout
          setFailure({
            placeKey,
            shownKey,
            message: error instanceof Error && error.message.length > 0 ? error.message : 'The planetary hour could not be computed.',
          });
          if (retryTimer.current !== null) clearTimeout(retryTimer.current);
          retryTimer.current = setTimeout(() => {
            retryTimer.current = null;
            if (!alive.current) return;
            setFailure(null);
            setRetryToken((token) => token + 1);
          }, RETRY_MS);
        },
      );
    };
    if (!scrubbed) {
      run();
      return undefined;
    }
    const timer = setTimeout(run, DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // lat/lng/placeKey are one fact; shownKey matters only while scrubbed (live reads the clock when it runs)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [placeKey, scrubbed ? shownKey : null, needsFetch, retryToken]);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      if (retryTimer.current !== null) clearTimeout(retryTimer.current);
      retryTimer.current = null;
      cancelPlanetaryHourRequest();
    };
  }, []);

  // While the shown instant moves (time-lapse or a drag), the held answer is
  // kept on screen, dimmed, with an "updating" cue; a first load still shows
  // the loading text and an error still shows the error.
  const heldSamePlace = held !== null && held.placeKey === placeKey;
  let view: 'loading' | 'ready' | 'no-sunrise' | 'unavailable' | 'updating';
  if (heldCovers && held !== null) view = held.data.hour !== null ? 'ready' : 'no-sunrise';
  else if (failedHere) view = 'unavailable';
  else if (heldSamePlace) view = 'updating';
  else view = 'loading';

  const hour = heldSamePlace && held !== null && (heldCovers || view === 'updating') ? held.data.hour : null;

  return (
    <div
      data-testid="planetary-hour-readout"
      data-state={view}
      className={`rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-gray-300 ${className}`.trim()}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-bold tracking-wide text-gray-200">Planetary hour</span>
        {(view === 'ready' || view === 'no-sunrise' || view === 'updating') && <ProvenanceTag kind="computed" />}
      </div>

      {view === 'loading' && (
        <p className="mt-1 text-gray-400" data-testid="planetary-hour-loading">
          Finding the planetary hour…
        </p>
      )}

      {view === 'unavailable' && failure !== null && (
        <p className="mt-1 text-amber-300" data-testid="planetary-hour-unavailable">
          Planetary hour unavailable: {failure.message}
        </p>
      )}

      {(view === 'no-sunrise' || (view === 'updating' && held !== null && held.data.hour === null)) && held !== null && (
        <div className={`mt-1 ${view === 'updating' ? 'opacity-60' : ''}`} data-testid="planetary-hour-none">
          <p className="m-0 font-medium text-gray-200">No planetary hour here</p>
          <p className="m-0 text-gray-400">{held.data.reason}</p>
          {view === 'updating' && (
            <p className="m-0 text-[10px] text-amber-300" data-testid="planetary-hour-updating">
              updating…
            </p>
          )}
        </div>
      )}

      {(view === 'ready' || (view === 'updating' && hour !== null)) && hour !== null && held !== null && (
        <div className={`mt-1 space-y-0.5 ${view === 'updating' ? 'opacity-60' : ''}`}>
          <div aria-live="polite" className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-base font-semibold text-white" data-testid="planetary-hour-ruler">
              {hour.ruler}
            </span>
            <span data-testid="planetary-hour-kind">
              {hour.isDaytime ? 'Day' : 'Night'} hour {hour.index} of 12
            </span>
          </div>
          <div>
            {view === 'updating' ? (
              <span className="text-[10px] text-amber-300" data-testid="planetary-hour-updating">
                updating…
              </span>
            ) : (
              <>
                <span className="font-mono text-gray-100" data-testid="planetary-hour-left" aria-live="off">
                  {formatLeft(Math.ceil((hour.endsAtMs - shownMs) / 1000))}
                </span>{' '}
                left
              </>
            )}
          </div>
          <div className="text-gray-400" data-testid="planetary-hour-day-ruler">
            Day ruled by {held.data.solarDay?.dayRuler}
          </div>
        </div>
      )}

      <div className="mt-1 text-[10px] text-gray-400" data-testid="planetary-hour-instant">
        {scrubbed ? 'Scrubbed instant' : 'Live'}: {formatUtc(shownMs)} · {lat.toFixed(2)}, {lng.toFixed(2)}
      </div>
    </div>
  );
}
