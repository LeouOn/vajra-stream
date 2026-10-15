/**
 * RenderStudio against a mocked render API (no server):
 *   - submits the right POST /render/jobs body (seed omitted when empty)
 *   - labels seeds "(drawn)" vs "(chosen)" from provenance.seed
 *   - shows measured image size and the image via apiUrl
 *   - running jobs count from started_at; cancel posts to the generic operations cancel route
 *   - reference images: client-side checks, multipart upload, reference_id in the job
 *   - says plainly when ComfyUI (or the render service) is unreachable
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { ConfigProvider } from 'antd';

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
}));

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>();
  return { ...actual, message: { ...actual.message, ...toast } };
});

import RenderStudio from '../../components/Operations/RenderStudio';
import { useOperationsStore } from '../../stores/operationsStore';
import type { Operation } from '../../types/operations';
import type { RenderHealth, RenderPreset } from '../../types/render';

const NOW = Date.parse('2026-10-14T12:00:00Z');

const PRESETS: RenderPreset[] = [
  { id: 'square-1024', width: 1024, height: 1024, export_width: 1024, export_height: 1024, label: 'Square' },
  { id: 's25', width: 1152, height: 2496, export_width: 1080, export_height: 2340, label: 'Phone' },
];

const HEALTHY: RenderHealth = {
  backend: 'comfyui-qwen-image-2.1',
  reachable: true,
  base_url: 'http://127.0.0.1:8188',
  detail: null,
  queue_remaining: 0,
};

function renderOp(overrides: Partial<Operation> & Pick<Operation, 'id'>): Operation {
  return {
    kind: 'render',
    status: 'queued',
    title: 'render',
    working_id: null,
    params: { prompt: 'a quiet lake at dawn', preset: 'square-1024', width: 1024, height: 1024 },
    provenance: null,
    result: null,
    error: null,
    created_at: '2026-10-14T11:59:00+00:00',
    started_at: null,
    finished_at: null,
    elapsed_seconds: null,
    ...overrides,
  };
}

interface Routes {
  presets: () => { status: number; body: unknown };
  health: () => { status: number; body: unknown };
  list: () => { status: number; body: unknown };
  submit: (body: unknown) => { status: number; body: unknown };
  cancel: () => { status: number; body: unknown };
  upload: (form: FormData) => { status: number; body: unknown };
}

let routes: Routes;
let fetchSpy: ReturnType<typeof vi.fn>;
let container: HTMLDivElement;
let root: Root;

function respond({ status, body }: { status: number; body: unknown }): Promise<Response> {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body } as Response);
}

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  useOperationsStore.getState().clear();
  Object.values(toast).forEach((fn) => fn.mockReset());
  vi.spyOn(Date, 'now').mockReturnValue(NOW);
  routes = {
    presets: () => ({ status: 200, body: PRESETS }),
    health: () => ({ status: 200, body: HEALTHY }),
    list: () => ({ status: 200, body: { operations: [], count: 0 } }),
    submit: (body) => {
      const req = body as { seed?: number; reference_id?: string };
      return {
        status: 202,
        body: {
          operation: renderOp({
            id: 'job-1',
            params: {
              prompt: 'a quiet lake at dawn',
              preset: 'square-1024',
              seed: req.seed ?? 4242,
              ...(req.reference_id ? { reference_id: req.reference_id } : {}),
            },
            provenance: { seed: req.seed === undefined ? 'draw' : 'record' },
          }),
        },
      };
    },
    cancel: () => ({ status: 200, body: { operation: renderOp({ id: 'job-1', status: 'cancelled' }) } }),
    upload: () => ({
      status: 201,
      body: { reference_id: 'ab12cd34ef56', sha256: 'ab12cd34ef567890ffff', filename: 'lake.png', width: 800, height: 600 },
    }),
  };
  fetchSpy = vi.fn((url: string, init?: RequestInit) => {
    if (url === '/api/v1/render/presets') return respond(routes.presets());
    if (url === '/api/v1/render/health') return respond(routes.health());
    if (url.startsWith('/api/v1/operations?')) return respond(routes.list());
    if (url === '/api/v1/render/jobs' && init?.method === 'POST') {
      return respond(routes.submit(JSON.parse(String(init.body))));
    }
    if (url.endsWith('/cancel')) return respond(routes.cancel());
    if (url === '/api/v1/render/references' && init?.method === 'POST') {
      return respond(routes.upload(init.body as FormData));
    }
    if (url === '/api/v1/operations/job-1') {
      return respond({
        status: 200,
        body: renderOp({ id: 'job-1', status: 'success', finished_at: '2026-10-14T12:00:00+00:00' }),
      });
    }
    return respond({ status: 404, body: { detail: 'not found' } });
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

async function renderStudio(): Promise<void> {
  await act(async () => {
    root.render(
      <ConfigProvider>
        <RenderStudio />
      </ConfigProvider>,
    );
  });
  await flush();
}

function setValue(el: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  setter?.call(el, value);
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

async function fill(prompt: string, seed?: string): Promise<void> {
  const textarea = container.querySelector<HTMLTextAreaElement>('textarea[aria-label="Prompt"]');
  const seedInput = container.querySelector<HTMLInputElement>('input[aria-label="Seed"]');
  if (!textarea || !seedInput) throw new Error('form fields not found');
  await act(async () => {
    setValue(textarea, prompt);
    if (seed !== undefined) setValue(seedInput, seed);
  });
}

async function submit(): Promise<void> {
  const form = container.querySelector('form');
  if (!form) throw new Error('form not found');
  await act(async () => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
  await flush();
}

function postedBodies(): unknown[] {
  return fetchSpy.mock.calls
    .filter((c) => c[0] === '/api/v1/render/jobs')
    .map((c) => JSON.parse(String((c[1] as RequestInit).body)));
}

function card(): HTMLElement {
  const el = container.querySelector<HTMLElement>('[data-testid="render-job"]');
  if (!el) throw new Error('no job card');
  return el;
}

describe('RenderStudio', () => {
  it('submits prompt and preset, omitting the seed when the field is empty', async () => {
    await renderStudio();
    await fill('  a quiet lake at dawn  ');
    await submit();
    expect(postedBodies()).toEqual([{ prompt: 'a quiet lake at dawn', preset: 'square-1024' }]);
    expect(card().dataset.status).toBe('queued');
    expect(card().textContent).toContain('Waiting its turn');
    expect(card().textContent).toContain('seed 4242 (drawn)');
  });

  it('sends a chosen seed as a number and labels it "(chosen)"', async () => {
    await renderStudio();
    await fill('a quiet lake at dawn', '123');
    await submit();
    expect(postedBodies()).toEqual([{ prompt: 'a quiet lake at dawn', preset: 'square-1024', seed: 123 }]);
    expect(card().querySelector('[data-testid="render-seed"]')?.textContent).toBe('seed 123 (chosen)');
  });

  it('does not submit an invalid seed or an empty prompt', async () => {
    await renderStudio();
    await submit();
    expect(toast.warning).toHaveBeenLastCalledWith('Write a prompt first.');
    await fill('a lake', '12abc');
    await submit();
    expect(toast.warning.mock.calls[toast.warning.mock.calls.length - 1]?.[0]).toContain('Seed must be a whole number');
    expect(postedBodies()).toEqual([]);
  });

  it('follows the job through running to a measured result pushed into the store', async () => {
    await renderStudio();
    await fill('a quiet lake at dawn');
    await submit();

    await act(async () => {
      useOperationsStore.getState().upsert(
        renderOp({
          id: 'job-1',
          status: 'running',
          started_at: new Date(NOW - 95_000).toISOString(),
          params: { prompt: 'a quiet lake at dawn', seed: 4242 },
          provenance: { seed: 'draw' },
        }),
      );
    });
    expect(card().dataset.status).toBe('running');
    expect(card().querySelector('[data-testid="render-elapsed"]')?.textContent).toContain('1m 35s since start');
    expect(card().textContent).toContain('1–3 minutes');
    expect(card().querySelector('[role="progressbar"]')).toBeNull();

    await act(async () => {
      useOperationsStore.getState().upsert(
        renderOp({
          id: 'job-1',
          status: 'success',
          started_at: '2026-10-14T11:58:00+00:00',
          finished_at: '2026-10-14T12:00:27+00:00',
          elapsed_seconds: 147.0,
          params: { prompt: 'a quiet lake at dawn', seed: 4242, width: 1024, height: 1024 },
          provenance: { seed: 'draw' },
          result: {
            image_url: '/api/v1/render/jobs/job-1/image',
            width: 1080,
            height: 2340,
            seed: 4242,
            sha256: 'abcdef0123456789abcdef',
          },
        }),
      );
    });
    expect(card().dataset.status).toBe('success');
    expect(card().querySelector('img')?.getAttribute('src')).toBe('/api/v1/render/jobs/job-1/image');
    const facts = card().querySelector('[data-testid="render-facts"]')?.textContent ?? '';
    expect(facts).toContain('1080×2340 px (measured from the PNG)');
    expect(facts).toContain('took 2m 27s (measured)');
    expect(card().querySelector('[data-testid="render-seed"]')?.textContent).toBe('seed 4242 (drawn)');
    expect(card().querySelector('button')).toBeNull(); // no cancel once finished
  });

  it('cancels an active job through POST /operations/{id}/cancel', async () => {
    await renderStudio();
    await fill('a quiet lake at dawn');
    await submit();
    const cancel = Array.from(card().querySelectorAll('button')).find((b) => b.textContent?.includes('Cancel'));
    expect(cancel).toBeDefined();
    await act(async () => {
      cancel?.click();
    });
    await flush();
    const cancelCall = fetchSpy.mock.calls.find((c) => String(c[0]).endsWith('/cancel'));
    expect(cancelCall?.[0]).toBe('/api/v1/operations/job-1/cancel');
    expect((cancelCall?.[1] as RequestInit).method).toBe('POST');
    expect(card().dataset.status).toBe('cancelled');
    expect(toast.info).toHaveBeenCalledWith('Render cancelled.');
  });

  it('answers a 409 cancel calmly and shows the finished record', async () => {
    routes.cancel = () => ({ status: 409, body: { detail: 'operation already finished' } });
    await renderStudio();
    await fill('a quiet lake at dawn');
    await submit();
    const cancel = Array.from(card().querySelectorAll('button')).find((b) => b.textContent?.includes('Cancel'));
    await act(async () => {
      cancel?.click();
    });
    await flush();
    expect(toast.info).toHaveBeenCalledWith('This operation already finished (success).');
    expect(toast.error).not.toHaveBeenCalled();
    expect(card().dataset.status).toBe('success');
  });

  describe('reference image', () => {
    function pick(file: File): Promise<void> {
      const input = container.querySelector<HTMLInputElement>('input[aria-label="Reference image"]');
      if (!input) throw new Error('reference input not found');
      Object.defineProperty(input, 'files', { configurable: true, value: [file] });
      return act(async () => {
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }

    function sized(name: string, type: string, size: number): File {
      const file = new File(['x'], name, { type });
      Object.defineProperty(file, 'size', { value: size });
      return file;
    }

    function uploads(): RequestInit[] {
      return fetchSpy.mock.calls.filter((c) => c[0] === '/api/v1/render/references').map((c) => c[1] as RequestInit);
    }

    it('says what a reference does, and that it is not a pixel edit', async () => {
      await renderStudio();
      const text = container.querySelector('[data-testid="render-reference"]')?.textContent ?? '';
      expect(text).toContain('conditions the scene');
      expect(text).toContain('not a pixel edit');
    });

    it('refuses a non-image or an oversize file before uploading', async () => {
      await renderStudio();
      await pick(sized('notes.txt', 'text/plain', 100));
      expect(container.querySelector('[data-testid="render-reference-error"]')?.textContent).toBe(
        'A reference must be a PNG, JPEG or WebP image.',
      );
      await pick(sized('huge.png', 'image/png', 21 * 1024 * 1024));
      expect(container.querySelector('[data-testid="render-reference-error"]')?.textContent).toContain(
        'at most 20 MB',
      );
      expect(uploads()).toEqual([]);
    });

    it('uploads as multipart field "image", previews it, and sends reference_id with the job', async () => {
      await renderStudio();
      await pick(sized('lake.png', 'image/png', 2048));
      await flush();
      const [init] = uploads();
      expect(init.method).toBe('POST');
      expect(init.body).toBeInstanceOf(FormData);
      const sent = (init.body as FormData).get('image');
      expect(sent).toBeInstanceOf(File);
      expect((sent as File).name).toBe('lake.png');

      const preview = container.querySelector('[data-testid="render-reference-preview"]');
      expect(preview?.querySelector('img')?.getAttribute('src')).toBe('/api/v1/render/references/ab12cd34ef56');
      expect(preview?.textContent).toContain('800×600 px');
      expect(preview?.textContent).toContain('sha256 ab12cd34ef56…');

      await fill('a quiet lake at dawn');
      await submit();
      expect(postedBodies()).toEqual([
        { prompt: 'a quiet lake at dawn', preset: 'square-1024', reference_id: 'ab12cd34ef56' },
      ]);
      const tag = card().querySelector('[data-testid="render-reference-tag"]');
      expect(tag?.textContent).toBe('reference ab12cd…');
      expect(tag?.getAttribute('href')).toBe('/api/v1/render/references/ab12cd34ef56');
    });

    it('shows a refused upload and sends no reference', async () => {
      routes.upload = () => ({ status: 413, body: { detail: 'reference image is larger than 20 MB' } });
      await renderStudio();
      await pick(sized('lake.webp', 'image/webp', 4096));
      await flush();
      expect(container.querySelector('[data-testid="render-reference-error"]')?.textContent).toBe(
        'reference image is larger than 20 MB',
      );
      await fill('a lake');
      await submit();
      expect(postedBodies()).toEqual([{ prompt: 'a lake', preset: 'square-1024' }]);
    });
  });

  it('shows the healthy backend with its URL', async () => {
    await renderStudio();
    const badge = container.querySelector('[data-testid="render-health"]')?.textContent ?? '';
    expect(badge).toContain('ComfyUI reachable at');
    expect(badge).toContain('http://127.0.0.1:8188');
  });

  it('says plainly when ComfyUI is unreachable and which URL it tried', async () => {
    routes.health = () => ({
      status: 200,
      body: { ...HEALTHY, reachable: false, base_url: 'http://127.0.0.1:8188', detail: 'connection refused' },
    });
    await renderStudio();
    const badge = container.querySelector('[data-testid="render-health"]')?.textContent ?? '';
    expect(badge).toContain('ComfyUI is not reachable at');
    expect(badge).toContain('http://127.0.0.1:8188');
    expect(badge).toContain('connection refused');
  });

  it('reports a refused render request through a toast', async () => {
    routes.submit = () => ({ status: 422, body: { detail: [{ msg: 'prompt must not be empty' }] } });
    await renderStudio();
    await fill('x');
    await submit();
    expect(toast.error).toHaveBeenCalledWith('prompt must not be empty');
    expect(container.querySelector('[data-testid="render-job"]')).toBeNull();
  });

  it('says so when the render service itself is missing', async () => {
    routes.health = () => ({ status: 404, body: { detail: 'Not Found' } });
    await renderStudio();
    const badge = container.querySelector('[data-testid="render-health"]')?.textContent ?? '';
    expect(badge).toContain('Render service not available');
    expect(badge).toContain('Not Found');
  });

  it('falls back to the built-in preset list when /render/presets fails', async () => {
    routes.presets = () => ({ status: 500, body: {} });
    await renderStudio();
    expect(container.textContent).toContain('showing the built-in list');
    await fill('a lake');
    await submit();
    expect(postedBodies()).toEqual([{ prompt: 'a lake', preset: 'square-1024' }]);
  });

  it('shows recent renders from GET /operations?kind=render', async () => {
    routes.list = () => ({
      status: 200,
      body: {
        operations: [
          renderOp({
            id: 'old-1',
            status: 'success',
            finished_at: '2026-10-14T10:00:00+00:00',
            elapsed_seconds: 55,
            result: { image_url: '/api/v1/render/jobs/old-1/image', width: 1024, height: 1024, seed: 9 },
          }),
          renderOp({ id: 'old-2', status: 'error', finished_at: '2026-10-14T09:00:00+00:00', error: 'boom' }),
        ],
        count: 2,
      },
    });
    await renderStudio();
    const urls = fetchSpy.mock.calls.map((c) => String(c[0]));
    expect(urls).toContain('/api/v1/operations?kind=render&limit=24');
    const tiles = container.querySelectorAll('[data-testid="render-gallery-item"]');
    expect(tiles).toHaveLength(2);
    expect(tiles[0].querySelector('img')?.getAttribute('src')).toBe('/api/v1/render/jobs/old-1/image');
    expect(tiles[0].textContent).toContain('1024×1024');
  });
});
