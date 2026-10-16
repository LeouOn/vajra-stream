/**
 * ChatMessageList — the scrolling conversation: user / assistant bubbles
 * (markdown, tool widgets, Retry on errors, per-message controls), the
 * "Working…" indicator while a job runs, and the suggested intentions
 * shown before the first exchange.
 *
 * @component
 */
import React from 'react';
import { RotateCcw } from 'lucide-react';
import type { DefaultOptionType } from 'antd/es/select';
import { audioFeedback } from '../../utils/audioFeedback';
import { RenderMessageWidgets } from './RenderMessageWidgets';
import type { ZoomItem } from './RenderMessageWidgets';
import { RichMarkdownRenderer } from './RichMarkdownRenderer';
import MessageControls from './MessageControls';
import type { ChatMessage, ProviderHealthEntry } from './commandCenterTypes';

const SUGGESTED_INTENTIONS = [
  { icon: '🌿', label: 'Generate a healing blessing', text: 'Generate a healing blessing narrative for all beings suffering from illness' },
  { icon: '🛡️', label: 'Cast protection ritual', text: 'Create a protection ritual to shield against negative forces' },
  { icon: '☯️', label: 'Consult the I Ching', text: 'Cast the I Ching and interpret the hexagram for my current situation' },
  { icon: '📿', label: 'Compose a dharani', text: 'Compose a dharani for purification of all obscurations' },
];

interface ChatMessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
  chatPhase: string;
  modelOptions: DefaultOptionType[];
  providerHealth: ProviderHealthEntry[];
  messagesEndRef: React.RefObject<HTMLDivElement>;
  onZoomItemClick: (item: ZoomItem) => void;
  onRetry: (index: number, text: string) => void;
  onRegenerate: (index: number, model: string | null) => void;
  onSuggest: (text: string) => void;
}

export default function ChatMessageList({
  messages, isLoading, chatPhase, modelOptions, providerHealth, messagesEndRef,
  onZoomItemClick, onRetry, onRegenerate, onSuggest,
}: ChatMessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
      {messages.map((msg, index) => (
        <div
          key={index}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div className={`
            max-w-[85%] rounded-xl px-4 py-3 shadow-lg
            ${msg.role === 'user'
              ? 'bg-gradient-to-br from-purple-600/90 to-indigo-700/95 text-white rounded-br-none border border-purple-400/20 shadow-[0_4px_12px_rgba(138,43,226,0.3)]'
              : 'bg-purple-950/25 backdrop-blur-md text-gray-100 rounded-bl-none border border-purple-500/20 shadow-[0_4px_12px_rgba(0,0,0,0.3)]'
            }
          `}>
            <div className="markdown-container">
              <RichMarkdownRenderer content={msg.content} />
            </div>
            {msg.role === 'assistant' && msg.toolCalls && (
              <RenderMessageWidgets toolCalls={msg.toolCalls} onZoomItemClick={onZoomItemClick} />
            )}
            {msg.role === 'assistant' && msg.isError && msg.retryInput && (
              <div className="mt-2 pt-2 border-t border-red-500/20">
                <button
                  type="button"
                  onClick={() => onRetry(index, msg.retryInput!)}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono text-red-300 border border-red-500/30 hover:bg-red-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <RotateCcw style={{ width: 11, height: 11 }} />
                  Retry
                </button>
              </div>
            )}
            {msg.role === 'assistant' && index > 0 && !msg.isError && (
              <MessageControls
                msg={msg}
                disabled={isLoading}
                modelOptions={modelOptions}
                providerHealth={providerHealth}
                onRegenerate={(model) => onRegenerate(index, model)}
              />
            )}
          </div>
        </div>
      ))}
      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-purple-950/25 backdrop-blur-md rounded-xl rounded-bl-none px-4 py-3 border border-purple-500/20 shadow-lg flex items-center space-x-3">
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-[11px] font-mono text-purple-300/80">
              {chatPhase ? `Working… ${chatPhase}` : 'Generating...'}
            </span>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />

      {messages.length <= 1 && !isLoading && (
        <div className="flex flex-col items-center justify-center flex-1 pb-8 px-4">
          <p className="text-[10px] font-mono uppercase tracking-widest text-purple-400/40 mb-4">Suggested Intentions</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full">
            {SUGGESTED_INTENTIONS.map((s) => (
              <button
                key={s.label}
                type="button"
                onClick={() => { onSuggest(s.text); audioFeedback.playClick(); }}
                className="flex items-center gap-3 p-3 rounded-xl bg-purple-950/20 border border-purple-500/15 hover:border-purple-500/40 hover:bg-purple-900/20 transition-all duration-200 text-left group"
              >
                <span className="text-xl flex-shrink-0">{s.icon}</span>
                <span className="text-xs text-gray-400 group-hover:text-purple-200 transition-colors">{s.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
