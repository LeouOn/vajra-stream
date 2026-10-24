/**
 * Earth & Sky wave 3 — the time controls.
 *
 * Live / Pause / scrub within +-24 h of the real now, plus "Next sunrise
 * here". Every control writes the one shared `skyStore` instant, so the dome,
 * the globes and the strip move together. The shown instant and the sunrise
 * come from the ephemeris: both are labelled "computed"; nothing here is
 * decorative.
 *
 * The store is clock-free, so this component owns "now": a 1 Hz tick (paused
 * while the tab is hidden) keeps the readout and the offset honest. A scrub is
 * clamped by `clampScrub`; a sunrise beyond now + 24 h is refused rather than
 * clamped, because a clamped answer would not land on the sunrise.
 *
 * Time-lapse (W5-C): Play advances the shown instant through the same store at
 * 60x/600x/3600x, with elapsed-time maths and a cadence cap (15 updates/s, or
 * 4/s under prefers-reduced-motion, where the two slowest speeds are the only
 * choices). It stops at the +24 h window edge, on any manual action, and when
 * the tab is hidden (silently; resuming is manual)."
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card, InputNumber, Slider, Space, Tag, Typography } from 'antd';
import { FastForward, Pause, Play, Square, Sunrise } from 'lucide-react';

import { useSkyStore } from '../../stores/skyStore';
import {
  SCRUB_LIMIT_MS,
  clampScrub,
  effectiveInstant,
  offsetMinutes,
  parseInstant,
} from '../../lib/skyClock';
import { cancelSunEventsRequest, fetchSunEvents } from '../../lib/sunEventsClient';
import ProvenanceTag from './ProvenanceTag';

const { Text } = Typography;
const TICK_MS = 1000;
const SPEEDS = [60, 600, 3600] as const;
const REDUCED_SPEEDS = [60, 600] as const;
/** How often the play loop looks at the clock; the cadence gate does the pacing. */
const PLAY_TICK_MS = 16;
/** At most 15 store updates per second (4/s under reduced motion). */
const PLAY_UPDATE_MS = 1000 / 15;
const PLAY_REDUCED_UPDATE_MS = 250;

/** Read the reduced-motion preference, live (a change event is honoured). */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false,
  );
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return undefined;
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setReduced(query.matches);
    query.addEventListener?.('change', onChange);
    return () => query.removeEventListener?.('change', onChange);
  }, []);
  return reduced;
}

interface Props {
  className?: string;
}

/** UTC with seconds, from the epoch — never a local-time formatter. */
function formatUtc(ms: number): string {
  const iso = new Date(ms).toISOString();
  return `${iso.slice(0, 10)} ${iso.slice(11, 19)} UTC`;
}

/** "+3 h 20 min" / "-45 min" / "0 min" (signed, whole minutes). */
function formatOffset(minutes: number): string {
  const rounded = Math.round(minutes);
  if (rounded === 0) return '0 min';
  const sign = rounded < 0 ? '-' : '+';
  const abs = Math.abs(rounded);
  const hours = Math.floor(abs / 60);
  const mins = abs % 60;
  if (hours === 0) return `${sign}${mins} min`;
  if (mins === 0) return `${sign}${hours} h`;
  return `${sign}${hours} h ${mins} min`;
}

function kindOf(error: unknown): string | undefined {
  if (typeof error === 'object' && error !== null && 'kind' in error) {
    const kind = (error as { kind?: unknown }).kind;
    return typeof kind === 'string' ? kind : undefined;
  }
  return undefined;
}

function messageOf(error: unknown): string {
  if (error instanceof Error && error.message.length > 0) return error.message;
  return 'Could not compute the next sunrise.';
}

/** Decimal only after normalisation: optional sign, digits, at most one '.'; no exponents. */
const DECIMAL_RE = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/;
/** A single comma and no '.' is a comma decimal point (coordinates never use thousands separators). */
const COMMA_DECIMAL_RE = /^[+-]?\d+,\d*$/;

/**
 * One parser for both fields and every submit path. NFKC first (a CJK IME's
 * full-width digits and '．' become ASCII); a single comma with no '.' is the
 * decimal point ('36,1' -> 36.1, '36,1,2' is rejected). Latitude is
 * range-checked; longitude accepts any finite decimal and the store wraps it
 * into [-180,180), after which the fields show the wrapped committed value
 * (never a silent clamp).
 */
function parseCoordinate(
  raw: string,
  which: 'lat' | 'lng',
): { ok: true; value: number } | { ok: false; error: string } {
  let text = raw.normalize('NFKC').trim();
  if (COMMA_DECIMAL_RE.test(text)) text = text.replace(',', '.');
  const example = which === 'lat' ? '36.1' : '139.4';
  if (!DECIMAL_RE.test(text)) {
    return { ok: false, error: `${which === 'lat' ? 'Latitude' : 'Longitude'} must be a number like ${example}` };
  }
  const value = Number(text);
  if (!Number.isFinite(value)) {
    return { ok: false, error: `${which === 'lat' ? 'Latitude' : 'Longitude'} must be a finite number` };
  }
  if (which === 'lat' && (value < -90 || value > 90)) {
    return { ok: false, error: 'Latitude must be between -90 and 90 degrees.' };
  }
  return { ok: true, value };
}

/**
 * Display form without exponent notation (String(1e-7) is '1e-7', which the
 * parser rightly rejects) and at most 6 decimals. The CLEAN field's commit uses
 * the store's full number, so this rounding never moves an untouched observer;
 * a dirty field commits exactly what was typed.
 */
function fmtCoordinate(value: number): string {
  const text = value.toFixed(6).replace(/\.?0+$/, '');
  return text === '-0' || text === '' ? '0' : text;
}

export default function SkyTimeControls({ className = '' }: Props): React.ReactElement {
  const at = useSkyStore((s) => s.at);
  const lat = useSkyStore((s) => s.lat);
  const lng = useSkyStore((s) => s.lng);
  const label = useSkyStore((s) => s.label);
  const setAt = useSkyStore((s) => s.setAt);
  const goLive = useSkyStore((s) => s.goLive);

  const [now, setNow] = useState(() => Date.now());
  const [loading, setLoading] = useState(false);
  const [sunriseNote, setSunriseNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(600);
  const [playNote, setPlayNote] = useState<string | null>(null);
  const [latRaw, setLatRaw] = useState(() => fmtCoordinate(lat));
  const [lngRaw, setLngRaw] = useState(() => fmtCoordinate(lng));
  const [latDirty, setLatDirty] = useState(false);
  const [lngDirty, setLngDirty] = useState(false);
  const [placeError, setPlaceError] = useState<string | null>(null);
  const [placeErrorField, setPlaceErrorField] = useState<'lat' | 'lng' | null>(null);
  const [resetEpoch, setResetEpoch] = useState(0);
  const reducedMotion = usePrefersReducedMotion();
  const requestId = useRef(0);

  // Unmount (navigate away): invalidate this component's in-flight request and
  // cancel the shared client request, so an answer that arrives later can never
  // write the global skyStore instant (W3-G2).
  useEffect(() => {
    return () => {
      requestId.current += 1;
      cancelSunEventsRequest();
    };
  }, []);

  // One clock for the readout and the offset; no work while the tab is hidden.
  useEffect(() => {
    const tick = () => {
      if (!document.hidden) setNow(Date.now());
    };
    const timer = window.setInterval(tick, TICK_MS);
    const onVisibility = () => {
      if (document.hidden) {
        // Hidden tab: stop the time-lapse silently; resuming is manual.
        setPlaying(false);
        return;
      }
      tick();
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  // A sunrise belongs to the place it was fetched for: when the observer
  // moves, any in-flight answer is stale and the note no longer applies.
  useEffect(() => {
    requestId.current += 1;
    setLoading(false);
    setSunriseNote(null);
    setError(null);
    setPlaying(false);
    setPlayNote(null);
  }, [lat, lng]);

  // Reduced motion: only the two slowest speeds, and a 4 Hz cadence.
  useEffect(() => {
    if (reducedMotion && speed > 600) setSpeed(600);
  }, [reducedMotion, speed]);

  // The time-lapse loop: elapsed-time maths (no drift), a cadence gate, and a
  // hard stop at the +24 h edge. It never wraps. It does not depend on `at`
  // (the store is read at tick time), so store updates do not restart it.
  useEffect(() => {
    if (!playing) return undefined;
    let last = Date.now();
    const minUpdate = reducedMotion ? PLAY_REDUCED_UPDATE_MS : PLAY_UPDATE_MS;
    const timer = window.setInterval(() => {
      if (document.hidden) {
        setPlaying(false);
        return;
      }
      const nowMs = Date.now();
      const elapsed = nowMs - last;
      if (elapsed < minUpdate) return;
      last = nowMs;
      const shown = effectiveInstant(useSkyStore.getState().at, nowMs).getTime();
      const limit = nowMs + SCRUB_LIMIT_MS;
      const target = shown + speed * elapsed;
      if (target >= limit) {
        setAt(new Date(limit).toISOString());
        setPlaying(false);
        setPlayNote('Reached the end of the +-24 h window');
        return;
      }
      setAt(new Date(target).toISOString());
    }, PLAY_TICK_MS);
    return () => window.clearInterval(timer);
  }, [playing, speed, reducedMotion, setAt]);

  const isLive = at === null;
  const shownMs = effectiveInstant(at, now).getTime();
  const offset = isLive ? 0 : offsetMinutes(at, now);
  const sliderValue = Math.max(-1440, Math.min(1440, Math.round(offset)));
  const observerText = label
    ? `${label} · ${lat.toFixed(4)}, ${lng.toFixed(4)}`
    : `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

  // One commit model for both coordinates: raw text is the draft (the
  // InputNumber's numeric onChange cannot carry '-' or '36,1'), and Enter,
  // blur and Set place all run commitPlace with the same parse/validation.
  // Dirty is PER FIELD: the clean field keeps following the store (a map pick
  // updates it) while the other keeps the draft; commit reads a clean field's
  // value from the store, never from its rounded display.
  useEffect(() => {
    if (!latDirty) setLatRaw(fmtCoordinate(lat));
    if (!lngDirty) setLngRaw(fmtCoordinate(lng));
  }, [lat, lng, latDirty, lngDirty]);

  const dirty = latDirty || lngDirty;

  const onDraft = useCallback((which: 'lat' | 'lng', text: string) => {
    if (which === 'lat') {
      setLatRaw(text);
      setLatDirty(true);
    } else {
      setLngRaw(text);
      setLngDirty(true);
    }
    setPlaceError(null);
    setPlaceErrorField(null);
  }, []);

  // Spinner/step only (antd's onStep): never the lossy onChange that the blur
  // and Enter flush emits for stripped text. Latitude is clamped here.
  const onStep = useCallback((which: 'lat' | 'lng', value: string) => {
    const number = Number(value);
    if (!Number.isFinite(number)) return;
    if (which === 'lat') {
      setLatRaw(fmtCoordinate(Math.max(-90, Math.min(90, number))));
      setLatDirty(true);
    } else {
      setLngRaw(fmtCoordinate(number));
      setLngDirty(true);
    }
    setPlaceError(null);
    setPlaceErrorField(null);
  }, []);

  const commitPlace = useCallback(() => {
    const parsedLat = latDirty ? parseCoordinate(latRaw, 'lat') : ({ ok: true, value: lat } as const);
    if (!parsedLat.ok) {
      setPlaceError(parsedLat.error);
      setPlaceErrorField('lat');
      return;
    }
    const parsedLng = lngDirty ? parseCoordinate(lngRaw, 'lng') : ({ ok: true, value: lng } as const);
    if (!parsedLng.ok) {
      setPlaceError(parsedLng.error);
      setPlaceErrorField('lng');
      return;
    }
    if (!latDirty && !lngDirty) {
      // Untouched: apply must be a no-op, not a re-round of the observer.
      setPlaceError(null);
      setPlaceErrorField(null);
      return;
    }
    try {
      useSkyStore.getState().setObserver(parsedLat.value, parsedLng.value);
    } catch (caught) {
      setPlaceError(
        caught instanceof RangeError
          ? 'Latitude must be between -90 and 90 degrees.'
          : 'Could not set the observer.',
      );
      setPlaceErrorField('lat');
      return;
    }
    const after = useSkyStore.getState();
    setLatRaw(fmtCoordinate(after.lat));
    setLngRaw(fmtCoordinate(after.lng));
    setLatDirty(false);
    setLngDirty(false);
    setPlaceError(null);
    setPlaceErrorField(null);
  }, [lat, latDirty, latRaw, lng, lngDirty, lngRaw]);

  const cancelDraft = useCallback(() => {
    setLatRaw(fmtCoordinate(lat));
    setLngRaw(fmtCoordinate(lng));
    setLatDirty(false);
    setLngDirty(false);
    setPlaceError(null);
    setPlaceErrorField(null);
    // Remount the controlled number inputs so a typed value the control is
    // still holding internally cannot outlive the cancelled draft.
    setResetEpoch((epoch) => epoch + 1);
  }, [lat, lng]);

  // The number control can stop the Escape keydown, so listen in the capture
  // phase while a draft exists. Blur commits before Escape can reach a
  // keyboard user, so this only cancels an UNBLURRED draft (documented).
  useEffect(() => {
    if (!dirty) return undefined;
    const onEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      const target = event.target as HTMLElement | null;
      if (!target || target.closest('[data-testid="sky-place-controls"]') === null) return;
      event.preventDefault();
      cancelDraft();
    };
    document.addEventListener('keydown', onEscape, true);
    return () => document.removeEventListener('keydown', onEscape, true);
  }, [cancelDraft, dirty]);

  const onLive = useCallback(() => {
    setPlaying(false);
    setPlayNote(null);
    requestId.current += 1;
    setLoading(false);
    setSunriseNote(null);
    setError(null);
    setNow(Date.now());
    goLive();
  }, [goLive]);

  const onPause = useCallback(() => {
    const nowMs = Date.now();
    setPlaying(false);
    setPlayNote(null);
    requestId.current += 1;
    setLoading(false);
    setSunriseNote(null);
    setError(null);
    setNow(nowMs);
    setAt(new Date(nowMs).toISOString());
  }, [setAt]);

  const onScrub = useCallback(
    (minutes: number | number[]) => {
      const value = Array.isArray(minutes) ? minutes[0] : minutes;
      const nowMs = Date.now();
      const target = clampScrub(nowMs + value * 60_000, nowMs);
      setNow(nowMs);
      setSunriseNote(null);
      setError(null);
      setPlaying(false);
      setPlayNote(null);
      requestId.current += 1;
      setLoading(false);
      setAt(new Date(target).toISOString());
    },
    [setAt],
  );

  const onNextSunrise = useCallback(async () => {
    setPlaying(false);
    setPlayNote(null);
    const request = (requestId.current += 1);
    setLoading(true);
    setError(null);
    setSunriseNote(null);
    try {
      // Ask from the shown instant PLUS 1 s. The engine floors the query to
      // the second, and the route prints the event itself, so asking from a
      // sunrise instant answers with that same sunrise forever. +1 s always
      // crosses the engine's one-second boundary (W3-R2 F1).
      const events = await fetchSunEvents(lat, lng, new Date(shownMs + 1000).toISOString());
      if (request !== requestId.current) return;
      if (events.next_sunrise === null) {
        setSunriseNote('No sunrise here within the next day (polar night or midnight sun).');
        return;
      }
      const sunriseMs = parseInstant(events.next_sunrise);
      if (sunriseMs > Date.now() + SCRUB_LIMIT_MS) {
        setSunriseNote('The next sunrise is more than 24 h away (outside the scrub range).');
        return;
      }
      setAt(new Date(sunriseMs).toISOString());
      setSunriseNote(`Sunrise set: ${formatUtc(sunriseMs)}`);
    } catch (err) {
      if (request !== requestId.current || kindOf(err) === 'stale') return;
      setError(messageOf(err));
    } finally {
      if (request === requestId.current) setLoading(false);
    }
  }, [lat, lng, shownMs, setAt]);

  const onPlay = useCallback(() => {
    if (playing) {
      setPlaying(false);
      return;
    }
    const nowMs = Date.now();
    const currentAt = useSkyStore.getState().at;
    const shownNow = effectiveInstant(currentAt, nowMs).getTime();
    if (shownNow >= nowMs + SCRUB_LIMIT_MS - 1000) {
      setPlaying(false);
      setPlayNote('Reached the end of the +-24 h window');
      return;
    }
    if (currentAt === null) {
      // Live: pause at now and start the time-lapse from there.
      setAt(new Date(nowMs).toISOString());
    }
    setNow(nowMs);
    setSunriseNote(null);
    setError(null);
    setPlayNote(null);
    requestId.current += 1;
    setLoading(false);
    setPlaying(true);
  }, [playing, setAt]);

  const speeds = reducedMotion ? REDUCED_SPEEDS : SPEEDS;
  const offsetText = isLive ? 'Following the real clock' : `${formatOffset(offset)} from now`;
  const shownAt = useMemo(() => formatUtc(shownMs), [shownMs]);

  return (
    <Card size="small" className={`bg-black/20 ${className}`.trim()} data-testid="sky-time-controls">
      <Space orientation="vertical" size={8} style={{ width: '100%' }}>
        <div className="flex items-center justify-between gap-2">
          <Space size={6} align="center">
            <Text strong>Sky time</Text>
            <ProvenanceTag kind="computed" />
          </Space>
          <Space size={4}>
            <Button
              size="small"
              type={isLive ? 'primary' : 'default'}
              icon={<Play size={12} aria-hidden="true" />}
              aria-label="Live sky time"
              aria-pressed={isLive}
              onClick={onLive}
            >
              Live
            </Button>
            <Button
              size="small"
              icon={<Pause size={12} aria-hidden="true" />}
              aria-label="Pause sky time at the current instant"
              aria-pressed={!isLive}
              onClick={onPause}
            >
              Pause
            </Button>
          </Space>
        </div>

        <div data-testid="sky-time-readout" aria-live="polite">
          <div>
            <Tag color={playing ? 'blue' : isLive ? 'green' : 'gold'} style={{ marginInlineEnd: 6 }}>
              {playing ? 'Playing' : isLive ? 'Live' : 'Paused'}
            </Tag>
            <Text>{shownAt}</Text>
          </div>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {offsetText}
          </Text>
          {(playing || playNote !== null) && (
            <div>
              <Text type="secondary" style={{ fontSize: 11 }} data-testid="sky-play-status">
                {playing ? `Playing at ${speed}x` : playNote}
              </Text>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2" data-testid="sky-play-controls">
          <Button
            size="small"
            type={playing ? 'primary' : 'default'}
            icon={playing ? <Square size={12} aria-hidden="true" /> : <FastForward size={12} aria-hidden="true" />}
            aria-label={playing ? 'Stop the time-lapse' : 'Play the time-lapse'}
            aria-pressed={playing}
            onClick={onPlay}
          >
            {playing ? 'Stop' : 'Play'}
          </Button>
          <label className="flex items-center gap-1 text-[11px] text-gray-400">
            <span>Speed</span>
            <select
              aria-label="Time-lapse speed"
              className="rounded border border-white/10 bg-slate-900 px-1 py-0.5 text-[11px] text-gray-100"
              value={speed}
              onChange={(event) => setSpeed(Number(event.target.value))}
            >
              {speeds.map((value) => (
                <option key={value} value={value}>
                  {value}x
                </option>
              ))}
            </select>
          </label>
        </div>

        <Slider
          min={-1440}
          max={1440}
          step={1}
          value={sliderValue}
          onChange={onScrub}
          ariaLabelForHandle="Time offset from now in minutes"
          tooltip={{ formatter: (value) => `${value ?? 0} min` }}
        />
        <div className="flex items-center justify-between gap-2">
          <Text type="secondary" style={{ fontSize: 11 }}>
            -24 h
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }} data-testid="sky-time-observer">
            {observerText}
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            +24 h
          </Text>
        </div>

        <div className="flex flex-wrap items-end gap-2" data-testid="sky-place-controls">
          <label className="flex flex-col gap-0.5 text-[10px] text-gray-400">
            <span>Latitude</span>
            <InputNumber
              key={`lat-${resetEpoch}`}
              size="small"
              stringMode
              aria-label="Latitude, degrees north"
              step={0.1}
              value={latRaw}
              onInput={(text: string) => onDraft('lat', text)}
              onStep={(value: string) => onStep('lat', value)}
              parser={(text: string | undefined) => (text ?? '').trim()}
              formatter={(value: string | undefined, info: { userTyping: boolean; input: string }) =>
                info.userTyping ? info.input : String(value ?? '')
              }
              onPressEnter={commitPlace}
              onBlur={() => {
                if (dirty) commitPlace();
              }}
              aria-invalid={placeErrorField === 'lat' || undefined}
              aria-describedby={placeErrorField === 'lat' ? 'sky-place-error-text' : undefined}
              style={{ width: 96 }}
            />
          </label>
          <label className="flex flex-col gap-0.5 text-[10px] text-gray-400">
            <span>Longitude</span>
            <InputNumber
              key={`lng-${resetEpoch}`}
              size="small"
              stringMode
              aria-label="Longitude, degrees east"
              step={0.1}
              value={lngRaw}
              onInput={(text: string) => onDraft('lng', text)}
              onStep={(value: string) => onStep('lng', value)}
              parser={(text: string | undefined) => (text ?? '').trim()}
              formatter={(value: string | undefined, info: { userTyping: boolean; input: string }) =>
                info.userTyping ? info.input : String(value ?? '')
              }
              onPressEnter={commitPlace}
              onBlur={() => {
                if (dirty) commitPlace();
              }}
              aria-invalid={placeErrorField === 'lng' || undefined}
              aria-describedby={placeErrorField === 'lng' ? 'sky-place-error-text' : undefined}
              style={{ width: 104 }}
            />
          </label>
          <Button
            size="small"
            type={dirty ? 'primary' : 'default'}
            data-testid="sky-place-set"
            data-pending={dirty ? 'true' : 'false'}
            onClick={commitPlace}
            aria-label="Set place from latitude and longitude"
          >
            Set place
          </Button>
          {dirty && (
            <Button
              size="small"
              type="link"
              data-testid="sky-place-cancel"
              aria-label="Use the current place and discard the draft"
              onMouseDown={(event) => {
                // Keep the field focused so the cancel is not preceded by a
                // blur-commit of the very draft it is discarding.
                event.preventDefault();
              }}
              onClick={cancelDraft}
            >
              Use current place
            </Button>
          )}
        </div>
        {placeError !== null && (
          <Text type="danger" role="alert" data-testid="sky-place-error" id="sky-place-error-text">
            {placeError}
          </Text>
        )}

        <Button
          block
          icon={<Sunrise size={14} aria-hidden="true" />}
          loading={loading}
          disabled={loading}
          aria-label="Next sunrise at this location"
          onClick={() => {
            void onNextSunrise();
          }}
        >
          {loading ? 'Finding sunrise…' : 'Next sunrise here'}
        </Button>

        {sunriseNote !== null && (
          <Text data-testid="sky-time-sunrise-note">
            {sunriseNote} <ProvenanceTag kind="computed" />
          </Text>
        )}
        {error !== null && (
          <Text type="danger" role="alert" data-testid="sky-time-error">
            {error}
          </Text>
        )}
      </Space>
    </Card>
  );
}
