/**
 * Unit tests for GrimoirePanel — Esoteric Grimoire and Learning Library.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import GrimoirePanel from '../../components/UI/GrimoirePanel';

const mockGrimoireResults = [
  {
    id: 'planet_mercury',
    category: 'planets',
    title: '🪐 Mercury',
    subtitle: 'Throat Chakra · Air',
    description: 'Communication, intellect, trading, technology',
    planet: 'Mercury',
    metal: 'Quicksilver / Brass',
    element: 'Air',
    chakra: 'Throat',
    minerals: ['Agate', 'Fluorite'],
    herbs: ['Lavender', 'Peppermint'],
    rates: [8, 33, 44],
    frequencies: [141.27, 448.0],
  },
  {
    id: 'tarot_major_1',
    category: 'tarot',
    title: '🃏 The Magician',
    subtitle: 'Major Arcana · Air · Ruler: Mercury',
    description: 'Skill, diplomacy, focused willpower',
    keywords: ['willpower', 'manifestation', 'skill'],
    details: {
      arcana: 'major',
      upright: 'Skill, diplomacy, mastery of four elements.',
      reversed: 'Weakness of will, duplicity.',
      desc: 'A magus stands with wand raised to heaven and pointing to earth.',
    },
  },
];

global.fetch = vi.fn().mockImplementation((url: string) => {
  if (url.includes('/divination/grimoire/search')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ status: 'success', results: mockGrimoireResults, count: 2 }),
    });
  }
  return Promise.resolve({
    ok: true,
    json: async () => ({ status: 'success' }),
  });
});

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
});

describe('GrimoirePanel', () => {
  it('renders title, mode tabs, and category filter pills', async () => {
    await act(async () => {
      root.render(<GrimoirePanel />);
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(container.textContent).toContain('The Esoteric Grimoire & Learning Library');
    expect(container.textContent).toContain('Grimoire Explorer');
    expect(container.textContent).toContain('Esoteric Tutor');
    expect(container.textContent).toContain('Dharma Parables');

    // Check category pills
    expect(container.textContent).toContain('All Knowledge');
    expect(container.textContent).toContain('Planets');
    expect(container.textContent).toContain('Tarot Codex');
    expect(container.textContent).toContain('I Ching');
    expect(container.textContent).toContain('Mantras');
    expect(container.textContent).toContain('Sutras');
    expect(container.textContent).toContain('Frequencies');
  });

  it('displays fetched grimoire items and correspondences', async () => {
    await act(async () => {
      root.render(<GrimoirePanel />);
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(container.textContent).toContain('Mercury');
    expect(container.textContent).toContain('The Magician');
  });

  it('switches between Grimoire Explorer, Esoteric Tutor, and Dharma Parables tabs', async () => {
    await act(async () => {
      root.render(<GrimoirePanel />);
      await new Promise((r) => setTimeout(r, 50));
    });

    const tutorTabBtn = Array.from(container.querySelectorAll('button')).find((b) =>
      b.textContent?.includes('Esoteric Tutor')
    );
    expect(tutorTabBtn).toBeDefined();

    await act(async () => {
      tutorTabBtn?.click();
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(container.textContent).toContain('Learn astrology, tarot, and I Ching at your own pace');
  });
});
