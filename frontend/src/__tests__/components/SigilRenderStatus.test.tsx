/**
 * Sigil AI image rendered locally (IMAGE_PROVIDER=comfyui), against a mocked API.
 *
 * The forge answers `ai_image_render: {operation_id, status}` instead of an
 * inline image. BroadcastPanel reads that operation once, then follows it
 * from the operations store (which `operation_update` WS events keep live):
 * queued → running with an honest elapsed count → the image from the render
 * image route; errors are shown, and Cancel posts /operations/{id}/cancel.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import BroadcastPanel from '../../components/UI/BroadcastPanel';
import SigilRenderStatus from '../../components/UI/SigilRenderStatus';
import { useOperationsStore } from '../../stores/operationsStore';
import type { Operation } from '../../types/operations';

vi.mock('../../components/3D/RadionicsGlobe', () => ({
  MiniGlobe: () => <div data-testid="mini-globe-stub" />,
}));

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({ sessions: {} }),
}));

const NOW = Date.parse('2026-10-15T12:00:00Z');
const OP_ID = 'op-sigil-1';

function sigilOp(overrides: Partial<Operation> = {}): Operation {
  return {
    id: OP_ID,
    kind: 'render',
    status: 'queued',
    title: 'sigil render',
    working_id: null,
    params: { prompt: 'abstract sigil', purpose: 'sigil', seed: 5 },
    provenance: { seed: 'draw' },
    result: null,
    error: null,
    created_at: '2026-10-15T11:59:00+00:00',
    started_at: null,
    finished_at: null,
    elapsed_seconds: null,
    ...overrides,
  };
}

type Reply = { status: number; body: unknown };

let fetchSpy: ReturnType<typeof vi.fn>;
let operationReply: () => Reply;
let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  useOperationsStore.getState().clear();
  vi.spyOn(Date, 'now').mockReturnValue(NOW);
  operationReply = () => ({ status: 200, body: sigilOp() });
  fetchSpy = vi.fn((url: string, init?: RequestInit) => {
    let reply: Reply = { status: 404, body: { detail: 'not found' } };
    if (url === '/api/v1/populations') reply = { status: 200, body: [] };
    else if (url === '/api/v1/sigils/forge' && init?.method === 'POST') {
      const { intention } = JSON.parse(String(init.body)) as { intention: string };
      reply = {
        status: 200,
        body: {
          status: 'success',
          sigil: {
            id: 'sigil_1',
            intention,
            reduced_letters: 'PRTCN',
            kamea: 'saturn',
            svg: '<svg></svg>',
            ai_image: null,
            ai_image_render: { operation_id: OP_ID, status: 'queued' },
          },
        },
      };
    } else if (url === `/api/v1/operations/${OP_ID}` && !init?.method) reply = operationReply();
    else if (url === `/api/v1/operations/${OP_ID}/cancel` && init?.method === 'POST') {
      reply = {
        status: 200,
        body: { operation: sigilOp({ status: 'cancelled', finished_at: '2026-10-15T12:00:00+00:00' }) },
      };
    }
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

function q<T extends Element = HTMLElement>(testId: string): T | null {
  return container.querySelector<T>(`[data-testid="${testId}"]`);
}

function buttonByText(text: string): HTMLButtonElement {
  const button = Array.from(container.querySelectorAll('button')).find((b) => b.textContent?.includes(text));
  if (!button) throw new Error(`no button "${text}"`);
  return button;
}

async function typeInto(input: HTMLInputElement, value: string): Promise<void> {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
  await act(async () => {
    setter?.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

function calls(): string[] {
  return fetchSpy.mock.calls.map((c) => `${(c[1] as RequestInit | undefined)?.method ?? 'GET'} ${String(c[0])}`);
}

describe('BroadcastPanel — sigil forged with a local render', () => {
  it('follows the queued render op: progress, elapsed, cancel', async () => {
    await act(async () => {
      root.render(
        <ConfigProvider>
          <BroadcastPanel />
        </ConfigProvider>,
      );
    });
    await flush();

    const input = container.querySelector<HTMLInputElement>('input[placeholder="e.g. Protection & Clarity"]');
    if (!input) throw new Error('no intention input');
    await typeInto(input, 'Protection');
    await act(async () => {
      buttonByText('Forge Sigil').click();
    });
    await flush();

    expect(calls()).toContain(`GET /api/v1/operations/${OP_ID}`);
    expect(q('sigil-render')?.dataset.status).toBe('queued');
    expect(q('sigil-render')?.textContent).toContain('Waiting for the GPU');
    expect(container.textContent).not.toContain('Offline Fallback Active');

    // An operation_update push (what useWebSocketStable ingests) moves it on.
    await act(async () => {
      useOperationsStore
        .getState()
        .ingest(sigilOp({ status: 'running', started_at: new Date(NOW - 65_000).toISOString() }));
    });
    expect(q('sigil-render')?.dataset.status).toBe('running');
    expect(q('sigil-render-elapsed')?.textContent).toContain('1m 05s');
    expect(q('sigil-render-elapsed')?.textContent).toContain('counted on this device');

    await act(async () => {
      buttonByText('Cancel render').click();
    });
    await flush();
    expect(calls()).toContain(`POST /api/v1/operations/${OP_ID}/cancel`);
    expect(q('sigil-render')?.dataset.status).toBe('cancelled');
    expect(container.textContent).not.toContain('Cancel render');
  });
});

describe('SigilRenderStatus', () => {
  async function renderStatus(operationId: string | null, error?: string): Promise<void> {
    await act(async () => {
      root.render(
        <ConfigProvider>
          <SigilRenderStatus render={{ operation_id: operationId, status: operationId ? 'queued' : 'error', error }} />
        </ConfigProvider>,
      );
    });
    await flush();
  }

  it('shows the finished image from the render image route', async () => {
    operationReply = () => ({
      status: 200,
      body: sigilOp({
        status: 'success',
        started_at: '2026-10-15T11:59:10+00:00',
        finished_at: '2026-10-15T11:59:58+00:00',
        elapsed_seconds: 48,
        result: { image_url: `/api/v1/render/jobs/${OP_ID}/image`, width: 1024, height: 1024, seed: 5 },
      }),
    });
    await renderStatus(OP_ID);
    expect(q('sigil-render')?.dataset.status).toBe('success');
    expect(q('sigil-render')?.querySelector('img')?.getAttribute('src')).toBe(`/api/v1/render/jobs/${OP_ID}/image`);
    expect(q('sigil-render')?.textContent).toContain('took 48s (measured)');
    expect(container.textContent).not.toContain('Cancel render');
  });

  it('shows the render error', async () => {
    operationReply = () => ({
      status: 200,
      body: sigilOp({ status: 'error', error: 'ComfyUI: out of memory', finished_at: '2026-10-15T11:59:58+00:00' }),
    });
    await renderStatus(OP_ID);
    expect(q('sigil-render-error')?.textContent).toBe('ComfyUI: out of memory');
    expect(q('sigil-render')?.querySelector('img')).toBeNull();
  });

  it('says so when the render could not be queued', async () => {
    await renderStatus(null, 'connection refused');
    expect(q('sigil-render-error')?.textContent).toBe('Local render could not be queued: connection refused');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('reports an operation it cannot read instead of hanging silently', async () => {
    operationReply = () => ({ status: 500, body: { detail: 'boom' } });
    await renderStatus(OP_ID);
    expect(q('sigil-render')?.dataset.status).toBe('unknown');
    expect(q('sigil-render')?.textContent).toContain('HTTP 500');
  });
});
