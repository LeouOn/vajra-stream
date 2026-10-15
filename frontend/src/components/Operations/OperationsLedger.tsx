/**
 * OperationsLedger — the record of real, timed operations, newest first.
 *
 * Every number here comes from the ledger (core/operations.py):
 *   - queued:   "queued" and when it was submitted
 *   - running:  a live count from the recorded `started_at` (this device's clock)
 *   - finished: the backend's measured `elapsed_seconds` and finish time
 * No scores, meters or throughput (docs/DEVELOPMENT_ROADMAP.md, "the honest instrument").
 *
 * @component
 * @route /operations/ledger
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, Select, Tag } from 'antd';
import { RefreshCw } from 'lucide-react';
import { selectOperations, useOperationsStore } from '../../stores/operationsStore';
import { describeTiming, formatDuration } from '../../lib/operationFormat';
import { useNow } from '../../hooks/useNow';
import OperationStatusTag from './OperationStatusTag';
import type { Operation, OperationKind, OperationStatus } from '../../types/operations';

const KINDS: OperationKind[] = ['render', 'broadcast', 'working', 'audio', 'tts', 'video', 'other'];
const STATUSES: OperationStatus[] = ['queued', 'running', 'success', 'error', 'cancelled', 'interrupted'];
const ALL = 'all';

function LedgerRow({ op, now }: { op: Operation; now: number }): React.ReactElement {
  const showError = op.error && (op.status === 'error' || op.status === 'interrupted' || op.status === 'cancelled');
  return (
    <li
      data-testid="ledger-row"
      data-status={op.status}
      className="rounded-lg border border-white/10 bg-gray-900/50 px-4 py-3 flex flex-col gap-1"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Tag style={{ marginInlineEnd: 0 }}>{op.kind}</Tag>
        <OperationStatusTag status={op.status} />
        <span className="text-sm text-gray-100 font-medium break-words min-w-0 flex-1">{op.title || op.id}</span>
        {op.working_id && (
          <Link
            to={`/workings?open=${encodeURIComponent(op.working_id)}`}
            className="text-xs text-cyan-300 hover:text-cyan-200 underline-offset-2 hover:underline"
          >
            working {op.working_id.slice(0, 8)}
          </Link>
        )}
      </div>
      <div className="text-xs text-gray-400 font-mono" data-testid="ledger-timing">
        {describeTiming(op, now)}
      </div>
      {showError && (
        <div className="text-xs text-red-300 break-words" data-testid="ledger-error">
          {op.error}
        </div>
      )}
    </li>
  );
}

export default function OperationsLedger(): React.ReactElement {
  const byId = useOperationsStore((s) => s.byId);
  const summary = useOperationsStore((s) => s.summary);
  const fetchOperations = useOperationsStore((s) => s.fetchOperations);
  const fetchSummary = useOperationsStore((s) => s.fetchSummary);

  const [kind, setKind] = useState<OperationKind | typeof ALL>(ALL);
  const [status, setStatus] = useState<OperationStatus | typeof ALL>(ALL);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchOperations({
      kind: kind === ALL ? undefined : kind,
      status: status === ALL ? undefined : status,
      limit: 200,
    })
      .then(() => {
        if (!cancelled) setListError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setListError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [kind, status, reloadTick, fetchOperations]);

  const operations = useMemo(
    () =>
      selectOperations({ byId }).filter(
        (op) => (kind === ALL || op.kind === kind) && (status === ALL || op.status === status),
      ),
    [byId, kind, status],
  );

  // Re-read the summary whenever the set of active operations changes
  // (something started or finished), so counts stay the backend's own.
  const activeKey = useMemo(
    () =>
      Object.values(byId)
        .filter((op) => op.status === 'queued' || op.status === 'running')
        .map((op) => `${op.id}:${op.status}`)
        .sort()
        .join(','),
    [byId],
  );
  useEffect(() => {
    let cancelled = false;
    fetchSummary()
      .then(() => {
        if (!cancelled) setSummaryError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setSummaryError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [activeKey, reloadTick, fetchSummary]);

  const anyRunning = operations.some((op) => op.status === 'running');
  const now = useNow(anyRunning);

  return (
    <div className="flex flex-col gap-4 max-w-4xl">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-sm font-bold text-white tracking-wider m-0">Operations ledger</h2>
        <div className="text-xs text-gray-400" data-testid="ledger-summary">
          {summary ? (
            <>
              {summary.completed} completed · {formatDuration(summary.seconds_held)} held by completed operations
              (measured) · {summary.active} active
            </>
          ) : summaryError ? (
            <span className="text-amber-300">Summary unavailable: {summaryError}</span>
          ) : (
            'Reading summary…'
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Select
          aria-label="Filter by kind"
          size="small"
          style={{ minWidth: 140 }}
          value={kind}
          onChange={(v: OperationKind | typeof ALL) => setKind(v)}
          options={[{ value: ALL, label: 'All kinds' }, ...KINDS.map((k) => ({ value: k, label: k }))]}
        />
        <Select
          aria-label="Filter by status"
          size="small"
          style={{ minWidth: 140 }}
          value={status}
          onChange={(v: OperationStatus | typeof ALL) => setStatus(v)}
          options={[{ value: ALL, label: 'All statuses' }, ...STATUSES.map((s) => ({ value: s, label: s }))]}
        />
        <Button
          size="small"
          icon={<RefreshCw className="w-3.5 h-3.5" />}
          loading={loading}
          onClick={() => setReloadTick((t) => t + 1)}
        >
          Refresh
        </Button>
      </div>

      {listError && (
        <div className="text-xs text-amber-300" role="alert">
          Could not load the ledger: {listError}
        </div>
      )}

      {operations.length === 0 ? (
        <div className="text-sm text-gray-500 italic">
          {loading ? 'Reading the ledger…' : 'No operations recorded for this filter yet.'}
        </div>
      ) : (
        <ul className="flex flex-col gap-2 list-none p-0 m-0">
          {operations.map((op) => (
            <LedgerRow key={op.id} op={op} now={now} />
          ))}
        </ul>
      )}
    </div>
  );
}
