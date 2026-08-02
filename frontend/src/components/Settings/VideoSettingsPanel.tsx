/**
 * VideoSettingsPanel — MiniMax video generation settings + test harness.
 *
 * Layout:
 *   - Configuration card (enable, model, duration, resolution, caps, prefix)
 *   - Cost display (daily spend, hourly calls, progress bar)
 *   - Test generation card (prompt textarea, confirmation modal, polling)
 *
 * The MiniMax video API is async: POST /generate returns a task_id, then we
 * poll POST /status every 5s until the video is ready (or fails). On success
 * we embed the returned MiniMax CDN video_url in a native <video> element.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Switch,
  Select,
  InputNumber,
  Input,
  Button,
  Modal,
  Progress,
  Alert,
  Space,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  message,
  Spin,
  Divider,
} from 'antd';
import {
  Video as VideoIcon,
  DollarSign,
  Gauge,
  Save,
  Wand2,
  Download,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { apiUrl } from '../../utils/api';

const { Title, Text, Paragraph } = Typography;

interface VideoConfig {
  enabled: boolean;
  default_model: string;
  default_duration: number;
  default_resolution: string;
  daily_cost_cap_usd: number;
  max_per_hour: number;
  prompt_style_prefix: string;
  prompt_optimizer: boolean;
}

interface CostStats {
  daily_spend_usd: number;
  hourly_calls: number;
  max_per_hour: number;
}

interface VideoModelInfo {
  id: string;
  cost_usd: number;
  label: string;
  durations: number[];
  resolutions: string[];
  ratios?: string[];
}

interface StatusResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'done' | 'failed' | string;
  video_url?: string;
  local_path?: string;
  download_error?: string;
  error?: string;
}

const EMPTY_CONFIG: VideoConfig = {
  enabled: false,
  default_model: 'T2V-01',
  default_duration: 6,
  default_resolution: '720P',
  daily_cost_cap_usd: 2.0,
  max_per_hour: 2,
  prompt_style_prefix: '',
  prompt_optimizer: true,
};

const PROMPT_MIN = 10;
const PROMPT_MAX = 2000;
const POLL_INTERVAL_MS = 5000;

export default function VideoSettingsPanel() {
  const [config, setConfig] = useState<VideoConfig>(EMPTY_CONFIG);
  const [stats, setStats] = useState<CostStats | null>(null);
  const [models, setModels] = useState<VideoModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [testPrompt, setTestPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [currentTask, setCurrentTask] = useState<{
    task_id: string;
    model: string;
  } | null>(null);
  const [taskStatus, setTaskStatus] = useState<StatusResponse | null>(null);
  const pollRef = useRef<number | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cfgRes, modelsRes] = await Promise.all([
        fetch(apiUrl('/videos/config')),
        fetch(apiUrl('/videos/models')),
      ]);
      if (cfgRes.ok) {
        const data = await cfgRes.json();
        setConfig({ ...EMPTY_CONFIG, ...data.config });
        setStats(data.cost_stats ?? null);
      }
      if (modelsRes.ok) {
        const data = await modelsRes.json();
        setModels(data);
      }
    } catch (err) {
      console.warn('VideoSettingsPanel: failed to fetch', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
      }
    };
  }, []);

  const saveField = async (field: keyof VideoConfig, value: unknown): Promise<void> => {
    setSaving(true);
    try {
      const res = await fetch(apiUrl('/videos/config'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        message.error(`Save failed: ${err.detail ?? 'unknown error'}`);
        return;
      }
      const data = await res.json();
      setConfig((c) => ({ ...c, ...data.config }));
      setStats(data.cost_stats ?? null);
      message.success('Saved');
    } catch (err) {
      message.error(`Save failed: ${String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollOnce = useCallback(async (taskId: string, model: string) => {
    try {
      const res = await fetch(apiUrl('/videos/status'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, model }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        setTaskStatus({
          task_id: taskId,
          status: 'failed',
          error: err.detail ?? `HTTP ${res.status}`,
        });
        stopPolling();
        return;
      }
      const data = (await res.json()) as StatusResponse;
      setTaskStatus(data);
      if (data.status === 'done' || data.status === 'failed') {
        stopPolling();
        setGenerating(false);
        // Refresh cost stats after a finished generation
        fetchAll();
      }
    } catch (err) {
      setTaskStatus({
        task_id: taskId,
        status: 'failed',
        error: String(err),
      });
      stopPolling();
      setGenerating(false);
    }
  }, [stopPolling, fetchAll]);

  const startPolling = useCallback((taskId: string, model: string) => {
    stopPolling();
    void pollOnce(taskId, model);
    pollRef.current = window.setInterval(() => {
      void pollOnce(taskId, model);
    }, POLL_INTERVAL_MS);
  }, [pollOnce, stopPolling]);

  const submitGeneration = useCallback(async () => {
    const prompt = testPrompt.trim();
    if (prompt.length < PROMPT_MIN) {
      message.warning(`Prompt must be at least ${PROMPT_MIN} characters`);
      return;
    }
    setGenerating(true);
    setTaskStatus(null);
    try {
      const res = await fetch(apiUrl('/videos/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        message.error(`Generate failed: ${err.detail ?? 'unknown error'}`);
        setGenerating(false);
        return;
      }
      const data = (await res.json()) as {
        task_id: string;
        model: string;
        cost_usd: number;
        prompt: string;
      };
      setCurrentTask({ task_id: data.task_id, model: data.model });
      setTaskStatus({
        task_id: data.task_id,
        status: 'pending',
      });
      startPolling(data.task_id, data.model);
    } catch (err) {
      message.error(`Generate failed: ${String(err)}`);
      setGenerating(false);
    }
  }, [testPrompt, startPolling]);

  const selectedModel: VideoModelInfo | undefined = models.find(
    (m) => m.id === config.default_model,
  );
  const availableDurations = selectedModel?.durations ?? [];
  const availableResolutions = selectedModel?.resolutions ?? [];
  const estimatedCost = selectedModel?.cost_usd ?? 0;
  const dailySpend = stats?.daily_spend_usd ?? 0;
  const dailyCap = stats?.daily_spend_usd
    ? config.daily_cost_cap_usd
    : config.daily_cost_cap_usd;
  const capPercent =
    dailyCap > 0 ? Math.min(100, (dailySpend / dailyCap) * 100) : 0;
  const promptLength = testPrompt.length;
  const promptValid =
    promptLength >= PROMPT_MIN && promptLength <= PROMPT_MAX && testPrompt.trim().length >= PROMPT_MIN;

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* Header */}
      <Card size="small" loading={loading}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space size={10} align="center">
            <VideoIcon size={18} className="text-pink-400" />
            <Title level={5} style={{ margin: 0 }}>
              Video Generation
            </Title>
            <Tag color={config.enabled ? 'green' : 'default'}>
              {config.enabled ? 'Enabled' : 'Disabled'}
            </Tag>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            MiniMax · async task + 5s polling
          </Text>
        </div>
      </Card>

      {/* Configuration */}
      <Card size="small" title="Configuration" loading={loading}>
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Text strong>Enable Video Generation</Text>
            <Switch
              checked={config.enabled}
              loading={saving}
              onChange={(checked) => saveField('enabled', checked)}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {config.enabled
                ? 'Generation endpoints are live'
                : 'All generation calls will be rejected'}
            </Text>
          </div>

          <Divider style={{ margin: '4px 0' }} />

          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12}>
              <Text strong>Model</Text>
              <Select
                value={config.default_model}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => saveField('default_model', v)}
                loading={loading && models.length === 0}
                options={models.map((m) => ({
                  value: m.id,
                  label: `${m.label} ($${m.cost_usd.toFixed(2)}/video)`,
                }))}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Text strong>Duration (s)</Text>
              <Select
                value={config.default_duration}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => saveField('default_duration', v)}
                options={availableDurations.map((d) => ({ value: d, label: `${d}s` }))}
                disabled={availableDurations.length === 0}
                placeholder={
                  availableDurations.length === 0 ? 'Pick a model first' : undefined
                }
              />
            </Col>
            <Col xs={12} sm={6}>
              <Text strong>Resolution</Text>
              <Select
                value={config.default_resolution}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => saveField('default_resolution', v)}
                options={availableResolutions.map((r) => ({ value: r, label: r }))}
                disabled={availableResolutions.length === 0}
                placeholder={
                  availableResolutions.length === 0 ? 'Pick a model first' : undefined
                }
              />
            </Col>
            <Col xs={12} sm={6}>
              <Text strong>Daily Cap (USD)</Text>
              <InputNumber
                value={config.daily_cost_cap_usd}
                min={0.01}
                max={100}
                step={0.25}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => v != null && saveField('daily_cost_cap_usd', v)}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Text strong>Max / Hour</Text>
              <InputNumber
                value={config.max_per_hour}
                min={1}
                max={1000}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => v != null && saveField('max_per_hour', v)}
              />
            </Col>
            <Col xs={24}>
              <Text strong>Prompt Style Prefix</Text>
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 11 }}>
                Prepended to every prompt. Max 500 chars.
              </Text>
              <Input.TextArea
                rows={2}
                placeholder="e.g. Cinematic 24fps, soft golden hour lighting, sacred geometry overlays, ethereal depth"
                value={config.prompt_style_prefix}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, prompt_style_prefix: e.target.value }))
                }
                style={{ marginTop: 4 }}
                maxLength={500}
                showCount
              />
              <Button
                type="primary"
                size="small"
                icon={<Save size={13} />}
                style={{ marginTop: 6 }}
                loading={saving}
                onClick={() =>
                  saveField('prompt_style_prefix', config.prompt_style_prefix)
                }
              >
                Save Prefix
              </Button>
            </Col>
          </Row>
        </Space>
      </Card>

      {/* Cost Display */}
      <Card size="small" title="Cost & Rate" loading={loading}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8}>
            <Statistic
              title="Today's Spend"
              value={dailySpend}
              precision={4}
              prefix={<DollarSign size={14} className="text-emerald-400" />}
              suffix={` / $${dailyCap.toFixed(2)}`}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="Hourly Calls"
              value={stats?.hourly_calls ?? 0}
              suffix={` / ${stats?.max_per_hour ?? config.max_per_hour}`}
              prefix={<Gauge size={14} className="text-blue-400" />}
            />
          </Col>
          <Col xs={24} sm={8}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Daily cap usage
            </Text>
            <Progress
              percent={Number(capPercent.toFixed(1))}
              size="small"
              status={capPercent >= 90 ? 'exception' : 'active'}
              strokeColor={capPercent >= 90 ? '#ef4444' : undefined}
            />
          </Col>
        </Row>
      </Card>

      {/* Test Generation */}
      <Card
        size="small"
        title={
          <Space size={6}>
            <Wand2 size={14} className="text-pink-400" />
            <Text strong>Test Generation</Text>
          </Space>
        }
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {!config.enabled && (
            <Alert
              type="warning"
              showIcon
              message="Video generation is disabled"
              description="Enable the toggle in Configuration above to submit test generations."
            />
          )}

          <div>
            <Text strong>Prompt</Text>
            <Text type="secondary" style={{ marginLeft: 8, fontSize: 11 }}>
              {PROMPT_MIN}–{PROMPT_MAX} characters. Style prefix above is auto-prepended.
            </Text>
            <Input.TextArea
              rows={4}
              placeholder="e.g. A slow cinematic pan across a Tibetan monastery at sunrise, golden light on prayer flags, snow-capped mountains in the background"
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              status={promptLength > PROMPT_MAX ? 'error' : undefined}
              style={{ marginTop: 4 }}
              maxLength={PROMPT_MAX}
              showCount
            />
            {promptLength < PROMPT_MIN && promptLength > 0 && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                {PROMPT_MIN - promptLength} more character{PROMPT_MIN - promptLength === 1 ? '' : 's'} needed
              </Text>
            )}
          </div>

          <Space size={12} align="center">
            <Button
              type="primary"
              icon={<Wand2 size={14} />}
              disabled={!config.enabled || !promptValid || generating}
              loading={generating}
              onClick={() => setConfirmOpen(true)}
            >
              Generate Video
            </Button>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Estimated cost: <Text strong>${estimatedCost.toFixed(2)}</Text> on {selectedModel?.label ?? config.default_model}
            </Text>
          </Space>

          {/* Task status / video preview */}
          {taskStatus && (
            <Card
              size="small"
              style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.1)' }}
              styles={{ body: { padding: 12 } }}
            >
              <Space direction="vertical" size={10} style={{ width: '100%' }}>
                <Space size={8} align="center">
                  <Text strong>Task:</Text>
                  <Text code style={{ fontSize: 11 }}>
                    {taskStatus.task_id}
                  </Text>
                  <Tag
                    color={
                      taskStatus.status === 'done'
                        ? 'green'
                        : taskStatus.status === 'failed'
                        ? 'red'
                        : 'blue'
                    }
                  >
                    {taskStatus.status.toUpperCase()}
                  </Tag>
                  {(taskStatus.status === 'pending' || taskStatus.status === 'processing') && (
                    <Spin size="small" />
                  )}
                </Space>

                {(taskStatus.status === 'pending' || taskStatus.status === 'processing') && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Generating... this typically takes 1–3 minutes.
                  </Text>
                )}

                {taskStatus.status === 'failed' && (
                  <Alert
                    type="error"
                    showIcon
                    icon={<AlertCircle size={14} />}
                    message="Generation failed"
                    description={taskStatus.error ?? taskStatus.download_error ?? 'Unknown error'}
                  />
                )}

                {taskStatus.status === 'done' && (
                  <Space direction="vertical" size={10} style={{ width: '100%' }}>
                    <Alert
                      type="success"
                      showIcon
                      icon={<CheckCircle2 size={14} />}
                      message="Video ready"
                      description={
                        taskStatus.local_path
                          ? `Saved to ${taskStatus.local_path} on the server.`
                          : 'Streamed from the MiniMax CDN.'
                      }
                    />
                    {taskStatus.video_url && (
                      <video
                        controls
                        src={taskStatus.video_url}
                        style={{
                          width: '100%',
                          maxHeight: 480,
                          borderRadius: 8,
                          background: 'rgba(0,0,0,0.4)',
                        }}
                      />
                    )}
                    {taskStatus.video_url && (
                      <a
                        href={taskStatus.video_url}
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button icon={<Download size={14} />}>Download from CDN</Button>
                      </a>
                    )}
                  </Space>
                )}
              </Space>
            </Card>
          )}
        </Space>
      </Card>

      {/* Confirmation Modal */}
      <Modal
        title="Confirm video generation"
        open={confirmOpen}
        onCancel={() => setConfirmOpen(false)}
        onOk={() => {
          setConfirmOpen(false);
          void submitGeneration();
        }}
        okText="Generate"
        cancelText="Cancel"
        okButtonProps={{ disabled: !config.enabled }}
      >
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Text>
            This will cost{' '}
            <Text strong style={{ color: '#fbbf24' }}>
              ${estimatedCost.toFixed(2)}
            </Text>
            .
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Model: <Text code>{selectedModel?.label ?? config.default_model}</Text>
            {' · '}Duration: <Text code>{config.default_duration}s</Text>
            {' · '}Resolution: <Text code>{config.default_resolution}</Text>
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Generation typically takes 1–3 minutes. Continue?
          </Text>
        </Space>
      </Modal>
    </Space>
  );
}
