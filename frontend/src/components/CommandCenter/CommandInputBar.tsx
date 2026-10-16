/**
 * CommandInputBar — the "Instruct the system..." input with Send, which
 * turns into Stop (cancel the running job) while a request is in flight.
 *
 * @component
 */
import React from 'react';
import { Send, Square } from 'lucide-react';
import { Input, Button, Space } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';

interface CommandInputBarProps {
  input: string;
  isLoading: boolean;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

export default function CommandInputBar({ input, isLoading, onInputChange, onSubmit, onCancel }: CommandInputBarProps) {
  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
      className="p-4 border-t border-purple-500/15 bg-black/40"
    >
      <Space.Compact style={{ width: '100%' }}>
        <Input
          value={input}
          onChange={(e) => { onInputChange(e.target.value); audioFeedback.playType(); }}
          disabled={isLoading}
          placeholder="Instruct the system..."
          className="bg-gray-900 border-purple-500/30 text-white placeholder:text-purple-300/40"
          style={{ flex: 1 }}
        />
        {isLoading ? (
          <Button
            danger
            icon={<Square style={{ width: 16, height: 16 }} />}
            onClick={onCancel}
            style={{ display: 'flex', alignItems: 'center' }}
          >
            Stop
          </Button>
        ) : (
          <Button
            type="primary"
            htmlType="submit"
            disabled={!input.trim()}
            icon={<Send style={{ width: 16, height: 16 }} />}
            style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)', border: 'none', display: 'flex', alignItems: 'center' }}
          >
            Send
          </Button>
        )}
      </Space.Compact>
    </form>
  );
}
