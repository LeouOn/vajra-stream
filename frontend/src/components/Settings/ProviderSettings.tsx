/**
 * ProviderSettings — settings route showing live LLM provider health.
 *
 * Surfaces the state of every provider registered in the backend
 * `ProviderRegistry` (Phase 2). Health rows are pushed in real-time over
 * the canonical WebSocket via the `PROVIDER_HEALTH` message handled in
 * `useWebSocketStable` (Task 3.2) — no polling. A one-shot REST fetch on
 * mount backfills the table before the first WS push lands.
 *
 * Layout:
 *   - Header (saffron icon + title + tagline)
 *   - Health summary + AntD Table (provider / status / latency / models / error)
 *   - Failover log Card — Timeline of healthy↔unhealthy transitions
 *     detected between consecutive `PROVIDER_HEALTH` pushes. The first
 *     push establishes the baseline (no events logged); subsequent
 *     pushes that flip a provider's `healthy` bit append an event.
 *
 * The component renders gracefully when `providerHealth` is empty — the
 * Table shows an "No providers registered" Empty state and the failover
 * log shows "No failover events recorded." until a transition occurs.
 *
 * @component
 * @route /settings
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, Table, Tag, Typography, Space, Empty, Tooltip, Timeline } from 'antd';
import type { TableColumnsType } from 'antd';
import {
  Activity, Server, AlertTriangle, CheckCircle2, Cpu,
} from 'lucide-react';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
const { Title, Text, Paragraph } = Typography;

/**
 * A single provider-health row in the AntD Table.
 */
interface ProviderHealthRow {
  key: string | number;
  provider: string;
  healthy: boolean;
  latency_ms: number;
  models_available: number;
  error: string | null;
  last_checked: number;
}

/**
 * One failover event: a transition of a single provider between healthy
 * and unhealthy (in either direction) between two consecutive
 * `PROVIDER_HEALTH` pushes. `timestamp` is the provider's `last_checked`
 * epoch seconds at the moment of the transition (falls back to wall-clock
 * if the backend omits the field).
 */
interface FailoverEvent {
  id: number;
  provider: string;
  fromHealthy: boolean;
  toHealthy: boolean;
  timestamp: number;
  error: string | null;
  latency_ms: number;
}

/**
 * Cap the in-memory event log so a long-lived session can't grow
 * unbounded. 50 events ≈ a few hours of dense churn — plenty for
 * day-to-day operator visibility.
 */
const MAX_FAILOVER_EVENTS = 50;

/**
 * Format a latency value (ms) for display.
 * Returns `'—'` for null/undefined so the column never shows `NaN`.
 */
function formatLatency(ms: number | null | undefined): string {
  if (ms == null || Number.isNaN(ms)) return '—';
  return `${ms.toFixed(0)}ms`;
}

export default function ProviderSettings() {
  const { providerHealth, lastProviderHealthUpdate } = useWebSocketStable();
  const [initialFetchAttempted, setInitialFetchAttempted] = useState<boolean>(false);

  /**
   * Failover log state. Derived by diffing consecutive `PROVIDER_HEALTH`
   * pushes in the effect below — the first push establishes the baseline
   * (no events), every subsequent push that flips a provider's `healthy`
   * bit appends an entry. Newest events first; capped at MAX_FAILOVER_EVENTS.
   */
  const [failoverLog, setFailoverLog] = useState<FailoverEvent[]>([]);

  /**
   * Baseline of the previous `PROVIDER_HEALTH` snapshot, keyed by provider
   * name. Kept in a ref so re-renders don't reset it; populated by the
   * diffing effect, read by the same effect on the next push.
   */
  const prevHealthRef = useRef<Map<string, { healthy: boolean; last_checked: number; latency_ms: number; error: string | null }>>(new Map());

  /**
    * One-shot initial fetch — backfills the table before the first WS push.
    * On failure we just log; the WS stream is the authoritative source.
    * We deliberately do not lift the response into local state because the
    * WS hook's `providerHealth` is the single source of truth for this view.
    */
  const fetchHealthOnce = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(`/api/v1/llm/providers/health`);
      if (!res.ok) {
        console.warn(
          'ProviderSettings: initial health fetch non-OK status',
          res.status,
        );
      }
    } catch (err) {
      console.warn(
        'ProviderSettings: initial health fetch failed, relying on WS',
        err,
      );
    } finally {
      setInitialFetchAttempted(true);
    }
  }, []);

  useEffect(() => {
    fetchHealthOnce();
  }, [fetchHealthOnce]);

  /**
   * Diff consecutive `PROVIDER_HEALTH` pushes and append a FailoverEvent
   * whenever a provider's `healthy` bit flips. The first push only
   * populates the baseline (no event). Idempotent across re-renders that
   * don't change `providerHealth`.
   */
  useEffect(() => {
    const prev = prevHealthRef.current;
    const incoming = Array.isArray(providerHealth) ? providerHealth : [];
    const next = new Map<string, { healthy: boolean; last_checked: number; latency_ms: number; error: string | null }>();
    const flipped: FailoverEvent[] = [];
    let bumpId = Date.now();

    for (const p of incoming) {
      if (!p || typeof p.provider !== 'string') continue;
      const snapshot = {
        healthy: Boolean(p.healthy),
        last_checked: typeof p.last_checked === 'number' ? p.last_checked : Date.now() / 1000,
        latency_ms: typeof p.latency_ms === 'number' ? p.latency_ms : 0,
        error: p.error ?? null,
      };
      next.set(p.provider, snapshot);

      const prior = prev.get(p.provider);
      if (prior && prior.healthy !== snapshot.healthy) {
        flipped.push({
          id: ++bumpId,
          provider: p.provider,
          fromHealthy: prior.healthy,
          toHealthy: snapshot.healthy,
          timestamp: snapshot.last_checked * 1000,
          error: snapshot.error,
          latency_ms: snapshot.latency_ms,
        });
      }
    }

    // Establish the new baseline. Even if no flips occurred this push,
    // we still update so the *next* push has the right reference frame.
    prevHealthRef.current = next;

    if (flipped.length > 0) {
      setFailoverLog((existing) =>
        [...flipped, ...existing].slice(0, MAX_FAILOVER_EVENTS),
      );
    }
  }, [providerHealth]);

  // Build table rows from the live WS state.
  const dataSource: ProviderHealthRow[] = (providerHealth || []).map((p, idx) => ({
    key: p.provider || idx,
    provider: p.provider,
    healthy: p.healthy,
    latency_ms: p.latency_ms,
    models_available: p.models_available,
    error: p.error,
    last_checked: p.last_checked,
  }));

  const columns: TableColumnsType<ProviderHealthRow> = [
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      render: (text: string) => (
        <Space size={6}>
          <Cpu size={13} className="text-amber-400" />
          <Text strong style={{ fontFamily: 'monospace' }}>
            {text}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'healthy',
      key: 'healthy',
      filters: [
        { text: 'Healthy', value: true },
        { text: 'Down', value: false },
      ],
      onFilter: (value: React.Key | boolean, record: ProviderHealthRow) =>
        record.healthy === value,
      render: (healthy: boolean) =>
        healthy ? (
          <Tag icon={<CheckCircle2 size={11} />} color="success">
            Healthy
          </Tag>
        ) : (
          <Tag icon={<AlertTriangle size={11} />} color="error">
            Down
          </Tag>
        ),
    },
    {
      title: 'Latency',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      sorter: (a: ProviderHealthRow, b: ProviderHealthRow) =>
        (a.latency_ms ?? 0) - (b.latency_ms ?? 0),
      render: (ms: number) => (
        <Text style={{ fontFamily: 'monospace' }}>{formatLatency(ms)}</Text>
      ),
    },
    {
      title: 'Models',
      dataIndex: 'models_available',
      key: 'models_available',
      sorter: (a: ProviderHealthRow, b: ProviderHealthRow) =>
        (a.models_available ?? 0) - (b.models_available ?? 0),
      render: (n: number) => <Tag>{n ?? 0}</Tag>,
    },
    {
      title: 'Last Error',
      dataIndex: 'error',
      key: 'error',
      render: (err: string | null) =>
        err ? (
          <Tooltip title={err}>
            <Text type="danger" ellipsis={{ tooltip: false }} style={{ maxWidth: 240 }}>
              {err}
            </Text>
          </Tooltip>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
  ];

  const healthyCount = dataSource.filter((p) => p.healthy).length;
  const totalCount = dataSource.length;
  const lastUpdateStr = lastProviderHealthUpdate
    ? new Date(lastProviderHealthUpdate).toLocaleTimeString()
    : initialFetchAttempted
      ? 'awaiting first push'
      : 'never';

  return (
    <div className="flex-1 h-full overflow-y-auto p-6">
      <Space direction="vertical" size={16} style={{ width: '100%', maxWidth: 1400, margin: '0 auto' }}>
        {/* Header */}
        <div>
          <Space size={12} align="center">
            <Server size={28} className="text-amber-400" />
            <div>
              <Title level={3} style={{ margin: 0 }}>LLM Provider Settings</Title>
              <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 13 }}>
                Health-aware failover registry · live via WebSocket
              </Text>
            </div>
          </Space>
          <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0, maxWidth: 720 }}>
            Monitor the health of every configured LLM provider. The backend
            registry ranks providers by priority and automatically fails over
            to the next healthy provider when one stops responding to its
            heartbeat check.
          </Paragraph>
        </div>

        {/* Summary + Health Table */}
        <Card size="small">
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space size={8} align="center">
                <Activity
                  size={14}
                  className={healthyCount > 0 ? 'text-emerald-400' : 'text-gray-500'}
                />
                <Text strong>
                  {healthyCount} / {totalCount} providers healthy
                </Text>
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Last update: {lastUpdateStr}
              </Text>
            </div>
            <Table
              size="small"
              columns={columns}
              dataSource={dataSource}
              pagination={false}
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description={
                      <Space direction="vertical" size={2}>
                        <Text type="secondary">No providers registered</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          Configure provider credentials to populate the registry.
                        </Text>
                      </Space>
                    }
                  />
                ),
              }}
            />
          </Space>
        </Card>

        {/* Failover Log — derived from consecutive PROVIDER_HEALTH pushes. */}
        <Card
          size="small"
          title={
            <Space size={6}>
              <Activity size={14} />
              <span>Failover Log</span>
              {failoverLog.length > 0 && (
                <Tag color="processing" style={{ marginLeft: 8 }}>
                  {failoverLog.length}
                </Tag>
              )}
            </Space>
          }
          extra={
            failoverLog.length > 0 ? (
              <Text
                type="secondary"
                style={{ fontSize: 12, cursor: 'pointer' }}
                onClick={() => setFailoverLog([])}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') setFailoverLog([]);
                }}
              >
                Clear
              </Text>
            ) : null
          }
        >
          {failoverLog.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <Space direction="vertical" size={2}>
                  <Text type="secondary">No failover events recorded.</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Provider health transitions will appear here as they happen.
                  </Text>
                </Space>
              }
            />
          ) : (
            <Timeline
              style={{ marginTop: 4, maxHeight: 280, overflowY: 'auto', paddingRight: 8 }}
              items={failoverLog.map((evt) => ({
                color: evt.toHealthy ? 'green' : 'red',
                children: (
                  <div data-testid="failover-event">
                    <Space size={8} wrap>
                      <Text strong style={{ fontFamily: 'monospace' }}>
                        {evt.provider}
                      </Text>
                      <Tag color={evt.fromHealthy ? 'success' : 'error'}>
                        {evt.fromHealthy ? 'Healthy' : 'Down'}
                      </Tag>
                      <Text type="secondary">→</Text>
                      <Tag color={evt.toHealthy ? 'success' : 'error'}>
                        {evt.toHealthy ? 'Healthy' : 'Down'}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(evt.timestamp).toLocaleTimeString()}
                      </Text>
                    </Space>
                    {evt.error && (
                      <Tooltip title={evt.error}>
                        <Text type="danger" style={{ fontSize: 11, display: 'block', marginTop: 2 }} ellipsis>
                          {evt.error}
                        </Text>
                      </Tooltip>
                    )}
                    {typeof evt.latency_ms === 'number' && evt.latency_ms > 0 && (
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        latency: {evt.latency_ms.toFixed(0)}ms
                      </Text>
                    )}
                  </div>
                ),
              }))}
            />
          )}
        </Card>
      </Space>
    </div>
  );
}
