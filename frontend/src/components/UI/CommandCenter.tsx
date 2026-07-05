/**
 * Command Center — primary operator console for Vajra.Stream.
 *
 * Central hub for issuing text commands to the unified orchestrator.
 * Features a terminal-style input with command history, live WebSocket
 * status feed, MOPS throughput display, and quick-action buttons for
 * common radionics and blessing operations. The largest UI component
 * (~600 lines) — serves as the primary interaction surface.
 *
 * Layout (post-redesign):
 *   1. Compact status header  (Link / Audio / Crystal / Scalar pills)
 *   2. Sacred day banner       (SakaDawa — daily sacred context)
 *   3. Main 2-column grid      (AI chat | Cosmic + Field Readings)
 *   4. Collapsible bottom row  (Journey / Buddhas / Blessings / Logs)
 *
 * @component
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  Send, Terminal, Cpu, AlertTriangle, Wifi, Volume2, Diamond, Waves,
  ChevronDown,
  Sparkles, Shield, Compass, BookOpen, Clock, Play, Square, X, Sun
} from 'lucide-react';
import { Card, Input, Button, Select, Switch, Tag, Badge, Space, Statistic, message } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';

import { useWebSocket } from '../../hooks/useWebSocket';
import SakaDawaBanner from './SakaDawaBanner';
import JourneyCard from './JourneyCard';
import BuddhaContemplationWidget from './BuddhaContemplationWidget';
import { RenderMessageWidgets } from '../CommandCenter/RenderMessageWidgets';
import { RichMarkdownRenderer } from '../CommandCenter/RichMarkdownRenderer';
import { quickCommands, createOperatorActions } from '../CommandCenter/constants';
import SystemMonitorsCard from '../CommandCenter/SystemMonitorsCard';
import CosmicAlignmentCard from '../CommandCenter/CosmicAlignmentCard';
import LogsCard from '../CommandCenter/LogsCard';
import ZoomModal from '../CommandCenter/ZoomModal';
import { createLogger } from '../../utils/logger';

export default function CommandCenter({
  isConnected,
  isPlaying,
  frequency,
  crystalStatus,
  scalarStatus,
  sessions,
  buddhaStatus,
  sakaDawa
}) {
  const [activeZoomItem, setActiveZoomItem] = useState(null);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '🔮 **Vajra.Stream Command Center Ready**\n\nI am your AI operator. I can assist you with system calibration, crystal programming, automated population blessings, and scalar broadcasts. How shall we direct the intention today?'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [toolLogs, setToolLogs] = useState([
    {
      timestamp: new Date().toLocaleTimeString(),
      type: 'system',
      message: 'Quantum RNG & Attunement system online. Idle.'
    }
  ]);
  const [auraCoherence, setAuraCoherence] = useState(35);
  const { currentAstrology } = useWebSocket();
  const astroData = currentAstrology;
  const [includeAstrology, setIncludeAstrology] = useState(true);
  const [includeAnatomy, setIncludeAnatomy] = useState(true);
  const [includeHardware, setIncludeHardware] = useState(true);
  const [availableModels, setAvailableModels] = useState({ local: [], api: [], lm_studio: [] });
  const [selectedModel, setSelectedModel] = useState('');
  const [debugMode, setDebugMode] = useState(false);
  const [debugPayload, setDebugPayload] = useState(null);
  const [activeLogTab, setActiveLogTab] = useState('tools');
  const log = createLogger('CommandCenter');

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
          // Result populated by WebSocket CURRENT_ASTROLOGY broadcast (useWebSocket hook).
          // Fetch is retained for immediate data on first mount before WS push arrives.
          await res.json();
        }
      } catch (e) {
        // Live data is also pushed via WS CURRENT_ASTROLOGY — log on failure
        // so ops can see the degraded path, but don't toast (WS will recover).
        log.error('Failed to fetch live astrology on mount:', e);
      }
    };

    const fetchAstro = async () => {
      doFetch(DEFAULT_LAT, DEFAULT_LNG);
    };

    fetchAstro();
    // 15s HTTP polling removed — live updates now via WS CURRENT_ASTROLOGY (currentAstrology).
  }, []);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch(`/api/v1/llm/models`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'success') {
            setAvailableModels(data.available || { local: [], api: [], lm_studio: [] });
            const model = data.default_model || '';
            setSelectedModel(model);
          }
        }
      } catch (e) {
        log.error("Failed to fetch available models", e);
        message.error('Could not load available models — model selector may be empty.');
        audioFeedback.playError();
      }
    };
    fetchModels();
  }, []);

  // Ref to hold latest handleSendMessage (avoids stale closure in event listener)
  const handleSendMessageRef = useRef(handleSendMessage);
  handleSendMessageRef.current = handleSendMessage;

  // Listen for vajra:quick-command custom events (fired by SakaDawaBanner, etc.)
  useEffect(() => {
    const handler = (e) => {
      if (e.detail?.command) {
        setInput(e.detail.command);
        setTimeout(() => {
          handleSendMessageRef.current(e.detail.command);
        }, 200);
      }
    };
    window.addEventListener('vajra:quick-command', handler);
    return () => window.removeEventListener('vajra:quick-command', handler);
  }, []);

  const messagesEndRef = useRef(null);
  const logEndRef = useRef(null);

  // Dynamic Aura Coherence simulation
  // OPTIMIZATION: was 250ms (4×/sec re-renders of the entire CommandCenter
  // including SystemMonitorsCard + ScalarWaveVisualizer). Slowed to 1000ms
  // — the VU bar only changes by 1-2% per tick anyway, so 1Hz is plenty
  // for human perception.
  useEffect(() => {
    const interval = setInterval(() => {
      const active = isPlaying || Object.keys(sessions).length > 0;
      setAuraCoherence(prev => {
        const base = active ? 88 : 35;
        const range = active ? 8 : 10;
        const drift = base + Math.sin(Date.now() / 2000) * (range / 2) + Math.random() * (range / 2);
        return Math.min(100, Math.max(0, Math.round(drift)));
      });
    }, 1000);
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

  const addToolLog = (type, message, status = 'info') => {
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

  // Ref to hold latest messages (avoids stale closure in fetch body during
  // rapid successive sends — the functional setMessages at L216 is correct for
  // state, but the fetch body at L226 used the closure `messages` variable
  // which could miss messages added by an in-flight send).
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  async function handleSendMessage(textToSend) {
    const text = textToSend || input;
    if (!text.trim()) return;

    setInput('');
    setIsLoading(true);
    audioFeedback.playTelemetry();

    // Build the complete message list from the ref (always latest) so the
    // fetch body and the state update use the same source of truth.
    const allMessages = [...messagesRef.current, { role: 'user', content: text }];
    messagesRef.current = allMessages; // update synchronously for next call
    setMessages(allMessages);
    addToolLog('user', `User requested: "${text}"`);

    try {
      addToolLog('llm', 'Analyzing intent and planning operations...', 'pending');

      const chatResponse = await fetch(`/api/v1/llm/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: allMessages.map(m => ({
            role: m.role,
            content: m.content
          })),
          provider: "auto",
          model: selectedModel || null,
          include_astrology: includeAstrology,
          astrology_data: includeAstrology ? astroData : null,
          include_anatomy: includeAnatomy,
          include_hardware: includeHardware,
          debug_mode: debugMode
        })
      });

      if (!chatResponse.ok) {
        throw new Error(`Chat API error: ${chatResponse.statusText}`);
      }

      const data = await chatResponse.json();
      if (data.debug_info) {
        setDebugPayload(data.debug_info);
      } else {
        setDebugPayload(null);
      }

      // Process tool calls
      if (data.tool_calls && data.tool_calls.length > 0) {
        data.tool_calls.forEach(tc => {
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

      // Add assistant response to state
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          toolCalls: data.tool_calls
        }
      ]);

    } catch (error) {
      log.error('Chat error:', error);
      addToolLog('system', `Error: ${error.message}`, 'error');
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ **Operator Error**: Connection failure or API request blocked. Switched to standby mode. \n\nError details: \`${error.message}\``
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const operatorActions = createOperatorActions({ frequency, isPlaying, sessions, crystalStatus, scalarStatus });

  async function handleOperatorAction(action) {
    if (isLoading) return;
    setIsLoading(true);
    audioFeedback.playTelemetry();
    setMessages(prev => [...prev, { role: 'user', content: `[${action.label}] ${action.prompt}`, action: action.key }]);
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
            ? `📊 ${(data.rates || []).map((r, i) => `${i + 1}. ${r.name || 'Rate ' + (i + 1)} → ${Array.isArray(r.values) ? r.values.join('-') : r.values}`).join('\n')}`
            : data.insight || JSON.stringify(data);
        setMessages(prev => [...prev, { role: 'assistant', content: summary, action: action.key }]);
        addToolLog('llm', `${action.label} complete`, 'success');
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Operator service unavailable.', action: 'error' }]);
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Unable to reach operator.', action: 'error' }]);
    }
    setIsLoading(false);
  }

  const activeSessionCount = Object.keys(sessions).length;

  return (
    <div className="h-full flex flex-col gap-4 p-4 md:p-6 overflow-hidden">

      {/* ============================================================
          COMPACT STATUS HEADER — at-a-glance system vitals as pills
          Replaces the full Link / Audio / Crystal status rows that
          used to live inside SystemMonitorsCard. Keeps the operator
          informed of system liveness without crowding the page.
      ============================================================= */}
      <div className="flex flex-wrap items-center gap-2 px-3 py-2 rounded-lg bg-gray-950/60 backdrop-blur-sm border border-white/5">
        <span className="text-[10px] font-mono uppercase tracking-wider text-gray-500 mr-1">status</span>

        {/* Link Status — websocket connectivity */}
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[10px] font-bold rounded-full border ${
          isConnected
            ? 'bg-green-950/80 border-green-500/30 text-green-400'
            : 'bg-red-950/80 border-red-500/30 text-red-400'
        }`}>
          <Wifi className="w-3 h-3" />
          {isConnected ? 'LINK LIVE' : 'LINK OFFLINE'}
        </span>

        {/* Audio Carrier — frequency generator running state */}
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[10px] font-bold rounded-full border font-mono ${
          isPlaying
            ? 'bg-cyan-950/80 border-cyan-500/30 text-cyan-400 animate-pulse'
            : 'bg-gray-800/80 border-white/10 text-gray-400'
        }`}>
          <Volume2 className="w-3 h-3" />
          {isPlaying ? `${frequency.toFixed(1)} HZ` : 'AUDIO IDLE'}
        </span>

        {/* Crystal Broadcaster — programming status */}
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[10px] font-bold rounded-full border ${
          crystalStatus?.is_programmed
            ? 'bg-yellow-950/80 border-yellow-500/30 text-yellow-400'
            : 'bg-gray-800/80 border-white/10 text-gray-400'
        }`}>
          <Diamond className="w-3 h-3" />
          {crystalStatus?.is_programmed ? 'CRYSTAL PROGRAMMED' : 'CRYSTAL STANDBY'}
        </span>

        {/* Scalar Array Rate — kept here so all 4 link/carrier/crystal/scalar
            indicators live in one row; ScalarRate is also still shown inside
            the Field Readings card for the full scalar context. */}
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[10px] font-bold rounded-full border bg-indigo-950/80 border-indigo-500/30 text-indigo-300 font-mono">
          <Waves className="w-3 h-3" />
          SCALAR {scalarStatus?.rate || '0.00 / 0.00'}
        </span>
      </div>

      {/* Sacred Day Banner — daily sacred-practice context */}
      <SakaDawaBanner sakaDawa={sakaDawa} />

      {/* ============================================================
          MAIN 2-COLUMN GRID (above the fold)

          LEFT  — AI Operator Chat (primary interaction, largest element).
          RIGHT — Cosmic Alignment + Field Readings (daily + system context).
          On mobile (single column) the right column stacks below chat.
          On `lg:` (≥1024px) it splits with chat ~60% / sidebar ~40% via
          minmax so chat gets all remaining space while the sidebar stays
          between 320–384px.
      ============================================================= */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(20rem,24rem)] gap-4 min-h-0">

        {/* ---- Left: AI Operator Chat ---- */}
        <Card
          className="h-full flex flex-col min-h-0 bg-gray-900/80 border-purple-500/20 overflow-hidden"
          styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', flex: 1 } }}
        >

          {/* Chat Header */}
          <div className="bg-gradient-to-r from-purple-900/40 via-indigo-900/40 to-blue-900/40 p-4 border-b border-white/10 flex justify-between items-center">
            <Space size={12}>
              <Badge status="processing" color="purple" />
              <div>
                <h2 className="text-lg font-bold text-white tracking-wide" style={{ margin: 0 }}>AI Command Center</h2>
                <p className="text-xs text-purple-300" style={{ margin: 0 }}>Vajra.Stream Digital Operator v1.2</p>
              </div>
            </Space>
            <Tag color="purple" icon={<Cpu style={{ width: 12, height: 12 }} />} className="font-mono text-[10px]">
              LLM AGENT ACTIVE
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
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-purple-950/25 backdrop-blur-md rounded-xl rounded-bl-none px-4 py-3 border border-purple-500/20 shadow-lg flex items-center space-x-2">
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
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
                value={selectedModel || undefined}
                onChange={(val) => { setSelectedModel(val); audioFeedback.playClick(); }}
                style={{ minWidth: 160, fontSize: '11px' }}
                className="font-mono"
                styles={{ popup: { minWidth: 220 } }}
                placeholder="Select model..."
              >
                {availableModels.lm_studio && availableModels.lm_studio.length > 0 && (
                  <Select.OptGroup label="LM Studio (Active)">
                    {availableModels.lm_studio.map(m => (
                      <Select.Option key={`lm_studio:${m}`} value={`lm_studio:${m}`}>{m}</Select.Option>
                    ))}
                  </Select.OptGroup>
                )}
                {availableModels.local && availableModels.local.length > 0 && (
                  <Select.OptGroup label="Local GGUF">
                    {availableModels.local.map(m => (
                      <Select.Option key={`local:${m}`} value={`local:${m}`}>{m}</Select.Option>
                    ))}
                  </Select.OptGroup>
                )}
                {availableModels.api && availableModels.api.length > 0 && (
                  <Select.OptGroup label="API Providers">
                    {availableModels.api
                      .map(m => {
                        // Backend returns strings shaped "provider_name (default_model)".
                        // Parse both pieces directly so every registered provider
                        // (openrouter, z_ai, minimax, deepseek, anthropic, openai, ...)
                        // routes to itself; never fall through to OpenAI.
                        const match = m.match(/^([a-zA-Z0-9_-]+)\s*\(([^)]+)\)\s*$/);
                        if (!match) return null;
                        const providerVal = match[1];
                        const defaultName = match[2];
                        const value = `${providerVal}:${defaultName}`;
                        return (
                          <Select.Option key={value} value={value}>{m}</Select.Option>
                        );
                      })
                      .filter((node): node is React.ReactElement => node !== null)}
                  </Select.OptGroup>
                )}
              </Select>
            </Space>

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
              <Button
                type="primary"
                htmlType="submit"
                disabled={isLoading || !input.trim()}
                icon={<Send style={{ width: 16, height: 16 }} />}
                style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)', border: 'none', display: 'flex', alignItems: 'center' }}
              >
                Send
              </Button>
            </Space.Compact>
          </form>

        </Card>

        {/* ---- Right: Cosmic Alignment + Field Readings ----
            Cosmic Alignment is the first card (daily-context above the
            fold). Field Readings sits below — keeps scalar / aura /
            attunement widgets one click away without crowding chat.    */}
        <div className="flex flex-col gap-4 min-h-0 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
          <CosmicAlignmentCard astroData={astroData} />
          <SystemMonitorsCard
            auraCoherence={auraCoherence}
            scalarStatus={scalarStatus}
          />
        </div>
      </div>

      {/* ============================================================
          COLLAPSIBLE PRACTICE + OPERATIONS PANEL

          Single row of 4 collapsible <details> panels. Closed by
          default so the page feels calm on first paint; user expands
          only what they need. Sequence on mobile: 1 column. On `md:`
          (≥768px): 2 columns, 2 rows. Each panel collapses inline so
          the main grid never gets pushed off-screen.

          Reused existing components (JourneyCard, BuddhaContemplationWidget,
          LogsCard). Active Blessing Rotations is rendered inline (sessions
          are still passed as a CommandCenter prop — no new component file).
      ============================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">

        {/* --- Character Journey --- */}
        <details className="bg-gray-900/70 border border-white/5 rounded-xl overflow-hidden backdrop-blur-sm group">
          <summary className="list-none [&::-webkit-details-marker]:hidden cursor-pointer flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors">
            <div className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-medium text-white tracking-wide">CHARACTER JOURNEY</span>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-500 transition-transform group-open:rotate-180" />
          </summary>
          <div className="border-t border-white/5">
            <JourneyCard />
          </div>
        </details>

        {/* --- 88 Buddhas Contemplation --- */}
        <details className="bg-gray-900/70 border border-white/5 rounded-xl overflow-hidden backdrop-blur-sm group">
          <summary className="list-none [&::-webkit-details-marker]:hidden cursor-pointer flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-yellow-400" />
              <span className="text-sm font-medium text-white tracking-wide">88 BUDDHAS CONTEMPLATION</span>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-500 transition-transform group-open:rotate-180" />
          </summary>
          <div className="border-t border-white/5">
            <BuddhaContemplationWidget buddhaStatus={buddhaStatus} />
          </div>
        </details>

        {/* --- Active Blessing Rotations (inline sessions list) ---
            Rendered directly in CommandCenter so we don't create a new
            component file — sessions prop continues to flow in from
            App.tsx (unchanged data flow). */}
        <details className="bg-gray-900/70 border border-white/5 rounded-xl overflow-hidden backdrop-blur-sm group">
          <summary className="list-none [&::-webkit-details-marker]:hidden cursor-pointer flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors">
            <div className="flex items-center gap-2">
              <Play className="w-4 h-4 text-green-400" />
              <span className="text-sm font-medium text-white tracking-wide">ACTIVE BLESSING ROTATIONS</span>
              <span className="text-[10px] font-mono text-gray-500">({activeSessionCount})</span>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-500 transition-transform group-open:rotate-180" />
          </summary>
          <div className="p-3 border-t border-white/5 max-h-48 overflow-y-auto">
            {activeSessionCount > 0 ? (
              <div className="space-y-1.5">
                {Object.values(sessions).map(session => (
                  <div
                    key={session.id}
                    className="flex justify-between items-center text-xs bg-white/5 px-3 py-2 rounded-lg border border-white/5"
                  >
                    <span className="text-purple-300 truncate max-w-[70%]">{session.name}</span>
                    <span className="text-[10px] bg-green-950 text-green-400 border border-green-500/30 px-1.5 py-0.2 rounded-full uppercase font-bold">
                      {session.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-gray-500 italic px-3 py-2">No operations active</div>
            )}
          </div>
        </details>

        {/* --- System Logs (TOOLS / LLM DEBUG tabs) ---
            LogsCard owns the TOOLS+DEBUG tab UI. Wrapping it in <details>
            keeps both terminal panels out of the way until the operator
            wants to inspect tool calls or debug payloads.            */}
        <details className="bg-gray-900/70 border border-white/5 rounded-xl overflow-hidden backdrop-blur-sm group">
          <summary className="list-none [&::-webkit-details-marker]:hidden cursor-pointer flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span className="text-sm font-medium text-white tracking-wide">SYSTEM LOGS</span>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-500 transition-transform group-open:rotate-180" />
          </summary>
          <div className="border-t border-white/5">
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
        </details>
      </div>

      {/* Zoom Modal (chart/widget zoom overlay) */}
      <ZoomModal activeZoomItem={activeZoomItem} onClose={() => setActiveZoomItem(null)} />

    </div>
  );
}
