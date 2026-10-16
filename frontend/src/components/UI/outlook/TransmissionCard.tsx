/**
 * TransmissionCard — a single (non-epic) narrative: TTS player, Illustrate
 * and Copy actions, and the Narrative / Affirmation tabs. The Narrative tab
 * reveals the ritual sections and, once complete, the Ritual Summary.
 *
 * @component
 */
import React from 'react';
import { Sparkles, BookOpen, Copy, CheckCircle, Image as ImageIcon } from 'lucide-react';
import { Card, Tabs, Button, Tag, Space, Typography, Divider, Tooltip } from 'antd';
import NarrativeTTSPlayer from '../NarrativeTTSPlayer';
import { GENRE_COLORS } from './outlookShared';
import type { CurrentNarrative } from './outlookNarrative';
import AffirmationPanel from './AffirmationPanel';
import RitualSections from './RitualSections';
import RitualSummaryCard from './RitualSummaryCard';
import type { OutlookGeneration } from './useOutlookGeneration';
import type { NarrativeMedia } from './useNarrativeMedia';

const { Text, Title } = Typography;

interface TransmissionCardProps {
  narrative: CurrentNarrative;
  /** The form's genre, used when the narrative carries none. */
  fallbackGenre: string;
  generation: OutlookGeneration;
  media: NarrativeMedia;
  sections: string[];
  revealedSections: number;
  narrativeSpeakRef: React.MutableRefObject<(() => void) | null>;
  onReplay: () => void;
}

export default function TransmissionCard({
  narrative, fallbackGenre, generation, media, sections, revealedSections, narrativeSpeakRef, onReplay,
}: TransmissionCardProps) {
  const {
    copied, copyNarrative, resultTab, setResultTab, affirmation, affirmationLoading,
    affirmationCopied, generateAffirmation, copyAffirmation, saveCurrentRitual,
  } = generation;

  return (
    <Card
      title={<Text strong className="font-mono text-xs uppercase">Transmission</Text>}
      style={{ background: GENRE_COLORS[narrative.genre || fallbackGenre] || 'transparent', transition: 'background 0.8s ease' }}
      extra={
        <Space size={4}>
          <NarrativeTTSPlayer
            text={narrative.narrative}
            role="outlook_narrative"
            onSpeakRef={narrativeSpeakRef}
          />
          <Tooltip title="Generate a sacred illustration from the narrative excerpt">
            <Button
              size="small"
              loading={media.illustrationLoading}
              icon={<ImageIcon className="w-3 h-3" />}
              onClick={media.generateIllustration}
            >
              Illustrate
            </Button>
          </Tooltip>
          <Button size="small" icon={copied ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            onClick={copyNarrative}>{copied ? 'Copied' : 'Copy'}</Button>
        </Space>
      }
    >
      <Tabs
        size="small"
        activeKey={resultTab}
        onChange={(key) => setResultTab(key === 'affirmation' ? 'affirmation' : 'narrative')}
        items={[
          {
            key: 'narrative',
            label: <span><BookOpen className="w-3 h-3 inline mr-1" />Narrative</span>,
            children: (
              <>
                <Title level={4} style={{ color: '#e2e8f0', textTransform: 'capitalize' }}>{narrative.genre} Revelation</Title>
                {narrative.model_used && (
                  <div style={{ marginBottom: 8 }}>
                    <Tag color="blue" style={{ fontSize: 10 }}>
                      🤖 {narrative.provider_used || 'unknown'}/{narrative.model_used}
                    </Tag>
                  </div>
                )}
                <Divider />
                <RitualSections narrative={narrative} sections={sections} revealedSections={revealedSections} />
                {sections.length > 0 && revealedSections >= sections.length && (
                  <RitualSummaryCard
                    narrative={narrative}
                    fallbackGenre={fallbackGenre}
                    media={media}
                    onSave={saveCurrentRitual}
                    onReplay={onReplay}
                  />
                )}
              </>
            ),
          },
          {
            key: 'affirmation',
            label: <span><Sparkles className="w-3 h-3 inline mr-1" />Affirmation</span>,
            children: (
              <AffirmationPanel
                affirmation={affirmation}
                loading={affirmationLoading}
                copied={affirmationCopied}
                onGenerate={generateAffirmation}
                onCopy={copyAffirmation}
              />
            ),
          },
        ]}
      />
    </Card>
  );
}
