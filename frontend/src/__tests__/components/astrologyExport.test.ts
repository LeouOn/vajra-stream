import { describe, it, expect } from 'vitest';
import {
  formatNatalChartMarkdown,
  formatTransitReportMarkdown,
  formatTransitReportJSON,
  formatLiveAstrologyMarkdown,
} from '../../lib/astrologyExport';

// Glyphs that must NEVER appear in LLM-optimized output.
const FORBIDDEN_GLYPHS = [
  '\u2609', '\u263D', '\u263F', '\u2640', '\u2642', '\u2643', '\u2644',
  '\u2645', '\u2646', '\u2647', '\u260A', '\u260B', // planet glyphs
  '\u2648', '\u2649', '\u264A', '\u264B', '\u264C', '\u264D',
  '\u264E', '\u264F', '\u2650', '\u2651', '\u2652', '\u2653', // zodiac glyphs
  '\u25B3', '\u25A1', '\u260C', '\u26B9', '\u260D', // aspect glyphs
];

const natalData = {
  name: 'John Doe',
  birth_time_iso: '1990-06-15T14:30:00+00:00',
  birth_location: { latitude: 37.7749, longitude: -122.4194 },
  western: {
    positions: {
      sun: { longitude: 84.58, sign: 'Gemini', degree: 24.58, house: 11 },
      moon: { longitude: 92.55, sign: 'Cancer', degree: 2.55, house: 11 },
      mercury: { longitude: 80.0, sign: 'Gemini', degree: 20.0, house: 11 },
      venus: { longitude: 70.0, sign: 'Taurus', degree: 10.0, house: 10, retrograde: true },
      mars: { longitude: 200.0, sign: 'Libra', degree: 20.0, house: 3 },
      ascendant: { longitude: 127.63, sign: 'Leo', degree: 7.63 },
      midheaven: { longitude: 27.08, sign: 'Aries', degree: 27.08 },
    },
    elements: { Fire: 4, Earth: 2, Air: 5, Water: 6 },
    modalities: { Cardinal: 10, Fixed: 4, Mutable: 5 },
    dominant_element: 'Water',
    dominant_modality: 'Cardinal',
    aspects: [
      {
        planet1: 'sun',
        planet2: 'moon',
        aspect: 'Conjunction',
        angle: 7.96,
        exactness: 0.04,
        description: 'Sun Conjunction Moon (Orb: 7.96\u00B0)',
      },
      {
        planet1: 'moon',
        planet2: 'neptune',
        aspect: 'Square',
        // `angle` is the angular distance between the two planets.
        // Square target = 90°, so orb = |91.74 - 90| = 1.74°.
        angle: 91.74,
        exactness: 0.78,
        description: 'Moon Square Neptune (Orb: 1.74\u00B0)',
      },
      {
        planet1: 'venus',
        planet2: 'uranus',
        aspect: 'Sextile',
        // Sextile target = 60°; orb = |70 - 60| = 10° -> filtered out by orb < 8.
        angle: 70.0,
        exactness: 0.05,
        description: 'Venus Sextile Uranus (Orb: 10.00\u00B0)',
      },
    ],
  },
  vedic: {
    tithi: { number: 1, name: 'Prathama', paksha: 'Shukla', progress: 0.12 },
    nakshatra: { number: 6, name: 'Ardra', progress: 0.12 },
    yoga: { number: 1, name: 'Ganda', progress: 0.5 },
    karana: { number: 1, name: 'Bava' },
    vara: { name: 'Ravivara (Sunday)', index: 0 },
    ascendant: { rashi_name: 'Karka', degree: 13.4, longitude: 103.4 },
    planets: {
      sun: { rashi_name: 'Mithuna', degree: 0.4, longitude: 60.4 },
      moon: { rashi_name: 'Mithuna', degree: 8.3, longitude: 68.3 },
    },
    ayanamsa: 23.8,
  },
  houses: {
    sun: { sign: 'Gemini', degree: 24.58, longitude: 84.58, house_placidus: 11, house_whole_sign: 11 },
    moon: { sign: 'Cancer', degree: 2.55, longitude: 92.55, house_placidus: 11, house_whole_sign: 11 },
    venus: { sign: 'Taurus', degree: 10.0, longitude: 70.0, house_placidus: 10, house_whole_sign: 10 },
    ascendant: { sign: 'Leo', degree: 7.63, longitude: 127.63, house_placidus: 1, house_whole_sign: 1 },
    midheaven: { sign: 'Aries', degree: 27.08, longitude: 27.08, house_placidus: 10, house_whole_sign: 10 },
  },
};

describe('formatNatalChartMarkdown', () => {
  it('renders all sections in the canonical order', () => {
    const result = formatNatalChartMarkdown(natalData);
    expect(result).toContain('# Natal Chart: John Doe');
    expect(result).toContain('## Planetary Placements');
    expect(result).toContain('## Element Balance');
    expect(result).toContain('## Modalities');
    expect(result).toContain('## Major Aspects (orb < 8\u00B0)');
    expect(result).toContain('## Vedic (Sidereal / Lahiri)');

    const sectionOrder = [
      result.indexOf('## Planetary Placements'),
      result.indexOf('## Element Balance'),
      result.indexOf('## Modalities'),
      result.indexOf('## Major Aspects'),
      result.indexOf('## Vedic'),
    ];
    for (let i = 0; i < sectionOrder.length - 1; i++) {
      expect(sectionOrder[i]).toBeLessThan(sectionOrder[i + 1]);
    }
  });

  it('is completely glyph-free', () => {
    const result = formatNatalChartMarkdown(natalData);
    for (const g of FORBIDDEN_GLYPHS) {
      expect(result).not.toContain(g);
    }
  });

  it('renders the planetary placements table with houses resolved from the houses map', () => {
    const result = formatNatalChartMarkdown(natalData);
    expect(result).toContain('| Planet | Sign | Degree | House |');
    expect(result).toContain('| Sun | Gemini | 24.58\u00B0 | 11 |');
    expect(result).toContain('| Moon | Cancer | 2.55\u00B0 | 11 |');
    // Ascendant house comes from the houses map (= 1)
    expect(result).toContain('| Ascendant | Leo | 7.63\u00B0 | 1 |');
  });

  it('appends (R) for retrograde planets', () => {
    const result = formatNatalChartMarkdown(natalData);
    expect(result).toContain('| Venus | Taurus (R) |');
  });

  it('marks the dominant element and modality', () => {
    const result = formatNatalChartMarkdown(natalData);
    expect(result).toContain('- Water: 6 points (dominant)');
    expect(result).toContain('- Cardinal: 10 points (dominant)');
  });

  it('groups aspects harmonious-then-challenging and computes orb from angle when absent', () => {
    const result = formatNatalChartMarkdown(natalData);
    // Harmonious: Sun conjunction Moon (orb = |7.96 - 0| = 7.96)
    expect(result).toContain('- Sun conjunction Moon \u2014 orb 7.96\u00B0');
    // Venus sextile Uranus has orb 10° (>= 8), filtered out.
    expect(result).not.toContain('Venus sextile Uranus');
    // Challenging: Moon square Neptune (orb = |91.74 - 90| = 1.74)
    expect(result).toContain('- Moon square Neptune \u2014 orb 1.74\u00B0');
    // Harmonious block must appear before Challenging block
    expect(result.indexOf('**Harmonious:**')).toBeLessThan(result.indexOf('**Challenging:**'));
  });

  it('does not duplicate the aspect word (no "Conjunction...Conjunction")', () => {
    const result = formatNatalChartMarkdown(natalData);
    expect(result).not.toMatch(/Conjunction.*Conjunction/);
    expect(result).not.toMatch(/\bSquare\b.*\bSquare\b/);
  });

  it('renders Vedic panchanga with paksha/phase and progress percentage', () => {
    const result = formatNatalChartMarkdown(natalData);
    expect(result).toContain('- Tithi: Prathama (Shukla/waxing, 12%)');
    expect(result).toContain('- Nakshatra: Ardra (12%)');
    expect(result).toContain('- Yoga: Ganda');
    expect(result).toContain('- Karana: Bava');
    expect(result).toContain('- Vara: Ravivara (Sunday)');
    expect(result).toContain('- Ascendant: Karka 13.40\u00B0');
    expect(result).toContain('- Sun: Mithuna 0.40\u00B0');
    expect(result).toContain('- Moon: Mithuna 8.30\u00B0');
  });

  it('handles empty aspects gracefully', () => {
    const data = { ...natalData, western: { ...natalData.western, aspects: [] } };
    const result = formatNatalChartMarkdown(data);
    expect(result).toContain('**Harmonious:**');
    expect(result).toContain('- None within orb');
    expect(result).toContain('**Challenging:**');
  });

  it('handles missing Vedic data gracefully', () => {
    const data = { ...natalData, vedic: {} };
    const result = formatNatalChartMarkdown(data);
    expect(result).toContain('## Vedic (Sidereal / Lahiri)');
    expect(result).toContain('- Tithi: \u2014');
  });

  it('handles null/undefined positions gracefully', () => {
    const data = { ...natalData, western: { ...natalData.western, positions: null }, houses: {} };
    const result = formatNatalChartMarkdown(data);
    expect(result).toContain('## Planetary Placements');
    expect(result).toContain('No positional data.');
  });

  it('returns a fallback string for null input', () => {
    const result = formatNatalChartMarkdown(null);
    expect(typeof result).toBe('string');
    expect(result).toContain('Natal Chart');
  });
});

describe('formatTransitReportMarkdown', () => {
  const transitData = {
    name: 'Transit Subject',
    birth_time_iso: '1990-06-15T12:00:00+00:00',
    transit_time: '2026-06-01T12:00:00+00:00',
    natal_houses: {
      sun: { sign: 'Aries', degree: 10.5, house_placidus: 1, house_whole_sign: 1 },
    },
    transit_houses: {
      sun: { sign: 'Gemini', degree: 75.0, house_placidus: 3, house_whole_sign: 3 },
    },
    top_harmonious: [
      { transit_planet: 'moon', natal_planet: 'sun', aspect: 'Trine', exactness: 0.91, orb: 0.9 },
    ],
    top_challenging: [
      { transit_planet: 'mars', natal_planet: 'saturn', aspect: 'Square', exactness: 0.7, orb: 3.5 },
      { transit_planet: 'saturn', natal_planet: 'house_4', aspect: 'Opposition', exactness: 0.5, orb: 4.0 },
    ],
    gochara: {
      jupiter: { transit_rashi: 'Leo (Simha)', transit_degree: 5.0, gochara_house: 5 },
    },
    bazi_clashes: { interactions: [{ pillar: 'Day', type: 'Clash', description: 'Fire clashes with Metal' }] },
  };

  it('renders all six sections glyph-free', () => {
    const result = formatTransitReportMarkdown(transitData);
    expect(result).toContain('# Transit Report: Transit Subject');
    expect(result).toContain('## Natal Placements');
    expect(result).toContain('## Transit Placements');
    expect(result).toContain('## Harmonious Transits');
    expect(result).toContain('## Challenging Transits');
    expect(result).toContain('## BaZi');
    expect(result).toContain('## Gochara (from Natal Moon)');
    for (const g of FORBIDDEN_GLYPHS) {
      expect(result).not.toContain(g);
    }
  });

  it('formats transit aspects as "N. Transit X aspect Natal Y — P% exact · O° orb"', () => {
    const result = formatTransitReportMarkdown(transitData);
    expect(result).toContain('1. Transit Moon trine Natal Sun \u2014 91% exact \u00B7 0.90\u00B0 orb');
    // House cusp natal target rendered as "House 4"
    expect(result).toContain('Transit Saturn opposition Natal House 4');
  });

  it('renders the dual-house placements table', () => {
    const result = formatTransitReportMarkdown(transitData);
    expect(result).toContain('| Planet | Sign | Degree | House (P) | House (WS) |');
    expect(result).toContain('| Sun | Aries | 10.50\u00B0 | 1 | 1 |');
    expect(result).toContain('| Sun | Gemini | 75.00\u00B0 | 3 | 3 |');
  });

  it('handles empty data without throwing', () => {
    const result = formatTransitReportMarkdown({
      name: 'Empty',
      natal_houses: {},
      transit_houses: {},
      top_harmonious: [],
      top_challenging: [],
      gochara: {},
      bazi_clashes: { interactions: [] },
    });
    expect(typeof result).toBe('string');
    expect(result).toContain('None within orb.');
    expect(result).toContain('No BaZi interactions found.');
    expect(result).toContain('No Gochara data available.');
  });

  it('returns a fallback string for null input', () => {
    const result = formatTransitReportMarkdown(null);
    expect(result).toContain('Transit Report');
  });
});

describe('formatTransitReportJSON', () => {
  it('serializes data to pretty JSON', () => {
    const result = formatTransitReportJSON({ name: 'X', values: [1, 2] });
    const parsed = JSON.parse(result);
    expect(parsed.name).toBe('X');
    expect(parsed.values).toEqual([1, 2]);
  });

  it('handles null input', () => {
    const result = formatTransitReportJSON(null);
    expect(JSON.parse(result)).toBeNull();
  });
});

// ----------------------------------------------------------------------
// formatLiveAstrologyMarkdown
// ----------------------------------------------------------------------

const liveData = {
  datetime: '2026-06-15T14:30:00+00:00',
  location: { latitude: 37.7749, longitude: -122.4194 },
  western: {
    positions: {
      sun: { sign: 'Gemini', degree: 24.61, house: 11 },
      moon: { sign: 'Cancer', degree: 3.01, house: 11 },
      mercury: { sign: 'Cancer', degree: 19.11, house: 12 },
      pluto: { sign: 'Aquarius', degree: 5.16, house: 6, retrograde: true },
      ascendant: { sign: 'Leo', degree: 16.47 },
    },
    elements: { Fire: 4, Earth: 2, Air: 5, Water: 6 },
    modalities: { Cardinal: 10, Fixed: 4, Mutable: 5 },
    aspects: [
      { planet1: 'sun', planet2: 'moon', aspect: 'Conjunction', orb: 7.96 },
      { planet1: 'moon', planet2: 'neptune', aspect: 'Square', orb: 1.74 },
    ],
  },
  indian: {
    tithi: { name: 'Prathama', paksha: 'Shukla', percentage: 16 },
    nakshatra: { name: 'Ardra', percentage: 16 },
    yoga: { name: 'Ganda' },
    karana: { name: 'Bava' },
    vara: { name: 'Ravivara', lord: 'Sun' },
    ascendant: { sign: 'Karka', degree: 22.2 },
    planets: {
      sun: { sign: 'Mithuna', degree: 0.4 },
      moon: { sign: 'Mithuna', degree: 8.8 },
    },
  },
  chinese: {
    sheng_xiao: 'Horse',
    four_pillars: { year: 'Bing-Wu', month: 'Jia-Wu', day: 'Xin-You', hour: 'Wu-Zi' },
    five_elements_balance: { wood: 1, fire: 3, earth: 1, metal: 2, water: 1 },
  },
  moon_phase: { phase_name: 'Waxing Crescent', illumination: 0.5 },
  auspicious_times: { sunrise: '06:12', sunset: '20:34' },
  timestamp: 1781548000,
};

describe('formatLiveAstrologyMarkdown', () => {
  it('renders the current datetime and location in the header', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('# Current Astrology');
    expect(result).toContain('2026-06-15 14:30');
    expect(result).toContain('37.7749');
    expect(result).toContain('-122.4194');
  });

  it('includes moon phase section', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('## Moon Phase');
    expect(result).toContain('Waxing Crescent');
    expect(result).toContain('0.5');
  });

  it('renders Western planet table with houses', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('## Western Tropical');
    expect(result).toContain('| Planet | Sign | Degree | House |');
    expect(result).toContain('| Sun | Gemini | 24.61');
    expect(result).toContain('| Moon | Cancer | 3.01');
  });

  it('marks retrograde planets with (R)', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('Pluto');
    expect(result).toContain('(R)');
  });

  it('includes elements and modalities sections', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('### Elements');
    expect(result).toContain('Fire: 4 points');
    expect(result).toContain('Dominant: Water');
    expect(result).toContain('### Modalities');
    expect(result).toContain('Cardinal: 10');
  });

  it('renders active aspects with orb', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('### Active Aspects');
    expect(result).toContain('Sun Conjunction Moon');
    expect(result).toContain('orb 7.96');
    expect(result).toContain('Moon Square Neptune');
  });

  it('renders Vedic panchanga', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('## Vedic Sidereal');
    expect(result).toContain('Tithi: Prathama (Shukla)');
    expect(result).toContain('Nakshatra: Ardra (16%)');
    expect(result).toContain('Yoga: Ganda');
    expect(result).toContain('Karana: Bava');
    expect(result).toContain('Vara: Ravivara (Sun)');
  });

  it('renders Chinese BaZi four pillars', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('## Chinese Lunisolar');
    expect(result).toContain('Sheng Xiao: Horse');
    expect(result).toContain('Year: Bing-Wu');
  });

  it('includes auspicious times', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    expect(result).toContain('## Auspicious Times');
    expect(result).toContain('Sunrise: 06:12');
  });

  it('is completely glyph-free', () => {
    const result = formatLiveAstrologyMarkdown(liveData);
    for (const g of FORBIDDEN_GLYPHS) {
      expect(result).not.toContain(g);
    }
  });

  it('handles empty data gracefully', () => {
    const result = formatLiveAstrologyMarkdown({});
    expect(result).toContain('# Current Astrology');
    expect(typeof result).toBe('string');
  });

  it('handles null input with a fallback message', () => {
    const result = formatLiveAstrologyMarkdown(null);
    expect(result).toContain('No data available');
  });
});
