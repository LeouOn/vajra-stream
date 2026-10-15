/**
 * Client for the local render API (docs/specs/2026-10-14-operations-and-local-render.md).
 * All URLs go through `apiUrl()` (ADR 004).
 */
import { apiUrl } from '../utils/api';
import { isOperation } from '../stores/operationsStore';
import type { Operation } from '../types/operations';
import type { RenderHealth, RenderJobRequest, RenderPreset } from '../types/render';

/** Used when `GET /render/presets` fails; mirrors the spec's preset ids. */
export const FALLBACK_PRESETS: readonly RenderPreset[] = [
  { id: 'square-1024', width: 1024, height: 1024, export_width: 1024, export_height: 1024, label: 'Square 1024×1024' },
  { id: 'desktop-19-10', width: 2432, height: 1280, export_width: 2432, export_height: 1280, label: 'Desktop 19:10 (2432×1280)' },
  { id: 'desktop-19-9', width: 2432, height: 1152, export_width: 2432, export_height: 1152, label: 'Desktop 19:9 (2432×1152)' },
  { id: 's25', width: 1152, height: 2496, export_width: 1080, export_height: 2340, label: 'Phone S25 (1080×2340)' },
];

const SEED_MAX = Number.MAX_SAFE_INTEGER;

/**
 * Parse the seed field: '' → no seed (the backend draws one); otherwise a
 * whole number. Capped at 2^53-1 so the value survives JSON as a JS number.
 */
export function parseSeed(text: string): { seed?: number; error?: string } {
  const t = text.trim();
  if (t === '') return {};
  if (!/^\d+$/.test(t) || Number(t) > SEED_MAX) {
    return { error: `Seed must be a whole number from 0 to ${SEED_MAX}, or empty to draw one.` };
  }
  return { seed: Number(t) };
}

/** Pull a readable message out of a FastAPI error body (`detail` may be a string or a list). */
async function errorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body: unknown = await res.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail
          .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : String(d)))
          .join('; ');
      }
    }
  } catch {
    // body was not JSON — fall through
  }
  return `${fallback} (HTTP ${res.status})`;
}

function operationFrom(body: unknown): Operation {
  if (body && typeof body === 'object' && 'operation' in body) {
    const op = (body as { operation: unknown }).operation;
    if (isOperation(op)) return op;
  }
  if (isOperation(body)) return body;
  throw new Error('render API returned no operation');
}

export async function fetchRenderPresets(): Promise<RenderPreset[]> {
  const res = await fetch(apiUrl('/render/presets'));
  if (!res.ok) throw new Error(await errorMessage(res, 'Could not load presets'));
  const body: unknown = await res.json();
  const list = Array.isArray(body)
    ? body
    : body && typeof body === 'object' && Array.isArray((body as { presets?: unknown }).presets)
      ? (body as { presets: unknown[] }).presets
      : null;
  const presets = (list ?? []).filter(
    (p): p is RenderPreset =>
      !!p && typeof p === 'object' && typeof (p as RenderPreset).id === 'string',
  );
  if (presets.length === 0) throw new Error('render API returned no presets');
  return presets;
}

export async function fetchRenderHealth(): Promise<RenderHealth> {
  const res = await fetch(apiUrl('/render/health'));
  if (!res.ok) throw new Error(await errorMessage(res, 'Render health check failed'));
  return (await res.json()) as RenderHealth;
}

export async function submitRenderJob(request: RenderJobRequest): Promise<Operation> {
  const res = await fetch(apiUrl('/render/jobs'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(await errorMessage(res, 'Render request was refused'));
  return operationFrom(await res.json());
}

export async function cancelRenderJob(id: string): Promise<Operation | null> {
  const res = await fetch(apiUrl(`/render/jobs/${encodeURIComponent(id)}/cancel`), { method: 'POST' });
  if (!res.ok) throw new Error(await errorMessage(res, 'Cancel failed'));
  try {
    return operationFrom(await res.json());
  } catch {
    return null; // cancelled; the WS push will carry the new state
  }
}
