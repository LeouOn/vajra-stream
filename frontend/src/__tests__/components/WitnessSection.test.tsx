/**
 * Witness images on a working folio (contract W2-2), against a mocked API:
 *   - "Render witness locally" posts {"backend":"local"} and follows the
 *     linked render operation from the store: queued, running with an honest
 *     elapsed count, then the folio's persisted local-render witness.
 *   - "Paint with hosted model" posts {"backend":"hosted"} and shows the folio it returns.
 *   - Hosted witnesses from before wave 2 (base64 image_data_url) still display.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import { WorkingFolioCard, type WorkingResult } from '../../components/CommandCenter/RenderMessageWidgets';
import { useOperationsStore } from '../../stores/operationsStore';
import type { Operation } from '../../types/operations';

const NOW = Date.parse('2026-10-15T12:00:00Z');
const WID = 'wrk_1';

const FOLIO: WorkingResult = {
  working_id: WID,
  intention: 'May the waters be clean',
  target: 'the watershed',
  rate_values: [12, 44, 70],
  image_prompt: 'a clear river at dawn',
};

const LOCAL_WITNESS = {
  status: 'ok',
  source: 'local-render',
  operation_id: 'op-1',
  image_url: '/api/v1/render/jobs/op-1/image',
  seed: 77,
  seed_provenance: 'draw',
  width: 1024,
  height: 1024,
  prompt: 'a clear river at dawn',
};

function renderOp(overrides: Partial<Operation> & Pick<Operation, 'id'>): Operation {
  return {
    kind: 'render',
    status: 'queued',
    title: 'witness render',
    working_id: WID,
    params: { prompt: 'a clear river at dawn', purpose: 'witness', working_id: WID, seed: 77 },
    provenance: { seed: 'draw' },
    result: null,
    error: null,
    created_at: '2026-10-15T11:58:00+00:00',
    started_at: null,
    finished_at: null,
    elapsed_seconds: null,
    ...overrides,
  };
}

type Reply = { status: number; body: unknown };

interface Routes {
  linked: () => Reply;
  witness: (body: unknown) => Reply;
  folio: () => Reply;
}

let routes: Routes;
let fetchSpy: ReturnType<typeof vi.fn>;
let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  useOperationsStore.getState().clear();
  vi.spyOn(Date, 'now').mockReturnValue(NOW);
  routes = {
    linked: () => ({ status: 200, body: { operations: [], count: 0 } }),
    witness: (body) => {
      const backend = (body as { backend?: string } | null)?.backend;
      if (backend === 'hosted') {
        return {
          status: 200,
          body: { ...FOLIO, witness: { status: 'ok', image_data_url: 'data:image/png;base64,SE9TVA==', model: 'flux' } },
        };
      }
      return { status: 202, body: { working_id: WID, operation: renderOp({ id: 'op-1' }) } };
    },
    folio: () => ({ status: 200, body: { ...FOLIO, witness: LOCAL_WITNESS } }),
  };
  fetchSpy = vi.fn((url: string, init?: RequestInit) => {
    let reply: Reply = { status: 404, body: { detail: 'not found' } };
    if (url.startsWith('/api/v1/operations?')) reply = routes.linked();
    else if (url === `/api/v1/operator/workings/${WID}/witness` && init?.method === 'POST') {
      reply = routes.witness(init.body ? JSON.parse(String(init.body)) : null);
    } else if (url === `/api/v1/operator/workings/${WID}` && !init?.method) reply = routes.folio();
    return Promise.resolve({
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: async () => reply.body,
    } as Response);
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

async function renderFolio(initial: WorkingResult, autoManifest = false): Promise<void> {
  await act(async () => {
    root.render(
      <ConfigProvider>
        <WorkingFolioCard initial={initial} autoManifest={autoManifest} showInstrument={false} />
      </ConfigProvider>,
    );
  });
  await flush();
}

function q<T extends Element = HTMLElement>(testId: string): T | null {
  return container.querySelector<T>(`[data-testid="${testId}"]`);
}

async function click(testId: string): Promise<void> {
  const el = q<HTMLButtonElement>(testId);
  if (!el) throw new Error(`no ${testId}`);
  await act(async () => {
    el.click();
  });
  await flush();
}

function witnessPosts(): Array<{ body: unknown; headers: unknown }> {
  return fetchSpy.mock.calls
    .filter((c) => String(c[0]).endsWith('/witness'))
    .map((c) => {
      const init = c[1] as RequestInit;
      return { body: init.body ? JSON.parse(String(init.body)) : null, headers: init.headers };
    });
}

describe('WitnessSection on a working folio', () => {
  it('still shows a hosted witness stored as base64 (from before local renders)', async () => {
    await renderFolio({
      ...FOLIO,
      witness: { status: 'ok', image_data_url: 'data:image/png;base64,QQ==', model: 'gpt-image-1' },
    });
    const plate = q('witness-plate');
    expect(plate?.textContent).toContain('Manifestation still');
    expect(plate?.querySelector('img')?.getAttribute('src')).toBe('data:image/png;base64,QQ==');
    expect(q('witness-source')?.textContent).toBe('hosted model · gpt-image-1');
    expect(q('witness-seed')).toBeNull();
    expect(q('witness-local')?.textContent).toBe('Render a new witness locally');
  });

  it('reads linked renders for this working from the ledger on open', async () => {
    await renderFolio(FOLIO);
    const urls = fetchSpy.mock.calls.map((c) => String(c[0]));
    expect(urls).toContain(`/api/v1/operations?kind=render&working_id=${WID}&limit=10`);
    expect(witnessPosts()).toEqual([]); // no autoManifest here
  });

  it('renders locally: posts {"backend":"local"}, then follows the operation to the stored witness', async () => {
    await renderFolio(FOLIO);
    expect(q('witness-local')?.textContent).toBe('Render witness locally');
    await click('witness-local');

    expect(witnessPosts()).toEqual([
      { body: { backend: 'local' }, headers: { 'Content-Type': 'application/json' } },
    ]);
    expect(q('witness-render')?.dataset.status).toBe('queued');
    expect(q('witness-render')?.textContent).toContain('Waiting its turn');
    expect(q<HTMLButtonElement>('witness-local')?.disabled).toBe(true);

    await act(async () => {
      useOperationsStore.getState().upsert(
        renderOp({ id: 'op-1', status: 'running', started_at: new Date(NOW - 95_000).toISOString() }),
      );
    });
    expect(q('witness-render')?.dataset.status).toBe('running');
    expect(q('witness-elapsed')?.textContent).toContain('1m 35s since start');
    expect(q('witness-elapsed')?.textContent).toContain('counted on this device');
    expect(container.querySelector('[role="progressbar"]')).toBeNull();

    await act(async () => {
      useOperationsStore.getState().upsert(
        renderOp({
          id: 'op-1',
          status: 'success',
          started_at: '2026-10-15T11:58:00+00:00',
          finished_at: '2026-10-15T11:59:00+00:00',
          elapsed_seconds: 55.2,
          result: { image_url: '/api/v1/render/jobs/op-1/image', width: 1024, height: 1024, seed: 77 },
        }),
      );
    });
    await flush();

    // The folio is re-read; its witness block now points at the render.
    expect(fetchSpy.mock.calls.some((c) => c[0] === `/api/v1/operator/workings/${WID}`)).toBe(true);
    expect(q('witness-render')).toBeNull();
    const plate = q('witness-plate');
    expect(plate?.textContent).toContain('local render');
    expect(plate?.querySelector('img')?.getAttribute('src')).toBe('/api/v1/render/jobs/op-1/image');
    const facts = q('witness-facts')?.textContent ?? '';
    expect(facts).toContain('1024×1024 px (measured)');
    expect(q('witness-seed')?.textContent).toBe('seed 77 (drawn)');
    expect(q<HTMLButtonElement>('witness-local')?.disabled).toBe(false);
  });

  it('shows the finished render from the operation while the folio has not caught up', async () => {
    routes.folio = () => ({ status: 200, body: FOLIO }); // listener hasn't written yet
    await renderFolio(FOLIO);
    await click('witness-local');
    await act(async () => {
      useOperationsStore.getState().upsert(
        renderOp({
          id: 'op-1',
          status: 'success',
          elapsed_seconds: 147,
          finished_at: '2026-10-15T12:00:00+00:00',
          result: { image_url: '/api/v1/render/jobs/op-1/image', width: 1080, height: 2340, seed: 77 },
        }),
      );
    });
    await flush();
    const live = q('witness-render');
    expect(live?.dataset.status).toBe('success');
    expect(live?.querySelector('img')?.getAttribute('src')).toBe('/api/v1/render/jobs/op-1/image');
    expect(live?.textContent).toContain('1080×2340 px (measured)');
    expect(live?.textContent).toContain('took 2m 27s (measured)');
    expect(q('witness-render-seed')?.textContent).toBe('seed 77 (drawn)');
  });

  it('paints with the hosted model: posts {"backend":"hosted"} and shows the returned folio', async () => {
    await renderFolio(FOLIO);
    await click('witness-hosted');
    expect(witnessPosts()).toEqual([
      { body: { backend: 'hosted' }, headers: { 'Content-Type': 'application/json' } },
    ]);
    expect(q('witness-plate')?.querySelector('img')?.getAttribute('src')).toBe('data:image/png;base64,SE9TVA==');
    expect(q('witness-source')?.textContent).toBe('hosted model · flux');
    expect(q('witness-render')).toBeNull();
  });

  it('labels a chosen seed on a stored local witness', async () => {
    await renderFolio({ ...FOLIO, witness: { ...LOCAL_WITNESS, seed: 5, seed_provenance: 'record' } });
    expect(q('witness-seed')?.textContent).toBe('seed 5 (chosen)');
  });

  it('shows the true-sky composite, its sky caption facts and a link to the plain scene', async () => {
    await renderFolio({
      ...FOLIO,
      witness: {
        ...LOCAL_WITNESS,
        image_url: '/api/v1/gallery/sky/op-7/image',
        scene_image_url: '/api/v1/render/jobs/op-7/image',
        caption_facts: [
          { label: 'Moon in the sky', value: 'altitude 23.4°, azimuth 201.7° (SSW)', provenance: 'computed' },
          { label: 'Sky overlay', value: 'Moon drawn at 5× apparent size', provenance: 'computed' },
        ],
      },
    });
    const plate = q('witness-plate');
    expect(plate?.querySelector('img')?.getAttribute('src')).toBe('/api/v1/gallery/sky/op-7/image');
    expect(q('witness-scene-link')?.querySelector('a')?.getAttribute('href')).toBe('/api/v1/render/jobs/op-7/image');
    const caption = q('image-caption-facts')?.textContent ?? '';
    expect(caption).toContain('Moon in the sky');
    expect(caption).toContain('Moon drawn at 5× apparent size');
  });

  it('shows a failed local render from the folio', async () => {
    await renderFolio({ ...FOLIO, witness: { status: 'error', operation_id: 'op-9', error: 'ComfyUI not reachable' } });
    expect(q('witness-error')?.textContent).toBe('Local witness render failed: ComfyUI not reachable');
    expect(q('witness-plate')).toBeNull();
  });

  it('shows a refused request plainly', async () => {
    routes.witness = () => ({ status: 503, body: { detail: 'Render backend is not reachable' } });
    await renderFolio(FOLIO);
    await click('witness-local');
    expect(q('witness-request-error')?.textContent).toBe('Render backend is not reachable');
    expect(q('witness-render')).toBeNull();
  });

  it('picks up a witness render already running and offers Cancel', async () => {
    routes.linked = () => ({
      status: 200,
      body: {
        operations: [renderOp({ id: 'op-2', status: 'running', started_at: new Date(NOW - 10_000).toISOString() })],
        count: 1,
      },
    });
    await renderFolio(FOLIO);
    expect(q('witness-render')?.dataset.status).toBe('running');
    expect(q('witness-elapsed')?.textContent).toContain('10s since start');
    expect(q('witness-render')?.textContent).toContain('Cancel');
  });

  it('ignores sigil renders linked to the same working', async () => {
    routes.linked = () => ({
      status: 200,
      body: {
        operations: [renderOp({ id: 'sig', status: 'running', params: { purpose: 'sigil' }, started_at: new Date(NOW).toISOString() })],
        count: 1,
      },
    });
    await renderFolio(FOLIO);
    expect(q('witness-render')).toBeNull();
  });

  describe('autoManifest (new working shown in chat)', () => {
    it('asks once with no body, letting the server pick the backend', async () => {
      await renderFolio(FOLIO, true);
      expect(witnessPosts()).toEqual([{ body: null, headers: undefined }]);
      expect(q('witness-render')?.dataset.status).toBe('queued');
    });

    it('does not queue a second render when one is already in flight', async () => {
      routes.linked = () => ({
        status: 200,
        body: { operations: [renderOp({ id: 'op-2', status: 'queued' })], count: 1 },
      });
      await renderFolio(FOLIO, true);
      expect(witnessPosts()).toEqual([]);
      expect(q('witness-render')?.dataset.status).toBe('queued');
    });

    it('does not ask when the folio already has an image', async () => {
      await renderFolio({ ...FOLIO, witness: LOCAL_WITNESS }, true);
      expect(witnessPosts()).toEqual([]);
    });
  });
});
