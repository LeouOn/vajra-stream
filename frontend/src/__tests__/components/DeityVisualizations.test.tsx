/**
 * The deity displays render the curated iconography (knowledge/iconography.json)
 * and nothing that contradicts it: SadhanaVisualization, FiveBuddhaMandala and
 * the Outlook RitualSummaryCard.
 */
import React from 'react';
import { describe, it, expect, vi, afterEach, beforeAll } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import SadhanaVisualization from '../../components/UI/SadhanaVisualization';
import FiveBuddhaMandala from '../../components/UI/FiveBuddhaMandala';
import RitualSummaryCard from '../../components/UI/outlook/RitualSummaryCard';
import { getDeityVisualization } from '../../lib/deityVisualizations';
import type { NarrativeMedia } from '../../components/UI/outlook/useNarrativeMedia';

vi.mock('../../components/UI/RitualVisualization', () => ({ default: () => null }));
vi.mock('../../utils/audioFeedback', () => ({ audioFeedback: { playTelemetry: vi.fn() } }));

beforeAll(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
});

let root: Root | null = null;
let container: HTMLDivElement | null = null;

async function render(node: React.ReactElement): Promise<HTMLDivElement> {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root?.render(node);
  });
  return container;
}

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

function iconographyText(el: HTMLElement): string {
  return el.querySelector('[data-testid="deity-iconography"]')?.textContent ?? '';
}

describe('SadhanaVisualization', () => {
  it('shows Green Tara with varada in the right hand and the refuge gesture in the left, never abhaya', async () => {
    const el = await render(<SadhanaVisualization deity={getDeityVisualization('green_tara')!} animate={false} />);
    const text = iconographyText(el);
    expect(text).toContain('Green body');
    expect(text).toContain('Right hand: varada mudra');
    expect(text).toContain('Left hand: refuge-granting gesture, holds the stem of a blue utpala lotus');
    expect(el.textContent).not.toMatch(/abhaya/i);
    expect(el.textContent).toContain('Śyāmatārā');
    expect(el.textContent).toContain('Air'); // karma family element
  });

  it('draws no sun disc where the curated seat has none (Amitabha)', async () => {
    const el = await render(<SadhanaVisualization deity={getDeityVisualization('amitabha')!} animate={false} />);
    expect(el.querySelector('ellipse[fill="url(#sun-disk-grad)"]')).toBeNull();
    expect(iconographyText(el)).toContain('Both hands: dhyana mudra, holds an alms bowl');
  });

  it('says Prajnaparamita’s principal gesture varies rather than asserting one', async () => {
    const el = await render(<SadhanaVisualization deity={getDeityVisualization('heart_sutra')!} animate={false} />);
    const text = iconographyText(el);
    expect(text).toContain('Principal hands: varies by lineage');
    expect(text).toContain('Upper right hand: holds a vajra');
    expect(text).not.toMatch(/dharmac/i);
  });

  it('gives the 88 Buddhas no individual iconography', async () => {
    const el = await render(<SadhanaVisualization deity={getDeityVisualization('88_buddhas')!} animate={false} />);
    expect(iconographyText(el)).toMatch(/no individually established iconography/);
    expect(el.textContent).not.toMatch(/añjali|prostration/i);
  });
});

describe('FiveBuddhaMandala', () => {
  it('labels each Buddha with the curated element and wisdom', async () => {
    const el = await render(<FiveBuddhaMandala size={400} />);
    const text = el.textContent ?? '';
    for (const name of ['Vairocana', 'Akṣobhya', 'Ratnasambhava', 'Amitābha', 'Amoghasiddhi']) {
      expect(text).toContain(name);
    }
    expect(text).toContain('Water · mirror-like');
    expect(text).toContain('Earth · equality');
    expect(text).toContain('some tantras exchange Vairocana and Akṣobhya');
  });

  it('shows the hovered Buddha’s curated colour, gesture and emblem', async () => {
    const el = await render(<FiveBuddhaMandala size={400} />);
    const groups = Array.from(el.querySelectorAll('svg g'));
    const akshobhya = groups.find((g) => g.textContent?.includes('Akṣobhya'));
    expect(akshobhya).toBeDefined();
    await act(async () => {
      akshobhya?.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
    });
    const hover = el.querySelector('[data-testid="dhyani-iconography"]')?.textContent ?? '';
    expect(hover).toContain('Blue body');
    expect(hover).toContain('Right hand: bhumisparsha mudra');
    expect(hover).toContain('emblem: the vajra');
    expect(el.textContent).toContain('Anger → mirror-like wisdom');
  });

  it('names the active family', async () => {
    const el = await render(<FiveBuddhaMandala activeFamily="karma" size={400} />);
    expect(el.textContent).toContain('This practice belongs to the karma family');
  });
});

describe('RitualSummaryCard', () => {
  const media: NarrativeMedia = {
    illustration: null,
    illustrationLoading: false,
    generateIllustration: async () => {},
    videoGenState: null,
    videoGenLoading: false,
    generateVideoFromNarrative: async () => {},
  };

  it('shows the curated form of the deity the entities name', async () => {
    const el = await render(
      <RitualSummaryCard
        narrative={{ entities_used: 'Avalokiteshvara (Chenrezig)', genre: 'healing' }}
        fallbackGenre="healing"
        media={media}
        onSave={() => {}}
        onReplay={() => {}}
      />,
    );
    const text = iconographyText(el);
    expect(text).toContain('Upper right hand: holds a crystal mala');
    expect(text).not.toMatch(/vase/i);
  });

  it('shows no deity for an entity without curated iconography', async () => {
    const el = await render(
      <RitualSummaryCard
        narrative={{ entities_used: 'Manjushri', genre: 'wisdom' }}
        fallbackGenre="wisdom"
        media={media}
        onSave={() => {}}
        onReplay={() => {}}
      />,
    );
    expect(el.querySelector('[data-testid="deity-iconography"]')).toBeNull();
    expect(el.textContent).toContain('Manjushri');
  });
});
