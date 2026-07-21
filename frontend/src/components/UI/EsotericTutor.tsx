import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Collapse, Typography, Spin, Tag } from 'antd';
import { GraduationCap, Send, RefreshCw, BookOpen } from 'lucide-react';

const { Text, Paragraph } = Typography;

type Subject = 'astrology' | 'tarot' | 'iching';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface Lesson {
  id: string;
  title: string;
  description: string;
}

const SUBJECT_CONFIG: Record<Subject, { label: string; icon: string; color: string; systemPrompt: string; lessons: Lesson[] }> = {
  astrology: {
    label: 'Astrology',
    icon: '🌟',
    color: '#8b5cf6',
    systemPrompt: `You are a warm, patient astrology teacher helping a beginner learn to read natal charts. 

Your teaching approach:
1. Start simple, build gradually. Never overwhelm with jargon.
2. When introducing a term (e.g. "trine"), define it immediately in plain language.
3. Use concrete examples whenever possible: "If your Sun is in Cancer, that means..."
4. Structure lessons: Signs → Planets → Houses → Aspects → Synthesis.
5. Encourage questions. Check understanding: "Does that make sense so far?"
6. Cover the 12 zodiac signs (elements, modalities, rulers), 10 planets (Sun through Pluto), 12 houses, and 5 major aspects (conjunction, sextile, square, trine, opposition).
7. Teach chart reading: "To read a chart, start with the Sun (identity), Moon (emotions), and Ascendant (persona)."

Keep responses to 150-300 words. Use headers (##) and bullet points for clarity. Be warm and encouraging.`,
    lessons: [
      { id: 'basics', title: 'Chart Basics', description: 'What is a natal chart? The big 3 (Sun, Moon, Rising)' },
      { id: 'signs', title: '12 Zodiac Signs', description: 'Elements (Fire/Earth/Air/Water), Modalities (Cardinal/Fixed/Mutable)' },
      { id: 'planets', title: '10 Planets', description: 'What each planet represents: Sun=identity, Moon=emotions, etc.' },
      { id: 'houses', title: '12 Houses', description: 'Life areas: 1st=self, 7th=partnership, 10th=career, etc.' },
      { id: 'aspects', title: 'Aspects', description: 'Conjunction, sextile, square, trine, opposition' },
      { id: 'reading', title: 'Reading a Chart', description: 'How to synthesize planet + sign + house + aspects' },
    ],
  },
  tarot: {
    label: 'Tarot',
    icon: '🃏',
    color: '#a855f7',
    systemPrompt: `You are a warm, patient tarot teacher helping a beginner learn to read the 78-card Rider-Waite-Smith deck.

Your teaching approach:
1. Start with the structure: 22 Major Arcana + 56 Minor Arcana (4 suits: Wands, Cups, Swords, Pentacles).
2. Teach card meanings with both upright and reversed interpretations.
3. Use storytelling: "The Fool's Journey through the Major Arcana tells the story of..."
4. Cover spreads: 1-card daily draw, 3-card past/present/future, Celtic Cross.
5. Teach the four suits and their elements: Wands=Fire, Cups=Water, Swords=Air, Pentacles=Earth.
6. Number meanings in Minor Arcana: Ace through 10 + Court Cards (Page, Knight, Queen, King).
7. Encourage intuition: "What do you see in this card? What feeling does it evoke?"

Keep responses to 150-300 words. Use headers (##) and bullet points for clarity. Be warm and encouraging.`,
    lessons: [
      { id: 'structure', title: 'Deck Structure', description: 'Major vs Minor Arcana, 4 suits, 78 cards total' },
      { id: 'major', title: 'Major Arcana', description: 'The Fool through The World — the soul\'s journey' },
      { id: 'suits', title: 'Four Suits', description: 'Wands(Fire), Cups(Water), Swords(Air), Pentacles(Earth)' },
      { id: 'court', title: 'Court Cards', description: 'Page, Knight, Queen, King — personalities and people' },
      { id: 'spreads', title: 'Spreads', description: '1-card, 3-card, Celtic Cross layouts' },
      { id: 'reversed', title: 'Reversed Cards', description: 'What it means when a card appears upside-down' },
    ],
  },
  iching: {
    label: 'I Ching',
    icon: '☯️',
    color: '#06b6d4',
    systemPrompt: `You are a warm, patient I Ching teacher helping a beginner learn the Book of Changes.

Your teaching approach:
1. Start with fundamentals: yin (broken line - -) and yang (solid line —).
2. Explain trigrams (bagua): 8 trigrams made of 3 lines, each with a nature image (Heaven, Earth, Water, Fire, Wind, Mountain, Lake, Thunder).
3. Explain hexagrams: 64 hexagrams made of 2 trigrams stacked (6 lines total).
4. Teach the casting method: yarrow stalks or 3-coin method, generating lines that can be changing (moving) or stable.
5. Cover key hexagrams: #1 Qián (The Creative/Heaven), #2 Kūn (The Receptive/Earth), #11 Tài (Peace), #24 Fù (Return).
6. Teach interpretation: the Judgment (彖), the Image (象), and the changing lines.
7. Emphasize the philosophy: change is constant, the wise person adapts.

Keep responses to 150-300 words. Use headers (##) and bullet points for clarity. Be warm and encouraging. Use both Chinese names and pinyin where helpful.`,
    lessons: [
      { id: 'basics', title: 'Yin & Yang', description: 'The two primal forces — broken and solid lines' },
      { id: 'trigrams', title: '8 Trigrams (Bagua)', description: 'Heaven, Earth, Water, Fire, Wind, Mountain, Lake, Thunder' },
      { id: 'hexagrams', title: '64 Hexagrams', description: 'Two trigrams stacked = one of 64 states of change' },
      { id: 'casting', title: 'Casting Method', description: '3-coin or yarrow stalk method for generating a reading' },
      { id: 'interpretation', title: 'Interpreting', description: 'Judgment text, Image text, and changing (moving) lines' },
      { id: 'philosophy', title: 'Philosophy of Change', description: 'The Taoist wisdom: all things transform' },
    ],
  },
};

export default function EsotericTutor() {
  const [activeSubject, setActiveSubject] = useState<Subject>('astrology');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentLesson, setCurrentLesson] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const config = SUBJECT_CONFIG[activeSubject];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const startLesson = async (lessonId: string) => {
    const lesson = config.lessons.find(l => l.id === lessonId);
    if (!lesson) return;
    setCurrentLesson(lessonId);
    setMessages([]);
    setInput('');

    const prompt = `Please teach me about: ${lesson.title}. ${lesson.description}. I'm a complete beginner — start from the basics and build up.`;
    await sendToLLM(prompt);
  };

  const askQuestion = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput('');
    await sendToLLM(q);
  };

  const sendToLLM = async (userText: string) => {
    setLoading(true);
    const newHistory = [...messages, { role: 'user' as const, content: userText }];

    try {
      const res = await fetch('/api/v1/llm/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            { role: 'system', content: config.systemPrompt },
            ...newHistory.slice(-20).map(m => ({ role: m.role, content: m.content })),
          ],
          max_tokens: 1200,
          temperature: 0.7,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const text = data.choices?.[0]?.message?.content
          || data.response
          || data.content
          || data.text
          || 'I\'m not sure how to respond to that. Could you rephrase?';
        setMessages([...newHistory, { role: 'assistant', content: text }]);
      } else {
        const errText = await res.text().catch(() => '');
        setMessages([...newHistory, { role: 'assistant', content: `Sorry, I couldn't reach the teaching engine (HTTP ${res.status}).${errText ? ' ' + errText.slice(0, 150) : ''}` }]);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setMessages([...newHistory, { role: 'assistant', content: `Connection error: ${msg}` }]);
    }
    setLoading(false);
  };

  const switchSubject = (subject: Subject) => {
    setActiveSubject(subject);
    setMessages([]);
    setCurrentLesson(null);
    setInput('');
  };

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h3 className="text-lg font-bold text-white flex items-center justify-center gap-2">
          <GraduationCap className="w-5 h-5" style={{ color: config.color }} />
          Esoteric Tutor
        </h3>
        <p className="text-xs text-gray-400 mt-1">Learn astrology, tarot, and I Ching at your own pace</p>
      </div>

      <div className="flex gap-2 justify-center">
        {(Object.keys(SUBJECT_CONFIG) as Subject[]).map(subject => {
          const sc = SUBJECT_CONFIG[subject];
          const isActive = activeSubject === subject;
          return (
            <button
              key={subject}
              type="button"
              onClick={() => switchSubject(subject)}
              className="px-4 py-2 rounded-lg text-sm font-semibold transition-all border"
              style={{
                borderColor: isActive ? sc.color : 'rgba(255,255,255,0.1)',
                backgroundColor: isActive ? `${sc.color}20` : 'transparent',
                color: isActive ? sc.color : '#64748b',
              }}
            >
              {sc.icon} {sc.label}
            </button>
          );
        })}
      </div>

      {!currentLesson && messages.length === 0 && (
        <div className="space-y-2">
          <Text className="!text-[10px] !font-mono !uppercase !text-gray-500 block">Choose a lesson to begin</Text>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {config.lessons.map((lesson, i) => (
              <button
                key={lesson.id}
                type="button"
                onClick={() => startLesson(lesson.id)}
                disabled={loading}
                className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/5 hover:border-white/15 hover:bg-white/8 transition-all text-left group"
              >
                <span className="text-lg flex-shrink-0 opacity-50 group-hover:opacity-100 transition-opacity" style={{ color: config.color }}>
                  {i + 1}
                </span>
                <div>
                  <div className="text-sm font-semibold text-gray-200 group-hover:text-white transition-colors">{lesson.title}</div>
                  <div className="text-[10px] text-gray-500 mt-0.5">{lesson.description}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div ref={scrollRef} className="space-y-3 max-h-[500px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-purple-900/50">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`text-xs leading-relaxed p-3 rounded-lg border ${
                msg.role === 'user'
                  ? 'bg-purple-950/20 border-purple-500/15'
                  : 'bg-black/40 border-white/5'
              }`}
            >
              {msg.role === 'user' && <span className="text-[9px] font-mono text-purple-400/60 block mb-1">YOU</span>}
              {msg.role === 'assistant' && <span className="text-[9px] font-mono block mb-1" style={{ color: config.color }}>TUTOR</span>}
              <span className="whitespace-pre-wrap text-gray-300">{msg.content}</span>
            </div>
          ))}
          {loading && (
            <div className="text-center py-3">
              <Spin size="small" />
              <span className="text-[10px] text-gray-500 ml-2">Teaching...</span>
            </div>
          )}
        </div>
      )}

      {messages.length > 0 && (
        <div className="flex gap-2">
          <Input.TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a follow-up question..."
            autoSize={{ minRows: 1, maxRows: 3 }}
            onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); askQuestion(); } }}
            disabled={loading}
          />
          <Button
            type="primary"
            size="small"
            loading={loading}
            onClick={askQuestion}
            disabled={!input.trim()}
            style={{ backgroundColor: config.color, borderColor: config.color }}
          >
            <Send className="w-3.5 h-3.5" />
          </Button>
        </div>
      )}

      {messages.length > 0 && (
        <div className="flex justify-center gap-2">
          <Button size="small" type="text" onClick={() => { setMessages([]); setCurrentLesson(null); }}>
            <RefreshCw className="w-3 h-3 mr-1" /> Back to Lessons
          </Button>
        </div>
      )}
    </div>
  );
}
