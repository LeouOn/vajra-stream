/**
 * Gallery — every real image the system has made, in one grid.
 *
 * Three stores feed it (backend/core/services/gallery.py): local renders
 * (render operations), hosted-provider saves, and folio witnesses held inline.
 * Click a tile for what made it: prompt, recorded settings, the seed labeled
 * drawn/chosen, provider/model, and links to its operation in the Ledger and
 * its folio in Workings.
 *
 * Honesty rules (docs/DEVELOPMENT_ROADMAP.md, "the honest instrument"):
 *   - Only what was recorded is shown; a hosted save from before sidecars
 *     says its prompt was not recorded instead of guessing one.
 *   - Files that are not decodable images are never shown as broken tiles;
 *     the backend reports them and the count of skipped files is visible.
 *
 * @component
 * @route /operations/gallery
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, Descriptions, Drawer, Radio, Tag } from 'antd';
import { ImageOff, RefreshCw } from 'lucide-react';
import { useOperationsStore } from '../../stores/operationsStore';
import { GALLERY_PAGE_SIZE, GALLERY_SOURCE_LABELS, fetchGallery } from '../../lib/galleryApi';
import { formatDateTime, formatDuration, resolveBackendUrl, seedLabel } from '../../lib/operationFormat';
import ProvenanceTag from '../UI/ProvenanceTag';
import { GALLERY_SOURCES, type GalleryItem, type GalleryPage, type GallerySource } from '../../types/gallery';
import type { Operation } from '../../types/operations';

const ALL = 'all';
type Filter = GallerySource | typeof ALL;

const SOURCE_COLORS: Record<GallerySource, string> = {
  'local-render': 'purple',
  hosted: 'blue',
  witness: 'gold',
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function sizeText(item: GalleryItem): string | null {
  return item.width && item.height ? `${item.width}×${item.height}` : null;
}

/** Changes whenever a render succeeds, so a new render shows up without a manual refresh. */
function successfulRendersKey(byId: Record<string, Operation>): string {
  return Object.values(byId)
    .filter((op) => op.kind === 'render' && op.status === 'success')
    .map((op) => op.id)
    .sort()
    .join(',');
}

function Tile({ item, onOpen }: { item: GalleryItem; onOpen: (item: GalleryItem) => void }): React.ReactElement {
  const [failed, setFailed] = useState(false);
  const label = item.prompt ?? `${GALLERY_SOURCE_LABELS[item.source]} image`;
  return (
    <li className="list-none">
      <button
        type="button"
        data-testid="gallery-tile"
        data-source={item.source}
        onClick={() => onOpen(item)}
        className="group w-full text-left rounded-lg overflow-hidden border border-white/10 bg-gray-900/50 hover:border-purple-400/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400"
        title={label}
      >
        <div className="aspect-square w-full bg-black/40 flex items-center justify-center">
          {failed ? (
            <span className="flex flex-col items-center gap-1 text-[10px] text-gray-500 p-2 text-center">
              <ImageOff className="w-5 h-5" />
              could not load
            </span>
          ) : (
            <img
              src={resolveBackendUrl(item.image_url)}
              alt={label}
              loading="lazy"
              decoding="async"
              onError={() => setFailed(true)}
              className="w-full h-full object-cover transition-transform group-hover:scale-[1.02]"
            />
          )}
        </div>
        <div className="px-2 py-1.5 flex items-center gap-1.5 min-w-0">
          <Tag color={SOURCE_COLORS[item.source]} style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}>
            {GALLERY_SOURCE_LABELS[item.source]}
          </Tag>
          <span className="text-[10px] text-gray-400 truncate">{formatDateTime(item.created_at)}</span>
        </div>
      </button>
    </li>
  );
}

function settingsEntries(settings: Record<string, unknown>): [string, string][] {
  return Object.entries(settings)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => [k.replace(/_/g, ' '), typeof v === 'object' ? JSON.stringify(v) : String(v)]);
}

function ItemDetail({ item }: { item: GalleryItem }): React.ReactElement {
  const { origin, links } = item;
  const src = resolveBackendUrl(item.image_url);
  const size = sizeText(item);
  const seedProvenance = origin.seed_provenance ?? null;
  const rows: { key: string; label: string; children: React.ReactNode }[] = [
    { key: 'source', label: 'Source', children: GALLERY_SOURCE_LABELS[item.source] },
    { key: 'created', label: 'Made', children: formatDateTime(item.created_at) },
    {
      key: 'file',
      label: 'File',
      children: `${size ? `${size} (measured) · ` : ''}${item.media_type} · ${formatBytes(item.bytes)}`,
    },
  ];
  if (item.purpose) rows.push({ key: 'purpose', label: 'Purpose', children: item.purpose });
  if (origin.seed !== undefined && origin.seed !== null) {
    rows.push({
      key: 'seed',
      label: 'Seed',
      children: (
        <span className="inline-flex items-center gap-1.5" data-testid="gallery-seed">
          {seedLabel(origin.seed, seedProvenance ? { seed: seedProvenance } : null)}
          {seedProvenance && <ProvenanceTag kind={seedProvenance} />}
        </span>
      ),
    });
  }
  if (origin.provider) rows.push({ key: 'provider', label: 'Provider', children: origin.provider });
  if (origin.model) rows.push({ key: 'model', label: 'Model', children: origin.model });
  if (typeof origin.backend_execution_seconds === 'number') {
    rows.push({
      key: 'exec',
      label: 'Backend time',
      children: `${formatDuration(origin.backend_execution_seconds)} (measured by the backend)`,
    });
  }
  for (const [label, value] of settingsEntries(item.settings)) {
    rows.push({ key: `setting-${label}`, label, children: value });
  }
  if (origin.sha256) {
    rows.push({
      key: 'sha',
      label: 'sha256',
      children: <span className="font-mono text-[10px] break-all">{origin.sha256}</span>,
    });
  }

  return (
    <div className="flex flex-col gap-4" data-testid="gallery-detail">
      <a href={src} target="_blank" rel="noreferrer" className="block">
        <img src={src} alt={item.prompt ?? 'image'} className="w-full rounded border border-white/10" />
      </a>
      <div>
        <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">Prompt</div>
        {item.prompt ? (
          <p className="text-sm text-gray-100 whitespace-pre-wrap break-words m-0" data-testid="gallery-prompt">
            {item.prompt}
          </p>
        ) : (
          <p className="text-sm text-gray-500 italic m-0" data-testid="gallery-prompt">
            Not recorded{item.source === 'hosted' && origin.sidecar === false ? ' (saved before sidecars existed)' : ''}.
          </p>
        )}
        {origin.revised_prompt && origin.revised_prompt !== item.prompt && (
          <p className="text-xs text-gray-400 mt-2 mb-0 break-words">Provider's revision: {origin.revised_prompt}</p>
        )}
      </div>
      <Descriptions size="small" column={1} bordered items={rows} />
      {(links.operation_id || links.working_id) && (
        <div className="flex flex-wrap gap-3 text-sm">
          {links.operation_id && (
            <Link
              data-testid="gallery-link-operation"
              to={`/operations/ledger?op=${encodeURIComponent(links.operation_id)}`}
              className="text-cyan-300 hover:text-cyan-200 underline-offset-2 hover:underline"
            >
              Operation in the Ledger
            </Link>
          )}
          {links.working_id && (
            <Link
              data-testid="gallery-link-working"
              to={`/workings?open=${encodeURIComponent(links.working_id)}`}
              className="text-amber-300 hover:text-amber-200 underline-offset-2 hover:underline"
            >
              Folio {links.working_id}
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

export default function Gallery(): React.ReactElement {
  const [filter, setFilter] = useState<Filter>(ALL);
  const [page, setPage] = useState<GalleryPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GalleryItem | null>(null);
  const requestId = useRef(0);

  const load = useCallback(
    async (offset: number): Promise<void> => {
      const id = ++requestId.current;
      setLoading(true);
      try {
        const next = await fetchGallery({
          source: filter === ALL ? undefined : filter,
          offset,
          limit: GALLERY_PAGE_SIZE,
        });
        if (id !== requestId.current) return;
        setPage((prev) => (offset > 0 && prev ? { ...next, items: [...prev.items, ...next.items] } : next));
        setError(null);
      } catch (err: unknown) {
        if (id === requestId.current) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    },
    [filter],
  );

  useEffect(() => {
    void load(0);
  }, [load]);

  // A render finishing elsewhere (WS operation_update) shows up here on its own.
  const rendersKey = useOperationsStore((s) => successfulRendersKey(s.byId));
  const seenRendersKey = useRef(rendersKey);
  useEffect(() => {
    if (rendersKey === seenRendersKey.current) return;
    seenRendersKey.current = rendersKey;
    void load(0);
  }, [rendersKey, load]);

  const items = page?.items ?? [];
  const counts = page?.counts;
  const allCount = counts ? GALLERY_SOURCES.reduce((sum, s) => sum + counts[s], 0) : null;
  const skipped = page?.skipped ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-sm font-bold text-white tracking-wider m-0">Gallery</h2>
        <span className="text-xs text-gray-400" data-testid="gallery-summary">
          {page
            ? `${page.total} image${page.total === 1 ? '' : 's'}${filter === ALL ? '' : ` · ${GALLERY_SOURCE_LABELS[filter]}`}`
            : loading
              ? 'Reading the gallery…'
              : ''}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Radio.Group
          aria-label="Filter by source"
          size="small"
          optionType="button"
          value={filter}
          onChange={(e) => setFilter(e.target.value as Filter)}
          options={[
            { value: ALL, label: `All${allCount === null ? '' : ` (${allCount})`}` },
            ...GALLERY_SOURCES.map((s) => ({
              value: s,
              label: `${GALLERY_SOURCE_LABELS[s]}${counts ? ` (${counts[s]})` : ''}`,
            })),
          ]}
        />
        <Button
          size="small"
          icon={<RefreshCw className="w-3.5 h-3.5" />}
          loading={loading}
          onClick={() => void load(0)}
        >
          Refresh
        </Button>
      </div>

      {error && (
        <div className="text-xs text-amber-300" role="alert">
          Could not load the gallery: {error}
        </div>
      )}

      {skipped.length > 0 && (
        <details className="text-xs text-gray-400" data-testid="gallery-skipped">
          <summary className="cursor-pointer select-none">
            {skipped.length} file{skipped.length === 1 ? '' : 's'} skipped: not decodable images
          </summary>
          <ul className="mt-1 ml-4 flex flex-col gap-0.5">
            {skipped.map((s) => (
              <li key={`${s.source}:${s.ref}`} className="break-all">
                <span className="font-mono">{s.ref}</span> ({GALLERY_SOURCE_LABELS[s.source] ?? s.source}): {s.reason}
              </li>
            ))}
          </ul>
        </details>
      )}

      {items.length === 0 ? (
        <div className="text-sm text-gray-500 italic" data-testid="gallery-empty">
          {loading
            ? 'Reading the gallery…'
            : error
              ? null
              : 'No images yet. Renders, hosted images and folio witnesses appear here once made.'}
        </div>
      ) : (
        <ul className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-3 p-0 m-0">
          {items.map((item) => (
            <Tile key={item.id} item={item} onOpen={setSelected} />
          ))}
        </ul>
      )}

      {page && items.length < page.total && (
        <div className="flex justify-center">
          <Button size="small" loading={loading} onClick={() => void load(items.length)} data-testid="gallery-more">
            Load more ({page.total - items.length} left)
          </Button>
        </div>
      )}

      <Drawer
        title={selected ? GALLERY_SOURCE_LABELS[selected.source] : 'Image'}
        placement="right"
        size="min(560px, 100vw)"
        open={selected !== null}
        onClose={() => setSelected(null)}
        destroyOnHidden
      >
        {selected && <ItemDetail item={selected} />}
      </Drawer>
    </div>
  );
}
