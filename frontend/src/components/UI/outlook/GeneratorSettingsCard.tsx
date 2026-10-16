/**
 * GeneratorSettingsCard — the Quick Generate "Transmission Settings" form:
 * realm and coordinates, epoch, global intentions, genre, oracle sources,
 * languages, model, cast (characters / populations), dialogue, excluded
 * forces, aspiration, difficulty, epic stages and the generate button.
 *
 * Presentational: all state lives in the parent's useGeneratorForm /
 * useOutlookModels hooks.
 *
 * @component
 */
import React, { useMemo } from 'react';
import {
  Sparkles, Globe, Clock, Shield, Users, RefreshCw, Shuffle, Dices,
} from 'lucide-react';
import {
  Card, Input, InputNumber, Button, Select, Switch, Tag, Row, Col, Space,
  Collapse, Typography, Divider, Badge, Tooltip,
} from 'antd';
import {
  DIFFICULTY_OPTIONS, GENRE_OPTIONS, GLOBAL_INTENTIONS, LANGUAGE_OPTIONS,
} from './outlookConstants';
import type { Character, Population, Realm } from './outlookShared';
import type { GeneratorForm } from './useGeneratorForm';
import type { ModelSelectOption, OutlookModelPicker } from './useOutlookModels';

const { Text } = Typography;

interface GeneratorSettingsCardProps {
  form: GeneratorForm;
  models: OutlookModelPicker;
  realms: Realm[];
  characters: Character[];
  populations: Population[];
  bgActive: boolean;
  loading: boolean;
  onGenerate: () => void;
}

export default function GeneratorSettingsCard({
  form, models, realms, characters, populations, bgActive, loading, onGenerate,
}: GeneratorSettingsCardProps) {
  const {
    lat, setLat, lon, setLon, genre, setGenre, selectedLangs, setSelectedLangs,
    isEpic, setIsEpic, stages, setStages, date, setDate,
    selectedRealmId, setSelectedRealmId, selectedCharIds, setSelectedCharIds,
    selectedPopIds, setSelectedPopIds, includeDialogue, setIncludeDialogue,
    customContext, setCustomContext, difficulty, setDifficulty,
    excludedForcesText, setExcludedForcesText,
    includeAstrology, setIncludeAstrology, includeTarot, setIncludeTarot,
    includeIching, setIncludeIching, randomizeRealm, setRandomizeRealm,
    randomizeCharacters, setRandomizeCharacters,
  } = form;
  const { selectedModel, setSelectedModel, randomModel, setRandomModel, modelOptions } = models;

  const realmOptions = useMemo(() =>
    realms.map(r => ({ value: r.id, label: `${r.name} (${r.is_metaphysical ? 'Meta' : 'Earth'})` }))
  , [realms]);

  const coordsLocked = randomizeRealm || (!!selectedRealmId && !(realms.find(r => r.id === selectedRealmId)?.is_metaphysical));

  return (
    <Card
      title={<Text strong className="font-mono text-xs uppercase">Transmission Settings</Text>}
      extra={bgActive && <Badge status="processing" color="cyan" text="BG Active" />}
      size="small"
    >
      <Space orientation="vertical" className="w-full" size="middle">

        {/* Active selections summary */}
        {(selectedRealmId || selectedCharIds.length > 0 || selectedPopIds.length > 0) && (
          <Space wrap size={[4, 4]}>
            {selectedRealmId && (() => {
              const r = realms.find(x => x.id === selectedRealmId);
              return <Tag closable color="cyan" onClose={() => setSelectedRealmId('')}>📍 {r?.name || 'Realm'}</Tag>;
            })()}
            {selectedCharIds.length > 0 && (
              <Tag closable color="purple" onClose={() => setSelectedCharIds([])}>👤 {selectedCharIds.length} characters</Tag>
            )}
            {selectedPopIds.length > 0 && (
              <Tag closable color="blue" onClose={() => setSelectedPopIds([])}>🫂 {selectedPopIds.length} populations</Tag>
            )}
          </Space>
        )}

        {/* Realm */}
        <div>
          <Text strong style={{ fontSize: 12 }}><Globe className="w-3 h-3 inline mr-1" /> Realm / Setting</Text>
          <Row gutter={8} align="middle" style={{ marginTop: 4 }}>
            <Col flex="auto">
              <Select
                value={selectedRealmId || undefined}
                onChange={setSelectedRealmId}
                disabled={randomizeRealm}
                placeholder="Dynamic Map Coordinates"
                allowClear
                size="small"
                className="w-full"
                options={realmOptions}
              />
            </Col>
            <Col>
              <Tooltip title="Randomize realm"><Switch size="small" checked={randomizeRealm} onChange={setRandomizeRealm} /></Tooltip>
            </Col>
          </Row>
        </div>

        {/* Coordinates */}
        <Row gutter={8}>
          <Col span={12}>
            <Text style={{ fontSize: 11 }}>Latitude</Text>
            <InputNumber size="small" className="w-full" value={lat} onChange={setLat} step={0.0001}
              disabled={coordsLocked} />
          </Col>
          <Col span={12}>
            <Text style={{ fontSize: 11 }}>Longitude</Text>
            <InputNumber size="small" className="w-full" value={lon} onChange={setLon} step={0.0001}
              disabled={coordsLocked} />
          </Col>
        </Row>

        {/* Date */}
        <div>
          <Text strong style={{ fontSize: 12 }}><Clock className="w-3 h-3 inline mr-1" /> Cosmic Epoch</Text>
          <Input size="small" type="datetime-local" value={date} onChange={e => setDate(e.target.value)} style={{ marginTop: 4 }} />
        </div>

        {/* Global Intentions Presets (saved from deleted RadionicsNarrative) */}
        <div>
          <Text strong style={{ fontSize: 12 }}><Globe className="w-3 h-3 inline mr-1" /> Global Intentions</Text>
          <div className="grid grid-cols-2 gap-1.5" style={{ marginTop: 4 }}>
            {GLOBAL_INTENTIONS.map((preset) => {
              const isActive = customContext.toLowerCase().includes(preset.id);
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => setCustomContext(preset.id)}
                  className={`p-1.5 rounded text-left text-[10px] transition-colors border ${
                    isActive
                      ? 'bg-cyan-950/60 border-cyan-500/40 text-cyan-200'
                      : 'bg-gray-800/50 border-white/5 text-gray-400 hover:border-white/15 hover:text-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-1">
                    <span>{preset.icon}</span>
                    <span className="font-medium truncate">{preset.label}</span>
                  </div>
                  <div className="text-[8px] opacity-70 mt-0.5 font-mono">
                    {preset.planet} · {preset.freq}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Genre */}
        <div>
          <Text strong style={{ fontSize: 12 }}>Blessing Genre</Text>
          <Select
            value={genre}
            onChange={setGenre}
            size="small"
            className="w-full"
            style={{ marginTop: 4 }}
            options={GENRE_OPTIONS}
          />
        </div>

        <Divider style={{ margin: '4px 0' }} />

        {/* Oracle Sources */}
        <div>
          <Text strong style={{ fontSize: 12 }}>Oracle Sources</Text>
          <Space orientation="vertical" size={4} style={{ marginTop: 4 }}>
            <Space><Switch size="small" checked={includeAstrology} onChange={setIncludeAstrology} /><Text style={{ fontSize: 11 }}>🌟 Astrology</Text></Space>
            <Space><Switch size="small" checked={includeTarot} onChange={setIncludeTarot} /><Text style={{ fontSize: 11 }}>🃏 Tarot</Text></Space>
            <Space><Switch size="small" checked={includeIching} onChange={setIncludeIching} /><Text style={{ fontSize: 11 }}>☯️ I Ching</Text></Space>
          </Space>
        </div>

        {/* Languages */}
        <div>
          <Text strong style={{ fontSize: 12 }}>Weave Languages</Text>
          <Select
            mode="multiple"
            size="small"
            value={selectedLangs}
            onChange={setSelectedLangs}
            className="w-full"
            style={{ marginTop: 4 }}
            options={LANGUAGE_OPTIONS}
          />
        </div>

        {/* Model */}
        <div>
          <Row justify="space-between" align="middle">
            <Col><Text strong style={{ fontSize: 12 }}>LLM Model</Text></Col>
            <Col>
              <Tooltip title="Let the backend pick a random provider each run">
                <Space size={4}>
                  <Switch size="small" checked={randomModel} onChange={setRandomModel} />
                  <Text style={{ fontSize: 11 }}><Dices className="w-3 h-3 inline mr-1" />🎲 Random</Text>
                </Space>
              </Tooltip>
            </Col>
          </Row>
          <Select
            size="small"
            value={selectedModel || undefined}
            onChange={setSelectedModel}
            className="w-full"
            style={{ marginTop: 4 }}
            options={modelOptions}
            placeholder="Auto-detect"
            disabled={randomModel}
            showSearch
            optionFilterProp="label"
            filterSort={(a: ModelSelectOption, b: ModelSelectOption) => a.label.localeCompare(b.label)}
          />
          {randomModel && (
            <Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 2 }}>
              <Shuffle className="w-3 h-3 inline mr-1" />Provider rolled at generation time — selection disabled.
            </Text>
          )}
        </div>

        <Divider style={{ margin: '4px 0' }} />

        {/* Characters — Collapsible */}
        <Collapse ghost size="small" expandIconPlacement="end"
          items={[{
            key: 'chars', label: <Text strong style={{ fontSize: 12 }}><Shield className="w-3 h-3 inline mr-1" />Characters ({selectedCharIds.length})</Text>,
            extra: <Tooltip title="Random 2-3"><Switch size="small" checked={randomizeCharacters} onChange={setRandomizeCharacters} /></Tooltip>,
            children: (
              <div className="max-h-40 overflow-y-auto">
                <Space orientation="vertical" size={2} className="w-full">
                  {characters.map(c => (
                    <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
                      <Switch size="small" checked={selectedCharIds.includes(c.id)}
                        onChange={checked => setSelectedCharIds(prev => checked ? [...prev, c.id] : prev.filter(id => id !== c.id))}
                        disabled={randomizeCharacters} />
                      <Text style={{ fontSize: 11, flex: 1 }}>{c.name}</Text>
                      <Tag style={{ fontSize: 9 }}>{c.role}</Tag>
                    </div>
                  ))}
                </Space>
              </div>
            ),
          }]}
        />

        {/* Populations — Collapsible */}
        <Collapse ghost size="small" expandIconPlacement="end"
          items={[{
            key: 'pops', label: <Text strong style={{ fontSize: 12 }}><Users className="w-3 h-3 inline mr-1" />Populations ({selectedPopIds.length})</Text>,
            children: (
              <div className="max-h-32 overflow-y-auto">
                <Space orientation="vertical" size={2} className="w-full">
                  {populations.map(p => (
                    <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
                      <Switch size="small" checked={selectedPopIds.includes(p.id)}
                        onChange={checked => setSelectedPopIds(prev => checked ? [...prev, p.id] : prev.filter(id => id !== p.id))} />
                      <Text style={{ fontSize: 11 }}>{p.name}</Text>
                    </div>
                  ))}
                </Space>
              </div>
            ),
          }]}
        />

        <Divider style={{ margin: '4px 0' }} />

        {/* Dialogue */}
        <Row justify="space-between" align="middle">
          <Col><Text strong style={{ fontSize: 12 }}>Weave Dialogue</Text></Col>
          <Col><Switch size="small" checked={includeDialogue} onChange={setIncludeDialogue} disabled={selectedCharIds.length === 0} /></Col>
        </Row>

        {/* Excluded Forces */}
        <div>
          <Text style={{ fontSize: 11 }}>Exclude Forces</Text>
          <Input size="small" value={excludedForcesText} onChange={e => setExcludedForcesText(e.target.value)}
            placeholder="sickness, doubt, obstacles" style={{ marginTop: 4 }} />
        </div>

        {/* Custom Context */}
        <div>
          <Text style={{ fontSize: 11 }}>Custom Aspiration</Text>
          <Input.TextArea size="small" rows={2} value={customContext} onChange={e => setCustomContext(e.target.value)}
            placeholder="Weave in intentions of peaceful passing for all beings..." style={{ marginTop: 4 }} />
        </div>

        <Divider style={{ margin: '4px 0' }} />

        {/* Difficulty Level */}
        <div>
          <Text strong style={{ fontSize: 12 }}>Difficulty Level</Text>
          <div className="grid grid-cols-3 gap-1.5" style={{ marginTop: 4 }}>
            {DIFFICULTY_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setDifficulty(opt.id)}
                className={`p-1.5 rounded text-[10px] transition-colors border ${
                  difficulty === opt.id
                    ? 'bg-purple-950/60 border-purple-500/40 text-purple-200'
                    : 'bg-gray-800/50 border-white/5 text-gray-400 hover:border-white/15 hover:text-gray-200'
                }`}
                title={opt.desc}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Epic Toggle */}
        <Row justify="space-between" align="middle">
          <Col>
            <Text strong style={{ fontSize: 12 }}>Epic Multi-Stage Journey</Text>
            <br /><Text type="secondary" style={{ fontSize: 10 }}>Generate {stages} sequential narrative stages.</Text>
          </Col>
          <Col><Switch checked={isEpic} onChange={setIsEpic} /></Col>
        </Row>
        {isEpic && (
          <Row align="middle" style={{ marginTop: 8 }}>
            <Text style={{ fontSize: 12, marginRight: 8 }}>Stages:</Text>
            <InputNumber size="small" min={3} max={15} value={stages} onChange={(v) => { if (v != null) setStages(v); }} />
          </Row>
        )}

        {/* Generate Button */}
        <Button
          type="primary"
          block
          size="large"
          icon={loading ? <RefreshCw className="animate-spin w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
          onClick={onGenerate}
          loading={loading}
          disabled={selectedLangs.length === 0}
          style={{ background: 'linear-gradient(135deg, #0891b2, #0d9488)', border: 'none' }}
        >
          {loading ? 'Decrypting Transmission...' : 'Initiate Narrative Stream'}
        </Button>
      </Space>
    </Card>
  );
}
