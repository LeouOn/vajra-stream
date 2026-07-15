import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  appendJournal,
  computeCurrentStreak,
  readJournal,
  readStreaks,
  recordSession,
  writeStreaks,
  type JournalEntry,
  type StreakMap,
} from '../utils/practiceStorage';

describe('practiceStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('streaks', () => {
    it('returns 0 for an empty list', () => {
      expect(computeCurrentStreak([], '2026-07-10')).toBe(0);
    });

    it('counts a single day ending today', () => {
      expect(computeCurrentStreak(['2026-07-10'], '2026-07-10')).toBe(1);
    });

    it('counts consecutive days ending today', () => {
      expect(
        computeCurrentStreak(['2026-07-08', '2026-07-09', '2026-07-10'], '2026-07-10'),
      ).toBe(3);
    });

    it('keeps streak visible when last session was yesterday', () => {
      expect(computeCurrentStreak(['2026-07-08', '2026-07-09'], '2026-07-10')).toBe(2);
    });

    it('resets to 0 after a one-day gap', () => {
      expect(computeCurrentStreak(['2026-07-07', '2026-07-08'], '2026-07-10')).toBe(0);
    });

    it('handles month/year rollover', () => {
      expect(
        computeCurrentStreak(['2026-06-29', '2026-06-30', '2026-07-01'], '2026-07-01'),
      ).toBe(3);
    });

    it('recordSession dedupes when the same date is recorded twice', () => {
      const first = recordSession({}, 'green_tara', '2026-07-10');
      const second = recordSession({ green_tara: first }, 'green_tara', '2026-07-10');
      expect(second).toEqual(first);
    });

    it('recordSession appends and sorts ascending', () => {
      const after1 = recordSession({}, 'green_tara', '2026-07-10');
      const after2 = recordSession({ green_tara: after1 }, 'green_tara', '2026-07-08');
      expect(after2).toEqual(['2026-07-08', '2026-07-10']);
    });

    it('writeStreaks then readStreaks round-trips', () => {
      const map: StreakMap = {
        green_tara: ['2026-07-08', '2026-07-09', '2026-07-10'],
        medicine_buddha: ['2026-07-10'],
      };
      writeStreaks(map);
      expect(readStreaks()).toEqual(map);
    });

    it('readStreaks drops malformed entries', () => {
      localStorage.setItem(
        'vajra_practice_streaks',
        JSON.stringify({
          green_tara: ['2026-07-10'],
          bad: 'not-an-array',
          ok: ['2026-07-09', 42],
        }),
      );
      expect(readStreaks()).toEqual({ green_tara: ['2026-07-10'] });
    });
  });

  describe('journal', () => {
    it('appendJournal stores entries sorted descending by date', () => {
      appendJournal({
        date: '2026-07-10', practiceId: 'green_tara', reflection: 'today', recited: 108,
      });
      appendJournal({
        date: '2026-07-08', practiceId: 'green_tara', reflection: 'two days ago', recited: 50,
      });
      appendJournal({
        date: '2026-07-09', practiceId: 'green_tara', reflection: 'yesterday', recited: 108,
      });
      const all = readJournal();
      expect(all.map((j) => j.date)).toEqual(['2026-07-10', '2026-07-09', '2026-07-08']);
    });

    it('readJournal filters malformed entries', () => {
      localStorage.setItem(
        'vajra_practice_journal',
        JSON.stringify([
          { date: '2026-07-10', practiceId: 'green_tara', reflection: 'ok', recited: 108 },
          null,
          { date: 42, practiceId: 'green_tara', reflection: 'bad date', recited: 0 },
          'not an object',
        ]),
      );
      const all = readJournal();
      expect(all).toHaveLength(1);
      expect(all[0].reflection).toBe('ok');
    });

    it('appendJournal trims to JOURNAL_MAX_ENTRIES', () => {
      // 200 entries pre-existing
      const initial: JournalEntry[] = [];
      for (let i = 0; i < 200; i += 1) {
        initial.push({
          date: `2026-01-${String((i % 28) + 1).padStart(2, '0')}`,
          practiceId: 'green_tara',
          reflection: `entry ${i}`,
          recited: 108,
        });
      }
      localStorage.setItem('vajra_practice_journal', JSON.stringify(initial));
      appendJournal({
        date: '2026-07-10',
        practiceId: 'green_tara',
        reflection: 'newest',
        recited: 108,
      });
      expect(readJournal()).toHaveLength(200);
    });
  });
});