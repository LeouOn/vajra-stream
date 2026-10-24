/**
 * CelestialSkyDome.tsx — Real-time topocentric night sky dome visualizer.
 *
 * Renders the visible sky above the practitioner's location:
 * - Zenith-centered horizon projection (0° to 90° altitude)
 * - Real-time planetary positions with sacred glyphs & colors
 * - Sacred Vedic fixed stars and Nakshatras (Sirius, Vega, Arcturus, etc.)
 * - Moon phase, illumination, and Local Sidereal Time (LST)
 */
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Card, Tag, Button, Space, Switch, Tooltip, Spin, Badge } from 'antd';
import { Compass, Sparkles, Moon, Sun, Eye, RefreshCw } from 'lucide-react';
import {
  cancelNightSkyRequest,
  fetchNightSky,
  NightSkyError,
  type NightSky as NightSkyPayload,
  type NightSkyErrorKind,
  type NightSkyPlanet,
  type NightSkyStar,
} from '../../lib/nightSkyClient';
import { useSkyStore } from '../../stores/skyStore';
import { useSkySeries } from '../../stores/skySeriesStore';
import {
  localScrubLst,
  sacredHorizontal,
  skyAtInstant,
  type ScrubbedSky,
} from '../../lib/skyScrub';
import { offsetMinutes, parseInstant } from '../../lib/skyClock';
import {
  domePoint,
  equatorialToHorizontal,
  julianDay,
  loadConstellationLines,
  loadStars,
  precessJ2000,
  starRadiusPx,
  starRgb,
  type ConstellationLines,
  type Star,
} from '../../lib/sky';
import {
  NIGHT_SUN_ALT_DEG,
  skyBackground,
  starAlpha as daylightStarAlpha,
} from '../../lib/skyBrightness';
import { buildSkyLayer } from '../../lib/skyLayer';
import ProvenanceTag from './ProvenanceTag';

const SEE_THROUGH_KEY = 'vajra.dome.seeThroughDaylight';

/** Per-viewer convenience only; anything goes wrong -> default off. */
function readSeeThroughPreference(): boolean {
  try {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(SEE_THROUGH_KEY) === '1';
  } catch {
    return false;
  }
}

/** Two-decimal degrees for DISPLAY only (drawing keeps the raw value). */
export function formatDeg(deg: number): string {
  return deg.toFixed(2);
}

/** "+2h 05m" style scrub offset. */
function formatOffset(minutes: number): string {
  const sign = minutes < 0 ? '-' : '+';
  const magnitude = Math.abs(Math.round(minutes));
  const hours = Math.floor(magnitude / 60);
  const mins = magnitude % 60;
  return `${sign}${hours}h ${String(mins).padStart(2, '0')}m`;
}

/** A planet drawn on the dome, with the position for the shown instant. */
interface PlanetMark {
  planet: NightSkyPlanet;
  alt: number;
  az: number;
}

/** A sacred star drawn on the dome, with the position for the shown instant. */
interface SacredMark {
  star: NightSkyStar;
  alt: number;
  az: number;
}

/** A response is fresh enough to advance the catalogue clock for two polls. */
const SKY_FRESH_MS = 2 * 60_000;

/** Visible wording for the failure class shown in the unavailable state. */
function reasonLabel(kind: string | null): string {
  switch (kind) {
    case 'invalid-response':
      return 'the server answer was malformed';
    case 'unavailable':
      return 'the ephemeris is unavailable';
    case 'network':
      return 'the server could not be reached';
    case 'invalid-input':
      return 'the observer request was rejected';
    case 'http':
      return 'the server returned an error';
    case 'stale':
      return 'a newer request replaced this one';
    default:
      return 'an unknown error';
  }
}

/** Mean sidereal rate, degrees per second. The row pins this literal. */
const SIDEREAL_DEG_PER_SEC = 0.0041781;
const LAYER_LST_STEP_DEG = 0.02;

/** Mean of the decorative twinkle sine (0.8 + 0.2*sin): the still value. */
const TWINKLE_REST_ALPHA = 0.8;
/** Fastest the decorative twinkle may redraw (spec budget: 30 fps). */
const TWINKLE_FRAME_MS = 33;
/** A still sky redraws at 1 Hz, and with reduced motion nothing runs faster. */
const STILL_REDRAW_MS = 1000;
/** Passed to the layer builder when the constellation figures are unavailable. */
const EMPTY_LINES: ConstellationLines = { crosswalk: '', tolerance_arcsec: 0, constellations: {} };

/**
 * True when the user's system asks for reduced motion. Read live: a `change`
 * listener (removed on unmount) lets the dome calm down without a reload.
 */
function usePrefersReducedMotion(): boolean {
  const query = '(prefers-reduced-motion: reduce)';
  const [reduced, setReduced] = useState<boolean>(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const media = window.matchMedia(query);
    setReduced(media.matches);
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  return reduced;
}

function wrap360(deg: number): number {
  return ((deg % 360) + 360) % 360;
}

function angleDelta(a: number, b: number): number {
  const d = Math.abs(a - b) % 360;
  return d > 180 ? 360 - d : d;
}

interface Props {
  latitude?: number;
  longitude?: number;
  className?: string;
}

export default function CelestialSkyDome({ latitude, longitude, className = '' }: Props): React.ReactElement {
  // Props still win for callers that pin a place (all existing callers);
  // otherwise the shared observer store (globe/strip pick) moves the dome.
  const storeLat = useSkyStore((state) => state.lat);
  const storeLng = useSkyStore((state) => state.lng);
  const scrubAtIso = useSkyStore((state) => state.at);
  const observerLat = latitude ?? storeLat;
  const observerLng = longitude ?? storeLng;
  const scrubMode = scrubAtIso !== null;
  const scrubAtMs = useMemo(
    () => (scrubAtIso === null ? null : parseInstant(scrubAtIso)),
    [scrubAtIso],
  );

  const [data, setData] = useState<NightSkyPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [status, setStatus] = useState<'loading' | 'ok' | 'stale' | 'unavailable'>('loading');
  const [errorKind, setErrorKind] = useState<NightSkyErrorKind | null>(null);
  const [lastGoodAt, setLastGoodAt] = useState<number | null>(null);
  const {
    series,
    status: seriesStatus,
    error: seriesError,
    errorKind: seriesErrorKind,
    fetchedAtMs: seriesFetchedAtMs,
  } = useSkySeries();
  const [showStars, setShowStars] = useState<boolean>(true);
  const [showPlanets, setShowPlanets] = useState<boolean>(true);
  const [showCatalogue, setShowCatalogue] = useState<boolean>(true);
  const [showFigures, setShowFigures] = useState<boolean>(true);
  const [showEcliptic, setShowEcliptic] = useState<boolean>(true);
  const [seeThrough, setSeeThrough] = useState<boolean>(readSeeThroughPreference);
  const [catalogue, setCatalogue] = useState<Star[] | null>(null);
  const [figureLines, setFigureLines] = useState<ConstellationLines | null>(null);
  const [catalogueStatus, setCatalogueStatus] = useState<'pending' | 'ready' | 'unavailable'>('pending');
  const [figuresStatus, setFiguresStatus] = useState<'pending' | 'ready' | 'unavailable'>('pending');
  const reducedMotion = usePrefersReducedMotion();
  const [hoveredObject, setHoveredObject] = useState<{
    name: string;
    sub: string;
    alt: number;
    az: number;
    extra: string;
    /** The tooltip's own position inside the canvas box (W3-M5). */
    x: number;
    y: number;
  } | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const hoverTipRef = useRef<HTMLDivElement | null>(null);
  const skyClockRef = useRef<{ lst: number; fetchedAt: number } | null>(null);
  const lastGoodRef = useRef<boolean>(false);
  const frozenAtRef = useRef<number | null>(null);
  const scrubModeRef = useRef<boolean>(false);
  scrubModeRef.current = scrubMode;
  const layerCacheRef = useRef<{
    canvas: HTMLCanvasElement | null;
    lst: number;
    size: number;
    flags: string;
    lat: number;
    epoch: number;
    buildMs: number;
    /** Stars in the current cached picture (layer stamps, or the daylight loop). */
    starsDrawn: number;
    starMode: 'layer' | 'separate';
  }>({
    canvas: null,
    lst: Number.NaN,
    size: -1,
    flags: '',
    lat: Number.NaN,
    epoch: Number.NaN,
    buildMs: 0,
    starsDrawn: 0,
    starMode: 'layer',
  });

  const loadSky = async () => {
    setLoading(true);
    let superseded = false;
    try {
      const sky = await fetchNightSky(observerLat, observerLng);
      skyClockRef.current = {
        lst: sky.observer.local_sidereal_time_deg,
        fetchedAt: performance.now(),
      };
      lastGoodRef.current = true;
      frozenAtRef.current = null;
      setData(sky);
      setLastGoodAt(Date.now());
      setStatus('ok');
      setErrorKind(null);
    } catch (error) {
      // A superseded answer is not a failure: a newer request owns the dome
      // (and the spinner), so it must not clear that request's loading state.
      if (error instanceof NightSkyError && error.kind === 'stale') {
        superseded = true;
      } else {
        setErrorKind(error instanceof NightSkyError ? error.kind : 'network');
        if (lastGoodRef.current) {
          // Freeze the catalogue clock where it was when the answer failed.
          frozenAtRef.current = performance.now();
          setStatus('stale');
        } else {
          setStatus('unavailable');
        }
      }
    } finally {
      if (!superseded) setLoading(false);
    }
  };

  useEffect(() => {
    void loadSky();
    const interval = setInterval(() => {
      if (!document.hidden && !scrubModeRef.current) void loadSky();
    }, 60000);
    const onVisibilityChange = () => {
      if (!document.hidden && !scrubModeRef.current) void loadSky();
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      // A place change or unmount must not leave the old request running.
      cancelNightSkyRequest();
    };
  }, [observerLat, observerLng]);

  // Scrubbing stops the live poll; leaving scrub resumes it immediately.
  const wasScrubbingRef = useRef<boolean>(false);
  useEffect(() => {
    if (scrubMode) {
      wasScrubbingRef.current = true;
      return;
    }
    if (!wasScrubbingRef.current) return;
    wasScrubbingRef.current = false;
    void loadSky();
  }, [scrubMode]);

  // "Fresh enough": two poll periods after the last good answer, mark stale so
  // the catalogue clock stops pretending the sky is current.
  useEffect(() => {
    if (scrubMode || status !== 'ok' || lastGoodAt === null) return;
    const remaining = Math.max(0, lastGoodAt + SKY_FRESH_MS - Date.now());
    const timeout = window.setTimeout(() => setStatus('stale'), remaining);
    return () => window.clearTimeout(timeout);
  }, [scrubMode, status, lastGoodAt]);

  useEffect(() => {
    let live = true;
    // The two lazy chunks load independently: one failure must not take the
    // other layer (or the computed ecliptic) down with it.
    loadStars()
      .then((stars) => {
        if (!live) return;
        setCatalogue(stars);
        setCatalogueStatus('ready');
      })
      .catch(() => {
        if (!live) return;
        setCatalogueStatus('unavailable');
      });
    loadConstellationLines()
      .then((lines) => {
        if (!live) return;
        setFigureLines(lines);
        setFiguresStatus('ready');
      })
      .catch(() => {
        if (!live) return;
        setFiguresStatus('unavailable');
      });
    return () => {
      live = false;
    };
  }, []);

  const scrubSacredInputs = useMemo(
    () =>
      (data?.sacred_stars ?? []).map((star) => ({
        id: star.id,
        ra_j2000: star.ra_j2000,
        dec_j2000: star.dec_j2000,
      })),
    [data],
  );

  // The scrubbed sky comes from one decoded series; the fallback (series
  // unavailable) still rotates the catalogue with local mean sidereal time.
  const scrubbed: ScrubbedSky | null = useMemo(() => {
    if (!scrubMode || scrubAtMs === null || series === null) return null;
    try {
      return skyAtInstant(series, scrubAtMs, observerLat, observerLng, scrubSacredInputs);
    } catch {
      // The held window may not cover a brand-new instant yet (the shared store
      // has already started the re-centred request): fall back to local
      // sidereal stars and never crash.
      return null;
    }
  }, [series, scrubMode, scrubAtMs, observerLat, observerLng, scrubSacredInputs]);

  // One banner truth: computed only when both a series and its interpolation exist.
  // A retained window that still covers the instant is usable: draw it and
  // qualify the failed refresh below, rather than claiming nothing is drawn.
  const scrubBannerState: 'idle' | 'loading' | 'ready' | 'unavailable' = !scrubMode
    ? 'idle'
    : scrubbed !== null
      ? 'ready'
      : seriesStatus === 'unavailable'
        ? 'unavailable'
        : 'loading';
  const scrubRetainedFailure = scrubMode && scrubbed !== null && seriesStatus === 'unavailable';
  const seriesAgeMinutes =
    seriesFetchedAtMs === null
      ? null
      : Math.max(0, Math.round((Date.now() - seriesFetchedAtMs) / 60_000));

  // One Sun altitude for both modes: the live payload's Sun entry, or the
  // scrub layer's Sun position. No Sun (series unavailable) -> night rendering.
  const sunAltDeg = scrubMode
    ? (scrubbed?.positions.sun?.alt ?? -90)
    : (data?.planets.find((planet) => planet.id === 'sun')?.altitude ?? -90);
  const daylightActive = sunAltDeg > NIGHT_SUN_ALT_DEG;
  const onSeeThroughChange = (next: boolean) => {
    setSeeThrough(next);
    try {
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(SEE_THROUGH_KEY, next ? '1' : '0');
      }
    } catch {
      /* convenience only; the page works without persistence */
    }
  };


  const scrubFallback = useMemo(() => {
    if (!scrubMode || scrubAtMs === null || scrubbed !== null) return null;
    const jd = julianDay(new Date(scrubAtMs));
    const lst = localScrubLst(scrubAtMs, observerLng);
    const sacred = sacredHorizontal(scrubSacredInputs, lst, observerLat, jd);
    return { jd, lst, sacred: sacred.positions, sacredMissing: sacred.missing };
  }, [scrubMode, scrubAtMs, scrubbed, observerLng, observerLat, scrubSacredInputs]);

  const planetMarks = useMemo<PlanetMark[]>(() => {
    if (!data) return [];
    const marks: PlanetMark[] = [];
    for (const planet of data.planets) {
      if (scrubMode) {
        const position = scrubbed?.positions[planet.id];
        if (!position || position.alt <= 0) continue;
        marks.push({ planet, alt: position.alt, az: position.az });
      } else if (planet.visible) {
        marks.push({ planet, alt: planet.altitude, az: planet.azimuth });
      }
    }
    return marks;
  }, [data, scrubMode, scrubbed]);

  const sacredMarks = useMemo<SacredMark[]>(() => {
    if (!data) return [];
    const metadata = new Map(data.sacred_stars.map((star) => [star.id, star]));
    const positions = scrubMode
      ? (scrubbed?.sacred ?? scrubFallback?.sacred ?? [])
      : data.sacred_stars
          .filter((star) => star.visible)
          .map((star) => ({ id: star.id, alt: star.altitude, az: star.azimuth }));
    const marks: SacredMark[] = [];
    for (const position of positions) {
      if (scrubMode && position.alt <= 0) continue;
      const star = metadata.get(position.id);
      if (!star) continue;
      marks.push({ star, alt: position.alt, az: position.az });
    }
    return marks;
  }, [data, scrubMode, scrubbed, scrubFallback]);

  const sacredMissing = scrubbed?.sacredMissing ?? scrubFallback?.sacredMissing ?? false;

  // Canvas drawing loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId = 0;
    let lastDrawMs = Number.NEGATIVE_INFINITY;
    const twinkles =
      !reducedMotion &&
      showStars &&
      sacredMarks.some(
        (mark) => daylightStarAlpha(mark.star.magnitude, sunAltDeg, seeThrough) > 0,
      );
    const drawIntervalMs = twinkles ? TWINKLE_FRAME_MS : STILL_REDRAW_MS;
    const separateStars = daylightActive && showCatalogue && catalogue !== null;
    const figureAlpha = daylightStarAlpha(2, sunAltDeg, seeThrough);
    // In daylight the layer never stamps stars (no flash before the catalogue
    // resolves); the per-star loop draws them once the catalogue is here.
    const layerShowCatalogue = showCatalogue && !daylightActive;

    const render = (time: number) => {
      const frameStarted = performance.now();
      const dpr = window.devicePixelRatio || 1;
      const size = Math.max(1, Math.round(Math.min(canvas.clientWidth || 500, canvas.clientHeight || 500)));
      const backing = Math.round(size * dpr);
      if (canvas.width !== backing || canvas.height !== backing) {
        canvas.width = backing;
        canvas.height = backing;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, size, size);

      const cx = size / 2;
      const cy = size / 2;
      const radius = size * 0.42;

      // Sky disc: exactly today's night fill below -18°, twilight indigo, day blue.
      const palette = skyBackground(sunAltDeg);
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
      grad.addColorStop(0, palette.core);
      grad.addColorStop(0.7, palette.mid);
      grad.addColorStop(1, palette.edge);
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Concentric Altitude Rings (30°, 60°)
      [30, 60].forEach((deg) => {
        const r = ((90 - deg) / 90) * radius;
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.12)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = 'rgba(148, 163, 184, 0.35)';
        ctx.font = '9px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`${deg}°`, cx, cy - r + 11);
      });
      ctx.setLineDash([]);

      // Horizon Circle
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.4)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.stroke();

      // Cardinal Labels (N at Top, E at Left, S at Bottom, W at Right)
      const cardinals = [
        { label: 'N', az: 0 },
        { label: 'E', az: 90 },
        { label: 'S', az: 180 },
        { label: 'W', az: 270 },
      ];
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      cardinals.forEach(({ label, az }) => {
        const radAz = (az * Math.PI) / 180;
        const lx = cx - (radius + 14) * Math.sin(radAz);
        const ly = cy - (radius + 14) * Math.cos(radAz);
        ctx.fillStyle = label === 'N' ? '#a78bfa' : 'rgba(226, 232, 240, 0.6)';
        ctx.fillText(label, lx, ly);
      });

      // Zenith crosshair
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.3)';
      ctx.beginPath();
      ctx.moveTo(cx - 5, cy);
      ctx.lineTo(cx + 5, cy);
      ctx.moveTo(cx, cy - 5);
      ctx.lineTo(cx, cy + 5);
      ctx.stroke();

      // Helper to project Alt/Az to canvas (x, y)
      const project = (alt: number, az: number): [number, number] => {
        const r = ((90 - Math.max(0, alt)) / 90) * radius;
        const radAz = (az * Math.PI) / 180;
        const px = cx - r * Math.sin(radAz);
        const py = cy - r * Math.cos(radAz);
        return [px, py];
      };

      // Catalogue, figures, and ecliptic share one offscreen canvas. The
      // animation loop only blits it. Rebuild when the observer latitude,
      // the epoch, the size, the layer flags or the sidereal time (>= 0.02°)
      // changed. The ecliptic is computed independently of the two lazy
      // chunks, so a failed chunk cannot take it down.
      const anyLayer = showCatalogue || showFigures || showEcliptic;
      let starsDrawnNow = 0;
      const starModeNow: 'layer' | 'separate' = separateStars ? 'separate' : 'layer';
      if (
        anyLayer &&
        typeof ctx.drawImage === 'function' &&
        typeof ctx.putImageData === 'function'
      ) {
        const flags = `${layerShowCatalogue ? 1 : 0}${showFigures ? 1 : 0}${showEcliptic ? 1 : 0}|${Math.round(figureAlpha * 20)}|${
          separateStars ? `d${Math.round(sunAltDeg * 4)}${seeThrough ? 'x' : 'n'}` : 'l'
        }`;
        let lst: number;
        let jd: number;
        let epochDay: number;
        let layerLat: number;
        if (scrubMode && scrubAtMs !== null) {
          // No payload in scrub mode: the series is computed for the shown
          // store/props place.
          layerLat = observerLat;
          if (scrubbed !== null) {
            lst = scrubbed.lst;
            jd = scrubbed.jd;
          } else {
            // The series is loading/unavailable: the catalogue still rotates
            // from local mean sidereal time (see localScrubLst).
            lst = localScrubLst(scrubAtMs, observerLng);
            jd = julianDay(new Date(scrubAtMs));
          }
          epochDay = Math.floor(scrubAtMs / 86400000);
        } else {
          // Live mode: everything payload-derived uses the payload's own
          // place. The requested observer may have moved on while the previous
          // answer is still on screen; drawing the new latitude with the old
          // LST/planets would be a sky that belongs to no place.
          layerLat = data.observer.latitude;
          const clock = skyClockRef.current;
          const nowMs = performance.now();
          // Advance with the wall clock only while the answer is fresh and no
          // later request has failed; otherwise the layer must stop drifting.
          const capMs = Math.min(
            nowMs,
            frozenAtRef.current ?? nowMs,
            clock === null ? nowMs : clock.fetchedAt + SKY_FRESH_MS,
          );
          const elapsedSec = clock === null ? 0 : Math.max(0, capMs - clock.fetchedAt) / 1000;
          lst = wrap360(
            (clock === null ? data.observer.local_sidereal_time_deg : clock.lst) +
              SIDEREAL_DEG_PER_SEC * elapsedSec,
          );
          const parsedMs = Date.parse(data.timestamp_utc);
          const validMs = Number.isFinite(parsedMs);
          jd = validMs ? julianDay(new Date(parsedMs)) : julianDay(new Date());
          // Whole-day epoch: precession moves ~50 arcsec/year, finer than the
          // catalogue, but a date change must still rebuild the layer.
          epochDay = Math.floor((validMs ? parsedMs : Date.now()) / 86400000);
        }
        const cache = layerCacheRef.current;
        const stale =
          cache.canvas === null ||
          cache.size !== size ||
          cache.flags !== flags ||
          cache.lat !== layerLat ||
          cache.epoch !== epochDay ||
          Number.isNaN(cache.lst) ||
          angleDelta(lst, cache.lst) >= LAYER_LST_STEP_DEG;
        if (stale) {
          const started = performance.now();
          const built = buildSkyLayer({
            stars: catalogue ?? [],
            lines: figureLines ?? EMPTY_LINES,
            lstDeg: lst,
            latDeg: layerLat,
            jd,
            size,
            showCatalogue: layerShowCatalogue,
            showFigures,
            showEcliptic,
          });
          if (built.stars.length === size * size * 4 && typeof ImageData === 'function') {
            if (cache.canvas === null) cache.canvas = document.createElement('canvas');
            if (cache.canvas.width !== size || cache.canvas.height !== size) {
              cache.canvas.width = size;
              cache.canvas.height = size;
            }
            const off = cache.canvas.getContext('2d');
            if (off && typeof off.putImageData === 'function') {
              off.putImageData(new ImageData(built.stars, size, size), 0, 0);
              // Daylight stars live in the cached canvas too, so a frame costs
              // one drawImage: draw them only when the cache rebuilds. Skip the
              // projection entirely for stars whose daylight alpha is 0.
              let builtStarsDrawn = 0;
              if (separateStars && catalogue !== null) {
                for (let i = 0; i < catalogue.length; i += 1) {
                  const star = catalogue[i];
                  const alpha = daylightStarAlpha(star.v, sunAltDeg, seeThrough);
                  if (!(alpha > 0)) continue;
                  const ofDate = precessJ2000(star.ra, star.dec, jd);
                  // Same place as the layer/planets (the payload's place in live mode).
                  const horizontal = equatorialToHorizontal(ofDate.ra, ofDate.dec, lst, layerLat);
                  if (!(horizontal.alt > 0)) continue;
                  const point = domePoint(horizontal.alt, horizontal.az, radius, cx, cy);
                  const rgb = starRgb(star.bv);
                  off.globalAlpha = alpha;
                  off.fillStyle = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
                  off.beginPath();
                  off.arc(point.x, point.y, Math.max(0.5, starRadiusPx(star.v)), 0, Math.PI * 2);
                  off.fill();
                  builtStarsDrawn += 1;
                }
                off.globalAlpha = 1;
              }
              cache.starsDrawn = separateStars
                ? builtStarsDrawn
                : layerShowCatalogue
                  ? (catalogue?.length ?? 0)
                  : 0;
              cache.starMode = separateStars ? 'separate' : 'layer';
              // Figures and the ecliptic fade with the sky; at 0 they are not
              // stroked at all (daylight with the x-ray toggle off).
              if (figureAlpha > 0) {
                off.globalAlpha = figureAlpha;
                off.beginPath();
                for (let i = 0; i < built.figures.length; i += 1) {
                  const seg = built.figures[i];
                  off.moveTo(seg.x1, seg.y1);
                  off.lineTo(seg.x2, seg.y2);
                }
                off.strokeStyle = 'rgba(148, 163, 184, 0.35)';
                off.lineWidth = 1;
                off.setLineDash([]);
                off.stroke();
                off.beginPath();
                for (let i = 0; i < built.ecliptic.length; i += 1) {
                  const seg = built.ecliptic[i];
                  off.moveTo(seg.x1, seg.y1);
                  off.lineTo(seg.x2, seg.y2);
                }
                off.strokeStyle = 'rgba(251, 191, 36, 0.75)';
                off.lineWidth = 1;
                off.setLineDash([6, 5]);
                off.stroke();
                off.setLineDash([]);
                off.globalAlpha = 1;
              }
              cache.lst = lst;
              cache.size = size;
              cache.flags = flags;
              cache.lat = layerLat;
              cache.epoch = epochDay;
              cache.buildMs = performance.now() - started;
            }
          }
        }
        starsDrawnNow = cache.starsDrawn;
        if (cache.canvas !== null) ctx.drawImage(cache.canvas, 0, 0);
        if (canvas.dataset) canvas.dataset.layerMs = cache.buildMs.toFixed(3);
      }

      // Draw Sacred Stars
      if (showStars) {
        sacredMarks.forEach((mark, idx) => {
          const s = mark.star;
          const daylight = daylightStarAlpha(s.magnitude, sunAltDeg, seeThrough);
          if (!(daylight > 0)) return;
          const [sx, sy] = project(mark.alt, mark.az);
          const twinkle =
            (reducedMotion
              ? TWINKLE_REST_ALPHA
              : 0.8 + 0.2 * Math.sin(time * 0.003 + idx * 1.5)) * daylight;
          const dotSize = Math.max(2, 4.5 - s.magnitude * 0.8);

          // Star glow
          ctx.beginPath();
          ctx.arc(sx, sy, dotSize * 2, 0, Math.PI * 2);
          ctx.fillStyle = s.color;
          ctx.globalAlpha = 0.15 * twinkle;
          ctx.fill();

          // Star core
          ctx.beginPath();
          ctx.arc(sx, sy, dotSize, 0, Math.PI * 2);
          ctx.fillStyle = s.color;
          ctx.globalAlpha = twinkle;
          ctx.fill();
          ctx.globalAlpha = 1.0;

          // Star label
          ctx.font = '9px sans-serif';
          ctx.textAlign = 'left';
          ctx.fillStyle = 'rgba(226, 232, 240, 0.7)';
          ctx.fillText(s.name.split(' ')[0], sx + 6, sy - 2);
        });
      }

      // Draw Planets
      if (showPlanets) {
        planetMarks.forEach((mark) => {
          const p = mark.planet;
          const [px, py] = project(mark.alt, mark.az);

          // Planet glow aura
          ctx.beginPath();
          ctx.arc(px, py, 11, 0, Math.PI * 2);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = 0.2;
          ctx.fill();

          // Planet glyph circle
          ctx.beginPath();
          ctx.arc(px, py, 7.5, 0, Math.PI * 2);
          ctx.fillStyle = '#0f172a';
          ctx.globalAlpha = 0.85;
          ctx.fill();
          ctx.strokeStyle = p.color;
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Glyph character
          ctx.globalAlpha = 1.0;
          ctx.fillStyle = p.color;
          ctx.font = '11px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(p.glyph, px, py);

          // Name & Sign tag (the sign is as-of-now, so it is omitted when scrubbed)
          ctx.font = '9px sans-serif';
          ctx.textAlign = 'left';
          ctx.fillStyle = p.color;
          ctx.fillText(scrubMode ? p.name : `${p.name} ${p.sign_glyph}`, px + 10, py - 4);
        });
      }

      if (canvas.dataset) {
        canvas.dataset.frameMs = (performance.now() - frameStarted).toFixed(3);
        canvas.dataset.scrub = scrubMode ? 'true' : 'false';
        canvas.dataset.scrubStatus = scrubBannerState;
        canvas.dataset.scrubPlanets = String(planetMarks.length);
        canvas.dataset.scrubSacred = String(sacredMarks.length);
        canvas.dataset.daylight = daylightActive ? (seeThrough ? 'xray' : 'hidden') : 'night';
        canvas.dataset.starMode = starModeNow;
        canvas.dataset.starsDrawn = String(starsDrawnNow);
        canvas.dataset.figureAlpha = figureAlpha.toFixed(2);
      }
    };

    // The decorative twinkle runs at <= 30 fps; a still sky redraws at 1 Hz.
    // rAF is used for the normal path because the browser pauses it while the
    // tab is hidden; a `visibilitychange` redraw makes the sky current on return.
    const draw = (time: number) => {
      render(time);
      lastDrawMs = time;
    };
    const onVisibilityChange = () => {
      if (document.hidden) return;
      draw(performance.now());
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    if (reducedMotion) {
      draw(performance.now());
      const redrawId = window.setInterval(() => {
        if (!document.hidden) draw(performance.now());
      }, STILL_REDRAW_MS);
      return () => {
        window.clearInterval(redrawId);
        document.removeEventListener('visibilitychange', onVisibilityChange);
      };
    }

    draw(0);
    const frame = (time: number) => {
      animId = window.requestAnimationFrame(frame);
      if (document.hidden) return;
      if (time - lastDrawMs >= drawIntervalMs) draw(time);
    };
    animId = window.requestAnimationFrame(frame);
    return () => {
      window.cancelAnimationFrame(animId);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [
    data,
    showStars,
    showPlanets,
    showCatalogue,
    showFigures,
    showEcliptic,
    catalogue,
    figureLines,
    reducedMotion,
    status,
    sunAltDeg,
    seeThrough,
    daylightActive,
    scrubMode,
    scrubAtMs,
    scrubBannerState,
    scrubbed,
    scrubFallback,
    planetMarks,
    sacredMarks,
  ]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const size = Math.min(canvas.clientWidth || 500, canvas.clientHeight || 500);
    const cx = size / 2;
    const cy = size / 2;
    const radius = size * 0.42;

    const project = (alt: number, az: number): [number, number] => {
      const r = ((90 - Math.max(0, alt)) / 90) * radius;
      const radAz = (az * Math.PI) / 180;
      return [cx - r * Math.sin(radAz), cy - r * Math.cos(radAz)];
    };

    // W3-M5: the tooltip keeps its own width and stays inside the canvas. It
    // used to be absolutely positioned at the cursor with no width of its own,
    // so the browser squeezed it into a ~74 px column (one word per line) and
    // it could hang 26 px outside the card at 420 px. It flips to the other
    // side of the cursor when it does not fit, then clamps.
    const tipW = hoverTipRef.current?.offsetWidth ?? 240;
    const tipH = hoverTipRef.current?.offsetHeight ?? 110;
    const canvasW = canvas.clientWidth || 0;
    const canvasH = canvas.clientHeight || 0;
    let tipX = mx + 10;
    if (tipX + tipW + 8 > canvasW) tipX = mx - tipW - 10;
    tipX = Math.max(4, Math.min(tipX, Math.max(4, canvasW - tipW - 4)));
    const tipY = Math.max(4, Math.min(my - 45, Math.max(4, canvasH - tipH - 4)));

    // Check planets first
    for (const mark of planetMarks) {
      const p = mark.planet;
      const [px, py] = project(mark.alt, mark.az);
      if (Math.hypot(mx - px, my - py) < 14) {
        setHoveredObject({
          name: scrubMode
            ? `${p.name} ${p.glyph}`
            : `${p.name} ${p.glyph} in ${p.sign} ${p.sign_glyph}`,
          sub: `Alt: ${formatDeg(mark.alt)}° · Az: ${formatDeg(mark.az)}°`,
          alt: mark.alt,
          az: mark.az,
          extra: p.esoteric_quality,
          x: tipX,
          y: tipY,
        });
        return;
      }
    }

    // Check stars
    for (const mark of sacredMarks) {
      const s = mark.star;
      const [sx, sy] = project(mark.alt, mark.az);
      if (Math.hypot(mx - sx, my - sy) < 12) {
        setHoveredObject({
          name: `${s.name}`,
          sub: `${s.nakshatra} · Alt: ${formatDeg(mark.alt)}° · Az: ${formatDeg(mark.az)}°`,
          alt: mark.alt,
          az: mark.az,
          extra: s.quality,
          x: tipX,
          y: tipY,
        });
        return;
      }
    }

    setHoveredObject(null);
  };

  const failedLayers: string[] = [];
  if (catalogueStatus === 'unavailable') failedLayers.push('stars');
  if (figuresStatus === 'unavailable') failedLayers.push('figures');
  const skyLayersToken =
    failedLayers.length > 0
      ? `${failedLayers.join('+')}-unavailable`
      : catalogueStatus === 'ready' && figuresStatus === 'ready'
        ? 'ready'
        : 'pending';

  // The chip list always shows the sacred stars above the horizon; the heading
  // says honestly whether the daylight layer is hiding/dimming them.
  const vedicHeading = !daylightActive
    ? 'Visible Vedic Nakshatras Overhead:'
    : seeThrough
      ? 'Vedic stars above the horizon (drawn faintly):'
      : sunAltDeg >= 0
        ? 'Vedic stars above the horizon (hidden by daylight):'
        : 'Vedic stars above the horizon (fainter ones hidden by the twilight sky):';

  const staleAgeSeconds =
    lastGoodAt === null ? null : Math.max(0, Math.round((Date.now() - lastGoodAt) / 1000));
  const scrubOffset = scrubAtIso === null ? null : formatOffset(offsetMinutes(scrubAtIso, Date.now()));
  const payloadIsOtherPlace =
    !scrubMode &&
    data !== null &&
    (Math.abs(data.observer.latitude - observerLat) > 1e-6 ||
      Math.abs(data.observer.longitude - observerLng) > 1e-6);

  return (
    <Card
      data-testid="celestial-sky-dome-card"
      className={`border border-purple-500/20 bg-slate-950/60 backdrop-blur-md rounded-2xl ${className}`}
      title={
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/*
            The title wraps instead of being cut (W3-M5): AntD's head title is
            `white-space: nowrap; overflow: hidden`, so below ~460 px the
            heading used to be clipped mid-word ("Celestial Night-Sky Do") by
            the Refresh button. The heading may wrap and the button may drop to
            the next line, so the whole title is always readable.
          */}
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <Compass className="w-5 h-5 shrink-0 text-purple-400" />
            <span className="whitespace-normal text-purple-200 font-serif text-lg tracking-wide">
              Celestial Night-Sky Dome
            </span>
            <Tag color="purple">Horizon Alt/Az</Tag>
          </div>
          {data && !scrubMode && (
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono min-w-0">
              <span className="whitespace-nowrap">LST: {data.observer.local_sidereal_time_hms}</span>
              <span className="flex items-center gap-1 text-amber-300 whitespace-nowrap">
                <Moon className="w-3.5 h-3.5" />
                {data.moon.phase_name} ({data.moon.illumination}%)
              </span>
            </div>
          )}
        </div>
      }
      extra={
        <Space orientation="horizontal" size="small">
          <Button
            size="small"
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
            onClick={() => void loadSky()}
          >
            Refresh
          </Button>
        </Space>
      }
    >
      {scrubMode && scrubAtMs !== null && (
        <div
          data-testid="sky-scrub-banner"
          className="mb-4 rounded-lg border border-sky-500/30 bg-sky-950/20 px-3 py-2 text-[11px] leading-snug text-sky-200"
        >
          <div>
            Scrubbed: {new Date(scrubAtMs).toISOString()} ({scrubOffset} from now).{' '}
            {scrubBannerState === 'ready'
              ? 'Sun, Moon, planets, stars: computed for that instant.'
              : scrubBannerState === 'unavailable'
                ? 'Stars: computed for that instant; planets not drawn: no series for this instant.'
                : 'Stars: computed for that instant; loading the series for the Sun, Moon and planets…'}{' '}
            Moon phase, zodiac signs and sacred-star notes: as of now.
          </div>
          {scrubRetainedFailure && (
            <div data-testid="sky-scrub-retained" className="mt-1 text-amber-300">
              Showing the series fetched {seriesAgeMinutes ?? '?'} min ago; refresh failed:{' '}
              {seriesError ?? reasonLabel(seriesErrorKind)}.
            </div>
          )}
          {scrubBannerState === 'loading' && (
            <div data-testid="sky-scrub-loading" className="mt-1 text-sky-300/80">
              Loading the 48 h time series…
            </div>
          )}
          {scrubBannerState === 'unavailable' && (
            <div data-testid="sky-scrub-unavailable" data-reason={seriesErrorKind ?? 'http'} className="mt-1 text-amber-300">
              Time series unavailable ({seriesError ?? reasonLabel(seriesErrorKind)}): planets are
              not drawn; stars use local sidereal time.
            </div>
          )}

          {sacredMissing && (
            <div data-testid="sky-scrub-sacred-unavailable" className="mt-1 text-amber-300">
              Sacred stars have no J2000 coordinates yet, so they are not drawn while scrubbing.
            </div>
          )}
        </div>
      )}
      {!data ? (
        status === 'unavailable' ? (
          <div
            data-testid="sky-unavailable"
            data-reason={errorKind ?? 'unknown'}
            className="rounded-xl border border-amber-500/30 bg-amber-950/20 px-4 py-6 text-center"
          >
            <div className="text-sm font-medium text-amber-200">Night sky unavailable</div>
            <div data-testid="sky-unavailable-reason" className="mt-1 text-xs text-amber-200/80">
              {reasonLabel(errorKind)}
            </div>
            <p className="mt-3 text-[11px] text-slate-400">
              No positions are shown rather than a blank or invented sky. The next refresh will try
              again.
            </p>
          </div>
        ) : (
          <div data-testid="sky-loading" className="rounded-xl border border-slate-800 px-4 py-6 text-center text-xs text-slate-400">
            Loading the night sky…
          </div>
        )
      ) : (
        <>
          {daylightActive && (
            <div
              data-testid="sky-daylight-caption"
              className="mb-4 rounded-lg border border-amber-500/30 bg-amber-950/15 px-3 py-2 text-[11px] text-amber-200"
            >
              {seeThrough
                ? 'Daylight x-ray: stars drawn faintly.'
                : sunAltDeg >= 0
                  ? `Stars hidden: the Sun is ${formatDeg(sunAltDeg)}° above the horizon.`
                  : `Twilight: fainter stars are hidden (the Sun is ${formatDeg(-sunAltDeg)}° below the horizon).`}
            </div>
          )}
          {payloadIsOtherPlace && status === 'ok' && (
            <div
              data-testid="sky-updating-place"
              className="mb-4 rounded-lg border border-sky-500/30 bg-sky-950/20 px-3 py-2 text-[11px] text-sky-200"
            >
              Updating place… still showing the previous sky until the new answer arrives.
            </div>
          )}
          {status === 'stale' && !scrubMode && (
            <div
              data-testid="sky-stale"
              data-reason={errorKind ?? 'stale'}
              data-other-place={payloadIsOtherPlace ? 'true' : 'false'}
              className="mb-4 rounded-lg border border-amber-500/30 bg-amber-950/20 px-3 py-2 text-[11px] text-amber-200"
            >
              {payloadIsOtherPlace
                ? `Planets and sacred stars are for another place (${data.observer.latitude.toFixed(3)}, ${data.observer.longitude.toFixed(3)}), not the requested one — last good ${staleAgeSeconds ?? '?'} s ago; not current.`
                : `Planets and sacred stars are stale — last good ${staleAgeSeconds ?? '?'} s ago; not current.`}
            </div>
          )}

          {/*
            Canvas and side panel share a WRAPPING flex row, so the layout follows the dome's own width and not the
            viewport's: side by side while the container fits both minimums (canvas 280 px, panel 250 px), stacked
            when it does not. The canvas is capped at 440 px and takes twice the spare room; the panel takes the rest.
            (The previous viewport-width grid gave the panel 133 px inside the Earth & Sky card at 1440 px, 53 px at
            1280 and none at 1100; measured in a real browser, docs/notes/earthsky/wave3/c1/dome-panel.mjs.)
          */}
          <div className="flex flex-wrap items-center gap-6">
        {/* Sky Dome Canvas */}
        <div className="relative mx-auto aspect-square max-w-[440px] flex-[2_1_280px] flex items-center justify-center">
          <canvas
            ref={canvasRef}
            data-testid="celestial-sky-dome-canvas"
            data-sky-layers={skyLayersToken}
            className="w-full h-full cursor-crosshair rounded-full"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoveredObject(null)}
          />

          {/* Interactive Hover Tooltip */}
          {hoveredObject && (
            <div
              ref={hoverTipRef}
              data-testid="sky-hover-tooltip"
              className="pointer-events-none absolute z-20 w-[240px] max-w-full rounded-lg border border-purple-500/30 bg-slate-900/90 p-2.5 shadow-xl text-xs text-slate-200"
              style={{ left: hoveredObject.x, top: hoveredObject.y }}
            >
              <div className="font-semibold text-purple-300">{hoveredObject.name}</div>
              <div className="text-slate-400 font-mono text-[11px]">{hoveredObject.sub}</div>
              <div className="text-amber-200/90 text-[10px] mt-1 border-t border-slate-700/60 pt-1">
                {hoveredObject.extra}
              </div>
            </div>
          )}
        </div>

        {/* Telemetry & Legend Panel */}
        <div
          data-testid="sky-side-panel"
          className="min-w-0 flex-[1_1_250px] space-y-4 overflow-hidden [container-type:inline-size]"
        >
          <div data-testid="sky-visible-header" className="border-b border-slate-800 pb-3">
            <span className="block text-xs uppercase tracking-wider text-slate-400 font-medium">
              Overhead Visibility
            </span>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs [@container(max-width:295px)]:gap-x-3">
              <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                <Switch size="small" checked={showPlanets} onChange={setShowPlanets} />
                <span>Planets ({scrubMode ? planetMarks.length : data?.visible_planets_count || 0})</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                <Switch size="small" checked={showStars} onChange={setShowStars} />
                <span>Vedic Stars ({scrubMode ? sacredMarks.length : data?.visible_stars_count || 0})</span>
              </label>
              <label data-testid="sky-switch-catalogue" className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                <Switch size="small" checked={showCatalogue} onChange={setShowCatalogue} />
                <span>Catalogue</span>
                {catalogueStatus === 'unavailable' && (
                  <span data-testid="sky-catalogue-unavailable" className="text-[10px] text-amber-300">
                    unavailable
                  </span>
                )}
              </label>
              <label data-testid="sky-switch-figures" className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                <Switch size="small" checked={showFigures} onChange={setShowFigures} />
                <span>Figures</span>
                {figuresStatus === 'unavailable' && (
                  <span data-testid="sky-figures-unavailable" className="text-[10px] text-amber-300">
                    unavailable
                  </span>
                )}
              </label>
              <label data-testid="sky-switch-ecliptic" className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                <Switch size="small" checked={showEcliptic} onChange={setShowEcliptic} />
                <span>Ecliptic</span>
              </label>
              <label data-testid="sky-see-through" className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                <Switch
                  size="small"
                  checked={seeThrough}
                  onChange={onSeeThroughChange}
                  aria-label="See through daylight"
                  aria-pressed={seeThrough}
                />
                <span>See through daylight</span>
              </label>
            </div>
          </div>

          {/* Active Visible Planets Grid */}
          <div
            data-testid="sky-planet-grid"
            className="grid grid-cols-[repeat(auto-fill,minmax(min(9rem,max(7.5rem,calc(50%_-_4px)),100%),1fr))] gap-2 min-w-0"
          >
            {planetMarks.map((mark) => {
              const p = mark.planet;
              return (
                <div
                  key={p.id}
                  data-testid="sky-planet-card"
                  className="min-w-0 overflow-hidden rounded-lg border border-slate-800 bg-slate-900/50 p-2 text-xs flex flex-col justify-between"
                >
                  <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-2 gap-y-0.5">
                    <span className="min-w-0 truncate font-medium" style={{ color: p.color }}>
                      {p.name} {p.glyph}
                    </span>
                    <Tag color="default" className="m-0 shrink-0 whitespace-nowrap text-[10px]">
                      Alt {formatDeg(mark.alt)}°
                    </Tag>
                  </div>
                  <div className="mt-1 break-words text-[10px] text-slate-400">
                    {scrubMode ? '' : `${p.sign} ${p.sign_glyph} · `}
                    <span className="whitespace-nowrap">Az {formatDeg(mark.az)}°</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Sacred Stars & Nakshatras */}
          <div>
            <div className="text-xs text-slate-400 mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span data-testid="sky-vedic-heading">{vedicHeading}</span>
            </div>
            <div className="flex min-w-0 flex-wrap gap-1.5">
              {sacredMarks.map((mark) => {
                const s = mark.star;
                return (
                  <Tooltip
                    key={s.id}
                    title={`${s.quality} (Azimuth: ${formatDeg(mark.az)}°, Alt: ${formatDeg(mark.alt)}°)`}
                  >
                    <Tag
                      color="purple"
                      data-testid="sky-sacred-badge"
                      className="max-w-full min-w-0 cursor-help overflow-hidden border border-purple-500/30 px-2 py-0.5 text-xs"
                      style={{ borderColor: s.color }}
                    >
                      <span className="truncate font-semibold" style={{ color: s.color }}>
                        {s.name.split(' ')[0]}
                      </span>{' '}
                      <span className="shrink-0 whitespace-nowrap font-mono text-[10px] opacity-75">
                        +{formatDeg(mark.alt)}°
                      </span>
                    </Tag>
                  </Tooltip>
                );
              })}
            </div>
          </div>
        </div>
      </div>
        </>
      )}
      <div className="mt-4 space-y-1 text-[10px] leading-snug text-slate-500" data-testid="sky-layer-footer">
        <div className="flex flex-wrap items-center gap-2">
          <span>Star and planet positions</span>
          <ProvenanceTag kind="computed" />
          <span>Ecliptic line</span>
          <ProvenanceTag kind="computed" />
          <span>Constellation figures</span>
          <ProvenanceTag kind="decorative" />
          <span>Twinkle</span>
          <ProvenanceTag kind="decorative" />
        </div>
        <p>
          BSC5 via CDS VizieR · IAU star names CC BY · figures: IAU and Sky & Telescope (Sinnott and Fienberg), CC BY 3.0, via d3-celestial BSD-3
        </p>
        <p>precession only; proper motion, nutation and aberration ignored</p>
        <p>
          Sun, Moon and planets are geocentric (no parallax; the Moon can differ by up to about 1
          degree from where it appears at your place).
        </p>
        {sacredMissing && (
          <p data-testid="sky-scrub-sacred-footer">sacred stars unavailable while scrubbing</p>
        )}
      </div>
    </Card>
  );
}
