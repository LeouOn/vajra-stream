/**
 * PageHeader — consistent route-level header strip.
 *
 * Renders an icon, a level-2 title, an optional secondary subtitle,
 * and an optional right-aligned actions slot. Spacing is unified via
 * marginBottom: 16 so every route has the same vertical rhythm under
 * its header.
 *
 * @component
 */
import React from 'react';
import { Space, Typography } from 'antd';

const { Title, Text } = Typography;

export interface PageHeaderProps {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export default function PageHeader({
  icon,
  title,
  subtitle,
  actions,
}: PageHeaderProps): React.ReactElement {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        marginBottom: 16,
        width: '100%',
      }}
    >
      <Space size={12} align="center" style={{ minWidth: 0 }}>
        {icon}
        <div style={{ minWidth: 0 }}>
          <Title level={2} style={{ margin: 0 }}>
            {title}
          </Title>
          {subtitle ? (
            <Text type="secondary" style={{ fontSize: 13 }}>
              {subtitle}
            </Text>
          ) : null}
        </div>
      </Space>
      {actions ? <Space size={8}>{actions}</Space> : null}
    </div>
  );
}