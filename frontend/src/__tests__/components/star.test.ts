/**
 * star.test.ts — pure mapping from workings summaries to night-sky stars.
 *
 * Locks the constellation math: moon bands, source hues, merit sizing,
 * time normalization, ghost/duplicate semantics, and sibling grouping.
 */
import { describe, it, expect } from 'vitest';
import {
  constellationGroups,
  moonPhaseToBand,
  relativeSealTime,
  sourceHue,
  starSize,
  summaryToStar,
  type Star,
} from '../../components/Workings/star';

describe('moonPhaseToBand', () => {
  it('maps canonical phases case-insensitively', () => {
    expect(moonPhaseToBand('Full Moon')).toBe(4);
    expect(moonPhaseToBand('waning crescent')).toBe(7);
    expect(moonPhaseToBand('New')).toBe(0);
    expect(moonPhaseToBand('Last Quarter Moon')).toBe(6);
  });
  it('falls back to the neutral mid band', () => {
    expect(moonPhaseToBand(undefined)).toBe(3);
    expect(moonPhaseToBand('')).toBe(3);
    expect(moonPhaseToBand('banana')).toBe(3);
  });
});

describe('sourceHue', () => {
  it('assigns the fixed palette', () => {
    expect(sourceHue('command-center')).toBe('#22d3ee');
    expect(sourceHue('Ritual-Composer')).toBe('#f472b6');
  });
  it('falls back to starlight white', () => {
    expect(sourceHue(undefined)).toBe('#e2e8f0');
  });
});

describe('starSize', () => {
  it('keeps ordinary nights small and Duchen nights brightest', () => {
    expect(starSize(1)).toBeLessThanOrEqual(2.2);
    expect(starSize(100000)).toBeGreaterThanOrEqual(7.8);
    expect(starSize(1000000)).toBeLessThanOrEqual(8); // capped
  });
});

describe('relativeSealTime', () => {
  it('describes recent seals and rejects garbage', () => {
    expect(relativeSealTime(new Date().toISOString())).toBe('just now');
    expect(relativeSealTime('nope')).toBe('—');
    expect(relativeSealTime('')).toBe('—');
  });
});

describe('summaryToStar', () => {
  const all = [
    {
      working_id: 'a',
      intention: 'Peace',
      target: 'All beings',
      sealed_at: '2026-08-14T00:00:00Z',
      rate_values: [1, 2, 3, 4, 5],
      source: 'command-center',
    },
    {
      working_id: 'b',
      intention: 'peace',
      target: 'all beings',
      sealed_at: '2026-08-16T00:00:00Z',
      rate_values: [1, 2, 3, 4, 5],
      source: 'command-center',
      hidden: true,
      duplicate_of: 'a',
      moon_phase: 'Full Moon',
      saka_dawa_multiplier: 100000,
    },
  ];
  it('normalizes time across the set', () => {
    const stars = all.map((s, i) => summaryToStar(s, i, all));
    expect(stars[0].t).toBe(0);
    expect(stars[1].t).toBe(1);
  });
  it('ghosts hidden duplicates and shares the sibling group key', () => {
    const stars = all.map((s, i) => summaryToStar(s, i, all));
    expect(stars[1].ghost).toBe(true);
    expect(stars[1].alpha).toBe(0.25);
    expect(stars[1].duplicateOf).toBe('a');
    expect(stars[1].groupKey).toBe(stars[0].groupKey);
  });
  it('centers a lone sitting', () => {
    const star = summaryToStar(all[0], 0, [all[0]]);
    expect(star.t).toBe(0.5);
  });
});

describe('constellationGroups', () => {
  it('groups siblings and orders them chronologically', () => {
    const mk = (id: string, t: number, key: string): Star => ({
      working_id: id,
      intention: 'peace',
      dials: '',
      sealedAt: '',
      multiplier: 1,
      t,
      band: 3,
      size: 2,
      hue: '#fff',
      alpha: 1,
      ghost: false,
      groupKey: key,
      duplicateOf: null,
    });
    const built = [
      mk('late', 0.9, 'peace|all beings|1,2,3,4,5'),
      mk('early', 0.1, 'peace|all beings|1,2,3,4,5'),
      mk('other', 0.5, 'healing|all beings|9,9,9,9,9'),
    ];
    const groups = constellationGroups(built);
    expect(groups).toHaveLength(2);
    expect(groups[0].map((s) => s.working_id)).toEqual(['early', 'late']);
  });
});
