/**
 * Session Timeline — chronological session history visualisation.
 * Horizontal timeline with colour-coded modality indicators and
 * expandable session detail cards.
 * @component
 * @param {{ sessions }} props
 */
import React, { useState, useEffect } from 'react';
import { Clock, Zap, Heart, Shield, Sparkles } from 'lucide-react';

type IntentionType = 'healing' | 'liberation' | 'empowerment' | 'protection' | 'peace' | 'love' | 'wisdom';

const INTENTION_ICONS: Record<IntentionType, typeof Heart> = {
  healing: Heart,
  liberation: Sparkles,
  empowerment: Zap,
  protection: Shield,
  peace: Heart,
  love: Heart,
  wisdom: Sparkles,
};
const INTENTION_COLORS: Record<IntentionType, string> = {
  healing: '#22c55e',
  liberation: '#a855f7',
  empowerment: '#f59e0b',
  protection: '#3b82f6',
  peace: '#06b6d4',
  love: '#ec4899',
  wisdom: '#8b5cf6',
};

interface ActiveSession {
  id: string;
  name?: string;
  intention?: string;
  duration?: number;
  status?: string;
  start_time?: string;
}

interface SessionConfig {
  name?: string;
  intention?: string;
  duration?: number;
}

interface HistoryEntry {
  id?: string;
  name?: string;
  config?: SessionConfig;
  status?: string;
  start_time?: string;
  duration?: number;
  total_runtime?: number;
  intention?: string;
}

interface SessionTimelineProps {
  sessions?: Record<string, ActiveSession>;
}

function getIntentionType(intention: string | undefined): IntentionType {
  if (!intention) return 'healing';
  const low = intention.toLowerCase();
  if (low.includes('heal') || low.includes('health') || low.includes('pain')) return 'healing';
  if (low.includes('liberat') || low.includes('free') || low.includes('release')) return 'liberation';
  if (low.includes('empower') || low.includes('power') || low.includes('strength')) return 'empowerment';
  if (low.includes('protect') || low.includes('shield') || low.includes('guard')) return 'protection';
  if (low.includes('peace') || low.includes('calm') || low.includes('harmony')) return 'peace';
  if (low.includes('love') || low.includes('heart') || low.includes('compassion')) return 'love';
  if (low.includes('wisdom') || low.includes('insight') || low.includes('clarity')) return 'wisdom';
  return 'healing';
}

export default function SessionTimeline({ sessions }: SessionTimelineProps) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const res = await fetch('/api/v1/sessions/history');
        if (res.ok) {
          const data = await res.json();
          const list: HistoryEntry[] = data.history || data || [];
          setHistory(list.slice(-30));
        }
      } catch {}
      setLoading(false);
    };
    fetchHistory();
  }, [sessions]);

  const allSessions: HistoryEntry[] = [...history];
  if (allSessions.length === 0 && sessions) {
    Object.values(sessions).forEach((s) => {
      allSessions.push({
        id: s.id,
        config: { name: s.name, intention: s.intention, duration: s.duration },
        status: s.status,
        start_time: s.start_time,
      });
    });
  }

  if (!loading && allSessions.length === 0) {
    return (
      <div className="bg-gray-900 rounded-lg border border-indigo-500/20 p-4 text-center">
        <Clock className="w-8 h-8 mx-auto mb-2 text-gray-600" />
        <p className="text-xs text-gray-500">No session history yet</p>
      </div>
    );
  }

  const maxDuration = Math.max(...allSessions.map((s) => (s.config?.duration || s.duration || 3600)), 1);

  return (
    <div className="bg-gray-900 rounded-lg border border-indigo-500/20 overflow-hidden">
      <div className="bg-gradient-to-r from-amber-900/20 to-orange-900/20 p-2.5 border-b border-amber-500/10 flex items-center gap-2">
        <Clock className="w-3.5 h-3.5 text-amber-400" />
        <h3 className="text-xs font-bold text-amber-300 uppercase tracking-wider">Session Timeline</h3>
        <span className="text-[10px] text-gray-500 ml-auto">{allSessions.length} sessions</span>
      </div>
      <div className="p-2 space-y-1.5 max-h-64 overflow-y-auto">
        {allSessions.slice(-20).map((s, i) => {
          const cfg: SessionConfig = s.config || {};
          const name = cfg.name || s.name || s.id || `S${i}`;
          const intention = cfg.intention || s.intention || '';
          const duration = cfg.duration || s.duration || 3600;
          const type = getIntentionType(intention);
          const Icon = INTENTION_ICONS[type] || Heart;
          const color = INTENTION_COLORS[type] || '#22c55e';
          const widthPct = Math.max(5, (duration / maxDuration) * 100);
          const status = s.status || 'completed';

          return (
            <div key={s.id || i} className="flex items-center gap-2 text-xs group">
              <div className="w-16 text-gray-500 truncate flex-shrink-0 text-[10px]" title={name}>
                {typeof name === 'string' ? name.slice(0, 12) : `S${i}`}
              </div>
              <div className="flex-1 h-5 bg-gray-800 rounded-full overflow-hidden relative">
                <div
                  className="h-full rounded-full flex items-center pl-2 transition-all"
                  style={{
                    width: `${widthPct}%`,
                    backgroundColor: color + '30',
                    borderLeft: `2px solid ${color}`,
                  }}
                >
                  <Icon className="w-3 h-3 flex-shrink-0" style={{ color }} />
                  <span className="text-[9px] text-gray-400 ml-1 truncate">
                    {intention?.slice(0, 20) || '—'}
                  </span>
                </div>
              </div>
              <span className="text-[10px] text-gray-600 w-10 text-right flex-shrink-0">
                {Math.round(duration / 60)}m
              </span>
              <span
                className={`text-[9px] w-14 flex-shrink-0 px-1.5 py-0.5 rounded-full text-center ${
                  status === 'running'
                    ? 'bg-green-950 text-green-400'
                    : status === 'stopped'
                      ? 'bg-gray-800 text-gray-500'
                      : 'bg-amber-950 text-amber-400'
                }`}
              >
                {status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
