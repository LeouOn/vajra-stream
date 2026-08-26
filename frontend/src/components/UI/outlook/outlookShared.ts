/**
 * outlookShared.ts — presentation constants + helpers shared by the
 * extracted Outlook tab components (Generator / Universe / History).
 */

export interface Realm {
  id: string | number;
  name: string;
  description?: string;
  location_type?: string;
  is_metaphysical?: boolean;
  latitude?: number | null;
  longitude?: number | null;
  dimension_frequency?: number;
  priority?: number;
  realm_governor?: string;
  celestial_coordinates?: string;
  total_narratives_featured?: number;
  timezone?: string;
  astrological_anchor?: string;
  elemental_affinity?: string;
  source_type?: string;
  [key: string]: unknown;
}

export interface Character {
  id: string | number;
  name: string;
  description?: string;
  role: string;
  tags?: string[];
  mantra_preference?: string;
  elemental_anchor?: string;
  total_narratives_featured?: number;
  dialogue_style?: string;
  priority?: number;
  source_type?: string;
  [key: string]: unknown;
}

export interface Population {
  id: string | number;
  name: string;
  description?: string;
  category?: string;
  is_active?: boolean;
  is_urgent?: boolean;
  priority?: number;
  intentions?: string[];
  [key: string]: unknown;
}

export type UniverseTabId = 'realms' | 'characters' | 'populations';

export const GENRE_COLORS: Record<string, string> = {
  healing: 'rgba(0, 168, 107, 0.05)',
  victory: 'rgba(220, 20, 60, 0.05)',
  alchemist: 'rgba(218, 165, 32, 0.05)',
  fun_parable: 'rgba(100, 149, 237, 0.05)',
  dharani: 'rgba(138, 43, 226, 0.05)',
  compassion: 'rgba(255, 105, 180, 0.05)',
  wisdom: 'rgba(100, 149, 237, 0.05)',
  protection: 'rgba(34, 139, 34, 0.05)',
};

export const GENRE_BORDER_COLORS: Record<string, string> = {
  healing: '#00A86B',
  victory: '#dc143c',
  alchemist: '#daa520',
  fun_parable: '#6495ed',
  dharani: '#8a2be2',
  compassion: '#ff69b4',
  wisdom: '#6495ed',
  protection: '#228b22',
};

export interface HistoryItem {
  id?: number;
  type?: string;
  date_generated?: string;
  genre?: string;
  content?: string;
  astrology_context?: string;
  divination_context?: string;
  divination_raw?: unknown;
  entities_invoked?: string;
  model_used?: string | null;
  provider_used?: string | null;
  [key: string]: unknown;
}

export interface SavedRitual {
  id: string;
  savedAt: string;
  genre: string;
  narrative: string;
  divinationRaw: unknown | null;
  entities: string | null;
  model: string | null;
  provider: string | null;
}

export const SAVED_RITUALS_KEY = 'vajra.savedRituals.v1';

export function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^>\s+/gm, '')
    .trim();
}
