import { useEffect, useRef, useState } from 'react';

import {
  decodeLand,
  extrapolateSubPoint,
  type EarthState,
  type LandData,
  type SubPoint,
} from '../../lib/earth';
import { drawWorldStrip, xyToLatLon } from '../../lib/equirect';
import { useEarthState } from '../../stores/earthStateStore';

/**
 * Flat equirectangular world strip (W3-E): land, the exact night mask, the
 * dawn line and the sub-solar point on one 2:1 canvas — the "world clock"
 * view where every longitude is readable at once.
 *
 * One canvas, redrawn at 1 Hz (no requestAnimationFrame loop; nothing
 * animates between ticks, so prefers-reduced-motion is honoured trivially),
 * paused when the document is hidden or the canvas is disconnected — the
 * MiniEarth lifecycle. Land is the same lazy 110 m rings the mini globe
 * uses; the sun comes from the shared earth-state store (an explicit `sun`
 * prop overrides it — tests and the layout row use that). No observer/
 * clock store dependency yet: the W3 layout row wires `observer` and
 * `onPick` to the skyStore.
 */
const TICK_MS = 1000;
const DEFAULT_WIDTH = 720;
const MIN_WIDTH_CHANGE = 2;

interface WorldStripProps {
  /** Click -> place (wrap-aware lat/lng). */
  onPick?: (lat: number, lng: number) => void;
  /** Observer marker position; null or omitted draws none. */
  observer?: { lat: number; lng: number } | null;
  className?: string;
  /** Sub-solar point override; undefined falls through to the shared store. */
  sun?: SubPoint | null;
}

export function WorldStrip({ onPick, observer, className, sun }: WorldStripProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [land, setLand] = useState<LandData | null>(null);
  const [width, setWidth] = useState(DEFAULT_WIDTH);

  // The shared store drives the sun; an explicit prop overrides it (the
  // MiniEarth pattern: tests pass a literal, undefined falls to the store).
  const slice = useEarthState();
  const stateRef = useRef<EarthState | null>(slice.state);
  stateRef.current = slice.state;
  const sunPropRef = useRef<SubPoint | null | undefined>(sun);
  sunPropRef.current = sun;

  const sunAvailable = sun !== undefined ? sun !== null : slice.status === 'ok' && slice.state !== null;

  useEffect(() => {
    let cancelled = false;
    // The 110 m rings load lazily so they stay out of the initial bundle.
    import('../../data/land-110m.json')
      .then((mod) => {
        if (!cancelled) setLand(decodeLand(mod.default));
      })
      .catch(() => {
        if (!cancelled) setLand(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap || typeof ResizeObserver === 'undefined') return undefined;
    const observer_ = new ResizeObserver((entries) => {
      const w = Math.round(entries[0]?.contentRect.width ?? 0);
      if (w > 0) setWidth((prev) => (Math.abs(prev - w) >= MIN_WIDTH_CHANGE ? w : prev));
    });
    observer_.observe(wrap);
    return () => observer_.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');

    const draw = () => {
      if (!ctx || !canvas.isConnected || document.hidden) return;
      const w = Number(canvas.getAttribute('width')) || width;
      const h = Number(canvas.getAttribute('height')) || Math.round(width / 2);
      let effective: SubPoint | null = null;
      if (sunPropRef.current !== undefined) {
        effective = sunPropRef.current;
      } else {
        const state = stateRef.current;
        if (state) {
          const atMs = Date.parse(state.at);
          const age = Number.isFinite(atMs) ? Math.max(0, (Date.now() - atMs) / 1000) : 0;
          effective = extrapolateSubPoint({ lat: state.sun.lat, lon: state.sun.lon }, age);
        }
      }
      drawWorldStrip(ctx, {
        width: w,
        height: h,
        land,
        sun: effective,
        observer,
      });
    };

    draw();
    const timer = window.setInterval(draw, TICK_MS);
    return () => window.clearInterval(timer);
    // slice.fetchedAt re-triggers on every store poll; identity of the
    // other inputs redraws on change.
  }, [land, width, observer, sun, slice.fetchedAt]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !onPick) return;
    const rect = canvas.getBoundingClientRect();
    const ch = Math.round(width / 2);
    // When the canvas is unmeasured (headless tests), scale is identity.
    const x = (e.clientX - rect.left) * (rect.width > 0 ? width / rect.width : 1);
    const y = (e.clientY - rect.top) * (rect.height > 0 ? ch / rect.height : 1);
    const { lat, lng } = xyToLatLon(x, y, width, ch);
    onPick(lat, lng);
  };

  const height = Math.round(width / 2);
  return (
    <div ref={wrapRef} className={`relative ${className ?? ''}`} data-testid="world-strip-wrap">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onClick={handleClick}
        className="block w-full cursor-crosshair"
        role="img"
        aria-label="Equirectangular world strip: land, the day-night boundary and the sub-solar point"
        data-testid="world-strip"
      />
      {!sunAvailable && (
        <span
          className="absolute inset-x-0 bottom-1 text-center text-[9px] leading-none text-white/80 select-none"
          data-testid="world-strip-unavailable"
        >
          ephemeris unavailable
        </span>
      )}
    </div>
  );
}
