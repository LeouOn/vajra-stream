/**
 * BackgroundServicesPanel — control the background daemons that can
 * auto-play audio (singing bowls, TTS) and auto-generate content.
 *
 * The autonomous radionics operator runs every N minutes and auto-starts
 * character journeys; each journey's BROADCAST phase plays prayer-bowl
 * audio for a minute at the character's frequency. The outlook loop
 * regenerates outlooks on a timer. This panel gives the user on/off
 * control over both so the app doesn't make surprise sounds.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Switch,
  Button,
  Space,
  Typography,
  Tag,
  Alert,
  message,
  Divider,
} from 'antd';
import { Activity, RefreshCw, Radio, Sparkles, Power } from 'lucide-react';
import { apiUrl } from '../../utils/api';

const { Title, Text, Paragraph } = Typography;

interface AutonomousStatus {
  active: boolean;
  interval_seconds: number;
  suggestions_count: number;
}

interface OutlookLoopStatus {
  active: boolean;
  interval_minutes: number;
}

export default function BackgroundServicesPanel() {
  const [autonomous, setAutonomous] = useState<AutonomousStatus | null>(null);
  const [outlookLoop, setOutlookLoop] = useState<OutlookLoopStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [autoRes, outlookRes] = await Promise.all([
        fetch(apiUrl('/operator/autonomous/status')),
        fetch(apiUrl('/outlook/loop/status')),
      ]);
      if (autoRes.ok) setAutonomous(await autoRes.json());
      if (outlookRes.ok) setOutlookLoop(await outlookRes.json());
    } catch (err) {
      console.warn('BackgroundServicesPanel: fetch failed', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 10000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const toggleAutonomous = async (on: boolean) => {
    try {
      const res = await fetch(apiUrl(on ? '/operator/autonomous/start' : '/operator/autonomous/stop'), {
        method: 'POST',
      });
      if (!res.ok) {
        message.error(`Could not ${on ? 'start' : 'stop'} autonomous operator`);
        return;
      }
      const data = await res.json();
      message.success(on ? 'Autonomous operator started' : 'Autonomous operator stopped');
      setAutonomous((prev) => ({ active: data.active ?? on, interval_seconds: prev?.interval_seconds ?? 300, suggestions_count: prev?.suggestions_count ?? 0 }));
    } catch (err) {
      message.error(String(err));
    }
  };

  const toggleOutlookLoop = async (on: boolean) => {
    try {
      const res = await fetch(apiUrl(on ? '/outlook/loop/start' : '/outlook/loop/stop'), {
        method: 'POST',
      });
      if (!res.ok) {
        message.error(`Could not ${on ? 'start' : 'stop'} outlook loop`);
        return;
      }
      message.success(on ? 'Outlook loop started' : 'Outlook loop stopped');
      setOutlookLoop((prev) => ({ active: on, interval_minutes: prev?.interval_minutes ?? 60 }));
    } catch (err) {
      message.error(String(err));
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card size="small" loading={loading}>
        <Space size={10} align="center">
          <Radio size={18} className="text-cyan-400" />
          <Title level={5} style={{ margin: 0 }}>
            Background Services
          </Title>
          <Tag color="blue">Control</Tag>
        </Space>
        <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>
          These background daemons run autonomously and can play audio or generate
          content on a timer. Toggle them to prevent surprise singing bowls.
        </Paragraph>
      </Card>

      <Alert
        type="info"
        showIcon
        message="Why do I hear singing bowls?"
        description={
          <Paragraph style={{ margin: 0, fontSize: 12 }} type="secondary">
            The autonomous operator auto-starts character journeys when it finds an
            auspicious timing window. Each journey's broadcast phase plays prayer-bowl
            audio for ~1 minute at the character's frequency. Stopping the autonomous
            operator halts this.
          </Paragraph>
        }
      />

      {/* Autonomous Operator */}
      <Card
        size="small"
        loading={loading}
        title={
          <Space size={6}>
            <Activity size={14} className="text-cyan-400" />
            <Text strong className="font-mono text-xs uppercase">Autonomous Radionics Operator</Text>
          </Space>
        }
        extra={
          <Space size={4}>
            <Tag color={autonomous?.active ? 'green' : 'default'}>
              {autonomous?.active ? 'RUNNING' : 'STOPPED'}
            </Tag>
            <Switch
              checked={autonomous?.active ?? false}
              onChange={toggleAutonomous}
              size="small"
            />
          </Space>
        }
      >
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <div>
            <Text strong style={{ fontSize: 12 }}>What it does</Text>
            <Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 12 }}>
              Every {autonomous?.interval_seconds ?? 300}s it checks astrological timing.
              When a "green window" is found, it auto-creates a character journey.
              Each journey advance plays singing-bowl audio during its broadcast phase.
            </Paragraph>
          </div>
          {autonomous && autonomous.suggestions_count > 0 && (
            <div>
              <Text type="secondary" style={{ fontSize: 11 }}>
                Journeys auto-launched: <Tag color="purple">{autonomous.suggestions_count}</Tag>
              </Text>
            </div>
          )}
          <Button
            size="small"
            icon={<Power size={12} />}
            onClick={() => toggleAutonomous(!autonomous?.active)}
          >
            {autonomous?.active ? 'Stop Operator' : 'Start Operator'}
          </Button>
        </Space>
      </Card>

      <Divider style={{ margin: '4px 0' }} />

      {/* Outlook Loop */}
      <Card
        size="small"
        loading={loading}
        title={
          <Space size={6}>
            <Sparkles size={14} className="text-purple-400" />
            <Text strong className="font-mono text-xs uppercase">Outlook Generation Loop</Text>
          </Space>
        }
        extra={
          <Space size={4}>
            <Tag color={outlookLoop?.active ? 'green' : 'default'}>
              {outlookLoop?.active ? 'RUNNING' : 'STOPPED'}
            </Tag>
            <Switch
              checked={outlookLoop?.active ?? false}
              onChange={toggleOutlookLoop}
              size="small"
            />
          </Space>
        }
      >
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <div>
            <Text strong style={{ fontSize: 12 }}>What it does</Text>
            <Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 12 }}>
              Regenerates outlooks every {outlookLoop?.interval_minutes ?? 60} minutes
              in the background. Uses LLM + full oracles. Toggle off to save API cost.
            </Paragraph>
          </div>
          <Button
            size="small"
            icon={<RefreshCw size={12} />}
            onClick={() => toggleOutlookLoop(!outlookLoop?.active)}
          >
            {outlookLoop?.active ? 'Stop Outlook Loop' : 'Start Outlook Loop'}
          </Button>
        </Space>
      </Card>
    </Space>
  );
}
