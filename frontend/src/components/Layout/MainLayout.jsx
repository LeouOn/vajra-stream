import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ToastContainer } from '../UI/Toast';
import VisualizationSelector from '../UI/VisualizationSelector';
import { audioFeedback } from '../../utils/audioFeedback';

// Ant Design
import { Layout, Menu, Button, Space, Badge, Dropdown } from 'antd';
import {
  CodeOutlined,
  CompassOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  AudioOutlined,
  CustomerServiceOutlined,
  BookOutlined,
  SoundOutlined,
  VideoCameraOutlined,
  DesktopOutlined,
  SettingOutlined,
  PlayCircleFilled,
  PauseCircleFilled
} from '@ant-design/icons';

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
    { key: 'command-center', icon: <DesktopOutlined />, label: 'Command Center' },
    { key: 'operations', icon: <CompassOutlined />, label: 'Operations' },
    { key: 'astrology', icon: <ClockCircleOutlined />, label: 'Cosmic Clock' },
    { key: 'outlook', icon: <FileTextOutlined />, label: 'Outlook' },
    { key: 'broadcast', icon: <AudioOutlined />, label: 'Broadcast' },
    { key: 'meditation', icon: <CustomerServiceOutlined />, label: 'Meditate' },
    { key: 'visualizers', icon: <VideoCameraOutlined />, label: 'Visualizer' },
    { key: 'grimoire', icon: <BookOutlined />, label: 'Grimoire' },
    { key: 'tts', icon: <SoundOutlined />, label: 'TTS' },
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
          <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', color: '#06b6d4' }}>
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
          <span style={{ color: '#8b5cf6', fontWeight: 'bold', marginRight: '16px' }}>
            Vajra.Stream - Sacred Technology Platform
          </span>
          {mopsData && (
            <span style={{ color: '#06b6d4', fontFamily: 'monospace' }}>
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
            icon={isPlaying ? <PauseCircleFilled style={{color:'#8b5cf6'}} /> : <PlayCircleFilled style={{color:'#06b6d4'}} />} 
            onClick={async () => { if (!isPlaying) { await generateAudio(); await playAudio(); } else { stopAudio(); } }}
          >
            <span style={{ color: '#06b6d4', fontWeight: 'bold', fontSize: '14px' }}>
              {frequency.toFixed(1)} Hz
            </span>
          </Button>
          <span>Volume: <strong>{Math.round(volume * 100)}%</strong></span>
          <span>Mode: <strong style={{ color: '#8b5cf6' }}>{prayerBowlMode ? 'Prayer Bowl' : 'Sine Wave'}</strong></span>
          <Badge status={isConnected ? 'success' : 'error'} text={isConnected ? 'Connected' : 'Offline'} />
        </Space>
      </Footer>
    </Layout>
  );
}
