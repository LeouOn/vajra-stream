import React, { useState } from 'react';
import { Popover, Button, Badge, Space, Tag } from 'antd';
import { Volume2, VolumeX, Square, Radio } from 'lucide-react';
import { useAudioActivity } from '../../stores/audioActivityStore';

export default function AudioManager() {
  const [open, setOpen] = useState(false);
  const { sources, stopOne, stopAll } = useAudioActivity();
  const activeCount = sources.length;

  const formatDuration = (startedAt: number) => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const content = (
    <div className="w-72 space-y-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono uppercase tracking-wider text-gray-400">
          Audio Activity
        </span>
        {activeCount > 0 && (
          <Button
            size="small"
            danger
            icon={<Square className="w-3 h-3" />}
            onClick={() => { stopAll(); }}
          >
            Stop All
          </Button>
        )}
      </div>

      {activeCount === 0 ? (
        <div className="text-center py-6">
          <VolumeX className="w-6 h-6 text-gray-600 mx-auto mb-2" />
          <p className="text-xs text-gray-500">No active audio sources</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {sources.map((source) => (
            <div
              key={source.id}
              className="flex items-center justify-between p-2 rounded-lg bg-white/5 border border-white/5"
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="text-sm flex-shrink-0">{source.icon}</span>
                <div className="min-w-0">
                  <div className="text-xs text-gray-300 truncate">{source.name}</div>
                  <div className="text-[9px] text-gray-600 font-mono">
                    {formatDuration(source.startedAt)}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => stopOne(source.id)}
                className="flex-shrink-0 w-6 h-6 rounded flex items-center justify-center text-red-400 hover:bg-red-500/20 transition-colors"
                title="Stop"
              >
                <Square className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="topRight"
    >
      <button
        type="button"
        className="flex items-center gap-1.5 px-2 py-1 rounded transition-colors"
        style={{
          background: activeCount > 0 ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
          border: activeCount > 0 ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid transparent',
        }}
      >
        {activeCount > 0 ? (
          <>
            <Radio className="w-3.5 h-3.5 text-red-400 animate-pulse" />
            <span className="text-[10px] font-mono text-red-400">
              {activeCount} audio {activeCount === 1 ? 'source' : 'sources'}
            </span>
          </>
        ) : (
          <>
            <Volume2 className="w-3.5 h-3.5" style={{ color: 'var(--ant-color-text-tertiary)' }} />
            <span className="text-[10px] font-mono" style={{ color: 'var(--ant-color-text-tertiary)' }}>
              Audio
            </span>
          </>
        )}
      </button>
    </Popover>
  );
}
