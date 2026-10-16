/**
 * Client for the deity iconography API (backend/app/api/v1/endpoints/iconography.py).
 * All URLs go through `apiUrl()` (ADR 004). Uploading the image itself is
 * `uploadReferenceImage` in ./renderApi (POST /render/references).
 */
import { apiUrl } from '../utils/api';
import { errorMessage } from './apiError';
import type { DeityDetail, DeityReferencePin, DeitySummary } from '../types/iconography';

function deityPath(deityId: string): string {
  return `/iconography/${encodeURIComponent(deityId)}`;
}

export async function fetchDeities(): Promise<DeitySummary[]> {
  const res = await fetch(apiUrl('/iconography'));
  if (!res.ok) throw new Error(await errorMessage(res, 'Could not load the iconography'));
  const body: unknown = await res.json();
  const list = body && typeof body === 'object' ? (body as { deities?: unknown }).deities : null;
  if (!Array.isArray(list)) throw new Error('iconography API returned no deities');
  return list.filter(
    (d): d is DeitySummary => !!d && typeof d === 'object' && typeof (d as DeitySummary).id === 'string',
  );
}

export async function fetchDeity(deityId: string, form?: string | null): Promise<DeityDetail> {
  const query = form ? `?form=${encodeURIComponent(form)}` : '';
  const res = await fetch(apiUrl(`${deityPath(deityId)}${query}`));
  if (!res.ok) throw new Error(await errorMessage(res, 'Could not load this deity'));
  const body = (await res.json()) as DeityDetail;
  if (!body || typeof body !== 'object' || !body.deity) throw new Error('iconography API returned no deity');
  return body;
}

/** `PUT /iconography/{deity}/reference` → the stored pin. */
export async function pinDeityReference(deityId: string, referenceId: string): Promise<DeityReferencePin> {
  const res = await fetch(apiUrl(`${deityPath(deityId)}/reference`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reference_id: referenceId }),
  });
  if (!res.ok) throw new Error(await errorMessage(res, 'The reference could not be pinned'));
  const body = (await res.json()) as { reference_id?: unknown; set_at?: unknown };
  return {
    reference_id: typeof body.reference_id === 'string' ? body.reference_id : referenceId,
    set_at: typeof body.set_at === 'string' ? body.set_at : null,
    available: true,
  };
}

/** `DELETE /iconography/{deity}/reference`; the stored image itself is kept. */
export async function unpinDeityReference(deityId: string): Promise<void> {
  const res = await fetch(apiUrl(`${deityPath(deityId)}/reference`), { method: 'DELETE' });
  if (!res.ok) throw new Error(await errorMessage(res, 'The reference could not be unpinned'));
}
