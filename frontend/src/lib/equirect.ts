/**
 * Earth & Sky wave 3 — flat equirectangular "world clock" strip (W3-E).
 *
 * Pure maths and a deterministic render function for an equirectangular
 * full-world strip (lng -180..180 left to right, lat 90..-90 top to bottom,
 * 2:1 aspect). The strip is easier than a globe for reading the 24-hour
 * wave: every longitude is visible at once, the night side is an exact
 * per-pixel mask (the Wave 1 lesson: shading is physics — see
 * orthographic.ts and its night tests), and the dawn line splits into the
 * sunrise (warm) and sunset (cool) halves at the SAME sunrise altitude
 * constant the globes use (SUNRISE_ALTITUDE_DEG, never a second number).
 *
 * No React, no WebGL, no animation: drawWorldStrip(ctx, view) paints one
 * complete frame, so a harness can screenshot it at any sun position.
 */
import {
  SUNRISE_ALTITUDE_DEG,
  paintLand,
  terminatorPoints,
  wrapLon,
  type LandData,
  type SubPoint,
} from './earth';
import { NIGHT_RAMP_END_ALT_DEG, NIGHT_RAMP_START_ALT_DEG } from './orthographic';

const RAD = Math.PI / 180;
const TAU = Math.PI * 2;

/** Ramp bounds in sin(altitude), shared with the globes' night mask. */
const SIN_START = Math.sin(NIGHT_RAMP_START_ALT_DEG * RAD);
const SIN_END = Math.sin(NIGHT_RAMP_END_ALT_DEG * RAD);

export interface LatLon {
  lat: number;
  lng: number;
}

/** A minimal ImageData shape, buildable without a canvas. */
export interface ImageDataLike {
  width: number;
  height: number;
  data: Uint8ClampedArray;
}

/** Place -> strip pixel (continuous coordinates; y grows down). */
export function latLonToXY(lat: number, lng: number, width: number, height: number): { x: number; y: number } {
  return {
    x: ((lng + 180) / 360) * width,
    y: ((90 - lat) / 180) * height,
  };
}

/**
 * Strip pixel -> place. Horizontally wrap-aware (the right edge and
 * anything past it wraps to the far east of -180, so dawn paths and clicks
 * never produce |lng| > 180); vertically clamped to the poles.
 */
export function xyToLatLon(x: number, y: number, width: number, height: number): LatLon {
  const fx = (((x / width) % 1) + 1) % 1;
  const clampedY = Math.min(height, Math.max(0, y));
  return {
    lng: wrapLon(fx * 360 - 180),
    lat: 90 - (clampedY / height) * 180,
  };
}

/**
 * Exact night factor for one pixel: the solar altitude of the pixel's
 * point, ramped exactly like the globes' mask (0 at and above
 * SUNRISE_ALTITUDE_DEG, 1 at and below -6 deg civil twilight, linear in
 * sin(altitude) between). sin(altitude) comes from the hour-angle form —
 * sin(lat)sin(dec) + cos(lat)cos(dec)cos(lng - sun.lon) — so no per-pixel
 * asin/acos is needed.
 */
export function nightFactorAt(
  sun: SubPoint,
  width: number,
  height: number,
  x: number,
  y: number,
): number {
  const { lat, lng } = xyToLatLon(x, y, width, height);
  const sinAlt =
    Math.sin(lat * RAD) * Math.sin(sun.lat * RAD) +
    Math.cos(lat * RAD) * Math.cos(sun.lat * RAD) * Math.cos((lng - sun.lon) * RAD);
  if (sinAlt >= SIN_START) return 0;
  if (sinAlt <= SIN_END) return 1;
  return (SIN_START - sinAlt) / (SIN_START - SIN_END);
}

/** Night factor at every pixel centre; row-major, length width*height. */
export function nightFactorMask(sun: SubPoint, width: number, height: number): Float32Array {
  const mask = new Float32Array(width * height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      mask[y * width + x] = nightFactorAt(sun, width, height, x + 0.5, y + 0.5);
    }
  }
  return mask;
}

/**
 * The night overlay actually composited onto the strip: rgb 97,97,112 with
 * alpha = round(255 * factor) (the MiniEarth night tint), alpha 0 in day.
 * Composited with 'multiply' it darkens land and ocean exactly as the mini
 * globe's night side does.
 */
export function nightOverlay(sun: SubPoint, width: number, height: number): ImageDataLike {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const f = nightFactorAt(sun, width, height, x + 0.5, y + 0.5);
      if (f > 0) {
        const o = (y * width + x) * 4;
        data[o] = 97;
        data[o + 1] = 97;
        data[o + 2] = 112;
        data[o + 3] = Math.round(255 * f);
      }
    }
  }
  return { width, height, data };
}

export interface DawnPath {
  side: 'sunrise' | 'sunset';
  /**
   * Polyline in strip pixels, x UNWRAPPED (may exceed [0, width) where the
   * half crosses the antimeridian); the draw function paints each path at
   * offsets -width, 0 and +width so both map edges show the crossing.
   */
  points: Array<{ x: number; y: number }>;
}

/**
 * The day/night boundary at SUNRISE_ALTITUDE_DEG as two continuous pixel
 * polylines: the sunset (east) half — terminator bearings 0..180 — and the
 * sunrise (west) half, bearings 180..360. terminatorPoints classifies
 * sides by wrapped longitude difference, which flips exactly at the
 * antimeridian seam points (both curve extremes sit at dlon 180 and get
 * labelled 'sunrise'), so the side here comes from the bearing sector
 * instead. Longitudes are unwrapped from the ARC'S MIDDLE outwards, where
 * the longitude is unambiguous, so no polyline jumps the antimeridian.
 */
export function dawnPaths(
  sun: SubPoint,
  width: number,
  height: number,
  segments = 360,
): DawnPath[] {
  const n = Math.max(4, segments);
  const pts = terminatorPoints(sun, SUNRISE_ALTITUDE_DEG, n);
  if (pts.length < 4) return [];
  const half = Math.floor(pts.length / 2);

  const unwrapArc = (from: number, to: number): Array<{ x: number; y: number }> => {
    const count = to - from + 1;
    const mid = from + Math.floor(count / 2);
    const lu: number[] = new Array(count);
    lu[mid - from] = pts[mid].lon;
    for (let k = mid + 1; k <= to; k += 1) {
      const prev = lu[k - 1 - from];
      lu[k - from] = prev + wrapLon(pts[k].lon - prev);
    }
    for (let k = mid - 1; k >= from; k -= 1) {
      const next = lu[k + 1 - from];
      lu[k - from] = next + wrapLon(pts[k].lon - next);
    }
    const out: Array<{ x: number; y: number }> = [];
    for (let k = from; k <= to; k += 1) {
      out.push(latLonToXY(pts[k].lat, lu[k - from], width, height));
    }
    return out;
  };

  return [
    { side: 'sunset', points: unwrapArc(0, half) },
    { side: 'sunrise', points: unwrapArc(half, pts.length - 1) },
  ];
}

/** Palette mirrors the mini globe (MiniEarth): navy ocean, cream land. */
export const STRIP_COLORS = { ocean: '#0b2a4a', land: '#d8d2c4' } as const;

const EMPTY_LAND: LandData = { v: 1, kind: 'land', decimals: 0, polys: [] };

export interface WorldStripView {
  width: number;
  height: number;
  /** Decoded land rings; null paints ocean only. */
  land: LandData | null;
  /** Sub-solar point; null draws no night mask, no dawn line, no sun marker. */
  sun: SubPoint | null;
  /** Observer marker; null or omitted draws none. */
  observer?: { lat: number; lng: number } | null;
}

/**
 * Paint one complete strip frame onto a 2d context, deterministically, in
 * this order: ocean, land rings (even-odd, holes subtract), the exact
 * per-pixel night mask (full resolution), the dawn line (each half at -width/0/+width so an
 * antimeridian crossing shows on both edges), the sun and observer
 * markers, and a one-pixel frame. Nothing here depends on time or on any
 * store: pass a sun position, get the picture. `makeOffscreen` exists so a
 * headless harness can inject a canvas double for the mask composite.
 */
export function drawWorldStrip(
  ctx: CanvasRenderingContext2D,
  view: WorldStripView,
  makeOffscreen: (w: number, h: number) => HTMLCanvasElement = (w, h) => {
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    return canvas;
  },
): void {
  const { width: w, height: h, land, sun, observer } = view;

  // Ocean + land: the committed equirectangular painter from lib/earth.
  paintLand(ctx, land ?? EMPTY_LAND, w, h, STRIP_COLORS);

  if (sun) {
    // Night mask at FULL resolution: "exact per-pixel" is the contract (the
    // mini globe's half-resolution ramp was a cost compromise; here the
    // mask is evaluated for every pixel centre). Composited with multiply so
    // land and ocean both darken.
    const off = makeOffscreen(w, h);
    const offCtx = off.getContext('2d');
    if (offCtx) {
      const img = ctx.createImageData(w, h);
      img.data.set(nightOverlay(sun, w, h).data);
      offCtx.putImageData(img, 0, 0);
      ctx.save();
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(off, 0, 0, w, h);
      ctx.restore();
    }

    // Dawn line: sunrise half warm, sunset half cool; painted thrice so
    // both edges of the map show the half that crosses the antimeridian.
    for (const path of dawnPaths(sun, w, h, 180)) {
      ctx.strokeStyle = path.side === 'sunrise' ? 'rgba(255,190,120,0.85)' : 'rgba(120,140,180,0.5)';
      ctx.lineWidth = path.side === 'sunrise' ? 1.2 : 0.8;
      for (const dx of [-w, 0, w]) {
        ctx.beginPath();
        path.points.forEach((p, i) => {
          if (i === 0) ctx.moveTo(p.x + dx, p.y);
          else ctx.lineTo(p.x + dx, p.y);
        });
        ctx.stroke();
      }
    }

    // Sub-solar marker: warm halo + core.
    const s = latLonToXY(sun.lat, sun.lon, w, h);
    ctx.fillStyle = 'rgba(255,214,102,0.35)';
    ctx.beginPath();
    ctx.arc(s.x, s.y, 9, 0, TAU);
    ctx.fill();
    ctx.fillStyle = '#ffd678';
    ctx.beginPath();
    ctx.arc(s.x, s.y, 4, 0, TAU);
    ctx.fill();
  }

  // Observer marker: ring + centre dot.
  if (observer) {
    const o = latLonToXY(observer.lat, observer.lng, w, h);
    ctx.strokeStyle = '#7ef29a';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(o.x, o.y, 5, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = '#7ef29a';
    ctx.beginPath();
    ctx.arc(o.x, o.y, 1.5, 0, TAU);
    ctx.fill();
  }

  // Frame.
  ctx.strokeStyle = 'rgba(255,255,255,0.25)';
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
}
