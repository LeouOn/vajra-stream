/**
 * W6-A — keep the address bar in step with the Earth & Sky store.
 *
 * On mount (once): read the address bar and RESTORE from it — valid `lat` +
 * `lng` together set the observer; the TIME decision is explicit (W6-A2 F1):
 * a link carrying `at` pins the instant when it is inside the ±24 h window
 * and otherwise selects LIVE (outside window: goLive + the window note;
 * unparseable or duplicated `at`: goLive + the invalid note); a link with
 * sky keys but no `at` is a LIVE link (emitted live links omit `at`), so it
 * selects Live whatever the store held; a visit with NO sky keys leaves the
 * store untouched (a paused sky survives an ordinary remount). The note
 * clears when the user picks a time again. The restore itself never
 * rewrites the URL: the link the user arrived with stays intact.
 *
 * After the restore, the URL FOLLOWS the store (the card is the source of
 * truth once it is open): observer moves rewrite `lat`/`lng`, scrub sets
 * `at`, going live removes it — always through `new URL(location.href)` so
 * the PATH, every other param AND THE HASH survive (W6-A2 F2). Writes are
 * debounced ~500 ms and use
 * `window.history.replaceState(window.history.state, '', url)` — replace,
 * not push (no history spam), and the router's state object survives.
 *
 * No popstate listener: browser back/forward is not fought over; the next
 * store change or a fresh mount re-syncs. No re-render loops: the sync runs
 * imperatively from the store subscription, React state holds only the note.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { useSkyStore } from '../stores/skyStore';
import { parseInstant, SCRUB_LIMIT_MS } from '../lib/skyClock';
import { parseSkyParams } from '../lib/skyUrl';

const SYNC_DEBOUNCE_MS = 500;

export const OUT_OF_WINDOW_NOTE = 'That link points outside the +-24 h window: showing Live.';
export const INVALID_AT_NOTE = 'That link has an invalid instant: showing Live.';

export interface SkyUrlSyncResult {
  /** The single outside-window note, or null (dismiss or none). */
  note: string | null;
  /** Dismiss the note. */
  dismissNote: () => void;
  /** Write the URL from the store NOW (cancels the pending debounce). */
  syncNow: () => void;
}

/** The URL for the current store state: only the sky search params mutate —
 * pathname, every other param AND THE HASH are carried over untouched (F2). */
function skyUrlForState(lat: number, lng: number, at: string | null): string {
  const url = new URL(window.location.href);
  url.searchParams.set('lat', (lat === 0 ? 0 : lat).toFixed(4));
  url.searchParams.set('lng', (lng === 0 ? 0 : lng).toFixed(4));
  if (at === null) {
    url.searchParams.delete('at');
  } else {
    url.searchParams.set('at', at);
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

function replaceIfChanged(url: string): void {
  const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (url !== current) {
    window.history.replaceState(window.history.state, '', url);
  }
}

export function useSkyUrlSync(): SkyUrlSyncResult {
  const [note, setNote] = useState<string | null>(null);
  const restoringRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Immediate write from the store; cancels any pending debounce. */
  const syncNow = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (typeof window === 'undefined') return;
    const { lat, lng, at } = useSkyStore.getState();
    replaceIfChanged(skyUrlForState(lat, lng, at));
  }, []);

  useEffect(() => {
    // Mount: restore once. StrictMode-safe (a second run re-reads the same
    // URL and re-applies the same values, still without writing).
    //
    // The TIME decision is explicit (W6-A2 F1): a link that carries `at`
    // either pins the instant (in window) or selects Live (outside window,
    // with the note; unparseable/duplicated `at` likewise Live + note). A
    // link with sky keys but NO `at` is a live link — Live it is, whatever
    // the store held (an emitted live link omits `at`). A visit with NO sky
    // keys at all leaves the store alone: it is not a link, and a paused sky
    // must survive an ordinary remount.
    restoringRef.current = true;
    const { lat, lng, at, problems, keys } = parseSkyParams(window.location.search);
    const store = useSkyStore.getState();
    if (lat !== undefined && lng !== undefined) {
      store.setObserver(lat, lng);
    }
    if (keys.at) {
      if (at === undefined) {
        store.goLive();
        setNote(INVALID_AT_NOTE);
      } else {
        const nowMs = Date.now();
        if (Math.abs(parseInstant(at) - nowMs) <= SCRUB_LIMIT_MS) {
          store.setAt(at);
        } else {
          store.goLive();
          setNote(OUT_OF_WINDOW_NOTE);
        }
      }
    } else if (keys.lat || keys.lng) {
      store.goLive();
    }
    if (problems.length > 0) {
      // Dropped params are surfaced here (and in the note when they were the
      // instant); one debug line aids link debugging.
      console.debug('skyUrl: dropped link params:', problems.join(' | '));
    }
    restoringRef.current = false;

    const unsubscribe = useSkyStore.subscribe((state) => {
      // The note promises "showing Live"; the moment the user picks a time
      // again, that promise is stale — drop it.
      if (state.at !== null) {
        setNote(null);
      }
      if (restoringRef.current) return;
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        replaceIfChanged(skyUrlForState(state.lat, state.lng, state.at));
      }, SYNC_DEBOUNCE_MS);
    });
    return () => {
      unsubscribe();
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  const dismissNote = useCallback(() => setNote(null), []);

  return { note, dismissNote, syncNow };
}
