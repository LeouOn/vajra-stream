import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles, Send, Loader2, Info, Lightbulb, TrendingUp, Settings,
  HelpCircle, Zap, Target, Radio, Play, Plus, Check, Copy, Activity,
  Heart, Eye, Music, Wind
} from 'lucide-react';

import { API_BASE as BASE } from '../../utils/api';
const API_BASE = `${BASE}/operator`;

const QUICK_ACTIONS = [
  {
    id: 'analyze',
    label: 'Analyze Intention',
    icon: Target,
    placeholder: 'Describe your intention...',
    examples: [
      'Help my friend with chronic back pain',
      'Send peace to a conflict zone',
      'Balance my heart chakra',
      'Release fear and anxiety',
    ],
  },
  {
    id: 'rates',
    label: 'Suggest Rates',
    icon: Activity,
    placeholder: 'What condition or intention?',
    examples: [
      'liver detoxification',
      'emotional healing after loss',
      'inflammation and pain',
      'spiritual awakening',
    ],
  },
  {
    id: 'insight',
    label: 'Session Insight',
    icon: Eye,
    placeholder: 'Analyze current session...',
    examples: [
      'What do my current readings suggest?',
      'Should I adjust my frequency?',
      'Is now a good time to conclude?',
    ],
  },
  {
    id: 'chat',
    label: 'Ask Anything',
    icon: Sparkles,
    placeholder: 'Ask about radionics, frequencies...',
    examples: [
      'What frequency helps with meditation?',
      'Explain how scalar waves work',
      'Which mantra for purification?',
    ],
  },
];

const CHAKRA_ICONS = {
  muladhara: '🔴',
  svadhisthana: '🟠',
  manipura: '🟡',
  anahata: '🟢',
  vishuddha: '🔵',
  ajna: '🟣',
  sahasrara: '⚪',
};

const MODALITY_ICONS = {
  scalar_waves: Activity,
  radionics: Radio,
  chakra_balancing: Heart,
  meridian_clearing: Wind,
  blessing: Sparkles,
  sound_healing: Music,
  visualization: Eye,
};

const STREAM_URL = `${API_BASE}/stream`;

const LLMInsightsPanel = ({ sessions, crystalStatus, scalarStatus, frequency, isPlaying }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeAction, setActiveAction] = useState('chat');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [rateResults, setRateResults] = useState(null);
  const [copied, setCopied] = useState(null);
  const [liveInsight, setLiveInsight] = useState(null);
  const [streamConnected, setStreamConnected] = useState(false);
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  // ---- SSE live insight stream ----
  useEffect(() => {
    const connectStream = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const es = new EventSource(STREAM_URL);
      eventSourceRef.current = es;

      es.onopen = () => setStreamConnected(true);

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.insight && data.type !== 'idle') {
            setLiveInsight(data);
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        setStreamConnected(false);
        es.close();
        // Reconnect after 5 seconds
        setTimeout(connectStream, 5000);
      };
    };

    connectStream();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const buildSessionContext = () => ({
    currentFrequency: frequency,
    isPlaying,
    activeSessions: Object.values(sessions || {}).filter(s => s.status === 'running').length,
    crystalActive: crystalStatus?.active || false,
    scalarRate: scalarStatus?.rate || null,
  });

  const sendMessage = async (text, actionType = null) => {
    if (!text.trim()) return;

    const userMessage = { role: 'user', content: text, action: actionType || activeAction };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setAnalysisResult(null);
    setRateResults(null);

    const action = actionType || activeAction;

    try {
      let endpoint, body;

      switch (action) {
        case 'analyze':
          endpoint = `${API_BASE}/analyze`;
          body = { intention: text };
          break;
        case 'rates':
          endpoint = `${API_BASE}/suggest-rates`;
          body = { intention_or_condition: text, count: 5 };
          break;
        case 'insight':
          endpoint = `${API_BASE}/insights`;
          body = { session_context: buildSessionContext() };
          break;
        case 'chat':
        default:
          endpoint = `${API_BASE}/chat`;
          body = { message: text };
          break;
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (response.ok) {
        const data = await response.json();

        // Handle different response types
        if (action === 'analyze' && data.analysis) {
          setAnalysisResult(data);
          const assistantMessage = {
            role: 'assistant',
            content: formatAnalysis(data),
            action: 'analyze',
            data,
          };
          setMessages(prev => [...prev, assistantMessage]);
        } else if (action === 'rates' && data.rates) {
          setRateResults(data);
          const assistantMessage = {
            role: 'assistant',
            content: formatRates(data),
            action: 'rates',
            data,
          };
          setMessages(prev => [...prev, assistantMessage]);
        } else if (data.insight) {
          const assistantMessage = {
            role: 'assistant',
            content: data.insight,
            action,
          };
          setMessages(prev => [...prev, assistantMessage]);
        } else if (data.reply) {
          const assistantMessage = {
            role: 'assistant',
            content: data.reply,
            action: 'chat',
            toolResults: data.tool_results,
          };
          setMessages(prev => [...prev, assistantMessage]);
        } else {
          const assistantMessage = {
            role: 'assistant',
            content: JSON.stringify(data, null, 2),
            action,
          };
          setMessages(prev => [...prev, assistantMessage]);
        }
      } else {
        const errorMsg = {
          role: 'assistant',
          content: 'Sorry, the operator service is unavailable. Make sure the backend is running and an LLM is configured.',
          action: 'error',
        };
        setMessages(prev => [...prev, errorMsg]);
      }
    } catch (error) {
      console.error('Operator error:', error);
      const errorMsg = {
        role: 'assistant',
        content: 'Unable to connect to the operator. Is the backend running on port 8008?',
        action: 'error',
      };
      setMessages(prev => [...prev, errorMsg]);
    }

    setIsLoading(false);
  };

  const formatAnalysis = (data) => {
    const a = data.analysis || {};
    const chakraIcon = CHAKRA_ICONS[a.primary_chakra] || '✨';
    return `**Analysis Complete**\n\n${chakraIcon} **Target:** ${a.target || 'N/A'}\n📋 **Condition:** ${a.condition || 'N/A'}\n🌀 **Primary Chakra:** ${a.primary_chakra || 'N/A'}\n📡 **Recommended Frequency:** ${a.recommended_frequency || 'N/A'} Hz\n🕉️ **Mantra:** ${a.recommended_mantra_tradition || 'N/A'}\n💡 **Reasoning:** ${a.explanation || 'N/A'}`;
  };

  const formatRates = (data) => {
    const rates = data.rates || [];
    return `**Rate Suggestions** (source: ${data.source || 'unknown'})\n\n${rates.map((r, i) =>
      `${i + 1}. **${r.name || 'Rate ' + (i + 1)}** → \`${Array.isArray(r.values) ? r.values.join('-') : r.values}\`\n   ${r.description || r.reasoning || ''}`
    ).join('\n\n')}`;
  };

  const handleApplyRates = (rateEntry) => {
    const msg = `Apply rate ${Array.isArray(rateEntry.values) ? rateEntry.values.join('-') : rateEntry.values} for ${rateEntry.name || 'this intention'}`;
    setInput(msg);
    sendMessage(msg, 'chat');
  };

  const handleCopyRates = (rateEntry) => {
    const text = Array.isArray(rateEntry.values) ? rateEntry.values.join('-') : String(rateEntry.values);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(rateEntry.name || text);
      setTimeout(() => setCopied(null), 1500);
    });
  };

  const handleExampleClick = (example) => {
    sendMessage(example);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const getActionColor = (action) => {
    const colors = {
      analyze: 'from-purple-900/50 to-indigo-900/50 border-purple-500/30',
      rates: 'from-emerald-900/50 to-teal-900/50 border-emerald-500/30',
      insight: 'from-amber-900/50 to-orange-900/50 border-amber-500/30',
      chat: 'from-indigo-900/50 to-blue-900/50 border-indigo-500/30',
    };
    return colors[action] || colors.chat;
  };

  const activeQuickAction = QUICK_ACTIONS.find(a => a.id === activeAction);

  return (
    <div className="bg-gray-900 rounded-lg border border-indigo-500/30 overflow-hidden flex flex-col" style={{ maxHeight: 'calc(100vh - 200px)' }}>
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-900/50 to-purple-900/50 p-3 border-b border-indigo-500/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-bold text-indigo-300">Radionics Operator</h3>
            <span className="text-[10px] px-1.5 py-0.5 bg-indigo-950 rounded text-indigo-400 font-mono">AI</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setMessages([]);
                setAnalysisResult(null);
                setRateResults(null);
              }}
              className="text-xs text-gray-400 hover:text-white transition-colors"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* Action Tabs */}
      <div className="flex border-b border-gray-700 overflow-x-auto">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.id}
            onClick={() => setActiveAction(action.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors ${
              activeAction === action.id
                ? 'bg-indigo-900/40 text-indigo-300 border-b-2 border-indigo-400'
                : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
            }`}
          >
            <action.icon className="w-3.5 h-3.5" />
            {action.label}
          </button>
        ))}
      </div>

      {/* Live Streaming Insight Ticker */}
      {liveInsight && (
        <div className="px-3 py-2 bg-gradient-to-r from-emerald-900/20 to-teal-900/20 border-b border-emerald-500/10 flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${streamConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
          <div className="flex items-center gap-1.5 flex-1 min-w-0">
            <Activity className="w-3 h-3 text-emerald-400 flex-shrink-0" />
            <span className="text-xs text-emerald-300/80 truncate animate-fade-in">
              {liveInsight.insight}
            </span>
          </div>
          <span className="text-[10px] text-emerald-600 font-mono">
            {liveInsight.type === 'llm_generated' ? 'AI' : 'RULES'}
          </span>
        </div>
      )}

      {/* Examples for current action */}
      {activeQuickAction && messages.length === 0 && (
        <div className="p-3 bg-gray-800/30 border-b border-gray-700/50">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Try asking</div>
          <div className="flex flex-wrap gap-1.5">
            {activeQuickAction.examples.map((example, idx) => (
              <button
                key={idx}
                onClick={() => handleExampleClick(example)}
                className="text-xs px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white rounded-full transition-colors border border-gray-700/50"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Rate Suggestion Cards (shown after analysis/rates) */}
      {(analysisResult || rateResults) && (
        <div className="p-3 bg-gray-800/30 border-b border-gray-700/50 space-y-2 max-h-48 overflow-y-auto">
          {(rateResults?.rates || analysisResult?.suggested_rates || []).slice(0, 5).map((rate, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 bg-gray-800/80 rounded-lg border border-gray-700/50 hover:border-indigo-500/30 transition-colors group"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-cyan-400 font-bold">
                    {Array.isArray(rate.values) ? rate.values.join('-') : rate.values}
                  </span>
                  <span className="text-xs text-gray-400 truncate">{rate.name || rate.description || ''}</span>
                </div>
                {rate.reasoning && (
                  <div className="text-[10px] text-gray-500 mt-0.5 truncate">{rate.reasoning}</div>
                )}
              </div>
              <div className="flex items-center gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleCopyRates(rate)}
                  className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
                  title="Copy rate"
                >
                  {copied === (rate.name || String(rate.values)) ? (
                    <Check className="w-3.5 h-3.5 text-green-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
                <button
                  onClick={() => handleApplyRates(rate)}
                  className="p-1 hover:bg-indigo-700 rounded text-gray-400 hover:text-indigo-300 transition-colors"
                  title="Apply this rate"
                >
                  <Play className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-[200px]">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Sparkles className="w-10 h-10 mx-auto mb-3 text-gray-600" />
            <p className="text-sm text-gray-500 max-w-xs mx-auto">
              I can analyze intentions, suggest radionics rates, interpret session readings, and answer questions about sacred technology.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx}>
            <div
              className={`rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-indigo-900/30 ml-6 border border-indigo-500/30'
                  : 'bg-gray-800 mr-6 border border-gray-700'
              }`}
            >
              <div className="text-[10px] mb-1.5 flex items-center gap-1.5">
                <span className={msg.role === 'user' ? 'text-indigo-400' : 'text-cyan-400'}>
                  {msg.role === 'user' ? 'You' : 'Operator'}
                </span>
                {msg.action && (
                  <span className="text-gray-600">· {msg.action}</span>
                )}
              </div>
              <div className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                {msg.content}
              </div>

              {/* Tool results */}
              {msg.toolResults && msg.toolResults.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-700">
                  <div className="text-[10px] text-gray-500 mb-1">Tools executed:</div>
                  {msg.toolResults.map((tr, i) => (
                    <div key={i} className="text-xs text-gray-400 bg-gray-900/50 rounded px-2 py-1 mt-1 font-mono">
                      {tr.tool}: {JSON.stringify(tr.result).slice(0, 120)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-400 pl-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Operator is thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Modality Suggestions (when analysis is present) */}
      {analysisResult?.recommended_modalities && (
        <div className="px-3 py-2 bg-gray-800/30 border-t border-gray-700/50">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Suggested Modalities</div>
          <div className="flex flex-wrap gap-1.5">
            {(analysisResult.recommended_modalities || []).map((mod) => {
              const Icon = MODALITY_ICONS[mod] || Sparkles;
              return (
                <span key={mod} className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-950/40 border border-indigo-500/20 rounded text-[10px] text-indigo-300">
                  <Icon className="w-3 h-3" />
                  {mod.replace(/_/g, ' ')}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-gray-700 bg-gray-900/50">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={activeQuickAction?.placeholder || 'Ask the operator...'}
              className="w-full bg-gray-800 text-white text-sm pl-3 pr-8 py-2.5 rounded-lg border border-gray-600 focus:border-indigo-500 focus:outline-none placeholder-gray-500"
            />
            {input && (
              <button
                onClick={() => setInput('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isLoading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-700 text-white px-3 rounded-lg transition-colors flex items-center gap-1.5"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LLMInsightsPanel;
