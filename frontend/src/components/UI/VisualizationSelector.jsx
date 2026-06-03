/**
 * Visualization Selector — dropdown in the header that picks the
 * active visualization mode on the /visualizers route.
 *
 * Restored to replace the broken import in MainLayout (the original
 * file was missing from the repo, so the dropdown never rendered).
 *
 * @param {{ currentType: string, onChange: (t: string) => void }} props
 */
import React from 'react';
import { Select, Tag } from 'antd';
import {
  Sparkles, Compass, Diamond, Circle, BarChart3, Activity, Waves,
  TrendingUp, Palette, Sun, Globe,
} from 'lucide-react';

const OPTIONS = [
  { value: 'sacred-geometry', label: 'Sacred Geometry', icon: Sparkles, color: 'purple' },
  { value: 'radionics', label: 'Radionics', icon: Compass, color: 'cyan' },
  { value: 'crystal-grid', label: 'Crystal Grid', icon: Diamond, color: 'cyan' },
  { value: 'sacred-mandala', label: 'Sacred Mandala', icon: Circle, color: 'magenta' },
  { value: 'audio-spectrum', label: 'Audio Spectrum', icon: BarChart3, color: 'gold' },
  { value: 'live-wave', label: 'Live Wave', icon: Activity, color: 'lime' },
  { value: 'scalar-wave', label: 'Scalar Wave', icon: Waves, color: 'cyan' },
  { value: 'trends', label: 'Trends', icon: TrendingUp, color: 'purple' },
  { value: 'rothko', label: 'Rothko', icon: Palette, color: 'orange' },
  { value: 'chakra-body', label: 'Chakra Body', icon: Sun, color: 'volcano' },
  { value: 'chakra-trend', label: 'Chakra Trend', icon: Activity, color: 'volcano' },
  { value: 'globe', label: 'Globe', icon: Globe, color: 'blue' },
  { value: 'waterfall', label: 'Frequency Waterfall', icon: BarChart3, color: 'geekblue' },
];

export default function VisualizationSelector({ currentType, onChange }) {
  const selected = OPTIONS.find((o) => o.value === currentType) || OPTIONS[0];
  const SelectedIcon = selected.icon;

  return (
    <Select
      value={currentType}
      onChange={onChange}
      style={{ minWidth: 200 }}
      size="middle"
      popupMatchSelectWidth={240}
      options={OPTIONS.map((o) => {
        const Icon = o.icon;
        return {
          value: o.value,
          label: (
            <span className="flex items-center gap-2">
              <Icon className="w-3.5 h-3.5" />
              {o.label}
            </span>
          ),
        };
      })}
      optionLabelProp="label"
      labelRender={() => (
        <span className="flex items-center gap-2">
          <SelectedIcon className="w-3.5 h-3.5" />
          <span>{selected.label}</span>
          <Tag color={selected.color} className="ml-1 text-[9px] font-mono leading-none border-0">
            viz
          </Tag>
        </span>
      )}
    />
  );
}
