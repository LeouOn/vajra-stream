/**
 * Images never carry numbers; the real values are captioned beside them with
 * their provenance (docs/DEVELOPMENT_ROADMAP.md, "the honest instrument").
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import ImageCaptionFacts from '../../components/UI/ImageCaptionFacts';
import { toCaptionFacts } from '../../lib/captionFacts';
import { WorkingFolioCard, type WorkingResult } from '../../components/CommandCenter/RenderMessageWidgets';
import { useOperationsStore } from '../../stores/operationsStore';

const FACTS = [
  { label: 'Sealed', value: '2026-08-15T12:00:00+00:00', provenance: 'record' },
  { label: 'Moon at sealing', value: '10% illuminated, waxing crescent', provenance: 'computed' },
  { label: 'Saka Dawa Duchen', value: '2027-05-21', provenance: 'computed' },
];

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function q(testId: string): HTMLElement | null {
  return container.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
}

describe('toCaptionFacts', () => {
  it('keeps well-formed facts and drops anything it would have to guess', () => {
    expect(
      toCaptionFacts([
        ...FACTS,
        { label: 'Count', value: 3, provenance: 'record' },
        { label: 'Bad', value: 'x', provenance: 'measured' },
        { value: 'no label', provenance: 'record' },
        null,
        'Moon 44%',
      ]),
    ).toEqual([...FACTS, { label: 'Count', value: '3', provenance: 'record' }]);
    expect(toCaptionFacts(undefined)).toEqual([]);
    expect(toCaptionFacts({ label: 'x' })).toEqual([]);
  });
});

describe('ImageCaptionFacts', () => {
  it('shows each value with its provenance label', () => {
    act(() => root.render(<ImageCaptionFacts facts={FACTS} />));
    const dl = q('image-caption-facts');
    expect(dl).not.toBeNull();
    const text = dl?.textContent ?? '';
    expect(text).toContain('Moon at sealing');
    expect(text).toContain('10% illuminated, waxing crescent');
    expect(text).toContain('2027-05-21');
    const tags = Array.from(dl?.querySelectorAll('span[data-provenance]') ?? []).map((t) => t.textContent);
    expect(tags).toEqual(['record', 'computed', 'computed']);
  });

  it('labels a draw as drawn', () => {
    act(() => root.render(<ImageCaptionFacts facts={[{ label: 'Seed', value: '77', provenance: 'draw' }]} />));
    expect(container.querySelector('span[data-provenance="draw"]')?.textContent).toBe('drawn');
  });

  it('renders nothing without facts', () => {
    act(() => root.render(<ImageCaptionFacts facts={[]} />));
    expect(q('image-caption-facts')).toBeNull();
    act(() => root.render(<ImageCaptionFacts facts={undefined} />));
    expect(q('image-caption-facts')).toBeNull();
  });
});

describe('WitnessSection captions', () => {
  it('captions a persisted witness with its facts', async () => {
    useOperationsStore.getState().clear();
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({ ok: true, status: 200, json: async () => ({ operations: [], count: 0 }) } as Response),
      ),
    );
    const folio: WorkingResult = {
      working_id: 'wrk_caption',
      intention: 'May the waters be clean',
      target: 'the watershed',
      rate_values: [12, 44, 70],
      witness: {
        status: 'ok',
        source: 'local-render',
        operation_id: 'op-1',
        image_url: '/api/v1/render/jobs/op-1/image',
        width: 1024,
        height: 1024,
        caption_facts: FACTS,
      },
    };
    await act(async () => {
      root.render(
        <ConfigProvider>
          <WorkingFolioCard initial={folio} showInstrument={false} />
        </ConfigProvider>,
      );
    });
    const caption = q('witness-plate')?.querySelector('[data-testid="image-caption-facts"]');
    expect(caption?.textContent).toContain('Saka Dawa Duchen');
    expect(caption?.textContent).toContain('10% illuminated, waxing crescent');
  });
});
