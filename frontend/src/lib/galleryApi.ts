/**
 * Client for the gallery API (`GET /api/v1/gallery`). URLs go through `apiUrl()` (ADR 004).
 */
import { apiUrl } from '../utils/api';
import { errorMessage } from './apiError';
import type { GalleryItem, GalleryPage, GallerySource } from '../types/gallery';

export const GALLERY_PAGE_SIZE = 48;

export interface GalleryQuery {
  source?: GallerySource;
  offset?: number;
  limit?: number;
}

export const GALLERY_SOURCE_LABELS: Record<GallerySource, string> = {
  'local-render': 'Local render',
  hosted: 'Hosted',
  witness: 'Folio witness',
};

function isGalleryItem(value: unknown): value is GalleryItem {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<GalleryItem>;
  return typeof item.id === 'string' && typeof item.image_url === 'string' && typeof item.source === 'string';
}

export async function fetchGallery(query: GalleryQuery = {}): Promise<GalleryPage> {
  const params = new URLSearchParams();
  if (query.source) params.set('source', query.source);
  params.set('offset', String(query.offset ?? 0));
  params.set('limit', String(query.limit ?? GALLERY_PAGE_SIZE));
  const res = await fetch(apiUrl(`/gallery?${params.toString()}`));
  if (!res.ok) throw new Error(await errorMessage(res, 'Could not load the gallery'));
  const body = (await res.json()) as Partial<GalleryPage> | null;
  if (!body || !Array.isArray(body.items)) throw new Error('gallery API returned no items');
  return {
    items: body.items.filter(isGalleryItem),
    total: typeof body.total === 'number' ? body.total : body.items.length,
    offset: typeof body.offset === 'number' ? body.offset : 0,
    limit: typeof body.limit === 'number' ? body.limit : GALLERY_PAGE_SIZE,
    counts: { 'local-render': 0, hosted: 0, witness: 0, ...(body.counts ?? {}) },
    skipped: Array.isArray(body.skipped) ? body.skipped : [],
  };
}
