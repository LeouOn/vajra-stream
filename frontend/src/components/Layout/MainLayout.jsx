import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Compass,
  Clock,
  FileText,
  Waves,
  Headphones,
  BookOpen,
  Volume2,
  Video,
  LayoutDashboard,
  PlayCircle,
  PauseCircle,
} from 'lucide-react';
import { ToastContainer } from '../UI/Toast';
import VisualizationSelector from '../UI/VisualizationSelector';
import { audioFeedback } from '../../utils/audioFeedback';
import { COLORS } from '../../lib/colors';

// Ant Design
import { Layout, Menu, Button, Space, Badge } from 'antd';

const { Header, Content, Footer } = Layout;

export default function MainLayout({
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
  visualizationType,
  handleVisualizationChange
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = location.pathname.split('/')[1] || 'command-center';

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 'b':
            e.preventDefault();
            navigate(activeTab === 'command-center' ? '/visualizers' : '/command-center');
            break;
          case 'd':
            e.preventDefault();
            handleVisualizationChange('trends');
            navigate('/visualizers');
            break;
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, navigate, handleVisualizationChange]);

  const handleMenuClick = (e) => {
    audioFeedback.playTick();
    navigate(`/${e.key}`);
  };

  const menuItems = [
    { key: 'command-center', icon: <LayoutDashboard size={16} />, label: 'Command Center' },
    { key: 'operations', icon: <Compass size={16} />, label: 'Operations' },
    { key: 'astrology', icon: <Clock size={16} />, label: 'Cosmic Clock' },
    { key: 'outlook', icon: <FileText size={16} />, label: 'Outlook' },
    { key: 'broadcast', icon: <Waves size={16} />, label: 'Broadcast' },
    { key: 'meditation', icon: <Headphones size={16} />, label: 'Meditate' },
    { key: 'visualizers', icon: <Video size={16} />, label: 'Visualizer' },
    { key: 'grimoire', icon: <BookOpen size={16} />, label: 'Grimoire' },
    { key: 'tts', icon: <Volume2 size={16} />, label: 'TTS' },
  ];

  return (
    <Layout style={{ minHeight: '100vh', background: 'transparent' }}>
      <ToastContainer />
      
      <Header style={{ 
        display: 'flex', 
        alignItems: 'center', 
        padding: '0 20px', 
        background: '#141414', 
        borderBottom: '1px solid #303030' 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', marginRight: '24px' }}>
          <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', color: COLORS.secondary }}>
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

        <Space style={{ marginLeft: 'auto' }}>
          {activeTab === 'visualizers' && (
            <VisualizationSelector
              currentType={visualizationType}
              onChange={handleVisualizationChange}
            />
          )}
        </Space>
      </Header>

      <Content style={{ position: 'relative', display: 'flex', flexDirection: 'column' }}>
        {children}
      </Content>

      <Footer style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: '10px 20px', 
        background: '#141414', 
        borderTop: '1px solid #303030',
        fontSize: '12px'
      }}>
        <div>
          <span style={{ color: COLORS.primary, fontWeight: 'bold', marginRight: '16px' }}>
            Vajra.Stream - Sacred Technology Platform
          </span>
          {mopsData && (
            <span style={{ color: COLORS.secondary, fontFamily: 'monospace' }}>
              MOPS: Scalar {(mopsData.scalar_pulses?.["1s"] / 1000000 || 0).toFixed(2)}M/s | 
              Mantra {Math.round(mopsData.mantras?.["10s"] || 0)}/s | 
              Crystals {Math.round(mopsData.crystals?.["10s"] || 0)}/s | 
              Divination {mopsData.divination?.["60s"] || 0}/s
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
}
