import React, { useState, useEffect } from 'react';
import { Compass, Calendar, MapPin, Clock, FileText, Tag, Save, X } from 'lucide-react';
import { Card, Input, Button, Space, Row, Col, Checkbox } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';

export default function NatalCalculator({ 
  onSubmit, 
  loading, 
  loadingStatus,
  editingChart, 
  onCancelEdit 
}) {
  const [name, setName] = useState('');
  const [birthDate, setBirthDate] = useState(() => {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  });
  const [city, setCity] = useState('San Francisco');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [notes, setNotes] = useState('');
  const [saveToDb, setSaveToDb] = useState(true);

  // If in edit mode, populate the fields
  useEffect(() => {
    if (editingChart) {
      setName(editingChart.name || '');
      // Format birth_time_iso to match datetime-local format (YYYY-MM-DDTHH:MM)
      if (editingChart.birth_time_iso) {
        const timePart = editingChart.birth_time_iso.substring(0, 16);
        setBirthDate(timePart);
      }
      setCity(editingChart.city || '');
      setDescription(editingChart.description || '');
      setTags(editingChart.tags || '');
      setNotes(editingChart.notes || '');
      setSaveToDb(true); // Must save to DB for updates
    } else {
      // Clear fields for new charts (except date defaults and city default)
      setName('');
      setCity('San Francisco');
      setDescription('');
      setTags('');
      setNotes('');
    }
  }, [editingChart]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!name || !birthDate || !city) {
      audioFeedback.playError();
      return;
    }

    audioFeedback.playTelemetry();
    onSubmit({
      name,
      birth_time_iso: birthDate,
      city,
      description,
      tags,
      notes,
      saveToDb: editingChart ? true : saveToDb
    });
  };

  const handleCityPreset = (presetCity) => {
    setCity(presetCity);
    audioFeedback.playTick();
  };

  return (
    <Card
      title={
        <span className="text-purple-400 font-mono text-xs tracking-wider uppercase flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4 text-purple-400" />
            {editingChart ? `Edit Profile: ${editingChart.name}` : 'NATAL CHART CALCULATOR'}
          </span>
          {editingChart && (
            <Button size="small" type="text" danger onClick={onCancelEdit} icon={<X className="w-3.5 h-3.5" />} />
          )}
        </span>
      }
      className="bg-gray-900/80 border-purple-500/20"
      styles={{ body: { padding: '16px' } }}
    >
      <form onSubmit={handleSubmit}>
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          <div>
            <label className="text-gray-400 text-xs font-semibold block mb-1">
              Subject Name
            </label>
            <Input
              type="text"
              placeholder="e.g. Gautama Buddha"
              value={name}
              onChange={(e) => { setName(e.target.value); audioFeedback.playType(); }}
              className="bg-gray-800 border-gray-700 text-white placeholder-gray-500"
            />
          </div>

          <Row gutter={8}>
            <Col span={12}>
              <label className="text-gray-400 text-xs font-semibold block mb-1">
                <Clock className="w-3 h-3 text-cyan-400 inline mr-1" />
                Birth Date & Time (Local)
              </label>
              <Input
                type="datetime-local"
                value={birthDate}
                onChange={(e) => { setBirthDate(e.target.value); audioFeedback.playType(); }}
                className="bg-gray-800 border-gray-700 text-white"
              />
            </Col>
            <Col span={12}>
              <label className="text-gray-400 text-xs font-semibold block mb-1">
                <MapPin className="w-3 h-3 text-rose-400 inline mr-1" />
                Birth City
              </label>
              <Input
                type="text"
                placeholder="e.g. Lumbini"
                value={city}
                onChange={(e) => { setCity(e.target.value); audioFeedback.playType(); }}
                className="bg-gray-800 border-gray-700 text-white placeholder-gray-500"
              />
            </Col>
          </Row>

          <div>
            <span className="text-[9px] text-gray-500 block uppercase font-bold mb-1">City Presets</span>
            <Space wrap size={4}>
              {['San Francisco', 'London', 'New Delhi', 'Beijing', 'Tokyo'].map((p) => (
                <Button
                  key={p}
                  size="small"
                  type="default"
                  ghost
                  onClick={() => handleCityPreset(p)}
                  style={{ fontSize: '9px', padding: '0 6px', height: '20px' }}
                >
                  {p}
                </Button>
              ))}
            </Space>
          </div>

          <div>
            <label className="text-gray-400 text-xs font-semibold block mb-1">
              Short Description / Event Type
            </label>
            <Input
              type="text"
              placeholder="e.g. Great Awakening Chart"
              value={description}
              onChange={(e) => { setDescription(e.target.value); audioFeedback.playType(); }}
              className="bg-gray-800 border-gray-700 text-white placeholder-gray-500"
            />
          </div>

          <Row gutter={8}>
            <Col span={12}>
              <label className="text-gray-400 text-xs font-semibold block mb-1">
                <Tag className="w-3 h-3 text-purple-400 inline mr-1" />
                Categorization Tags
              </label>
              <Input
                type="text"
                placeholder="Client, Family, Event (comma separated)"
                value={tags}
                onChange={(e) => { setTags(e.target.value); audioFeedback.playType(); }}
                className="bg-gray-800 border-gray-700 text-white placeholder-gray-500"
              />
            </Col>
            <Col span={12}>
              <label className="text-gray-400 text-xs font-semibold block mb-1">
                <FileText className="w-3 h-3 text-amber-400 inline mr-1" />
                Notes / Birth Source
              </label>
              <Input
                type="text"
                placeholder="Time from hospital record"
                value={notes}
                onChange={(e) => { setNotes(e.target.value); audioFeedback.playType(); }}
                className="bg-gray-800 border-gray-700 text-white placeholder-gray-500"
              />
            </Col>
          </Row>

          {!editingChart && (
            <div className="py-1">
              <Checkbox 
                checked={saveToDb} 
                onChange={(e) => { audioFeedback.playTick(); setSaveToDb(e.target.checked); }}
                className="text-gray-400 text-xs select-none"
              >
                Save profile to SQLite database
              </Checkbox>
            </div>
          )}

          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            block
            icon={editingChart ? <Save className="w-4 h-4" /> : <Compass className="w-4 h-4" />}
            style={{ 
              background: editingChart 
                ? 'linear-gradient(135deg, #059669, #10b981)' 
                : 'linear-gradient(135deg, #7c3aed, #4f46e5)', 
              border: 'none',
              marginTop: '4px'
            }}
          >
            {loading && loadingStatus ? loadingStatus : (editingChart ? 'Update Saved Profile' : 'Calculate & Display Chart')}
          </Button>
        </Space>
      </form>
    </Card>
  );
}
