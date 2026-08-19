/**
 * Unit tests for DharaniReciter — full unabbreviated mantras and recitation engine.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import DharaniReciter from '../../components/UI/DharaniReciter';

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

describe('DharaniReciter', () => {
  it('renders all 12 dharanis without abbreviated ellipsis strings', async () => {
    await act(async () => {
      root.render(<DharaniReciter />);
    });

    expect(container.textContent).toContain('Great Compassion Dharani');
    expect(container.textContent).toContain('Ushnisha Vijaya Dharani');
    expect(container.textContent).toContain('Vajrasattva 100-Syllable Mantra');
    expect(container.textContent).toContain('Cundi Dharani');
    expect(container.textContent).toContain('Medicine Buddha Dharani');
    expect(container.textContent).toContain('Amitabha Rebirth Dharani');
    expect(container.textContent).toContain('Green Tara Dharani');
    expect(container.textContent).toContain('Vajra Guru Mantra');
    expect(container.textContent).toContain('Heart Sutra Mantra');
    expect(container.textContent).toContain('Manjushri Wisdom Dharani');
    expect(container.textContent).toContain('Shurangama Heart Mantra & Opening');
    expect(container.textContent).toContain('Treasure Casket Seal Dharani');

    // Verify there are no ellipsis truncation marks in the rendered text
    expect(container.textContent).not.toContain('…');
  });

  it('displays full unabbreviated Sanskrit text for selected dharani', async () => {
    await act(async () => {
      root.render(<DharaniReciter />);
    });

    // Great Compassion full text phrases should be present
    expect(container.textContent).toContain('Namo Ratna-trayāya');
    expect(container.textContent).toContain('Āryāvalokiteśvarāya');
    expect(container.textContent).toContain('Sidhyantu Mantra-padāni Svāhā');
  });

  it('switches between Sanskrit, Chinese, and Tibetan scripts', async () => {
    await act(async () => {
      root.render(<DharaniReciter />);
    });

    const chineseBtn = Array.from(container.querySelectorAll('button')).find((b) =>
      b.textContent?.includes('Chinese')
    );
    expect(chineseBtn).toBeDefined();

    await act(async () => {
      chineseBtn?.click();
    });

    // Chinese Great Compassion Dharani text should be visible
    expect(container.textContent).toContain('南無喝囉怛那哆囉夜耶');
    expect(container.textContent).toContain('婆盧羯帝爍缽囉耶');
  });
});
