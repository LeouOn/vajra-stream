/**
 * Gallery against a mocked gallery API (no server):
 *   - a lazy-loaded thumbnail per item, its URL resolved through apiUrl
 *   - source filter asks the backend (`source=`), with per-source counts
 *   - skipped (undecodable) files are counted, never shown as tiles
 *   - the detail drawer: prompt, seed labeled drawn/chosen, links to the
 *     operation in the Ledger and the folio in Workings
 *   - "not recorded" instead of an invented prompt for pre-sidecar saves
 *   - paging appends; a render finishing elsewhere reloads the grid
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import Gallery from '../../components/Operations/Gallery';
import { useOperationsStore } from '../../stores/operationsStore';
import type { GalleryItem, GalleryPage } from '../../types/gallery';
import type { Operation } from '../../types/operations';

function item(overrides: Partial<GalleryItem> & Pick<GalleryItem, 'id' | 'source'>): GalleryItem {
  return {
    created_at: '2026-10-15T10:00:00+00:00',
    prompt: null,
    width: 1024,
    height: 1024,
    media_type: 'image/png',
    bytes: 2048,
    image_url: `/api/v1/gallery/hosted/${overrides.id}.png`,
    purpose: null,
    links: { operation_id: null, working_id: null },
    origin: {},
    settings: {},
    ...overrides,
  };
}

const RENDER = item({
  id: 'render:op1',
  source: 'local-render',
  prompt: 'a quiet lake at dawn',
  image_url: '/api/v1/render/jobs/op1/image',
  purpose: 'witness',
  links: { operation_id: 'op1', working_id: 'wrk_abc123' },
  origin: { seed: 42, seed_provenance: 'draw', backend_execution_seconds: 77.2, sha256: 'ab'.repeat(32) },
  settings: { preset: 'square-1024', backend: 'comfyui-qwen-image-2.1', reference_id: null },
});
const HOSTED_OLD = item({
  id: 'hosted:img_1785633576_cb2a7bbc.jpg',
  source: 'hosted',
  media_type: 'image/jpeg',
  image_url: '/api/v1/gallery/hosted/img_1785633576_cb2a7bbc.jpg',
  origin: { sidecar: false },
});
const WITNESS = item({
  id: 'witness:wrk_def456',
  source: 'witness',
  prompt: 'a stupa under stars',
  image_url: '/api/v1/gallery/witness/wrk_def456/image',
  purpose: 'witness',
  links: { operation_id: null, working_id: 'wrk_def456' },
  origin: { provider: 'openrouter', model: 'google/gemini-3.1-flash-lite-image' },
});

function pageOf(items: GalleryItem[], overrides: Partial<GalleryPage> = {}): GalleryPage {
  return {
    items,
    total: items.length,
    offset: 0,
    limit: 48,
    counts: { 'local-render': 1, hosted: 1, witness: 1 },
    skipped: [],
    ...overrides,
  };
}

let respond: (url: string) => { status: number; body: unknown };
let fetchSpy: ReturnType<typeof vi.fn>;
let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  useOperationsStore.getState().clear();
  respond = () => ({
    status: 200,
    body: pageOf([RENDER, HOSTED_OLD, WITNESS], {
      skipped: [{ source: 'hosted', ref: 'img_1700000000_00000001.png', reason: 'only 15 bytes, too small to be an image' }],
    }),
  });
  fetchSpy = vi.fn((url: string) => {
    const { status, body } = respond(url);
    return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body } as Response);
  });
  vi.stubGlobal('fetch', fetchSpy);
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

async function flush(): Promise<void> {
  await act(async () => {
    await new Promise((r) => setTimeout(r, 0));
  });
}

async function renderGallery(): Promise<void> {
  await act(async () => {
    root.render(
      <ConfigProvider>
        <MemoryRouter>
          <Gallery />
        </MemoryRouter>
      </ConfigProvider>,
    );
  });
  await flush();
}

function tiles(): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>('[data-testid="gallery-tile"]'));
}

function galleryCalls(): string[] {
  return fetchSpy.mock.calls.map((c) => String(c[0])).filter((u) => u.startsWith('/api/v1/gallery'));
}

function lastGalleryCall(): string | undefined {
  const calls = galleryCalls();
  return calls[calls.length - 1];
}

async function openTile(index: number): Promise<HTMLElement> {
  await act(async () => {
    tiles()[index].click();
  });
  await flush();
  const detail = document.querySelector<HTMLElement>('[data-testid="gallery-detail"]');
  if (!detail) throw new Error('detail drawer did not open');
  return detail;
}

describe('Gallery', () => {
  it('shows a lazy thumbnail per item, resolved through apiUrl', async () => {
    await renderGallery();
    expect(galleryCalls()[0]).toBe('/api/v1/gallery?offset=0&limit=48');
    expect(tiles().map((t) => t.dataset.source)).toEqual(['local-render', 'hosted', 'witness']);
    const imgs = tiles().map((t) => t.querySelector('img'));
    expect(imgs.map((i) => i?.getAttribute('src'))).toEqual([
      '/api/v1/render/jobs/op1/image',
      '/api/v1/gallery/hosted/img_1785633576_cb2a7bbc.jpg',
      '/api/v1/gallery/witness/wrk_def456/image',
    ]);
    expect(imgs.every((i) => i?.getAttribute('loading') === 'lazy')).toBe(true);
    expect(container.textContent).toContain('3 images');
  });

  it('counts skipped files without showing them as tiles', async () => {
    await renderGallery();
    const skipped = container.querySelector('[data-testid="gallery-skipped"]');
    expect(skipped?.textContent).toContain('1 file skipped: not decodable images');
    expect(skipped?.textContent).toContain('img_1700000000_00000001.png');
    expect(skipped?.textContent).toContain('too small');
    expect(tiles()).toHaveLength(3);
  });

  it('a broken image load becomes a calm placeholder', async () => {
    await renderGallery();
    const img = tiles()[1].querySelector('img');
    await act(async () => {
      img?.dispatchEvent(new Event('error'));
    });
    expect(tiles()[1].querySelector('img')).toBeNull();
    expect(tiles()[1].textContent).toContain('could not load');
  });

  it('filters by source through the backend, with counts in the labels', async () => {
    await renderGallery();
    const hostedOption = Array.from(container.querySelectorAll('label')).find((l) =>
      l.textContent?.startsWith('Hosted'),
    );
    expect(hostedOption?.textContent).toBe('Hosted (1)');
    respond = () => ({ status: 200, body: pageOf([HOSTED_OLD]) });
    await act(async () => {
      hostedOption?.querySelector('input')?.click();
    });
    await flush();
    expect(lastGalleryCall()).toBe('/api/v1/gallery?source=hosted&offset=0&limit=48');
    expect(tiles().map((t) => t.dataset.source)).toEqual(['hosted']);
  });

  it('opens a render with its prompt, drawn seed and links to the Ledger and the folio', async () => {
    await renderGallery();
    const detail = await openTile(0);
    expect(detail.querySelector('[data-testid="gallery-prompt"]')?.textContent).toBe('a quiet lake at dawn');
    const seed = detail.querySelector('[data-testid="gallery-seed"]');
    expect(seed?.textContent).toContain('seed 42 (drawn)');
    expect(seed?.querySelector('[data-provenance="draw"]')).not.toBeNull();
    expect(detail.textContent).toContain('square-1024');
    expect(detail.textContent).toContain('1024×1024 (measured)');
    expect(detail.textContent).not.toContain('reference id'); // null settings are left out
    expect(detail.querySelector('[data-testid="gallery-link-operation"]')?.getAttribute('href')).toBe(
      '/operations/ledger?op=op1',
    );
    expect(detail.querySelector('[data-testid="gallery-link-working"]')?.getAttribute('href')).toBe(
      '/workings?open=wrk_abc123',
    );
  });

  it('says a pre-sidecar prompt was not recorded instead of inventing one', async () => {
    await renderGallery();
    const detail = await openTile(1);
    expect(detail.querySelector('[data-testid="gallery-prompt"]')?.textContent).toBe(
      'Not recorded (saved before sidecars existed).',
    );
    expect(detail.querySelector('[data-testid="gallery-seed"]')).toBeNull();
    expect(detail.querySelector('[data-testid="gallery-link-operation"]')).toBeNull();
  });

  it('shows provider and model for a hosted witness and links its folio', async () => {
    await renderGallery();
    const detail = await openTile(2);
    expect(detail.textContent).toContain('openrouter');
    expect(detail.textContent).toContain('google/gemini-3.1-flash-lite-image');
    expect(detail.querySelector('[data-testid="gallery-link-working"]')?.getAttribute('href')).toBe(
      '/workings?open=wrk_def456',
    );
  });

  it('loads more pages and appends them', async () => {
    respond = () => ({ status: 200, body: pageOf([RENDER], { total: 2 }) });
    await renderGallery();
    const more = container.querySelector<HTMLButtonElement>('[data-testid="gallery-more"]');
    expect(more?.textContent).toContain('1 left');
    respond = () => ({ status: 200, body: pageOf([WITNESS], { total: 2, offset: 1 }) });
    await act(async () => {
      more?.click();
    });
    await flush();
    expect(lastGalleryCall()).toBe('/api/v1/gallery?offset=1&limit=48');
    expect(tiles()).toHaveLength(2);
    expect(container.querySelector('[data-testid="gallery-more"]')).toBeNull();
  });

  it('reports a failed load', async () => {
    respond = () => ({ status: 500, body: { detail: 'disk unavailable' } });
    await renderGallery();
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('disk unavailable');
    expect(tiles()).toHaveLength(0);
  });

  it('says so plainly when there are no images', async () => {
    respond = () => ({ status: 200, body: pageOf([], { counts: { 'local-render': 0, hosted: 0, witness: 0 } }) });
    await renderGallery();
    expect(container.querySelector('[data-testid="gallery-empty"]')?.textContent).toContain('No images yet');
  });

  it('reloads when a render finishes elsewhere', async () => {
    await renderGallery();
    const before = galleryCalls().length;
    const finished: Operation = {
      id: 'op2',
      kind: 'render',
      status: 'success',
      title: 'render',
      working_id: null,
      params: null,
      provenance: null,
      result: null,
      error: null,
      created_at: '2026-10-15T11:00:00+00:00',
      started_at: '2026-10-15T11:00:01+00:00',
      finished_at: '2026-10-15T11:01:00+00:00',
      elapsed_seconds: 59,
    };
    await act(async () => {
      useOperationsStore.getState().upsert(finished);
    });
    await flush();
    expect(galleryCalls().length).toBe(before + 1);
  });
});
