/**
 * HistoryTab — Past Transmissions: the stored outlook ledger with
 * search, genre/type filters, model badges, and per-item delete.
 *
 * Owns its filter state (search / genre / type are used nowhere else);
 * data and mutations arrive via props from the dashboard shell so a
 * generation in the Generator tab can trigger a parent-side refresh.
 */
import React, { useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Empty,
  Input,
  Popconfirm,
  Row,
  Select,
  Space,
  Tag,
  Tooltip,
} from 'antd';
import { Clock, Compass, Copy, Download, History, Play, RefreshCw, Trash2 } from 'lucide-react';

import { message } from 'antd';
import { SAVED_RITUALS_KEY, GENRE_COLORS, GENRE_BORDER_COLORS, stripMarkdown, type HistoryItem, type SavedRitual } from './outlookShared';
import { audioFeedback } from '../../../utils/audioFeedback';

interface HistoryTabProps {
  historyList: HistoryItem[];
  onRefresh: () => void;
  onDelete: (item: HistoryItem) => Promise<void> | void;
  onLoadInGenerator: (item: HistoryItem) => void;
}

export default function HistoryTab({
  historyList,
  onRefresh,
  onDelete,
  onLoadInGenerator,
}: HistoryTabProps): React.ReactElement {
  const [historyGenreFilter, setHistoryGenreFilter] = useState<string>('all');
  const [historyTypeFilter, setHistoryTypeFilter] = useState<string>('all');
  const [historySearch, setHistorySearch] = useState('');

  const filtered = useMemo(
    () =>
      historyList
        .filter(item => historyGenreFilter === 'all' || item.genre === historyGenreFilter)
        .filter(item => historyTypeFilter === 'all' || item.type === historyTypeFilter)
        .filter(item => {
          const needle = historySearch.trim().toLowerCase();
          if (!needle) return true;
          const hay = `${item.content || ''} ${item.entities_invoked || ''} ${item.genre || ''}`.toLowerCase();
          return hay.includes(needle);
        }),
    [historyList, historyGenreFilter, historyTypeFilter, historySearch],
  );

  return (
    <div className="space-y-4">
      <Card size="small">
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <History className="w-4 h-4 text-cyan-400" />
              <span className="font-mono text-xs font-semibold uppercase tracking-wide">Past Transmissions</span>
              <Tag color="cyan">{historyList.length}</Tag>
            </Space>
          </Col>
          <Col>
            <Space>
              <Input.Search
                size="small"
                allowClear
                placeholder="Search transmissions…"
                style={{ width: 180 }}
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
              />
              <Select
                size="small"
                value={historyGenreFilter}
                onChange={setHistoryGenreFilter}
                style={{ width: 140 }}
                options={[
                  { value: 'all', label: 'All Genres' },
                  ...Array.from(new Set(historyList.map(h => h.genre).filter(Boolean))).map(g => ({
                    value: g!,
                    label: g!.charAt(0).toUpperCase() + g!.slice(1),
                  })),
                ]}
              />
              <Select
                size="small"
                value={historyTypeFilter}
                onChange={setHistoryTypeFilter}
                style={{ width: 110 }}
                options={[
                  { value: 'all', label: 'All Types' },
                  { value: 'single', label: 'Single' },
                  { value: 'epic', label: 'Epic' },
                ]}
              />
              <Button size="small" icon={<RefreshCw className="w-3 h-3" />} onClick={onRefresh}>
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {historyList.length === 0 ? (
        <Card>
          <Empty
            image={<Compass className="w-16 h-16" style={{ color: '#06b6d4', opacity: 0.4 }} />}
            description={
              <div>
                <div className="text-base" style={{ color: '#94a3b8' }}>No Transmissions Yet</div>
                <div className="text-xs text-slate-400">Create one in the Generator tab.</div>
              </div>
            }
          />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {filtered.map((item, idx) => {
            const genre = item.genre || 'unknown';
            const genreColor = GENRE_COLORS[genre] || 'transparent';
            const borderColor = GENRE_BORDER_COLORS[genre] || '#334155';
            const rawContent = item.type === 'epic' ? 'Multi-stage epic narrative' : (item.content || '');
            const preview = stripMarkdown(rawContent);
            const date = item.date_generated ? new Date(item.date_generated) : null;
            return (
              <Col xs={24} md={12} lg={8} key={`hist-${idx}`}>
                <Card
                  size="small"
                  hoverable
                  style={{
                    background: genreColor,
                    borderLeft: `3px solid ${borderColor}`,
                    transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
                  }}
                  actions={[
                    <Tooltip title="Load in Generator" key="load">
                      <Button
                        type="text"
                        size="small"
                        icon={<Play className="w-3 h-3" />}
                        onClick={() => onLoadInGenerator(item)}
                      />
                    </Tooltip>,
                    <Tooltip title="Copy text" key="copy">
                      <Button
                        type="text"
                        size="small"
                        icon={<Copy className="w-3 h-3" />}
                        onClick={() => {
                          navigator.clipboard.writeText(item.content || '');
                          message.success('Copied narrative text.');
                          audioFeedback.playSuccess();
                        }}
                      />
                    </Tooltip>,
                    <Tooltip title="Save to archive" key="save">
                      <Button
                        type="text"
                        size="small"
                        icon={<Download className="w-3 h-3" />}
                        onClick={() => {
                          const entry: SavedRitual = {
                            id: `ritual_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
                            savedAt: new Date().toISOString(),
                            genre: item.genre || 'unknown',
                            narrative: item.content || '',
                            divinationRaw: item.divination_raw ?? null,
                            entities: item.entities_invoked ?? null,
                            model: item.model_used ?? null,
                            provider: item.provider_used ?? null,
                          };
                          try {
                            const existing = JSON.parse(window.localStorage.getItem(SAVED_RITUALS_KEY) || '[]') as SavedRitual[];
                            window.localStorage.setItem(SAVED_RITUALS_KEY, JSON.stringify([entry, ...existing].slice(0, 50)));
                            message.success('Saved to local archive.');
                          } catch {
                            message.error('Could not save — storage full or disabled.');
                          }
                        }}
                      />
                    </Tooltip>,
                    <Popconfirm
                      key="delete"
                      title="Delete this transmission?"
                      description="It will be removed from the ledger permanently."
                      okText="Delete"
                      okType="danger"
                      cancelText="Keep"
                      onConfirm={() => { void onDelete(item); }}
                    >
                      <Button type="text" size="small" danger icon={<Trash2 className="w-3 h-3" />} />
                    </Popconfirm>,
                  ]}
                >
                  <Card.Meta
                    title={
                      <Space size={4}>
                        <span className="text-[13px] font-semibold capitalize">{genre}</span>
                        <Tag color={item.type === 'epic' ? 'purple' : 'cyan'} style={{ fontSize: 9 }}>
                          {item.type === 'epic' ? 'EPIC' : 'SINGLE'}
                        </Tag>
                      </Space>
                    }
                    description={
                      <div>
                        <div
                          className="mb-2 leading-normal"
                          style={{
                            fontSize: 11,
                            color: '#94a3b8',
                            display: '-webkit-box',
                            WebkitLineClamp: 3,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }}
                        >
                          {preview || '(empty)'}
                        </div>
                        <Space size={[8, 4]} wrap>
                          {date && (
                            <span className="inline-flex items-center gap-1 text-[10px] text-slate-400">
                              <Clock className="h-2.5 w-2.5" />
                              {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          )}
                          {item.entities_invoked && (
                            <Tag
                              style={{ fontSize: 9, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                            >
                              👤 {item.entities_invoked}
                            </Tag>
                          )}
                          {item.model_used && (
                            <Tooltip
                              title={`Written by ${item.model_used}${item.provider_used ? ` via ${item.provider_used}` : ''}`}
                            >
                              <Tag
                                color="geekblue"
                                style={{ fontSize: 9, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                              >
                                🤖 {item.model_used.split('/').pop()}
                              </Tag>
                            </Tooltip>
                          )}
                          {item.divination_context && (
                            <Tag
                              style={{ fontSize: 9, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                            >
                              🔮 {item.divination_context}
                            </Tag>
                          )}
                        </Space>
                      </div>
                    }
                  />
                </Card>
              </Col>
            );
          })}
        </Row>
      )}
    </div>
  );
}
