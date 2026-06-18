/**
 * TTSSettingsPanel — voice, backend, and language configuration for TTS.
 *
 * Connects to GET/POST /api/v1/tts/config to display available backends,
 * speakers, voices, and languages. Allows switching between Edge TTS and
 * Qwen3-TTS backends, selecting voices, and configuring speech rate.
 *
 * Used by: BuddhaContemplationWidget, Narrative display, Saka Dawa banner
 *
 * @component
 */
import React, { useState, useEffect } from 'react';
import {
  Volume2, Zap, Cpu, Mic, Languages, Settings,
  RefreshCw, Check, ChevronDown,
} from 'lucide-react';
import { Card, Select, Slider, Button, Switch, Tag, Space, Typography, Divider, Spin, Empty, message } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';

const { Text, Title } = Typography;

export default function TTSSettingsPanel({ onConfigChange, compact = false }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Local form state
  const [backend, setBackend] = useState('auto');
  const [edgeVoice, setEdgeVoice] = useState('zh-CN-YunxiNeural');
  const [edgeRate, setEdgeRate] = useState('-25%');
  const [qwenModel, setQwenModel] = useState('Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice');
  const [qwenSpeaker, setQwenSpeaker] = useState('Uncle_Fu');
  const [qwenLanguage, setQwenLanguage] = useState('Chinese');

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/tts/config`);
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
        // Sync local state from server config
        const cc = data.current_config || {};
        setBackend(cc.backend || 'auto');
        setEdgeVoice(cc.edge_voice || 'zh-CN-YunxiNeural');
        setEdgeRate(cc.edge_rate || '-25%');
        setQwenModel(cc.qwen_model || 'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice');
        setQwenSpeaker(cc.qwen_speaker || 'Uncle_Fu');
        setQwenLanguage(cc.qwen_language || 'Chinese');
      }
    } catch {}
    setLoading(false);
  };

  const saveConfig = async (updates = {}) => {
    setSaving(true);
    try {
      const body = { ...updates };
      if (!updates.backend) body.backend = backend;
      if (!updates.edge_voice) body.edge_voice = edgeVoice;
      if (!updates.edge_rate) body.edge_rate = edgeRate;
      if (!updates.qwen_model) body.qwen_model = qwenModel;
      if (!updates.qwen_speaker) body.qwen_speaker = qwenSpeaker;
      if (!updates.qwen_language) body.qwen_language = qwenLanguage;

      const res = await fetch(`/api/v1/tts/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        message.success('TTS settings saved');
        audioFeedback.playSuccess();
        const data = await res.json();
        if (onConfigChange) onConfigChange(data);
      }
    } catch {}
    setSaving(false);
  };

  if (loading) return <Spin size="small" />;
  if (!config) return <Empty description="TTS unavailable" />;

  const qwenAvail = config.qwen?.available;
  const edgeVoices = config.edge?.voices || [];
  const qwenSpeakers = config.qwen?.speakers || [];
  const qwenRitual = config.qwen?.ritual_speakers || {};
  const qwenDesignPresets = config.qwen?.voice_design_presets || [];
  const qwenModels = config.qwen?.models || {};
  const gpuInfo = config.gpu || { gpu_available: false, backend: 'cpu', devices: [] };

  const rateOptions = {
    '-50%': 'Very Slow', '-35%': 'Slow (Sacred)', '-25%': 'Moderate (Sutra)',
    '-10%': 'Slightly Slow', '+0%': 'Normal', '+20%': 'Fast',
  };

  if (compact) {
    // Compact inline version for embedding in widgets
    return (
      <Space size="small" wrap>
        <Select
          size="small"
          value={backend}
          onChange={v => { setBackend(v); saveConfig({ backend: v }); }}
          style={{ width: 100 }}
          options={[
            { value: 'auto', label: '🤖 Auto' },
            { value: 'edge', label: '⚡ Edge' },
            { value: 'qwen', label: qwenAvail ? '🧠 Qwen' : '🧠 Qwen (N/A)', disabled: !qwenAvail },
          ]}
        />
        {backend === 'qwen' || (backend === 'auto' && qwenAvail) ? (
          <Select
            size="small"
            value={qwenSpeaker}
            onChange={v => { setQwenSpeaker(v); saveConfig({ qwen_speaker: v }); }}
            style={{ width: 130 }}
            options={qwenSpeakers.map(s => ({ value: s.id, label: `${s.id} (${s.native})` }))}
          />
        ) : (
          <Select
            size="small"
            value={edgeVoice}
            onChange={v => { setEdgeVoice(v); saveConfig({ edge_voice: v }); }}
            style={{ width: 180 }}
            options={edgeVoices.map(v => ({ value: v.id, label: `${v.id.split('-').pop()} (${v.style})` }))}
          />
        )}
        <Button size="small" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchConfig} />
      </Space>
    );
  }

  // Full panel
  return (
    <Card
      size="small"
      title={<Space><Volume2 className="w-4 h-4 text-cyan-400" /><Text strong>Text-to-Speech Settings</Text></Space>}
      extra={
        <Button size="small" icon={<RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />}
          onClick={fetchConfig} loading={loading}>Refresh</Button>
      }
    >
      <Space direction="vertical" className="w-full" size="middle">
        {/* Backend Selection */}
        <div>
          <Text strong style={{ fontSize: 12 }}>TTS Backend</Text>
          <Select
            value={backend}
            onChange={v => { setBackend(v); saveConfig({ backend: v }); }}
            className="w-full"
            style={{ marginTop: 4 }}
            options={[
              { value: 'auto', label: '🤖 Auto-detect (GPU → Qwen, CPU → Edge)' },
              { value: 'edge', label: '⚡ Edge TTS — Fast, no GPU, Chinese-optimized' },
              { value: 'qwen', label: '🧠 Qwen3-TTS — Neural, voice design/clone, 10 languages', disabled: !qwenAvail },
            ]}
          />
          {!qwenAvail && (
            <Text type="secondary" style={{ fontSize: 10 }}>
              Qwen3-TTS requires NVIDIA GPU + <code>pip install qwen-tts</code>
            </Text>
          )}
        </div>

        <Divider style={{ margin: '4px 0' }} />

        {/* Edge TTS Settings */}
        {(backend === 'edge' || backend === 'auto') && (
          <>
            <Text strong style={{ fontSize: 12, color: '#06b6d4' }}>⚡ Edge TTS Voice</Text>
            <Select
              value={edgeVoice}
              onChange={v => { setEdgeVoice(v); saveConfig({ edge_voice: v }); }}
              className="w-full"
              options={edgeVoices.map(v => ({
                value: v.id,
                label: `${v.id} — ${v.description} (${v.gender}, ${v.style})`,
              }))}
            />
            <div>
              <Text style={{ fontSize: 11 }}>Speech Rate: {edgeRate} ({rateOptions[edgeRate] || edgeRate})</Text>
              <Slider
                min={0} max={5} step={1}
                value={['-50%','-35%','-25%','-10%','+0%','+20%'].indexOf(edgeRate)}
                onChange={i => {
                  const rates = ['-50%','-35%','-25%','-10%','+0%','+20%'];
                  setEdgeRate(rates[i]);
                }}
                onAfterChange={() => saveConfig({ edge_rate: edgeRate })}
                marks={{
                  0: 'Very Slow', 1: 'Slow', 2: 'Sutra', 3: 'Moderate', 4: 'Normal', 5: 'Fast',
                }}
              />
            </div>
          </>
        )}

        {/* Qwen3-TTS Settings */}
        {(backend === 'qwen' || backend === 'auto') && qwenAvail && (
          <>
            <Text strong style={{ fontSize: 12, color: '#a855f7' }}>🧠 Qwen3-TTS Model</Text>
            <Select
              value={qwenModel}
              onChange={v => { setQwenModel(v); saveConfig({ qwen_model: v }); }}
              className="w-full"
              options={Object.entries(qwenModels).map(([label, value]) => ({
                value, label: `${label} — ${value}`,
              }))}
            />

            <Text strong style={{ fontSize: 12, color: '#a855f7' }}>Speaker</Text>
            <Select
              value={qwenSpeaker}
              onChange={v => { setQwenSpeaker(v); saveConfig({ qwen_speaker: v }); }}
              className="w-full"
              options={qwenSpeakers.map(s => ({
                value: s.id,
                label: `${s.id} — ${s.description} (${s.native}, ${s.gender} ${s.age})`,
              }))}
            />

            {/* Ritual speaker quick picks */}
            <div>
              <Text style={{ fontSize: 10 }}>Ritual Presets:</Text>
              <Space wrap size={[4, 4]} style={{ marginTop: 4 }}>
                {Object.entries(qwenRitual).map(([role, speaker]) => (
                  <Tag
                    key={role}
                    color={qwenSpeaker === speaker ? 'purple' : 'default'}
                    style={{ cursor: 'pointer' }}
                    onClick={() => { setQwenSpeaker(speaker); saveConfig({ qwen_speaker: speaker }); }}
                  >
                    {role.replace(/_/g, ' ')} → {speaker}
                  </Tag>
                ))}
              </Space>
            </div>

            <div>
              <Text strong style={{ fontSize: 12 }}>Language</Text>
              <Select
                value={qwenLanguage}
                onChange={v => { setQwenLanguage(v); saveConfig({ qwen_language: v }); }}
                className="w-full"
                style={{ marginTop: 4 }}
                options={(config.qwen?.languages || ['Chinese','English']).map(l => ({ value: l, label: l }))}
              />
            </div>

            {/* Voice Design Presets */}
            {qwenDesignPresets.length > 0 && (
              <div>
                <Text style={{ fontSize: 10 }}>Voice Design Presets (requires 1.7B-Design model):</Text>
                <Space wrap size={[4, 4]} style={{ marginTop: 4 }}>
                  {qwenDesignPresets.map(p => (
                    <Tag key={p} style={{ fontSize: 9, cursor: 'pointer' }}
                      onClick={() => message.info(`Voice design: ${p.replace(/_/g, ' ')}`)}>
                      {p.replace(/_/g, ' ')}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
          </>
        )}

        <Divider style={{ margin: '4px 0' }} />

        <Button
          type="primary"
          block
          icon={<Check className="w-4 h-4" />}
          onClick={() => saveConfig()}
          loading={saving}
        >
          Apply TTS Settings
        </Button>

        {/* Current status */}
        <Text type="secondary" style={{ fontSize: 10 }}>
          Active: <Tag color="cyan">{config.active_backend}</Tag>
          {config.active_backend === 'edge' && <span>Voice: {edgeVoice} @ {edgeRate}</span>}
          {config.active_backend === 'qwen' && <span>Speaker: {qwenSpeaker} | {qwenLanguage}</span>}
        </Text>

        {/* GPU / ROCm Status */}
        <div style={{ background: gpuInfo.gpu_available ? '#064e3b20' : '#1e293b', borderRadius: 8, padding: '8px 12px', border: '1px solid ' + (gpuInfo.gpu_available ? '#065f4630' : '#334155') }}>
          <Space size={4}>
            <Tag color={gpuInfo.gpu_available ? 'green' : 'default'} style={{ fontSize: 10 }}>
              {gpuInfo.gpu_available
                ? `🎮 ${gpuInfo.backend} GPU`
                : '💻 CPU Only'}
            </Tag>
            {gpuInfo.devices?.map(d => (
              <Tag key={d.id} color="purple" style={{ fontSize: 10 }}>
                {d.name} ({d.vram_gb}GB)
              </Tag>
            ))}
          </Space>
          {!gpuInfo.gpu_available && (
            <Text type="secondary" style={{ fontSize: 9, display: 'block', marginTop: 4 }}>
              Install ROCm PyTorch for AMD GPU: <code style={{ fontSize: 9 }}>pip install torch --index-url https://download.pytorch.org/whl/rocm6.0</code>
              <br />Then: <code style={{ fontSize: 9 }}>pip install qwen-tts</code> for Qwen3-TTS neural voices.
            </Text>
          )}
        </div>
      </Space>
    </Card>
  );
}
