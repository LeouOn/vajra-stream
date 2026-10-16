/**
 * CommandShortcuts — the quick-command chip row (sends a canned command)
 * and the operator quick actions (call an operator endpoint directly).
 * All buttons are disabled while a request is running.
 *
 * @component
 */
import React from 'react';
import { Button, Space } from 'antd';
import { quickCommands } from './constants';
import type { OperatorAction } from './commandCenterTypes';

interface CommandShortcutsProps {
  isLoading: boolean;
  operatorActions: OperatorAction[];
  onQuickCommand: (text: string) => void;
  onOperatorAction: (action: OperatorAction) => void;
}

export default function CommandShortcuts({ isLoading, operatorActions, onQuickCommand, onOperatorAction }: CommandShortcutsProps) {
  return (
    <>
      {/* Quick Suggestion Chips */}
      <div className="px-4 py-2 bg-gray-950/20 border-t border-white/5 overflow-x-auto">
        <Space wrap size={[4, 4]}>
          {quickCommands.map((cmd) => (
            <Button
              key={cmd.label}
              size="small"
              type="default"
              ghost
              disabled={isLoading}
              onClick={() => onQuickCommand(cmd.text)}
              style={{ fontSize: '11px', borderRadius: '12px' }}
            >
              {cmd.label}
            </Button>
          ))}
        </Space>
      </div>

      {/* Operator Quick Actions */}
      <div className="px-4 py-1.5 bg-gradient-to-r from-indigo-950/30 to-purple-950/20 border-t border-indigo-500/15">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[9px] font-mono text-indigo-300/70 uppercase tracking-wider">Operator</span>
          <Space wrap size={[4, 4]}>
            {operatorActions.map((action) => (
              <Button
                key={action.key}
                size="small"
                type="default"
                disabled={isLoading}
                onClick={() => onOperatorAction(action)}
                style={{
                  fontSize: '10px',
                  borderRadius: '12px',
                  background: 'rgba(99, 102, 241, 0.08)',
                  borderColor: 'rgba(99, 102, 241, 0.3)',
                  color: '#a5b4fc',
                }}
              >
                <span className="mr-1">{action.icon}</span>{action.label}
              </Button>
            ))}
          </Space>
        </div>
      </div>
    </>
  );
}
