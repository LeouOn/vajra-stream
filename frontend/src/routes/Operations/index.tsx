/**
 * OperationsPage — grouped route merging the former `/broadcast` route
 * into Operations as an Ant Design Tabs sibling.
 *
 * Consolidation (UI rework 2026-06-20, 12 → 7 routes):
 *   /operations            → OperationsPanel (default "Operations" tab,
 *                             keeps its internal divination/composer/etc.
 *                             sub-tabs fully intact — not modified)
 *   /operations/broadcast  → BroadcastPanel (merged from the old /broadcast)
 *
 * The existing OperationsPanel already owns a rich internal sub-tab strip
 * (Divination Suite / Ritual Composer / Prayer Wheel / Dharani / Chakra /
 * Time Cycles). Rather than mutating that component, we wrap it in a
 * top-level AntD Tabs row so Broadcast becomes a peer surface. This
 * preserves all existing behavior while satisfying the merge requirement.
 *
 * URL contract:
 *   /operations             → default tab (operations)
 *   /operations/broadcast   → broadcast tab
 *   Unknown/legacy :tab     → falls back to the default tab.
 *
 * @component
 * @route /operations/:tab
 */
import React from 'react';
import { Tabs } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import OperationsPanel from '../../components/UI/OperationsPanel';
import BroadcastPanel from '../../components/UI/BroadcastPanel';

const TAB_KEYS = ['operations', 'broadcast'] as const;
type TabKey = (typeof TAB_KEYS)[number];

const DEFAULT_TAB: TabKey = 'operations';

/** Height reserved above the tab pane (header + tab bar + footer). */
const PANE_HEIGHT = 'calc(100vh - 176px)';

function resolveTab(tab: string | undefined): TabKey {
  if (tab && (TAB_KEYS as readonly string[]).includes(tab)) {
    return tab as TabKey;
  }
  return DEFAULT_TAB;
}

export default function OperationsPage(): React.ReactElement {
  const { tab } = useParams<{ tab: string }>();
  const navigate = useNavigate();
  const activeTab = resolveTab(tab);

  const items = [
    {
      key: 'operations',
      label: 'Operations',
      children: (
        <div style={{ height: PANE_HEIGHT }}>
          <OperationsPanel />
        </div>
      ),
    },
    {
      key: 'broadcast',
      label: 'Broadcast',
      children: (
        <div style={{ height: PANE_HEIGHT }} className="overflow-y-auto">
          <BroadcastPanel />
        </div>
      ),
    },
  ];

  const handleChange = (key: string): void => {
    navigate(`/operations/${key}`);
  };

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <Tabs
        activeKey={activeTab}
        onChange={handleChange}
        items={items}
        size="large"
        tabBarStyle={{ paddingLeft: 16, paddingRight: 16, marginBottom: 0 }}
      />
    </div>
  );
}
