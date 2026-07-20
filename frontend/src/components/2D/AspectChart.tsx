import React, { useState, useMemo } from 'react';
import { Input, Button, Collapse, Typography, Spin } from 'antd';

const { Text, Paragraph } = Typography;

interface PlanetPosition {
  longitude: number;
  sign?: string;
  degree?: number;
  retrograde?: boolean;
  house?: number;
}

type AspectType = 'conjunction' | 'opposition' | 'trine' | 'square' | 'sextile';

interface Aspect {
  planet1: string;
  planet2: string;
  type: AspectType;
  orb: number;
  exact: number;
}

interface AspectChartProps {
  positions: Record<string, PlanetPosition>;
  size?: number;
}

const PLANET_GLYPHS: Record<string, string> = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂',
  jupiter: '♃', saturn: '♄', uranus: '♅', neptune: '♆', pluto: '♇',
  north_node: '☊', ascendant: 'Asc', midheaven: 'MC',
};

const PLANET_MEANINGS: Record<string, string> = {
  sun: '☉ Sun — Core identity, vitality, ego, conscious purpose',
  moon: '☽ Moon — Emotions, instincts, habits, inner self',
  mercury: '☿ Mercury — Communication, intellect, learning, commerce',
  venus: '♀ Venus — Love, beauty, values, relationships, art',
  mars: '♂ Mars — Action, desire, energy, courage, conflict',
  jupiter: '♃ Jupiter — Expansion, wisdom, luck, philosophy, growth',
  saturn: '♄ Saturn — Structure, discipline, karma, limitation, mastery',
  uranus: '♅ Uranus — Innovation, rebellion, sudden change, freedom',
  neptune: '♆ Neptune — Dreams, illusion, spirituality, mysticism',
  pluto: '♇ Pluto — Transformation, power, death/rebirth, the underworld',
  north_node: '☊ North Node — Soul purpose, karmic direction, future path',
};

const PLANET_COLORS: Record<string, string> = {
  sun: '#fbbf24', moon: '#e0e7ff', mercury: '#22d3ee', venus: '#f472b6',
  mars: '#ef4444', jupiter: '#f59e0b', saturn: '#94a3b8', uranus: '#a78bfa',
  neptune: '#60a5fa', pluto: '#6b21a8', north_node: '#10b981',
  ascendant: '#fde68a', midheaven: '#fcd34d',
};

const ASPECT_CONFIG: Record<AspectType, { angle: number; orb: number; color: string; label: string; symbol: string }> = {
  conjunction: { angle: 0, orb: 8, color: '#e2e8f0', label: 'Conjunction', symbol: '☉' },
  opposition: { angle: 180, orb: 8, color: '#ef4444', label: 'Opposition', symbol: '☉' },
  trine: { angle: 120, orb: 8, color: '#3b82f6', label: 'Trine', symbol: '△' },
  square: { angle: 90, orb: 8, color: '#f97316', label: 'Square', symbol: '□' },
  sextile: { angle: 60, orb: 6, color: '#22c55e', label: 'Sextile', symbol: '✦' },
};

const ZODIAC_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
const ZODIAC_GLYPHS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];

const ZODIAC_MEANINGS = [
  '♈ Aries — Fire, Cardinal. Pioneer, courage, initiation',
  '♉ Taurus — Earth, Fixed. Stability, values, patience',
  '♊ Gemini — Air, Mutable. Communication, duality, curiosity',
  '♋ Cancer — Water, Cardinal. Emotion, nurturing, home',
  '♌ Leo — Fire, Fixed. Creativity, pride, self-expression',
  '♍ Virgo — Earth, Mutable. Service, analysis, precision',
  '♎ Libra — Air, Cardinal. Balance, partnership, justice',
  '♏ Scorpio — Water, Fixed. Transformation, intensity, depth',
  '♐ Sagittarius — Fire, Mutable. Philosophy, travel, truth',
  '♑ Capricorn — Earth, Cardinal. Ambition, structure, discipline',
  '♒ Aquarius — Air, Fixed. Innovation, community, rebellion',
  '♓ Pisces — Water, Mutable. Mysticism, compassion, dissolution',
];

const SIGN_ELEMENT: Record<string, string> = {
  Aries: 'Fire', Leo: 'Fire', Sagittarius: 'Fire',
  Taurus: 'Earth', Virgo: 'Earth', Capricorn: 'Earth',
  Gemini: 'Air', Libra: 'Air', Aquarius: 'Air',
  Cancer: 'Water', Scorpio: 'Water', Pisces: 'Water',
};
const SIGN_MODALITY: Record<string, string> = {
  Aries: 'Cardinal', Cancer: 'Cardinal', Libra: 'Cardinal', Capricorn: 'Cardinal',
  Taurus: 'Fixed', Leo: 'Fixed', Scorpio: 'Fixed', Aquarius: 'Fixed',
  Gemini: 'Mutable', Virgo: 'Mutable', Sagittarius: 'Mutable', Pisces: 'Mutable',
};
const ASPECT_INTERPRETATION: Record<AspectType, string> = {
  conjunction: 'Fusion, blending of energies, intensification',
  opposition: 'Tension, polarity, awareness through contrast',
  trine: 'Harmonious flow, natural talent, ease',
  square: 'Dynamic friction, growth through challenge',
  sextile: 'Opportunity, creative potential, gentle cooperation',
};
const PLANET_DIGNITY: Record<string, Record<string, string>> = {
  sun:     { Leo: 'domicile', Aries: 'exaltation', Libra: 'detriment', Aquarius: 'fall' },
  moon:    { Cancer: 'domicile', Taurus: 'exaltation', Scorpio: 'detriment', Capricorn: 'fall' },
  mercury: { Gemini: 'domicile', Virgo: 'domicile', Sagittarius: 'detriment', Pisces: 'detriment' },
  venus:   { Taurus: 'domicile', Libra: 'domicile', Aries: 'detriment', Scorpio: 'detriment' },
  mars:    { Aries: 'domicile', Scorpio: 'domicile', Libra: 'detriment', Taurus: 'fall' },
  jupiter: { Sagittarius: 'domicile', Pisces: 'domicile', Gemini: 'detriment', Virgo: 'fall' },
  saturn:  { Capricorn: 'domicile', Aquarius: 'domicile', Cancer: 'detriment', Leo: 'fall' },
};

function angularDistance(lon1: number, lon2: number): number {
  let diff = Math.abs(lon1 - lon2) % 360;
  if (diff > 180) diff = 360 - diff;
  return diff;
}

function calculateAspects(positions: Record<string, PlanetPosition>): Aspect[] {
  const planetNames = Object.keys(positions).filter(n => n !== 'ascendant' && n !== 'midheaven');
  const aspects: Aspect[] = [];

  for (let i = 0; i < planetNames.length; i++) {
    for (let j = i + 1; j < planetNames.length; j++) {
      const p1 = planetNames[i];
      const p2 = planetNames[j];
      const dist = angularDistance(positions[p1].longitude, positions[p2].longitude);

      for (const [type, config] of Object.entries(ASPECT_CONFIG)) {
        const orb = Math.abs(dist - config.angle);
        if (orb <= config.orb) {
          aspects.push({
            planet1: p1,
            planet2: p2,
            type: type as AspectType,
            orb: orb,
            exact: config.angle,
          });
          break;
        }
      }
    }
  }
  return aspects.sort((a, b) => a.orb - b.orb);
}

export default function AspectChart({ positions, size = 420 }: AspectChartProps) {
  const [visibleAspects, setVisibleAspects] = useState<Set<AspectType>>(
    new Set(['conjunction', 'opposition', 'trine', 'square', 'sextile'])
  );
  const [llmQuestion, setLlmQuestion] = useState('');
  const [llmResponse, setLlmResponse] = useState('');
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmHistory, setLlmHistory] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);

  const aspects = useMemo(() => calculateAspects(positions), [positions]);

  const askChartLLM = async () => {
    const q = llmQuestion.trim() || 'Give me a comprehensive interpretation of this astrological chart. Cover the core identity, emotional nature, communication style, love and drive, growth areas, karmic patterns, and current challenges.';
    setLlmLoading(true);
    setLlmResponse('');
    try {
      const planetNames = Object.keys(positions).filter(n => n !== 'ascendant' && n !== 'midheaven');

      const elementCount: Record<string, number> = { Fire: 0, Earth: 0, Air: 0, Water: 0 };
      const modalityCount: Record<string, number> = { Cardinal: 0, Fixed: 0, Mutable: 0 };
      const planetsByHouse: Record<number, Array<string>> = {};
      const dignityList: string[] = [];

      const planetLines = planetNames.map(n => {
        const p = positions[n];
        const sign = p.sign || '?';
        const deg = p.degree?.toFixed(1) || '?';
        const house = p.house || '?';
        const ret = p.retrograde ? ' ℞ (retrograde)' : '';
        const glyph = PLANET_GLYPHS[n] || n[0].toUpperCase();
        if (SIGN_ELEMENT[sign]) elementCount[SIGN_ELEMENT[sign]]++;
        if (SIGN_MODALITY[sign]) modalityCount[SIGN_MODALITY[sign]]++;
        if (!planetsByHouse[house]) planetsByHouse[house] = [];
        planetsByHouse[house].push(`${glyph} ${n} in ${sign} ${deg}°`);
        if (PLANET_DIGNITY[n]?.[sign]) dignityList.push(`${n} ${PLANET_DIGNITY[n][sign]} in ${sign}`);
        return `${glyph} ${n}: ${sign} ${deg}° (House ${house})${ret}`;
      });

      const ascLon = positions.ascendant?.longitude || 0;
      const ascSign = positions.ascendant?.sign || 'Unknown';
      const ascDeg = positions.ascendant?.degree?.toFixed(1) || '?';
      const mcSign = positions.midheaven?.sign || 'Unknown';
      const mcDeg = positions.midheaven?.degree?.toFixed(1) || '?';

      const houseLines = Object.keys(planetsByHouse)
        .sort((a, b) => Number(a) - Number(b))
        .map(h => `  House ${h}: ${planetsByHouse[Number(h)].join(', ')}`)
        .join('\n');

      const aspectLines = aspects
        .sort((a, b) => a.orb - b.orb)
        .slice(0, 12)
        .map(a => {
          const interp = ASPECT_INTERPRETATION[a.type] || '';
          return `${a.planet1} ${a.type} ${a.planet2} — orb ${a.orb.toFixed(1)}° (${interp})`;
        })
        .join('\n');

      const elementLine = Object.entries(elementCount).map(([e, c]) => `${e}: ${c}`).join(' | ');
      const modalityLine = Object.entries(modalityCount).map(([m, c]) => `${m}: ${c}`).join(' | ');

      const systemPrompt = `You are an expert astrologer with deep knowledge of natal chart interpretation. Use the following natal chart data to answer the user's question with specificity and insight.

# NATAL CHART

## Angles
- Ascendant (Rising Sign): ${ascSign} ${ascDeg}° — how others see this person, physical body, first impressions
- Midheaven (MC): ${mcSign} ${mcDeg}° — career, public image, direction in life

## Planetary Positions (by sign and house)
${planetLines.join('\n')}

## Planets by House
${houseLines || '  (no house data)'}

## Element Balance: ${elementLine}
## Modality Balance: ${modalityLine}

## Essential Dignities (highlighted)
${dignityList.length ? dignityList.join('\n') : '  (no strong dignities)'}

## Major Aspects (sorted by tightness)
${aspectLines || '  (no major aspects within orb)'}

# INTERPRETATION FRAMEWORK

When answering:
1. Reference SPECIFIC positions and aspects from the chart above. Never give generic descriptions.
2. Connect multiple chart factors to show themes (e.g., "Your Sun in ${planetNames.find(n => positions[n].sign) ? 'see positions' : 'see chart'} plus Moon trine Saturn suggests...").
3. Cover the layered personality: Sun (core identity), Moon (emotions), Ascendant (persona), Mercury (mind), Venus (love), Mars (drive), then outer planets (Saturn, Jupiter, Uranus, Neptune, Pluto) for generational/karmic patterns.
4. For aspect interpretations, name the dynamic (conjunction = fusion, square = tension/growth, trine = flow, opposition = polarization, sextile = opportunity).
5. Honor retrograde planets — they turn energy inward, delay, or revisit themes.
6. Use warm, specific language. Avoid jargon dumps. Give the querent something they can feel.

If the user asked a specific question (not a full reading), focus deeply on that question using the chart data — don't produce a generic reading.

Keep your response between 400–800 words unless the question demands more depth.`;

      const res = await fetch('/api/v1/llm/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            { role: 'system', content: systemPrompt },
            ...llmHistory,
            { role: 'user', content: q },
          ],
          max_tokens: 1500,
          temperature: 0.7,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const text = data.choices?.[0]?.message?.content
          || data.response
          || data.content
          || data.message
          || data.text;
        const finalText = text || 'The astrologer returned no text. Please try rephrasing your question.';
        setLlmResponse(finalText);
        setLlmHistory(prev => [...prev, { role: 'user', content: q }, { role: 'assistant', content: finalText }].slice(-20));
        setLlmQuestion('');
      } else {
        const errBody = await res.text().catch(() => '');
        setLlmResponse(`Could not reach the LLM (HTTP ${res.status}).${errBody ? ' ' + errBody.slice(0, 200) : ''}`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setLlmResponse(`Network error: ${msg}`);
    }
    setLlmLoading(false);
  };

  const cx = size / 2;
  const cy = size / 2;
  const outerR = size * 0.46;
  const zodiacR = size * 0.40;
  const planetR = size * 0.33;
  const innerR = size * 0.14;

  const ascLon = positions.ascendant?.longitude || 0;

  const getPlanetPos = (longitude: number, radius: number) => {
    const angle = ((longitude - ascLon - 180) * Math.PI) / 180;
    return {
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    };
  };

  const toggleAspect = (type: AspectType) => {
    setVisibleAspects(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const filteredAspects = aspects.filter(a => visibleAspects.has(a.type));

  return (
    <div className="flex flex-col items-center gap-3">
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[460px]">
        <defs>
          <radialGradient id="chart-bg">
            <stop offset="0%" stopColor="#0f0a1e" stopOpacity={0.6} />
            <stop offset="100%" stopColor="#020617" stopOpacity={0.3} />
          </radialGradient>
        </defs>

        <circle cx={cx} cy={cy} r={outerR} fill="url(#chart-bg)" stroke="rgba(139, 92, 246, 0.2)" strokeWidth={1.5} />
        <circle cx={cx} cy={cy} r={zodiacR} fill="none" stroke="rgba(139, 92, 246, 0.15)" strokeWidth={1} />
        <circle cx={cx} cy={cy} r={planetR} fill="none" stroke="rgba(139, 92, 246, 0.08)" strokeWidth={1} />
        <circle cx={cx} cy={cy} r={innerR} fill="none" stroke="rgba(139, 92, 246, 0.1)" strokeWidth={1} />

        {ZODIAC_SIGNS.map((sign, i) => {
          const startAngle = ((i * 30 - ascLon - 180) * Math.PI) / 180;
          const endAngle = (((i + 1) * 30 - ascLon - 180) * Math.PI) / 180;
          const x1 = cx + Math.cos(startAngle) * zodiacR;
          const y1 = cy + Math.sin(startAngle) * zodiacR;
          const x2 = cx + Math.cos(endAngle) * zodiacR;
          const y2 = cy + Math.sin(endAngle) * zodiacR;
          const midAngle = (((i * 30 + 15) - ascLon - 180) * Math.PI) / 180;
          const labelR = (zodiacR + outerR) / 2;
          const lx = cx + Math.cos(midAngle) * labelR;
          const ly = cy + Math.sin(midAngle) * labelR;

          return (
            <g key={sign}>
              <title>{ZODIAC_MEANINGS[i]}</title>
              <line x1={cx + Math.cos(startAngle) * innerR} y1={cy + Math.sin(startAngle) * innerR}
                    x2={x1} y2={y1} stroke="rgba(139, 92, 246, 0.06)" strokeWidth={0.5} />
              <line x1={x1} y1={y1} x2={cx + Math.cos(startAngle) * outerR} y2={cy + Math.sin(startAngle) * outerR}
                    stroke="rgba(139, 92, 246, 0.15)" strokeWidth={1} />
              <text x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
                    fontSize={size * 0.032} fill="#94a3b8" opacity={0.5}>
                {ZODIAC_GLYPHS[i]}
              </text>
            </g>
          );
        })}

        {filteredAspects.map((aspect, i) => {
          const p1 = getPlanetPos(positions[aspect.planet1].longitude, planetR * 0.95);
          const p2 = getPlanetPos(positions[aspect.planet2].longitude, planetR * 0.95);
          const config = ASPECT_CONFIG[aspect.type];
          const opacity = Math.max(0.3, 1 - aspect.orb / config.orb);

          return (
            <line
              key={`aspect-${i}`}
              x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke={config.color}
              strokeWidth={aspect.orb < 2 ? 2 : 1.5}
              opacity={opacity * 0.7}
              strokeLinecap="round"
            />
          );
        })}

        {/* ASC / DSC / MC / IC axis lines */}
        {(() => {
          const ascP = getPlanetPos(ascLon, outerR);
          const dscP = getPlanetPos(ascLon + 180, outerR);
          const mcLon = positions.midheaven?.longitude || (ascLon + 270);
          const mcP = getPlanetPos(mcLon, outerR);
          const icP = getPlanetPos(mcLon + 180, outerR);
          return (
            <>
              <line x1={ascP.x} y1={ascP.y} x2={dscP.x} y2={dscP.y} stroke="rgba(253,224,71,0.2)" strokeWidth={1} strokeDasharray="5,4" />
              <line x1={mcP.x} y1={mcP.y} x2={icP.x} y2={icP.y} stroke="rgba(253,224,71,0.15)" strokeWidth={1} strokeDasharray="5,4" />
              <text x={ascP.x - 16} y={ascP.y + 3} fontSize={size * 0.025} fill="rgba(253,224,71,0.6)" fontWeight="bold" fontFamily="monospace">ASC</text>
              <text x={dscP.x + 4} y={dscP.y + 3} fontSize={size * 0.025} fill="rgba(253,224,71,0.4)" fontWeight="bold" fontFamily="monospace">DSC</text>
              <text x={mcP.x - 7} y={mcP.y - 7} fontSize={size * 0.025} fill="rgba(253,224,71,0.4)" fontWeight="bold" fontFamily="monospace">MC</text>
            </>
          );
        })()}

        {Object.entries(positions).map(([name, pos]) => {
          const p = getPlanetPos(pos.longitude, planetR);
          const color = PLANET_COLORS[name] || '#94a3b8';
          const glyph = PLANET_GLYPHS[name] || name[0].toUpperCase();

          return (
            <g key={name}>
              <title>{PLANET_MEANINGS[name] || name}</title>
              <circle cx={p.x} cy={p.y} r={size * 0.025} fill={color} opacity={0.2} />
              <text x={p.x} y={p.y + size * 0.008} textAnchor="middle"
                    fontSize={size * 0.035} fill={color} fontWeight="bold">
                {glyph}
              </text>
              {pos.retrograde && (
                <text x={p.x + size * 0.02} y={p.y - size * 0.015}
                      fontSize={size * 0.02} fill="#ef4444" opacity={0.7}>℞</text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="flex flex-wrap gap-2 justify-center">
        {(Object.keys(ASPECT_CONFIG) as AspectType[]).map(type => {
          const config = ASPECT_CONFIG[type];
          const isActive = visibleAspects.has(type);
          const count = aspects.filter(a => a.type === type).length;
          return (
            <button
              key={type}
              type="button"
              onClick={() => toggleAspect(type)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-mono transition-all border"
              style={{
                borderColor: isActive ? config.color : 'rgba(255,255,255,0.1)',
                backgroundColor: isActive ? `${config.color}15` : 'transparent',
                color: isActive ? config.color : '#64748b',
                opacity: isActive ? 1 : 0.5,
              }}
            >
              <span style={{ color: config.color }}>{config.symbol}</span>
              <span>{config.label}</span>
              <span className="text-[8px] opacity-60">({count})</span>
            </button>
          );
        })}
      </div>

      <div className="max-w-md w-full space-y-1">
        <div className="text-[9px] font-mono uppercase text-gray-500 text-center mb-1">Active Aspects</div>
        {filteredAspects.slice(0, 8).map((aspect, i) => {
          const config = ASPECT_CONFIG[aspect.type];
          return (
            <div key={i} className="flex items-center justify-between text-[10px] font-mono px-2 py-0.5 rounded"
                 style={{ backgroundColor: `${config.color}08` }}>
              <span className="flex items-center gap-1.5">
                <span style={{ color: PLANET_COLORS[aspect.planet1] }}>
                  {PLANET_GLYPHS[aspect.planet1] || aspect.planet1}
                </span>
                <span style={{ color: config.color }}>{config.symbol}</span>
                <span style={{ color: PLANET_COLORS[aspect.planet2] }}>
                  {PLANET_GLYPHS[aspect.planet2] || aspect.planet2}
                </span>
              </span>
              <span className="text-gray-500">
                {aspect.orb.toFixed(2)}° orb
              </span>
            </div>
          );
        })}
      </div>

      <Collapse
        ghost
        size="small"
        className="!mt-3 w-full max-w-md"
        items={[
          {
            key: 'llm',
            label: <Text className="!text-xs !font-mono !text-cyan-400">🔮 Ask the Astrologer — Chart Interpretation</Text>,
            children: (
              <div className="space-y-2">
                <Input.TextArea
                  value={llmQuestion}
                  onChange={(e) => setLlmQuestion(e.target.value)}
                  placeholder="Ask a follow-up question... (e.g. 'What does my Venus square Mars mean for love?')"
                  autoSize={{ minRows: 1, maxRows: 3 }}
                  onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); if (!llmLoading) askChartLLM(); } }}
                />
                <div className="flex gap-2">
                  <Button
                    type="primary"
                    size="small"
                    loading={llmLoading}
                    onClick={askChartLLM}
                    className="flex-1"
                  >
                    {llmLoading ? 'Consulting...' : llmHistory.length > 0 ? 'Ask' : 'Interpret My Chart'}
                  </Button>
                  {llmHistory.length > 0 && (
                    <Button
                      size="small"
                      onClick={() => { setLlmHistory([]); setLlmResponse(''); setLlmQuestion(''); }}
                    >
                      New Reading
                    </Button>
                  )}
                </div>
                {llmHistory.length > 0 && (
                  <div className="space-y-2 max-h-[500px] overflow-y-auto">
                    {llmHistory.map((msg, i) => (
                      <div
                        key={i}
                        className={`text-xs leading-relaxed p-3 rounded-lg border ${
                          msg.role === 'user'
                            ? 'bg-purple-950/20 border-purple-500/15 text-purple-200'
                            : 'bg-black/40 border-white/5 text-gray-300'
                        }`}
                      >
                        {msg.role === 'user' && <span className="text-[9px] font-mono text-purple-400/60 block mb-1">YOU</span>}
                        {msg.role === 'assistant' && <span className="text-[9px] font-mono text-cyan-400/60 block mb-1">ASTROLOGER</span>}
                        <span className="whitespace-pre-wrap">{msg.content}</span>
                      </div>
                    ))}
                  </div>
                )}
                {llmLoading && (
                  <div className="text-xs text-gray-500 text-center py-2 animate-pulse">Consulting the stars...</div>
                )}
              </div>
            ),
          },
          {
            key: 'guide',
            label: <Text className="!text-xs !font-mono !text-purple-400">📖 Symbol Reference Guide</Text>,
            children: (
              <div className="space-y-3">
                <div>
                  <Text className="!text-[10px] !font-mono !uppercase !text-gray-500 block mb-1">Planets</Text>
                  <div className="grid grid-cols-2 gap-1">
                    {Object.entries(PLANET_MEANINGS).map(([key, meaning]) => (
                      <div key={key} className="text-[10px] text-gray-400 flex items-center gap-1">
                        <span style={{ color: PLANET_COLORS[key] }} className="font-bold text-sm">{PLANET_GLYPHS[key]}</span>
                        <span>{meaning.split('—')[1]?.trim()}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <Text className="!text-[10px] !font-mono !uppercase !text-gray-500 block mb-1">Zodiac Signs</Text>
                  <div className="grid grid-cols-2 gap-1">
                    {ZODIAC_MEANINGS.map((z, i) => (
                      <div key={i} className="text-[10px] text-gray-400">
                        {z}
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <Text className="!text-[10px] !font-mono !uppercase !text-gray-500 block mb-1">Aspects</Text>
                  <div className="grid grid-cols-2 gap-1">
                    {(Object.keys(ASPECT_CONFIG) as AspectType[]).map(type => {
                      const c = ASPECT_CONFIG[type];
                      return (
                        <div key={type} className="text-[10px] text-gray-400 flex items-center gap-1">
                          <span style={{ color: c.color }} className="font-bold">{c.symbol}</span>
                          <span>{c.label} ({c.angle}°)</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
