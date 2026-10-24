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
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card, Slider, Space, Tag, Typography } from 'antd';
import { Pause, Play, Sunrise } from 'lucide-react';

import { useSkyStore } from '../../stores/skyStore';
import {
  SCRUB_LIMIT_MS,
  clampScrub,
  effectiveInstant,
  offsetMinutes,
  parseInstant,
} from '../../lib/skyClock';
import { fetchSunEvents } from '../../lib/sunEventsClient';
import ProvenanceTag from './ProvenanceTag';

const { Text } = Typography;
const TICK_MS = 1000;

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
  const requestId = useRef(0);

  // One clock for the readout and the offset; no work while the tab is hidden.
  useEffect(() => {
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
  }, []);

  // A sunrise belongs to the place it was fetched for: when the observer
  // moves, any in-flight answer is stale and the note no longer applies.
  useEffect(() => {
    requestId.current += 1;
    setLoading(false);
    setSunriseNote(null);
    setError(null);
  }, [lat, lng]);

  const isLive = at === null;
  const shownMs = effectiveInstant(at, now).getTime();
  const offset = isLive ? 0 : offsetMinutes(at, now);
  const sliderValue = Math.max(-1440, Math.min(1440, Math.round(offset)));
  const observerText = label
    ? `${label} · ${lat.toFixed(4)}, ${lng.toFixed(4)}`
    : `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

  const onLive = useCallback(() => {
    requestId.current += 1;
    setLoading(false);
    setSunriseNote(null);
    setError(null);
    setNow(Date.now());
    goLive();
  }, [goLive]);

  const onPause = useCallback(() => {
    const nowMs = Date.now();
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
      requestId.current += 1;
      setLoading(false);
      setAt(new Date(target).toISOString());
    },
    [setAt],
  );

  const onNextSunrise = useCallback(async () => {
    const request = (requestId.current += 1);
    setLoading(true);
    setError(null);
    setSunriseNote(null);
    try {
      const events = await fetchSunEvents(lat, lng, new Date(shownMs).toISOString());
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
            <Tag color={isLive ? 'green' : 'gold'} style={{ marginInlineEnd: 6 }}>
              {isLive ? 'Live' : 'Paused'}
            </Tag>
            <Text>{shownAt}</Text>
          </div>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {offsetText}
          </Text>
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
