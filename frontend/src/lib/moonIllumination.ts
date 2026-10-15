/**
 * Format the Moon's illumination for display.
 *
 * `core/astrology.py:get_moon_phase` always reports `illumination` as a
 * 0–100 percentage (`(1 - cos(phase_angle)) / 2 * 100`), and the
 * "Copy for LLM" export (`lib/astrologyExport.js`) prints it as-is.
 *
 * The Cosmic Clock card used to guess the unit (`<= 1` → fraction → ×100),
 * which mis-rendered every value under 1% — i.e. the ~2 days around each
 * new moon — as up to 100% (0.45% showed as "45.0%").
 */
export function formatMoonIllumination(illumination: number | null | undefined): string {
  if (illumination == null || !Number.isFinite(illumination)) return '—';
  return `${illumination.toFixed(1)}%`;
}
