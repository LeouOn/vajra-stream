import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, Terminal, Cpu, Activity, Wifi, AlertTriangle, 
  Sparkles, Shield, Compass, BookOpen, Clock, Play, Square 
} from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';

const API_BASE = 'http://localhost:8008/api/v1';

const QuantumWaveform = ({ isPlaying, frequency }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const width = canvas.width;
      const height = canvas.height;
      const midY = height / 2;
      
      // Draw grid lines inside the mini-visualizer
      ctx.strokeStyle = 'rgba(138, 43, 226, 0.1)';
      ctx.lineWidth = 1;
      // horizontal mid line
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();
      
      // Draw wave
      const amplitude = isPlaying ? 12 : 3;
      const speed = isPlaying ? 0.15 : 0.03;
      const wavelength = isPlaying ? 25 : 60;
      
      ctx.beginPath();
      ctx.lineWidth = isPlaying ? 2 : 1;
      ctx.strokeStyle = isPlaying ? 'rgba(0, 255, 255, 0.85)' : 'rgba(138, 43, 226, 0.4)';
      
      if (isPlaying) {
        ctx.shadowBlur = 6;
        ctx.shadowColor = 'rgba(0, 255, 255, 0.6)';
      } else {
        ctx.shadowBlur = 0;
      }
      
      for (let x = 0; x < width; x++) {
        const y = midY + Math.sin(x / wavelength + phase) * amplitude * Math.cos(x / (wavelength * 2.5) + phase * 0.5);
        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
      
      ctx.shadowBlur = 0;
      ctx.font = '8px monospace';
      ctx.fillStyle = isPlaying ? '#00f5ff' : '#8a2be2';
      ctx.fillText(isPlaying ? `CARRIER ACTIVE: ${frequency.toFixed(1)}Hz` : 'CARRIER STANDBY', 6, height - 6);
      
      phase += speed;
      animationId = requestAnimationFrame(render);
    };

    render();
    
    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [isPlaying, frequency]);

  return (
    <canvas 
      ref={canvasRef} 
      width={280} 
      height={64} 
      className="w-full bg-black/75 rounded-lg border border-purple-500/20 shadow-inner"
    />
  );
};

export default function CommandCenter({ 
  isConnected, 
  isPlaying, 
  frequency, 
  crystalStatus, 
  scalarStatus,
  sessions
}) {
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

  const handleSendMessage = async (textToSend) => {
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
          provider: 'local'
        })
      });

      if (!chatResponse.ok) {
        throw new Error(`Chat API error: ${chatResponse.statusText}`);
      }

      const data = await chatResponse.json();
      
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
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);

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
    <div className="h-full flex flex-col lg:flex-row gap-6 p-4 md:p-6 overflow-hidden">
      
      {/* Left Column: Chat and Commands */}
      <div className="flex-1 flex flex-col min-h-0 bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 overflow-hidden shadow-2xl">
        
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-purple-900/40 via-indigo-900/40 to-blue-900/40 p-4 border-b border-white/10 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-3 h-3 bg-purple-500 rounded-full animate-ping absolute" />
              <div className="w-3 h-3 bg-purple-600 rounded-full relative" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide">AI Command Center</h2>
              <p className="text-xs text-purple-300">Vajra.Stream Digital Operator v1.2</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs px-2.5 py-1 bg-purple-950/80 border border-purple-500/30 text-purple-300 rounded-full flex items-center gap-1.5 font-mono">
              <Cpu className="w-3 h-3 text-purple-400" />
              LLM AGENT ACTIVE
            </span>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
          {messages.map((msg, index) => (
            <div 
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`
                max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed shadow-lg
                ${msg.role === 'user' 
                  ? 'bg-purple-600/90 text-white rounded-br-none border border-purple-400/20' 
                  : 'bg-gray-800/80 text-gray-100 rounded-bl-none border border-white/5'
                }
              `}>
                <div className="markdown-container">
                  {msg.content.split('\n\n').map((paragraph, pi) => {
                    // Check if bullet point or bold header
                    if (paragraph.startsWith('- ') || paragraph.startsWith('* ')) {
                      return (
                        <ul key={pi} className="list-disc pl-5 space-y-1.5 my-2">
                          {paragraph.split('\n').map((item, li) => (
                            <li key={li}>
                              {item.replace(/^[-*]\s+/, '').split('**').map((chunk, ci) => 
                                ci % 2 === 1 ? <strong key={ci} className="text-purple-300">{chunk}</strong> : chunk
                              )}
                            </li>
                          ))}
                        </ul>
                      );
                    }
                    
                    return (
                      <p key={pi} className="mb-2 last:mb-0">
                        {paragraph.split('**').map((chunk, ci) => {
                          if (ci % 2 === 1) {
                            return <strong key={ci} className="text-purple-300 font-semibold">{chunk}</strong>;
                          }
                          // Handle inline code block
                          if (chunk.includes('`')) {
                            return chunk.split('`').map((c, idx) => 
                              idx % 2 === 1 ? <code key={idx} className="bg-black/45 px-1 py-0.5 rounded text-cyan-300 font-mono text-xs">{c}</code> : c
                            );
                          }
                          return chunk;
                        })}
                      </p>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-800/80 rounded-xl rounded-bl-none px-4 py-3 border border-white/5 shadow-lg flex items-center space-x-2">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="px-4 py-2 bg-gray-950/20 border-t border-white/5 flex gap-2 overflow-x-auto scrollbar-none whitespace-nowrap">
          {quickCommands.map((cmd) => (
            <button
              key={cmd.label}
              disabled={isLoading}
              onClick={() => handleSendMessage(cmd.text)}
              onMouseEnter={() => audioFeedback.playTick()}
              className="px-3 py-1.5 bg-purple-900/20 hover:bg-purple-800/40 border border-purple-500/20 rounded-full text-xs font-semibold text-purple-300 hover:text-white transition-all duration-300 hover:scale-105 active:scale-95"
            >
              {cmd.label}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
          className="p-4 border-t border-white/10 bg-gray-950/40 flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              audioFeedback.playType();
            }}
            disabled={isLoading}
            placeholder="Instruct the system (e.g. 'start peace session', 'list populations')..."
            className="flex-1 bg-gray-900/80 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-all font-sans"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            onMouseEnter={() => audioFeedback.playTick()}
            className="px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 text-white rounded-lg transition-all duration-300 flex items-center justify-center shadow-md font-semibold text-sm gap-2"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </form>

      </div>

      {/* Right Column: Status & Tool execution logs */}
      <div className="w-full lg:w-80 flex flex-col gap-6 h-full min-h-0">
        
        {/* Status Monitors Card */}
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 flex flex-col shadow-2xl">
          <h3 className="text-sm font-bold text-white mb-4 tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-400" />
            SYSTEM MONITORS
          </h3>
          
          <div className="space-y-4">
            
            {/* Quantum Resonance Carrier Oscilloscope */}
            <div className="flex flex-col gap-1.5">
              <span className="text-xs text-gray-400 font-medium">Quantum Resonance Carrier</span>
              <QuantumWaveform isPlaying={isPlaying} frequency={frequency} />
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
        </div>

        {/* Tool Execution Logs (Terminal UI) */}
        <div className="flex-1 min-h-[220px] bg-black/95 rounded-xl border border-white/10 p-4 flex flex-col font-mono shadow-2xl">
          <div className="flex justify-between items-center mb-3">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-purple-400 animate-pulse" />
              <span className="text-xs font-bold text-gray-300">TOOL EXECUTION LOG</span>
            </div>
            <button 
              onClick={() => { setToolLogs([]); audioFeedback.playClick(); }}
              onMouseEnter={() => audioFeedback.playTick()}
              className="text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
            >
              CLEAR
            </button>
          </div>
          
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
        </div>

      </div>

    </div>
  );
}
