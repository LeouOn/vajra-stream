/**
 * ImageSettingsPanel — provider-agnostic image generation settings.
 *
 * Wraps the backend ImageGenerationService (modular — see
 * docs/image-generation-extract.md). Cost-controlled, cached, and
 * rate-limited. Off by default.
 *
 * Layout:
 *   - Cost stats summary (daily spend / cap / hourly calls / cache)
 *   - Toggle enabled + provider + model + budget caps
 *   - API keys (masked) — OpenRouter + MiniMax
 *   - Prompt validator sandbox
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Switch,
  Select,
  InputNumber,
  Input,
  Button,
  Space,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  Alert,
  message,
  Tooltip,
  Divider,
} from 'antd';
import {
  ImageIcon,
  DollarSign,
  Gauge,
  Database,
  Save,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { apiUrl } from '../../utils/api';

const { Title, Text, Paragraph } = Typography;

interface ImageConfig {
  enabled: boolean;
  default_provider: string;
  default_model: string;
  daily_cost_cap_usd: number;
  max_images_per_call: number;
  max_per_hour: number;
  cache_ttl_seconds: number;
  max_prompt_tokens: number;
  openrouter_api_key: string;
  minimax_api_key: string;
}

interface CostStats {
  daily_spend_usd: number;
  daily_cost_cap_usd: number;
  hourly_calls: number;
  max_per_hour: number;
  cache_entries: number;
}

interface ModelsByProvider {
  openrouter: Array<{ id: string; cost_usd: number; label: string }>;
  minimax: Array<{ id: string; cost_usd: number; label: string }>;
}

interface ValidationResponse {
  ok: boolean;
  estimated_tokens: number;
  error?: string;
  suggestion?: string;
}

const EMPTY_CONFIG: ImageConfig = {
  enabled: false,
  default_provider: 'openrouter',
  default_model: 'google/gemini-3.1-flash-lite-image',
  daily_cost_cap_usd: 0.5,
  max_images_per_call: 3,
  max_per_hour: 10,
  cache_ttl_seconds: 3600,
  max_prompt_tokens: 1000,
  openrouter_api_key: '',
  minimax_api_key: '',
};

export default function ImageSettingsPanel() {
  const [config, setConfig] = useState<ImageConfig>(EMPTY_CONFIG);
  const [stats, setStats] = useState<CostStats | null>(null);
  const [models, setModels] = useState<ModelsByProvider>({ openrouter: [], minimax: [] });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testPrompt, setTestPrompt] = useState('');
  const [validation, setValidation] = useState<ValidationResponse | null>(null);
  const [orKeyInput, setOrKeyInput] = useState('');
  const [mmKeyInput, setMmKeyInput] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cfgRes, modelsRes] = await Promise.all([
        fetch(apiUrl('/images/config')),
        fetch(apiUrl('/images/models')),
      ]);
      if (cfgRes.ok) {
        const data = await cfgRes.json();
        setConfig({ ...EMPTY_CONFIG, ...data.config });
        setStats(data.cost_stats ?? null);
      }
      if (modelsRes.ok) {
        setModels(await modelsRes.json());
      }
    } catch (err) {
      console.warn('ImageSettingsPanel: failed to fetch', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 15000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const saveField = async (field: keyof ImageConfig, value: unknown) => {
    setSaving(true);
    try {
      const res = await fetch(apiUrl('/images/config'), {
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

  const handleApiKeySave = async (provider: 'openrouter' | 'minimax') => {
    const key = provider === 'openrouter' ? orKeyInput.trim() : mmKeyInput.trim();
    if (!key) {
      message.warning('Enter an API key first');
      return;
    }
    await saveField(
      provider === 'openrouter' ? 'openrouter_api_key' : 'minimax_api_key',
      key,
    );
    if (provider === 'openrouter') setOrKeyInput('');
    else setMmKeyInput('');
  };

  const validateTestPrompt = async () => {
    if (!testPrompt.trim()) {
      message.warning('Enter a test prompt');
      return;
    }
    try {
      const res = await fetch(apiUrl('/images/validate_prompt'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: testPrompt }),
      });
      if (!res.ok) {
        message.error('Validation failed');
        return;
      }
      setValidation(await res.json());
    } catch (err) {
      message.error(`Validation failed: ${String(err)}`);
    }
  };

  const providerModels =
    config.default_provider === 'minimax' ? models.minimax : models.openrouter;

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* Header */}
      <Card size="small" loading={loading}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space size={10} align="center">
            <ImageIcon size={18} className="text-purple-400" />
            <Title level={5} style={{ margin: 0 }}>
              Image Generation
            </Title>
            <Tag color={config.enabled ? 'green' : 'default'}>
              {config.enabled ? 'Enabled' : 'Disabled'}
            </Tag>
          </Space>
          <Space size={8} align="center">
            <Text type="secondary" style={{ fontSize: 12 }}>
              Provider-agnostic · OpenRouter · MiniMax
            </Text>
            <Tooltip title="Cost-controlled, cached, rate-limited · OFF by default">
              <Sparkles size={13} className="text-gray-400" />
            </Tooltip>
          </Space>
        </div>
      </Card>

      <Alert
        type="warning"
        showIcon
        message="Provider integration not yet verified against live APIs"
        description={
          <Paragraph style={{ margin: 0, fontSize: 12 }} type="secondary">
            The OpenRouter and MiniMax HTTP contracts (endpoint paths, request bodies,
            response parsers) are implemented from documented specs but have not been
            round-trip tested with real API keys yet. If generation fails with a parse
            error or unexpected response shape, report the response payload so the
            parser can be adjusted.
          </Paragraph>
        }
      />

      {/* Cost Stats */}
      <Card size="small" loading={loading}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic
              title="Today's Spend"
              value={stats?.daily_spend_usd ?? 0}
              precision={4}
              prefix={<DollarSign size={14} className="text-emerald-400" />}
              suffix={` / $${(stats?.daily_cost_cap_usd ?? 0).toFixed(2)}`}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Hourly Calls"
              value={stats?.hourly_calls ?? 0}
              suffix={` / ${stats?.max_per_hour ?? 0}`}
              prefix={<Gauge size={14} className="text-blue-400" />}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Cache Entries"
              value={stats?.cache_entries ?? 0}
              prefix={<Database size={14} className="text-purple-400" />}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Max / Call"
              value={config.max_images_per_call}
              prefix={<ImageIcon size={14} className="text-amber-400" />}
            />
          </Col>
        </Row>
      </Card>

      {/* Configuration */}
      <Card size="small" title="Configuration" loading={loading}>
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Text strong>Enable Image Generation</Text>
            <Switch
              checked={config.enabled}
              loading={saving}
              onChange={(checked) => saveField('enabled', checked)}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {config.enabled
                ? 'LLM tools and HTTP endpoints may generate images'
                : 'All image generation is blocked'}
            </Text>
          </div>

          <Divider style={{ margin: '4px 0' }} />

          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12}>
              <Text strong>Default Provider</Text>
              <Select
                value={config.default_provider}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => saveField('default_provider', v)}
                options={[
                  { value: 'openrouter', label: 'OpenRouter (cheap, many models)' },
                  { value: 'minimax', label: 'MiniMax (subject_reference support)' },
                ]}
              />
            </Col>
            <Col xs={24} sm={12}>
              <Text strong>Default Model</Text>
              <Select
                value={config.default_model}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => saveField('default_model', v)}
                options={providerModels.map((m) => ({
                  value: m.id,
                  label: `${m.label} ($${m.cost_usd.toFixed(3)}/img)`,
                }))}
                showSearch
              />
            </Col>
            <Col xs={12} sm={6}>
              <Text strong>Daily Cap ($)</Text>
              <InputNumber
                value={config.daily_cost_cap_usd}
                min={0.01}
                max={100}
                step={0.05}
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
            <Col xs={12} sm={6}>
              <Text strong>Max / Call</Text>
              <InputNumber
                value={config.max_images_per_call}
                min={1}
                max={10}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => v != null && saveField('max_images_per_call', v)}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Text strong>Prompt Token Cap</Text>
              <InputNumber
                value={config.max_prompt_tokens}
                min={100}
                max={4000}
                step={100}
                style={{ width: '100%', marginTop: 4 }}
                onChange={(v) => v != null && saveField('max_prompt_tokens', v)}
              />
            </Col>
          </Row>
        </Space>
      </Card>

      {/* API Keys */}
      <Card size="small" title="API Keys" loading={loading}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Alert
            type="info"
            showIcon
            message="Keys are stored in the local Vajra.Stream SQLite DB"
            description={
              <Paragraph style={{ margin: 0, fontSize: 12 }} type="secondary">
                Keys never leave this machine — they are sent directly to the
                provider's API on each generation request. Get an OpenRouter key
                at <a href="https://openrouter.ai" target="_blank" rel="noopener">openrouter.ai</a>;
                MiniMax at <a href="https://www.minimax.io" target="_blank" rel="noopener">minimax.io</a>.
              </Paragraph>
            }
          />

          <div>
            <Text strong>OpenRouter API Key</Text>
            <Text type="secondary" style={{ marginLeft: 8 }}>
              Current: <code>{config.openrouter_api_key || '(not set)'}</code>
            </Text>
            <Input.Password
              placeholder="sk-or-v1-..."
              value={orKeyInput}
              onChange={(e) => setOrKeyInput(e.target.value)}
              style={{ marginTop: 4 }}
            />
            <Button
              type="primary"
              size="small"
              icon={<Save size={13} />}
              style={{ marginTop: 6 }}
              loading={saving}
              onClick={() => handleApiKeySave('openrouter')}
            >
              Update OpenRouter Key
            </Button>
          </div>

          <div>
            <Text strong>MiniMax API Key</Text>
            <Text type="secondary" style={{ marginLeft: 8 }}>
              Current: <code>{config.minimax_api_key || '(not set)'}</code>
            </Text>
            <Input.Password
              placeholder="sk-mm-..."
              value={mmKeyInput}
              onChange={(e) => setMmKeyInput(e.target.value)}
              style={{ marginTop: 4 }}
            />
            <Button
              type="primary"
              size="small"
              icon={<Save size={13} />}
              style={{ marginTop: 6 }}
              loading={saving}
              onClick={() => handleApiKeySave('minimax')}
            >
              Update MiniMax Key
            </Button>
          </div>
        </Space>
      </Card>

      {/* Prompt Validator Sandbox */}
      <Card size="small" title="Prompt Token Estimator">
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Paste a prompt to estimate tokens before sending it to the API.
            30-60 words is ideal; the configured cap is{' '}
            <code>{config.max_prompt_tokens}</code> tokens.
          </Paragraph>
          <Input.TextArea
            rows={4}
            placeholder="e.g. Heart chakra mandala, golden sacred geometry, soft cyan and magenta rays, intricate lotus petals, glowing center, dark velvet background"
            value={testPrompt}
            onChange={(e) => setTestPrompt(e.target.value)}
          />
          <Button
            type="default"
            icon={<Sparkles size={13} />}
            loading={saving}
            onClick={validateTestPrompt}
          >
            Estimate Tokens
          </Button>
          {validation && (
            <Alert
              type={validation.ok ? 'success' : 'warning'}
              showIcon
              icon={validation.ok ? <CheckCircle2 size={14} /> : undefined}
              message={
                validation.ok
                  ? `OK — estimated ${validation.estimated_tokens} tokens`
                  : validation.error
              }
              description={validation.suggestion ? `Try: ${validation.suggestion}` : undefined}
            />
          )}
        </Space>
      </Card>
    </Space>
  );
}
