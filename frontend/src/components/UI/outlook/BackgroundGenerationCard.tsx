/**
 * BackgroundGenerationCard — on/off switch, interval, loop mode, oracle
 * sources and running stats for the server-side blessing loop.
 *
 * Presentational: state and requests live in useBackgroundGeneration.
 *
 * @component
 */
import React from 'react';
import { Moon, Bell } from 'lucide-react';
import {
  Card, Select, Switch, Segmented, Row, Col, Space, Typography, Badge, Checkbox,
} from 'antd';
import { BG_INTERVAL_OPTIONS } from './outlookConstants';
import type { BackgroundGeneration } from './useBackgroundGeneration';

const { Text } = Typography;

interface BackgroundGenerationCardProps {
  bg: BackgroundGeneration;
}

export default function BackgroundGenerationCard({ bg }: BackgroundGenerationCardProps) {
  const {
    bgActive, bgInterval, setBgInterval, bgMode, setBgMode,
    bgAstrology, setBgAstrology, bgTarot, setBgTarot, bgIching, setBgIching,
    bgCycleGenres, setBgCycleGenres, bgStats, toggleBackgroundGeneration,
  } = bg;

  return (
    <Card
      title={
        <Text strong className="font-mono text-xs uppercase">
          <Moon className="w-3 h-3 inline mr-1" />Background Generation
          {bgActive && <Badge status="processing" color="purple" style={{ marginLeft: 8 }} />}
        </Text>
      }
      size="small"
      style={{ marginTop: 16 }}
    >
      <Space orientation="vertical" className="w-full" size="middle">
        <Row justify="space-between" align="middle">
          <Col>
            <Text style={{ fontSize: 12 }}>
              Auto-generate blessings with full oracles. Saves to history.
            </Text>
          </Col>
          <Col>
            <Switch
              checked={bgActive}
              onChange={toggleBackgroundGeneration}
              checkedChildren="🌙 On"
              unCheckedChildren="Off"
            />
          </Col>
        </Row>

        <div>
          <Text style={{ fontSize: 11 }}>Interval</Text>
          <Select
            value={bgInterval}
            onChange={setBgInterval}
            size="small"
            disabled={bgActive}
            className="w-full"
            style={{ marginTop: 4 }}
            options={BG_INTERVAL_OPTIONS}
          />
        </div>

        <Segmented
          block
          size="small"
          value={bgMode}
          onChange={setBgMode}
          disabled={bgActive}
          options={[
            { label: 'Sequential', value: 'sequential_delay' },
            { label: 'Consecutive', value: 'consecutive' },
          ]}
        />

        <div>
          <Text style={{ fontSize: 11 }}>Oracle Sources</Text>
          <Space orientation="vertical" size={4} style={{ marginTop: 4 }}>
            <Space>
              <Switch size="small" checked={bgAstrology} onChange={setBgAstrology} disabled={bgActive} />
              <Text style={{ fontSize: 11 }}>🌟 Astrology</Text>
            </Space>
            <Space>
              <Switch size="small" checked={bgTarot} onChange={setBgTarot} disabled={bgActive} />
              <Text style={{ fontSize: 11 }}>🃏 Tarot</Text>
            </Space>
            <Space>
              <Switch size="small" checked={bgIching} onChange={setBgIching} disabled={bgActive} />
              <Text style={{ fontSize: 11 }}>☯️ I Ching</Text>
            </Space>
          </Space>
        </div>

        <Row justify="space-between" align="middle">
          <Col>
            <Checkbox
              checked={bgCycleGenres}
              onChange={e => setBgCycleGenres(e.target.checked)}
              disabled={bgActive}
              style={{ fontSize: 12 }}
            >
              🔄 Cycle all genres
            </Checkbox>
          </Col>
        </Row>

        {(bgStats.total_generated ?? 0) > 0 && (
          <div style={{ background: 'rgba(139,92,246,0.05)', padding: 8, borderRadius: 6 }}>
            <Text style={{ fontSize: 10 }} className="font-mono">
              <Bell className="w-3 h-3 inline mr-1" />
              Generated: {bgStats.total_generated} · Saved: {bgStats.total_saved}
              {(bgStats.total_errors ?? 0) > 0 && ` · Errors: ${bgStats.total_errors}`}
            </Text>
            {bgStats.last_generated_at && (
              <div>
                <Text type="secondary" style={{ fontSize: 9 }}>
                  Last: {new Date(bgStats.last_generated_at).toLocaleString()}
                  {bgStats.last_genre && ` · ${bgStats.last_genre}`}
                </Text>
              </div>
            )}
          </div>
        )}

        {bgActive && (
          <Text type="secondary" style={{ fontSize: 10 }}>
            Running every {bgInterval} min — {bgMode === 'consecutive' ? 'consecutive (5s apart)' : 'sequential delay'}.
            Genres {bgCycleGenres ? 'cycling' : 'fixed'}.
          </Text>
        )}
      </Space>
    </Card>
  );
}
