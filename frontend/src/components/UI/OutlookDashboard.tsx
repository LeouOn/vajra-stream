/**
 * Outlook Dashboard — narrative generation, universe management, and blessing loop.
 *
 * Composition root. The tabs:
 * 1. Generator — Guided Flow or Quick Generate settings, background
 *    generation, and the narrative result (outlook/NarrativeResult)
 * 2. Universe — manage realms, characters, populations (outlook/UniverseTab)
 * 3. History — browse past transmissions (outlook/HistoryTab)
 * 4. Journey — the practice journey card
 *
 * State lives in focused hooks under ./outlook (form, universe, history,
 * models, background loop, generation, media, ritual reveal, TTS bridge);
 * this file wires them together and owns the mount/reconnect refreshes.
 *
 * @component
 */
import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Zap } from 'lucide-react';
import { Card, Segmented, Row, Col, Space } from 'antd';
import { useUIStore } from '../../stores/uiStore';
import { audioFeedback } from '../../utils/audioFeedback';
import { useAudioStore } from '../../stores/audioStore';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import RothkoGenerator from '../2D/RothkoGenerator';
import GuidedRitualFlow from './GuidedRitualFlow';
import JourneyCard from './JourneyCard';
import HistoryTab from './outlook/HistoryTab';
import UniverseTab from './outlook/UniverseTab';
import OutlookHeader from './outlook/OutlookHeader';
import GeneratorSettingsCard from './outlook/GeneratorSettingsCard';
import BackgroundGenerationCard from './outlook/BackgroundGenerationCard';
import NarrativeResult from './outlook/NarrativeResult';
import { DEFAULT_CHARACTERS } from './outlook/outlookConstants';
import type { CurrentNarrative, GenerationMode, GeneratorTab } from './outlook/outlookNarrative';
import { useGeneratorForm } from './outlook/useGeneratorForm';
import { useOutlookUniverse } from './outlook/useOutlookUniverse';
import { useOutlookHistory } from './outlook/useOutlookHistory';
import { useOutlookModels } from './outlook/useOutlookModels';
import { useOutlookGeneration } from './outlook/useOutlookGeneration';
import { useNarrativeMedia } from './outlook/useNarrativeMedia';
import { useBackgroundGeneration } from './outlook/useBackgroundGeneration';
import { useRitualReveal } from './outlook/useRitualReveal';
import { useNarrativeTTS } from './outlook/useNarrativeTTS';

export default function OutlookDashboard() {
  const { isPlaying } = useAudioStore();
  const addToast = useUIStore((s) => s.addToast);
  const { isConnected } = useWebSocketStable();
  const [activeTab, setActiveTab] = useState<GeneratorTab>('generator');
  const [generationMode, setGenerationMode] = useState<GenerationMode>('guided');

  const form = useGeneratorForm();
  const universe = useOutlookUniverse(addToast);
  const { historyList, fetchHistory, deleteHistoryItem } = useOutlookHistory(addToast);
  const models = useOutlookModels(addToast);
  const generation = useOutlookGeneration({
    form,
    model: models,
    fetchHistory,
    fetchUniverseData: universe.fetchUniverseData,
  });
  const { currentNarrative, setCurrentNarrative } = generation;
  const media = useNarrativeMedia(currentNarrative);
  const bg = useBackgroundGeneration({
    lat: form.lat,
    lon: form.lon,
    selectedLangs: form.selectedLangs,
    fetchHistory,
  });

  const { fetchUniverseData, realms, characters, setCharacters, populations } = universe;
  const { fetchModels, fetchProvidersHealth } = models;
  const { fetchBgStatus } = bg;

  useEffect(() => {
    fetchUniverseData();
    fetchHistory();
    fetchModels();
    fetchProvidersHealth();
    fetchBgStatus();
  }, []);

  useEffect(() => {
    if (isConnected) {
      fetchUniverseData();
      fetchHistory();
      fetchModels();
      fetchProvidersHealth();
      fetchBgStatus();
    }
    // Intentionally NOT listing the fetch callbacks in deps — they capture
    // addToast and may change identity on each render, which would cause
    // an infinite refetch loop. This matches the JourneyCard pattern.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected]);

  // Auto-set coordinates from selected realm
  const { selectedRealmId, setLat, setLon, selectedPopIds, setSelectedPopIds } = form;
  useEffect(() => {
    if (selectedRealmId) {
      const realm = realms.find(r => r.id === selectedRealmId);
      if (realm && !realm.is_metaphysical && realm.latitude != null && realm.longitude != null) {
        setLat(realm.latitude);
        setLon(realm.longitude);
      }
    }
  }, [selectedRealmId, realms]);

  // Seed defaults so first-time users don't see "Characters (0) /
  // Populations (0)". Seed characters are local-only (not persisted);
  // populations are auto-selected from the backend's first 3. Each seeds
  // once on its own: the characters usually land first, and a shared
  // "seeded" flag used to stop the populations from ever being selected.
  const charactersSeededRef = useRef(false);
  useEffect(() => {
    if (charactersSeededRef.current) return;
    charactersSeededRef.current = true;
    if (characters.length === 0) {
      setCharacters(DEFAULT_CHARACTERS);
    }
  }, [characters.length]);

  const populationsSeededRef = useRef(false);
  useEffect(() => {
    if (populationsSeededRef.current || populations.length === 0) return;
    populationsSeededRef.current = true;
    if (selectedPopIds.length === 0) {
      setSelectedPopIds(populations.slice(0, 3).map(p => p.id));
    }
  }, [populations, selectedPopIds.length]);

  const { sections, revealedSections } = useRitualReveal(currentNarrative);
  const { narrativeSpeakRef, replayTTS } = useNarrativeTTS();

  const handleStartBroadcast = async (): Promise<void> => {
    if (!bg.bgActive) {
      await bg.toggleBackgroundGeneration();
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6">
      <Space orientation="vertical" size="large" className="w-full">

        <OutlookHeader activeTab={activeTab} onTabChange={setActiveTab} />

        {/* ── Ambient Rothko ── */}
        <Card styles={{ body: { padding: 0, height: 100, overflow: 'hidden' } }}>
          <RothkoGenerator isPlaying={isPlaying} palette="compassion" transitionSpeed={60} />
        </Card>

        {activeTab === 'generator' && (
          <>
            {/* Mode Toggle */}
            <div style={{ marginBottom: 16 }}>
              <Segmented
                value={generationMode}
                onChange={(v) => { setGenerationMode(v as GenerationMode); audioFeedback.playTabChange(); }}
                options={[
                  { label: <span><Sparkles className="w-3 h-3 inline mr-1" />🔮 Guided Flow</span>, value: 'guided' },
                  { label: <span><Zap className="w-3 h-3 inline mr-1" />⚡ Quick Generate</span>, value: 'quick' },
                ]}
                className="bg-black/40 border border-white/5"
              />
            </div>
            <Row gutter={[24, 24]}>
              {/* ── Left: Settings or Guided Flow ── */}
              <Col xs={24} xl={8}>
                {generationMode === 'guided' ? (
                  <GuidedRitualFlow
                    cosmicData={undefined}
                    activeChart={null}
                    result={currentNarrative}
                    broadcastActive={bg.bgActive}
                    onResult={(data) => setCurrentNarrative(data as CurrentNarrative)}
                    onStartBroadcast={() => { void handleStartBroadcast(); }}
                    onComplete={() => setGenerationMode('quick')}
                    onBackToQuick={() => setGenerationMode('quick')}
                  />
                ) : (
                  <GeneratorSettingsCard
                    form={form}
                    models={models}
                    realms={realms}
                    characters={characters}
                    populations={populations}
                    bgActive={bg.bgActive}
                    loading={generation.loading}
                    onGenerate={generation.handleGenerate}
                  />
                )}
                <BackgroundGenerationCard bg={bg} />
              </Col>

              {/* ── Right: Narrative Display ── */}
              <Col xs={24} xl={16}>
                <NarrativeResult
                  generation={generation}
                  media={media}
                  fallbackGenre={form.genre}
                  sections={sections}
                  revealedSections={revealedSections}
                  narrativeSpeakRef={narrativeSpeakRef}
                  onReplay={replayTTS}
                />
              </Col>
            </Row>
          </>
        )}

        {activeTab === 'universe' && (
          <UniverseTab
            realms={realms}
            characters={characters}
            populations={populations}
            roles={universe.roles}
            locationTypes={universe.locationTypes}
            selectedRealmId={selectedRealmId}
            onSelectRealm={form.setSelectedRealmId}
            selectedCharIds={form.selectedCharIds}
            onChangeSelectedCharIds={form.setSelectedCharIds}
            onRefreshUniverse={fetchUniverseData}
          />
        )}
        {activeTab === 'history' && (
          <HistoryTab
            historyList={historyList}
            onRefresh={fetchHistory}
            onDelete={(item) => deleteHistoryItem(item)}
            onLoadInGenerator={(item) => {
              generation.loadHistoryItem(item);
              setActiveTab('generator');
              audioFeedback.playClick();
            }}
          />
        )}
        {activeTab === 'journey' && (
          <div className="max-w-2xl mx-auto">
            <JourneyCard />
          </div>
        )}
      </Space>

    </div>
  );
}
