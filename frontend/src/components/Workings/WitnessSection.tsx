/**
 * WitnessSection — a working folio's witness image (contract W2-2).
 *
 * Two parts:
 *   1. The folio's persisted `witness` block: a local render (`image_url`,
 *      measured size, seed labeled drawn/chosen) or a hosted image (base64
 *      `image_data_url`, including every witness made before local renders).
 *   2. The linked render operation (`working_id` + `kind=render`) while it is
 *      queued or running, read from the operations store: status, an honest
 *      elapsed count from `started_at`, and a Cancel. No progress bar — the
 *      backend reports none. When it finishes the folio is re-read, because a
 *      backend listener writes the witness block.
 *
 * Actions: "Render witness locally" (primary) or "Paint with hosted model".
 *
 * @component
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { isActiveStatus, selectByWorkingId, useOperationsStore } from '../../stores/operationsStore';
import {
  fetchWorkingFolio,
  isWitnessRender,
  requestWitness,
  witnessSeedProvenance,
  type WitnessBackend,
  type WitnessBlock,
} from '../../lib/witnessApi';
import {
  describeTiming,
  formatClock,
  formatDuration,
  liveElapsedSeconds,
  resolveBackendUrl,
  seedLabel,
} from '../../lib/operationFormat';
import { useNow } from '../../hooks/useNow';
import { WitnessPlate } from '../CommandCenter/WorkingInstrument';
import OperationStatusTag from '../Operations/OperationStatusTag';
import type { Operation } from '../../types/operations';
import type { WorkingResult, ZoomItem } from '../CommandCenter/RenderMessageWidgets';

/** Re-read a live witness render this often in case the WebSocket drops. */
const POLL_MS = 10_000;

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function str(v: unknown): string | null {
  return typeof v === 'string' && v.length > 0 ? v : null;
}

function sizeText(width: number | null, height: number | null): string | null {
  return width !== null && height !== null ? `${width}×${height} px (measured)` : null;
}

const BUTTON =
  'text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-amber-500/30 text-amber-200 hover:bg-amber-500/10 disabled:opacity-50';

function PersistedWitness({
  witness,
  title,
  onZoomItemClick,
}: {
  witness: WitnessBlock;
  title: string;
  onZoomItemClick?: (item: ZoomItem) => void;
}): React.ReactElement | null {
  if (witness.status === 'error' || (witness.error && witness.status !== 'ok')) {
    return (
      <p className="text-[11px] text-red-300" data-testid="witness-error">
        {witness.operation_id ? 'Local witness render failed: ' : ''}
        {witness.error || 'Witness image failed.'}
      </p>
    );
  }
  const local = witness.source === 'local-render';
  const src = witness.image_url ? resolveBackendUrl(witness.image_url) : (witness.image_data_url ?? null);
  if (!src) return null;
  const size = sizeText(num(witness.width), num(witness.height));
  return (
    <WitnessPlate label={local ? 'Witness · local render' : 'Manifestation still'}>
      <img
        src={src}
        alt="Witness image"
        className="w-full max-h-64 object-contain rounded-lg cursor-zoom-in"
        onClick={() => onZoomItemClick?.({ type: 'image', title, image_data_url: src })}
      />
      <div className="mt-1 flex flex-col gap-0.5 text-[10px] font-mono text-amber-200/70" data-testid="witness-facts">
        <span data-testid="witness-source">
          {local ? 'local render' : `hosted model${witness.model ? ` · ${witness.model}` : ''}`}
        </span>
        {local && size && <span>{size}</span>}
        {local && num(witness.seed) !== null && (
          <span data-testid="witness-seed">{seedLabel(num(witness.seed) ?? 0, witnessSeedProvenance(witness))}</span>
        )}
      </div>
    </WitnessPlate>
  );
}

function LiveWitnessRender({
  op,
  now,
  onCancel,
  cancelling,
  note,
}: {
  op: Operation;
  now: number;
  onCancel: () => void;
  cancelling: boolean;
  note: string | null;
}): React.ReactElement {
  const active = isActiveStatus(op.status);
  const result = op.result ?? {};
  const imageUrl = str(result.image_url);
  const live = op.status === 'running' ? liveElapsedSeconds(op, now) : null;
  const queuePosition = num(result.queue_position);
  const seed = num(result.seed) ?? num(op.params?.seed);
  const size = sizeText(num(result.width), num(result.height));

  return (
    <div
      data-testid="witness-render"
      data-status={op.status}
      className="rounded-lg border border-amber-500/20 bg-black/40 px-3 py-2 flex flex-col gap-1.5 text-[11px]"
    >
      <div className="flex flex-wrap items-center gap-2">
        <OperationStatusTag status={op.status} />
        <span className="text-amber-100 flex-1 min-w-0">Local witness render</span>
        {active && (
          <button type="button" onClick={onCancel} disabled={cancelling} className={BUTTON}>
            {cancelling ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
      </div>
      {op.status === 'queued' && (
        <p className="m-0 text-amber-200/70">
          Waiting its turn — the GPU renders one image at a time.
          {queuePosition !== null ? ` ComfyUI queue position ${queuePosition}.` : ''}
        </p>
      )}
      {op.status === 'running' && (
        <p className="m-0 font-mono text-amber-200/70" data-testid="witness-elapsed">
          {live === null
            ? 'rendering · start time not recorded'
            : `rendering · ${formatDuration(live)} since start at ${formatClock(op.started_at)} (counted on this device)`}
        </p>
      )}
      {op.status === 'success' && imageUrl && (
        <img
          src={resolveBackendUrl(imageUrl)}
          alt="Witness image"
          className="w-full max-h-64 object-contain rounded-lg"
        />
      )}
      {!active && (
        <div className="flex flex-col gap-0.5 font-mono text-[10px] text-amber-200/70">
          {op.status === 'success' && size && <span>{size}</span>}
          <span>{describeTiming(op, now)}</span>
        </div>
      )}
      {seed !== null && (
        <span className="font-mono text-[10px] text-amber-200/70" data-testid="witness-render-seed">
          {seedLabel(seed, op.provenance)}
        </span>
      )}
      {op.error && !active && <p className="m-0 text-red-300">{op.error}</p>}
      {note && <p className="m-0 text-amber-200/80">{note}</p>}
    </div>
  );
}

export default function WitnessSection({
  folio,
  onFolio,
  onZoomItemClick,
  autoManifest = false,
}: {
  folio: WorkingResult;
  onFolio: (folio: WorkingResult) => void;
  onZoomItemClick?: (item: ZoomItem) => void;
  /** Ask once on mount (server picks the backend) when the folio has no image yet. */
  autoManifest?: boolean;
}): React.ReactElement | null {
  const workingId = folio.working_id ?? null;
  const witness: WitnessBlock | null = folio.witness ?? null;
  const hasImage = !!(witness?.image_url || witness?.image_data_url);

  const byId = useOperationsStore((s) => s.byId);
  const upsert = useOperationsStore((s) => s.upsert);
  const fetchOperations = useOperationsStore((s) => s.fetchOperations);
  const fetchOperation = useOperationsStore((s) => s.fetchOperation);
  const cancelOperation = useOperationsStore((s) => s.cancelOperation);

  const [busy, setBusy] = useState<WitnessBackend | 'auto' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [watchedId, setWatchedId] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [cancelNote, setCancelNote] = useState<string | null>(null);

  const latest = useMemo(
    () => (workingId ? (selectByWorkingId({ byId }, workingId).find(isWitnessRender) ?? null) : null),
    [byId, workingId],
  );
  const latestActive = !!latest && isActiveStatus(latest.status);

  // Read the renders already linked to this working (e.g. queued from chat,
  // then opened here). With `autoManifest`, ask for a witness only when there
  // is no image and none is in flight, so a remount never queues a second job.
  useEffect(() => {
    if (!workingId) return undefined;
    let cancelled = false;
    const load = async (): Promise<void> => {
      let ops: Operation[] = [];
      try {
        ops = await fetchOperations({ working_id: workingId, kind: 'render', limit: 10 });
      } catch {
        ops = [];
      }
      if (cancelled || !autoManifest || hasImage) return;
      const witnessOps = ops.filter(isWitnessRender);
      if (witnessOps.some((op) => isActiveStatus(op.status))) return; // the watcher below follows it
      if (witnessOps.some((op) => op.status === 'success')) {
        const data = await fetchWorkingFolio(workingId).catch(() => null);
        if (data && !cancelled) onFolio(data as WorkingResult);
        return;
      }
      await ask(undefined);
    };
    void load();
    return () => {
      cancelled = true;
    };
    // Once per working, when it is shown.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workingId]);

  // Follow any witness render we see in flight.
  useEffect(() => {
    if (latest && latestActive) setWatchedId(latest.id);
  }, [latest, latestActive]);

  // Polling fallback while it is in flight.
  const latestId = latest?.id ?? null;
  useEffect(() => {
    if (!latestId || !latestActive) return undefined;
    const id = setInterval(() => {
      fetchOperation(latestId).catch(() => undefined);
    }, POLL_MS);
    return () => clearInterval(id);
  }, [latestId, latestActive, fetchOperation]);

  // When a watched render finishes, re-read the folio: the backend listener
  // has written (or is writing) its witness block.
  const watchedFinished = !!latest && latest.id === watchedId && !latestActive;
  const rereadFor = useRef<string | null>(null);
  useEffect(() => {
    if (!watchedFinished || !workingId || !latestId || rereadFor.current === latestId) return;
    rereadFor.current = latestId;
    fetchWorkingFolio(workingId)
      .then((data) => onFolio(data as WorkingResult))
      .catch(() => undefined);
  }, [watchedFinished, workingId, latestId, onFolio]);

  const ask = useCallback(
    async (backend: WitnessBackend | undefined): Promise<void> => {
      if (!workingId) return;
      setBusy(backend ?? 'auto');
      setError(null);
      setCancelNote(null);
      try {
        const reply = await requestWitness(workingId, backend);
        if (reply.kind === 'operation') {
          upsert(reply.operation);
          setWatchedId(reply.operation.id);
        } else {
          onFolio(reply.folio as WorkingResult);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setBusy(null);
      }
    },
    [workingId, upsert, onFolio],
  );

  const handleCancel = async (): Promise<void> => {
    if (!latest) return;
    setCancelling(true);
    try {
      const outcome = await cancelOperation(latest.id);
      setCancelNote(outcome.ok ? null : outcome.message);
    } finally {
      setCancelling(false);
    }
  };

  const now = useNow(latest?.status === 'running');
  if (!workingId) return null;

  // Show the operation while it runs, and after it ends until the folio's
  // witness block reflects it (or if that write failed).
  const showLive =
    !!latest && (latestActive || (latest.id === watchedId && witness?.operation_id !== latest.id));

  return (
    <div className="space-y-2" data-testid="witness-section">
      {witness && (
        <PersistedWitness
          witness={witness}
          title={folio.intention || 'Witness'}
          onZoomItemClick={onZoomItemClick}
        />
      )}
      {showLive && latest && (
        <LiveWitnessRender
          op={latest}
          now={now}
          onCancel={() => void handleCancel()}
          cancelling={cancelling}
          note={cancelNote}
        />
      )}
      {error && (
        <p className="text-[11px] text-red-300" role="alert" data-testid="witness-request-error">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          data-testid="witness-local"
          onClick={() => void ask('local')}
          disabled={busy !== null || latestActive}
          className={BUTTON}
        >
          {busy === 'local' || busy === 'auto'
            ? 'Queueing local render…'
            : hasImage
              ? 'Render a new witness locally'
              : 'Render witness locally'}
        </button>
        <button
          type="button"
          data-testid="witness-hosted"
          onClick={() => void ask('hosted')}
          disabled={busy !== null}
          className={`${BUTTON} border-amber-500/15 text-amber-200/70`}
        >
          {busy === 'hosted' ? 'Painting with hosted model…' : 'Paint with hosted model'}
        </button>
      </div>
    </div>
  );
}
