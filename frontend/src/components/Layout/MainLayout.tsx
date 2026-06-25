/**
 * MainLayout — top-level layout for all /visualizers, /operations, etc.
 * routes. Renders the header (brand + status badge + nav menu),
 * the children content area, and the footer (MOPS readout +
 * play/pause control + volume + mode).
 *
 * The nav menu reads from lib/routes.ts (ROUTES registry) so the
 * menu and the <Route> declarations in App.jsx share one source
 * of truth. Adding a new route means adding one entry to ROUTES
 * and one component mapping in App.jsx.
 */
import React, { useEffect, KeyboardEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { PlayCircle, PauseCircle } from 'lucide-react';
import { ToastContainer } from '../UI/Toast';
import { audioFeedback } from '../../utils/audioFeedback';
import { COLORS } from '../../lib/colors';
import { ROUTES, DEFAULT_ROUTE } from '../../lib/routes';

// Ant Design
import { Layout, Menu, Button, Space, Badge } from 'antd';

const { Header, Content, Footer } = Layout;

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

interface Props {
  children: React.ReactNode;
  isConnected: boolean;
  isPlaying: boolean;
  frequency: number;
  volume: number;
  prayerBowlMode: boolean;
  generateAudio: () => Promise<void>;
  playAudio: () => Promise<void>;
  stopAudio: () => void;
  mopsData: MopsData | null;
}

const MainLayoutComponent: React.FC<Props> = ({
  children,
  isConnected,
  isPlaying,
  frequency,
  volume,
  prayerBowlMode,
  generateAudio,
  playAudio,
  stopAudio,
  mopsData,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = location.pathname.split('/')[1] || DEFAULT_ROUTE;

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 'b':
            e.preventDefault();
            navigate(activeTab === DEFAULT_ROUTE ? '/practice' : `/${DEFAULT_ROUTE}`);
            break;
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, navigate]);

  const handleMenuClick = (e: { key: string }) => {
    audioFeedback.playTick();
    navigate(`/${e.key}`);
  };

  const menuItems = ROUTES.map(({ key, label, icon: Icon }) => ({
    key,
    label,
    icon: <Icon size={16} />,
  }));

  return (
    <Layout style={{ minHeight: '100vh', background: 'transparent' }}>
      <ToastContainer />

      <Header style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0 20px',
        background: 'rgba(20, 10, 30, 0.7)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(139, 92, 246, 0.2)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', marginRight: '24px' }}>
          <h1 style={{ margin: 0, fontSize: '22px', fontWeight: '700', color: COLORS.secondary, textShadow: '0 0 12px rgba(6, 182, 212, 0.4)', letterSpacing: '0.5px' }}>
            🔮 Vajra.Stream
          </h1>
          <Badge status={isConnected ? 'success' : 'error'} text={isConnected ? 'LIVE' : 'OFFLINE'} style={{ marginLeft: 16 }} />
        </div>

        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[activeTab]}
          onClick={handleMenuClick}
          items={menuItems}
          style={{ flex: 1, minWidth: 0, background: 'transparent', borderBottom: 'none' }}
        />
      </Header>

      <Content style={{ position: 'relative', display: 'flex', flexDirection: 'column' }}>
        {children}
      </Content>

      <Footer style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '10px 20px',
        background: 'rgba(20, 10, 30, 0.7)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderTop: '1px solid rgba(139, 92, 246, 0.2)',
        fontSize: '12px'
      }}>
        <div>
          <span style={{ color: COLORS.primary, fontWeight: 'bold', marginRight: '16px' }}>
            Vajra.Stream - Sacred Technology Platform
          </span>
          {mopsData && (
            <span style={{ color: COLORS.secondary, fontFamily: 'monospace' }}>
              MOPS: Scalar {(mopsData.scalar_pulses?.["1s"] / 1000000 || 0).toFixed(2)}M/s |
              Mantra {Math.round(mopsData.mantras?.["10s"] ?? 0)}/s |
              Crystals {Math.round(mopsData.crystals?.["10s"] ?? 0)}/s |
              Divination {mopsData.divination?.["60s"] ?? 0}/s
            </span>
          )}
        </div>
        <Space size="large">
          <Button
            type="text"
            icon={isPlaying ? <PauseCircle size={18} color={COLORS.primary} /> : <PlayCircle size={18} color={COLORS.secondary} />}
            onClick={async () => { if (!isPlaying) { await generateAudio(); await playAudio(); } else { stopAudio(); } }}
          >
            <span style={{ color: COLORS.secondary, fontWeight: 'bold', fontSize: '14px' }}>
              {frequency.toFixed(1)} Hz
            </span>
          </Button>
          <span>Volume: <strong>{Math.round(volume * 100)}%</strong></span>
          <span>Mode: <strong style={{ color: COLORS.primary }}>{prayerBowlMode ? 'Prayer Bowl' : 'Sine Wave'}</strong></span>
        </Space>
      </Footer>
    </Layout>
  );
};

// Memoize so the layout shell doesn't re-render on every store change.
// Without this, any audio-store update (isPlaying, frequency, volume) causes
// a full re-render of the nav menu + footer + children wrapper.
const MainLayout = React.memo(MainLayoutComponent);
export default MainLayout;
