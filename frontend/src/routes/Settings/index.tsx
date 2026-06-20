/**
 * SettingsPage — grouped route merging the former `/tts` route into
 * Settings as an Ant Design Tabs sibling.
 *
 * Consolidation (UI rework 2026-06-20, 12 → 7 routes):
 *   /settings        → ProviderSettings (default "LLM Providers" tab)
 *   /settings/tts    → TTSSettingsPanel (merged from the old /tts)
 *
 * ProviderSettings previously rendered standalone at `/settings` and owns
 * its own header + scroll container; TTSSettingsPanel previously rendered
 * at `/tts` wrapped in an overflow container. Neither component is
 * modified internally — both are simply placed into tab panes here.
 *
 * URL contract:
 *   /settings        → default tab (providers)
 *   /settings/tts    → tts tab
 *   Unknown/legacy :tab → falls back to the default tab.
 *
 * @component
 * @route /settings/:tab
 */
import React from 'react';
import { Tabs } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import ProviderSettings from '../../components/Settings/ProviderSettings';
import TTSSettingsPanel from '../../components/UI/TTSSettingsPanel';

const TAB_KEYS = ['providers', 'tts'] as const;
type TabKey = (typeof TAB_KEYS)[number];

const DEFAULT_TAB: TabKey = 'providers';

/** Height reserved above the tab pane (header + tab bar + footer). */
const PANE_HEIGHT = 'calc(100vh - 176px)';

function resolveTab(tab: string | undefined): TabKey {
  if (tab && (TAB_KEYS as readonly string[]).includes(tab)) {
    return tab as TabKey;
  }
  return DEFAULT_TAB;
}

export default function SettingsPage(): React.ReactElement {
  const { tab } = useParams<{ tab: string }>();
  const navigate = useNavigate();
  const activeTab = resolveTab(tab);

  const items = [
    {
      key: 'providers',
      label: 'LLM Providers',
      children: (
        <div style={{ height: PANE_HEIGHT }}>
          <ProviderSettings />
        </div>
      ),
    },
    {
      key: 'tts',
      label: 'TTS',
      children: (
        <div style={{ height: PANE_HEIGHT }} className="overflow-y-auto p-6">
          <TTSSettingsPanel />
        </div>
      ),
    },
  ];

  const handleChange = (key: string): void => {
    navigate(`/settings/${key}`);
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
