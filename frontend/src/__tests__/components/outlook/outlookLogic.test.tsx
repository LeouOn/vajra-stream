/**
 * Outlook extracted logic: narrative helpers, model options, the defensive
 * list unwrap, the saved-ritual archive and the ritual reveal hook.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

vi.mock('../../../components/UI/outlook/ritualAudio', () => ({
  playSectionChime: vi.fn(),
  playDedicationBell: vi.fn(),
}));

import {
  parseSections, historyItemToNarrative, narrativePlainText, toEpicChapters,
  type CurrentNarrative,
} from '../../../components/UI/outlook/outlookNarrative';
import { buildOutlookModelOptions } from '../../../components/UI/outlook/useOutlookModels';
import { unwrapList } from '../../../components/UI/outlook/useOutlookUniverse';
import {
  appendSavedRitual, buildSavedRitual, loadSavedRituals,
} from '../../../components/UI/outlook/savedRituals';
import { useRitualReveal, REVEAL_STEP_MS } from '../../../components/UI/outlook/useRitualReveal';
import { playDedicationBell, playSectionChime } from '../../../components/UI/outlook/ritualAudio';

const BODY = 'Light pours from the lapis heaven across every valley and every sleeping town.';

describe('parseSections', () => {
  it('splits on bold roman headers and folds the preamble into the first section', () => {
    const s = parseSections(`Opening words.\n\n**I. Invocatio** ${BODY}\n**II. Dedicatio** ${BODY}`);
    expect(s).toHaveLength(2);
    expect(s[0].startsWith('Opening words.\n\n**I. Invocatio**')).toBe(true);
    expect(s[1].startsWith('**II. Dedicatio**')).toBe(true);
  });

  it('drops sections of 50 characters or fewer', () => {
    expect(parseSections(`**I. Short** tiny\n**II. Long** ${BODY}`)).toEqual([`**II. Long** ${BODY}`]);
  });

  it('returns the preamble alone when there are no headers, and nothing for empty text', () => {
    expect(parseSections('Just a paragraph.')).toEqual(['Just a paragraph.']);
    expect(parseSections('')).toEqual([]);
  });
});

describe('narrative helpers', () => {
  it('normalizes an epic history row into chapters', () => {
    const n = historyItemToNarrative({
      id: 3, type: 'epic', genre: 'victory',
      content: [{ title: 'Dawn', content: 'one' }, null, { chapter: 9, content: 'two' }] as unknown as string,
      astrology_context: 'Sun', divination_context: 'Tower', entities_invoked: 'Tara',
      divination_raw: ['not', 'an', 'object'],
    });
    expect(n.narrative).toBeUndefined();
    expect(n.narrative_parts).toEqual([
      { chapter: 1, title: 'Dawn', content: 'one' },
      { chapter: 9, title: 'Chapter 2', content: 'two' },
    ]);
    expect(n.astrology_used).toBe('Sun');
    expect(n.divination_used).toBe('Tower');
    expect(n.entities_used).toBe('Tara');
    expect(n.divination_raw).toBeUndefined();
    expect(narrativePlainText(n)).toBe('one two');
  });

  it('keeps a single row as narrative text', () => {
    const n = historyItemToNarrative({ type: 'single', content: 'Plain.', divination_raw: { tarot: { name: 'Star' } } });
    expect(n.narrative).toBe('Plain.');
    expect(n.narrative_parts).toBeUndefined();
    expect(n.divination_raw?.tarot?.name).toBe('Star');
    expect(toEpicChapters('x')).toBeUndefined();
  });
});

describe('buildOutlookModelOptions', () => {
  it('orders auto, featured, default, healthy API providers, LM Studio, local — de-duplicated', () => {
    const opts = buildOutlookModelOptions(
      {
        api: ['deepseek (deepseek-chat)', 'openai (gpt-4o)', 'not a provider entry', 'mystery (m-1)'],
        lm_studio: ['qwen'],
        local: ['llama.gguf'],
      },
      { openai: false },
      'nvidia/default:free',
      [
        { id: 'a/b:free', name: 'AB', is_free: true },
        { id: 'c/d', name: 'CD', is_free: false },
        { id: 'a/b:free', name: 'AB again', is_free: true },
      ],
    );
    expect(opts.map((o) => o.value)).toEqual([
      '', 'a/b:free', 'c/d', 'nvidia/default:free', 'deepseek:deepseek-chat', 'mystery:m-1', 'lm_studio:qwen', 'local:llama.gguf',
    ]);
    expect(opts[1].label).toBe('🆓 AB (FREE)');
    expect(opts[2].label).toBe('💳 CD (paid)');
    expect(opts[4].label).toBe('🐉 DeepSeek (deepseek-chat)');
    expect(opts[5].label).toBe('✨ mystery (m-1)');
  });

  it('skips the default entry when it is already featured', () => {
    const opts = buildOutlookModelOptions({}, {}, 'a/b:free', [{ id: 'a/b:free', name: 'AB', is_free: true }]);
    expect(opts.map((o) => o.value)).toEqual(['', 'a/b:free']);
  });
});

describe('unwrapList', () => {
  it('accepts bare arrays and {items} / {data} envelopes, else []', () => {
    expect(unwrapList<number>([1, 2])).toEqual([1, 2]);
    expect(unwrapList<number>({ items: [3] })).toEqual([3]);
    expect(unwrapList<number>({ data: [4] })).toEqual([4]);
    expect(unwrapList<number>({})).toEqual([]);
    expect(unwrapList<number>(null)).toEqual([]);
  });
});

describe('saved ritual archive', () => {
  beforeEach(() => window.localStorage.clear());

  it('prepends entries, falls back to the form genre, and caps at 50', () => {
    const narrative: CurrentNarrative & { narrative: string } = { narrative: 'text', entities_used: 'Tara' };
    const entry = buildSavedRitual(narrative, 'dharani');
    expect(entry).toMatchObject({ genre: 'dharani', narrative: 'text', entities: 'Tara', model: null, provider: null, divinationRaw: null });
    expect(entry.id).toMatch(/^ritual_\d+_[a-z0-9]{1,6}$/);

    for (let i = 0; i < 52; i += 1) appendSavedRitual({ ...entry, id: `r${i}` });
    const saved = loadSavedRituals();
    expect(saved).toHaveLength(50);
    expect(saved[0].id).toBe('r51');
  });

  it('reads a corrupt archive as empty', () => {
    window.localStorage.setItem('vajra.savedRituals.v1', '{not json');
    expect(loadSavedRituals()).toEqual([]);
  });
});

describe('useRitualReveal', () => {
  let container: HTMLDivElement;
  let root: Root;
  let latest: { sections: string[]; revealedSections: number } = { sections: [], revealedSections: 0 };

  function Harness({ narrative }: { narrative: CurrentNarrative | null }) {
    latest = useRitualReveal(narrative);
    return null;
  }

  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(playSectionChime).mockClear();
    vi.mocked(playDedicationBell).mockClear();
    container = document.createElement('div');
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    vi.useRealTimers();
  });

  const text = `**I. One** ${BODY}\n**II. Two** ${BODY}\n**III. Three** ${BODY}`;

  it('reveals one section per step, chiming then ringing the bell on the last', () => {
    act(() => root.render(<Harness narrative={{ narrative: text }} />));
    expect(latest.sections).toHaveLength(3);
    expect(latest.revealedSections).toBe(0);

    act(() => { vi.advanceTimersByTime(REVEAL_STEP_MS); });
    expect(latest.revealedSections).toBe(1);
    act(() => { vi.advanceTimersByTime(REVEAL_STEP_MS * 2); });
    expect(latest.revealedSections).toBe(3);
    expect(playSectionChime).toHaveBeenCalledTimes(2);
    expect(playDedicationBell).toHaveBeenCalledTimes(1);
  });

  it('restarts for a new narrative and cancels pending reveals on unmount', () => {
    act(() => root.render(<Harness narrative={{ narrative: text }} />));
    act(() => { vi.advanceTimersByTime(REVEAL_STEP_MS); });
    expect(latest.revealedSections).toBe(1);

    act(() => root.render(<Harness narrative={{ narrative: text }} />));
    expect(latest.revealedSections).toBe(0);

    act(() => root.unmount());
    root = createRoot(container);
    vi.advanceTimersByTime(REVEAL_STEP_MS * 5);
    expect(playDedicationBell).not.toHaveBeenCalled();
  });

  it('reveals nothing for a narrative without text', () => {
    act(() => root.render(<Harness narrative={{ narrative_parts: [] }} />));
    act(() => { vi.advanceTimersByTime(REVEAL_STEP_MS * 3); });
    expect(latest.sections).toEqual([]);
    expect(latest.revealedSections).toBe(0);
  });
});
