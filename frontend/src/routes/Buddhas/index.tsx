/**
 * BuddhasPage — dedicated route for the 88-Buddha contemplation practice.
 *
 * Replaces the inline BuddhaContemplationWidget with a full-page layout
 * that surfaces: page title + subtitle, an overall progress bar driven by
 * the live WebSocket recitation status, a current-Buddha display card,
 * an IntentionEditor, and 5 sidebar feature components (DailyStreak,
 * DedicationText, ShareExport, AudioSettings, SessionHistory).
 *
 * Data flow: subscribes to `buddhaStatus` via `useWebSocketStable` (the
 * canonical WS hook) — no polling. The page renders a graceful fallback
 * when `buddhaStatus` is undefined or null so the route works even before
 * the first `BUDDHA_RECITATION_UPDATE` arrives.
 *
 * @component
 * @route /buddhas
 */
import React, { useState, useCallback } from 'react';
import { Row, Col, Card, Progress, Typography, Space, Tag, Divider, Empty, Button, Result } from 'antd';
import {
  BookOpen, Sparkles, Compass, Zap, Activity, Play, Square, Loader2,
} from 'lucide-react';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import { audioFeedback } from '../../utils/audioFeedback';
import type { RecitationStatus } from '../../../types';
import IntentionEditor from './IntentionEditor';
import DedicationText from './DedicationText';
import SessionHistory from './SessionHistory';
import ShareExport from './ShareExport';
import DailyStreak from './DailyStreak';
import AudioSettings from './AudioSettings';

const { Title, Text, Paragraph } = Typography;

const CATEGORY_LABELS: Record<string, string> = {
  past: '53 Past Buddhas',
  confession: '35 Confession Buddhas',
};
const CATEGORY_TAG_COLOR: Record<string, string> = {
  past: 'amber',
  confession: 'cyan',
};

/**
 * The rich current-buddha payload. `BuddhaEntry` (in types.ts) captures the
 * fields the backend always emits; the live WS payload additionally carries
 * optional `meaning` / `realm` / `light` tags surfaced as AntD Tags here.
 */
interface CurrentBuddha {
  name_chinese?: string;
  name_pinyin?: string;
  name_sanskrit?: string;
  category?: string;
  meaning?: string;
  realm?: string;
  light?: string;
}

/**
 * CurrentBuddhaCard — displays the live current Buddha from the WS payload.
 * Gracefully handles an absent `current_buddha` (e.g. session not running).
 */
function CurrentBuddhaCard({ status }: { status?: RecitationStatus | null }) {
  const raw = status?.current_buddha;
  const cb: CurrentBuddha = (raw && typeof raw === 'object' ? raw : {}) as CurrentBuddha;
  const name = cb.name_chinese;

  if (!name) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" size={2}>
              <Text type="secondary">No active recitation.</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Start a session to see the current Buddha here.
              </Text>
            </Space>
          }
        />
      </Card>
    );
  }

  const category = cb.category || '';
  const catLabel = CATEGORY_LABELS[category] || category;
  const catColor = CATEGORY_TAG_COLOR[category] || 'default';

  return (
    <Card>
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <div style={{ textAlign: 'center' }}>
          <Title level={2} style={{ margin: 0, color: '#fcd34d', letterSpacing: '0.08em' }}>
            {cb.name_chinese}
          </Title>
          <Space size={8} align="center" style={{ marginTop: 4 }}>
            {cb.name_pinyin && (
              <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 13 }}>
                {cb.name_pinyin}
              </Text>
            )}
            {cb.name_sanskrit && (
              <>
                <span style={{ color: 'rgba(255,255,255,0.2)' }}>·</span>
                <Text italic type="secondary" style={{ fontSize: 12 }}>
                  {cb.name_sanskrit}
                </Text>
              </>
            )}
          </Space>
        </div>

        <Space size={6} wrap style={{ justifyContent: 'center', width: '100%' }}>
          {catLabel && <Tag color={catColor}>{catLabel}</Tag>}
          {cb.meaning && (
            <Tag icon={<Sparkles size={11} />} color="purple">{cb.meaning}</Tag>
          )}
          {cb.realm && (
            <Tag icon={<Compass size={11} />} color="geekblue">{cb.realm}</Tag>
          )}
          {cb.light && (
            <Tag icon={<Zap size={11} />} color="gold">{cb.light}</Tag>
          )}
        </Space>
      </Space>
    </Card>
  );
}

interface RecitationControlsProps {
  running: boolean;
  intention: string;
  loading: boolean;
  onToggle: () => void;
}

/**
 * RecitationControls — Start/Stop buttons that POST to the backend
 * `/operator/buddhas/recitation/{start|stop}` endpoints. Uses the current
 * intention from the page state. No polling — the parent WS hook delivers
 * updates.
 */
function RecitationControls({ running, intention, loading, onToggle }: RecitationControlsProps) {
  return (
    <Button
      type={running ? 'default' : 'primary'}
      danger={running}
      size="large"
      icon={loading ? <Loader2 size={16} className="animate-spin" /> : running ? <Square size={16} /> : <Play size={16} />}
      onClick={onToggle}
      loading={loading}
      style={running ? { borderColor: '#dc2626', color: '#fca5a5' } : undefined}
    >
      {running ? 'Stop Recitation' : `Start 88-Buddha Loop${intention ? '' : ''}`}
    </Button>
  );
}

export default function BuddhasPage() {
  const { buddhaStatus } = useWebSocketStable();
  const [intention, setIntention] = useState<string>('');
  const [toggling, setToggling] = useState<boolean>(false);

  const running = !!buddhaStatus?.running;
  const progressPct = Math.max(
    0,
    Math.min(100, buddhaStatus?.progress_pct ?? 0),
  );

  const handleToggle = useCallback(async () => {
    setToggling(true);
    audioFeedback.playTelemetry();
    try {
      if (running) {
        await fetch(`/api/v1/operator/buddhas/recitation/stop`, { method: 'POST' });
      } else {
        await fetch(`/api/v1/operator/buddhas/recitation/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            intention: intention || '愿一切众生离苦得乐',
            interval_seconds: 3.0,
          }),
        });
      }
    } catch (err) {
      console.error('BuddhasPage: toggle recitation failed', err);
    } finally {
      setToggling(false);
    }
  }, [running, intention]);

  return (
    <div className="flex-1 h-full overflow-y-auto p-6">
      <Space direction="vertical" size={16} style={{ width: '100%', maxWidth: 1400, margin: '0 auto' }}>
        {/* Header */}
        <div>
          <Space size={12} align="center">
            <BookOpen size={28} className="text-amber-400" />
            <div>
              <Title level={3} style={{ margin: 0 }}>88 Buddhas Contemplation</Title>
              <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 13 }}>
                八十八佛大懺悔文 · The Great Confession of the 88 Buddhas
              </Text>
            </div>
          </Space>
        </div>

        {/* Progress bar (graceful: shows 0% if no status yet) */}
        <Card size="small">
          <Space direction="vertical" size={6} style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <Space size={8} align="center">
                <Activity size={14} className={running ? 'text-emerald-400' : 'text-gray-500'} />
                <Text strong>{running ? 'Reciting' : 'Idle'}</Text>
                {buddhaStatus?.current_cycle != null && (
                  <Tag color="emerald">cycle {buddhaStatus.current_cycle}</Tag>
                )}
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {buddhaStatus?.total_recited ?? 0} chanted
                {buddhaStatus?.total_buddhas ? ` / ${buddhaStatus.total_buddhas}` : ''}
              </Text>
            </div>
            <Progress
              percent={progressPct}
              status={running ? 'active' : 'normal'}
              strokeColor={{ from: '#10b981', to: '#06b6d4' }}
            />
            <Space size={16} wrap style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
              <span>Mala: <Text strong style={{ color: '#c4b5fd' }}>{buddhaStatus?.mala_count ?? 0}</Text></span>
              <span>Dedications: <Text strong style={{ color: '#fcd34d' }}>{buddhaStatus?.dedications ?? 0}</Text></span>
              {buddhaStatus?.last_recited_at && (
                <span>Last: {new Date(buddhaStatus.last_recited_at).toLocaleTimeString()}</span>
              )}
            </Space>
          </Space>
        </Card>

        {/* Main + sidebar grid */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <CurrentBuddhaCard status={buddhaStatus} />
              <IntentionEditor value={intention} onChange={setIntention} />
              <Card size="small">
                <RecitationControls
                  running={running}
                  intention={intention}
                  loading={toggling}
                  onToggle={handleToggle}
                />
              </Card>
            </Space>
          </Col>

          <Col xs={24} lg={8}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <DailyStreak />
              <DedicationText />
              <ShareExport buddhaStatus={buddhaStatus} intention={intention} />
              <AudioSettings />
              <SessionHistory buddhaStatus={buddhaStatus} />
            </Space>
          </Col>
        </Row>

        <Divider style={{ margin: '8px 0' }} />
        <Result
          status="info"
          icon={<Sparkles size={32} className="text-purple-400" />}
          title={<Text type="secondary" style={{ fontSize: 14 }}>愿一切众生离苦得乐</Text>}
          subTitle={
            <Text type="secondary" style={{ fontSize: 12 }}>
              Recitation data streams in real-time over WebSocket. No polling.
            </Text>
          }
          style={{ padding: '12px 0' }}
        />
      </Space>
    </div>
  );
}
