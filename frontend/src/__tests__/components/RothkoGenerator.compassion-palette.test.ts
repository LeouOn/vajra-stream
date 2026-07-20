/**
 * S4 — Meditation compassion palette must read as PINK on render, not BROWN.
 *
 * The pre-fix palette was dusty muted rose (#e8a0bf, #c75b7a, #f2d0d9, #ba274a,
 * #f9e4e8) which, when blurred with high opacity over a near-black bg,
 * blended into a brownish-maroon canvas that contradicted the visible copy
 * "Pinks, soft reds, warm whites". This test pins the palette to a tighter
 * hue/saturation contract that any future edit must satisfy.
 *
 * Asserts (per color in palette.colors):
 *   - R > G + 15           (clearly warm/pink, not yellow-red)
 *   - R > B + 0            (R dominates so it reads as pink, not grey)
 *   - sum(R,G,B) > 320     (not muddy/dark enough to flatten to brown on blur)
 *   - max(R,G,B) - min(R,G,B) >= 40  (visible saturation)
 */
import React from 'react';
import { describe, it, expect } from 'vitest';
import { PALETTES } from '../../components/2D/RothkoGenerator';

const hexToRgb = (hex: string): { r: number; g: number; b: number } => {
  const h = hex.replace('#', '');
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
};

const isVividPink = (hex: string): { ok: boolean; reason?: string } => {
  const { r, g, b } = hexToRgb(hex);
  if (r < g + 15) return { ok: false, reason: `R (${r}) not > G+15 (${g + 15}); reads yellow-red, not pink` };
  if (r < b) return { ok: false, reason: `R (${r}) < B (${b}); reads as cool/dusty, not pink` };
  const sum = r + g + b;
  if (sum < 320) return { ok: false, reason: `sum=${sum} < 320; too dark, will blend to brown on blur` };
  const range = Math.max(r, g, b) - Math.min(r, g, b);
  if (range < 40) return { ok: false, reason: `range=${range} < 40; desaturated, will read muddy` };
  return { ok: true };
};

describe('compassion palette is vivid pink (regression for meditation brown render)', () => {
  it('every color in palette.colors is a vivid warm pink', () => {
    const palette = PALETTES.compassion;
    expect(palette.colors.length).toBeGreaterThanOrEqual(5);
    palette.colors.forEach((hex) => {
      const result = isVividPink(hex);
      expect(result.ok, `color ${hex} failed: ${result.reason}`).toBe(true);
    });
  });

  it('palette description promises pink/red/warm-white (not brown)', () => {
    const desc = PALETTES.compassion.description.toLowerCase();
    expect(desc).toMatch(/pink|rose|red|warm|blush|coral|love|loving/);
    expect(desc).not.toMatch(/brown|ochre|earth|amber/);
  });

  it('palette bg is a warm dark (not grey/cool), so it does not flatten the palette to brown', () => {
    const { r, g, b } = hexToRgb(PALETTES.compassion.bg);
    expect(r).toBeGreaterThanOrEqual(g); // warm not cool
    expect(r).toBeGreaterThanOrEqual(b); // warm not blue
  });
});
