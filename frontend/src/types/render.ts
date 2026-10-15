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
  /** Present only while queued/running. */
  queue_position?: number;
}
