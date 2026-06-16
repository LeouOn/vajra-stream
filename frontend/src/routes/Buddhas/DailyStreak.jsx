/**
 * DailyStreak — consecutive-day recitation streak counter.
 *
 * Reads the streak from localStorage (`vajra-buddha-streak`):
 *   { lastDay: 'YYYY-MM-DD', count: N }
 * The "Mark today" button updates the streak: if `lastDay` is yesterday,
 * count++ and store today; if `lastDay` is today, no-op; otherwise reset
 * to 1. Renders an AntD Statistic with a small flame icon. Pure
 * client-side, no backend, no polling.
 *
 * @component
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card, Statistic, Button, Typography, Space, Tag } from 'antd';
import { Flame, CalendarCheck } from 'lucide-react';

const { Text, Title } = Typography;
const STORAGE_KEY = 'vajra-buddha-streak';

function todayStr() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function yesterdayStr() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function readStreak() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { lastDay: null, count: 0 };
    const parsed = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) return { lastDay: null, count: 0 };
    return {
      lastDay: typeof parsed.lastDay === 'string' ? parsed.lastDay : null,
      count: Number.isFinite(parsed.count) ? parsed.count : 0,
    };
  } catch {
    return { lastDay: null, count: 0 };
  }
}

function writeStreak(state) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* ignore */ }
}

export default function DailyStreak() {
  const [streak, setStreak] = useState({ lastDay: null, count: 0 });

  useEffect(() => {
    setStreak(readStreak());
  }, []);

  const handleMarkToday = useCallback(() => {
    const today = todayStr();
    const yesterday = yesterdayStr();
    setStreak((prev) => {
      let next;
      if (prev.lastDay === today) {
        next = prev; // already marked today
      } else if (prev.lastDay === yesterday) {
        next = { lastDay: today, count: prev.count + 1 };
      } else {
        next = { lastDay: today, count: 1 };
      }
      writeStreak(next);
      return next;
    });
  }, []);

  const alreadyToday = streak.lastDay === todayStr();

  return (
    <Card
      size="small"
      title={
        <Space size={8} align="center">
          <Flame size={16} className={alreadyToday ? 'text-orange-400' : 'text-gray-500'} />
          <Title level={5} style={{ margin: 0 }}>Daily Streak</Title>
        </Space>
      }
      extra={alreadyToday ? <Tag color="orange">today</Tag> : null}
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Statistic
          value={streak.count}
          prefix={<Flame size={18} className="text-orange-400" />}
          suffix={streak.count === 1 ? 'day' : 'days'}
          valueStyle={{ color: '#ffd700' }}
        />
        <Button
          block
          type={alreadyToday ? 'default' : 'primary'}
          icon={<CalendarCheck size={14} />}
          onClick={handleMarkToday}
          disabled={alreadyToday}
        >
          {alreadyToday ? 'Marked for today' : 'Mark today'}
        </Button>
        {streak.lastDay && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            Last practice: {streak.lastDay}
          </Text>
        )}
      </Space>
    </Card>
  );
}
