/**
 * ChatHeader — the chat card's title bar with the LLM agent's connection
 * badge.
 *
 * @component
 */
import React from 'react';
import { Cpu } from 'lucide-react';
import { Badge, Space, Tag } from 'antd';

interface ChatHeaderProps {
  isConnected: boolean;
}

export default function ChatHeader({ isConnected }: ChatHeaderProps) {
  return (
    <div className="bg-gradient-to-r from-purple-900/40 via-indigo-900/40 to-blue-900/40 p-4 border-b border-white/10 flex justify-between items-center">
      <Space size={12}>
        <Badge status={isConnected ? 'processing' : 'error'} color={isConnected ? 'purple' : 'red'} />
        <div>
          <h2 className="text-lg font-bold text-white tracking-wide" style={{ margin: 0 }}>AI Command Center</h2>
          <p className="text-xs text-purple-300" style={{ margin: 0 }}>Vajra.Stream Digital Operator v1.2</p>
        </div>
      </Space>
      <Tag
        color={isConnected ? 'purple' : 'red'}
        icon={<Cpu style={{ width: 12, height: 12 }} />}
        className="font-mono text-[10px]"
      >
        {isConnected ? 'LLM AGENT ACTIVE' : 'LLM AGENT OFFLINE'}
      </Tag>
    </div>
  );
}
