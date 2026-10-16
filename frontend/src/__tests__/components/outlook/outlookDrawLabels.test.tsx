/**
 * The tarot card and I Ching hexagram behind a narrative are draws, so the
 * Outlook oracle panels label them "drawn" (honest instrument, roadmap Phase 2).
 */
import React from 'react';
import { describe, it, expect, afterEach } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import EsotericSidebar from '../../../components/UI/outlook/EsotericSidebar';
import type { CurrentNarrative } from '../../../components/UI/outlook/outlookNarrative';

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

describe('Outlook draw labels', () => {
  it('labels the esoteric reading as drawn', () => {
    const narrative = {
      divination_raw: {
        tarot: { name: 'The Star', orientation: 'upright' },
        iching: { name: 'Peace' },
      },
    } as CurrentNarrative;
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root?.render(<EsotericSidebar narrative={narrative} />));

    const tags = container.querySelectorAll('[data-provenance="draw"]');
    expect(tags.length).toBeGreaterThan(0);
    expect(container.textContent).toContain('The Star');
  });
});
