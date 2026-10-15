/**
 * Local render contract — mirrors backend/app/api/v1/endpoints/render.py.
 *
 * A render job IS an operation (`kind: 'render'`); see ./operations.ts and
 * docs/specs/2026-10-14-operations-and-local-render.md ("Render contract").
 */
import type { Operation } from './operations';

/** `GET /render/presets` item. `export_*` is the size of the delivered PNG. */
export interface RenderPreset {
  id: string;
  width: number;
  height: number;
  export_width: number;
  export_height: number;
  label: string;
}

/** `GET /render/health`. Never raises when ComfyUI is down — `reachable` says so. */
export interface RenderHealth {
  backend: string;
  reachable: boolean;
  base_url: string;
  detail: string | null;
  queue_remaining: number | null;
}

/** `POST /render/jobs` body. Omitting `seed` means the backend draws one. */
export interface RenderJobRequest {
  prompt: string;
  preset?: string;
  width?: number;
  height?: number;
  seed?: number;
  backend?: string;
  working_id?: string;
  purpose?: 'free' | 'witness' | 'sigil';
  /** From `POST /render/references`; conditions the scene (contract W2-1). */
  reference_id?: string;
}

/** `POST /render/references` → 201. Sizes are measured from the stored file. */
export interface RenderReference {
  reference_id: string;
  sha256: string;
  filename: string;
  width: number;
  height: number;
}

/** `POST /render/jobs` → 202. */
export interface RenderJobResponse {
  operation: Operation;
}

/** `operation.result` of a successful render. All sizes are measured from the PNG. */
export interface RenderResult {
  backend_prompt_id?: string;
  image_url?: string;
  width?: number;
  height?: number;
  seed?: number;
  sha256?: string;
  artifact_path?: string;
  /**
   * Seconds the backend itself spent executing (from its own timestamps).
   * Unlike the ledger's elapsed_seconds, this excludes queue waiting and any
   * server downtime before a restart re-attach.
   */
  backend_execution_seconds?: number;
  /** sha256 of the reference image, when the job used one. */
  reference_sha256?: string;
  /** Present only while queued/running. */
  queue_position?: number;
}
