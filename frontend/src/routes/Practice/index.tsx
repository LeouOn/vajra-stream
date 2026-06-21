/**
 * PracticePage — grouped route wrapping four practice surfaces in an
 * Ant Design Tabs component, with the active tab deep-linked to the URL.
 *
 * Consolidates the former flat routes (12 → 7, UI rework 2026-06-20):
 *   /sanctuary   → /practice/sanctuary   (SanctuaryPage)
 *   /buddhas     → /practice/buddhas     (BuddhasPage)
 *   /meditation  → /practice/meditation  (MeditationTab — Rothko fullscreen)
 *   /visualizers → /practice/visualizers (VisualizerTab — 3D sacred geometry)
 *   /scalar      → /practice/scalar      (ScalarTab — Living Mandala)
 *
 * URL contract:
 *   /practice             → redirects to /practice/sanctuary (App.tsx)
 *   /practice/:tab        → renders the matching tab; unknown tabs fall
 *                            back to the default (sanctuary) so deep
 *                            links never render a blank pane.
 *
 * The existing page components are imported unchanged — this wrapper is
 * purely a tabbed container (no internal modifications).
 *
 * @component
 * @route /practice/:tab
 */
import React from 'react';
import { Tabs } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import SanctuaryPage from '../Sanctuary';
import BuddhasPage from '../Buddhas';
import MeditationTab from './MeditationTab';
import VisualizerTab from './VisualizerTab';
import ScalarTab from './ScalarTab';

const PRACTICE_TAB_KEYS = ['sanctuary', 'buddhas', 'meditation', 'visualizers', 'scalar'] as const;
type PracticeTabKey = (typeof PRACTICE_TAB_KEYS)[number];

const DEFAULT_TAB: PracticeTabKey = 'sanctuary';

/** Height reserved above the tab pane (header + tab bar + footer). */
const PANE_HEIGHT = 'calc(100vh - 176px)';

function resolveTab(tab: string | undefined): PracticeTabKey {
  if (tab && (PRACTICE_TAB_KEYS as readonly string[]).includes(tab)) {
    return tab as PracticeTabKey;
  }
  return DEFAULT_TAB;
}

export default function PracticePage(): React.ReactElement {
  const { tab } = useParams<{ tab: string }>();
  const navigate = useNavigate();
  const activeTab = resolveTab(tab);

  const items = [
    {
      key: 'sanctuary',
      label: 'Sanctuary',
      children: (
        <div style={{ height: PANE_HEIGHT }} className="overflow-hidden">
          <SanctuaryPage />
        </div>
      ),
    },
    {
      key: 'buddhas',
      label: '88 Buddhas',
      children: (
        <div style={{ height: PANE_HEIGHT }} className="overflow-y-auto">
          <BuddhasPage />
        </div>
      ),
    },
    {
      key: 'meditation',
      label: 'Meditation',
      children: (
        <div style={{ height: PANE_HEIGHT }}>
          <MeditationTab />
        </div>
      ),
    },
    {
      key: 'visualizers',
      label: 'Visualizer',
      children: (
        <div style={{ height: PANE_HEIGHT }}>
          <VisualizerTab />
        </div>
      ),
    },
    {
      key: 'scalar',
      label: 'Living Mandala',
      children: (
        <div style={{ height: PANE_HEIGHT }} className="overflow-hidden">
          <ScalarTab />
        </div>
      ),
    },
  ];

  const handleChange = (key: string): void => {
    navigate(`/practice/${key}`);
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
