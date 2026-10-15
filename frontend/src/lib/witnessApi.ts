/**
 * Witness images for working folios (contract W2-2,
 * docs/specs/2026-10-14-operations-and-local-render.md).
 *
 * `POST /operator/workings/{id}/witness` takes `{"backend": "local" | "hosted"}`:
 *   - local  → 202 `{working_id, operation}`: a render job linked by
 *              `working_id` (purpose "witness"). An operations listener on the
 *              backend writes the folio's `witness` block when it finishes.
 *   - hosted → the updated folio, synchronously (OpenRouter path).
 * With no body the backend picks (local when the render backend is reachable).
 */
import { apiUrl } from '../utils/api';
import { errorMessage } from './apiError';
import { isOperation } from '../stores/operationsStore';
import type { Operation, Provenance } from '../types/operations';

export type WitnessBackend = 'local' | 'hosted';

/**
 * The folio's persisted `witness` block. A local render writes
 * `source: "local-render"` with `image_url`; the hosted path (and every
 * witness from before wave 2) carries a base64 `image_data_url`.
 */
export interface WitnessBlock {
  status?: string;
  source?: string;
  operation_id?: string;
  image_url?: string;
  image_data_url?: string;
  seed?: number;
  seed_provenance?: string;
  width?: number;
  height?: number;
  prompt?: string;
  model?: string;
  error?: string;
  /** Real values captioned beside the image (see lib/captionFacts.ts); validated on display. */
  caption_facts?: unknown;
}

export type WitnessReply =
  | { kind: 'operation'; operation: Operation }
  | { kind: 'folio'; folio: Record<string, unknown> };

function workingPath(workingId: string): string {
  return `/operator/workings/${encodeURIComponent(workingId)}`;
}

/** Ask for a witness image. Omit `backend` to let the server choose. */
export async function requestWitness(workingId: string, backend?: WitnessBackend): Promise<WitnessReply> {
  const init: RequestInit = { method: 'POST' };
  if (backend) {
    init.headers = { 'Content-Type': 'application/json' };
    init.body = JSON.stringify({ backend });
  }
  const res = await fetch(apiUrl(`${workingPath(workingId)}/witness`), init);
  if (!res.ok) throw new Error(await errorMessage(res, 'Witness request was refused'));
  const body: unknown = await res.json();
  if (!body || typeof body !== 'object') throw new Error('witness request returned nothing readable');
  const op = (body as { operation?: unknown }).operation;
  if (isOperation(op)) return { kind: 'operation', operation: op };
  return { kind: 'folio', folio: body as Record<string, unknown> };
}

/** `GET /operator/workings/{id}` — re-read a folio after its render finished. */
export async function fetchWorkingFolio(workingId: string): Promise<Record<string, unknown>> {
  const res = await fetch(apiUrl(workingPath(workingId)));
  if (!res.ok) throw new Error(await errorMessage(res, 'Could not re-read the working'));
  const body: unknown = await res.json();
  if (!body || typeof body !== 'object') throw new Error('working returned nothing readable');
  return body as Record<string, unknown>;
}

const PROVENANCES: readonly Provenance[] = ['record', 'computed', 'draw', 'decorative'];

/** `{seed: <provenance>}` for `seedLabel()`, or null when the block didn't record it. */
export function witnessSeedProvenance(block: WitnessBlock): Record<string, Provenance> | null {
  const p = block.seed_provenance;
  return p && (PROVENANCES as readonly string[]).includes(p) ? { seed: p as Provenance } : null;
}

/** A render operation that belongs to a folio's witness (not, say, its sigil). */
export function isWitnessRender(op: Operation): boolean {
  if (op.kind !== 'render') return false;
  const purpose = op.params?.purpose;
  return purpose === undefined || purpose === null || purpose === 'witness';
}
