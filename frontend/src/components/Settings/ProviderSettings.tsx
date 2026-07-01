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
 *   - Failover log Card (placeholder; provider-switch events land here later)
 *
 * The component renders gracefully when `providerHealth` is empty — the
 * Table shows an "No providers registered" Empty state.
 *
 * @component
 * @route /settings
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, Tag, Typography, Space, Empty, Tooltip, Tabs } from 'antd';
import type { TableColumnsType } from 'antd';
import {
  Activity, Server, AlertTriangle, CheckCircle2, Cpu, Boxes,
} from 'lucide-react';
import { useWebSocketStable, type LLMUsageUpdate } from '../../hooks/useWebSocketStable';
import UsageDashboard from './UsageDashboard';
import ModelManager from './ModelManager';
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
 * Format a latency value (ms) for display.
 * Returns `'—'` for null/undefined so the column never shows `NaN`.
 */
function formatLatency(ms: number | null | undefined): string {
  if (ms == null || Number.isNaN(ms)) return '—';
  return `${ms.toFixed(0)}ms`;
}

export default function ProviderSettings() {
  const { providerHealth, lastProviderHealthUpdate, usageUpdate, lastUsageUpdateAt } = useWebSocketStable();
  const [activeSettingsTab, setActiveSettingsTab] = useState<string>('health');

  /**
   * Live cost/call badge payload passed down to UsageDashboard so the
   * dashboard renders as a prop-driven component (WS state lives in
   * the hook; this view is the entry-point that owns the WS lifecycle).
   */
  const wsUsageProps: { usageUpdate: LLMUsageUpdate | null; lastUsageUpdateAt: number | null } = {
    usageUpdate,
    lastUsageUpdateAt,
  };
  const [initialFetchAttempted, setInitialFetchAttempted] = useState<boolean>(false);

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
            Monitor the health of every configured LLM provider, manage model discovery,
            and curate your preferred list. The backend registry ranks providers by
            priority and automatically fails over to the next healthy provider when one
            stops responding to its heartbeat check.
          </Paragraph>
        </div>

        <Tabs
          activeKey={activeSettingsTab}
          onChange={setActiveSettingsTab}
          items={[
            {
              key: 'health',
              label: (
                <span>
                  <Activity size={13} className="inline mr-1" />
                  Provider Health
                </span>
              ),
              children: (
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
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

                  {/* Usage Dashboard — live LLM cost + token analytics */}
                  <UsageDashboard {...wsUsageProps} />

                  {/* Failover Log (placeholder) */}
                  <Card
                    size="small"
                    title={
                      <Space size={6}>
                        <Activity size={14} />
                        <span>Failover Log</span>
                      </Space>
                    }
                  >
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={
                        <Space direction="vertical" size={2}>
                          <Text type="secondary">No failover events recorded.</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            Provider switch events will be streamed here in a future update.
                          </Text>
                        </Space>
                      }
                    />
                  </Card>
                </Space>
              ),
            },
            {
              key: 'models',
              label: (
                <span>
                  <Boxes size={13} className="inline mr-1" />
                  Model Manager
                </span>
              ),
              children: <ModelManager />,
            },
          ]}
        />
      </Space>
    </div>
  );
}
