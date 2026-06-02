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
import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, Terminal, Cpu, Activity, Wifi, AlertTriangle, 
  Sparkles, Shield, Compass, BookOpen, Clock, Play, Square, X, Moon, Sun
} from 'lucide-react';
import { Card, Input, Button, Select, Switch, Tag, Modal, Tabs, Badge, Space, Statistic } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';

import { API_BASE } from '../../utils/api';
import ScalarWaveVisualizer from '../2D/ScalarWaveVisualizer';
import { useWebSocket } from '../../hooks/useWebSocket';
import { AttunementChart } from './AttunementChart';
import SakaDawaBanner from './SakaDawaBanner';
import JourneyCard from './JourneyCard';
import BuddhaContemplationWidget from './BuddhaContemplationWidget';

const RenderMessageWidgets = ({ toolCalls, onZoomItemClick }) => {
  if (!toolCalls || toolCalls.length === 0) return null;
  
  return (
    <div className="mt-3 space-y-3 border-t border-white/5 pt-3">
      {toolCalls.map((tc, idx) => {
        if (tc.status !== 'success') return null;
        
        // 1. Forge Sigil Widget
        if (tc.tool_name === 'forge_sigil') {
          const sigil = tc.result;
          if (!sigil) return null;
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-cyan-500/20 space-y-3">
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase font-mono">
                <span>🔮 SIGIL FORGED</span>
              </div>
              <div className="text-xs text-gray-300 font-medium">
                Intention: <span className="text-white italic">"{sigil.intention}"</span>
              </div>
              <div className="flex gap-4 items-center">
                {/* SVG Kamea */}
                <div 
                  onClick={() => onZoomItemClick && onZoomItemClick({ 
                    type: 'sigil', 
                    title: 'Forged Sigil', 
                    intention: sigil.intention, 
                    svg: sigil.svg, 
                    ai_image: sigil.ai_image 
                  })}
                  className="w-24 h-24 bg-gray-950 rounded-lg p-1 border border-white/5 flex items-center justify-center cursor-zoom-in hover:border-cyan-400 hover:scale-105 transition-all duration-300"
                >
                  <div dangerouslySetInnerHTML={{ __html: sigil.svg }} className="w-full h-full" />
                </div>
                {/* AI image if generated */}
                {sigil.ai_image && (
                  <div 
                    onClick={() => onZoomItemClick && onZoomItemClick({ 
                      type: 'sigil_ai', 
                      title: 'AI Sigil Image', 
                      intention: sigil.intention, 
                      ai_image: sigil.ai_image 
                    })}
                    className="w-24 h-24 bg-gray-950 rounded-lg p-1 border border-white/5 overflow-hidden flex items-center justify-center cursor-zoom-in hover:border-cyan-400 hover:scale-105 transition-all duration-300"
                  >
                    <img src={sigil.ai_image} alt="AI Sigil" className="w-full h-full object-cover rounded-md" />
                  </div>
                )}
              </div>
            </div>
          );
        }
        
        // 2. Tarot Spread Widget
        if (tc.tool_name === 'cast_tarot_spread') {
          const cards = tc.result?.cards || [];
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-purple-500/20 space-y-3">
              <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold uppercase font-mono">
                <span>🃏 TAROT CARDS DRAWN</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {cards.map((card, cidx) => (
                  <div 
                    key={card.id} 
                    onClick={() => onZoomItemClick && onZoomItemClick({ 
                      type: 'tarot', 
                      title: card.name, 
                      svg: card.svg, 
                      card: card 
                    })}
                    className="bg-gray-950/80 p-2.5 rounded-lg border border-white/5 flex flex-col items-center hover:border-purple-500/50 hover:scale-105 cursor-zoom-in transition-all duration-300"
                  >
                    <div dangerouslySetInnerHTML={{ __html: card.svg }} className="divination-card-container w-20 h-32 flex justify-center" />
                    <span className="text-[10px] text-gray-400 font-bold mt-2 truncate max-w-full text-center">{card.name}</span>
                    <span className="text-[8px] text-purple-300 italic truncate max-w-full text-center">{card.orientation.toUpperCase()}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        }
        
        // 3. I Ching Widget
        if (tc.tool_name === 'cast_i_ching') {
          const cast = tc.result;
          if (!cast) return null;
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-cyan-500/20 space-y-3">
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase font-mono">
                <span>☯️ I CHING HEXAGRAM CAST</span>
              </div>
              <div 
                onClick={() => onZoomItemClick && onZoomItemClick({ 
                  type: 'iching', 
                  title: 'I Ching Hexagram', 
                  svg: cast.svg, 
                  cast: cast 
                })}
                className="flex flex-col sm:flex-row gap-4 items-center cursor-zoom-in hover:bg-white/5 p-2 rounded-lg transition-all duration-300"
              >
                <div dangerouslySetInnerHTML={{ __html: cast.svg }} className="divination-card-container w-full max-w-[200px]" />
                <div className="flex-1 text-xs space-y-1.5 text-gray-300">
                  <div>
                    <span className="font-bold text-white block">Primary: {cast.primary?.name}</span>
                    <span className="text-[10px] italic">{cast.primary?.meaning}</span>
                  </div>
                  {cast.has_changes && (
                    <div className="pt-1.5 border-t border-white/5">
                      <span className="font-bold text-purple-300 block">Relating: {cast.relating?.name}</span>
                      <span className="text-[10px] italic">{cast.relating?.meaning}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        }
        
        // 4. Geomancy Widget
        if (tc.tool_name === 'cast_geomancy') {
          const chart = tc.result;
          if (!chart) return null;
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-yellow-500/20 space-y-3">
              <div className="flex items-center gap-2 text-yellow-400 text-xs font-semibold uppercase font-mono">
                <span>👁 GEOMANTIC SHIELD CAST</span>
              </div>
              <div 
                onClick={() => onZoomItemClick && onZoomItemClick({ 
                  type: 'geomancy', 
                  title: 'Geomantic Shield', 
                  svg: chart.svg, 
                  chart: chart 
                })}
                className="flex flex-col sm:flex-row gap-4 items-center cursor-zoom-in hover:bg-white/5 p-2 rounded-lg transition-all duration-300"
              >
                <div dangerouslySetInnerHTML={{ __html: chart.svg }} className="w-full max-w-[240px]" />
                <div className="flex-1 text-xs space-y-2 text-gray-300">
                  <div>
                    <span className="font-bold text-white block">The Judge: {chart.figures?.Judge?.name}</span>
                    <span className="text-[10px] italic">{chart.figures?.Judge?.meaning}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="px-2 py-0.5 bg-yellow-950 text-yellow-300 border border-yellow-500/20 rounded text-[9px] uppercase font-mono">
                      ELEMENT: {chart.figures?.Judge?.element}
                    </span>
                    <span className="px-2 py-0.5 bg-purple-950 text-purple-300 border border-purple-500/20 rounded text-[9px] uppercase font-mono">
                      RULER: {chart.figures?.Judge?.ruler}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        }
        
        return null;
      })}
    </div>
  );
};

const RichMarkdownRenderer = ({ content }) => {
  if (!content) return null;
  
  const lines = content.split('\n');
  const elements = [];
  let currentList = null; // { type: 'ul' | 'ol', items: [] }
  let inCodeBlock = false;
  let codeBlockLines = [];
  let codeBlockLang = '';

  const flushList = (key) => {
    if (currentList) {
      const Tag = currentList.type;
      const listKey = `list-${key}`;
      elements.push(
        <Tag key={listKey} className={currentList.type === 'ul' ? 'list-disc pl-5 space-y-1.5 my-2.5' : 'list-decimal pl-5 space-y-1.5 my-2.5'}>
          {currentList.items.map((item, idx) => (
            <li key={idx} className="text-gray-200 text-sm leading-relaxed">
              {renderInlineStyles(item)}
            </li>
          ))}
        </Tag>
      );
      currentList = null;
    }
  };

  const renderInlineStyles = (lineText) => {
    let parts = [lineText];
    
    // Bold: **text**
    parts = parts.flatMap(part => {
      if (typeof part !== 'string') return part;
      const subparts = part.split('**');
      return subparts.map((chunk, idx) => {
        if (idx % 2 === 1) {
          return <strong key={idx} className="text-purple-300 font-bold">{chunk}</strong>;
        }
        return chunk;
      });
    });

    // Inline code: `code`
    parts = parts.flatMap(part => {
      if (typeof part !== 'string') return part;
      const subparts = part.split('`');
      return subparts.map((chunk, idx) => {
        if (idx % 2 === 1) {
          return <code key={idx} className="bg-black/60 border border-white/10 px-1.5 py-0.5 rounded text-cyan-300 font-mono text-xs break-all [word-break:break-all] max-w-[200px] inline-block overflow-hidden text-ellipsis align-bottom">{chunk}</code>;
        }
        return chunk;
      });
    });

    // Italics: *text*
    parts = parts.flatMap(part => {
      if (typeof part !== 'string') return part;
      const subparts = part.split('*');
      if (subparts.length > 1 && subparts.length % 2 === 1) {
        return subparts.map((chunk, idx) => {
          if (idx % 2 === 1) {
            return <em key={idx} className="text-gray-300 italic">{chunk}</em>;
          }
          return chunk;
        });
      }
      return part;
    });

    return parts;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Handle code block
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        const blockKey = `code-${elements.length}-${i}`;
        elements.push(
          <pre key={blockKey} className="bg-black/80 border border-white/10 p-3 rounded-lg font-mono text-xs text-cyan-400 overflow-x-auto my-3 leading-normal">
            <code>{codeBlockLines.join('\n')}</code>
          </pre>
        );
        inCodeBlock = false;
        codeBlockLines = [];
      } else {
        flushList(i);
        inCodeBlock = true;
        codeBlockLang = line.replace('```', '').trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Handle headers
    if (line.startsWith('### ')) {
      flushList(i);
      const text = line.substring(4);
      elements.push(<h4 key={`h4-${i}`} className="text-sm font-bold text-white tracking-wide mt-3 mb-2">{renderInlineStyles(text)}</h4>);
      continue;
    }
    if (line.startsWith('## ')) {
      flushList(i);
      const text = line.substring(3);
      elements.push(<h3 key={`h3-${i}`} className="text-base font-bold text-white tracking-wider mt-4 mb-2">{renderInlineStyles(text)}</h3>);
      continue;
    }
    if (line.startsWith('# ')) {
      flushList(i);
      const text = line.substring(2);
      elements.push(<h2 key={`h2-${i}`} className="text-lg font-bold text-white tracking-widest mt-4 mb-2">{renderInlineStyles(text)}</h2>);
      continue;
    }

    // Handle blockquotes
    if (line.trim().startsWith('> ')) {
      flushList(i);
      const text = line.trim().substring(2);
      elements.push(
        <blockquote key={`bq-${i}`} className="border-l-4 border-purple-500/60 bg-purple-950/20 px-3 py-2 my-2 rounded-r-lg text-xs italic text-purple-200">
          {renderInlineStyles(text)}
        </blockquote>
      );
      continue;
    }

    // Handle unordered lists
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const text = line.trim().substring(2);
      if (!currentList || currentList.type !== 'ul') {
        flushList(i);
        currentList = { type: 'ul', items: [text] };
      } else {
        currentList.items.push(text);
      }
      continue;
    }

    // Handle ordered lists
    const olMatch = line.trim().match(/^(\d+)\.\s(.*)/);
    if (olMatch) {
      const text = olMatch[2];
      if (!currentList || currentList.type !== 'ol') {
        flushList(i);
        currentList = { type: 'ol', items: [text] };
      } else {
        currentList.items.push(text);
      }
      continue;
    }

    // Empty lines
    if (!line.trim()) {
      flushList(i);
      continue;
    }

    // Regular paragraph
    flushList(i);
    elements.push(
      <p key={`p-${i}`} className="mb-2 last:mb-0 text-gray-100 text-sm leading-relaxed">
        {renderInlineStyles(line)}
      </p>
    );
  }

  flushList(lines.length);

  return elements;
};

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
  const [astroData, setAstroData] = useState(null);
  const [includeAstrology, setIncludeAstrology] = useState(true);
  const [includeAnatomy, setIncludeAnatomy] = useState(true);
  const [includeHardware, setIncludeHardware] = useState(true);
  const [availableModels, setAvailableModels] = useState({ local: [], api: [], lm_studio: [] });
  const [selectedModel, setSelectedModel] = useState('');
  const [debugMode, setDebugMode] = useState(false);
  const [debugPayload, setDebugPayload] = useState(null);
  const [activeLogTab, setActiveLogTab] = useState('tools');
  
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
        
        const res = await fetch(`${API_BASE}/astrology/current?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          setAstroData(data.astrology);
        }
      } catch (e) {
        // Ignore
      }
    };

    // Default to San Francisco, CA — only use geolocation if user explicitly requests "use my location"
    const SF_LAT = 37.7749;
    const SF_LON = -122.4194;

    const fetchAstro = async () => {
      doFetch(SF_LAT, SF_LON);
    };
    
    fetchAstro();
    const interval = setInterval(fetchAstro, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch(`${API_BASE}/llm/models`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'success') {
            setAvailableModels(data.available || { local: [], api: [], lm_studio: [] });
            const model = data.default_model || '';
            setSelectedModel(model);
          }
        }
      } catch (e) {
        console.error("Failed to fetch available models", e);
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

  async function handleSendMessage(textToSend) {
    const text = textToSend || input;
    if (!text.trim()) return;

    setInput('');
    setIsLoading(true);
    audioFeedback.playTelemetry();

    // Add user message to state
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    addToolLog('user', `User requested: "${text}"`);

    try {
      addToolLog('llm', 'Analyzing intent and planning operations...', 'pending');
      
      const chatResponse = await fetch(`${API_BASE}/llm/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, { role: 'user', content: text }].map(m => ({
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
      console.error('Chat error:', error);
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

  const quickCommands = [
    { label: 'Start automation', text: 'start automation' },
    { label: 'Stop automation', text: 'stop automation' },
    { label: 'List populations', text: 'list populations' },
    { label: 'Start RNG session', text: 'start RNG session' },
    { label: 'Get statistics', text: 'get statistics' },
    { label: 'Dharma Wisdom', text: 'tell me a dharma tale' }
  ];

  return (
    <div className="h-full flex flex-col gap-4 p-4 md:p-6 overflow-hidden">
      {/* Saka Dawa Banner */}
      <SakaDawaBanner sakaDawa={sakaDawa} />

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        
        {/* Left Column: Chat and Commands */}
      <Card className="flex-1 flex flex-col min-h-0 bg-gray-900/80 border-purple-500/20 overflow-hidden" styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', flex: 1 } }}>
        
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
                  {availableModels.api.map(m => {
                    let providerVal = 'openai';
                    let defaultName = 'gpt-4o-mini';
                    if (m.toLowerCase().includes('deepseek')) {
                      providerVal = 'deepseek';
                      const match = m.match(/\(([^)]+)\)/);
                      defaultName = match ? match[1] : 'deepseek-chat';
                    } else if (m.toLowerCase().includes('anthropic')) {
                      providerVal = 'anthropic';
                      defaultName = 'claude-3-5-haiku-20241022';
                    } else if (m.toLowerCase().includes('openai')) {
                      providerVal = 'openai';
                      defaultName = 'gpt-4o-mini';
                    }
                    return (
                      <Select.Option key={`${providerVal}:${defaultName}`} value={`${providerVal}:${defaultName}`}>{m}</Select.Option>
                    );
                  })}
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

      {/* Right Column: Status & Tool execution logs */}
      <div className="w-full lg:w-80 flex flex-col gap-6 h-full min-h-0 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
        
        {/* Journey Card (Epic Multi-Stage Journey) */}
        <JourneyCard />

        {/* Buddha Contemplation Widget */}
        <BuddhaContemplationWidget buddhaStatus={buddhaStatus} />
        
        {/* Status Monitors Card */}
        <Card
          title={<span className="text-white text-sm tracking-wider font-bold"><Activity className="w-4 h-4 text-purple-400 inline mr-2" />SYSTEM MONITORS</span>}
          className="bg-gray-900/80 border-purple-500/20"
          styles={{ body: { padding: '16px' } }}
        >
          
          <div className="space-y-4">
            
            {/* Scalar Wave Interference Visualizer */}
            <div className="flex flex-col gap-1.5">
              <span className="text-xs text-gray-400 font-medium">Scalar Wave Field</span>
              <div className="h-20">
                <ScalarWaveVisualizer />
              </div>
            </div>

            {/* Aura Field Coherence VU Meter */}
            <div className="bg-white/5 p-3 rounded-lg border border-white/5">
              <div className="flex justify-between items-center text-xs text-gray-400 font-medium mb-1.5">
                <span>Aura Field Coherence</span>
                <span className="text-purple-400 font-mono font-bold animate-pulse">{auraCoherence}%</span>
              </div>
              <div className="flex gap-0.5 h-2.5 bg-black/60 rounded p-0.5 overflow-hidden border border-white/5">
                {Array.from({ length: 20 }).map((_, idx) => {
                  const threshold = (idx / 20) * 100;
                  const active = auraCoherence > threshold;
                  let color = "bg-purple-950";
                  if (active) {
                    if (idx < 12) color = "bg-purple-500 shadow-[0_0_4px_rgba(168,85,247,0.7)]";
                    else if (idx < 17) color = "bg-cyan-400 shadow-[0_0_4px_rgba(34,211,238,0.7)]";
                    else color = "bg-yellow-400 shadow-[0_0_4px_rgba(250,204,21,0.7)]";
                  }
                  return <div key={idx} className={`flex-1 rounded-sm transition-all duration-300 ${color}`} />;
                })}
              </div>
              <div className="flex justify-between text-[8px] text-gray-500 font-mono mt-1 select-none">
                <span>MIN (0.0)</span>
                <span>CALIBRATED (1.0)</span>
                <span>PEAK</span>
              </div>
            </div>

            {/* Live Attunement Metrics Chart */}
            <div className="mt-2">
              <AttunementChart />
            </div>

            {/* Connection Status */}
            <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
              <span className="text-xs text-gray-400 font-medium">Link Status</span>
              <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full flex items-center gap-1.5 ${
                isConnected 
                  ? 'bg-green-950/80 border border-green-500/30 text-green-400' 
                  : 'bg-red-950/80 border border-red-500/30 text-red-400'
              }`}>
                <Wifi className="w-3 h-3" />
                {isConnected ? 'LIVE CONNECTED' : 'OFFLINE'}
              </span>
            </div>

            {/* Freq generator status */}
            <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
              <span className="text-xs text-gray-400 font-medium">Audio Carrier</span>
              <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full flex items-center gap-1.5 ${
                isPlaying 
                  ? 'bg-cyan-950/80 border border-cyan-500/30 text-cyan-400 animate-pulse' 
                  : 'bg-gray-800/80 border border-white/10 text-gray-400'
              }`}>
                {isPlaying ? `${frequency.toFixed(1)} Hz` : 'INACTIVE'}
              </span>
            </div>

            {/* Crystal Broadcaster Grid status */}
            <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
              <span className="text-xs text-gray-400 font-medium">Crystal Broadcaster</span>
              <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
                crystalStatus?.is_programmed
                  ? 'bg-yellow-950/80 border border-yellow-500/30 text-yellow-400'
                  : 'bg-gray-800/80 border border-white/10 text-gray-400'
              }`}>
                {crystalStatus?.is_programmed ? 'PROGRAMMED' : 'STANDBY'}
              </span>
            </div>

            {/* Scalar status */}
            <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
              <span className="text-xs text-gray-400 font-medium">Scalar Array Rate</span>
              <span className="text-xs font-mono text-indigo-300 font-bold bg-indigo-950/40 px-2 py-0.5 border border-indigo-500/20 rounded">
                {scalarStatus?.rate || '0.00 / 0.00'}
              </span>
            </div>

            {/* Active session count */}
            <div className="bg-white/5 p-3 rounded-lg border border-white/5">
              <div className="text-xs text-gray-400 font-medium mb-2">Active Blessing Rotations</div>
              {Object.keys(sessions).length > 0 ? (
                <div className="space-y-1.5 max-h-24 overflow-y-auto">
                  {Object.values(sessions).map(session => (
                    <div key={session.id} className="flex justify-between items-center text-xs">
                      <span className="text-purple-300 truncate max-w-[70%]">{session.name}</span>
                      <span className="text-[10px] bg-green-950 text-green-400 border border-green-500/30 px-1.5 py-0.2 rounded-full uppercase">
                        {session.status}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-gray-500 italic">No operations active</div>
              )}
            </div>
          </div>

        </Card>

        {/* Cosmic Alignment Widget */}
        <Card
          title={<span className="text-white text-sm tracking-wider font-bold"><Moon className="w-4 h-4 text-cyan-400 inline mr-2" />COSMIC ALIGNMENT</span>}
          className="bg-gray-900/80 border-purple-500/20"
          styles={{ body: { padding: '16px' } }}
        >

          {astroData ? (
            <div className="space-y-4 text-xs">
              
              {/* Planetary Hour */}
              <div className="p-3 bg-yellow-950/20 border border-yellow-500/20 rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-yellow-400 font-mono tracking-wider block uppercase">PLANETARY HOUR</span>
                  <span className="text-sm font-bold text-white mt-0.5 block">{astroData.planetary_hours?.current_planetary_hour} hour</span>
                </div>
                <span className="text-xs font-mono text-gray-400">Day: {astroData.planetary_hours?.day_planet}</span>
              </div>

              {/* Vedic Panchang */}
              <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-xl space-y-1.5">
                <span className="text-[10px] text-purple-400 font-mono tracking-wider block uppercase">VEDIC PANCHANG</span>
                <div className="flex justify-between">
                  <span className="text-gray-400">Tithi:</span>
                  <span className="text-gray-200 font-bold">{astroData.indian?.panchanga?.tithi?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Nakshatra:</span>
                  <span className="text-gray-200 font-bold">{astroData.indian?.panchanga?.nakshatra?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Yoga:</span>
                  <span className={`font-bold ${astroData.indian?.panchanga?.yoga?.name === 'Vajra' ? 'text-yellow-300 animate-pulse glow-text' : 'text-gray-200'}`}>
                    {astroData.indian?.panchanga?.yoga?.name}
                  </span>
                </div>
              </div>

              {/* Chinese Pillar summary */}
              <div className="p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-xl space-y-1.5">
                <span className="text-[10px] text-cyan-400 font-mono tracking-wider block uppercase">CHINESE LUNAR</span>
                <div className="flex justify-between">
                  <span className="text-gray-400">Zodiac:</span>
                  <span className="text-gray-200 font-bold">{astroData.chinese?.zodiac_animal} (Year)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Lunar Date:</span>
                  <span className="text-gray-200 font-bold">Month {astroData.chinese?.lunar_date?.month} Day {astroData.chinese?.lunar_date?.day}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Shichen:</span>
                  <span className="text-gray-200 font-bold">{astroData.chinese?.shichen?.name} ({astroData.chinese?.shichen?.branch})</span>
                </div>
              </div>

            </div>
          ) : (
            <div className="text-xs text-gray-500 italic py-2 text-center">Tuning astronomical clocks...</div>
          )}
        </Card>

        {/* Tool Execution / LLM Debug Logs (Terminal UI) */}
        <Card
          className="flex-1 min-h-[220px] bg-gray-900/80 border-purple-500/20 font-mono"
          styles={{ body: { padding: '12px', display: 'flex', flexDirection: 'column', flex: 1 } }}
          title={
            <Tabs
              size="small"
              activeKey={activeLogTab}
              onChange={(key) => { setActiveLogTab(key); audioFeedback.playClick(); }}
              style={{ marginBottom: 0 }}
              items={[
                { key: 'tools', label: 'TOOLS' },
                { key: 'debug', label: 'LLM DEBUG' }
              ]}
            />
          }
          extra={
            activeLogTab === 'tools' ? (
              <Button size="small" type="text" onClick={() => { setToolLogs([]); audioFeedback.playClick(); }} style={{ color: '#9ca3af', fontSize: '10px' }}>CLEAR</Button>
            ) : (
              <Button size="small" type="text" onClick={() => { setDebugPayload(null); audioFeedback.playClick(); }} style={{ color: '#9ca3af', fontSize: '10px' }}>RESET</Button>
            )
          }
        >
          
          {activeLogTab === 'tools' ? (
            <div className="flex-1 overflow-y-auto space-y-2 text-[11px] leading-relaxed scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
              {toolLogs.map((log, i) => (
                <div key={i} className="flex items-start gap-1">
                  <span className="text-gray-600 select-none">[{log.timestamp}]</span>
                  <span className={`font-bold select-none ${
                    log.type === 'tool' ? 'text-cyan-400' :
                    log.type === 'llm' ? 'text-purple-400' :
                    log.type === 'system' ? 'text-yellow-400' : 'text-gray-500'
                  }`}>
                    {log.type.toUpperCase()}:
                  </span>
                  <span className={`
                    ${log.status === 'success' ? 'text-green-400' :
                      log.status === 'error' ? 'text-red-400' :
                      log.status === 'pending' ? 'text-yellow-400 animate-pulse' : 'text-gray-300'
                    }
                  `}>
                    {log.message}
                  </span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto text-[10px] font-mono leading-normal text-cyan-300/90 whitespace-pre scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent bg-black/45 p-2 rounded border border-white/5 select-text selection:bg-purple-950/80">
              {debugPayload ? (
                JSON.stringify(debugPayload, null, 2)
              ) : (
                <span className="text-gray-500 italic">No telemetry data. Enable "Debug Payload" checkbox and submit a query.</span>
              )}
            </div>
          )}
        </Card>

      </div>
    </div>

      {/* Zoom Modal */}
      <Modal
        open={!!activeZoomItem}
        onCancel={() => setActiveZoomItem(null)}
        footer={null}
        width={800}
        centered
        styles={{ body: { padding: '24px', background: '#0a0a0a', display: 'flex', gap: '24px', maxHeight: '80vh', overflowY: 'auto' } }}
      >
        {activeZoomItem && (
          <>
            {/* Left: Graphic Container */}
            <div className="flex-1 flex items-center justify-center bg-gray-900/60 rounded-xl p-4 border border-white/5 min-h-[300px]">
              {activeZoomItem.type === 'sigil' && activeZoomItem.svg && (
                <div dangerouslySetInnerHTML={{ __html: activeZoomItem.svg }} className="w-full max-w-[280px] h-full flex items-center justify-center shadow-lg" />
              )}
              {activeZoomItem.type === 'sigil_ai' && activeZoomItem.ai_image && (
                <img src={activeZoomItem.ai_image} alt={activeZoomItem.title} className="w-full max-w-[280px] object-contain rounded-xl shadow-lg border border-purple-500/20" />
              )}
              {activeZoomItem.type === 'tarot' && activeZoomItem.svg && (
                <div dangerouslySetInnerHTML={{ __html: activeZoomItem.svg }} className="w-full max-w-[160px] h-full flex items-center justify-center shadow-lg" />
              )}
              {activeZoomItem.type === 'iching' && activeZoomItem.svg && (
                <div dangerouslySetInnerHTML={{ __html: activeZoomItem.svg }} className="w-full max-w-[320px] h-full flex items-center justify-center shadow-lg" />
              )}
              {activeZoomItem.type === 'geomancy' && activeZoomItem.svg && (
                <div dangerouslySetInnerHTML={{ __html: activeZoomItem.svg }} className="w-full max-w-[360px] h-full flex items-center justify-center shadow-lg" />
              )}
            </div>

            {/* Right: Info details */}
            <div className="flex-1 flex flex-col justify-start space-y-4">
              <div>
                <span className="text-[10px] text-purple-400 font-mono font-bold tracking-widest block uppercase">VAJRA.STREAM ORACLE</span>
                <h3 className="text-xl font-bold text-white font-serif">{activeZoomItem.title}</h3>
              </div>

              {/* Tarot details */}
              {activeZoomItem.type === 'tarot' && activeZoomItem.card && (
                <div className="space-y-3 text-sm text-gray-300">
                  <div className="flex flex-wrap gap-2">
                    <span className="px-2 py-0.5 bg-purple-950 text-purple-300 border border-purple-500/20 rounded-md text-[10px] font-mono">
                      ELEMENT: {activeZoomItem.card.element}
                    </span>
                    {activeZoomItem.card.ruler && (
                      <span className="px-2 py-0.5 bg-cyan-950 text-cyan-300 border border-cyan-500/20 rounded-md text-[10px] font-mono">
                        RULER: {activeZoomItem.card.ruler}
                      </span>
                    )}
                    {activeZoomItem.card.hebrew && (
                      <span className="px-2 py-0.5 bg-yellow-950 text-yellow-300 border border-yellow-500/20 rounded-md text-[10px] font-mono">
                        LETTER: {activeZoomItem.card.hebrew}
                      </span>
                    )}
                    <span className="px-2 py-0.5 bg-gray-800 text-gray-200 border border-white/5 rounded-md text-[10px] font-mono">
                      {activeZoomItem.card.orientation.toUpperCase()}
                    </span>
                  </div>
                  <div className="space-y-2 border-t border-white/10 pt-3">
                    <h4 className="text-xs font-bold text-white font-mono uppercase">Esoteric Meaning</h4>
                    <p className="italic text-purple-200 bg-purple-900/10 p-3 rounded-lg border border-purple-500/10">
                      "{activeZoomItem.card.meaning}"
                    </p>
                  </div>
                </div>
              )}

              {/* Sigil details */}
              {(activeZoomItem.type === 'sigil' || activeZoomItem.type === 'sigil_ai') && (
                <div className="space-y-3 text-sm text-gray-300">
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-cyan-400 font-mono uppercase">Intention Focus</h4>
                    <p className="italic text-cyan-100 bg-cyan-900/10 p-3 rounded-lg border border-cyan-500/10">
                      "{activeZoomItem.intention}"
                    </p>
                  </div>
                  <div className="border-t border-white/10 pt-3 text-xs text-gray-400 leading-relaxed font-mono">
                    <p>Frequencies tuned. Kamea grid calculation completed. Scalar intention broadcast set at peak resonance.</p>
                  </div>
                </div>
              )}

              {/* I Ching details */}
              {activeZoomItem.type === 'iching' && activeZoomItem.cast && (
                <div className="space-y-3 text-sm text-gray-300">
                  <div className="space-y-2">
                    <span className="text-xs font-bold text-white font-mono uppercase block">Primary Hexagram</span>
                    <div className="p-3 bg-gray-900/60 rounded-lg border border-white/5">
                      <span className="font-bold text-cyan-400 block">{activeZoomItem.cast.primary?.name}</span>
                      <p className="text-xs text-gray-300 mt-1">{activeZoomItem.cast.primary?.meaning}</p>
                    </div>
                  </div>
                  
                  {activeZoomItem.cast.has_changes && (
                    <div className="space-y-2 pt-2 border-t border-white/10">
                      <span className="text-xs font-bold text-purple-300 font-mono uppercase block">Relating Hexagram (After Changes)</span>
                      <div className="p-3 bg-gray-900/60 rounded-lg border border-purple-500/10">
                        <span className="font-bold text-purple-300 block">{activeZoomItem.cast.relating?.name}</span>
                        <p className="text-xs text-gray-300 mt-1">{activeZoomItem.cast.relating?.meaning}</p>
                      </div>
                      <div className="text-[10px] text-gray-400 font-mono">
                        Changing Lines: {activeZoomItem.cast.changing_lines.join(', ')}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Geomancy details */}
              {activeZoomItem.type === 'geomancy' && activeZoomItem.chart && (
                <div className="space-y-3 text-sm text-gray-300">
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2 bg-gray-900/60 border border-white/5 rounded">
                      <span className="text-gray-500 block">THE JUDGE</span>
                      <span className="text-yellow-400 font-bold">{activeZoomItem.chart.figures?.Judge?.name}</span>
                    </div>
                    <div className="p-2 bg-gray-900/60 border border-white/5 rounded">
                      <span className="text-gray-500 block">RECONCILER</span>
                      <span className="text-yellow-400 font-bold">{activeZoomItem.chart.figures?.Reconciler?.name}</span>
                    </div>
                    <div className="p-2 bg-gray-900/60 border border-white/5 rounded">
                      <span className="text-gray-500 block">RIGHT WITNESS</span>
                      <span className="text-gray-300">{activeZoomItem.chart.figures?.['Right Witness']?.name}</span>
                    </div>
                    <div className="p-2 bg-gray-900/60 border border-white/5 rounded">
                      <span className="text-gray-500 block">LEFT WITNESS</span>
                      <span className="text-gray-300">{activeZoomItem.chart.figures?.['Left Witness']?.name}</span>
                    </div>
                  </div>
                  
                  <div className="border-t border-white/10 pt-3 space-y-2">
                    <h4 className="text-xs font-bold text-white font-mono uppercase">Geomantic Meaning (Judge)</h4>
                    <p className="italic text-yellow-200 bg-yellow-950/10 p-3 rounded-lg border border-yellow-500/10">
                      "{activeZoomItem.chart.figures?.Judge?.meaning}"
                    </p>
                  </div>

                  <div className="border-t border-white/10 pt-3">
                    <h4 className="text-xs font-bold text-white font-mono uppercase mb-2">Astrological House Projection</h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-[10px] max-h-32 overflow-y-auto pr-1">
                      {Array.from({ length: 12 }).map((_, idx) => {
                        const houseNum = idx + 1;
                        const figure = activeZoomItem.chart.houses?.[houseNum];
                        if (!figure) return null;
                        return (
                          <div key={houseNum} className="p-1.5 bg-black/40 border border-white/5 rounded flex flex-col justify-between">
                            <span className="text-gray-500 font-bold">House {houseNum}</span>
                            <span className="text-purple-300 font-semibold truncate">{figure.name}</span>
                            <span className="text-[8px] text-gray-400 font-mono truncate">{figure.element} / {figure.ruler}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </Modal>

    </div>
  );
}
