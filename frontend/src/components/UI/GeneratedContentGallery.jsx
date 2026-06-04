/**
 * Generated Content Gallery — browse, search, play, and export saved blessings.
 *
 * Connects to GET /api/v1/outlook/history and GET /api/v1/outlook/export
 * to display all generated narratives, sutras, and blessings with:
 * - Full-text search across all content
 * - Genre/type filtering
 * - TTS playback of any narrative
 * - Copy to clipboard
 * - Export as JSON
 * - Date-sorted timeline
 *
 * @component
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  Sparkles, BookOpen, Copy, CheckCircle, Search, Filter,
  Download, Play, Clock, Tag, FileText, RefreshCw,
  Volume2, ExternalLink, ChevronDown, ChevronUp,
} from 'lucide-react';
import {
  Card, Input, Select, Button, Tag as AntTag, Space, Typography,
  List, Divider, Empty, Spin, message, Segmented,
} from 'antd';
import { API_BASE } from '../../utils/api';
import { audioFeedback } from '../../utils/audioFeedback';

const { Text, Paragraph, Title } = Typography;

const GENRE_COLORS = {
  healing: 'green', victory: 'red', alchemist: 'purple',
  fun_parable: 'orange', dharani: 'blue', compassion: 'pink',
  wisdom: 'gold',
};

export default function GeneratedContentGallery({ compact = false }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [genreFilter, setGenreFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [expandedId, setExpandedId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [playingId, setPlayingId] = useState(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/outlook/history?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setItems(data.history || []);
      }
    } catch {}
    setLoading(false);
  };

  const filtered = useMemo(() => {
    let result = items;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(i =>
        (typeof i.content === 'string' && i.content.toLowerCase().includes(q)) ||
        (i.genre || '').toLowerCase().includes(q) ||
        (i.astrology_context || '').toLowerCase().includes(q)
      );
    }
    if (genreFilter !== 'all') result = result.filter(i => i.genre === genreFilter);
    if (typeFilter !== 'all') result = result.filter(i => i.type === typeFilter);
    return result;
  }, [items, search, genreFilter, typeFilter]);

  const genres = useMemo(() => [...new Set(items.map(i => i.genre).filter(Boolean))], [items]);

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    message.success('Copied to clipboard');
    audioFeedback.playClick();
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handlePlay = async (text, id) => {
    setPlayingId(id);
    audioFeedback.playTelemetry();
    try {
      await fetch(`${API_BASE}/tts/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 1000) }),
      });
      message.success('TTS playback started');
    } catch { message.error('TTS playback failed'); }
    setPlayingId(null);
  };

  const handleExport = async () => {
    try {
      const res = await fetch(`${API_BASE}/outlook/export`);
      if (res.ok) {
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `vajra-narratives-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        message.success('Exported all narratives');
      }
    } catch { message.error('Export failed'); }
  };

  if (loading) return <Spin><div className="py-20" /></Spin>;

  return (
    <Card
      size="small"
      title={<Space><BookOpen className="w-4 h-4 text-purple-400" /><Text strong>Generated Content Gallery</Text></Space>}
      extra={
        <Space>
          <Button size="small" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchHistory} loading={loading} />
          <Button size="small" icon={<Download className="w-3 h-3" />} onClick={handleExport}>Export</Button>
        </Space>
      }
    >
      {/* Filters */}
      <Space wrap style={{ marginBottom: 16 }}>
        <Input
          size="small"
          placeholder="Search content..."
          prefix={<Search className="w-3 h-3" />}
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: 200 }}
          allowClear
        />
        <Select
          size="small"
          value={genreFilter}
          onChange={setGenreFilter}
          style={{ width: 120 }}
          options={[{ value: 'all', label: 'All Genres' }, ...genres.map(g => ({ value: g, label: g }))]}
        />
        <Select
          size="small"
          value={typeFilter}
          onChange={setTypeFilter}
          style={{ width: 110 }}
          options={[
            { value: 'all', label: 'All Types' },
            { value: 'single', label: 'Single' },
            { value: 'epic', label: 'Epic' },
          ]}
        />
        <Text type="secondary" style={{ fontSize: 11 }}>{filtered.length} of {items.length}</Text>
      </Space>

      {filtered.length === 0 ? (
        <Empty description={items.length === 0 ? "No generated content yet — generate a blessing from the Outlook tab" : "No results match your filters"} />
      ) : compact ? (
        /* Compact list */
        <List
          size="small"
          dataSource={filtered.slice(0, 10)}
          renderItem={item => (
            <List.Item
              actions={[
                <Button key="copy" type="text" size="small" icon={copiedId === item.id ? <CheckCircle className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                  onClick={() => handleCopy(typeof item.content === 'string' ? item.content : JSON.stringify(item.content), item.id)} />,
                <Button key="play" type="text" size="small" icon={playingId === item.id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Volume2 className="w-3 h-3" />}
                  onClick={() => handlePlay(typeof item.content === 'string' ? item.content : '', item.id)}
                  disabled={!item.content || typeof item.content !== 'string'} />,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space size={4}>
                    <AntTag color={GENRE_COLORS[item.genre] || 'default'} style={{ fontSize: 10 }}>{item.genre}</AntTag>
                    <AntTag style={{ fontSize: 9 }}>{item.type}</AntTag>
                    <Text style={{ fontSize: 12, fontWeight: 600 }}>
                      {typeof item.content === 'string' ? item.content.slice(0, 60) : `${item.type} narrative`}...
                    </Text>
                  </Space>
                }
                description={
                  <Text type="secondary" style={{ fontSize: 10 }}>
                    {item.date_generated?.slice(0, 16)?.replace('T', ' ')} · {item.astrology_context?.slice(0, 40) || 'No astrology context'}
                  </Text>
                }
              />
            </List.Item>
          )}
        />
      ) : (
        /* Full card view */
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1">
          {filtered.map(item => {
            const isExpanded = expandedId === item.id;
            const content = typeof item.content === 'string' ? item.content : JSON.stringify(item.content, null, 2);
            return (
              <Card
                key={item.id}
                size="small"
                hoverable
                className="transition-all"
                onClick={() => setExpandedId(isExpanded ? null : item.id)}
              >
                <div className="flex justify-between items-start">
                  <Space size={4} wrap>
                    <AntTag color={GENRE_COLORS[item.genre] || 'default'} style={{ fontSize: 10 }}>{item.genre || 'unknown'}</AntTag>
                    <AntTag style={{ fontSize: 9 }}>{item.type}</AntTag>
                    {item.languages && (Array.isArray(item.languages) ? item.languages : [item.languages]).map(l => (
                      <AntTag key={l} color="cyan" style={{ fontSize: 8 }}>{l}</AntTag>
                    ))}
                  </Space>
                  <Space size={4}>
                    <Text type="secondary" style={{ fontSize: 10 }}>{item.date_generated?.slice(0, 16)?.replace('T', ' ')}</Text>
                    {isExpanded ? <ChevronUp className="w-3 h-3 text-gray-500" /> : <ChevronDown className="w-3 h-3 text-gray-500" />}
                  </Space>
                </div>

                {isExpanded && (
                  <div className="mt-3 space-y-3">
                    <Paragraph
                      style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7, fontFamily: 'Georgia, serif', maxHeight: 400, overflowY: 'auto' }}
                    >
                      {content}
                    </Paragraph>

                    <Divider style={{ margin: '8px 0' }} />

                    {item.astrology_context && (
                      <div>
                        <Text strong style={{ fontSize: 10 }}>🌟 Astrology</Text>
                        <Paragraph type="secondary" style={{ fontSize: 10 }} ellipsis={{ rows: 2 }}>{item.astrology_context}</Paragraph>
                      </div>
                    )}
                    {item.divination_context && (
                      <div>
                        <Text strong style={{ fontSize: 10 }}>🔮 Divination</Text>
                        <Paragraph type="secondary" style={{ fontSize: 10 }} ellipsis={{ rows: 2 }}>{item.divination_context}</Paragraph>
                      </div>
                    )}

                    <Space>
                      <Button size="small" icon={copiedId === item.id ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        onClick={(e) => { e.stopPropagation(); handleCopy(content, item.id); }}>
                        {copiedId === item.id ? 'Copied' : 'Copy'}
                      </Button>
                      <Button size="small" icon={playingId === item.id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Volume2 className="w-3 h-3" />}
                        onClick={(e) => { e.stopPropagation(); handlePlay(content, item.id); }}
                        disabled={!content}>
                        Play TTS
                      </Button>
                    </Space>
                  </div>
                )}

                {!isExpanded && (
                  <Paragraph type="secondary" style={{ fontSize: 11, marginTop: 4 }} ellipsis={{ rows: 2 }}>
                    {content.slice(0, 200)}
                  </Paragraph>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </Card>
  );
}
