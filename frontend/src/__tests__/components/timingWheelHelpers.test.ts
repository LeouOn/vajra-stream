import { describe, it, expect } from 'vitest';
import {
  polarToCartesian,
  describeWedge,
  formatHourTime,
  PLANET_COLORS,
  PLANET_SYMBOLS,
  GENRE_COLORS,
} from '../../components/UI/timingWheelHelpers';

describe('timingWheelHelpers', () => {
  it('converts polar coordinates to Cartesian correctly', () => {
    // 0 deg is UP (y = cy - radius, x = cx)
    const top = polarToCartesian(100, 100, 50, 0);
    expect(top.x).toBeCloseTo(100, 1);
    expect(top.y).toBeCloseTo(50, 1);

    // 90 deg is RIGHT (x = cx + radius, y = cy)
    const right = polarToCartesian(100, 100, 50, 90);
    expect(right.x).toBeCloseTo(150, 1);
    expect(right.y).toBeCloseTo(100, 1);

    // 180 deg is DOWN (y = cy + radius, x = cx)
    const bottom = polarToCartesian(100, 100, 50, 180);
    expect(bottom.x).toBeCloseTo(100, 1);
    expect(bottom.y).toBeCloseTo(150, 1);
  });

  it('generates valid SVG wedge paths', () => {
    const path = describeWedge(100, 100, 30, 80, 0, 45);
    expect(path).toContain('M ');
    expect(path).toContain('A 80 80');
    expect(path).toContain('L ');
    expect(path).toContain('A 30 30');
    expect(path).toContain('Z');
  });

  it('formats ISO time correctly', () => {
    const formatted = formatHourTime('2026-08-18T14:30:00Z');
    expect(typeof formatted).toBe('string');
    expect(formatted.length).toBeGreaterThan(0);
  });

  it('contains color definitions and symbols for all 7 Chaldean planets', () => {
    const planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'];
    planets.forEach((p) => {
      expect(PLANET_COLORS[p]).toBeDefined();
      expect(PLANET_SYMBOLS[p]).toBeDefined();
    });
  });

  it('contains color definitions for standard practice genres', () => {
    const genres = ['healing', 'wisdom', 'purification', 'compassion', 'protection', 'prosperity', 'victory', 'creativity'];
    genres.forEach((g) => {
      expect(GENRE_COLORS[g]).toBeDefined();
    });
  });
});
