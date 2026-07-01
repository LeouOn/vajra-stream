/**
 * ModelManager — full LLM model discovery & management panel.
 *
 * Drives the four-section UX called out in TASK:
 *   1. Available Models table (search + free/long-context filters + inline test probe)
 *   2. Saved Models cards (test / remove)
 *   3. Custom Models form (add by model id; provider auto-detected from prefix)
 *   4. Active Model Display (recommended default per use case)
 *
 * Data sources:
 *   - GET  /api/v1/llm/models/available  (cached 5 min on the backend)
 *   - GET  /api/v1/llm/models/saved
 *   - POST /api/v1/llm/models/add
 *   - DELETE /api/v1/llm/models/{model_id}
 *   - POST /api/v1/llm/models/{model_id}/test
 *   - GET  /api/v1/llm/models/defaults
 *
 * @component
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card, Table, Tag, Typography, Space, Input, Switch, Button, Form,
  Tooltip, message, Empty, Spin, Divider, Badge, Segmented,
} from 'antd';
import type { TableColumnsType } from 'antd';
import {
  Search, Star, FlaskConical, Trash2, Plus, Zap, RefreshCw,
  CheckCircle2, AlertTriangle, Cpu, Clock, DollarSign, Database,
} from 'lucide-react';
import { apiUrl } from '../../utils/api';

const { Text, Paragraph, Title } = Typography;

// ─── API types (mirror backend Pydantic models) ──────────────────

interface AvailableModel {
  id: string;
  name: string;
  provider: string;
  context_length: number | null;
  input_per_m: number;
  output_per_m: number;
  is_free: boolean;
  featured: boolean;
  description: string;
  source: string;
}

interface SavedCustomModel {
  model_id: string;
  display_name: string;
  provider: string;
  added_at: string;
}

interface UseCaseDefault {
  model_id: string;
  display_name: string;
  provider: string;
  rationale: string;
}

interface ModelTestResult {
  success: boolean;
  response: string;
  latency_ms: number;
  tokens_used: number;
  cost_estimate: number;
  error: string;
}

interface AvailableModelsResponse {
  status: string;
  count: number;
  fetched_at: number | null;
  source: string;
  models: AvailableModel[];
}

interface SavedModelsResponse {
  status: string;
  count: number;
  models: SavedCustomModel[];
}

interface DefaultsResponse {
  status: string;
  defaults: Record<string, UseCaseDefault>;
}

// ─── Display helpers ─────────────────────────────────────────────

function formatPrice(price: number): string {
  if (price === 0) return 'FREE';
  if (price < 0.01) return `$${price.toFixed(4)}`;
  return `$${price.toFixed(2)}`;
}

function formatContext(ctx: number | null | undefined): string {
  if (ctx == null) return '—';
  if (ctx >= 1_000_000) return `${(ctx / 1_000_000).toFixed(ctx % 1_000_000 === 0 ? 0 : 1)}M`;
  if (ctx >= 1000) return `${Math.round(ctx / 1000)}K`;
  return String(ctx);
}

function detectProvider(modelId: string): string {
  if (modelId.includes('/')) return modelId.split('/')[0].toLowerCase();
  return 'openrouter';
}

// ─── Component ───────────────────────────────────────────────────

type ModelManagerTab = 'available' | 'saved' | 'custom' | 'active';

export default function ModelManager(): React.ReactElement {
  // Data
  const [available, setAvailable] = useState<AvailableModel[]>([]);
  const [saved, setSaved] = useState<SavedCustomModel[]>([]);
  const [defaults, setDefaults] = useState<Record<string, UseCaseDefault>>({});

  // Loading flags
  const [loadingAvailable, setLoadingAvailable] = useState<boolean>(true);
  const [loadingSaved, setLoadingSaved] = useState<boolean>(true);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [freeOnly, setFreeOnly] = useState<boolean>(false);
  const [largeContextOnly, setLargeContextOnly] = useState<boolean>(false);

  // Per-model test state
  const [testResults, setTestResults] = useState<Record<string, ModelTestResult>>({});
  const [testingModelIds, setTestingModelIds] = useState<Set<string>>(new Set());

  // Custom model form
  const [form] = Form.useForm<{ model_id: string; display_name: string; provider: string }>();
  const [submitting, setSubmitting] = useState<boolean>(false);

  const [activeTab, setActiveTab] = useState<ModelManagerTab>('available');

  // ─── Data fetching ────────────────────────────────────────────

  const fetchAvailable = useCallback(async (): Promise<void> => {
    setLoadingAvailable(true);
    try {
      const res = await fetch(apiUrl('/llm/models/available'));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as AvailableModelsResponse;
      setAvailable(data.models || []);
    } catch (err) {
      console.error('ModelManager: available fetch failed', err);
      message.error('Could not load available models from OpenRouter.');
    } finally {
      setLoadingAvailable(false);
    }
  }, []);

  const fetchSaved = useCallback(async (): Promise<void> => {
    setLoadingSaved(true);
    try {
      const res = await fetch(apiUrl('/llm/models/saved'));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as SavedModelsResponse;
      setSaved(data.models || []);
    } catch (err) {
      console.error('ModelManager: saved fetch failed', err);
    } finally {
      setLoadingSaved(false);
    }
  }, []);

  const fetchDefaults = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(apiUrl('/llm/models/defaults'));
      if (!res.ok) return;
      const data = (await res.json()) as DefaultsResponse;
      setDefaults(data.defaults || {});
    } catch (err) {
      console.warn('ModelManager: defaults fetch failed', err);
    }
  }, []);

  useEffect(() => {
    fetchAvailable();
    fetchSaved();
    fetchDefaults();
  }, [fetchAvailable, fetchSaved, fetchDefaults]);

  // ─── Actions ──────────────────────────────────────────────────

  const savedIds = useMemo<Set<string>>(() => new Set(saved.map(s => s.model_id)), [saved]);

  const addSaved = useCallback(async (model: AvailableModel): Promise<void> => {
    try {
      const res = await fetch(apiUrl('/llm/models/add'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: model.id,
          display_name: model.name,
          provider: model.provider,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      message.success(`Saved "${model.name}".`);
      fetchSaved();
    } catch (err) {
      console.error('addSaved failed', err);
      message.error('Failed to save model.');
    }
  }, [fetchSaved]);

  const removeSaved = useCallback(async (modelId: string, displayName: string): Promise<void> => {
    try {
      const res = await fetch(apiUrl(`/llm/models/${encodeURIComponent(modelId)}`), {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      message.success(`Removed "${displayName}".`);
      fetchSaved();
    } catch (err) {
      console.error('removeSaved failed', err);
      message.error('Failed to remove model.');
    }
  }, [fetchSaved]);

  const testModel = useCallback(async (modelId: string): Promise<void> => {
    setTestingModelIds(prev => new Set(prev).add(modelId));
    try {
      const res = await fetch(apiUrl(`/llm/models/${encodeURIComponent(modelId)}/test`), {
        method: 'POST',
      });
      const data = (await res.json()) as ModelTestResult;
      setTestResults(prev => ({ ...prev, [modelId]: data }));
      if (data.success) {
        message.success(`"${modelId}" responded in ${data.latency_ms.toFixed(0)}ms.`);
      } else {
        message.warning(`Test failed: ${data.error || 'unknown error'}`);
      }
    } catch (err) {
      console.error('testModel failed', err);
      const fallback: ModelTestResult = {
        success: false,
        response: '',
        latency_ms: 0,
        tokens_used: 0,
        cost_estimate: 0,
        error: err instanceof Error ? err.message : 'Network error',
      };
      setTestResults(prev => ({ ...prev, [modelId]: fallback }));
      message.error('Network error during test.');
    } finally {
      setTestingModelIds(prev => {
        const next = new Set(prev);
        next.delete(modelId);
        return next;
      });
    }
  }, []);

  const submitCustom = useCallback(async (values: { model_id: string; display_name: string; provider: string }): Promise<void> => {
    const modelId = values.model_id.trim();
    if (!modelId) {
      message.error('Model ID is required.');
      return;
    }
    setSubmitting(true);
    try {
      const provider = (values.provider?.trim() || detectProvider(modelId));
      const res = await fetch(apiUrl('/llm/models/add'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: modelId,
          display_name: values.display_name?.trim() || modelId,
          provider,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      message.success(`Added custom model "${modelId}".`);
      form.resetFields();
      fetchSaved();
    } catch (err) {
      console.error('submitCustom failed', err);
      message.error('Failed to add custom model.');
    } finally {
      setSubmitting(false);
    }
  }, [form, fetchSaved]);

  // ─── Filtered available models ────────────────────────────────

  const filteredAvailable = useMemo<AvailableModel[]>(() => {
    let result = available;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(m =>
        m.id.toLowerCase().includes(q) ||
        m.name.toLowerCase().includes(q) ||
        m.provider.toLowerCase().includes(q)
      );
    }
    if (freeOnly) result = result.filter(m => m.is_free);
    if (largeContextOnly) {
      result = result.filter(m => (m.context_length ?? 0) >= 100_000);
    }
    return result;
  }, [available, search, freeOnly, largeContextOnly]);

  const freeCount = useMemo(() => available.filter(m => m.is_free).length, [available]);

  // ─── Available-table columns ──────────────────────────────────

  const columns: TableColumnsType<AvailableModel> = useMemo(() => [
    {
      title: 'Model',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (name: string, record: AvailableModel) => (
        <Space size={4} direction="vertical" style={{ lineHeight: 1.2 }}>
          <Space size={4}>
            <Text strong style={{ fontSize: 13 }}>{name}</Text>
            {record.featured && <Tag color="gold" style={{ fontSize: 9, margin: 0 }}>FEATURED</Tag>}
            {record.is_free && <Tag color="green" style={{ fontSize: 9, margin: 0 }}>FREE</Tag>}
          </Space>
          <Text type="secondary" style={{ fontSize: 10, fontFamily: 'monospace' }}>{record.id}</Text>
        </Space>
      ),
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      width: 110,
      filters: Array.from(new Set(available.map(m => m.provider))).map(p => ({ text: p, value: p })),
      onFilter: (value, record) => record.provider === value,
      render: (provider: string) => <Tag style={{ fontSize: 10 }}>{provider}</Tag>,
    },
    {
      title: 'Context',
      dataIndex: 'context_length',
      key: 'context_length',
      width: 80,
      sorter: (a, b) => (a.context_length ?? 0) - (b.context_length ?? 0),
      render: (ctx: number | null) => (
        <Text style={{ fontFamily: 'monospace', fontSize: 11 }}>{formatContext(ctx)}</Text>
      ),
    },
    {
      title: 'Input $/M',
      dataIndex: 'input_per_m',
      key: 'input_per_m',
      width: 90,
      sorter: (a, b) => a.input_per_m - b.input_per_m,
      render: (price: number, record: AvailableModel) => (
        <Text style={{ color: record.is_free ? '#52c41a' : undefined, fontFamily: 'monospace', fontSize: 11 }}>
          {formatPrice(price)}
        </Text>
      ),
    },
    {
      title: 'Output $/M',
      dataIndex: 'output_per_m',
      key: 'output_per_m',
      width: 90,
      sorter: (a, b) => a.output_per_m - b.output_per_m,
      render: (price: number, record: AvailableModel) => (
        <Text style={{ color: record.is_free ? '#52c41a' : undefined, fontFamily: 'monospace', fontSize: 11 }}>
          {formatPrice(price)}
        </Text>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 160,
      render: (_: unknown, record: AvailableModel) => {
        const result = testResults[record.id];
        const isTesting = testingModelIds.has(record.id);
        const isSaved = savedIds.has(record.id);
        return (
          <Space size={4} direction="vertical" align="end" style={{ lineHeight: 1.1 }}>
            <Space size={2}>
              <Tooltip title={isSaved ? 'Already saved' : 'Save to preferred list'}>
                <Button
                  size="small"
                  type={isSaved ? 'default' : 'text'}
                  icon={<Star size={12} fill={isSaved ? 'currentColor' : 'none'} className={isSaved ? 'text-amber-400' : 'text-gray-400'} />}
                  disabled={isSaved}
                  onClick={() => addSaved(record)}
                />
              </Tooltip>
              <Button
                size="small"
                type="default"
                loading={isTesting}
                icon={!isTesting && <FlaskConical size={12} />}
                onClick={() => testModel(record.id)}
              >
                Test
              </Button>
            </Space>
            {result && (
              <Text
                style={{
                  fontSize: 9,
                  fontFamily: 'monospace',
                  color: result.success ? '#52c41a' : '#ff4d4f',
                  maxWidth: 200,
                }}
                ellipsis={{ tooltip: result.success ? `"${result.response}" (${result.latency_ms.toFixed(0)}ms)` : result.error }}
              >
                {result.success
                  ? `✓ ${result.response.slice(0, 30)} · ${result.latency_ms.toFixed(0)}ms · ${result.tokens_used} tok`
                  : `✗ ${result.error.slice(0, 60)}`}
              </Text>
            )}
          </Space>
        );
      },
    },
  ], [available, savedIds, testingModelIds, testResults, addSaved, testModel]);

  // ─── Active-model defaults display ────────────────────────────

  const USE_CASE_LABELS: Record<string, string> = {
    outlook_narrative: 'Outlook / Narrative Generation',
    command_center_chat: 'Command Center Chat',
    blessing_loop: 'Blessing Loop (24/7)',
    autonomous_operator: 'Autonomous Operator',
    tarot_divination: 'Tarot / Divination',
    practice_tts: 'Practice TTS',
  };

  return (
    <div className="w-full">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        {/* Header */}
        <div>
          <Space size={12} align="center">
            <Cpu size={22} className="text-amber-400" />
            <div>
              <Title level={4} style={{ margin: 0 }}>Model Manager</Title>
              <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>
                Discover · Save · Test · Configure
              </Text>
            </div>
          </Space>
        </div>

        {/* Section nav */}
        <Segmented
          block
          value={activeTab}
          onChange={(v) => setActiveTab(v as ModelManagerTab)}
          options={[
            { label: <span><Database className="w-3 h-3 inline mr-1" />Available ({available.length})</span>, value: 'available' },
            { label: <span><Star className="w-3 h-3 inline mr-1" />Saved ({saved.length})</span>, value: 'saved' },
            { label: <span><Plus className="w-3 h-3 inline mr-1" />Custom</span>, value: 'custom' },
            { label: <span><Zap className="w-3 h-3 inline mr-1" />Active</span>, value: 'active' },
          ]}
        />

        {/* ── Section 1: Available Models ── */}
        {activeTab === 'available' && (
          <Card size="small">
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
                <Input
                  allowClear
                  size="middle"
                  prefix={<Search size={14} />}
                  placeholder="Search 338+ models by name, id, or provider…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  style={{ width: 320 }}
                />
                <Space size={6}>
                  <Switch size="small" checked={freeOnly} onChange={setFreeOnly} />
                  <Text style={{ fontSize: 12 }}>Free only ({freeCount})</Text>
                </Space>
                <Space size={6}>
                  <Switch size="small" checked={largeContextOnly} onChange={setLargeContextOnly} />
                  <Text style={{ fontSize: 12 }}>≥ 100K context</Text>
                </Space>
                <div style={{ marginLeft: 'auto' }}>
                  <Button
                    size="small"
                    icon={<RefreshCw size={12} />}
                    onClick={fetchAvailable}
                    loading={loadingAvailable}
                  >
                    Refresh
                  </Button>
                </div>
              </div>
              <Text type="secondary" style={{ fontSize: 11 }}>
                Showing <Text strong>{filteredAvailable.length}</Text> of <Text strong>{available.length}</Text> models
                {available.length > 0 && available[0] && (
                  <> · cache source: <Tag style={{ fontSize: 9 }}>{available[0]?.source || 'openrouter'}</Tag></>
                )}
              </Text>

              <Table<AvailableModel>
                size="small"
                columns={columns}
                dataSource={filteredAvailable.map(m => ({ ...m, key: m.id }))}
                loading={loadingAvailable && available.length === 0}
                pagination={{ pageSize: 25, showSizeChanger: true, pageSizeOptions: ['10', '25', '50', '100'] }}
                scroll={{ x: 700 }}
                locale={{
                  emptyText: (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={
                        <Space direction="vertical" size={2}>
                          <Text type="secondary">No models match your filters.</Text>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            Try clearing the search or filters.
                          </Text>
                        </Space>
                      }
                    />
                  ),
                }}
              />
            </Space>
          </Card>
        )}

        {/* ── Section 2: Saved Models ── */}
        {activeTab === 'saved' && (
          <Card
            size="small"
            title={<Space size={6}><Star size={14} className="text-amber-400" /><span>Preferred Models</span></Space>}
          >
            {loadingSaved ? (
              <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
            ) : saved.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Space direction="vertical" size={2}>
                    <Text type="secondary">No saved models yet.</Text>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      Star models from the Available tab, or add a custom model by ID.
                    </Text>
                  </Space>
                }
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {saved.map(m => {
                  const av = available.find(a => a.id === m.model_id);
                  const isFree = av?.is_free ?? (m.model_id.endsWith(':free'));
                  const result = testResults[m.model_id];
                  const isTesting = testingModelIds.has(m.model_id);
                  return (
                    <Card
                      key={m.model_id}
                      size="small"
                      styles={{ body: { padding: 12 } }}
                    >
                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        <Space size={4} align="start" style={{ width: '100%' }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <Text strong style={{ fontSize: 13, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {m.display_name}
                            </Text>
                            <Text type="secondary" style={{ fontSize: 10, fontFamily: 'monospace' }}>{m.model_id}</Text>
                          </div>
                          {isFree && <Tag color="green" style={{ fontSize: 9 }}>FREE</Tag>}
                        </Space>
                        <Space size={4} wrap>
                          <Tag style={{ fontSize: 9 }}>{m.provider}</Tag>
                          {av?.context_length != null && (
                            <Tag style={{ fontSize: 9 }} icon={<Clock size={9} />}>{formatContext(av.context_length)}</Tag>
                          )}
                          {av && !isFree && (
                            <Tag style={{ fontSize: 9 }} icon={<DollarSign size={9} />}>
                              {formatPrice(av.input_per_m)}/M in
                            </Tag>
                          )}
                        </Space>
                        {result && (
                          <div style={{
                            fontSize: 10,
                            fontFamily: 'monospace',
                            padding: '4px 6px',
                            borderRadius: 4,
                            background: result.success ? 'rgba(82,196,26,0.08)' : 'rgba(255,77,79,0.08)',
                            color: result.success ? '#52c41a' : '#ff4d4f',
                          }}>
                            {result.success
                              ? `✓ ${result.response.slice(0, 40)} · ${result.latency_ms.toFixed(0)}ms · ${result.tokens_used} tok · $${result.cost_estimate.toFixed(6)}`
                              : `✗ ${result.error.slice(0, 80)}`}
                          </div>
                        )}
                        <Space size={4} style={{ marginTop: 4 }}>
                          <Button
                            size="small"
                            loading={isTesting}
                            icon={!isTesting && <FlaskConical size={11} />}
                            onClick={() => testModel(m.model_id)}
                          >
                            Test
                          </Button>
                          <Button
                            size="small"
                            danger
                            icon={<Trash2 size={11} />}
                            onClick={() => removeSaved(m.model_id, m.display_name)}
                          />
                        </Space>
                      </Space>
                    </Card>
                  );
                })}
              </div>
            )}
          </Card>
        )}

        {/* ── Section 3: Custom Models ── */}
        {activeTab === 'custom' && (
          <Card
            size="small"
            title={<Space size={6}><Plus size={14} className="text-cyan-400" /><span>Add Custom Model</span></Space>}
          >
            <Paragraph type="secondary" style={{ fontSize: 12 }}>
              Add any OpenRouter model by its ID — for example the free 550B Nemotron:
              <Text code copyable style={{ marginLeft: 6 }}>nvidia/nemotron-3-ultra-550b-a55b:free</Text>
            </Paragraph>
            <Form
              form={form}
              layout="vertical"
              onFinish={submitCustom}
              initialValues={{ provider: '' }}
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Form.Item
                  label="Model ID"
                  name="model_id"
                  rules={[{ required: true, message: 'Model ID is required' }]}
                  extra={<Text type="secondary" style={{ fontSize: 10 }}>e.g. nvidia/nemotron-3-ultra-550b-a55b:free</Text>}
                >
                  <Input
                    placeholder="vendor/model-name"
                    onChange={(e) => {
                      const detected = detectProvider(e.target.value);
                      if (detected && detected !== 'openrouter') {
                        form.setFieldValue('provider', detected);
                      }
                    }}
                  />
                </Form.Item>
                <Form.Item
                  label="Display Name"
                  name="display_name"
                  extra={<Text type="secondary" style={{ fontSize: 10 }}>Shown in selectors. Defaults to the id.</Text>}
                >
                  <Input placeholder="My Custom Model" />
                </Form.Item>
                <Form.Item
                  label="Provider"
                  name="provider"
                  extra={<Text type="secondary" style={{ fontSize: 10 }}>Auto-detected from id prefix.</Text>}
                >
                  <Input placeholder="openrouter" />
                </Form.Item>
              </div>
              <Button
                type="primary"
                htmlType="submit"
                loading={submitting}
                icon={<Plus size={14} />}
                style={{ background: 'linear-gradient(135deg, #0891b2, #0d9488)', border: 'none' }}
              >
                Add to Saved List
              </Button>
            </Form>
            <Divider style={{ margin: '16px 0 12px' }} />
            <Space size={6} align="center">
              <Database size={12} className="text-gray-400" />
              <Text type="secondary" style={{ fontSize: 12 }}>
                Custom models are stored in <Text code style={{ fontSize: 11 }}>~/.vajra-stream/custom_models.json</Text>
              </Text>
            </Space>
          </Card>
        )}

        {/* ── Section 4: Active Model Display ── */}
        {activeTab === 'active' && (
          <Card
            size="small"
            title={<Space size={6}><Zap size={14} className="text-amber-400" /><span>Recommended Defaults per Feature</span></Space>}
          >
            <Paragraph type="secondary" style={{ fontSize: 12 }}>
              These are the recommended default models for each Vajra.Stream feature. They are
              the single source of truth used by the system when no model is explicitly chosen.
            </Paragraph>
            {Object.keys(defaults).length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={<Text type="secondary">Defaults unavailable (backend unreachable).</Text>}
              />
            ) : (
              <Table
                size="small"
                pagination={false}
                dataSource={Object.entries(defaults).map(([key, d]) => ({ key, ...d }))}
                columns={[
                  {
                    title: 'Feature',
                    dataIndex: 'key',
                    key: 'feature',
                    render: (key: string) => (
                      <Text strong style={{ fontSize: 12 }}>{USE_CASE_LABELS[key] || key}</Text>
                    ),
                  },
                  {
                    title: 'Model',
                    dataIndex: 'display_name',
                    key: 'model',
                    render: (name: string, record: UseCaseDefault & { key: string }) => (
                      <Space size={4} direction="vertical" style={{ lineHeight: 1.2 }}>
                        <Space size={4}>
                          <Text strong style={{ fontSize: 12 }}>{name}</Text>
                          {record.model_id.endsWith(':free') && <Tag color="green" style={{ fontSize: 9 }}>FREE</Tag>}
                        </Space>
                        <Text type="secondary" style={{ fontSize: 10, fontFamily: 'monospace' }}>{record.model_id}</Text>
                      </Space>
                    ),
                  },
                  {
                    title: 'Provider',
                    dataIndex: 'provider',
                    key: 'provider',
                    render: (p: string) => <Tag style={{ fontSize: 10 }}>{p}</Tag>,
                  },
                  {
                    title: 'Rationale',
                    dataIndex: 'rationale',
                    key: 'rationale',
                    render: (r: string) => (
                      <Text type="secondary" style={{ fontSize: 11 }}>{r}</Text>
                    ),
                  },
                ]}
              />
            )}
            <Divider style={{ margin: '16px 0 12px' }} />
            <Space size={6} align="center">
              <CheckCircle2 size={12} className="text-emerald-400" />
              <Text type="secondary" style={{ fontSize: 11 }}>
                Nemotron free model is the default for the unlimited blessing loop (zero cost).
              </Text>
            </Space>
          </Card>
        )}

        {/* Footer status bar */}
        <div style={{ textAlign: 'right' }}>
          <Space size={8}>
            <Badge status={available.length > 0 ? 'success' : 'error'} />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {available.length > 0
                ? `${available.length} models in catalogue`
                : 'Catalogue unreachable'}
            </Text>
            {testingModelIds.size > 0 && (
              <Tag icon={<AlertTriangle size={10} />} color="processing">
                testing {testingModelIds.size}
              </Tag>
            )}
          </Space>
        </div>
      </Space>
    </div>
  );
}
