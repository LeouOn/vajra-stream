/**
 * Status chip for an operation. Plain words, no scores.
 * @component
 */
import React from 'react';
import { Tag } from 'antd';
import type { OperationStatus } from '../../types/operations';

const STATUS_COLOR: Record<OperationStatus, string> = {
  queued: 'default',
  running: 'processing',
  success: 'success',
  error: 'error',
  cancelled: 'default',
  interrupted: 'warning',
};

export default function OperationStatusTag({ status }: { status: OperationStatus }): React.ReactElement {
  return (
    <Tag color={STATUS_COLOR[status] ?? 'default'} data-testid="op-status" style={{ marginInlineEnd: 0 }}>
      {status}
    </Tag>
  );
}
