/**
 * States — shared UI state primitives.
 *
 * Three presentational helpers used across routes to avoid re-implementing
 * the same loading / error / empty affordances inside each component.
 *
 *  - `LoadingState` — centered AntD Spin with optional message
 *  - `ErrorState`   — red-tinted card with a retry button
 *  - `EmptyState`   — AntD Empty with optional icon and description
 *
 * @component
 */
import React from 'react';
import { Alert, Button, Empty, Spin } from 'antd';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export interface LoadingStateProps {
  message?: string;
  /** Vertical height the spinner should occupy (e.g. 'h-64', 'h-96'). */
  height?: string;
}

export function LoadingState({
  message,
  height = 'h-64',
}: LoadingStateProps): React.ReactElement {
  return (
    <div className={`flex flex-col items-center justify-center ${height} w-full`}>
      <Spin size="large" />
      {message ? (
        <div className="mt-3 text-sm text-slate-400">{message}</div>
      ) : null}
    </div>
  );
}

export interface ErrorStateProps {
  message: string;
  description?: string;
  onRetry?: () => void;
  /** Vertical height the card should occupy. */
  height?: string;
}

export function ErrorState({
  message,
  description,
  onRetry,
  height = 'h-64',
}: ErrorStateProps): React.ReactElement {
  return (
    <div className={`flex items-center justify-center w-full p-4 ${height}`}>
      <Alert
        type="error"
        showIcon
        icon={<AlertTriangle className="w-5 h-5" />}
        message={message}
        description={description}
        action={
          onRetry ? (
            <Button
              type="primary"
              danger
              icon={<RefreshCw className="w-4 h-4" />}
              onClick={onRetry}
            >
              Retry
            </Button>
          ) : undefined
        }
        style={{ maxWidth: 560, width: '100%' }}
      />
    </div>
  );
}

export interface EmptyStateProps {
  message?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({
  message = 'Nothing here yet',
  description,
  icon,
  action,
}: EmptyStateProps): React.ReactElement {
  return (
    <div className="flex flex-col items-center justify-center p-8 w-full">
      <Empty
        image={icon ?? Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div className="text-center">
            <div className="text-sm text-slate-400">{message}</div>
            {description ? (
              <div className="text-xs text-slate-500 mt-1">{description}</div>
            ) : null}
          </div>
        }
      >
        {action ?? null}
      </Empty>
    </div>
  );
}