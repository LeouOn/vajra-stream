/**
 * Tests for the pure data arrays exported by BodhicittaBanner.jsx.
 *
 * Verifies the 10 bodhicitta affirmations and 4 Four Immeasurables
 * are intact: right count, required fields, expected content
 * (text length, mantra format, icon refs), and the canonical
 * mapping of the Four Immeasurables.
 */
import { describe, it, expect } from 'vitest';
import { AFFIRMATIONS, FOUR_IMMEASURABLES } from '../components/UI/BodhicittaBanner';

describe('AFFIRMATIONS', () => {
  it('has 10 entries', () => {
    expect(AFFIRMATIONS).toHaveLength(10);
  });

  it('every entry has text, source, icon, color', () => {
    for (const a of AFFIRMATIONS) {
      expect(typeof a.text).toBe('string');
      expect(a.text.length).toBeGreaterThan(20);
      expect(typeof a.source).toBe('string');
      expect(a.source.length).toBeGreaterThan(0);
      expect(['function', 'object']).toContain(typeof a.icon);
      expect(typeof a.color).toBe('string');
      expect(a.color).toMatch(/^text-/);
    }
  });

  it('all sources reference the Four Immeasurables or classic texts', () => {
    const keywords = ['Maitri', 'Karuna', 'Mudita', 'Upeksha',
                       'Shantideva', 'Atisha', 'Bodhicitta', 'Bodhisattva',
                       'Sangha', 'Vow', 'Ceremony'];
    for (const a of AFFIRMATIONS) {
      const hasKeyword = keywords.some(kw => a.source.includes(kw));
      expect(hasKeyword, `affirmation source should mention a known tradition: ${a.source}`).toBe(true);
    }
  });

  it('all texts are meaningful (length 40-300)', () => {
    for (const a of AFFIRMATIONS) {
      expect(a.text.length, `text too short: ${a.text}`).toBeGreaterThanOrEqual(40);
      expect(a.text.length, `text too long: ${a.text}`).toBeLessThanOrEqual(300);
    }
  });

  it('most texts mention "beings" (Shantideva quote is the exception)', () => {
    const mentions = AFFIRMATIONS.filter(a => a.text.toLowerCase().includes('beings'));
    expect(mentions.length, 'at least 8 of 10 should mention beings').toBeGreaterThanOrEqual(8);
  });
});

describe('FOUR_IMMEASURABLES', () => {
  it('has exactly 4 entries (Maitri, Karuna, Mudita, Upeksha)', () => {
    expect(FOUR_IMMEASURABLES).toHaveLength(4);
    const names = FOUR_IMMEASURABLES.map(x => x.name);
    expect(names).toEqual(['Maitri', 'Karuna', 'Mudita', 'Upeksha']);
  });

  it('every entry has the canonical 7 fields', () => {
    const required = ['name', 'sanskrit', 'english', 'mantra', 'wish', 'practice', 'color'];
    for (const imm of FOUR_IMMEASURABLES) {
      for (const field of required) {
        expect(imm[field], `${imm.name} missing ${field}`).toBeDefined();
        expect(imm[field], `${imm.name} ${field} should be non-empty`).not.toBe('');
      }
    }
  });

  it('the canonical name -> english mapping is correct', () => {
    const byName = Object.fromEntries(FOUR_IMMEASURABLES.map(x => [x.name, x.english]));
    expect(byName.Maitri).toBe('Loving-Kindness');
    expect(byName.Karuna).toBe('Compassion');
    expect(byName.Mudita).toBe('Sympathetic Joy');
    expect(byName.Upeksha).toBe('Equanimity');
  });

  it('mantras start with "Om "', () => {
    for (const imm of FOUR_IMMEASURABLES) {
      expect(imm.mantra.startsWith('Om '), `${imm.name} mantra: ${imm.mantra}`).toBe(true);
    }
  });

  it('mantras end with "Ah Hum" except Karuna (which is the Chenrezig mantra)', () => {
    for (const imm of FOUR_IMMEASURABLES) {
      const isKaruna = imm.name === 'Karuna';
      if (isKaruna) {
        expect(imm.mantra).toBe('Om Mani Padme Hum');
      } else {
        expect(imm.mantra.endsWith('Ah Hum'), `${imm.name} mantra: ${imm.mantra}`).toBe(true);
      }
    }
  });

  it('wishes start with "May all beings"', () => {
    for (const imm of FOUR_IMMEASURABLES) {
      expect(imm.wish.startsWith('May all beings'),
             `${imm.name}: ${imm.wish}`).toBe(true);
    }
  });

  it('colors are valid hex codes', () => {
    for (const imm of FOUR_IMMEASURABLES) {
      expect(imm.color, `${imm.name} color`).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
});
