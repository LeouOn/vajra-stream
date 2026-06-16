/**
 * DedicationText — randomly selects one of three dedication-of-merit verses.
 *
 * Traditional Mahāyāna closing verses used to seal the merit of practice so
 * it does not ripen for oneself alone but is shared with all beings. The
 * component picks a random dedication on mount and offers a refresh button.
 * Pure client-side: no backend dependency, no polling.
 *
 * @component
 * @param {Object}   props
 * @param {function} [props.onRefresh] Optional callback fired when the user requests a new dedication.
 */
import React, { useState, useCallback } from 'react';
import { Card, Button, Typography, Space } from 'antd';
import { RefreshCw, Sparkles } from 'lucide-react';

const { Text, Paragraph, Title } = Typography;

const DEDICATIONS = [
  {
    sanskrit: ' pariṇāmanā',
    body:
      'By this merit may all beings attain the state of Omniscience and ' +
      'defeat the enemy of faults — the ocean of saṃsāra. May all beings ' +
      'be liberated from the fearful waves of birth, old age, sickness, and death.',
    attribution: '— Longchenpa, root dedication',
  },
  {
    sanskrit: ' pariṇāmanā',
    body:
      'Whatever merit I have gathered by making offerings to the Buddhas, ' +
      'may it become a seed to liberate beings. Whatever good I have done, ' +
      'by others\' merit and mine, may the Dharma flourish forever.',
    attribution: '— Shantideva, Bodhicaryāvatāra (paraphrased)',
  },
  {
    sanskrit: ' pariṇāmanā',
    body:
      'May sentient beings in the three realms below, and throughout the ' +
      'ten directions, all be freed from suffering and the cause of suffering. ' +
      'May they never be parted from the great happiness that is free of suffering.',
    attribution: '— The Four Immeasurables',
  },
];

function pickDedication(exclude = -1) {
  if (DEDICATIONS.length <= 1) return DEDICATIONS[0];
  let idx = exclude;
  while (idx === exclude) idx = Math.floor(Math.random() * DEDICATIONS.length);
  return DEDICATIONS[idx];
}

export default function DedicationText({ onRefresh }) {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * DEDICATIONS.length));

  const handleRefresh = useCallback(() => {
    const next = pickDedication(index);
    setIndex(DEDICATIONS.indexOf(next));
    onRefresh?.();
  }, [index, onRefresh]);

  const dedication = DEDICATIONS[index];

  return (
    <Card
      size="small"
      title={
        <Space size={8} align="center">
          <Sparkles size={16} className="text-cyan-400" />
          <Title level={5} style={{ margin: 0 }}>Dedication of Merit</Title>
        </Space>
      }
      extra={
        <Button
          type="text"
          size="small"
          icon={<RefreshCw size={14} />}
          onClick={handleRefresh}
          aria-label="Draw another dedication"
        />
      }
    >
      <Space direction="vertical" size={6} style={{ width: '100%' }}>
        <Text type="secondary" italic style={{ fontSize: 11 }}>
          {dedication.sanskrit}
        </Text>
        <Paragraph style={{ margin: 0, fontSize: 13, lineHeight: 1.55, fontStyle: 'italic' }}>
          “{dedication.body}”
        </Paragraph>
        <Text type="secondary" style={{ fontSize: 11 }}>{dedication.attribution}</Text>
      </Space>
    </Card>
  );
}
