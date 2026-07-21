/**
 * Command Center — primary operator console for Vajra.Stream.
 *
 * Central hub for issuing text commands to the unified orchestrator.
 * Features a terminal-style input with command history, live WebSocket
 * status feed, MOPS throughput display, and quick-action buttons for
 * common radionics and blessing operations. The largest UI component
 * (~1300 lines) — serves as the primary interaction surface.
 *
 * @component
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { ReactNode } from 'react';
import {
  Send, Terminal, Cpu, AlertTriangle,
  Sparkles, Shield, Compass, BookOpen, Clock, Play, Square, X, Sun,
  RefreshCw, Bug, RotateCcw, Activity, HeartPulse
} from 'lucide-react';
import { Card, Input, Button, Select, Switch, Tag, Badge, Space, Statistic, Tooltip } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { audioFeedback } from '../../utils/audioFeedback';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { apiUrl } from '../../utils/api';

import { useWebSocketStable as useWebSocket } from '../../hooks/useWebSocketStable';
import SakaDawaBanner from './SakaDawaBanner';
import { RenderMessageWidgets } from '../CommandCenter/RenderMessageWidgets';
import { RichMarkdownRenderer } from '../CommandCenter/RichMarkdownRenderer';
import { quickCommands, createOperatorActions } from '../CommandCenter/constants';
import SystemMonitorsCard from '../CommandCenter/SystemMonitorsCard';
import LogsCard from '../CommandCenter/LogsCard';
import ZoomModal from '../CommandCenter/ZoomModal';
import PageHeader from './PageHeader';

// ─── Types ──────────────────────────────────────────────────────────

/** A single tool-call result from the chat API. */
interface ToolCall {
  tool_name: string;
  arguments: Record<string, unknown>;
  status: string;
  result?: unknown;
  error?: string | null;
}

/** Per-message debug telemetry returned by /api/v1/llm/chat (debug_mode=true). */
interface DebugInfo {
  model?: string;
  provider?: string;
  provider_selected?: string;
  model_selected?: string;
  input_tokens?: number;
  output_tokens?: number;
  finish_reason?: string;
  reasoning_content?: string;
  reasoning_tokens?: number;
  system_prompt?: string;
  messages_sent?: Array<{ role: string; content: string }>;
  tools_available?: string[];
  timestamp?: number;
  [key: string]: unknown;
}

/** A chat message (user or assistant) with optional debug telemetry. */
interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  action?: string;
  toolCalls?: ToolCall[];
  debugInfo?: DebugInfo | null;
  reasoningContent?: string | null;
  modelUsed?: string | null;
  providerUsed?: string | null;
  inputTokens?: number | null;
  outputTokens?: number | null;
  latencyMs?: number | null;
  costUsd?: number | null;
  promptMessages?: ChatMessage[];
  isError?: boolean;
  retryInput?: string;
}

/** Rich model metadata from GET /api/v1/llm/models/available. */
interface AvailableModelMeta {
  id: string;
  name: string;
  provider: string;
  context_length: number | null;
  input_per_m: number;
  output_per_m: number;
  is_free: boolean;
  featured: boolean;
  description: string;
  source: string;
}

/** Response shape of GET /api/v1/llm/models/available. */
interface AvailableModelsResponse {
  status: string;
  count: number;
  fetched_at: number | null;
  source: string;
  models: AvailableModelMeta[];
}

/** Per-model pricing entry for client-side cost computation. */
interface ModelPricing {
  input_per_m: number;
  output_per_m: number;
  is_free: boolean;
}

/** Provider health entry from GET /api/v1/llm/providers/health. */
interface ProviderHealthEntry {
  provider: string;
  healthy: boolean;
  latency_ms: number | null;
  error: string | null;
  checked_at: number;
}

/** Response shape of GET /api/v1/llm/providers/health. */
interface ProviderHealthResponse {
  providers: ProviderHealthEntry[];
  healthy_count: number;
  total_count: number;
  message?: string;
}

/** MOPS throughput rolling-average window. */
interface MopsWindow {
  '1s'?: number;
  '10s'?: number;
  '60s'?: number;
  '5m'?: number;
}

/** MOPS throughput averages (matches backend core/services/mops_engine.py). */
interface MopsAverages {
  scalar_pulses?: MopsWindow;
  mantras?: MopsWindow;
  crystals?: MopsWindow;
  divination?: MopsWindow;
  tuning?: MopsWindow;
}

/** Chakra entry from GET /api/v1/healing/chakra/all. */
interface ChakraEntry {
  name?: string;
  sanskrit?: string;
  english?: string;
  element?: string;
  color?: string;
  frequency?: number | number[];
  qualities?: string[];
  location?: string;
  [key: string]: unknown;
}

/** Basic models endpoint response (GET /api/v1/llm/models). */
interface BasicModelsResponse {
  status: string;
  available: {
    local: string[];
    api: string[];
    lm_studio: string[];
  };
  default_model: string;
  lm_studio_connected: boolean;
}

export default function CommandCenter({ 
  isConnected, 
  isPlaying, 
  frequency, 
  crystalStatus, 
  scalarStatus,
  sessions,
  sakaDawa
}) {
  const [activeZoomItem, setActiveZoomItem] = useState<unknown>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: '🔮 **Vajra.Stream Command Center Ready**\n\nI am your AI operator. I can assist you with system calibration, crystal programming, automated population blessings, and scalar broadcasts. How shall we direct the intention today?'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const [toolLogs, setToolLogs] = useState([
    {
      timestamp: new Date().toLocaleTimeString(),
      type: 'system',
      message: 'Quantum RNG & Attunement system online. Idle.'
    }
  ]);
  const [auraCoherence, setAuraCoherence] = useState(35);
  const [astroData, setAstroData] = useState<Record<string, unknown> | null>(null);
  const [includeAstrology, setIncludeAstrology] = useState(true);
  const [includeAnatomy, setIncludeAnatomy] = useState(true);
  const [includeHardware, setIncludeHardware] = useState(true);
  const [availableModels, setAvailableModels] = useState<{ local: string[]; api: string[]; lm_studio: string[] }>({ local: [], api: [], lm_studio: [] });
  const [selectedModel, setSelectedModel] = useState('auto');
  const [debugMode, setDebugMode] = useState(false);
  const [debugPayload, setDebugPayload] = useState<DebugInfo | Record<string, unknown> | null>(null);
  const [activeLogTab, setActiveLogTab] = useState('tools');

  const [availableModelList, setAvailableModelList] = useState<AvailableModelMeta[]>([]);
  const [modelPricing, setModelPricing] = useState<Record<string, ModelPricing>>({});
  const [providerHealth, setProviderHealth] = useState<ProviderHealthEntry[]>([]);
  const [chakraData, setChakraData] = useState<ChakraEntry[] | null>(null);
  const [mopsData, setMopsData] = useState<MopsAverages | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  
  useEffect(() => {
    const doFetch = async (lat, lon) => {
      try {
        const d = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const localTime = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
        
        const params = new URLSearchParams();
        params.append('datetime_str', localTime);
        if (lat !== null && lon !== null) {
          params.append('latitude', lat.toString());
          params.append('longitude', lon.toString());
        }
        
        const res = await fetch(`/api/v1/astrology/current?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          setAstroData(data.astrology);
        }
      } catch (e) {
        // Ignore
      }
    };

    const fetchAstro = async () => {
      doFetch(DEFAULT_LAT, DEFAULT_LNG);
    };
    
    fetchAstro();
    const interval = setInterval(fetchAstro, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch(apiUrl('/llm/models'));
        if (res.ok) {
          const data: BasicModelsResponse = await res.json();
          if (data.status === 'success') {
            setAvailableModels(data.available || { local: [], api: [], lm_studio: [] });
            if (!selectedModel || selectedModel === 'auto') {
              setSelectedModel('auto');
            }
          }
        }
      } catch (e) {
        console.error("Failed to fetch available models", e);
      }
    };
    fetchModels();
  }, []);

  useEffect(() => {
    const fetchModelCatalog = async () => {
      try {
        const res = await fetch(apiUrl('/llm/models/available'));
        if (res.ok) {
          const data: AvailableModelsResponse = await res.json();
          if (data.status === 'success' && Array.isArray(data.models)) {
            setAvailableModelList(data.models);
            const pricing: Record<string, ModelPricing> = {};
            for (const m of data.models) {
              pricing[m.id] = {
                input_per_m: m.input_per_m,
                output_per_m: m.output_per_m,
                is_free: m.is_free,
              };
            }
            setModelPricing(pricing);
          }
        }
      } catch {
        /* catalog is best-effort; basic /models still provides the selector */
      }
    };
    fetchModelCatalog();
  }, []);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(apiUrl('/llm/providers/health'));
        if (res.ok) {
          const data: ProviderHealthResponse = await res.json();
          setProviderHealth(data.providers || []);
        }
      } catch {
        /* health checks are best-effort */
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!includeAnatomy) {
      setChakraData(null);
      return;
    }
    let cancelled = false;
    const fetchChakras = async () => {
      try {
        const res = await fetch(apiUrl('/healing/chakra/all'));
        if (res.ok) {
          const data = await res.json();
          if (!cancelled && data.chakras) {
            setChakraData(data.chakras as ChakraEntry[]);
          }
        }
      } catch {
        /* chakra context is best-effort */
      }
    };
    fetchChakras();
    return () => { cancelled = true; };
  }, [includeAnatomy]);

  useEffect(() => {
    if (!includeHardware) {
      setMopsData(null);
      return;
    }
    let cancelled = false;
    const fetchMops = async () => {
      try {
        const res = await fetch(apiUrl('/mops/current'));
        if (res.ok) {
          const data = await res.json();
          if (!cancelled && data.mops) {
            setMopsData(data.mops as MopsAverages);
          }
        }
      } catch {
        /* mops context is best-effort */
      }
    };
    fetchMops();
    const interval = setInterval(fetchMops, 10000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [includeHardware]);

  // Ref to hold latest handleSendMessage (avoids stale closure in event listener)
  const handleSendMessageRef = useRef(handleSendMessage);
  handleSendMessageRef.current = handleSendMessage;

  // Listen for vajra:quick-command custom events (fired by SakaDawaBanner, etc.)
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ command?: string }>).detail;
      if (detail?.command) {
        setInput(detail.command);
        setTimeout(() => {
          handleSendMessageRef.current(detail.command);
        }, 200);
      }
    };
    window.addEventListener('vajra:quick-command', handler);
    return () => window.removeEventListener('vajra:quick-command', handler);
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Dynamic Aura Coherence simulation
  useEffect(() => {
    const interval = setInterval(() => {
      const active = isPlaying || Object.keys(sessions).length > 0;
      setAuraCoherence(prev => {
        const base = active ? 88 : 35;
        const range = active ? 8 : 10;
        const drift = base + Math.sin(Date.now() / 2000) * (range / 2) + Math.random() * (range / 2);
        return Math.min(100, Math.max(0, Math.round(drift)));
      });
    }, 250);
    return () => clearInterval(interval);
  }, [isPlaying, sessions]);

  // Auto-scroll to bottom of messages and logs
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [toolLogs]);

  // Play sound when messages update
  useEffect(() => {
    if (messages.length > 1) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === 'assistant') {
        audioFeedback.playTabChange();
      } else {
        audioFeedback.playClick();
      }
    }
  }, [messages]);

  // Play sound when tool execution logs update
  useEffect(() => {
    if (toolLogs.length > 1) {
      const lastLog = toolLogs[toolLogs.length - 1];
      if (lastLog.status === 'success') {
        audioFeedback.playSuccess();
      } else if (lastLog.status === 'error') {
        audioFeedback.playError();
      } else {
        audioFeedback.playTick();
      }
    }
  }, [toolLogs]);

  const addToolLog = (type: string, message: string, status: string = 'info') => {
    setToolLogs(prev => [
      ...prev,
      {
        timestamp: new Date().toLocaleTimeString(),
        type,
        message,
        status
      }
    ]);
  };

  const buildModelOptions = (): DefaultOptionType[] => {
    const stripPrefix = (m: string, prefix: string) =>
      m.startsWith(`${prefix}:`) ? m.slice(prefix.length + 1) : m;

    const groups: DefaultOptionType[] = [{
      label: '⚡ Auto',
      title: 'Auto-select',
      options: [
        { value: 'auto', label: '⚡ Auto (registry pick_best)' },
      ],
    }];

    if (availableModels.lm_studio && availableModels.lm_studio.length > 0) {
      groups.push({
        label: '🖥 LM Studio',
        title: 'LM Studio (Active)',
        options: availableModels.lm_studio.map(m => ({
          value: `lm_studio:${m}`,
          label: m,
        })),
      });
    }

    if (availableModels.local && availableModels.local.length > 0) {
      groups.push({
        label: '💾 Local GGUF',
        title: 'Local GGUF',
        options: availableModels.local.map(m => {
          const bare = stripPrefix(m, 'local');
          return { value: `local:${bare}`, label: bare };
        }),
      });
    }

    const apiByProvider = new Map<string, AvailableModelMeta[]>();
    for (const m of availableModelList) {
      const arr = apiByProvider.get(m.provider) || [];
      arr.push(m);
      apiByProvider.set(m.provider, arr);
    }
    const sortedProviders = Array.from(apiByProvider.keys()).sort();
    for (const provider of sortedProviders) {
      const models = apiByProvider.get(provider)!;
      groups.push({
        label: provider.charAt(0).toUpperCase() + provider.slice(1),
        title: provider,
        options: models.map(m => ({
          value: m.id,
          label: (
            <span className="flex items-center gap-1.5">
              <span className="truncate">{m.name}</span>
              {m.is_free
                ? <Tag color="green" style={{ fontSize: '8px', lineHeight: '14px', margin: 0, padding: '0 4px' }}>FREE</Tag>
                : <span className="text-gray-500 text-[9px] ml-auto font-mono">
                    ${m.input_per_m.toFixed(2)}/${m.output_per_m.toFixed(2)} per M
                  </span>}
            </span>
          ),
        })),
      });
    }

    if (availableModels.api && availableModels.api.length > 0 && availableModelList.length === 0) {
      groups.push({
        label: '🌐 API Providers',
        title: 'API Providers',
        options: availableModels.api
          .map((m): { value: string; label: string } | null => {
            const match = m.match(/^([a-zA-Z0-9_-]+)\s*\(([^)]+)\)\s*$/);
            if (!match) return null;
            return { value: `${match[1]}:${match[2]}`, label: m };
          })
          .filter((opt): opt is { value: string; label: string } => opt !== null),
      });
    }

    return groups;
  };

  function formatAstrologyContext(data: Record<string, unknown>): string {
    const lines: string[] = ['🪐 **Current Astrological Context:**'];
    const western = data.western as Record<string, unknown> | undefined;
    if (western) {
      if (western.sun_sign) lines.push(`- Sun: ${western.sun_sign}`);
      if (western.moon_sign) lines.push(`- Moon: ${western.moon_sign}`);
      if (western.ascendant) lines.push(`- Ascendant: ${western.ascendant}`);
    }
    const moonPhase = data.moon_phase as Record<string, unknown> | undefined;
    if (moonPhase) {
      if (moonPhase.phase_name) lines.push(`- Moon Phase: ${moonPhase.phase_name} (${moonPhase.illumination ?? ''}%)`);
    }
    const indian = data.indian as Record<string, unknown> | undefined;
    if (indian) {
      if (indian.nakshatra) lines.push(`- Nakshatra: ${indian.nakshatra}`);
    }
    return lines.join('\n');
  }

  function formatChakraContext(chakras: ChakraEntry[]): string {
    const lines: string[] = ['💚 **Energetic Anatomy (Chakra System) Context:**'];
    for (const c of chakras.slice(0, 7)) {
      const freq = Array.isArray(c.frequency) ? c.frequency.join('/') : (c.frequency ?? '');
      lines.push(`- ${c.name || c.sanskrit || 'Unknown'} (${c.sanskrit || ''}): ${c.element || ''} element, ${c.color || ''} color${freq ? `, ${freq} Hz` : ''}`);
    }
    return lines.join('\n');
  }

  function formatMopsContext(mops: MopsAverages): string {
    const lines: string[] = ['⚙️ **System Metrics (MOPS Throughput):**'];
    const categories: Array<[string, string, MopsWindow | undefined]> = [
      ['Scalar Pulses', 'scalar_pulses', mops.scalar_pulses],
      ['Mantras', 'mantras', mops.mantras],
      ['Crystals', 'crystals', mops.crystals],
      ['Divination', 'divination', mops.divination],
      ['Tuning', 'tuning', mops.tuning],
    ];
    for (const [label, , win] of categories) {
      if (win) {
        const rate = win['60s'] ?? win['10s'] ?? win['1s'] ?? 0;
        lines.push(`- ${label}: ${rate.toFixed(2)}/s (60s avg)`);
      }
    }
    return lines.join('\n');
  }

  function buildContextSystemMessage(): string | null {
    const parts: string[] = [];
    if (includeAstrology && astroData) {
      const ctx = formatAstrologyContext(astroData);
      if (ctx) parts.push(ctx);
    }
    if (includeAnatomy && chakraData && chakraData.length > 0) {
      parts.push(formatChakraContext(chakraData));
    }
    if (includeHardware && mopsData) {
      const ctx = formatMopsContext(mopsData);
      if (ctx) parts.push(ctx);
    }
    return parts.length > 0 ? parts.join('\n\n---\n\n') : null;
  }

  function computeCostUsd(modelId: string | null, inputTokens: number | null, outputTokens: number | null): number | null {
    if (!modelId || inputTokens == null || outputTokens == null) return null;
    const pricing = modelPricing[modelId];
    if (!pricing) return null;
    if (pricing.is_free) return 0;
    const cost = (inputTokens * pricing.input_per_m / 1_000_000) + (outputTokens * pricing.output_per_m / 1_000_000);
    return Math.round(cost * 1e6) / 1e6;
  }

  async function callChatAPI(
    msgs: ChatMessage[],
    opts: {
      model?: string;
      astrology?: boolean;
      anatomy?: boolean;
      hardware?: boolean;
      debug?: boolean;
    } = {}
  ): Promise<{
    response: string;
    tool_calls?: ToolCall[];
    debug_info?: DebugInfo;
    latencyMs: number;
  }> {
    const {
      model = selectedModel,
      astrology = includeAstrology,
      anatomy = includeAnatomy,
      hardware = includeHardware,
      debug = debugMode,
    } = opts;

    const contextSystem = buildContextSystemMessage();
    const messagesToSend = contextSystem
      ? [{ role: 'system' as const, content: contextSystem }, ...msgs]
      : msgs;

    const start = Date.now();
    abortRef.current = new AbortController();
    const chatResponse = await fetch(apiUrl('/llm/chat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: messagesToSend.map(m => ({ role: m.role, content: m.content })),
        provider: 'auto',
        model: model === 'auto' ? null : (model || null),
        include_astrology: astrology,
        astrology_data: astrology ? astroData : null,
        include_anatomy: anatomy,
        include_hardware: hardware,
        debug_mode: debug,
      }),
      signal: abortRef.current.signal,
    });
    const latencyMs = Date.now() - start;
    if (!chatResponse.ok) {
      throw new Error(`Chat API error: ${chatResponse.status} ${chatResponse.statusText}`);
    }
    const json = await chatResponse.json();
    return { ...json, latencyMs };
  }

  async function handleSendMessage(textToSend?: string) {
    const text = textToSend || input;
    if (!text.trim()) return;

    setInput('');
    setIsLoading(true);
    setLastError(null);
    audioFeedback.playTelemetry();

    const priorMessages = messages;
    const userMsg: ChatMessage = { role: 'user', content: text };
    const newMessages = [...priorMessages, userMsg];
    setMessages(newMessages);
    addToolLog('user', `User requested: "${text}"`);

    try {
      addToolLog('llm', 'Analyzing intent and planning operations...', 'pending');

      const data = await callChatAPI(newMessages);
      const latencyMs = data.latencyMs;
      if (data.debug_info) {
        setDebugPayload(data.debug_info);
      } else {
        setDebugPayload(null);
      }

      if (data.tool_calls && data.tool_calls.length > 0) {
        data.tool_calls.forEach((tc: ToolCall) => {
          if (tc.status === 'success') {
            addToolLog(
              'tool',
              `Executed ${tc.tool_name}(${JSON.stringify(tc.arguments)}) successfully`,
              'success'
            );
          } else {
            addToolLog(
              'tool',
              `Failed executing ${tc.tool_name}: ${tc.error}`,
              'error'
            );
          }
        });
      } else {
        addToolLog('llm', 'Request processed. No mechanical tool calls required.');
      }

      const dbg = data.debug_info || null;
      const modelUsed = dbg?.model || (selectedModel !== 'auto' ? selectedModel : null);
      const inputTokens = dbg?.input_tokens ?? null;
      const outputTokens = dbg?.output_tokens ?? null;
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: data.response,
        toolCalls: data.tool_calls,
        debugInfo: dbg,
        reasoningContent: dbg?.reasoning_content || null,
        modelUsed,
        providerUsed: dbg?.provider || dbg?.provider_selected || null,
        inputTokens,
        outputTokens,
        latencyMs,
        costUsd: computeCostUsd(modelUsed, inputTokens, outputTokens),
        promptMessages: newMessages,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      const errMsg = error instanceof Error ? error.message : String(error);
      console.error('Chat error:', error);
      addToolLog('system', `Error: ${errMsg}`, 'error');
      setLastError(errMsg);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant' as const,
          content: `⚠️ **Operator Error**: Connection failure or API request blocked.\n\nError details: \`${errMsg}\``,
          isError: true,
          retryInput: text,
        },
      ]);
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  }

  function handleCancelGeneration() {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsLoading(false);
    addToolLog('system', 'Generation cancelled by user.', 'error');
  }

  async function handleRegenerate(index: number, newModel: string | null = null) {
    const target = messages[index];
    if (!target || target.role !== 'assistant' || isLoading) return;
    const promptMessages = Array.isArray(target.promptMessages)
      ? target.promptMessages
      : messages.slice(0, index).filter(m => m.role === 'user' || m.role === 'assistant');
    if (promptMessages.length === 0) return;

    setIsLoading(true);
    audioFeedback.playTelemetry();
    addToolLog('llm', `Regenerating message #${index}${newModel ? ` with ${newModel}` : ''}...`, 'pending');
    try {
      const data = await callChatAPI(promptMessages, newModel ? { model: newModel } : {});
      const dbg = data.debug_info || target.debugInfo || null;
      const modelUsed = dbg?.model || newModel || target.modelUsed || (selectedModel !== 'auto' ? selectedModel : null);
      const inputTokens = dbg?.input_tokens ?? target.inputTokens ?? null;
      const outputTokens = dbg?.output_tokens ?? target.outputTokens ?? null;
      const updated: ChatMessage = {
        ...target,
        content: data.response,
        toolCalls: data.tool_calls ?? target.toolCalls,
        debugInfo: dbg,
        reasoningContent: dbg?.reasoning_content || null,
        modelUsed,
        providerUsed: dbg?.provider || dbg?.provider_selected || target.providerUsed || null,
        inputTokens,
        outputTokens,
        latencyMs: data.latencyMs ?? target.latencyMs ?? null,
        costUsd: computeCostUsd(modelUsed, inputTokens, outputTokens),
        isError: false,
        promptMessages,
      };
      setMessages(prev => prev.map((m, i) => (i === index ? updated : m)));
      if (data.debug_info) setDebugPayload(data.debug_info);
      addToolLog('llm', 'Regeneration complete', 'success');
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : String(error);
      console.error('Regenerate error:', error);
      addToolLog('system', `Regenerate error: ${errMsg}`, 'error');
      setLastError(errMsg);
    } finally {
      setIsLoading(false);
    }
  }

  const operatorActions = createOperatorActions({ frequency, isPlaying, sessions, crystalStatus, scalarStatus });

  async function handleOperatorAction(action: { key: string; label: string; icon: string; prompt: string; endpoint: string; body: () => Record<string, unknown> }) {
    if (isLoading) return;
    setIsLoading(true);
    audioFeedback.playTelemetry();
    setMessages(prev => [...prev, { role: 'user' as const, content: `[${action.label}] ${action.prompt}`, action: action.key }]);
    addToolLog('user', `Operator action: ${action.label}`);
    addToolLog('llm', `Calling ${action.endpoint.split('/').pop()}...`, 'pending');
    try {
      const res = await fetch(action.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(action.body()),
      });
      if (res.ok) {
        const data = await res.json();
        const summary = action.key === 'analyze'
          ? `🎯 Target: ${data.analysis?.target || '—'}\n🌀 Chakra: ${data.analysis?.primary_chakra || '—'}\n📡 Freq: ${data.analysis?.recommended_frequency || '—'} Hz\n🕉️ Mantra: ${data.analysis?.recommended_mantra_tradition || '—'}`
          : action.key === 'rates'
            ? `📊 ${(data.rates || []).map((r: Record<string, unknown>, i: number) => `${i + 1}. ${r.name || 'Rate ' + (i + 1)} → ${Array.isArray(r.values) ? (r.values as unknown[]).join('-') : r.values}`).join('\n')}`
            : data.insight || JSON.stringify(data);
        setMessages(prev => [...prev, { role: 'assistant' as const, content: summary, action: action.key }]);
        addToolLog('llm', `${action.label} complete`, 'success');
      } else {
        setMessages(prev => [...prev, { role: 'assistant' as const, content: 'Operator service unavailable.', action: 'error' }]);
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant' as const, content: 'Unable to reach operator.', action: 'error' }]);
    }
    setIsLoading(false);
  }

  return (
    <div className="h-full flex flex-col gap-4 p-4 md:p-6 overflow-hidden">
      <PageHeader
        icon={<Sparkles className="w-7 h-7 text-purple-400" />}
        title="Command Center"
        subtitle="Issue intentions, monitor broadcasts, and orchestrate the unified system."
      />

      {/* Saka Dawa Banner */}
      <SakaDawaBanner sakaDawa={sakaDawa} />

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        
        {/* Left Column: Chat and Commands */}
      <Card className="flex-1 flex flex-col min-h-0 bg-gray-900/80 border-purple-500/20 overflow-hidden" styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', flex: 1 } }}>
        
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-purple-900/40 via-indigo-900/40 to-blue-900/40 p-4 border-b border-white/10 flex justify-between items-center">
          <Space size={12}>
            <Badge status={isConnected ? 'processing' : 'error'} color={isConnected ? 'purple' : 'red'} />
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide" style={{ margin: 0 }}>AI Command Center</h2>
              <p className="text-xs text-purple-300" style={{ margin: 0 }}>Vajra.Stream Digital Operator v1.2</p>
            </div>
          </Space>
          <Tag
            color={isConnected ? 'purple' : 'red'}
            icon={<Cpu style={{ width: 12, height: 12 }} />}
            className="font-mono text-[10px]"
          >
            {isConnected ? 'LLM AGENT ACTIVE' : 'LLM AGENT OFFLINE'}
          </Tag>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`
                max-w-[85%] rounded-xl px-4 py-3 shadow-lg
                ${msg.role === 'user'
                  ? 'bg-gradient-to-br from-purple-600/90 to-indigo-700/95 text-white rounded-br-none border border-purple-400/20 shadow-[0_4px_12px_rgba(138,43,226,0.3)]'
                  : 'bg-purple-950/25 backdrop-blur-md text-gray-100 rounded-bl-none border border-purple-500/20 shadow-[0_4px_12px_rgba(0,0,0,0.3)]'
                }
              `}>
                <div className="markdown-container">
                  <RichMarkdownRenderer content={msg.content} />
                </div>
                {msg.role === 'assistant' && msg.toolCalls && (
                  <RenderMessageWidgets toolCalls={msg.toolCalls} onZoomItemClick={setActiveZoomItem} />
                )}
                {msg.role === 'assistant' && msg.isError && msg.retryInput && (
                  <div className="mt-2 pt-2 border-t border-red-500/20">
                    <button
                      type="button"
                      onClick={() => {
                        setMessages(prev => prev.filter((_, i) => i !== index));
                        handleSendMessage(msg.retryInput!);
                      }}
                      disabled={isLoading}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono text-red-300 border border-red-500/30 hover:bg-red-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <RotateCcw style={{ width: 11, height: 11 }} />
                      Retry
                    </button>
                  </div>
                )}
                {msg.role === 'assistant' && index > 0 && !msg.isError && (
                  <MessageControls
                    msg={msg}
                    disabled={isLoading}
                    modelOptions={buildModelOptions()}
                    providerHealth={providerHealth}
                    onRegenerate={(model) => handleRegenerate(index, model)}
                  />
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-purple-950/25 backdrop-blur-md rounded-xl rounded-bl-none px-4 py-3 border border-purple-500/20 shadow-lg flex items-center space-x-3">
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-[11px] font-mono text-purple-300/80">Generating...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />

          {messages.length <= 1 && !isLoading && (
            <div className="flex flex-col items-center justify-center flex-1 pb-8 px-4">
              <p className="text-[10px] font-mono uppercase tracking-widest text-purple-400/40 mb-4">Suggested Intentions</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full">
                {[
                  { icon: '🌿', label: 'Generate a healing blessing', text: 'Generate a healing blessing narrative for all beings suffering from illness' },
                  { icon: '🛡️', label: 'Cast protection ritual', text: 'Create a protection ritual to shield against negative forces' },
                  { icon: '☯️', label: 'Consult the I Ching', text: 'Cast the I Ching and interpret the hexagram for my current situation' },
                  { icon: '📿', label: 'Compose a dharani', text: 'Compose a dharani for purification of all obscurations' },
                ].map((s) => (
                  <button
                    key={s.label}
                    type="button"
                    onClick={() => { setInput(s.text); audioFeedback.playClick(); }}
                    className="flex items-center gap-3 p-3 rounded-xl bg-purple-950/20 border border-purple-500/15 hover:border-purple-500/40 hover:bg-purple-900/20 transition-all duration-200 text-left group"
                  >
                    <span className="text-xl flex-shrink-0">{s.icon}</span>
                    <span className="text-xs text-gray-400 group-hover:text-purple-200 transition-colors">{s.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Quick Suggestion Chips */}
        <div className="px-4 py-2 bg-gray-950/20 border-t border-white/5 overflow-x-auto">
          <Space wrap size={[4, 4]}>
            {quickCommands.map((cmd) => (
              <Button
                key={cmd.label}
                size="small"
                type="default"
                ghost
                disabled={isLoading}
                onClick={() => handleSendMessage(cmd.text)}
                style={{ fontSize: '11px', borderRadius: '12px' }}
              >
                {cmd.label}
              </Button>
            ))}
          </Space>
        </div>

        {/* Operator Quick Actions */}
        <div className="px-4 py-1.5 bg-gradient-to-r from-indigo-950/30 to-purple-950/20 border-t border-indigo-500/15">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[9px] font-mono text-indigo-300/70 uppercase tracking-wider">Operator</span>
            <Space wrap size={[4, 4]}>
              {operatorActions.map((action) => (
                <Button
                  key={action.key}
                  size="small"
                  type="default"
                  disabled={isLoading}
                  onClick={() => handleOperatorAction(action)}
                  style={{
                    fontSize: '10px',
                    borderRadius: '12px',
                    background: 'rgba(99, 102, 241, 0.08)',
                    borderColor: 'rgba(99, 102, 241, 0.3)',
                    color: '#a5b4fc',
                  }}
                >
                  <span className="mr-1">{action.icon}</span>{action.label}
                </Button>
              ))}
            </Space>
          </div>
        </div>

        {/* LLM Environmental Context Injection Panel */}
        <div className="px-4 py-2 border-t border-purple-500/15 bg-black/30 flex flex-wrap items-center gap-4 text-xs font-mono select-none">
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Inject Context:</span>
          
          <Space size={8} wrap>
            <Space size={4}>
              <Switch size="small" checked={includeAstrology} onChange={(v) => { setIncludeAstrology(v); audioFeedback.playClick(); }} />
              <span className="text-gray-400 text-[11px]">🪐 Astrology</span>
            </Space>
            <Space size={4}>
              <Switch size="small" checked={includeAnatomy} onChange={(v) => { setIncludeAnatomy(v); audioFeedback.playClick(); }} />
              <span className="text-gray-400 text-[11px]">💚 Chakras</span>
            </Space>
            <Space size={4}>
              <Switch size="small" checked={includeHardware} onChange={(v) => { setIncludeHardware(v); audioFeedback.playClick(); }} />
              <span className="text-gray-400 text-[11px]">⚙️ Metrics</span>
            </Space>
          </Space>

          <Space size={4} style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: 16 }}>
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Model:</span>
            <Select
              size="small"
              value={selectedModel || 'auto'}
              onChange={(val: string) => { setSelectedModel(val); audioFeedback.playClick(); }}
              style={{ minWidth: 160, fontSize: '11px' }}
              className="font-mono"
              styles={{ popup: { minWidth: 260 } }}
              placeholder="Select model..."
              showSearch
              optionFilterProp="label"
              options={buildModelOptions()}
            />
          </Space>

          {providerHealth.length > 0 && (
            <Tooltip
              title={
                <div className="text-[10px] font-mono space-y-0.5">
                  {providerHealth.map(ph => (
                    <div key={ph.provider} className="flex items-center gap-1">
                      <span style={{ color: ph.healthy ? '#52c41a' : '#ff4d4f' }}>
                        {ph.healthy ? '●' : '○'}
                      </span>
                      <span>{ph.provider}</span>
                      {ph.latency_ms != null && <span className="text-gray-400">{Math.round(ph.latency_ms)}ms</span>}
                    </div>
                  ))}
                </div>
              }
            >
              <span className="text-[10px] font-mono text-gray-500 flex items-center gap-1 cursor-help">
                <Activity style={{ width: 10, height: 10 }} />
                {providerHealth.filter(p => p.healthy).length}/{providerHealth.length} providers
              </span>
            </Tooltip>
          )}

          <Space size={4} style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: 16 }}>
            <Switch size="small" checked={debugMode} onChange={(v) => { setDebugMode(v); audioFeedback.playClick(); }} />
            <span className="text-yellow-500/95 font-bold text-[11px]">🛠️ Debug</span>
          </Space>
        </div>

        {/* Input Bar */}
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
          className="p-4 border-t border-purple-500/15 bg-black/40"
        >
          <Space.Compact style={{ width: '100%' }}>
            <Input
              value={input}
              onChange={(e) => { setInput(e.target.value); audioFeedback.playType(); }}
              disabled={isLoading}
              placeholder="Instruct the system..."
              className="bg-gray-900 border-purple-500/30 text-white placeholder:text-purple-300/40"
              style={{ flex: 1 }}
            />
            {isLoading ? (
              <Button
                danger
                icon={<Square style={{ width: 16, height: 16 }} />}
                onClick={handleCancelGeneration}
                style={{ display: 'flex', alignItems: 'center' }}
              >
                Stop
              </Button>
            ) : (
              <Button
                type="primary"
                htmlType="submit"
                disabled={!input.trim()}
                icon={<Send style={{ width: 16, height: 16 }} />}
                style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)', border: 'none', display: 'flex', alignItems: 'center' }}
              >
                Send
              </Button>
            )}
          </Space.Compact>
        </form>

      </Card>

      {/* Right Column: Status & Tool execution logs */}
      <div className="w-full lg:w-80 flex flex-col gap-6 h-full min-h-0 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">

        {/* Status Monitors Card */}
        <SystemMonitorsCard
          auraCoherence={auraCoherence}
          isConnected={isConnected}
          isPlaying={isPlaying}
          frequency={frequency}
          crystalStatus={crystalStatus}
          scalarStatus={scalarStatus}
          sessions={sessions}
        />

        {/* Tool Execution / LLM Debug Logs (Terminal UI) */}
        <LogsCard
          activeLogTab={activeLogTab}
          toolLogs={toolLogs}
          debugPayload={debugPayload}
          logEndRef={logEndRef}
          onTabChange={setActiveLogTab}
          onClearLogs={() => setToolLogs([])}
          onResetDebug={() => setDebugPayload(null)}
        />

      </div>
    </div>

      {/* Zoom Modal */}
      <ZoomModal activeZoomItem={activeZoomItem} onClose={() => setActiveZoomItem(null)} />

    </div>
  );
}

interface MessageControlsProps {
  msg: ChatMessage;
  disabled: boolean;
  modelOptions: DefaultOptionType[];
  providerHealth?: ProviderHealthEntry[];
  onRegenerate: (model: string | null) => void;
}

function MessageControls({ msg, disabled, modelOptions, providerHealth = [], onRegenerate }: MessageControlsProps) {
  const [showDebug, setShowDebug] = useState(false);
  const [pickModel, setPickModel] = useState(false);
  const dbg = msg.debugInfo || {};
  const hasDebug = !!msg.debugInfo;

  const tokenPart = (msg.inputTokens != null && msg.outputTokens != null)
    ? `${msg.inputTokens}→${msg.outputTokens} tokens`
    : null;
  const latencyPart = msg.latencyMs != null ? `${(msg.latencyMs / 1000).toFixed(1)}s` : null;
  const costPart = msg.costUsd != null ? `$${msg.costUsd.toFixed(4)}` : null;

  const compactParts = [tokenPart, latencyPart, costPart].filter(Boolean);
  const compactLine = compactParts.length > 0 ? compactParts.join(' | ') : null;

  const msgProvider = msg.providerUsed || dbg.provider || dbg.provider_selected;
  const providerHealthEntry = msgProvider
    ? providerHealth.find(p => p.provider === msgProvider)
    : undefined;

  return (
    <div className="mt-2 pt-2 border-t border-white/5 flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          type="button"
          onClick={() => setShowDebug(v => !v)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono text-purple-300/80 hover:text-purple-200 hover:bg-purple-500/10 transition-colors"
          title="Toggle debug info"
        >
          🔧 Debug
        </button>

        <button
          type="button"
          onClick={() => setPickModel(v => !v)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono text-cyan-300/80 hover:text-cyan-200 hover:bg-cyan-500/10 transition-colors"
          title="Change model and regenerate"
          disabled={disabled}
        >
          {msg.modelUsed
            ? <span className="max-w-[160px] truncate">{msg.modelUsed}</span>
            : <span>Model</span>}
        </button>

        <button
          type="button"
          onClick={() => onRegenerate(null)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono text-emerald-300/80 hover:text-emerald-200 hover:bg-emerald-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          title="Regenerate with the same model"
          disabled={disabled}
        >
          🔄 Regenerate
        </button>

        {compactLine && (
          <span className="text-[9px] font-mono text-gray-500 ml-auto">{compactLine}</span>
        )}
      </div>

      {msg.modelUsed && (
        <div className="text-[9px] font-mono text-gray-600">
          Model: {msg.modelUsed}
          {msgProvider && providerHealthEntry && (
            <span style={{ color: providerHealthEntry.healthy ? '#52c41a' : '#ff4d4f' }}>
              {' '}({providerHealthEntry.healthy ? '✓' : '✗'} {msgProvider})
            </span>
          )}
          {compactLine && <span className="text-gray-500"> | {compactLine}</span>}
        </div>
      )}

      {pickModel && (
        <div className="bg-black/40 border border-white/10 rounded p-2">
          <div className="text-[10px] text-gray-400 mb-1 font-mono">
            Regenerate this message with a different model:
          </div>
          <Select
            size="small"
            showSearch
            placeholder="Pick a model..."
            style={{ width: '100%', fontSize: '11px' }}
            optionFilterProp="label"
            options={modelOptions}
            onChange={(val: string) => {
              setPickModel(false);
              onRegenerate(val);
            }}
          />
        </div>
      )}

      {showDebug && (
        <div className="bg-black/50 border border-yellow-500/20 rounded p-2 text-[10px] font-mono text-yellow-200/90 space-y-1 overflow-x-auto">
          <div><span className="text-yellow-500">model:</span> {msg.modelUsed || '—'}</div>
          <div><span className="text-yellow-500">provider:</span> {msgProvider || '—'}</div>
          {tokenPart && <div><span className="text-yellow-500">tokens:</span> {tokenPart}</div>}
          {latencyPart && <div><span className="text-yellow-500">latency:</span> {latencyPart}</div>}
          {costPart && <div><span className="text-yellow-500">cost:</span> {costPart}</div>}
          {dbg.finish_reason && <div><span className="text-yellow-500">finish:</span> {dbg.finish_reason}</div>}
          {dbg.reasoning_tokens != null && (
            <div><span className="text-yellow-500">reasoning_tokens:</span> {dbg.reasoning_tokens}</div>
          )}
          {providerHealth.length > 0 && (
            <div className="pt-1 mt-1 border-t border-yellow-500/10">
              <div className="text-yellow-500 mb-0.5">provider health:</div>
              {providerHealth.map(ph => (
                <div key={ph.provider} className="flex items-center gap-1">
                  <span style={{ color: ph.healthy ? '#52c41a' : '#ff4d4f' }}>
                    {ph.healthy ? '●' : '○'}
                  </span>
                  <span>{ph.provider}</span>
                  {ph.latency_ms != null && <span className="text-gray-400">{Math.round(ph.latency_ms)}ms</span>}
                  {ph.error && <span className="text-red-400 truncate">{ph.error}</span>}
                </div>
              ))}
            </div>
          )}
          {msg.reasoningContent && (
            <details className="mt-1">
              <summary className="cursor-pointer text-yellow-400/80 select-none">💭 Reasoning content</summary>
              <pre className="mt-1 whitespace-pre-wrap break-words text-yellow-100/70 max-h-60 overflow-y-auto">{msg.reasoningContent}</pre>
            </details>
          )}
          {!hasDebug && (
            <div className="text-gray-500 italic">
              No debug info — enable 🛠️ Debug mode in the env bar before sending to capture per-message details.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
