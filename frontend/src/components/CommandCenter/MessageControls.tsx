/**
 * MessageControls — per-assistant-message footer: debug toggle, model
 * picker to regenerate with another model, regenerate with the same model,
 * and the token / latency / cost line with the provider's health.
 *
 * @component
 */
import React, { useState } from 'react';
import { Select } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import type { ChatMessage, ProviderHealthEntry } from './commandCenterTypes';

interface MessageControlsProps {
  msg: ChatMessage;
  disabled: boolean;
  modelOptions: DefaultOptionType[];
  providerHealth?: ProviderHealthEntry[];
  onRegenerate: (model: string | null) => void;
}

export default function MessageControls({ msg, disabled, modelOptions, providerHealth = [], onRegenerate }: MessageControlsProps) {
  const [showDebug, setShowDebug] = useState(false);
  const [pickModel, setPickModel] = useState(false);
  const dbg = msg.debugInfo || {};
  const hasDebug = !!msg.debugInfo;

  const tokenPart = (msg.inputTokens != null && msg.outputTokens != null)
    ? `${msg.inputTokens}→${msg.outputTokens} tokens`
    : null;
  const latencyPart = msg.latencyMs != null ? `${(msg.latencyMs / 1000).toFixed(1)}s` : null;
  const costPart = msg.costUsd != null ? `$${msg.costUsd.toFixed(4)}` : null;

  const compactParts = [tokenPart, latencyPart, costPart].filter(Boolean);
  const compactLine = compactParts.length > 0 ? compactParts.join(' | ') : null;

  const msgProvider = msg.providerUsed || dbg.provider || dbg.provider_selected;
  const providerHealthEntry = msgProvider
    ? providerHealth.find(p => p.provider === msgProvider)
    : undefined;

  return (
    <div className="mt-2 pt-2 border-t border-white/5 flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          type="button"
          onClick={() => setShowDebug(v => !v)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono text-purple-300/80 hover:text-purple-200 hover:bg-purple-500/10 transition-colors"
          title="Toggle debug info"
        >
          🔧 Debug
        </button>

        <button
          type="button"
          onClick={() => setPickModel(v => !v)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono text-cyan-300/80 hover:text-cyan-200 hover:bg-cyan-500/10 transition-colors"
          title="Change model and regenerate"
          disabled={disabled}
        >
          {msg.modelUsed
            ? <span className="max-w-[160px] truncate">{msg.modelUsed}</span>
            : <span>Model</span>}
        </button>

        <button
          type="button"
          onClick={() => onRegenerate(null)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono text-emerald-300/80 hover:text-emerald-200 hover:bg-emerald-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          title="Regenerate with the same model"
          disabled={disabled}
        >
          🔄 Regenerate
        </button>

        {compactLine && (
          <span className="text-[9px] font-mono text-gray-500 ml-auto">{compactLine}</span>
        )}
      </div>

      {msg.modelUsed && (
        <div className="text-[9px] font-mono text-gray-600">
          Model: {msg.modelUsed}
          {msgProvider && providerHealthEntry && (
            <span style={{ color: providerHealthEntry.healthy ? '#52c41a' : '#ff4d4f' }}>
              {' '}({providerHealthEntry.healthy ? '✓' : '✗'} {msgProvider})
            </span>
          )}
          {compactLine && <span className="text-gray-500"> | {compactLine}</span>}
        </div>
      )}

      {pickModel && (
        <div className="bg-black/40 border border-white/10 rounded p-2">
          <div className="text-[10px] text-gray-400 mb-1 font-mono">
            Regenerate this message with a different model:
          </div>
          <Select
            size="small"
            showSearch
            placeholder="Pick a model..."
            style={{ width: '100%', fontSize: '11px' }}
            optionFilterProp="label"
            options={modelOptions}
            onChange={(val: string) => {
              setPickModel(false);
              onRegenerate(val);
            }}
          />
        </div>
      )}

      {showDebug && (
        <div className="bg-black/50 border border-yellow-500/20 rounded p-2 text-[10px] font-mono text-yellow-200/90 space-y-1 overflow-x-auto">
          <div><span className="text-yellow-500">model:</span> {msg.modelUsed || '—'}</div>
          <div><span className="text-yellow-500">provider:</span> {msgProvider || '—'}</div>
          {tokenPart && <div><span className="text-yellow-500">tokens:</span> {tokenPart}</div>}
          {latencyPart && <div><span className="text-yellow-500">latency:</span> {latencyPart}</div>}
          {costPart && <div><span className="text-yellow-500">cost:</span> {costPart}</div>}
          {dbg.finish_reason && <div><span className="text-yellow-500">finish:</span> {dbg.finish_reason}</div>}
          {dbg.reasoning_tokens != null && (
            <div><span className="text-yellow-500">reasoning_tokens:</span> {dbg.reasoning_tokens}</div>
          )}
          {providerHealth.length > 0 && (
            <div className="pt-1 mt-1 border-t border-yellow-500/10">
              <div className="text-yellow-500 mb-0.5">provider health:</div>
              {providerHealth.map(ph => (
                <div key={ph.provider} className="flex items-center gap-1">
                  <span style={{ color: ph.healthy ? '#52c41a' : '#ff4d4f' }}>
                    {ph.healthy ? '●' : '○'}
                  </span>
                  <span>{ph.provider}</span>
                  {ph.latency_ms != null && <span className="text-gray-400">{Math.round(ph.latency_ms)}ms</span>}
                  {ph.error && <span className="text-red-400 truncate">{ph.error}</span>}
                </div>
              ))}
            </div>
          )}
          {msg.reasoningContent && (
            <details className="mt-1">
              <summary className="cursor-pointer text-yellow-400/80 select-none">💭 Reasoning content</summary>
              <pre className="mt-1 whitespace-pre-wrap break-words text-yellow-100/70 max-h-60 overflow-y-auto">{msg.reasoningContent}</pre>
            </details>
          )}
          {!hasDebug && (
            <div className="text-gray-500 italic">
              No debug info — enable 🛠️ Debug mode in the env bar before sending to capture per-message details.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
