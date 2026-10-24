/**
 * Earth & Sky wave 5 — the twilight horizon glow (pure parameters).
 *
 * A warm gradient along the rim of the dome disc, centred on the Sun's
 * azimuth, strongest around Sun -2..+2 deg and absent by +6 deg. Above +6 deg
 * only a faint halo around the Sun marker remains. The night picture
 * (Sun <= -18) gets nothing, so it is byte-identical.
 *
 * `TWILIGHT_GLOW_ENABLED` is the one switch: set it false to remove the glow
 * without touching the dome.
 */

export const TWILIGHT_GLOW_ENABLED = true;
/** Glow fades in from this Sun altitude. */
export const GLOW_START_SUN_ALT_DEG = -18;
/** Full strength from here... */
export const GLOW_FULL_SUN_ALT_DEG = -2;
/** ...to here, then fades out. */
export const GLOW_PEAK_END_SUN_ALT_DEG = 2;
/** Glow ends here; above it only the halo remains. */
export const GLOW_END_SUN_ALT_DEG = 6;
/** Angular width of the warm rim band. */
export const GLOW_WIDTH_DEG = 70;
/** Half-width: beyond this off-axis angle the glow is 0. */
export const GLOW_HALF_WIDTH_DEG = GLOW_WIDTH_DEG / 2;
/** Opacity of the midday halo around the Sun marker. */
export const HALO_ALPHA = 0.18;

export type GlowKind = 'horizon' | 'halo' | 'none';

export interface SkyGlow {
  kind: GlowKind;
  /** 0..1 strength (halo uses HALO_ALPHA). */
  alpha: number;
  /** Azimuth of the Sun / band centre, degrees [0, 360). */
  azimuthDeg: number;
}

function wrap360(deg: number): number {
  const wrapped = deg % 360;
  return wrapped < 0 ? wrapped + 360 : wrapped;
}

/** Half-width of the flat 1.0 plateau around the Sun's azimuth. */
export const GLOW_PLATEAU_HALF_WIDTH_DEG = 12;

/**
 * The angular alpha envelope across the band: a FLAT 1.0 plateau within +-12
 * degrees of the Sun's azimuth, then a raised cosine from 12 to 35 degrees down
 * to 0, with zero slope at 12 and at 35 (no crisp radial cut). The plateau keeps
 * the strongest twilight (-2 deg) and the deep -12 deg case visibly warm rather
 * than spending the energy in a narrow spike. Symmetric and continuous; 0
 * outside the band.
 */
export function angularGlowProfile(offsetDeg: number): number {
  const abs = Math.abs(offsetDeg);
  if (!Number.isFinite(abs) || abs >= GLOW_HALF_WIDTH_DEG) return 0;
  if (abs <= GLOW_PLATEAU_HALF_WIDTH_DEG) return 1;
  const t = (abs - GLOW_PLATEAU_HALF_WIDTH_DEG) / (GLOW_HALF_WIDTH_DEG - GLOW_PLATEAU_HALF_WIDTH_DEG);
  return 0.5 * (1 + Math.cos(Math.PI * t));
}

/**
 * The glow parameters for a Sun altitude/azimuth. Continuous through the
 * twilight band; the kind changes to `halo` above +6 deg (the faint daytime
 * glow around the Sun marker).
 */
export function twilightGlow(sunAltDeg: number, sunAzDeg: number): SkyGlow {
  const azimuthDeg = Number.isFinite(sunAzDeg) ? wrap360(sunAzDeg) : 0;
  if (!Number.isFinite(sunAltDeg) || sunAltDeg < GLOW_START_SUN_ALT_DEG) {
    return { kind: 'none', alpha: 0, azimuthDeg };
  }
  if (sunAltDeg > GLOW_END_SUN_ALT_DEG) {
    return { kind: 'halo', alpha: HALO_ALPHA, azimuthDeg };
  }
  let alpha: number;
  if (sunAltDeg <= GLOW_FULL_SUN_ALT_DEG) {
    alpha =
      (sunAltDeg - GLOW_START_SUN_ALT_DEG) /
      (GLOW_FULL_SUN_ALT_DEG - GLOW_START_SUN_ALT_DEG);
  } else if (sunAltDeg <= GLOW_PEAK_END_SUN_ALT_DEG) {
    alpha = 1;
  } else {
    alpha = (GLOW_END_SUN_ALT_DEG - sunAltDeg) / (GLOW_END_SUN_ALT_DEG - GLOW_PEAK_END_SUN_ALT_DEG);
  }
  return { kind: 'horizon', alpha: Math.max(0, Math.min(1, alpha)), azimuthDeg };
}
