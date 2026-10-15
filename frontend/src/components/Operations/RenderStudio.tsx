/**
 * RenderStudio — submit local renders (ComfyUI behind the render API) and
 * watch them as real operations.
 *
 * Honesty rules (docs/DEVELOPMENT_ROADMAP.md, "the honest instrument"):
 *   - No progress bar: the backend reports no progress, so none is invented.
 *     A running job shows only the live count from its recorded start.
 *   - Image size is the measured PNG size from `result`, not the request.
 *   - A seed is labeled "(drawn)" when `provenance.seed === 'draw'`, else "(chosen)".
 *   - A reference image conditions the scene; the copy says it is not a pixel edit.
 *   - Witness and sigil renders carry no numbers in the image; their
 *     `params.caption_facts` (computed/record values) are captioned under it.
 *
 * @component
 * @route /operations/render
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Input, Select, message } from 'antd';
import { ImageIcon, RefreshCw, Square, Upload } from 'lucide-react';
import { selectActive, selectRecent, useOperationsStore } from '../../stores/operationsStore';
import {
  FALLBACK_PRESETS,
  REFERENCE_ACCEPT,
  fetchRenderHealth,
  fetchRenderPresets,
  parseSeed,
  referenceImageUrl,
  submitRenderJob,
  uploadReferenceImage,
  validateReferenceFile,
} from '../../lib/renderApi';
import {
  describeTiming,
  formatClock,
  formatDuration,
  liveElapsedSeconds,
  resolveBackendUrl,
  seedLabel,
} from '../../lib/operationFormat';
import { useNow } from '../../hooks/useNow';
import OperationStatusTag from './OperationStatusTag';
import ImageCaptionFacts from '../UI/ImageCaptionFacts';
import type { Operation } from '../../types/operations';
import type { RenderHealth, RenderJobRequest, RenderPreset, RenderReference } from '../../types/render';

const POLL_MS = 10_000;
const HEALTH_POLL_MS = 30_000;

interface RenderView {
  prompt: string | null;
  imageUrl: string | null;
  width: number | null;
  height: number | null;
  seed: number | null;
  sha256: string | null;
  backendSeconds: number | null;
  queuePosition: number | null;
  referenceId: string | null;
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function str(v: unknown): string | null {
  return typeof v === 'string' && v.length > 0 ? v : null;
}

function readRender(op: Operation): RenderView {
  const r = op.result ?? {};
  const p = op.params ?? {};
  return {
    prompt: str(p.prompt),
    imageUrl: str(r.image_url),
    width: num(r.width),
    height: num(r.height),
    seed: num(r.seed) ?? num(p.seed),
    sha256: str(r.sha256),
    backendSeconds: num(r.backend_execution_seconds),
    queuePosition: num(r.queue_position),
    referenceId: str(p.reference_id),
  };
}

function HealthBadge({
  health,
  error,
  onRecheck,
}: {
  health: RenderHealth | null;
  error: string | null;
  onRecheck: () => void;
}): React.ReactElement {
  let tone = 'border-white/10 text-gray-400';
  let body: React.ReactNode = 'Checking the render backend…';
  if (error) {
    tone = 'border-amber-500/30 text-amber-200';
    body = <>Render service not available — health check failed: {error}</>;
  } else if (health && !health.reachable) {
    tone = 'border-amber-500/30 text-amber-200';
    body = (
      <>
        ComfyUI is not reachable at <span className="font-mono">{health.base_url}</span>
        {health.detail ? <> — {health.detail}</> : null}. Jobs will wait or fail until it is running.
      </>
    );
  } else if (health) {
    tone = 'border-emerald-500/30 text-emerald-200';
    body = (
      <>
        ComfyUI reachable at <span className="font-mono">{health.base_url}</span>
        {health.queue_remaining !== null && health.queue_remaining !== undefined
          ? ` · ${health.queue_remaining} in its queue`
          : null}
      </>
    );
  }
  return (
    <div
      data-testid="render-health"
      className={`flex flex-wrap items-center gap-2 rounded-lg border bg-gray-900/40 px-3 py-2 text-xs ${tone}`}
    >
      <span className="min-w-0 break-words flex-1">{body}</span>
      <Button size="small" type="text" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={onRecheck}>
        Check again
      </Button>
    </div>
  );
}

function JobCard({
  op,
  now,
  onCancel,
  cancelling,
}: {
  op: Operation;
  now: number;
  onCancel: (id: string) => void;
  cancelling: boolean;
}): React.ReactElement {
  const view = readRender(op);
  const active = op.status === 'queued' || op.status === 'running';
  const live = op.status === 'running' ? liveElapsedSeconds(op, now) : null;
  const imageSrc = view.imageUrl ? resolveBackendUrl(view.imageUrl) : null;

  return (
    <section
      data-testid="render-job"
      data-status={op.status}
      className="rounded-xl border border-white/10 bg-gray-900/60 p-4 flex flex-col gap-3"
    >
      <div className="flex flex-wrap items-center gap-2">
        <OperationStatusTag status={op.status} />
        <span className="text-sm text-gray-100 break-words min-w-0 flex-1">{view.prompt ?? op.title}</span>
        {active && (
          <Button
            size="small"
            danger
            icon={<Square className="w-3 h-3" />}
            loading={cancelling}
            onClick={() => onCancel(op.id)}
          >
            Cancel
          </Button>
        )}
      </div>

      {op.status === 'queued' && (
        <p className="text-xs text-gray-400 m-0 flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-gray-400/70 animate-pulse" aria-hidden />
          Waiting its turn — the GPU renders one image at a time.
          {view.queuePosition !== null ? ` ComfyUI queue position ${view.queuePosition}.` : ''}
        </p>
      )}

      {op.status === 'running' && (
        <div className="text-xs text-gray-300 flex flex-col gap-1">
          <p className="m-0 flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-purple-400/80 animate-pulse" aria-hidden />
            Rendering. A cold start loads the model first and can take 1–3 minutes; a quiet stretch is normal.
          </p>
          <p className="m-0 font-mono text-gray-400" data-testid="render-elapsed">
            {live === null
              ? 'start time not recorded'
              : `${formatDuration(live)} since start at ${formatClock(op.started_at)} (counted on this device)`}
          </p>
        </div>
      )}

      {op.status === 'success' && imageSrc && (
        <a href={imageSrc} target="_blank" rel="noreferrer" className="block">
          <img
            src={imageSrc}
            alt={view.prompt ?? 'render'}
            className="max-h-[60vh] max-w-full rounded-lg border border-white/10 object-contain"
          />
        </a>
      )}

      {op.status === 'success' && <ImageCaptionFacts facts={op.params?.caption_facts} className="text-xs" />}

      {!active && (
        <div className="text-xs text-gray-400 font-mono flex flex-col gap-0.5" data-testid="render-facts">
          {op.status === 'success' && (
            <span>
              {view.width !== null && view.height !== null
                ? `${view.width}×${view.height} px (measured from the PNG)`
                : 'size not reported'}
            </span>
          )}
          <span>{describeTiming(op, now)}</span>
          {view.backendSeconds !== null && (
            <span data-testid="render-backend-seconds">
              {`${formatDuration(view.backendSeconds)} executing on the render backend (its own timestamps)`}
            </span>
          )}
          {view.sha256 && <span>sha256 {view.sha256.slice(0, 16)}…</span>}
        </div>
      )}

      {view.seed !== null && (
        <div className="text-xs text-gray-400" data-testid="render-seed">
          {seedLabel(view.seed, op.provenance)}
        </div>
      )}

      {view.referenceId && (
        <a
          href={referenceImageUrl(view.referenceId)}
          target="_blank"
          rel="noreferrer"
          data-testid="render-reference-tag"
          className="text-xs text-gray-400 font-mono hover:text-gray-200 self-start"
          title="The reference image this render was conditioned on"
        >
          reference {view.referenceId.slice(0, 6)}…
        </a>
      )}

      {op.error && (op.status === 'error' || op.status === 'interrupted' || op.status === 'cancelled') && (
        <div className="text-xs text-red-300 break-words" role="alert">
          {op.error}
        </div>
      )}
    </section>
  );
}

function GalleryTile({ op, onSelect }: { op: Operation; onSelect: (id: string) => void }): React.ReactElement {
  const view = readRender(op);
  const src = op.status === 'success' && view.imageUrl ? resolveBackendUrl(view.imageUrl) : null;
  return (
    <button
      type="button"
      data-testid="render-gallery-item"
      onClick={() => onSelect(op.id)}
      className="text-left rounded-lg border border-white/10 bg-gray-900/40 hover:border-purple-400/40 p-2 flex flex-col gap-1 min-w-0"
    >
      {src ? (
        <img src={src} alt={view.prompt ?? 'render'} loading="lazy" className="w-full aspect-square object-cover rounded" />
      ) : (
        <div className="w-full aspect-square rounded bg-black/40 flex items-center justify-center">
          <OperationStatusTag status={op.status} />
        </div>
      )}
      <span className="text-[11px] text-gray-300 truncate">{view.prompt ?? op.title}</span>
      <span className="text-[10px] text-gray-500 font-mono truncate">
        {view.width !== null && view.height !== null ? `${view.width}×${view.height}` : op.status}
        {op.elapsed_seconds !== null ? ` · ${formatDuration(op.elapsed_seconds)}` : ''}
      </span>
    </button>
  );
}

function ReferencePicker({
  reference,
  onChange,
}: {
  reference: RenderReference | null;
  onChange: (ref: RenderReference | null) => void;
}): React.ReactElement {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File): Promise<void> => {
    const problem = validateReferenceFile(file);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setUploading(true);
    try {
      onChange(await uploadReferenceImage(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2" data-testid="render-reference">
      <span className="text-xs text-gray-400">Reference image (optional)</span>
      <p className="text-[11px] text-gray-500 m-0">
        A reference conditions the scene: the model reads it alongside the prompt. It is not a pixel edit, and the
        uploaded file is stored unchanged. PNG, JPEG or WebP, up to 20 MB.
      </p>
      {reference ? (
        <div className="flex flex-wrap items-center gap-3" data-testid="render-reference-preview">
          <img
            src={referenceImageUrl(reference.reference_id)}
            alt="Reference image"
            className="h-20 w-20 rounded border border-white/10 object-cover"
          />
          <div className="text-[11px] text-gray-400 font-mono flex flex-col min-w-0">
            <span className="truncate">{reference.filename}</span>
            <span>
              {reference.width}×{reference.height} px · sha256 {reference.sha256.slice(0, 12)}…
            </span>
          </div>
          <Button size="small" onClick={() => onChange(null)}>
            Remove reference
          </Button>
        </div>
      ) : (
        <div>
          <input
            ref={inputRef}
            type="file"
            accept={REFERENCE_ACCEPT}
            aria-label="Reference image"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = '';
              if (file) void handleFile(file);
            }}
          />
          <Button
            size="small"
            icon={<Upload className="w-3.5 h-3.5" />}
            loading={uploading}
            onClick={() => inputRef.current?.click()}
          >
            Choose image…
          </Button>
        </div>
      )}
      {error && (
        <span className="text-[11px] text-amber-300" role="alert" data-testid="render-reference-error">
          {error}
        </span>
      )}
    </div>
  );
}

export default function RenderStudio(): React.ReactElement {
  const byId = useOperationsStore((s) => s.byId);
  const upsert = useOperationsStore((s) => s.upsert);
  const fetchOperations = useOperationsStore((s) => s.fetchOperations);
  const fetchOperation = useOperationsStore((s) => s.fetchOperation);
  const cancelOperation = useOperationsStore((s) => s.cancelOperation);

  const [prompt, setPrompt] = useState('');
  const [presets, setPresets] = useState<readonly RenderPreset[]>(FALLBACK_PRESETS);
  const [presetsFallback, setPresetsFallback] = useState(false);
  const [presetId, setPresetId] = useState<string>(FALLBACK_PRESETS[0].id);
  const [seedText, setSeedText] = useState('');
  const [reference, setReference] = useState<RenderReference | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [health, setHealth] = useState<RenderHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [healthTick, setHealthTick] = useState(0);

  const seedParse = parseSeed(seedText);

  useEffect(() => {
    let cancelled = false;
    fetchRenderPresets()
      .then((list) => {
        if (cancelled) return;
        setPresets(list);
        setPresetsFallback(false);
        setPresetId((cur) => (list.some((p) => p.id === cur) ? cur : list[0].id));
      })
      .catch(() => {
        if (!cancelled) setPresetsFallback(true);
      });
    fetchOperations({ kind: 'render', limit: 24 }).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [fetchOperations]);

  useEffect(() => {
    let cancelled = false;
    const check = (): void => {
      fetchRenderHealth()
        .then((h) => {
          if (cancelled) return;
          setHealth(h);
          setHealthError(null);
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setHealth(null);
          setHealthError(err instanceof Error ? err.message : String(err));
        });
    };
    check();
    const id = setInterval(check, HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [healthTick]);

  const activeRenders = useMemo(() => selectActive({ byId }, 'render'), [byId]);
  const recentRenders = useMemo(() => selectRecent({ byId }, 12, 'render'), [byId]);
  const current: Operation | null = (currentJobId ? byId[currentJobId] : undefined) ?? activeRenders[0] ?? null;
  const currentActive = !!current && (current.status === 'queued' || current.status === 'running');
  const now = useNow(current?.status === 'running');

  // Fallback for a dropped WebSocket: re-read the live job now and then.
  const currentId = current?.id ?? null;
  useEffect(() => {
    if (!currentId || !currentActive) return undefined;
    const id = setInterval(() => {
      fetchOperation(currentId).catch(() => undefined);
    }, POLL_MS);
    return () => clearInterval(id);
  }, [currentId, currentActive, fetchOperation]);

  const handleSubmit = async (): Promise<void> => {
    const text = prompt.trim();
    if (!text) {
      message.warning('Write a prompt first.');
      return;
    }
    if (seedParse.error) {
      message.warning(seedParse.error);
      return;
    }
    const body: RenderJobRequest = { prompt: text, preset: presetId };
    if (seedParse.seed !== undefined) body.seed = seedParse.seed;
    if (reference) body.reference_id = reference.reference_id;
    setSubmitting(true);
    try {
      const op = await submitRenderJob(body);
      upsert(op);
      setCurrentJobId(op.id);
      message.success('Render queued.');
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (id: string): Promise<void> => {
    setCancellingId(id);
    try {
      const outcome = await cancelOperation(id);
      if (outcome.ok) message.info('Render cancelled.');
      else if (outcome.reason === 'failed') message.error(outcome.message);
      else message.info(outcome.message);
    } finally {
      setCancellingId(null);
    }
  };

  const selectedPreset = presets.find((p) => p.id === presetId);

  return (
    <div className="flex flex-col gap-5 max-w-4xl">
      <HealthBadge health={health} error={healthError} onRecheck={() => setHealthTick((t) => t + 1)} />

      <form
        className="flex flex-col gap-3 rounded-xl border border-white/10 bg-gray-900/60 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSubmit();
        }}
      >
        <label className="flex flex-col gap-1 text-xs text-gray-400">
          Prompt
          <Input.TextArea
            aria-label="Prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            autoSize={{ minRows: 3, maxRows: 10 }}
            placeholder="What should the image show?"
          />
        </label>
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col gap-1 text-xs text-gray-400 min-w-[220px]">
            Size
            <Select
              aria-label="Preset"
              value={presetId}
              onChange={(v: string) => setPresetId(v)}
              options={presets.map((p) => ({ value: p.id, label: p.label || p.id }))}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-gray-400 min-w-[220px]">
            Seed (optional)
            <Input
              aria-label="Seed"
              value={seedText}
              onChange={(e) => setSeedText(e.target.value)}
              placeholder="empty — a seed is drawn"
              inputMode="numeric"
              status={seedParse.error ? 'error' : undefined}
            />
          </label>
        </div>
        <div className="text-[11px] text-gray-500">
          {selectedPreset
            ? `Delivered at ${selectedPreset.export_width}×${selectedPreset.export_height}.`
            : null}{' '}
          {presetsFallback ? 'Preset list unavailable from the server; showing the built-in list.' : null}
          {seedParse.error ? <span className="text-amber-300"> {seedParse.error}</span> : null}
        </div>
        <ReferencePicker reference={reference} onChange={setReference} />
        <div>
          <Button type="primary" htmlType="submit" loading={submitting} icon={<ImageIcon className="w-4 h-4" />}>
            Render
          </Button>
        </div>
      </form>

      {current ? (
        <JobCard op={current} now={now} onCancel={handleCancel} cancelling={cancellingId === current.id} />
      ) : (
        <p className="text-sm text-gray-500 italic m-0">No render in progress.</p>
      )}

      {activeRenders.length > 1 && (
        <p className="text-xs text-gray-400 m-0">{activeRenders.length} renders queued or running, served in order.</p>
      )}

      <section className="flex flex-col gap-2">
        <h3 className="text-xs font-bold text-white tracking-wider m-0">Recent renders</h3>
        {recentRenders.length === 0 ? (
          <p className="text-xs text-gray-500 italic m-0">None yet.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {recentRenders.map((op) => (
              <GalleryTile key={op.id} op={op} onSelect={setCurrentJobId} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
