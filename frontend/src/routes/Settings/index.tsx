import React from 'react';
import ProviderSettings from '../../components/Settings/ProviderSettings';
import TTSSettingsPanel from '../../components/UI/TTSSettingsPanel';
import VideoSettingsPanel from '../../components/Settings/VideoSettingsPanel';

export default function SettingsPage(): React.ReactElement {
  return (
    <div className="flex-1 h-full overflow-y-auto p-6 space-y-6">
      <ProviderSettings />
      <TTSSettingsPanel />
      <VideoSettingsPanel />
    </div>
  );
}
