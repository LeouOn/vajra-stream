/**
 * Pure star-field layer for the night-sky dome.
 *
 * No React and no canvas. The dome paints the returned buffer with one
 * putImageData and strokes the returned segments. Geometry matches the
 * dome: radius = size * 0.42, centre at (size/2, size/2), and domePoint.
 * Only altitude strictly above the horizon is drawn.
 */
import {
  constellationSegments,
  domePoint,
  eclipticPoints,
  equatorialToHorizontal,
  precessJ2000,
  starAlpha,
  starRadiusPx,
  starRgb,
  type ConstellationLines,
  type Star,
} from './sky';

export interface SkySegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface SkyLayerRequest {
  stars: readonly Star[];
  lines: ConstellationLines;
  lstDeg: number;
  latDeg: number;
  jd: number;
  size: number;
  showCatalogue: boolean;
  showFigures: boolean;
  showEcliptic: boolean;
}

export interface SkyLayerBuffers {
  /** Backed by a plain ArrayBuffer so the dome can pass it to ImageData. */
  stars: Uint8ClampedArray<ArrayBuffer>;
  figures: SkySegment[];
  ecliptic: SkySegment[];
}

interface Placed {
  x: number;
  y: number;
}

function projectStar(
  ra: number,
  dec: number,
  precess: boolean,
  lstDeg: number,
  latDeg: number,
  jd: number,
  radius: number,
  cx: number,
  cy: number,
): Placed | null {
  const eq = precess ? precessJ2000(ra, dec, jd) : { ra, dec };
  const horizontal = equatorialToHorizontal(eq.ra, eq.dec, lstDeg, latDeg);
  if (!(horizontal.alt > 0)) return null;
  return domePoint(horizontal.alt, horizontal.az, radius, cx, cy);
}

function stamp(
  buffer: Uint8ClampedArray,
  grid: number,
  x: number,
  y: number,
  radiusPx: number,
  rgb: [number, number, number],
  alpha: number,
): void {
  if (!(alpha > 0)) return;
  // Straight RGBA. The dome drawImages this buffer, and canvas compositing
  // multiplies RGB by alpha. Premultiplying here would fade faint stars twice.
  const red = rgb[0];
  const green = rgb[1];
  const blue = rgb[2];
  const channelA = Math.round(alpha * 255);
  const blend = (col: number, row: number): void => {
    if (col < 0 || row < 0 || col >= grid || row >= grid) return;
    const offset = (row * grid + col) * 4;
    if (red > buffer[offset]) buffer[offset] = red;
    if (green > buffer[offset + 1]) buffer[offset + 1] = green;
    if (blue > buffer[offset + 2]) buffer[offset + 2] = blue;
    if (channelA > buffer[offset + 3]) buffer[offset + 3] = channelA;
  };
  const reach = radiusPx * radiusPx;
  const minCol = Math.max(0, Math.floor(x - radiusPx));
  const maxCol = Math.min(grid - 1, Math.ceil(x + radiusPx));
  const minRow = Math.max(0, Math.floor(y - radiusPx));
  const maxRow = Math.min(grid - 1, Math.ceil(y + radiusPx));
  for (let row = minRow; row <= maxRow; row += 1) {
    const dy = row + 0.5 - y;
    for (let col = minCol; col <= maxCol; col += 1) {
      const dx = col + 0.5 - x;
      if (dx * dx + dy * dy <= reach) blend(col, row);
    }
  }
  // A sub-pixel radius can miss every pixel centre. The nearest pixel still
  // carries the star, or a V 6.4 star at an arbitrary position would vanish.
  blend(Math.round(x - 0.5), Math.round(y - 0.5));
}

function segmentsFrom(
  points: (Placed | null)[],
  close: boolean,
): SkySegment[] {
  const segments: SkySegment[] = [];
  const count = points.length;
  if (count < 2) return segments;
  const last = close ? count : count - 1;
  for (let i = 0; i < last; i += 1) {
    const start = points[i];
    const end = points[(i + 1) % count];
    if (start === null || end === null) continue;
    segments.push({ x1: start.x, y1: start.y, x2: end.x, y2: end.y });
  }
  return segments;
}

export function buildSkyLayer(request: SkyLayerRequest): SkyLayerBuffers {
  const grid = Math.max(1, Math.round(request.size));
  const cx = grid / 2;
  const cy = grid / 2;
  const radius = grid * 0.42;
  const stars = new Uint8ClampedArray(grid * grid * 4);

  if (request.showCatalogue) {
    for (let i = 0; i < request.stars.length; i += 1) {
      const star = request.stars[i];
      const placed = projectStar(
        star.ra,
        star.dec,
        true,
        request.lstDeg,
        request.latDeg,
        request.jd,
        radius,
        cx,
        cy,
      );
      if (placed === null) continue;
      stamp(stars, grid, placed.x, placed.y, starRadiusPx(star.v), starRgb(star.bv), starAlpha(star.v));
    }
  }

  let figures: SkySegment[] = [];
  if (request.showFigures) {
    const byHr = new Map<number, Star>();
    for (let i = 0; i < request.stars.length; i += 1) {
      byHr.set(request.stars[i].hr, request.stars[i]);
    }
    const groups = constellationSegments(request.lines, byHr);
    for (let g = 0; g < groups.length; g += 1) {
      const polylines = groups[g].polylines;
      for (let p = 0; p < polylines.length; p += 1) {
        const placed: (Placed | null)[] = [];
        const polyline = polylines[p];
        for (let s = 0; s < polyline.length; s += 1) {
          const star = polyline[s];
          placed.push(
            projectStar(star.ra, star.dec, true, request.lstDeg, request.latDeg, request.jd, radius, cx, cy),
          );
        }
        const parts = segmentsFrom(placed, false);
        for (let k = 0; k < parts.length; k += 1) figures.push(parts[k]);
      }
    }
  }

  let ecliptic: SkySegment[] = [];
  if (request.showEcliptic) {
    const samples = eclipticPoints(request.jd);
    const placed: (Placed | null)[] = [];
    for (let i = 0; i < samples.length; i += 1) {
      const sample = samples[i];
      placed.push(
        projectStar(sample.ra, sample.dec, false, request.lstDeg, request.latDeg, request.jd, radius, cx, cy),
      );
    }
    ecliptic = segmentsFrom(placed, true);
  }

  return { stars, figures, ecliptic };
}
