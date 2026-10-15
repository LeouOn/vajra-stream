/**
 * SigilRenderStatus — the local render behind a forged sigil's AI image.
 *
 * With `IMAGE_PROVIDER=comfyui`, `POST /sigils/forge` returns
 * `ai_image_render: {operation_id, status}` instead of an inline image: a
 * render operation queued on the GPU that finishes minutes later. This shows
 * that operation from the operations store (kept live by `operation_update`
 * WebSocket events; read once here by id): status, an honest elapsed count
 * from `started_at`, the finished image from the render image route, the
 * error, and a Cancel (`POST /operations/{id}/cancel`). No progress bar — the
 * backend reports none.
 *
 * @component
 */
import React, { useEffect, useState } from 'react';
import { isActiveStatus, useOperationsStore } from '../../stores/operationsStore';
import { describeTiming, formatDuration, liveElapsedSeconds, resolveBackendUrl } from '../../lib/operationFormat';
import { useNow } from '../../hooks/useNow';
import OperationStatusTag from '../Operations/OperationStatusTag';

/** `ai_image_render` as `sigil_service.forge_sigil` returns it. */
export interface SigilRender {
  /** null when the render could not be queued (then `error` says why). */
  operation_id: string | null;
  status: string;
  error?: string | null;
}

function str(v: unknown): string | null {
  return typeof v === 'string' && v.length > 0 ? v : null;
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

const BUTTON =
  'text-[10px] font-semibold px-2 py-1 rounded-md border border-purple-500/30 text-purple-200 hover:bg-purple-500/10 disabled:opacity-50';

export default function SigilRenderStatus({ render }: { render: SigilRender }): React.ReactElement {
  const opId = render.operation_id;
  const op = useOperationsStore((s) => (opId ? s.byId[opId] : undefined));
  const fetchOperation = useOperationsStore((s) => s.fetchOperation);
  const cancelOperation = useOperationsStore((s) => s.cancelOperation);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  // Read the operation once; later changes arrive as `operation_update` events.
  useEffect(() => {
    if (!opId) return undefined;
    let cancelled = false;
    setLoadError(null);
    fetchOperation(opId).catch((err: unknown) => {
      if (!cancelled) setLoadError(err instanceof Error ? err.message : String(err));
    });
    return () => {
      cancelled = true;
    };
  }, [opId, fetchOperation]);

  const now = useNow(op?.status === 'running');

  if (!opId) {
    return (
      <p className="m-0 text-[10px] text-red-300 text-center" data-testid="sigil-render-error">
        Local render could not be queued{render.error ? `: ${render.error}` : '.'}
      </p>
    );
  }

  if (!op) {
    return (
      <div className="text-[10px] text-gray-400 text-center space-y-1" data-testid="sigil-render" data-status="unknown">
        <p className="m-0">Local render {render.status}…</p>
        {loadError && <p className="m-0 text-red-300">{loadError}</p>}
      </div>
    );
  }

  const active = isActiveStatus(op.status);
  const result = op.result ?? {};
  const imageUrl = op.status === 'success' ? str(result.image_url) : null;
  const queuePosition = num(result.queue_position);
  const live = op.status === 'running' ? liveElapsedSeconds(op, now) : null;

  const handleCancel = async (): Promise<void> => {
    setCancelling(true);
    try {
      const outcome = await cancelOperation(op.id);
      setNote(outcome.ok ? null : outcome.message);
    } finally {
      setCancelling(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-1 text-[10px] text-center" data-testid="sigil-render" data-status={op.status}>
      <OperationStatusTag status={op.status} />
      {imageUrl && (
        <img src={resolveBackendUrl(imageUrl)} alt="AI Sigil" className="w-24 h-24 rounded-lg object-cover" />
      )}
      {op.status === 'queued' && (
        <p className="m-0 text-gray-400">
          Waiting for the GPU (one render at a time).
          {queuePosition !== null ? ` Queue position ${queuePosition}.` : ''}
        </p>
      )}
      {op.status === 'running' && (
        <p className="m-0 font-mono text-gray-400" data-testid="sigil-render-elapsed">
          {live === null ? 'rendering · start time not recorded' : `rendering · ${formatDuration(live)} (counted on this device)`}
        </p>
      )}
      {!active && <p className="m-0 font-mono text-gray-500">{describeTiming(op, now)}</p>}
      {op.error && !active && (
        <p className="m-0 text-red-300" data-testid="sigil-render-error">
          {op.error}
        </p>
      )}
      {active && (
        <button type="button" onClick={() => void handleCancel()} disabled={cancelling} className={BUTTON}>
          {cancelling ? 'Cancelling…' : 'Cancel render'}
        </button>
      )}
      {note && <p className="m-0 text-amber-200/80">{note}</p>}
    </div>
  );
}
