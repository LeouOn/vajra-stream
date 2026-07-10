/**
 * Practice streak + journal storage helpers.
 *
 * Kept in a standalone module so the per-practice streak math, the
 * per-session journal entry shape, and the localStorage round-trip are
 * independently testable (the PracticeDetail component file pulls in
 * AntD / R3F / Web Audio and isn't a friendly test subject).
 *
 * localStorage keys:
 *   vajra_practice_streaks: { [practiceId]: ["YYYY-MM-DD", ...] }
 *   vajra_practice_journal: [{ date, practiceId, reflection, recited }]
 *
 * Both shapes are sorted descending on read (journal) or ascending on
 * write (streaks) so downstream code can rely on a stable order.
 */

export interface StreakMap {
  [practiceId: string]: string[];
}

export interface JournalEntry {
  date: string;
  practiceId: string;
  reflection: string;
  recited: number;
}

export const STREAK_STORAGE_KEY = 'vajra_practice_streaks';
export const JOURNAL_STORAGE_KEY = 'vajra_practice_journal';
export const JOURNAL_MAX_ENTRIES = 200;

export function todayStr(): string {
  const d = new Date();
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, '0'),
    String(d.getDate()).padStart(2, '0'),
  ].join('-');
}

function shiftDate(date: string, deltaDays: number): string {
  const parts = date.split('-');
  if (parts.length !== 3) return date;
  const [y, m, d] = parts.map((n) => Number.parseInt(n, 10));
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return date;
  const epoch = Date.UTC(y, m - 1, d) + deltaDays * 86400000;
  const shifted = new Date(epoch);
  return [
    shifted.getUTCFullYear(),
    String(shifted.getUTCMonth() + 1).padStart(2, '0'),
    String(shifted.getUTCDate()).padStart(2, '0'),
  ].join('-');
}

export function readStreaks(): StreakMap {
  try {
    const raw = localStorage.getItem(STREAK_STORAGE_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    const result: StreakMap = {};
    for (const [key, val] of Object.entries(parsed as Record<string, unknown>)) {
      if (Array.isArray(val) && val.every((d) => typeof d === 'string')) {
        result[key] = [...new Set(val)].sort();
      }
    }
    return result;
  } catch {
    return {};
  }
}

export function writeStreaks(map: StreakMap): void {
  try {
    localStorage.setItem(STREAK_STORAGE_KEY, JSON.stringify(map));
  } catch {
    // localStorage quota / disabled — silently ignore.
  }
}

export function recordSession(
  map: StreakMap,
  practiceId: string,
  date: string,
): string[] {
  const existing = map[practiceId] ?? [];
  if (existing.includes(date)) return existing;
  const next = [...existing, date].sort();
  writeStreaks({ ...map, [practiceId]: next });
  return next;
}

export function computeCurrentStreak(dates: string[], today: string): number {
  if (dates.length === 0) return 0;
  const set = new Set(dates);
  const yesterday = shiftDate(today, -1);
  let cursor: string;
  if (set.has(today)) {
    cursor = today;
  } else if (set.has(yesterday)) {
    cursor = yesterday;
  } else {
    return 0;
  }
  let count = 0;
  while (set.has(cursor)) {
    count += 1;
    cursor = shiftDate(cursor, -1);
  }
  return count;
}

export function readJournal(): JournalEntry[] {
  try {
    const raw = localStorage.getItem(JOURNAL_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((e): e is JournalEntry =>
        !!e
        && typeof e === 'object'
        && typeof (e as JournalEntry).date === 'string'
        && typeof (e as JournalEntry).practiceId === 'string'
        && typeof (e as JournalEntry).reflection === 'string',
      )
      .sort((a, b) => b.date.localeCompare(a.date));
  } catch {
    return [];
  }
}

export function appendJournal(entry: JournalEntry): void {
  try {
    const all = readJournal();
    all.unshift(entry);
    const trimmed = all.slice(0, JOURNAL_MAX_ENTRIES);
    localStorage.setItem(JOURNAL_STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    // ignore
  }
}