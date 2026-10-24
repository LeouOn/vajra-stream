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
