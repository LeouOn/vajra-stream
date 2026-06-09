import React, { useState } from 'react';
import { 
  User, Trash2, Edit, Sparkles, Filter, Tag, Download, Upload, Plus, AlertTriangle, Check, X
} from 'lucide-react';
import { Card, Input, Button, Tag as AntTag, Space, Tooltip, Popconfirm, Select } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';

export default function SavedChartsDrawer({ 
  charts, 
  onLoadNatal, 
  onSelectTransit,
  onSetSubjectA,
  onSetSubjectB,
  onEdit, 
  onDelete, 
  onExport, 
  onImport,
  subjectA,
  subjectB,
  activeChartId
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTag, setSelectedTag] = useState('All');

  // Extract all unique tags
  const allTags = ['All', ...new Set(charts.flatMap(c => c.tags ? c.tags.split(',').map(t => t.trim()) : []))];

  const filteredCharts = charts.filter(chart => {
    const matchesSearch = chart.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          chart.city.toLowerCase().includes(searchTerm.toLowerCase());
    const tagsList = chart.tags ? chart.tags.split(',').map(t => t.trim()) : [];
    const matchesTag = selectedTag === 'All' || tagsList.includes(selectedTag);
    return matchesSearch && matchesTag;
  });

  const handleImportChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const data = JSON.parse(event.target.result);
          onImport(data);
        } catch (err) {
          console.error("Invalid JSON file for import", err);
          audioFeedback.playError();
        }
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-950/40 rounded-xl border border-purple-500/10 overflow-hidden">
      {/* Header and Toolbar */}
      <div className="p-4 border-b border-purple-500/10 bg-gray-900/40 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-bold text-purple-300 uppercase tracking-wider">Saved Charts DB</h3>
          </div>
          <div className="flex gap-2">
            <Tooltip title="Export Backup">
              <Button 
                size="small" 
                type="default" 
                ghost 
                icon={<Download className="w-3.5 h-3.5" />} 
                onClick={() => { audioFeedback.playClick(); onExport(); }}
              />
            </Tooltip>
            <Tooltip title="Import Backup">
              <div className="relative inline-block">
                <input 
                  type="file" 
                  accept=".json" 
                  onChange={handleImportChange} 
                  className="hidden" 
                  id="import-file-input" 
                />
                <Button 
                  size="small" 
                  type="default" 
                  ghost 
                  icon={<Upload className="w-3.5 h-3.5" />} 
                  onClick={() => { audioFeedback.playClick(); document.getElementById('import-file-input').click(); }}
                />
              </div>
            </Tooltip>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-2">
          <Input 
            placeholder="Search profiles..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-gray-900 border-gray-800 text-white placeholder-gray-500 text-xs"
            size="small"
          />
          <Select
            value={selectedTag}
            onChange={setSelectedTag}
            size="small"
            className="min-w-[90px]"
            dropdownClassName="bg-gray-950 border-gray-800 text-white"
            options={allTags.map(tag => ({ value: tag, label: tag }))}
          />
        </div>
      </div>

      {/* Charts list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 max-h-[500px]">
        {filteredCharts.length > 0 ? (
          filteredCharts.map((chart) => {
            const tagsList = chart.tags ? chart.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
            const isActive = activeChartId === chart.id;
            const isA = subjectA?.id === chart.id;
            const isB = subjectB?.id === chart.id;

            return (
              <Card 
                key={chart.id} 
                size="small" 
                className={`bg-gray-900/60 border transition-all ${
                  isActive ? 'border-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.15)] bg-purple-950/10' : 'border-white/5 hover:border-white/10'
                }`}
                styles={{ body: { padding: '10px' } }}
              >
                <div className="flex flex-col space-y-2">
                  <div className="flex justify-between items-start">
                    <div className="min-w-0">
                      <span className="font-semibold text-white text-xs block truncate">{chart.name}</span>
                      <span className="text-[10px] text-gray-400 block truncate">{chart.city}</span>
                      <span className="text-[9px] text-gray-500 font-mono block">
                        {new Date(chart.birth_time_iso).toLocaleDateString()} {new Date(chart.birth_time_iso).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </span>
                    </div>
                    <div className="flex gap-1.5">
                      <button 
                        onClick={() => { audioFeedback.playTick(); onEdit(chart); }}
                        className="p-1 rounded bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white"
                      >
                        <Edit className="w-3 h-3" />
                      </button>
                      <Popconfirm
                        title="Delete profile?"
                        onConfirm={() => { audioFeedback.playClick(); onDelete(chart.id); }}
                        okText="Yes"
                        cancelText="No"
                        okButtonProps={{ danger: true }}
                      >
                        <button className="p-1 rounded bg-red-950/20 hover:bg-red-950/40 text-red-400">
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </Popconfirm>
                    </div>
                  </div>

                  {/* Description / Notes preview */}
                  {chart.description && (
                    <p className="text-[10px] text-gray-500 italic truncate mb-0">{chart.description}</p>
                  )}

                  {/* Tags list */}
                  {tagsList.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {tagsList.map(tag => (
                        <AntTag key={tag} color="purple" style={{ fontSize: '8px', padding: '0 4px', margin: 0 }}>
                          {tag}
                        </AntTag>
                      ))}
                    </div>
                  )}

                  {/* Actions Bar */}
                  <div className="grid grid-cols-4 gap-1 pt-1.5 border-t border-white/5">
                    <Button 
                      size="small" 
                      type={isActive ? "primary" : "default"}
                      ghost={!isActive}
                      onClick={() => { audioFeedback.playSuccess(); onLoadNatal(chart); }}
                      style={{ fontSize: '9px', padding: '0 4px', height: '20px' }}
                    >
                      Natal
                    </Button>
                    <Button 
                      size="small" 
                      type="default"
                      ghost
                      onClick={() => { audioFeedback.playSuccess(); onSelectTransit(chart); }}
                      style={{ fontSize: '9px', padding: '0 4px', height: '20px' }}
                    >
                      Transits
                    </Button>
                    <Button 
                      size="small" 
                      type={isA ? "primary" : "default"}
                      ghost={!isA}
                      onClick={() => { audioFeedback.playTick(); onSetSubjectA(chart); }}
                      style={{ fontSize: '9px', padding: '0 4px', height: '20px', borderColor: isA ? '#06b6d4' : undefined, color: isA ? '#06b6d4' : undefined }}
                    >
                      Syn. A
                    </Button>
                    <Button 
                      size="small" 
                      type={isB ? "primary" : "default"}
                      ghost={!isB}
                      onClick={() => { audioFeedback.playTick(); onSetSubjectB(chart); }}
                      style={{ fontSize: '9px', padding: '0 4px', height: '20px', borderColor: isB ? '#e0f2fe' : undefined, color: isB ? '#e0f2fe' : undefined }}
                    >
                      Syn. B
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })
        ) : (
          <div className="text-center italic text-gray-600 text-xs py-8">
            No saved charts found
          </div>
        )}
      </div>
    </div>
  );
}
