/**
 * Gallery — mirrors backend/core/services/gallery.py.
 *
 * REST: GET /api/v1/gallery?source=&offset=&limit=
 * Bytes: each item's `image_url` (`/api/v1/...`, resolve with `resolveBackendUrl`).
 */
import type { Provenance } from './operations';

/** Where the bytes live: a render operation, a hosted-provider save, or a folio's inline witness. */
export type GallerySource = 'local-render' | 'hosted' | 'witness';

export const GALLERY_SOURCES: readonly GallerySource[] = ['local-render', 'hosted', 'witness'];

export interface GalleryLinks {
  operation_id: string | null;
  working_id: string | null;
}

/**
 * What made the image. Renders: seed and its provenance, sha256, timings.
 * Hosted / witness: provider and model when they were recorded.
 */
export interface GalleryOrigin {
  seed?: number | string | null;
  seed_provenance?: Provenance | null;
  sha256?: string | null;
  backend_execution_seconds?: number | null;
  elapsed_seconds?: number | null;
  reference_sha256?: string | null;
  provider?: string | null;
  model?: string | null;
  cost_usd?: number | null;
  revised_prompt?: string | null;
  /** Hosted only: false for saves made before sidecars existed (no prompt/provider on record). */
  sidecar?: boolean;
}

export interface GalleryItem {
  /** `render:<op_id>`, `hosted:<filename>` or `witness:<working_id>`. */
  id: string;
  source: GallerySource;
  /** ISO-8601 UTC, or null when nothing recorded it. */
  created_at: string | null;
  prompt: string | null;
  width: number | null;
  height: number | null;
  media_type: string;
  bytes: number;
  image_url: string;
  /** Render purpose (`free` | `witness` | `sigil`), or `witness` for a folio's hosted witness. */
  purpose: string | null;
  links: GalleryLinks;
  origin: GalleryOrigin;
  /** Generation settings as recorded (preset, backend, size, ...). */
  settings: Record<string, unknown>;
  /** Computed facts for a caption, passed through untouched when the record has them. */
  caption_facts?: unknown;
}

/** A file left out because it is not a decodable image. */
export interface GallerySkipped {
  source: GallerySource;
  ref: string;
  reason: string;
}

export interface GalleryPage {
  items: GalleryItem[];
  total: number;
  offset: number;
  limit: number;
  counts: Record<GallerySource, number>;
  skipped: GallerySkipped[];
}
