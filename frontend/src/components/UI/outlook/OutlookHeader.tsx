/**
 * OutlookHeader — page title card with the Generator / Universe / History /
 * Journey tab switch.
 *
 * @component
 */
import React from 'react';
import { Compass, Sparkles, History, Layers } from 'lucide-react';
import { Card, Segmented, Row, Col, Space, Typography } from 'antd';
import { audioFeedback } from '../../../utils/audioFeedback';
import type { GeneratorTab } from './outlookNarrative';

const { Text, Title } = Typography;

interface OutlookHeaderProps {
  activeTab: GeneratorTab;
  onTabChange: (tab: GeneratorTab) => void;
}

export default function OutlookHeader({ activeTab, onTabChange }: OutlookHeaderProps) {
  return (
    <Card size="small">
      <Row justify="space-between" align="middle">
        <Col>
          <Space>
            <Compass className="w-6 h-6" style={{ color: '#06b6d4' }} />
            <div>
              <Title level={5} style={{ margin: 0, color: '#67e8f9' }}>Narrative Generation & Outlook</Title>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Construct localized, sutra-style blessing cycles based on high-entropy oracles, planetary lines, and active entity grids.
              </Text>
            </div>
          </Space>
        </Col>
        <Col>
          <Segmented
            value={activeTab}
            onChange={(v: GeneratorTab) => { onTabChange(v); audioFeedback.playClick(); }}
            options={[
              { label: <span><Sparkles className="w-3 h-3 inline mr-1" />Generator</span>, value: 'generator' },
              { label: <span><Layers className="w-3 h-3 inline mr-1" />Universe</span>, value: 'universe' },
              { label: <span><History className="w-3 h-3 inline mr-1" />History</span>, value: 'history' },
              { label: <span><Compass className="w-3 h-3 inline mr-1" />Journey</span>, value: 'journey' },
            ]}
          />
        </Col>
      </Row>
    </Card>
  );
}
