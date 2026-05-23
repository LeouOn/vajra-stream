import React, { useState } from 'react';
import { Sparkles, Send, Loader2, Info, Lightbulb, TrendingUp, Settings, HelpCircle, X } from 'lucide-react';

const API_BASE = 'http://localhost:8008/api/v1';

const QUICK_PROMPTS = [
  { id: 'explain', label: 'Explain current settings', icon: Settings },
  { id: 'trends', label: 'What do trends show?', icon: TrendingUp },
  { id: 'suggest', label: 'Suggest improvements', icon: Lightbulb },
  { id: 'status', label: 'System status overview', icon: Info },
];

const SUGGESTED_QUESTIONS = {
  explain: [
    "Why is the current frequency optimal for healing?",
    "What does the harmonic strength setting do?",
    "How does prayer bowl mode differ from pure sine?"
  ],
  trends: [
    "What patterns do you see in my session history?",
    "Which frequency is most effective based on trends?",
    "Should I adjust settings based on these trends?"
  ],
  suggest: [
    "What frequency would help with sleep?",
    "How can I improve crystal grid efficiency?",
    "What intentions would be most beneficial now?"
  ],
  status: [
    "Is my crystal grid working optimally?",
    "What factors affect broadcast strength?",
    "How can I tell if healing energy is flowing?"
  ]
};

const LLMInsightsPanel = ({ sessions, crystalStatus, scalarStatus, frequency, isPlaying }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [contextTab, setContextTab] = useState('current');

  const getContextData = () => {
    const activeSessions = Object.values(sessions).filter(s => s.status === 'running');
    return {
      currentFrequency: frequency,
      isPlaying,
      activeSessions: activeSessions.length,
      crystalActive: crystalStatus?.active || false,
      scalarRate: scalarStatus?.rate || null,
      recentTrends: activeSessions.slice(0, 5).map(s => ({
        name: s.name,
        intention: s.intention,
        duration: s.duration
      }))
    };
  };

  const buildSystemPrompt = () => {
    const ctx = getContextData();
    return `You are an AI assistant for Vajra.Stream, a sacred technology platform for blessing, healing, and transformation using radionics, crystal grids, and scalar wave generation.

Current System State:
- Frequency: ${ctx.currentFrequency?.toFixed(1) || 'N/A'} Hz
- Audio: ${ctx.isPlaying ? 'Playing' : 'Idle'}
- Active Sessions: ${ctx.activeSessions}
- Crystal Grid: ${ctx.crystalActive ? 'Active' : 'Inactive'}
- Scalar Rate: ${ctx.scalarRate || 'Not tuned'}

Recent Sessions: ${JSON.stringify(ctx.recentTrends)}

Provide helpful, concise insights about the Vajra.Stream system. Explain technical concepts in accessible ways. Focus on practical recommendations for spiritual practice.

When appropriate, suggest:
- Optimal frequencies for different intentions
- How to improve crystal grid efficiency
- Meaningful intentions to set
- Settings adjustments based on goals`;
  };

  const sendMessage = async (text) => {
    if (!text.trim()) return;
    
    const userMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/llm/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            { role: 'system', content: buildSystemPrompt() },
            ...messages,
            userMessage
          ],
          temperature: 0.7,
          max_tokens: 500
        })
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMessage = { role: 'assistant', content: data.response };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const errorMsg = { role: 'assistant', content: 'Sorry, I could not process that request. Please try again.' };
        setMessages(prev => [...prev, errorMsg]);
      }
    } catch (error) {
      console.error('LLM chat error:', error);
      const errorMsg = { role: 'assistant', content: 'Unable to connect to the AI service. Make sure the backend is running.' };
      setMessages(prev => [...prev, errorMsg]);
    }

    setIsLoading(false);
  };

  const handleQuickPrompt = (promptId) => {
    const questions = SUGGESTED_QUESTIONS[promptId];
    if (questions && questions.length > 0) {
      sendMessage(questions[0]);
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg border border-indigo-500/30 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-900/50 to-purple-900/50 p-3 border-b border-indigo-500/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-bold text-indigo-300">AI Insights</h3>
          </div>
          <button
            onClick={() => setMessages([])}
            className="text-xs text-gray-400 hover:text-white flex items-center gap-1"
          >
            <X className="w-3 h-3" /> Clear
          </button>
        </div>
      </div>

      {/* Context Tabs */}
      <div className="flex border-b border-gray-700">
        {['current', 'trends', 'suggestions'].map((tab) => (
          <button
            key={tab}
            onClick={() => setContextTab(tab)}
            className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
              contextTab === tab
                ? 'bg-indigo-900/30 text-indigo-300 border-b-2 border-indigo-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Context Content */}
      {contextTab === 'current' && (
        <div className="p-3 bg-gray-800/50 border-b border-gray-700">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-gray-800 p-2 rounded">
              <span className="text-gray-400">Frequency</span>
              <div className="text-indigo-400 font-mono font-bold">{frequency?.toFixed(1) || 'N/A'} Hz</div>
            </div>
            <div className="bg-gray-800 p-2 rounded">
              <span className="text-gray-400">Status</span>
              <div className={isPlaying ? 'text-green-400 font-bold' : 'text-gray-400'}>
                {isPlaying ? 'Playing' : 'Idle'}
              </div>
            </div>
            <div className="bg-gray-800 p-2 rounded">
              <span className="text-gray-400">Crystal</span>
              <div className={crystalStatus?.active ? 'text-green-400 font-bold' : 'text-gray-400'}>
                {crystalStatus?.active ? 'Active' : 'Inactive'}
              </div>
            </div>
            <div className="bg-gray-800 p-2 rounded">
              <span className="text-gray-400">Scalar Rate</span>
              <div className="text-cyan-400 font-bold">{scalarStatus?.rate || 'None'}</div>
            </div>
          </div>
        </div>
      )}

      {contextTab === 'trends' && (
        <div className="p-3 bg-gray-800/50 border-b border-gray-700">
          <div className="text-xs text-gray-400 mb-2">Session Activity</div>
          <div className="space-y-1">
            {Object.values(sessions).filter(s => s.status === 'running').length > 0 ? (
              Object.values(sessions).filter(s => s.status === 'running').slice(0, 3).map((session) => (
                <div key={session.id} className="flex justify-between text-xs p-2 bg-gray-800 rounded">
                  <span className="text-purple-300 truncate">{session.name}</span>
                  <span className="text-gray-500">{session.audio_frequency?.toFixed(0) || '?'} Hz</span>
                </div>
              ))
            ) : (
              <div className="text-xs text-gray-500 text-center py-2">No active sessions</div>
            )}
          </div>
        </div>
      )}

      {contextTab === 'suggestions' && (
        <div className="p-3 bg-gray-800/50 border-b border-gray-700">
          <div className="grid grid-cols-2 gap-2">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt.id}
                onClick={() => handleQuickPrompt(prompt.id)}
                className="flex items-center gap-2 p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-left transition-colors"
              >
                <prompt.icon className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                <span className="text-gray-300">{prompt.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="h-64 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <HelpCircle className="w-8 h-8 mx-auto mb-2 text-gray-600" />
            <p className="text-sm text-gray-500">
              Ask about your settings, trends, or how to improve your practice
            </p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`rounded-lg p-3 ${
              msg.role === 'user'
                ? 'bg-indigo-900/30 ml-8 border border-indigo-500/30'
                : 'bg-gray-800 mr-8 border border-gray-700'
            }`}
          >
            <div className="text-xs mb-1 flex items-center gap-1">
              <span className={msg.role === 'user' ? 'text-indigo-400' : 'text-cyan-400'}>
                {msg.role === 'user' ? 'You' : 'AI'}
              </span>
            </div>
            <div className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
              {msg.content}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
            placeholder="Ask about settings, trends..."
            className="flex-1 bg-gray-800 text-white text-sm px-3 py-2 rounded-lg border border-gray-600 focus:border-indigo-500 focus:outline-none placeholder-gray-500"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isLoading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-700 text-white p-2 rounded-lg transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default LLMInsightsPanel;