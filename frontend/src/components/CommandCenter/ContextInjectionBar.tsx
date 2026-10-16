/**
 * ContextInjectionBar — the env bar under the chat: which context to inject
 * (astrology, chakras, status & ledger), the model picker, provider health
 * summary, and debug mode.
 *
 * @component
 */
import React from 'react';
import { Activity } from 'lucide-react';
import { Select, Switch, Space, Tooltip } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { audioFeedback } from '../../utils/audioFeedback';
import type { ProviderHealthEntry } from './commandCenterTypes';
import type { ChatEnvironment } from './useChatEnvironment';

interface ContextInjectionBarProps {
  env: ChatEnvironment;
  selectedModel: string;
  onSelectModel: (model: string) => void;
  modelOptions: DefaultOptionType[];
  providerHealth: ProviderHealthEntry[];
}

export default function ContextInjectionBar({ env, selectedModel, onSelectModel, modelOptions, providerHealth }: ContextInjectionBarProps) {
  const {
    includeAstrology, setIncludeAstrology, includeAnatomy, setIncludeAnatomy,
    includeHardware, setIncludeHardware, debugMode, setDebugMode,
  } = env;

  return (
    <div className="px-4 py-2 border-t border-purple-500/15 bg-black/30 flex flex-wrap items-center gap-4 text-xs font-mono select-none">
      <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Inject Context:</span>

      <Space size={8} wrap>
        <Space size={4}>
          <Switch size="small" checked={includeAstrology} onChange={(v) => { setIncludeAstrology(v); audioFeedback.playClick(); }} />
          <span className="text-gray-400 text-[11px]">🪐 Astrology</span>
        </Space>
        <Space size={4}>
          <Switch size="small" checked={includeAnatomy} onChange={(v) => { setIncludeAnatomy(v); audioFeedback.playClick(); }} />
          <span className="text-gray-400 text-[11px]">💚 Chakras</span>
        </Space>
        <Space size={4}>
          <Switch size="small" checked={includeHardware} onChange={(v) => { setIncludeHardware(v); audioFeedback.playClick(); }} />
          <span className="text-gray-400 text-[11px]">⚙️ Status &amp; Ledger</span>
        </Space>
      </Space>

      <Space size={4} style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: 16 }}>
        <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Model:</span>
        <Select
          size="small"
          value={selectedModel || 'auto'}
          onChange={(val: string) => { onSelectModel(val); audioFeedback.playClick(); }}
          style={{ minWidth: 160, fontSize: '11px' }}
          className="font-mono"
          styles={{ popup: { root: { minWidth: 260 } } }}
          placeholder="Select model..."
          showSearch
          optionFilterProp="label"
          options={modelOptions}
        />
      </Space>

      {providerHealth.length > 0 && (
        <Tooltip
          title={
            <div className="text-[10px] font-mono space-y-0.5">
              {providerHealth.map(ph => (
                <div key={ph.provider} className="flex items-center gap-1">
                  <span style={{ color: ph.healthy ? '#52c41a' : '#ff4d4f' }}>
                    {ph.healthy ? '●' : '○'}
                  </span>
                  <span>{ph.provider}</span>
                  {ph.latency_ms != null && <span className="text-gray-400">{Math.round(ph.latency_ms)}ms</span>}
                </div>
              ))}
            </div>
          }
        >
          <span className="text-[10px] font-mono text-gray-500 flex items-center gap-1 cursor-help">
            <Activity style={{ width: 10, height: 10 }} />
            {providerHealth.filter(p => p.healthy).length}/{providerHealth.length} providers
          </span>
        </Tooltip>
      )}

      <Space size={4} style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: 16 }}>
        <Switch size="small" checked={debugMode} onChange={(v) => { setDebugMode(v); audioFeedback.playClick(); }} />
        <span className="text-yellow-500/95 font-bold text-[11px]">🛠️ Debug</span>
      </Space>
    </div>
  );
}
