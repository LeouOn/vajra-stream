/**
 * savedRituals.ts — the local ritual archive (localStorage, newest first,
 * capped at 50 entries).
 */
import { SAVED_RITUALS_KEY, type SavedRitual } from './outlookShared';
import type { CurrentNarrative } from './outlookNarrative';

export function loadSavedRituals(): SavedRitual[] {
  try {
    const raw = window.localStorage.getItem(SAVED_RITUALS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed as SavedRitual[] : [];
  } catch {
    return [];
  }
}

/** Archive entry for a narrative; `fallbackGenre` is the form's genre. */
export function buildSavedRitual(narrative: CurrentNarrative & { narrative: string }, fallbackGenre: string): SavedRitual {
  return {
    id: `ritual_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    savedAt: new Date().toISOString(),
    genre: narrative.genre || fallbackGenre,
    narrative: narrative.narrative,
    divinationRaw: narrative.divination_raw || null,
    entities: narrative.entities_used || null,
    model: narrative.model_used || null,
    provider: narrative.provider_used || null,
  };
}

/** Prepend an entry to the archive. Throws when localStorage is full or disabled. */
export function appendSavedRitual(entry: SavedRitual): void {
  const existing = loadSavedRituals();
  const next = [entry, ...existing].slice(0, 50);
  window.localStorage.setItem(SAVED_RITUALS_KEY, JSON.stringify(next));
}
