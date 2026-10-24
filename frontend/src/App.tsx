import React, { Suspense, lazy, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useWebSocketStable as useWebSocket } from './hooks/useWebSocketStable';
import { useAudioStore } from './stores/audioStore';

// Ant Design
import { ConfigProvider, theme, Result } from 'antd';

import MainLayout from './components/Layout/MainLayout';
import CommandCenter from './components/UI/CommandCenter';
import ErrorBoundary from './components/UI/ErrorBoundary';
import { audioFeedback } from './utils/audioFeedback';
import { COLORS } from './lib/colors';
import { antdTheme } from './theme/antdTheme';
import { DEFAULT_ROUTE } from './lib/routes';

// Every view but the Command Center (the landing route) loads on first visit,
// so the initial bundle stays under Vite's chunk warning.
const AstrologyPanel = lazy(() => import('./components/UI/AstrologyPanel'));
const OutlookDashboard = lazy(() => import('./components/UI/OutlookDashboard'));
const GrimoirePanel = lazy(() => import('./components/UI/GrimoirePanel'));
const PracticePage = lazy(() => import('./routes/Practice'));
const OperationsPage = lazy(() => import('./routes/Operations'));
const SettingsPage = lazy(() => import('./routes/Settings'));
const WorkingsPage = lazy(() => import('./routes/Workings'));
const PracticeSelector = lazy(() => import('./components/UI/PracticeSelector'));
const PracticeDetail = lazy(() => import('./components/UI/PracticeDetail'));

function AppContent(): React.ReactElement {
  const location = useLocation();
  const activeTab = location.pathname.split('/')[1] || DEFAULT_ROUTE;

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
    >
      <Suspense fallback={<div className="flex-1 h-full flex items-center justify-center text-xs font-mono text-purple-300/70">Loading…</div>}>
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

        <Route path="/workings" element={
          <ErrorBoundary fallbackTitle="Workings failed to render">
            <WorkingsPage />
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
      </Suspense>
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
