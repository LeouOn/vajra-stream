/**
 * NarrativeResult — the Generator's right column: a spinner while
 * generating, the epic viewer for multi-stage journeys, the transmission
 * (with illustration and oracle sidebar) for a single narrative, or the
 * empty "awaiting" state.
 *
 * @component
 */
import React from 'react';
import { Compass } from 'lucide-react';
import { Card, Row, Col, Tag, Spin, Empty, Typography } from 'antd';
import EpicStoryViewer from '../EpicStoryViewer';
import EsotericSidebar from './EsotericSidebar';
import IllustrationCard from './IllustrationCard';
import TransmissionCard from './TransmissionCard';
import type { OutlookGeneration } from './useOutlookGeneration';
import type { NarrativeMedia } from './useNarrativeMedia';

const { Text, Title } = Typography;

interface NarrativeResultProps {
  generation: OutlookGeneration;
  media: NarrativeMedia;
  /** The form's genre, used when the narrative carries none. */
  fallbackGenre: string;
  sections: string[];
  revealedSections: number;
  narrativeSpeakRef: React.MutableRefObject<(() => void) | null>;
  onReplay: () => void;
}

export default function NarrativeResult({
  generation, media, fallbackGenre, sections, revealedSections, narrativeSpeakRef, onReplay,
}: NarrativeResultProps) {
  const { loading, currentNarrative } = generation;

  if (loading) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center py-20">
          <Spin size="large" />
          <Text type="secondary" style={{ marginTop: 16 }}>Generating your narrative transmission...</Text>
        </div>
      </Card>
    );
  }

  if (!currentNarrative) {
    return (
      <Card>
        <Empty
          image={<Compass className="w-16 h-16" style={{ color: '#06b6d4', opacity: 0.4 }} />}
          description={
            <div>
              <Title level={4} style={{ color: '#94a3b8' }}>Awaiting Narrative Beacon</Title>
              <Text type="secondary">Configure settings on the left and initiate the stream to invoke a blessing sutra.</Text>
            </div>
          }
        />
      </Card>
    );
  }

  if (currentNarrative.type === 'epic' || currentNarrative.narrative_parts) {
    return (
      <>
        {currentNarrative.model_used && (
          <div style={{ marginBottom: 8 }}>
            <Tag color="blue" style={{ fontSize: 10 }}>
              🤖 {currentNarrative.provider_used || 'unknown'}/{currentNarrative.model_used}
            </Tag>
          </div>
        )}
        <EpicStoryViewer
          narrativeParts={currentNarrative.narrative_parts}
          astrologyContext={currentNarrative.astrology_used}
          divinationContext={currentNarrative.divination_used}
          divinationRaw={currentNarrative.divination_raw}
          entitiesInvoked={currentNarrative.entities_used}
        />
      </>
    );
  }

  return (
    <Row gutter={[24, 24]}>
      <Col xs={24} lg={16}>
        <TransmissionCard
          narrative={currentNarrative}
          fallbackGenre={fallbackGenre}
          generation={generation}
          media={media}
          sections={sections}
          revealedSections={revealedSections}
          narrativeSpeakRef={narrativeSpeakRef}
          onReplay={onReplay}
        />
        {media.illustration && <IllustrationCard illustration={media.illustration} />}
      </Col>
      <Col xs={24} lg={8}>
        <EsotericSidebar narrative={currentNarrative} />
      </Col>
    </Row>
  );
}
