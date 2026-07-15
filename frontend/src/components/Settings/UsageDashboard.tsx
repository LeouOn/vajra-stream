/**
 * UsageDashboard — LLM usage statistics panel.
 *
 * Live view of token + cost consumption across every registered provider.
 * Backfilled on mount from `GET /api/v1/llm/usage/summary` and refreshed
 * by two streams:
 *
 *   1. REST poll every 5s against `/api/v1/llm/usage/recent?limit=50`
 *      so the "recent calls" table keeps streaming without a WS push
 *      per row (the backend only emits `LLM_USAGE_UPDATE` on aggregate
 *      settle).
 *   2. WebSocket `LLM_USAGE_UPDATE` (via `useWebSocketStable`) — drives
 *      the live cost badge in the header.
 *
 * Sections:
 *   - KPI row       — Total Calls / Total Tokens / Total Cost / Burn Rate
 *   - Per-provider  — Table with traffic-light cost coloring
 *   - Recent calls  — Last 20 invocations with monospace token counts
 *   - Cost badge    — "$X.XX today" with green/yellow/red tier
 *
 * Renders gracefully with empty state when no usage data has been
 * recorded yet (e.g. fresh backend with no LLM calls).
 *
 * @component
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card, Row, Col, Statistic, Table, Tag, Typography, Space, Empty,
  Badge, Tooltip,
} from 'antd';
import type { TableColumnsType } from 'antd';
import {
  DollarSign, Zap, TrendingUp, Activity, BarChart3,
} from 'lucide-react';
import { type LLMUsageUpdate } from '../../hooks/useWebSocketStable';
import { apiUrl } from '../../utils/api';

const { Text, Title } = Typography;

const POLL_INTERVAL_MS = 5000;
const RECENT_LIMIT = 50;
const RECENT_DISPLAY = 20;

// Cost tier thresholds (USD). Match the live badge tiers so the per-row
// color and the badge tell the same story.
const COST_GREEN = 1;
const COST_YELLOW = 5;

interface ProviderStat {
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
}

interface RecentCall {
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  latency_ms: number;
  timestamp: number | string;
}

interface UsageSummary {
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  provider_stats: Record<string, ProviderStat>;
  recent_calls?: RecentCall[];
}

interface RecentResponse {
  calls: RecentCall[];
}

type CostTier = 'green' | 'yellow' | 'red';

function costTier(usd: number): CostTier {
  if (usd < COST_GREEN) return 'green';
  if (usd < COST_YELLOW) return 'yellow';
  return 'red';
}

function costColor(usd: number): string {
  const tier = costTier(usd);
  if (tier === 'green') return 'success';
  if (tier === 'yellow') return 'warning';
  return 'error';
}

function formatCost(usd: number | null | undefined): string {
  if (usd == null || Number.isNaN(usd)) return '$0.00';
  return `$${usd.toFixed(2)}`;
}

function formatNumber(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '0';
  return n.toLocaleString();
}

function formatTimestamp(ts: number | string): string {
  if (ts == null) return '—';
  const ms = typeof ts === 'number' ? ts : Date.parse(ts);
  if (Number.isNaN(ms)) return '—';
  return new Date(ms).toLocaleTimeString();
}

/**
 * Estimate burn rate ($/hour) by extrapolating the rolling recent-call
 * window. Uses the sum cost of `recentCalls` divided by the time span
 * between the oldest and newest entry. Falls back to $0 when fewer
 * than two timestamps are present (cannot extrapolate a rate).
 */
function computeBurnRateUsdPerHour(calls: RecentCall[]): number {
  if (!calls || calls.length < 2) return 0;
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  let cost = 0;
  for (const c of calls) {
    const ms = typeof c.timestamp === 'number' ? c.timestamp : Date.parse(c.timestamp);
    if (!Number.isNaN(ms)) {
      if (ms < min) min = ms;
      if (ms > max) max = ms;
    }
    cost += c.cost_usd ?? 0;
  }
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) return 0;
  const hours = (max - min) / (1000 * 60 * 60);
  if (hours <= 0) return 0;
  return cost / hours;
}

interface UsageDashboardProps {
  usageUpdate: LLMUsageUpdate | null;
  lastUsageUpdateAt: number | null;
}

export default function UsageDashboard(props: UsageDashboardProps) {
  const usageUpdate = props.usageUpdate;
  const lastUsageUpdateAt = props.lastUsageUpdateAt;

  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [recentCalls, setRecentCalls] = useState<RecentCall[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchAt, setLastFetchAt] = useState<number | null>(null);

  /**
   * Fetch `/api/v1/llm/usage/summary` and seed both summary and the
   * recent-calls tail. The recent-calls list is also kept fresh via
   * the `/llm/usage/recent` poll below.
   */
  const fetchSummary = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(apiUrl('/llm/usage/summary'));
      if (!res.ok) {
        setError(`summary fetch failed (${res.status})`);
        return;
      }
      const data: UsageSummary = await res.json();
      setSummary(data);
      if (Array.isArray(data.recent_calls)) {
        setRecentCalls(data.recent_calls);
      }
      setError(null);
      setLastFetchAt(Date.now());
    } catch (err) {
      console.warn('UsageDashboard: summary fetch failed', err);
      setError('summary fetch error');
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Fetch `/api/v1/llm/usage/recent?limit=50` — polls every 5s so the
   * recent-calls table updates without a per-call WS push.
   */
  const fetchRecent = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(apiUrl(`/llm/usage/recent?limit=${RECENT_LIMIT}`));
      if (!res.ok) return;
      const data: RecentResponse = await res.json();
      if (Array.isArray(data.calls)) {
        setRecentCalls(data.calls);
      }
      setLastFetchAt(Date.now());
    } catch (err) {
      console.warn('UsageDashboard: recent fetch failed', err);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
    const id = setInterval(fetchRecent, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchSummary, fetchRecent]);

  /**
   * Merge the WS badge payload into the visible summary. We treat the WS
   * snapshot as authoritative for today's counters; the REST snapshot
   * remains authoritative for full provider breakdown.
   */
  const liveUpdate: LLMUsageUpdate | null = usageUpdate ?? null;

  const totalCalls = liveUpdate?.total_calls ?? summary?.total_calls ?? 0;
  const totalCost = liveUpdate?.total_cost_usd ?? summary?.total_cost_usd ?? 0;
  const costToday = liveUpdate?.cost_today ?? 0;
  const callsToday = liveUpdate?.calls_today ?? 0;
  const totalPromptTokens = summary?.total_prompt_tokens ?? 0;
  const totalCompletionTokens = summary?.total_completion_tokens ?? 0;
  const totalTokens = totalPromptTokens + totalCompletionTokens;
  const burnRate = useMemo(() => computeBurnRateUsdPerHour(recentCalls), [recentCalls]);
  const costTierToday = costTier(costToday);

  const providerRows = useMemo(() => {
    const stats = summary?.provider_stats ?? {};
    return Object.entries(stats).map(([provider, s], idx) => {
      const calls = s.calls ?? 0;
      const avgLatency = calls > 0
        ? Math.round(
          recentCalls
            .filter((c) => c.provider === provider)
            .reduce((sum, c) => sum + (c.latency_ms ?? 0), 0) / Math.max(1, calls),
        )
        : 0;
      return {
        key: provider || idx,
        provider,
        calls,
        prompt_tokens: s.prompt_tokens ?? 0,
        completion_tokens: s.completion_tokens ?? 0,
        cost_usd: s.cost_usd ?? 0,
        avg_latency_ms: avgLatency,
      };
    });
  }, [summary, recentCalls]);

  const recentRows = useMemo(() => {
    return (recentCalls || [])
      .slice(0, RECENT_DISPLAY)
      .map((c, idx) => ({
        key: `${c.timestamp ?? idx}-${idx}`,
        timestamp: c.timestamp ?? 0,
        provider: c.provider ?? '—',
        model: c.model ?? '—',
        prompt_tokens: c.prompt_tokens ?? 0,
        completion_tokens: c.completion_tokens ?? 0,
        cost_usd: c.cost_usd ?? 0,
        latency_ms: c.latency_ms ?? 0,
      }));
  }, [recentCalls]);

  const providerColumns: TableColumnsType<{
    key: string | number;
    provider: string;
    calls: number;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
    avg_latency_ms: number;
  }> = [
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      render: (text: string) => (
        <Text strong style={{ fontFamily: 'monospace' }}>{text}</Text>
      ),
    },
    {
      title: 'Calls',
      dataIndex: 'calls',
      key: 'calls',
      sorter: (a, b) => a.calls - b.calls,
      render: (n: number) => (
        <Tag style={{ fontFamily: 'monospace' }}>{formatNumber(n)}</Tag>
      ),
    },
    {
      title: 'Prompt Tokens',
      dataIndex: 'prompt_tokens',
      key: 'prompt_tokens',
      sorter: (a, b) => a.prompt_tokens - b.prompt_tokens,
      render: (n: number) => (
        <Text style={{ fontFamily: 'monospace' }}>{formatNumber(n)}</Text>
      ),
    },
    {
      title: 'Completion Tokens',
      dataIndex: 'completion_tokens',
      key: 'completion_tokens',
      sorter: (a, b) => a.completion_tokens - b.completion_tokens,
      render: (n: number) => (
        <Text style={{ fontFamily: 'monospace' }}>{formatNumber(n)}</Text>
      ),
    },
    {
      title: 'Cost (USD)',
      dataIndex: 'cost_usd',
      key: 'cost_usd',
      sorter: (a, b) => a.cost_usd - b.cost_usd,
      render: (n: number) => (
        <Tag color={costColor(n)} style={{ fontFamily: 'monospace', fontWeight: 600 }}>
          {formatCost(n)}
        </Tag>
      ),
    },
    {
      title: 'Avg Latency',
      dataIndex: 'avg_latency_ms',
      key: 'avg_latency_ms',
      sorter: (a, b) => a.avg_latency_ms - b.avg_latency_ms,
      render: (ms: number) => (
        <Text style={{ fontFamily: 'monospace' }}>
          {ms > 0 ? `${ms}ms` : '—'}
        </Text>
      ),
    },
  ];

  const recentColumns: TableColumnsType<{
    key: string;
    timestamp: number | string;
    provider: string;
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
    latency_ms: number;
  }> = [
    {
      title: 'Time',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 110,
      render: (ts: number | string) => (
        <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {formatTimestamp(ts)}
        </Text>
      ),
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      render: (text: string) => (
        <Text strong style={{ fontFamily: 'monospace' }}>{text}</Text>
      ),
    },
    {
      title: 'Model',
      dataIndex: 'model',
      key: 'model',
      ellipsis: true,
      render: (text: string) => (
        <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {text}
        </Text>
      ),
    },
    {
      title: 'Tokens In',
      dataIndex: 'prompt_tokens',
      key: 'prompt_tokens',
      align: 'right',
      render: (n: number) => (
        <Text style={{ fontFamily: 'monospace' }}>{formatNumber(n)}</Text>
      ),
    },
    {
      title: 'Tokens Out',
      dataIndex: 'completion_tokens',
      key: 'completion_tokens',
      align: 'right',
      render: (n: number) => (
        <Text style={{ fontFamily: 'monospace' }}>{formatNumber(n)}</Text>
      ),
    },
    {
      title: 'Cost',
      dataIndex: 'cost_usd',
      key: 'cost_usd',
      align: 'right',
      render: (n: number) => (
        <Tag color={costColor(n)} style={{ fontFamily: 'monospace', fontWeight: 600 }}>
          {formatCost(n)}
        </Tag>
      ),
    },
    {
      title: 'Latency',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      align: 'right',
      render: (ms: number) => (
        <Text style={{ fontFamily: 'monospace' }}>{ms}ms</Text>
      ),
    },
  ];

  const badgeStatus = costTierToday === 'green'
    ? 'success'
    : costTierToday === 'yellow'
      ? 'warning'
      : 'error';

  const lastUpdateStr = lastUsageUpdateAt
    ? new Date(lastUsageUpdateAt).toLocaleTimeString()
    : lastFetchAt
      ? `polled ${new Date(lastFetchAt).toLocaleTimeString()}`
      : loading
        ? 'loading…'
        : 'never';

  return (
    <Card
      size="small"
      title={
        <Space size={8} align="center">
          <BarChart3 size={14} />
          <span>LLM Usage &amp; Cost</span>
        </Space>
      }
      extra={
        <Space size={8}>
          <Tooltip title={`Tier: <$${COST_GREEN} green · <$${COST_YELLOW} yellow · ≥$${COST_YELLOW} red`}>
            <Badge
              status={badgeStatus}
              text={
                <Text
                  strong
                  style={{ fontFamily: 'monospace' }}
                >
                  {formatCost(costToday)} today
                </Text>
              }
            />
          </Tooltip>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Last update: {lastUpdateStr}
          </Text>
        </Space>
      }
    >
      <Space orientation="vertical" size={16} style={{ width: '100%' }}>
        {error && (
          <Text type="danger" style={{ fontSize: 12 }}>
            {error}
          </Text>
        )}

        {/* KPI Row */}
        <Row gutter={16}>
          <Col xs={24} sm={12} md={6}>
            <Card size="small" className="glassmorphism">
              <Statistic
                title={
                  <Space size={6}>
                    <Activity size={12} />
                    <span>Total Calls</span>
                  </Space>
                }
                value={totalCalls}
                formatter={(v: number | string) => formatNumber(typeof v === 'number' ? v : Number(v))}
              />
              <Text type="secondary" style={{ fontSize: 11 }}>
                {formatNumber(callsToday)} today
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small" className="glassmorphism">
              <Statistic
                title={
                  <Space size={6}>
                    <Zap size={12} />
                    <span>Total Tokens</span>
                  </Space>
                }
                value={totalTokens}
                formatter={(v: number | string) => formatNumber(typeof v === 'number' ? v : Number(v))}
              />
              <Text type="secondary" style={{ fontSize: 11, fontFamily: 'monospace' }}>
                {formatNumber(totalPromptTokens)} in · {formatNumber(totalCompletionTokens)} out
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small" className="glassmorphism">
              <Statistic
                title={
                  <Space size={6}>
                    <DollarSign size={12} />
                    <span>Total Cost</span>
                  </Space>
                }
                value={totalCost}
                precision={2}
                prefix="$"
                formatter={(v: number | string) => formatCost(typeof v === 'number' ? v : Number(v))}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small" className="glassmorphism">
              <Statistic
                title={
                  <Space size={6}>
                    <TrendingUp size={12} />
                    <span>Burn Rate</span>
                  </Space>
                }
                value={burnRate}
                precision={2}
                prefix="$"
                suffix="/hr"
                formatter={(v: number | string) => formatCost(typeof v === 'number' ? v : Number(v))}
              />
              <Text type="secondary" style={{ fontSize: 11 }}>
                est. from last {recentCalls.length} calls
              </Text>
            </Card>
          </Col>
        </Row>

        {/* Per-Provider Table */}
        <div>
          <Title level={5} style={{ marginTop: 0, marginBottom: 8 }}>
            <Space size={6}>
              <CpuIcon />
              <span>Per-Provider Breakdown</span>
            </Space>
          </Title>
          <Table
            size="small"
            columns={providerColumns}
            dataSource={providerRows}
            pagination={false}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space orientation="vertical" size={2}>
                      <Text type="secondary">No usage recorded yet.</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Make an LLM call to populate per-provider stats.
                      </Text>
                    </Space>
                  }
                />
              ),
            }}
          />
        </div>

        {/* Recent Calls */}
        <div>
          <Title level={5} style={{ marginTop: 0, marginBottom: 8 }}>
            <Space size={6}>
              <Activity size={13} />
              <span>Recent Calls</span>
              <Tag color="default" style={{ fontSize: 10 }}>last {RECENT_DISPLAY}</Tag>
            </Space>
          </Title>
          <Table
            size="small"
            columns={recentColumns}
            dataSource={recentRows}
            pagination={false}
            scroll={{ x: 'max-content' }}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space orientation="vertical" size={2}>
                      <Text type="secondary">No recent calls.</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Calls will appear here as they are recorded.
                      </Text>
                    </Space>
                  }
                />
              ),
            }}
          />
        </div>
      </Space>
    </Card>
  );
}

// Local icon wrapper so the CPU/emerald theme stays consistent with
// ProviderSettings without importing a heavy icon set inline.
function CpuIcon() {
  return <span style={{ color: '#facc15' }}>◆</span>;
}
