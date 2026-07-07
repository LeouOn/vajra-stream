/**
 * GuidedRitualFlow — a 5-step linear ritual wizard that chains existing
 * backend APIs into a ceremonial blessing experience.
 *
 * Steps:
 *   ① Kāmanā    — Intention: preset + custom text + genre auto-suggest
 *   ② Samāpatti — Alignment: cosmic conditions + oracle draw
 *   ③ Sādhana   — Generation: auto-triggered, calls /outlook/generate_single
 *   ④ Pārāyaṇa  — Recitation: TTS playback of the generated narrative
 *   ⑤ Pravṛtti  — Continuation: broadcast, new ritual, complete
 *
 * The wizard uses AntD's `Steps` for navigation, with each step rendered
 * as an AntD `Card` in the body's main area. Linear flow — each step must
 * complete before the next.
 *
 * @component
 */
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Steps, Card, Button, Input, Select, Tag, Space, Row, Col, Spin,
  message, Divider, Tooltip, Typography,
} from 'antd';
import {
  Sparkles, Compass, Dices, Volume2, Radio, CheckCircle,
  ArrowLeft, ArrowRight, RotateCcw, Moon, Star, Sun, AlertTriangle,
} from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';
import NarrativeTTSPlayer from './NarrativeTTSPlayer';
import { createLogger } from '../../utils/logger';

const { Text, Paragraph } = Typography;

// ─── Local structural mirror of `OutlookDashboard`'s CurrentNarrative ─────
// The parent component owns the canonical type; we declare a structurally
// compatible shape here so this component compiles independently. Because
// TypeScript is structural, any object the parent passes in that matches
// this contract (including the parent-owned `CurrentNarrative`) is accepted.
interface CurrentNarrativeLike {
  type?: string;
  genre?: string;
  narrative?: string;
  narrative_parts?: string[] | string;
  astrology_used?: string;
  divination_used?: string;
  entities_used?: string;
  model_used?: string;
  provider_used?: string;
  [key: string]: unknown;
}

// ─── Constants ────────────────────────────────────────────

const GENRE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'healing', label: '🌿 Healing' },
  { value: 'victory', label: '🛡️ Victory' },
  { value: 'alchemist', label: '⚗️ Alchemist' },
  { value: 'dharani', label: '📿 Dharani' },
];

const VOICE_PRESETS: ReadonlyArray<{ value: string; label: string }> = [
  { value: '', label: '✨ Default' },
  { value: 'compassionate_bodhisattva', label: '🪷 Compassionate Bodhisattva' },
  { value: 'sutra_chanter', label: '📿 Sutra Chanter' },
  { value: 'meditation_master', label: '🧘 Meditation Master' },
  { value: 'zen_teacher', label: '🍃 Zen Teacher' },
  { value: 'english_sacred', label: '📖 English Sacred' },
];

const INTENTION_PRESETS: ReadonlyArray<{
  label: string;
  value: string;
  genre: string;
  keywords: string;
}> = [
  { label: '🕊️ World Peace', value: 'World peace and the cessation of all conflict', genre: 'healing', keywords: 'peace conflict war' },
  { label: '💎 Prosperity', value: 'Abundance and prosperity for all beings', genre: 'alchemist', keywords: 'abundance prosperity wealth' },
  { label: '☀️ Healing', value: 'Healing of all physical, mental, and spiritual illness', genre: 'healing', keywords: 'healing illness disease sickness' },
  { label: '🌲 Reforestation', value: "Healing and restoration of the world's forests and ecosystems", genre: 'healing', keywords: 'forest tree reforestation ecosystem nature' },
  { label: '🌊 Purification', value: 'Purification of all negativity and obscurations', genre: 'dharani', keywords: 'purify purification clean cleansing' },
  { label: '✨ Liberation', value: 'Liberation of all sentient beings from samsara', genre: 'victory', keywords: 'liberation freedom awakening samsara' },
];

const STEP_TITLES = ['Intention', 'Alignment', 'Generation', 'Recitation', 'Continuation'] as const;
type StepIndex = 0 | 1 | 2 | 3 | 4;

interface CosmicData {
  planetaryHour?: string;
  moonPhase?: string;
  moonIllumination?: number;
  nakshatra?: string;
  dominantElement?: string;
  dashaPeriod?: string;
}

interface ActiveChart {
  birth_time_iso?: string;
  latitude?: number;
  longitude?: number;
  name?: string;
}

interface OracleDraw {
  kind: 'tarot' | 'iching' | 'geomancy' | null;
  result: string;
}

interface GuidedRitualFlowProps {
  cosmicData?: CosmicData;
  activeChart?: ActiveChart | null;
  result?: CurrentNarrativeLike | null;
  broadcastActive?: boolean;
  onResult: (data: CurrentNarrativeLike) => void;
  onStartBroadcast: () => void;
  onComplete: () => void;
  onBackToQuick: () => void;
}

// ─── Helpers ──────────────────────────────────────────────

/** Choose a genre based on keyword overlap with the user's intention text. */
function suggestGenre(intention: string): string {
  const text = intention.toLowerCase();
  let bestGenre: string = 'healing';
  let bestScore = 0;
  for (const preset of INTENTION_PRESETS) {
    const keywords = preset.keywords.split(/\s+/);
    const score = keywords.reduce((acc, kw) => (kw && text.includes(kw) ? acc + 1 : acc), 0);
    if (score > bestScore) {
      bestScore = score;
      bestGenre = preset.genre;
    }
  }
  return bestGenre;
}

const PURPLE_GRADIENT_STYLE: React.CSSProperties = {
  background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
  border: 'none',
  color: '#fff',
};

const HEADER_CLASS = 'text-[10px] font-mono tracking-wider uppercase text-amber-400';

// ─── Component ────────────────────────────────────────────

export default function GuidedRitualFlow({
  cosmicData,
  activeChart,
  result,
  broadcastActive,
  onResult,
  onStartBroadcast,
  onComplete,
  onBackToQuick,
}: GuidedRitualFlowProps): JSX.Element {
  const log = createLogger('GuidedRitualFlow');

  // ─── Wizard state ────────────────────────────────────────
  const [step, setStep] = useState<StepIndex>(0);

  // Step 0
  const [intention, setIntention] = useState<string>('');
  const [genre, setGenre] = useState<string>('healing');

  // Step 1
  const [oracle, setOracle] = useState<OracleDraw>({ kind: null, result: '' });
  const [oracleLoading, setOracleLoading] = useState<boolean>(false);

  // Step 2 — generation
  const [generating, setGenerating] = useState<boolean>(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Step 3 — TTS
  const [voicePreset, setVoicePreset] = useState<string>('');

  // Guard against the auto-trigger useEffect firing twice in strict mode.
  const generationTriggeredRef = useRef<boolean>(false);

  // ─── Handlers ────────────────────────────────────────────

  const handleIntentionPreset = useCallback((value: string, suggestedGenre: string): void => {
    audioFeedback.playClick();
    setIntention(value);
    setGenre(suggestedGenre);
  }, []);

  const handleContinueFromZero = useCallback((): void => {
    if (!intention.trim()) {
      message.warning('Please set an intention to continue.');
      return;
    }
    audioFeedback.playTabChange();
    setStep(1);
  }, [intention]);

  const drawOracle = useCallback(async (kind: 'tarot' | 'iching' | 'geomancy'): Promise<void> => {
    setOracleLoading(true);
    audioFeedback.playTelemetry();
    try {
      const endpoint =
        kind === 'tarot'
          ? '/divination/tarot/draw'
          : kind === 'iching'
          ? '/divination/iching/cast'
          : '/divination/geomancy/cast';
      const body = kind === 'tarot' ? JSON.stringify({ count: 1 }) : undefined;
      const res = await fetch(`/api/v1${endpoint}`, {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body,
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({} as { detail?: string }));
        throw new Error(detail.detail || `Oracle cast failed: HTTP ${res.status}`);
      }
      const data = await res.json() as Record<string, unknown>;
      // Render the divination payload as readable text. ``stringify`` with 2-space
      // indent produces a stable, glanceable summary across all three oracles.
      setOracle({ kind, result: JSON.stringify(data, null, 2) });
      audioFeedback.playSuccess();
      message.success(`${kind} cast complete.`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      log.error(`${kind} draw failed:`, msg);
      message.error(msg);
      audioFeedback.playError();
    } finally {
      setOracleLoading(false);
    }
  }, [log]);

  const triggerGeneration = useCallback(async (): Promise<void> => {
    if (generationTriggeredRef.current) return;
    generationTriggeredRef.current = true;
    setGenerating(true);
    setGenerationError(null);
    audioFeedback.playTelemetry();

    try {
      const body: Record<string, unknown> = {
        lat: activeChart?.latitude ?? 34.0522,
        lon: activeChart?.longitude ?? -118.2437,
        languages: ['English'],
        genre,
        custom_context: intention,
        include_astrology: true,
        include_tarot: oracle.kind === 'tarot',
        include_iching: oracle.kind === 'iching' || oracle.kind === null,
        include_geomancy: oracle.kind === 'geomancy',
      };
      if (activeChart?.birth_time_iso) body.natal_date_iso = activeChart.birth_time_iso;
      if (activeChart?.latitude != null) body.natal_lat = activeChart.latitude;
      if (activeChart?.longitude != null) body.natal_lon = activeChart.longitude;

      const res = await fetch('/api/v1/outlook/generate_single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({} as { detail?: string }));
        throw new Error(err.detail || `Generation failed: HTTP ${res.status}`);
      }
      const data = await res.json() as CurrentNarrativeLike;
      onResult(data);
      audioFeedback.playSuccess();
      message.success('Narrative received from the cosmos.');
      // Auto-advance after a brief linger so the success toast is readable.
      setTimeout(() => setStep(3), 600);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      log.error('Generation failed:', msg);
      setGenerationError(msg);
      audioFeedback.playError();
      // Allow retry by clearing the trigger guard.
      generationTriggeredRef.current = false;
    } finally {
      setGenerating(false);
    }
  }, [activeChart, genre, intention, oracle.kind, onResult, log]);

  const retryGeneration = useCallback((): void => {
    setGenerationError(null);
    generationTriggeredRef.current = false;
    void triggerGeneration();
  }, [triggerGeneration]);

  // Auto-trigger generation on entering step 2 — only if not already generated.
  useEffect(() => {
    if (step !== 2) return;
    if (result) {
      // A result is already present (e.g. user went Back, then Forward again).
      // Skip generation but still advance to step 3.
      const id = window.setTimeout(() => setStep(3), 300);
      return () => window.clearTimeout(id);
    }
    void triggerGeneration();
  }, [step, result, triggerGeneration]);

  // Auto-suggest genre from intention keywords the first time intention
  // is populated by a preset click. Free-form typing keeps the user's choice.
  useEffect(() => {
    if (!intention) return;
    const matched = INTENTION_PRESETS.find(p => p.value === intention);
    if (matched) setGenre(matched.genre);
    // Only react to preset matches — don't override a user's manual typing here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intention]);

  // ─── Derived values ──────────────────────────────────────

  const narrativeText = useMemo<string>(() => {
    if (!result) return '';
    return result.narrative ?? '';
  }, [result]);

  // ─── Render ──────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* ── Top: Step indicator ────────────────────────────── */}
      <Card size="small" className="bg-gray-900/80 border-purple-500/20">
        <Steps
          size="small"
          current={step}
          items={STEP_TITLES.map((title, idx) => ({ title }))}
          className="[&_.ant-steps-item-title]:text-[10px] [&_.ant-steps-item-title]:font-mono [&_.ant-steps-item-title]:uppercase [&_.ant-steps-item-title]:tracking-wider"
        />
      </Card>

      {/* ═══════════════════════════════════════════════════════
          STEP 0 — Intention (Kāmanā)
      ═══════════════════════════════════════════════════════ */}
      {step === 0 && (
        <Card
          key="step-0"
          className="bg-gray-900/80 border-purple-500/20 animate-slide-up"
          title={
            <Space>
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span className={HEADER_CLASS}>① Intention — Kāmanā</span>
            </Space>
          }
        >
          <Space orientation="vertical" size="middle" className="w-full">
            <Text style={{ fontSize: 12 }} type="secondary">
              Choose an intention, or compose your own. The genre will follow the meaning.
            </Text>

            <div>
              <Text className={`${HEADER_CLASS} block mb-2`}>Sacred Presets</Text>
              <Space wrap>
                {INTENTION_PRESETS.map((preset) => {
                  const isActive = intention === preset.value;
                  return (
                    <Button
                      key={preset.label}
                      size="small"
                      ghost
                      style={isActive ? PURPLE_GRADIENT_STYLE : undefined}
                      onClick={() => handleIntentionPreset(preset.value, preset.genre)}
                    >
                      {preset.label}
                    </Button>
                  );
                })}
              </Space>
            </div>

            <div>
              <Text className={`${HEADER_CLASS} block mb-2`}>Custom Intention</Text>
              <Input.TextArea
                rows={3}
                value={intention}
                onChange={(e) => {
                  const v = e.target.value;
                  setIntention(v);
                  // If the user types, suggest a genre from the text but only
                  // when they haven't already manually selected one this session.
                  if (v && genre === 'healing') {
                    const suggested = suggestGenre(v);
                    if (suggested !== 'healing') setGenre(suggested);
                  }
                }}
                placeholder="Compose your own aspiration... (e.g. 'May all beings find peace')"
                maxLength={500}
                showCount
              />
            </div>

            <div>
              <Text className={`${HEADER_CLASS} block mb-2`}>Genre (auto-suggested)</Text>
              <Select
                value={genre}
                onChange={(v: string) => {
                  audioFeedback.playClick();
                  setGenre(v);
                }}
                className="w-full"
                size="middle"
                options={GENRE_OPTIONS as { value: string; label: string }[]}
              />
            </div>

            <Divider style={{ margin: '4px 0' }} />

            <Row justify="end">
              <Col>
                <Button
                  type="primary"
                  size="middle"
                  disabled={!intention.trim()}
                  onClick={handleContinueFromZero}
                  icon={<ArrowRight className="w-4 h-4" />}
                  style={intention.trim() ? PURPLE_GRADIENT_STYLE : undefined}
                >
                  Continue →
                </Button>
              </Col>
            </Row>
          </Space>
        </Card>
      )}

      {/* ═══════════════════════════════════════════════════════
          STEP 1 — Alignment (Samāpatti)
      ═══════════════════════════════════════════════════════ */}
      {step === 1 && (
        <Card
          key="step-1"
          className="bg-gray-900/80 border-purple-500/20 animate-slide-up"
          title={
            <Space>
              <Compass className="w-4 h-4 text-cyan-400" />
              <span className={HEADER_CLASS}>② Alignment — Samāpatti</span>
            </Space>
          }
        >
          <Row gutter={[16, 16]}>
            {/* Left: Cosmic Conditions */}
            <Col xs={24} md={12}>
              <Card
                size="small"
                className="bg-black/40 border-white/5 h-full"
                title={
                  <Text className={HEADER_CLASS}>
                    <Moon className="w-3 h-3 inline mr-1" /> Cosmic Conditions
                  </Text>
                }
              >
                {cosmicData ? (
                  <Space orientation="vertical" size="small" className="w-full">
                    {cosmicData.planetaryHour && (
                      <div>
                        <Text type="secondary" style={{ fontSize: 10 }}>Planetary Hour</Text>
                        <div><Tag color="purple">{cosmicData.planetaryHour}</Tag></div>
                      </div>
                    )}
                    {cosmicData.moonPhase && (
                      <div>
                        <Text type="secondary" style={{ fontSize: 10 }}>Moon Phase</Text>
                        <div>
                          <Tag color="cyan">
                            {cosmicData.moonPhase}
                            {typeof cosmicData.moonIllumination === 'number' &&
                              ` · ${Math.round(cosmicData.moonIllumination * 100)}%`}
                          </Tag>
                        </div>
                      </div>
                    )}
                    {cosmicData.nakshatra && (
                      <div>
                        <Text type="secondary" style={{ fontSize: 10 }}>Nakshatra</Text>
                        <div><Tag color="geekblue">{cosmicData.nakshatra}</Tag></div>
                      </div>
                    )}
                    {cosmicData.dominantElement && (
                      <div>
                        <Text type="secondary" style={{ fontSize: 10 }}>Dominant Element</Text>
                        <div>
                          <Tag color={
                            cosmicData.dominantElement.toLowerCase().includes('fire') ? 'volcano' :
                            cosmicData.dominantElement.toLowerCase().includes('water') ? 'blue' :
                            cosmicData.dominantElement.toLowerCase().includes('earth') ? 'gold' :
                            cosmicData.dominantElement.toLowerCase().includes('air') ? 'cyan' :
                            'purple'
                          }>
                            {cosmicData.dominantElement}
                          </Tag>
                        </div>
                      </div>
                    )}
                    {cosmicData.dashaPeriod && (
                      <div>
                        <Text type="secondary" style={{ fontSize: 10 }}>Dasha Period</Text>
                        <div><Tag>{cosmicData.dashaPeriod}</Tag></div>
                      </div>
                    )}
                    {!cosmicData.planetaryHour &&
                      !cosmicData.moonPhase &&
                      !cosmicData.nakshatra &&
                      !cosmicData.dominantElement && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        <Star className="w-3 h-3 inline mr-1" />
                        Partial cosmic data received; the ritual will proceed without a full chart.
                      </Text>
                    )}
                  </Space>
                ) : (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <Sun className="w-3 h-3 inline mr-1" />
                    Awaiting cosmic data...
                  </Text>
                )}
              </Card>
            </Col>

            {/* Right: Oracle Draw */}
            <Col xs={24} md={12}>
              <Card
                size="small"
                className="bg-black/40 border-white/5 h-full"
                title={
                  <Text className={HEADER_CLASS}>
                    <Dices className="w-3 h-3 inline mr-1" /> Oracle Draw
                  </Text>
                }
              >
                <Space orientation="vertical" size="small" className="w-full">
                  <Space wrap>
                    <Button
                      size="small"
                      ghost
                      loading={oracleLoading && oracle.kind !== 'tarot'}
                      style={oracle.kind === 'tarot' ? PURPLE_GRADIENT_STYLE : undefined}
                      onClick={() => void drawOracle('tarot')}
                    >
                      🃏 Draw Tarot
                    </Button>
                    <Button
                      size="small"
                      ghost
                      loading={oracleLoading && oracle.kind !== 'iching'}
                      style={oracle.kind === 'iching' ? PURPLE_GRADIENT_STYLE : undefined}
                      onClick={() => void drawOracle('iching')}
                    >
                      ☯️ Cast I Ching
                    </Button>
                    <Button
                      size="small"
                      ghost
                      loading={oracleLoading && oracle.kind !== 'geomancy'}
                      style={oracle.kind === 'geomancy' ? PURPLE_GRADIENT_STYLE : undefined}
                      onClick={() => void drawOracle('geomancy')}
                    >
                      🔮 Cast Geomancy
                    </Button>
                  </Space>

                  {oracle.kind && (
                    <Tooltip title={oracle.result} placement="topLeft">
                      <Tag color="purple" className="cursor-help">
                        {oracle.kind} drawn — hover to view
                      </Tag>
                    </Tooltip>
                  )}
                  {oracle.result && (
                    <Paragraph
                      style={{ fontSize: 10, color: '#a5b4fc', maxHeight: 120, overflowY: 'auto' }}
                      className="!mb-0 whitespace-pre-wrap font-mono"
                    >
                      {oracle.result.slice(0, 280)}
                      {oracle.result.length > 280 ? '…' : ''}
                    </Paragraph>
                  )}
                </Space>
              </Card>
            </Col>
          </Row>

          <Divider style={{ margin: '12px 0 8px' }} />

          <Row justify="space-between">
            <Col>
              <Button
                ghost
                size="middle"
                icon={<ArrowLeft className="w-4 h-4" />}
                onClick={() => {
                  audioFeedback.playClick();
                  setStep(0);
                }}
              >
                ← Back
              </Button>
            </Col>
            <Col>
              <Button
                type="primary"
                size="middle"
                onClick={() => {
                  audioFeedback.playTabChange();
                  setStep(2);
                }}
                icon={<ArrowRight className="w-4 h-4" />}
                style={PURPLE_GRADIENT_STYLE}
              >
                Continue →
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* ═══════════════════════════════════════════════════════
          STEP 2 — Generation (Sādhana)
      ═══════════════════════════════════════════════════════ */}
      {step === 2 && (
        <Card
          key="step-2"
          className="bg-gray-900/80 border-purple-500/20 animate-slide-up"
          title={
            <Space>
              <Sparkles className="w-4 h-4 text-amber-400 animate-pulse-slow" />
              <span className={HEADER_CLASS}>③ Generation — Sādhana</span>
            </Space>
          }
        >
          {generating ? (
            <div className="py-8 text-center">
              <Spin size="large" />
              <Paragraph
                className="!mt-4 font-mono !text-amber-300/80 text-xs uppercase tracking-wider"
                style={{ letterSpacing: '0.1em' }}
              >
                Channeling the cosmic narrative…
              </Paragraph>
            </div>
          ) : generationError ? (
            <Space orientation="vertical" size="middle" className="w-full">
              <div className="flex items-start gap-2 text-red-300">
                <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                <div>
                  <Text strong className="text-red-300">Generation failed</Text>
                  <Paragraph className="!mb-0 text-sm" type="secondary">
                    {generationError}
                  </Paragraph>
                </div>
              </div>
              <Space>
                <Button
                  type="primary"
                  danger
                  onClick={retryGeneration}
                  icon={<RotateCcw className="w-4 h-4" />}
                >
                  Retry Generation
                </Button>
                <Button ghost onClick={() => setStep(1)} icon={<ArrowLeft className="w-4 h-4" />}>
                  ← Back to Alignment
                </Button>
              </Space>
            </Space>
          ) : (
            <Space orientation="vertical" size="middle" className="w-full">
              <Text className="text-cyan-300 font-mono text-sm">
                <CheckCircle className="w-4 h-4 inline mr-1" />
                Narrative received. Advancing to recitation…
              </Text>
              <div className="flex justify-end">
                <Button
                  type="primary"
                  size="middle"
                  onClick={() => {
                    audioFeedback.playTabChange();
                    setStep(3);
                  }}
                  icon={<ArrowRight className="w-4 h-4" />}
                  style={PURPLE_GRADIENT_STYLE}
                >
                  Continue →
                </Button>
              </div>
            </Space>
          )}
        </Card>
      )}

      {/* ═══════════════════════════════════════════════════════
          STEP 3 — Recitation (Pārāyaṇa)
      ═══════════════════════════════════════════════════════ */}
      {step === 3 && (
        <Card
          key="step-3"
          className="bg-gray-900/80 border-purple-500/20 animate-slide-up"
          title={
            <Space>
              <Volume2 className="w-4 h-4 text-emerald-400" />
              <span className={HEADER_CLASS}>④ Recitation — Pārāyaṇa</span>
            </Space>
          }
        >
          <Space orientation="vertical" size="middle" className="w-full">
            {!narrativeText ? (
              <Text type="secondary">
                No narrative available. Return to generation.
              </Text>
            ) : (
              <>
                <div>
                  <Text className={`${HEADER_CLASS} block mb-2`}>Voice Preset</Text>
                  <Select
                    value={voicePreset}
                    onChange={(v: string) => {
                      audioFeedback.playClick();
                      setVoicePreset(v);
                    }}
                    className="w-full"
                    options={VOICE_PRESETS as { value: string; label: string }[]}
                  />
                </div>

                <Divider style={{ margin: '4px 0' }} />

                <div>
                  <Text className={`${HEADER_CLASS} block mb-2`}>Listen</Text>
                  <NarrativeTTSPlayer
                    text={narrativeText}
                    role="guided_ritual"
                    voice={voicePreset || null}
                    label="Recite Narrative"
                    size="middle"
                    showAdvanced
                  />
                </div>

                <Paragraph
                  className="!mt-3 text-sm leading-relaxed"
                  style={{
                    color: '#cbd5e1',
                    maxHeight: 220,
                    overflowY: 'auto',
                    background: 'rgba(0,0,0,0.4)',
                    padding: 12,
                    borderRadius: 8,
                  }}
                >
                  {narrativeText}
                </Paragraph>
              </>
            )}

            <Divider style={{ margin: '4px 0' }} />

            <Row justify="space-between">
              <Col>
                <Button
                  ghost
                  size="middle"
                  icon={<ArrowLeft className="w-4 h-4" />}
                  onClick={() => {
                    audioFeedback.playClick();
                    setStep(2);
                  }}
                >
                  ← Back
                </Button>
              </Col>
              <Col>
                <Button
                  type="primary"
                  size="middle"
                  onClick={() => {
                    audioFeedback.playTabChange();
                    setStep(4);
                  }}
                  disabled={!narrativeText}
                  icon={<ArrowRight className="w-4 h-4" />}
                  style={narrativeText ? PURPLE_GRADIENT_STYLE : undefined}
                >
                  Continue →
                </Button>
              </Col>
            </Row>
          </Space>
        </Card>
      )}

      {/* ═══════════════════════════════════════════════════════
          STEP 4 — Continuation (Pravṛtti)
      ═══════════════════════════════════════════════════════ */}
      {step === 4 && (
        <Card
          key="step-4"
          className="bg-gray-900/80 border-purple-500/20 animate-slide-up"
          title={
            <Space>
              <Radio className="w-4 h-4 text-rose-400" />
              <span className={HEADER_CLASS}>⑤ Continuation — Pravṛtti</span>
            </Space>
          }
        >
          <Space orientation="vertical" size="middle" className="w-full">
            <Text className="text-slate-300 text-sm">
              The narrative has been received. What would you like to do next?
            </Text>

            {broadcastActive && (
              <Tag color="processing" className="font-mono">
                📡 Broadcasting in progress
              </Tag>
            )}

            <Space wrap>
              <Button
                type="primary"
                danger={broadcastActive}
                size="middle"
                icon={<Radio className="w-4 h-4" />}
                onClick={() => {
                  audioFeedback.playTabChange();
                  onStartBroadcast();
                }}
              >
                📡 {broadcastActive ? 'Broadcasting…' : 'Start Broadcasting'}
              </Button>
              <Button
                ghost
                size="middle"
                icon={<RotateCcw className="w-4 h-4" />}
                onClick={() => {
                  audioFeedback.playTabChange();
                  setStep(0);
                  setIntention('');
                  setGenre('healing');
                  setOracle({ kind: null, result: '' });
                  setGenerationError(null);
                  setVoicePreset('');
                  generationTriggeredRef.current = false;
                }}
              >
                🔄 New Ritual
              </Button>
              <Button
                ghost
                size="middle"
                icon={<CheckCircle className="w-4 h-4" />}
                onClick={() => {
                  audioFeedback.playSuccess();
                  onComplete();
                }}
              >
                ✓ Complete
              </Button>
              <Button
                ghost
                size="middle"
                icon={<ArrowLeft className="w-4 h-4" />}
                onClick={() => {
                  audioFeedback.playClick();
                  onBackToQuick();
                }}
              >
                ← Quick Mode
              </Button>
            </Space>
          </Space>
        </Card>
      )}
    </div>
  );
}
