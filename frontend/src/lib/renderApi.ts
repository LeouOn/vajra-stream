/**
 * Client for the local render API (docs/specs/2026-10-14-operations-and-local-render.md).
 * All URLs go through `apiUrl()` (ADR 004).
 */
import { apiUrl } from '../utils/api';
import { errorMessage } from './apiError';
import { operationFromBody } from '../stores/operationsStore';
import type { Operation } from '../types/operations';
import type { RenderHealth, RenderJobRequest, RenderPreset, RenderReference } from '../types/render';

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

function operationFrom(body: unknown): Operation {
  const op = operationFromBody(body);
  if (!op) throw new Error('render API returned no operation');
  return op;
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

// ---------------------------------------------------------------------------
// Reference images (contract W2-1)
// ---------------------------------------------------------------------------

/** Server limit for a reference upload: 20 MB. */
export const REFERENCE_MAX_BYTES = 20 * 1024 * 1024;

const REFERENCE_TYPES: Record<string, readonly string[]> = {
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/webp': ['.webp'],
};

/** `accept` attribute for the file picker. */
export const REFERENCE_ACCEPT = Object.keys(REFERENCE_TYPES).join(',');

function formatMegabytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Check a picked file before uploading: PNG, JPEG or WebP, not empty, at
 * most 20 MB. Returns a plain-language reason, or null when it is fine.
 * The server checks again; this only saves a pointless upload.
 */
export function validateReferenceFile(file: Pick<File, 'name' | 'type' | 'size'>): string | null {
  const name = file.name.toLowerCase();
  const typeOk = file.type
    ? file.type in REFERENCE_TYPES
    : Object.values(REFERENCE_TYPES).some((exts) => exts.some((ext) => name.endsWith(ext)));
  if (!typeOk) return 'A reference must be a PNG, JPEG or WebP image.';
  if (file.size <= 0) return 'That file is empty.';
  if (file.size > REFERENCE_MAX_BYTES) {
    return `That file is ${formatMegabytes(file.size)}; a reference can be at most 20 MB.`;
  }
  return null;
}

function isRenderReference(value: unknown): value is RenderReference {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  return typeof v.reference_id === 'string' && v.reference_id.length > 0 && typeof v.sha256 === 'string';
}

/** `POST /render/references` (multipart, field `image`) → the stored reference. */
export async function uploadReferenceImage(file: File): Promise<RenderReference> {
  const form = new FormData();
  form.append('image', file, file.name);
  const res = await fetch(apiUrl('/render/references'), { method: 'POST', body: form });
  if (!res.ok) throw new Error(await errorMessage(res, 'Reference upload was refused'));
  const body: unknown = await res.json();
  if (!isRenderReference(body)) throw new Error('render API returned no reference');
  return body;
}

/** URL of a stored reference image (`GET /render/references/{id}`). */
export function referenceImageUrl(referenceId: string): string {
  return apiUrl(`/render/references/${encodeURIComponent(referenceId)}`);
}
