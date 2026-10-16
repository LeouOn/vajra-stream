/**
 * EsotericSidebar — the oracle context behind a narrative: divination
 * (tarot / I Ching), astrology and invoked entities.
 *
 * @component
 */
import React from 'react';
import { BookOpen, Sun } from 'lucide-react';
import { Card, Space, Tag, Typography } from 'antd';
import ProvenanceTag from '../ProvenanceTag';
import type { CurrentNarrative } from './outlookNarrative';

const { Text, Paragraph } = Typography;

interface EsotericSidebarProps {
  narrative: CurrentNarrative;
}

export default function EsotericSidebar({ narrative }: EsotericSidebarProps) {
  return (
    <Space orientation="vertical" className="w-full" size="middle">
      {/* Divination */}
      {narrative.divination_raw && (
        <Card size="small" title={<span><Text strong className="font-mono text-xs uppercase">🔮 Esoteric Reading</Text> <ProvenanceTag kind="draw" /></span>}>
          {/* SVGs suppressed — they were taking up all available space.
              The text descriptions below carry the same information. */}
          {narrative.divination_raw.tarot?.name && (
            <div className="mb-2">
              <Tag color="purple" style={{ fontSize: 10 }}>
                🃏 {narrative.divination_raw.tarot.name}
                {narrative.divination_raw.tarot.orientation ? ` (${narrative.divination_raw.tarot.orientation})` : ''}
              </Tag>
            </div>
          )}
          {narrative.divination_raw.iching?.name && (
            <div className="mb-2">
              <Tag color="cyan" style={{ fontSize: 10 }}>
                ☯️ {narrative.divination_raw.iching.name}
                {narrative.divination_raw.iching.changing_lines ? ` → ${narrative.divination_raw.iching.relating_name || ''}` : ''}
              </Tag>
            </div>
          )}
          {narrative.divination_used && (
            <Paragraph style={{ fontSize: 11, fontStyle: 'italic' }} ellipsis={{ rows: 4 }}>
              "{narrative.divination_used}"
            </Paragraph>
          )}
        </Card>
      )}
      {/* Astrology */}
      {narrative.astrology_used && (
        <Card size="small" title={<Text strong className="font-mono text-xs uppercase"><Sun className="w-3 h-3 inline mr-1" />Astrology</Text>}>
          <Paragraph style={{ fontSize: 11 }}>{narrative.astrology_used}</Paragraph>
        </Card>
      )}
      {/* Entities */}
      {narrative.entities_used && (
        <Card size="small" title={<Text strong className="font-mono text-xs uppercase"><BookOpen className="w-3 h-3 inline mr-1" />Entities Invoked</Text>}>
          <Paragraph style={{ fontSize: 11 }}>{narrative.entities_used}</Paragraph>
        </Card>
      )}
    </Space>
  );
}
