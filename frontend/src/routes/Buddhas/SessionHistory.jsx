/**
 * SessionHistory — record and display past 88-Buddha recitation sessions.
 *
 * Sessions are persisted client-side only in localStorage
 * (key `vajra-buddha-sessions`). Each entry: { id, ts, intention,
 * totalRecited, malaCount, dedications }. A "Record session" button lets
 * the user push the current live session into the log; clear-all removes
 * everything. Renders a compact list with empty-state.
 *
 * @component
 * @param {Object}   props
 * @param {Object}   [props.buddhaStatus] The live recitation status from useWebSocketStable.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card, Button, Typography, List, Tag, Space, Empty, Popconfirm, message } from 'antd';
import { History, Trash2, PlusCircle, Clock } from 'lucide-react';

const { Text, Title } = Typography;
const STORAGE_KEY = 'vajra-buddha-sessions';
const MAX_ENTRIES = 50;

function readSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeSessions(entries) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
    return true;
  } catch {
    return false;
  }
}

function formatTimestamp(ts) {
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString();
  } catch {
    return '';
  }
}

export default function SessionHistory({ buddhaStatus }) {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    setSessions(readSessions());
  }, []);

  const handleRecord = useCallback(() => {
    if (!buddhaStatus || !buddhaStatus.running) {
      message.warning('No active recitation to record.');
      return;
    }
    const entry = {
      id: `buddha-sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      ts: Date.now(),
      intention: buddhaStatus.intention || '',
      totalRecited: buddhaStatus.total_recited || 0,
      malaCount: buddhaStatus.mala_count || 0,
      dedications: buddhaStatus.dedications || 0,
      cycle: buddhaStatus.current_cycle || 0,
    };
    const next = [entry, ...readSessions()].slice(0, MAX_ENTRIES);
    if (writeSessions(next)) {
      setSessions(next);
      message.success('Session recorded.');
    } else {
      message.error('Could not save session — storage full?');
    }
  }, [buddhaStatus]);

  const handleClear = useCallback(() => {
    writeSessions([]);
    setSessions([]);
    message.success('History cleared.');
  }, []);

  return (
    <Card
      size="small"
      title={
        <Space size={8} align="center">
          <History size={16} className="text-purple-400" />
          <Title level={5} style={{ margin: 0 }}>Session History</Title>
          <Tag color="purple" style={{ marginLeft: 4 }}>{sessions.length}</Tag>
        </Space>
      }
      extra={
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<PlusCircle size={14} />}
            onClick={handleRecord}
            disabled={!buddhaStatus?.running}
          >
            Record
          </Button>
          <Popconfirm
            title="Clear all session history?"
            okText="Clear"
            cancelText="Keep"
            onConfirm={handleClear}
            disabled={sessions.length === 0}
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<Trash2 size={14} />}
              disabled={sessions.length === 0}
            />
          </Popconfirm>
        </Space>
      }
    >
      {sessions.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={<Text type="secondary" style={{ fontSize: 12 }}>No recorded sessions yet.</Text>}
        />
      ) : (
        <List
          size="small"
          dataSource={sessions.slice(0, 12)}
          renderItem={(s) => (
            <List.Item style={{ padding: '8px 0' }}>
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Space size={6} wrap>
                  <Tag color="emerald">×{s.totalRecited}</Tag>
                  <Tag color="gold">mala {s.malaCount}</Tag>
                  <Tag color="cyan">#{s.cycle || 0}</Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    <Clock size={10} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                    {formatTimestamp(s.ts)}
                  </Text>
                </Space>
                {s.intention && (
                  <Text italic style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)' }}>
                    “{s.intention.slice(0, 80)}{s.intention.length > 80 ? '…' : ''}”
                  </Text>
                )}
              </Space>
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
