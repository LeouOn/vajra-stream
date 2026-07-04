/**
 * IntentionEditor — set the bodhicitta intention for a recitation session.
 *
 * Controlled TextArea that fires `onChange(text)` on every keystroke so the
 * parent page can hold the canonical copy (used for both display and the
 * eventual `/operator/buddhas/recitation/start` POST). Persists the last
 * submitted intention to localStorage so a refresh doesn't lose the user's
 * vow. No polling — the parent owns buddhaStatus via useWebSocketStable.
 *
 * @component
 */
import React, { useCallback, useEffect } from 'react';
import { Card, Input, Typography, Space, Tag } from 'antd';
import { Heart, Sparkles } from 'lucide-react';

const { Text, Title } = Typography;
const { TextArea } = Input;

const STORAGE_KEY = 'vajra-buddha-intention';
const MAX_LENGTH = 280;
const DEFAULT_INTENTION = '愿一切众生离苦得乐'; // May all beings be free from suffering and find happiness

interface IntentionEditorProps {
  /** Current intention text. */
  value: string;
  /** Callback fired with the new string on change. */
  onChange: (text: string) => void;
}

export default function IntentionEditor({ value, onChange }: IntentionEditorProps) {
  // Hydrate once on mount: if the parent gave us a value, persist it;
  // otherwise restore the last saved intention from localStorage.
  useEffect(() => {
    if (value) {
      try { localStorage.setItem(STORAGE_KEY, value); } catch { /* quota / private mode */ }
      return;
    }
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      onChange?.(saved || DEFAULT_INTENTION);
    } catch { /* ignore */ }
  }, [value, onChange]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const next = e.target.value ?? '';
      onChange?.(next);
      try { localStorage.setItem(STORAGE_KEY, next); } catch { /* ignore */ }
    },
    [onChange],
  );

  return (
    <Card
      size="small"
      title={
        <Space size={8} align="center">
          <Heart size={16} className="text-amber-400" />
          <Title level={5} style={{ margin: 0 }}>Bodhicitta Intention</Title>
        </Space>
      }
      extra={<Tag color="amber">发心</Tag>}
    >
      <Space orientation="vertical" size={8} style={{ width: '100%' }}>
        <Text type="secondary" italic style={{ fontSize: 12 }}>
          Set the heart-intention that dedicates the merit of this recitation.
        </Text>
        <TextArea
          value={value ?? ''}
          onChange={handleChange}
          autoSize={{ minRows: 2, maxRows: 5 }}
          maxLength={MAX_LENGTH}
          showCount
          placeholder="May all beings be free from suffering and the causes of suffering…"
        />
        <Space size={6} align="center">
          <Sparkles size={12} className="text-purple-400" />
          <Text type="secondary" style={{ fontSize: 11 }}>
            Carries through every name chanted in this session.
          </Text>
        </Space>
      </Space>
    </Card>
  );
}
