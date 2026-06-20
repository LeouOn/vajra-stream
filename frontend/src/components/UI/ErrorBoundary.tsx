import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from 'antd';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallbackTitle?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary for lazy-loaded components.
 * Catches render errors and chained-load failures (network,
 * chunk fetch, etc.) and shows a compact retry panel.
 */
export default class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="bg-red-950/20 border border-red-500/15 rounded-xl p-6 text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto" />
          <p className="text-sm text-red-300 font-semibold">
            {this.props.fallbackTitle || 'Component failed to load'}
          </p>
          <p className="text-xs text-red-400/60 font-mono max-w-md mx-auto truncate">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <Button
            size="small"
            type="primary"
            danger
            ghost
            icon={<RefreshCw className="w-3.5 h-3.5" />}
            onClick={this.handleRetry}
          >
            Retry
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
