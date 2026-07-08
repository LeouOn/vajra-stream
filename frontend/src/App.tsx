import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useWebSocketStable as useWebSocket } from './hooks/useWebSocketStable';
import { useAudioStore } from './stores/audioStore';

/** MOPS throughput windows (matches MainLayout.MopsData structural shape). */
interface MopsWindow {
  [window: string]: number;
}

interface MopsData {
  scalar_pulses?: MopsWindow;
  mantras?: MopsWindow;
  crystals?: MopsWindow;
  divination?: MopsWindow;
  tuning?: MopsWindow;
}

// Ant Design
import { ConfigProvider, theme, Result } from 'antd';

import MainLayout from './components/Layout/MainLayout';
import CommandCenter from './components/UI/CommandCenter';
import AstrologyPanel from './components/UI/AstrologyPanel';
import OutlookDashboard from './components/UI/OutlookDashboard';
import GrimoirePanel from './components/UI/GrimoirePanel';
import PracticePage from './routes/Practice';
import OperationsPage from './routes/Operations';
import SettingsPage from './routes/Settings';
import PracticeSelector from './components/UI/PracticeSelector';
import PracticeDetail from './components/UI/PracticeDetail';
import ErrorBoundary from './components/UI/ErrorBoundary';
import { audioFeedback } from './utils/audioFeedback';
import { COLORS } from './lib/colors';
import { antdTheme } from './theme/antdTheme';
import { DEFAULT_ROUTE } from './lib/routes';

function AppContent(): React.ReactElement {
  const [mopsData, setMopsData] = useState<MopsData | null>(null);
  const location = useLocation();
  const activeTab = location.pathname.split('/')[1] || DEFAULT_ROUTE;

  useEffect(() => {
    const fetchMops = async (): Promise<void> => {
      try {
        const res = await fetch('/api/v1/mops/current');
        if (res.ok) {
          const data = await res.json();
          setMopsData(data.mops as MopsData);
        }
      } catch {
        // Ignore connectivity warnings
      }
    };
    fetchMops();
    const interval = setInterval(fetchMops, 2000);
    return () => clearInterval(interval);
  }, []);

  const {
    isConnected,
    sessions,
    crystalStatus,
    scalarStatus,
    buddhaStatus,
    sakaDawa,
    practices: wsPractices
  } = useWebSocket();

  const {
    isPlaying,
    frequency,
    volume,
    prayerBowlMode,
    updateSettings,
    generateAudio,
    playAudio,
    stopAudio,
  } = useAudioStore();

  useEffect(() => {
    updateSettings({
      frequency: 136.1,
      volume: 0.8,
      prayerBowlMode: true,
      harmonicStrength: 0.3,
      modulationDepth: 0.05
    });
  }, [updateSettings]);

  const isFirstRender = useRef<boolean>(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    audioFeedback.playTabChange();
  }, [activeTab]);

  useEffect(() => {
    if (isFirstRender.current) return;
    audioFeedback.playClick();
  }, [activeTab]);

  return (
    <MainLayout
      isConnected={isConnected}
      isPlaying={isPlaying}
      frequency={frequency}
      volume={volume}
      prayerBowlMode={prayerBowlMode}
      generateAudio={async (): Promise<void> => { await generateAudio(); }}
      playAudio={async (): Promise<void> => { await playAudio(); }}
      stopAudio={(): void => { void stopAudio(); }}
      mopsData={mopsData}
    >
      <Routes>
        <Route path="/" element={<Navigate to={`/${DEFAULT_ROUTE}`} replace />} />

        {/* ==================== MAIN GROUPED ROUTES (7) ====================
            Every renderable route is wrapped in <ErrorBoundary> so a single
            render error in any view (or a lazy-loaded chunk failure) is
            contained and shows a retry panel instead of crashing the app. */}

        <Route path="/command-center" element={
          <ErrorBoundary fallbackTitle="Command Center failed to render">
            <div className="flex-1 h-full overflow-hidden">
              <CommandCenter
                isConnected={isConnected}
                isPlaying={isPlaying}
                frequency={frequency}
                crystalStatus={crystalStatus}
                scalarStatus={scalarStatus}
                sessions={sessions}
                buddhaStatus={buddhaStatus}
                sakaDawa={sakaDawa}
              />
            </div>
          </ErrorBoundary>
        } />

        <Route path="/practice" element={<Navigate to="/practice/sanctuary" replace />} />
        <Route path="/practice/:tab" element={
          <ErrorBoundary fallbackTitle="Practice view failed to render">
            <PracticePage />
          </ErrorBoundary>
        } />

        <Route path="/practices" element={
          <ErrorBoundary fallbackTitle="Practice Library failed to render">
            <div className="flex-1 h-full overflow-hidden">
              <PracticeSelector />
            </div>
          </ErrorBoundary>
        } />
        <Route path="/practices/:id" element={
          <ErrorBoundary fallbackTitle="Practice detail failed to render">
            <div className="flex-1 h-full overflow-hidden">
              <PracticeDetail wsPractices={wsPractices} />
            </div>
          </ErrorBoundary>
        } />

        <Route path="/astrology" element={
          <ErrorBoundary fallbackTitle="Cosmic Clock failed to render">
            <div className="flex-1 h-full overflow-hidden">
              <AstrologyPanel />
            </div>
          </ErrorBoundary>
        } />

        <Route path="/outlook" element={
          <ErrorBoundary fallbackTitle="Outlook failed to render">
            <div className="flex-1 h-full overflow-hidden">
              <OutlookDashboard />
            </div>
          </ErrorBoundary>
        } />

        <Route path="/operations" element={
          <ErrorBoundary fallbackTitle="Operations failed to render">
            <OperationsPage />
          </ErrorBoundary>
        } />
        <Route path="/operations/:tab" element={
          <ErrorBoundary fallbackTitle="Operations failed to render">
            <OperationsPage />
          </ErrorBoundary>
        } />

        <Route path="/grimoire" element={
          <ErrorBoundary fallbackTitle="Grimoire failed to render">
            <div className="flex-1 h-full overflow-hidden">
              <GrimoirePanel />
            </div>
          </ErrorBoundary>
        } />

        <Route path="/settings" element={
          <ErrorBoundary fallbackTitle="Settings failed to render">
            <SettingsPage />
          </ErrorBoundary>
        } />
        <Route path="/settings/:tab" element={
          <ErrorBoundary fallbackTitle="Settings failed to render">
            <SettingsPage />
          </ErrorBoundary>
        } />

        {/* ==================== LEGACY ROUTE REDIRECTS ==================== */}
        {/* Old flat routes keep working via <Navigate> so bookmarks and
            internal links don't break. See lib/routes.ts header comment
            and docs/specs/2026-06-20-ui-rework-design.md. */}
        <Route path="/sanctuary" element={<Navigate to="/practice/sanctuary" replace />} />
        <Route path="/buddhas" element={<Navigate to="/practice/buddhas" replace />} />
        <Route path="/meditation" element={<Navigate to="/practice/meditation" replace />} />
        <Route path="/visualizers" element={<Navigate to="/practice/visualizers" replace />} />
        <Route path="/broadcast" element={<Navigate to="/operations/broadcast" replace />} />
        <Route path="/tts" element={<Navigate to="/settings/tts" replace />} />

        <Route path="*" element={
          <div className="flex-1 flex items-center justify-center bg-gray-900">
            <Result
              status="404"
              title="404"
              subTitle="The path you requested does not match any known route."
              extra={
                <a
                  href={`/${DEFAULT_ROUTE}`}
                  className="inline-block px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
                >
                  Return to Command Center
                </a>
              }
            />
          </div>
        } />
      </Routes>
    </MainLayout>
  );
}

function App(): React.ReactElement {
  return (
    <ConfigProvider
      theme={{
        ...antdTheme,
        algorithm: theme.darkAlgorithm,
        token: {
          ...antdTheme.token,
          colorPrimary: COLORS.primary, // vajra-purple (--primary in globals.css)
          colorInfo: COLORS.secondary, // vajra-cyan (--secondary in globals.css)
        },
        components: {
          ...(antdTheme.components ?? {}),
          Slider: {
            handleColor: COLORS.primary,
            trackBg: COLORS.primary,
            trackHoverBg: COLORS.primary,
          },
          Switch: {
            colorPrimary: COLORS.primary,
            colorPrimaryHover: COLORS.primary,
          },
          Tabs: {
            inkBarColor: COLORS.primary,
            itemActiveColor: COLORS.primary,
            itemHoverColor: COLORS.primary,
            itemSelectedColor: COLORS.primary,
          },
          Progress: {
            defaultColor: COLORS.primary,
          },
        },
      }}
    >
      <ErrorBoundary fallbackTitle="Application failed to render">
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </ErrorBoundary>
    </ConfigProvider>
  );
}

export default App;
