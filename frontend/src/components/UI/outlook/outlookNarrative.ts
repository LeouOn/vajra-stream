/**
 * outlookNarrative.ts — the Generator's narrative shapes and the pure helpers
 * that read them (chapter validation, plain text, ritual section split,
 * history-item normalization). No React here.
 */
import type { EpicChapter } from '../EpicStoryViewer';
import type { HistoryItem } from './outlookShared';

export interface DivinationCardPayload {
  svg?: string;
  name?: string;
  [key: string]: unknown;
}

export interface SigilData {
  kamea?: string;
  reduced?: string;
  coordinates?: Array<{ x: number; y: number; value?: number; letter?: string }>;
  svg?: string;
}

export interface DivinationRaw {
  tarot?: DivinationCardPayload;
  iching?: DivinationCardPayload;
  sigil?: SigilData;
  [key: string]: unknown;
}

export interface CurrentNarrative {
  id?: string | number;
  type?: string;
  genre?: string;
  narrative?: string;
  /** Epic outlooks: the chapter list (the generator and /history both send objects). */
  narrative_parts?: EpicChapter[];
  astrology_used?: string;
  divination_used?: string;
  divination_raw?: DivinationRaw;
  entities_used?: string;
  model_used?: string | null;
  provider_used?: string | null;
  [key: string]: unknown;
}

/** POST /outlook/illustration reply. */
export interface IllustrationResult {
  image_data_url: string;
  model?: string;
  cost_usd?: number;
  provider_used?: string;
  revised_prompt?: string | null;
  cached?: boolean;
  /** The imagery-only prompt the server sent (no chart numbers). */
  prompt?: string;
  /** Real values captioned under the image (moon at chart time, ...). */
  caption_facts?: unknown;
}

export type ResultTab = 'narrative' | 'affirmation';
export type LoopMode = 'sequential_delay' | 'consecutive';
export type GeneratorTab = 'generator' | 'universe' | 'history' | 'journey';
export type GenerationMode = 'guided' | 'quick';

/** Validate an epic's stored chapter list (HistoryItem.content for type 'epic'). */
export function toEpicChapters(value: unknown): EpicChapter[] | undefined {
  if (!Array.isArray(value)) return undefined;
  return value
    .filter((p): p is Record<string, unknown> => !!p && typeof p === 'object')
    .map((p, i) => ({
      chapter: typeof p.chapter === 'number' ? p.chapter : i + 1,
      title: typeof p.title === 'string' ? p.title : `Chapter ${i + 1}`,
      content: typeof p.content === 'string' ? p.content : '',
    }));
}

export function toDivinationRaw(value: unknown): DivinationRaw | undefined {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as DivinationRaw) : undefined;
}

/** Plain text of a narrative, joining an epic's chapters when there is no single text. */
export function narrativePlainText(n: CurrentNarrative): string {
  return n.narrative || (n.narrative_parts ?? []).map(p => p.content).join(' ');
}

/** Map a /outlook/history row onto the Generator's narrative shape. */
export function historyItemToNarrative(item: HistoryItem): CurrentNarrative {
  return {
    ...item,
    astrology_used: item.astrology_context,
    divination_used: item.divination_context,
    divination_raw: toDivinationRaw(item.divination_raw),
    entities_used: item.entities_invoked,
    narrative: item.type === 'epic' ? undefined : item.content,
    narrative_parts: item.type === 'epic' ? toEpicChapters(item.content) : undefined,
  };
}

/**
 * Split a narrative into ritual sections on its bold Roman-numeral headers
 * (`**I. `, `**II. ` ...). Sections of 50 characters or fewer are dropped;
 * a preamble is folded into the first section, or stands alone when there
 * are no headers.
 */
export function parseSections(text: string): string[] {
  // Splitting on the captured group means odd-indexed parts are the
  // roman numerals (I, II, III…) and even-indexed parts are the bodies.
  // We re-prepend the header marker so the rendered text keeps its
  // bold section titles.
  const parts = text.split(/\*\*([IVX]+)\.\s/);
  const sections: string[] = [];
  for (let i = 1; i < parts.length; i += 2) {
    const combined = `**${parts[i]}. ${parts[i + 1] || ''}`;
    if (combined.trim().length > 50) sections.push(combined);
  }
  const preamble = parts[0]?.trim();
  if (preamble && sections.length > 0) {
    sections[0] = `${preamble}\n\n${sections[0]}`;
  } else if (preamble && sections.length === 0) {
    sections.push(preamble);
  }
  return sections;
}
