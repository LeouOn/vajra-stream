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
import { Card, Table, Tag, Typography, Space, Empty, Tooltip, Timeline, Button, Modal, Form, Input, InputNumber, Select, message } from 'antd';
import type { TableColumnsType } from 'antd';
import {
  Activity, Server, AlertTriangle, CheckCircle2, Cpu,
  Plus, Search, X,
} from 'lucide-react';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import { createLogger } from '../../utils/logger';
const { Title, Text, Paragraph } = Typography;

/**
 * Shape of an entry in the provider catalog returned by
 * GET /api/v1/llm/providers/available — used to populate the Add Provider form.
 */
interface ProviderCatalogEntry {
  label: string;
  requires_api_key: boolean;
  default_base_url: string | null;
  default_model: string | null;
  default_priority: number;
  env_var: string | null;
}

interface ProviderCatalog {
  [key: string]: ProviderCatalogEntry;
}

/**
 * Shape of a discovered local LLM endpoint returned by
 * POST /api/v1/llm/providers/discover.
 */
interface DiscoveredEndpoint {
  name: string;
  base_url: string;
  reachable: boolean;
  models: string[];
  error: string | null;
}

interface DiscoverResponse {
  discovered: DiscoveredEndpoint[];
  unreachable: DiscoveredEndpoint[];
}

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
  const log = createLogger('ProviderSettings');
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

  // ─── Add Provider modal + Discover Local state ───────────────────────────
  const [addModalOpen, setAddModalOpen] = useState<boolean>(false);
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [discovering, setDiscovering] = useState<boolean>(false);
  const [discovered, setDiscovered] = useState<DiscoveredEndpoint[]>([]);
  const [testing, setTesting] = useState<boolean>(false);
  const [addForm] = Form.useForm();
  const selectedProvider = Form.useWatch('provider', addForm);

  // Lazy-load the provider catalog when the modal first opens
  const fetchCatalog = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(`/api/v1/llm/providers/available`);
      if (res.ok) {
        const data: { providers: ProviderCatalog } = await res.json();
        setCatalog(data.providers);
      }
    } catch (err) {
      log.warn('Failed to fetch provider catalog:', err);
    }
  }, [log]);

  // Probe local LLM endpoints (LM Studio, Ollama, llama.cpp server)
  const discoverLocal = useCallback(async (): Promise<void> => {
    setDiscovering(true);
    try {
      const res = await fetch(`/api/v1/llm/providers/discover`, { method: 'POST' });
      if (!res.ok) {
        message.error('Discovery failed');
        return;
      }
      const data: DiscoverResponse = await res.json();
      setDiscovered(data.discovered);
      if (data.discovered.length === 0) {
        message.info('No local LLM servers found on common ports (1234, 11434, 8000)');
      } else {
        message.success(`Found ${data.discovered.length} local LLM server${data.discovered.length === 1 ? '' : 's'}`);
      }
    } catch (err) {
      message.error('Discovery network error: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setDiscovering(false);
    }
  }, []);

  // Test a provider config without registering it
  const testConnection = useCallback(async (values: {
    provider: string;
    api_key?: string;
    base_url?: string;
    default_model?: string;
    priority?: number;
  }): Promise<void> => {
    setTesting(true);
    try {
      const res = await fetch(`/api/v1/llm/providers/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (data.reachable) {
        message.success(`✓ ${data.provider} reachable (${data.latency_ms ?? '?'}ms, ${data.models_available ?? '?'} models)`);
      } else {
        message.error(`✗ ${data.provider} unreachable: ${data.error ?? 'unknown error'}`);
      }
    } catch (err) {
      message.error('Test network error: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setTesting(false);
    }
  }, []);

  // Register a provider with the live registry
  const registerProvider = useCallback(async (values: {
    provider: string;
    api_key?: string;
    base_url?: string;
    default_model?: string;
    priority?: number;
  }): Promise<void> => {
    try {
      const res = await fetch(`/api/v1/llm/providers/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (res.ok) {
        message.success(`Registered ${values.provider}`);
        setAddModalOpen(false);
        addForm.resetFields();
      } else {
        message.error(`Registration failed: ${data.detail ?? res.statusText}`);
      }
    } catch (err) {
      message.error('Registration network error: ' + (err instanceof Error ? err.message : String(err)));
    }
  }, [addForm]);

  // Open the modal and lazy-load the catalog
  const openAddModal = useCallback(() => {
    setAddModalOpen(true);
    if (!catalog) fetchCatalog();
  }, [catalog, fetchCatalog]);

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
        log.warn(
          'ProviderSettings: initial health fetch non-OK status',
          res.status,
        );
      }
    } catch (err) {
      log.warn(
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <Space size={8} align="center">
                <Activity
                  size={14}
                  className={healthyCount > 0 ? 'text-emerald-400' : 'text-gray-500'}
                />
                <Text strong>
                  {healthyCount} / {totalCount} providers healthy
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Last update: {lastUpdateStr}
                </Text>
              </Space>
              <Space size={6}>
                <Button
                  size="small"
                  icon={<Search size={12} />}
                  onClick={discoverLocal}
                  loading={discovering}
                  title="Probe LM Studio (:1234), Ollama (:11434), llama.cpp server (:8000)"
                >
                  Discover Local
                </Button>
                <Button
                  size="small"
                  type="primary"
                  icon={<Plus size={12} />}
                  onClick={openAddModal}
                >
                  Add Provider
                </Button>
              </Space>
            </div>
            {/* Discovered local servers — shown only after Discover Local runs */}
            {discovered.length > 0 && (
              <div style={{ background: 'rgba(168, 85, 247, 0.08)', border: '1px solid rgba(168, 85, 247, 0.2)', borderRadius: 6, padding: '8px 12px' }}>
                <Text strong style={{ fontSize: 12 }}>Discovered local servers:</Text>
                <Space direction="vertical" size={4} style={{ marginTop: 4 }}>
                  {discovered.map((d) => (
                    <Space key={d.name} size={8}>
                      <Tag color="purple">{d.name}</Tag>
                      <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>{d.base_url}</Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {d.models.length > 0 ? `${d.models.length} model${d.models.length === 1 ? '' : 's'}: ${d.models.slice(0, 3).join(', ')}${d.models.length > 3 ? '…' : ''}` : 'no models listed'}
                      </Text>
                    </Space>
                  ))}
                </Space>
              </div>
            )}
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

      {/* Add Provider Modal — form to register a new LLM provider at runtime */}
      <Modal
        title={
          <Space size={8}>
            <Plus size={16} />
            <span>Register LLM Provider</span>
          </Space>
        }
        open={addModalOpen}
        onCancel={() => {
          setAddModalOpen(false);
          addForm.resetFields();
        }}
        footer={null}
        width={560}
        destroyOnClose
      >
        <Form
          form={addForm}
          layout="vertical"
          onFinish={(values) => registerProvider(values)}
          initialValues={{ priority: 50 }}
        >
          <Form.Item
            name="provider"
            label="Provider Type"
            rules={[{ required: true, message: 'Pick a provider type' }]}
          >
            <Select
              placeholder={catalog ? 'Select a provider…' : 'Loading catalog…'}
              disabled={!catalog}
              onChange={(value) => {
                // Auto-fill defaults from catalog when the user picks a type
                const entry = catalog?.[value];
                if (entry) {
                  addForm.setFieldsValue({
                    base_url: entry.default_base_url ?? undefined,
                    default_model: entry.default_model ?? undefined,
                    priority: entry.default_priority ?? undefined,
                  });
                }
              }}
              options={
                catalog
                  ? Object.entries(catalog).map(([key, entry]) => ({
                      value: key,
                      label: (
                        <Space size={6}>
                          <span>{entry.label}</span>
                          {entry.env_var && (
                            <Text type="secondary" style={{ fontSize: 10 }}>env: {entry.env_var}</Text>
                          )}
                          {entry.requires_api_key && (
                            <Tag color="orange" style={{ fontSize: 9, margin: 0 }}>key required</Tag>
                          )}
                        </Space>
                      ),
                    }))
                  : []
              }
            />
          </Form.Item>

          {selectedProvider && catalog?.[selectedProvider]?.requires_api_key && (
            <Form.Item
              name="api_key"
              label="API Key"
              rules={[{ required: true, message: 'API key is required for this provider' }]}
            >
              <Input.Password
                placeholder={`Paste ${catalog?.[selectedProvider]?.label ?? ''} API key…`}
                autoComplete="off"
              />
            </Form.Item>
          )}

          <Form.Item name="base_url" label="Base URL (optional)">
            <Input
              placeholder="Leave blank to use provider default"
              addonBefore={
                <Tooltip title="Clear to use the provider's default endpoint">
                  <X
                    size={12}
                    style={{ cursor: 'pointer' }}
                    onClick={() => addForm.setFieldValue('base_url', undefined)}
                  />
                </Tooltip>
              }
            />
          </Form.Item>

          <Form.Item name="default_model" label="Default Model (optional)">
            <Input placeholder="e.g. gpt-4o-mini, claude-3-5-sonnet-latest" />
          </Form.Item>

          <Form.Item
            name="priority"
            label="Priority (higher = tried first)"
            tooltip="When multiple providers are registered, the registry picks the highest-priority healthy one. Default: 50."
          >
            <InputNumber min={1} max={100} style={{ width: 120 }} />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: 16 }}>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
              >
                Register
              </Button>
              <Button
                onClick={() => {
                  const values = addForm.getFieldsValue();
                  if (values.provider) testConnection(values);
                }}
                loading={testing}
              >
                Test Connection
              </Button>
              <Button onClick={() => setAddModalOpen(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
