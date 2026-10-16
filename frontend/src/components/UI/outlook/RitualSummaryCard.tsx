/**
 * RitualSummaryCard — shown once every ritual section is revealed: deity,
 * genre, model and oracle summary, the deity and sigil visualizations, and
 * the Save / Replay / Bell / manifestation-video actions with the video
 * task's progress.
 *
 * @component
 */
import React from 'react';
import { Download, Volume2, Bell } from 'lucide-react';
import { Card, Button, Row, Col, Space, Spin, Typography } from 'antd';
import SadhanaVisualization from '../SadhanaVisualization';
import RitualVisualization from '../RitualVisualization';
import ProvenanceTag from '../ProvenanceTag';
import { getDeityFromEntityText } from '../../../lib/deityVisualizations';
import { GENRE_COLORS } from './outlookShared';
import type { CurrentNarrative } from './outlookNarrative';
import { playDedicationBell } from './ritualAudio';
import type { NarrativeMedia } from './useNarrativeMedia';

const { Text } = Typography;

interface RitualSummaryCardProps {
  narrative: CurrentNarrative;
  /** The form's genre, used when the narrative carries none. */
  fallbackGenre: string;
  media: NarrativeMedia;
  onSave: () => void;
  onReplay: () => void;
}

export default function RitualSummaryCard({ narrative, fallbackGenre, media, onSave, onReplay }: RitualSummaryCardProps) {
  const { videoGenState, videoGenLoading, generateVideoFromNarrative } = media;
  const genre = narrative.genre || fallbackGenre;

  return (
    <Card
      title={<Text strong style={{ fontSize: 12 }}>📋 Ritual Summary</Text>}
      size="small"
      style={{ marginTop: 16, background: GENRE_COLORS[genre] || 'transparent' }}
    >
      <Row gutter={[8, 8]}>
        <Col xs={24} sm={12} md={8}>
          <Text type="secondary" style={{ fontSize: 10 }}>Deity</Text>
          <div><Text strong style={{ fontSize: 12 }}>{narrative.entities_used || narrative.divination_used || '—'}</Text></div>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Text type="secondary" style={{ fontSize: 10 }}>Genre</Text>
          <div><Text strong style={{ fontSize: 12, textTransform: 'capitalize' }}>{genre}</Text></div>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Text type="secondary" style={{ fontSize: 10 }}>Model</Text>
          <div><Text strong style={{ fontSize: 12 }}>{narrative.model_used ? `${narrative.provider_used || 'unknown'}/${narrative.model_used}` : '—'}</Text></div>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Text type="secondary" style={{ fontSize: 10 }}>Tarot</Text> <ProvenanceTag kind="draw" />
          <div><Text strong style={{ fontSize: 12 }}>{narrative.divination_raw?.tarot?.name || '—'}</Text></div>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Text type="secondary" style={{ fontSize: 10 }}>I Ching</Text> <ProvenanceTag kind="draw" />
          <div><Text strong style={{ fontSize: 12 }}>{narrative.divination_raw?.iching?.name || '—'}</Text></div>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Text type="secondary" style={{ fontSize: 10 }}>Kamea</Text>
          <div><Text strong style={{ fontSize: 12 }}>{narrative.divination_raw?.sigil?.kamea || '—'}</Text></div>
        </Col>
      </Row>
      {getDeityFromEntityText(narrative.entities_used as string) && (
        <div style={{ marginTop: 12 }} className="flex justify-center">
          <SadhanaVisualization
            deity={getDeityFromEntityText(narrative.entities_used as string)!}
            size={200}
            showLabels
            practicePhase="reciting"
          />
        </div>
      )}
      <div style={{ marginTop: 12 }}>
        <RitualVisualization
          sigil={narrative.divination_raw?.sigil as { kamea?: string; reduced?: string; coordinates?: Array<{ x: number; y: number; value?: number; letter?: string }>; svg?: string } | undefined}
          rates={narrative.divination_raw?.rates as { signature?: { values: number[]; name: string; potency?: number }; balancing?: Array<{ values: number[]; name: string; potency?: number }> } | undefined}
          genre={genre}
          kameaPlanet={narrative.divination_raw?.sigil?.kamea}
        />
      </div>
      <Space style={{ marginTop: 12 }} wrap>
        <Button size="small" icon={<Download className="w-3 h-3" />} onClick={onSave}>
          Save Ritual
        </Button>
        <Button size="small" icon={<Volume2 className="w-3 h-3" />} onClick={onReplay}>
          Replay
        </Button>
        <Button
          size="small"
          icon={<Bell className="w-3 h-3" />}
          onClick={playDedicationBell}
        >
          Bell
        </Button>
        <Button
          size="small"
          loading={videoGenLoading}
          icon={<Volume2 className="w-3 h-3" />}
          onClick={generateVideoFromNarrative}
        >
          {videoGenLoading ? 'Composing...' : 'Generate Manifestation Video'}
        </Button>
      </Space>
      {videoGenState && (
        <div style={{ marginTop: 12 }}>
          {videoGenState.video_prompt && (
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 10 }}>Video prompt:</Text>
              <div className="text-[11px] text-purple-300/80 italic whitespace-pre-wrap mt-1">{videoGenState.video_prompt}</div>
            </div>
          )}
          {videoGenState.status && !videoGenState.video_url && (
            <div className="flex items-center gap-2">
              <Spin size="small" />
              <Text type="secondary" style={{ fontSize: 11 }}>
                {videoGenState.status === 'submitted' || videoGenState.status === 'processing' || videoGenState.status === 'pending'
                  ? 'Generating video... this can take 1-3 minutes.'
                  : `Task status: ${videoGenState.status}`}
              </Text>
            </div>
          )}
          {(videoGenState.video_url || videoGenState.local_path) && (
            <div>
              <video
                controls
                src={videoGenState.video_url || videoGenState.local_path}
                style={{ width: '100%', maxWidth: 320, borderRadius: 8, marginTop: 8 }}
              />
              {videoGenState.video_url && (
                <Button
                  size="small"
                  type="link"
                  href={videoGenState.video_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ paddingLeft: 0, marginTop: 4 }}
                >
                  Download video
                </Button>
              )}
            </div>
          )}
          {videoGenState.error && (
            <Text type="danger" style={{ fontSize: 11 }}>{videoGenState.error}</Text>
          )}
        </div>
      )}
    </Card>
  );
}
