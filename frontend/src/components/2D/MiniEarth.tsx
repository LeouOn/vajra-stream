import { useEffect, useRef, useState } from 'react';

import { DEFAULT_LNG } from '../../lib/geo';
import {
  SUNRISE_ALTITUDE_DEG,
  extrapolateSubPoint,
  shownNowMs,
  terminatorPoints,
  wrapLon,
  type EarthState,
  type SubPoint,
} from '../../lib/earth';
import { clipRingToDisc, nightFactorMask, orthographicProject } from '../../lib/orthographic';
import { useEarthState } from '../../stores/earthStateStore';

/**
 * 2D orthographic mini Earth — replaces the second WebGL canvas on the
 * Broadcast tab (W1-D2). Draws the 110 m land rings, the night side as a
 * 0.38 multiply from the sub-solar point, the dawn line (sunrise half warm)
 * and a small status dot. Redraws at 1 Hz with a slow eastward drift of the
 * disc centre; no requestAnimationFrame, no random source, timer stops when
 * the document is hidden or the canvas is disconnected.
 *
 * Until the earth-state store lands (W1-D1) the component takes the state
 * as a prop; the store hook is wired at integration.
 */

const SIZES = { small: 200, large: 320 } as const;
const DRIFT_DEG_PER_TICK = 1 / 60; // <= 1 deg/min at the 1 Hz tick
const TICK_MS = 1000;

interface MiniEarthProps {
  isActive: boolean;
  size: 'small' | 'large';
  /** Earth state; when null the land is drawn without night/dawn and an
   * "ephemeris unavailable" label is shown. */
  state?: EarthState | null;
}

export function MiniEarth({ isActive, size, state }: MiniEarthProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [land, setLand] = useState<{ polys: { o: number[]; h: number[][] }[] } | null>(null);
  const driftRef = useRef(0);
  // The shared store drives the component; an explicit prop overrides it
  // (tests pass a literal state; undefined falls through to the store).
  const slice = useEarthState();
  const effective = state !== undefined ? state : slice.status === 'ok' ? slice.state : null;
  const stateRef = useRef<EarthState | null>(effective);
  stateRef.current = effective;
  // A scrubbed (frozen) slice must not drift with the wall clock; an explicit `state` prop is always "live".
  const clockRef = useRef<{ frozen?: boolean; fetchedAt: number | null }>(slice);
  clockRef.current = state !== undefined ? { fetchedAt: null } : slice;

  useEffect(() => {
    let cancelled = false;
    // The 110 m rings load lazily so they stay out of the initial bundle.
    import('../../data/land-110m.json').then((mod) => {
      if (!cancelled) setLand(mod.default as { polys: { o: number[]; h: number[][] }[] });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    const radius = SIZES[size] / 2;

    const draw = () => {
      if (!canvas.isConnected || document.hidden) return;
      if (!ctx) return;
      const centreLon = wrapLon(DEFAULT_LNG + driftRef.current);
      const centre: SubPoint = { lat: 20, lon: centreLon };
      ctx.clearRect(0, 0, radius * 2, radius * 2);

      // Ocean disc
      ctx.save();
      ctx.beginPath();
      ctx.arc(radius, radius, radius - 0.5, 0, 2 * Math.PI);
      ctx.clip();
      ctx.fillStyle = '#0b2a4a';
      ctx.fillRect(0, 0, radius * 2, radius * 2);

      // Land rings (outer rings only; holes would be sub-pixel at this
      // size), clipped at the horizon so a ring crossing the limb closes
      // along the limb instead of drawing a straight chord (W1-D2c).
      if (land) {
        ctx.fillStyle = '#d8d2c4';
        ctx.beginPath();
        for (const poly of land.polys) {
          const flat = poly.o;
          const ring: Array<{ lat: number; lon: number }> = [];
          for (let i = 0; i < flat.length; i += 2) {
            ring.push({ lon: flat[i] / 1000, lat: flat[i + 1] / 1000 });
          }
          for (const cmd of clipRingToDisc(ring, centre, radius)) {
            if (cmd.op === 'M') ctx.moveTo(cmd.x, cmd.y);
            else if (cmd.op === 'L') ctx.lineTo(cmd.x, cmd.y);
            else ctx.arc(radius, radius, radius - 0.5, cmd.a0, cmd.a1, cmd.a1 < cmd.a0);
          }
        }
        ctx.fill();
      }

      // Night side (W1-D2b): exact per-pixel mask — invert the orthographic
      // projection per pixel, evaluate the Sun altitude, ramp 0 at the
      // sunrise altitude to the full 0.38 multiply by civil twilight (-6 deg).
      const current = stateRef.current;
      if (current) {
        const atMs = Date.parse(current.at);
        const age = Number.isFinite(atMs) ? Math.max(0, (shownNowMs(clockRef.current, Date.now()) - atMs) / 1000) : 0;
        const sun = extrapolateSubPoint({ lat: current.sun.lat, lon: current.sun.lon }, age);
        // Half-resolution mask: the night ramp is a smooth gradient, so a
        // (radius/2) mask upscaled on composite is visually identical at
        // 200-320 px and a quarter of the per-pixel work.
        const maskRadius = Math.max(16, radius >> 1);
        const mask = nightFactorMask(centre, sun, maskRadius);
        const img = ctx.createImageData(maskRadius * 2, maskRadius * 2);
        for (let i = 0; i < mask.length; i += 1) {
          const f = mask[i];
          if (f > 0) {
            const o = i * 4;
            img.data[o] = 97;
            img.data[o + 1] = 97;
            img.data[o + 2] = 112;
            img.data[o + 3] = Math.round(255 * f);
          }
        }
        const off = document.createElement('canvas');
        off.width = maskRadius * 2;
        off.height = maskRadius * 2;
        off.getContext('2d')?.putImageData(img, 0, 0);
        ctx.globalCompositeOperation = 'multiply';
        ctx.drawImage(off, 0, 0, radius * 2, radius * 2);
        ctx.globalCompositeOperation = 'source-over';

        // Dawn line: terminator at the sunrise altitude; sunrise half warm.
        const terminator = terminatorPoints(sun, SUNRISE_ALTITUDE_DEG, 180);
        for (const side of ['sunrise', 'sunset'] as const) {
          ctx.strokeStyle = side === 'sunrise' ? 'rgba(255,190,120,0.85)' : 'rgba(120,140,180,0.5)';
          ctx.lineWidth = side === 'sunrise' ? 1.2 : 0.8;
          ctx.beginPath();
          let open = false;
          for (const point of terminator) {
            if (point.side !== side) continue;
            const p = orthographicProject(point, centre, radius);
            if (p.visible) {
              if (open) ctx.lineTo(p.x, p.y);
              else {
                ctx.moveTo(p.x, p.y);
                open = true;
              }
            } else open = false;
          }
          ctx.stroke();
        }
      }
      ctx.restore();

      // Limb
      ctx.strokeStyle = 'rgba(255,255,255,0.25)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(radius, radius, radius - 0.5, 0, 2 * Math.PI);
      ctx.stroke();

      // Status dot
      if (isActive) {
        ctx.fillStyle = '#7ef29a';
        ctx.beginPath();
        ctx.arc(radius * 2 - 10, 10, 3.5, 0, 2 * Math.PI);
        ctx.fill();
      }

    };

    draw();
    const timer = window.setInterval(() => {
      driftRef.current += DRIFT_DEG_PER_TICK;
      draw();
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [isActive, land, size, effective, slice.fetchedAt, slice.frozen]);

  const px = SIZES[size];
  return (
    <div className="relative inline-block" data-testid="mini-earth-wrap">
      <canvas
        ref={canvasRef}
        width={px}
        height={px}
        className="rounded-full bg-transparent"
        role="img"
        aria-label="Orthographic mini Earth"
        data-testid="mini-earth"
      />
      {effective === null && (
        <span
          className="absolute inset-x-0 bottom-1 text-center text-[9px] leading-none text-white/80 select-none"
          data-testid="mini-earth-unavailable"
        >
          ephemeris unavailable
        </span>
      )}
    </div>
  );
}
