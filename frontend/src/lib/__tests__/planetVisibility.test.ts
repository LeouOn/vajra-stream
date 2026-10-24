import { describe, expect, it } from 'vitest';
import {
  DAY_PLANET_LIMIT_MAG,
  HIGH_DAY_PLANET_LIMIT_MAG,
  PLANET_LIMIT_FLOOR_MAG,
  PLANET_MAGNITUDES,
  formatPlanetMagnitude,
  isDimmedPlanet,
  planetLimitingMagnitude,
  planetVisible,
} from '../planetVisibility';
import { limitingMagnitude } from '../skyBrightness';

const FULL_HIGH_MOON = { altDeg: 80, illuminatedFraction: 1 };

describe('planetLimitingMagnitude', () => {
  it('uses the star limit at night and through twilight', () => {
    for (const alt of [-40, -18, -12, -6, -0.1]) {
      expect(planetLimitingMagnitude(alt)).toBe(limitingMagnitude(alt));
      expect(planetLimitingMagnitude(alt, FULL_HIGH_MOON)).toBe(
        limitingMagnitude(alt, FULL_HIGH_MOON),
      );
    }
  });

  it('uses the daylight pieces: Venus-only 0..10, Jupiter from +10', () => {
    expect(planetLimitingMagnitude(0)).toBe(DAY_PLANET_LIMIT_MAG);
    expect(planetLimitingMagnitude(5)).toBe(DAY_PLANET_LIMIT_MAG);
    expect(planetLimitingMagnitude(10)).toBe(HIGH_DAY_PLANET_LIMIT_MAG);
    expect(planetLimitingMagnitude(40)).toBe(HIGH_DAY_PLANET_LIMIT_MAG);
  });

  it('never goes below the documented floor and steps only at Sun 0 and +10', () => {
    let previous = Infinity;
    for (let alt = -30; alt <= 9.9; alt += 0.1) {
      const limit = planetLimitingMagnitude(alt);
      expect(limit).toBeGreaterThanOrEqual(PLANET_LIMIT_FLOOR_MAG);
      expect(limit).toBeLessThanOrEqual(previous + 1e-12);
      previous = limit;
    }
    for (let alt = 10; alt <= 40; alt += 0.1) {
      expect(planetLimitingMagnitude(alt)).toBeGreaterThanOrEqual(PLANET_LIMIT_FLOOR_MAG);
      expect(planetLimitingMagnitude(alt)).toBe(HIGH_DAY_PLANET_LIMIT_MAG);
    }
    // The planet limit steps down at Sun 0 (Jupiter leaves) and back up at +10
    // (Jupiter returns); document both edges.
    expect(planetLimitingMagnitude(-0.1)).toBe(limitingMagnitude(-0.1));
    expect(planetLimitingMagnitude(0)).toBe(DAY_PLANET_LIMIT_MAG);
    expect(planetLimitingMagnitude(9.9)).toBe(DAY_PLANET_LIMIT_MAG);
    expect(planetLimitingMagnitude(10)).toBe(HIGH_DAY_PLANET_LIMIT_MAG);
  });
});

describe('planetVisible', () => {
  const altGrid = [-40, -18, -12, -6, -3, 0, 5, 10, 40];
  const expectations: Record<string, boolean[]> = {
    // -40  -18   -12   -6    -3    0     5     10    40
    mercury: [true, true, true, true, false, false, false, false, false],
    venus: [true, true, true, true, true, true, true, true, true],
    mars: [true, true, true, true, false, false, false, false, false],
    jupiter: [true, true, true, true, true, false, false, true, true],
    saturn: [true, true, true, true, false, false, false, false, false],
    uranus: [true, true, false, false, false, false, false, false, false],
    neptune: [false, false, false, false, false, false, false, false, false],
    pluto: [false, false, false, false, false, false, false, false, false],
  };
  it('matches the literal Sun-altitude grid for every planet', () => {
    for (const [id, rows] of Object.entries(expectations)) {
      altGrid.forEach((alt, index) => {
        expect(planetVisible(PLANET_MAGNITUDES[id], alt), `${id} at ${alt}`).toBe(rows[index]);
      });
    }
  });

  it('the Moon penalty dims the faint planets at night but not the bright ones', () => {
    expect(planetVisible(PLANET_MAGNITUDES.uranus, -30, FULL_HIGH_MOON)).toBe(false);
    expect(planetVisible(PLANET_MAGNITUDES.saturn, -30, FULL_HIGH_MOON)).toBe(true);
    expect(planetVisible(PLANET_MAGNITUDES.venus, -30, FULL_HIGH_MOON)).toBe(true);
  });
});

describe('isDimmedPlanet', () => {
  it('never dims the Sun/Moon or the x-ray view, and formats magnitudes', () => {
    expect(isDimmedPlanet('sun', 0, 40, undefined, false)).toBe(false);
    expect(isDimmedPlanet('moon', 0, 40, undefined, false)).toBe(false);
    expect(isDimmedPlanet('neptune', 7.8, -30, undefined, true)).toBe(false);
    expect(isDimmedPlanet('neptune', 7.8, -30, undefined, false)).toBe(true);
    expect(isDimmedPlanet('jupiter', -2.2, 5, undefined, false)).toBe(true);
    expect(isDimmedPlanet('jupiter', -2.2, 10, undefined, false)).toBe(false);
    expect(formatPlanetMagnitude(7.8)).toBe('+7.8');
    expect(formatPlanetMagnitude(-2.2)).toBe('-2.2');
  });
});
