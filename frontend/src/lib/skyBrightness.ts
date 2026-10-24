/**
 * Earth & Sky wave 4 — daytime sky brightness (pure; no DOM, no randomness).
 *
 * The anchors are an APPROXIMATION from standard twilight sightings (astronomical
 * -18°, nautical -12°, civil -6°), not a radiative-transfer model: the eye's
 * limiting magnitude falls roughly linearly through twilight and reaches "no
 * naked-eye stars" shortly after sunrise. They are continuous so the sky never
 * pops as the Sun moves.
 *
 * `skyBackground` keeps the current night fill exactly at and below -18° and
 * moves through indigo/twilight to a desaturated day blue by +10°.
 *
 * W5-B: `limitingMagnitude` and `starAlpha` take an OPTIONAL last argument, the Moon
 * (`moonlight.ts`). A Moon above the horizon lowers the limit by `moonlightPenaltyMag`,
 * scaled by how dark the Sun-limited sky still is. Without the argument, or with the
 * Moon at or below the horizon (or new), every result is byte-identical to before.
 */
import { moonlightPenaltyMag, type MoonLight } from './moonlight';


/** At and below this Sun altitude the sky is astronomical night (today's dome). */
export const NIGHT_SUN_ALT_DEG = -18;
/** At and above this Sun altitude the day-blue disc is fully in. */
export const DAY_SUN_ALT_DEG = 10;
/** Width of the fading band at the limiting magnitude (same 0.5 as sky.ts). */
const FADE_BAND_MAG = 0.5;

/**
 * Sun altitude -> naked-eye limiting magnitude (the magnitude at which a star's
 * alpha reaches 0). Between anchors the value is linear; outside them clamped.
 * Approximate sightings: astronomical night sees the whole V<=6.5 catalogue,
 * nautical twilight ~4.0, civil ~2.0, -3° ~-0.5 (only Sirius-class stars),
 * 0° ~-2.0 (none), +10° ~-4.0.
 */
const LIMIT_ANCHORS: readonly (readonly [number, number])[] = [
  [-18, 6.5],
  [-12, 4],
  [-6, 2],
  [-3, -0.5],
  [0, -2],
  [10, -4],
];

/** The Sun-limited limit at astronomical night (the whole catalogue), and where moonlight stops adding to the glow. */
const NIGHT_LIMIT_MAG = 6.5;
const MOON_FADES_AT_LIMIT_MAG = 2;

/**
 * The naked-eye limiting magnitude for a Sun altitude and, optionally, the Moon.
 *
 * Moonlight adds to the sky's glow, so it matters most in a truly dark sky and not at all once twilight has already
 * brightened it: the Moon's penalty is multiplied by how dark the Sun-limited sky is, 1 at a limit of 6.5 (Sun at or
 * below -18°) falling linearly to 0 at a limit of 2 (civil twilight, Sun at -6°, and brighter). The result is never
 * brighter than the Moonless one, and a Moon at or below the horizon returns the Moonless value unchanged.
 */
export function limitingMagnitude(sunAltDeg: number, moon?: MoonLight): number {
  const sunLimit = sunLimitingMagnitude(sunAltDeg);
  if (moon === undefined) return sunLimit;
  const penalty = moonlightPenaltyMag(moon.altDeg, moon.illuminatedFraction);
  if (penalty <= 0) return sunLimit;
  const darkness = clamp01((sunLimit - MOON_FADES_AT_LIMIT_MAG) / (NIGHT_LIMIT_MAG - MOON_FADES_AT_LIMIT_MAG));
  return sunLimit - penalty * darkness;
}

function sunLimitingMagnitude(sunAltDeg: number): number {
  if (!Number.isFinite(sunAltDeg)) return 6.5;
  if (sunAltDeg <= NIGHT_SUN_ALT_DEG) return 6.5;
  if (sunAltDeg >= DAY_SUN_ALT_DEG) return -4;
  for (let index = 1; index < LIMIT_ANCHORS.length; index += 1) {
    const [altHi, limitHi] = LIMIT_ANCHORS[index];
    if (sunAltDeg <= altHi) {
      const [altLo, limitLo] = LIMIT_ANCHORS[index - 1];
      const t = (sunAltDeg - altLo) / (altHi - altLo);
      return limitLo + (limitHi - limitLo) * t;
    }
  }
  return -4;
}

/**
 * The alpha of a star of `magnitude` for a given Sun altitude.
 *
 * Naked-eye view (`seeThrough = false`): 1 for stars well inside the limit,
 * fading linearly to 0 at the limiting magnitude (the same 0.5-mag band sky.ts
 * uses, so astronomical night is exactly today's rendering).
 *
 * "See through daylight" (`seeThrough = true`): at least a faint floor, brighter
 * for brighter stars (0.35 at Sirius-class, 0.12 at the catalogue edge), but
 * never dimmer than the real alpha when the real alpha is higher. The floor does not
 * depend on the Moon: the x-ray view shows the stars the glow has hidden.
 *
 * `moon` (W5-B, optional): moonlight lowers the limit as `limitingMagnitude` describes.
 */
export function starAlpha(
  magnitude: number,
  sunAltDeg: number,
  seeThrough = false,
  moon?: MoonLight,
): number {
  if (!Number.isFinite(magnitude)) return 0;
  const normal = clamp01((limitingMagnitude(sunAltDeg, moon) - magnitude) / FADE_BAND_MAG);
  if (!seeThrough) return normal;
  const floor = 0.12 + 0.23 * clamp01((6.5 - magnitude) / 8);
  return Math.max(normal, floor);
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

export interface SkyPalette {
  /** Radial-gradient centre. */
  core: string;
  /** Radial-gradient middle stop. */
  mid: string;
  /** Radial-gradient outer stop (disc edge). */
  edge: string;
}

/** Today's dark dome fill; returned byte-for-byte at astronomical night. */
const NIGHT_PALETTE: SkyPalette = { core: '#0f172a', mid: '#090d16', edge: '#020617' };
/** Calm, desaturated day blue that still belongs in the dark UI. */
const DAY_PALETTE: SkyPalette = { core: '#3c5573', mid: '#314a66', edge: '#263c52' };

const PALETTE_ANCHORS: readonly (readonly [number, SkyPalette])[] = [
  [-18, NIGHT_PALETTE],
  [-12, { core: '#141a38', mid: '#0d1229', edge: '#070b1a' }],
  [-6, { core: '#1d2447', mid: '#151b36', edge: '#0c1124' }],
  [0, { core: '#2c3a5c', mid: '#223048', edge: '#172134' }],
  [10, DAY_PALETTE],
];

/** The three radial-gradient stops for the dome disc at this Sun altitude. */
export function skyBackground(sunAltDeg: number): SkyPalette {
  if (!Number.isFinite(sunAltDeg) || sunAltDeg <= NIGHT_SUN_ALT_DEG) return NIGHT_PALETTE;
  if (sunAltDeg >= DAY_SUN_ALT_DEG) return DAY_PALETTE;
  for (let index = 1; index < PALETTE_ANCHORS.length; index += 1) {
    const [altHi, hi] = PALETTE_ANCHORS[index];
    if (sunAltDeg <= altHi) {
      const [altLo, lo] = PALETTE_ANCHORS[index - 1];
      const t = (sunAltDeg - altLo) / (altHi - altLo);
      return {
        core: mixHex(lo.core, hi.core, t),
        mid: mixHex(lo.mid, hi.mid, t),
        edge: mixHex(lo.edge, hi.edge, t),
      };
    }
  }
  return DAY_PALETTE;
}

function mixHex(a: string, b: string, t: number): string {
  const clampT = clamp01(t);
  const channel = (offset: number) => {
    const av = parseInt(a.slice(offset, offset + 2), 16);
    const bv = parseInt(b.slice(offset, offset + 2), 16);
    return Math.round(av + (bv - av) * clampT)
      .toString(16)
      .padStart(2, '0');
  };
  return `#${channel(1)}${channel(3)}${channel(5)}`;
}
