/**
 * RitualMonitor — live view of the Autonomous Ritual Engine.
 *
 * Shows:
 * - Engine state (running/stopped/executing)
 * - Current ritual phase with animated progress
 * - Upcoming schedule (next 24h of planetary hours + favorable genres)
 * - Recent ritual history
 * - Merit accumulation stats (today + total)
 * - Start/Stop/Configure controls
 *
 * Live engine state arrives via WebSocket (RITUAL_ENGINE_STATUS broadcast →
 * ritualStatus from useWebSocketStable). History + merit are not broadcast
 * over WS, so a one-shot initial REST fetch is performed on mount and the
 * action handlers (start/stop/trigger) refetch after each mutation.
 * No periodic polling.
 *
 * Mutations: POST /api/v1/ritual/start, /stop, /trigger, /config
 *
 * @component
 */
import React, { useState, useEffect } from 'react';
import {
  Play, Square, Zap, Clock, Activity, Sparkles,
  Heart, TrendingUp, Settings, RefreshCw, Radio,
  Moon, Sun, ChevronRight,
} from 'lucide-react';
import {
  Card, Button, Tag, Space, Typography, Row, Col, Statistic,
  List, Switch, Select, Slider, InputNumber, Divider, Spin, Empty,
  Progress, message, Badge,
} from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';

const { Text, Title, Paragraph } = Typography;

const PHASE_ICONS = {
  preparation: Sparkles, invocation: Zap, broadcast: Radio, dedication: Heart,
};
const PHASE_LABELS = {
  preparation: 'Preparation', invocation: 'Invocation',
  broadcast: 'Broadcast', dedication: 'Dedication',
};
const QUALITY_COLORS = {
  excellent: 'green', good: 'cyan', challenging: 'orange',
  transmutative: 'purple', neutral: 'default',
};

export default function RitualMonitor({ compact = false }) {
  const { ritualStatus } = useWebSocketStable();
  const [restStatus, setRestStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);

  // One-shot initial fetch for full payload (status + history + merit).
  // Engine state updates flow in live via WS RITUAL_ENGINE_STATUS → ritualStatus.
  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`/api/v1/ritual/status`);
      if (res.ok) setRestStatus(await res.json());
    } catch {}
    setLoading(false);
  };

  const handleStart = async () => {
    setActionLoading(true);
    audioFeedback.playTelemetry();
    try {
      await fetch(`/api/v1/ritual/start`, { method: 'POST' });
      message.success('Ritual Engine started');
      await fetchStatus();
    } catch { message.error('Failed to start'); }
    setActionLoading(false);
  };

  const handleStop = async () => {
    setActionLoading(true);
    try {
      await fetch(`/api/v1/ritual/stop`, { method: 'POST' });
      message.success('Ritual Engine stopped');
      await fetchStatus();
    } catch { message.error('Failed to stop'); }
    setActionLoading(false);
  };

  const handleTrigger = async () => {
    setActionLoading(true);
    audioFeedback.playTelemetry();
    try {
      const res = await fetch(`/api/v1/ritual/trigger`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'executed') {
        message.success(`Ritual executed: ${data.ritual.practice_name}`);
      }
      await fetchStatus();
    } catch { message.error('Trigger failed'); }
    setActionLoading(false);
  };

  const s = ritualStatus || restStatus?.status || {};
  const isRunning = s.state === 'running' || s.state === 'executing';
  const isExecuting = s.state === 'executing';
  const history = restStatus?.history || [];
  const merit = restStatus?.merit || {};
  const schedule = s.schedule || [];

  if (loading) return <Spin><div className="py-10" /></Spin>;

  return (
    <Card
      size="small"
      title={
        <Space>
          <Activity className={`w-4 h-4 ${isRunning ? 'text-emerald-400 animate-pulse' : 'text-slate-500'}`} />
          <Text strong>Autonomous Ritual Engine</Text>
          <Badge
            status={isRunning ? 'processing' : 'default'}
            text={isExecuting ? 'EXECUTING' : isRunning ? 'RUNNING' : 'STOPPED'}
          />
        </Space>
      }
      extra={
        <Space>
          <Button size="small" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchStatus} />
          {isRunning ? (
            <Button size="small" danger icon={<Square className="w-3 h-3" />} onClick={handleStop} loading={actionLoading}>Stop</Button>
          ) : (
            <Button size="small" type="primary" icon={<Play className="w-3 h-3" />} onClick={handleStart} loading={actionLoading}>Start</Button>
          )}
          <Button size="small" icon={<Zap className="w-3 h-3" />} onClick={handleTrigger} loading={actionLoading} disabled={isExecuting}>
            Trigger Now
          </Button>
        </Space>
      }
    >
      <Row gutter={[16, 16]}>
        {/* Merit Stats */}
        <Col xs={12} sm={6}>
          <Statistic
            title="Today's Merit"
            value={merit.today_merit || 0}
            suffix="pts"
            valueStyle={{ color: '#f59e0b', fontSize: 20 }}
            prefix={<Heart className="w-4 h-4" />}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="Today's Rituals"
            value={merit.today_rituals || 0}
            valueStyle={{ color: '#06b6d4', fontSize: 20 }}
            prefix={<Sparkles className="w-4 h-4" />}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="Total Merit"
            value={merit.total_merit || 0}
            suffix="pts"
            valueStyle={{ color: '#a855f7', fontSize: 20 }}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="Total Rituals"
            value={merit.total_rituals || 0}
            valueStyle={{ color: '#ec4899', fontSize: 20 }}
          />
        </Col>
      </Row>

      <Divider style={{ margin: '12px 0' }} />

      {/* Current Ritual (if executing) */}
      {isExecuting && s.current_ritual && (
        <div className="bg-purple-950/20 border border-purple-500/20 rounded-lg p-3 mb-3">
          <Space>
            <Zap className="w-4 h-4 text-purple-400 animate-pulse" />
            <Text strong style={{ color: '#c084fc' }}>
              Now Executing: {s.current_ritual.practice_name}
            </Text>
            <Tag color={QUALITY_COLORS[s.current_ritual.timing_quality] || 'default'}>
              {s.current_ritual.planetary_hour} hour
            </Tag>
          </Space>
          {s.current_ritual.narrative_preview && (
            <Paragraph type="secondary" style={{ fontSize: 10, marginTop: 4 }} ellipsis={{ rows: 1 }}>
              {s.current_ritual.narrative_preview}
            </Paragraph>
          )}
        </div>
      )}

      {/* Upcoming Schedule */}
      {!compact && schedule.length > 0 && (
        <div className="mb-3">
          <Text strong style={{ fontSize: 11 }}>Next 24h Schedule</Text>
          <div className="flex gap-1 mt-1 overflow-x-auto pb-1" style={{ maxWidth: '100%' }}>
            {schedule.slice(0, 12).map((h, i) => (
              <div key={i} className="flex-shrink-0 text-center px-2 py-1 rounded bg-slate-800/50 border border-slate-700/30" style={{ minWidth: 60 }}>
                <Text style={{ fontSize: 9, display: 'block' }}>+{h.hour_offset}h</Text>
                <Text strong style={{ fontSize: 10, display: 'block', color: h.favorable_genres.length > 0 ? '#a78bfa' : '#64748b' }}>
                  {h.planet}
                </Text>
                {h.favorable_genres.slice(0, 2).map(g => (
                  <Tag key={g} color="purple" style={{ fontSize: 7, margin: '1px 0', padding: '0 3px' }}>{g}</Tag>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent History */}
      {history.length > 0 && (
        <div>
          <Text strong style={{ fontSize: 11 }}>Recent Rituals</Text>
          <List
            size="small"
            dataSource={history.slice(0, compact ? 3 : 10)}
            renderItem={r => (
              <List.Item>
                <List.Item.Meta
                  avatar={
                    <Tag color={QUALITY_COLORS[r.timing_quality] || 'default'} style={{ fontSize: 9 }}>
                      {r.planetary_hour}
                    </Tag>
                  }
                  title={
                    <Space size={4}>
                      <Text style={{ fontSize: 11 }}>{r.practice_name}</Text>
                      <Tag color="gold" style={{ fontSize: 8 }}>×{r.merit_multiplier}</Tag>
                      {r.tts_generated && <Tag color="cyan" style={{ fontSize: 8 }}>TTS</Tag>}
                    </Space>
                  }
                  description={
                    <Text type="secondary" style={{ fontSize: 9 }}>
                      {r.completed_at?.slice(11, 16)} · {r.narrative_length} chars
                    </Text>
                  }
                />
              </List.Item>
            )}
          />
        </div>
      )}

      {history.length === 0 && !isExecuting && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No rituals executed yet. Start the engine or trigger a ritual manually."
        />
      )}
    </Card>
  );
}
