/**
 * AudioSettings — quality selection for TTS-recited Buddha names.
 *
 * A simple Select with three presets (low / medium / high) controlling the
 * trade-off between audio fidelity and bandwidth / latency when the backend
 * chants each Buddha name via the TTS provider. The choice is persisted to
 * localStorage (`vajra-buddha-audio-quality`) so it survives reloads. Pure
 * client-side preference; no polling and no backend round-trip required to
 * render. The parent route is responsible for passing the selected value
 * into any future TTS request body.
 *
 * @component
 * @param {Object}   props
 * @param {string}   [props.value]    Controlled current quality ('low' | 'medium' | 'high').
 * @param {function} [props.onChange] Callback fired with the new quality string.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card, Select, Typography, Space, Tag } from 'antd';
import { Volume2, Gauge } from 'lucide-react';

const { Text, Title } = Typography;
const STORAGE_KEY = 'vajra-buddha-audio-quality';
const DEFAULT_QUALITY = 'medium';

const QUALITY_OPTIONS = [
  {
    value: 'low',
    label: 'Low — 16 kHz mono',
    description: 'Smallest payload, lowest latency. Best for slow networks.',
  },
  {
    value: 'medium',
    label: 'Medium — 24 kHz mono',
    description: 'Balanced fidelity and bandwidth. Recommended.',
  },
  {
    value: 'high',
    label: 'High — 44.1 kHz stereo',
    description: 'Full fidelity bowl resonance. Larger payload.',
  },
];

function readSaved() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'low' || v === 'medium' || v === 'high') return v;
  } catch { /* ignore */ }
  return DEFAULT_QUALITY;
}

export default function AudioSettings({ value, onChange }) {
  const [internal, setInternal] = useState(readSaved);
  const current = value ?? internal;

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, current); } catch { /* ignore */ }
  }, [current]);

  const handleChange = useCallback(
    (next) => {
      if (value === undefined) setInternal(next);
      onChange?.(next);
    },
    [value, onChange],
  );

  const active = QUALITY_OPTIONS.find((o) => o.value === current) || QUALITY_OPTIONS[1];

  return (
    <Card
      size="small"
      title={
        <Space size={8} align="center">
          <Volume2 size={16} className="text-cyan-400" />
          <Title level={5} style={{ margin: 0 }}>Audio Quality</Title>
        </Space>
      }
      extra={<Tag color="cyan">{current.toUpperCase()}</Tag>}
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Select
          value={current}
          onChange={handleChange}
          options={QUALITY_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
          style={{ width: '100%' }}
          suffixIcon={<Gauge size={14} />}
        />
        <Text type="secondary" italic style={{ fontSize: 11 }}>
          {active.description}
        </Text>
      </Space>
    </Card>
  );
}
