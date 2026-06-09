/**
 * Unit tests for astroHelpers.js — the shared pure-logic module.
 *
 * Covers: aspect classification, planet/sign/angle glyph maps, SVG
 * positioning math, field-selection filtering, and markdown export.
 * All tests run in node env (no jsdom needed) because the module
 * is pure data + functions with no React or DOM dependencies.
 */
import { describe, it, expect } from 'vitest';
import {
  HARMONIOUS_ASPECTS, CHALLENGING_ASPECTS,
  aspectCategory, aspectGlyph, planetGlyph,
  isHarmonious, isChallenging, countByCategory,
  SIGN_GLYPHS, SIGN_NAMES, SIGN_ELEMENT, ELEMENT_COLORS,
  signElement, signElementColor, signName,
  toSvgAngle, polarToXY, describeArc,
  isHouseCusp, houseLabel, natalDisplayName,
  applyFieldSelection, toMarkdown,
} from '../lib/astroHelpers';

describe('aspectCategory', () => {
  it('classifies trine/sextile/conjunction as harmonious', () => {
    expect(aspectCategory('trine')).toBe('harmonious');
    expect(aspectCategory('sextile')).toBe('harmonious');
    expect(aspectCategory('conjunction')).toBe('harmonious');
  });

  it('classifies square/opposition as challenging', () => {
    expect(aspectCategory('square')).toBe('challenging');
    expect(aspectCategory('opposition')).toBe('challenging');
  });

  it('classifies unknown as minor', () => {
    expect(aspectCategory('quincunx')).toBe('minor');
    expect(aspectCategory('semisextile')).toBe('minor');
    expect(aspectCategory('unknown')).toBe('minor');
  });

  it('is case-insensitive', () => {
    expect(aspectCategory('TRINE')).toBe('harmonious');
    expect(aspectCategory('Trine')).toBe('harmonious');
    expect(aspectCategory('SQUARE')).toBe('challenging');
    expect(aspectCategory('Opposition')).toBe('challenging');
  });

  it('handles null/undefined/empty gracefully', () => {
    expect(aspectCategory(null)).toBe('minor');
    expect(aspectCategory(undefined)).toBe('minor');
    expect(aspectCategory('')).toBe('minor');
  });

  it('exposes the underlying Sets as lowercase keys', () => {
    expect(HARMONIOUS_ASPECTS.has('trine')).toBe(true);
    expect(HARMONIOUS_ASPECTS.has('Trine')).toBe(false);
    expect(CHALLENGING_ASPECTS.has('square')).toBe(true);
  });
});

describe('isHarmonious / isChallenging', () => {
  it('return true only for the matching category', () => {
    expect(isHarmonious('trine')).toBe(true);
    expect(isHarmonious('square')).toBe(false);
    expect(isChallenging('square')).toBe(true);
    expect(isChallenging('trine')).toBe(false);
  });
});

describe('countByCategory', () => {
  it('counts aspects in each category', () => {
    const aspects = [
      { aspect: 'trine' }, { aspect: 'sextile' }, { aspect: 'conjunction' },
      { aspect: 'square' }, { aspect: 'opposition' },
      { aspect: 'quincunx' },
    ];
    const counts = countByCategory(aspects);
    expect(counts.harmonious).toBe(3);
    expect(counts.challenging).toBe(2);
    expect(counts.minor).toBe(1);
  });

  it('returns zeros for empty input', () => {
    expect(countByCategory([])).toEqual({ harmonious: 0, challenging: 0, minor: 0 });
    expect(countByCategory(null)).toEqual({ harmonious: 0, challenging: 0, minor: 0 });
  });
});

describe('aspectGlyph', () => {
  it('returns a glyph for known aspects', () => {
    expect(aspectGlyph('conjunction')).toBeTruthy();
    expect(aspectGlyph('trine')).toBeTruthy();
    expect(aspectGlyph('square')).toBeTruthy();
    expect(aspectGlyph('opposition')).toBeTruthy();
    expect(aspectGlyph('sextile')).toBeTruthy();
  });

  it('is case-insensitive', () => {
    expect(aspectGlyph('Conjunction')).toBe(aspectGlyph('conjunction'));
    expect(aspectGlyph('TRINE')).toBe(aspectGlyph('trine'));
  });

  it('returns a placeholder for unknown aspects', () => {
    expect(aspectGlyph('xyz')).toBeTruthy();
  });
});

describe('planetGlyph', () => {
  it('returns a glyph for all 10 standard planets', () => {
    const planets = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];
    for (const p of planets) {
      expect(planetGlyph(p)).toBeTruthy();
    }
  });

  it('returns a glyph for lunar nodes and chiron', () => {
    expect(planetGlyph('north_node')).toBeTruthy();
    expect(planetGlyph('south_node')).toBeTruthy();
    expect(planetGlyph('chiron')).toBeTruthy();
  });

  it('returns a placeholder for unknown bodies', () => {
    expect(planetGlyph('unknown_body')).toBeTruthy();
  });
});

describe('SIGN_GLYPHS / SIGN_NAMES / SIGN_ELEMENT', () => {
  it('all arrays have 12 entries (one per zodiac sign)', () => {
    expect(SIGN_GLYPHS).toHaveLength(12);
    expect(SIGN_NAMES).toHaveLength(12);
    expect(SIGN_ELEMENT).toHaveLength(12);
  });

  it('SIGN_NAMES starts with Aries and ends with Pisces', () => {
    expect(SIGN_NAMES[0]).toBe('Aries');
    expect(SIGN_NAMES[11]).toBe('Pisces');
  });

  it('SIGN_ELEMENT cycles through Fire/Earth/Air/Water 3x', () => {
    expect(SIGN_ELEMENT).toEqual([
      'Fire', 'Earth', 'Air', 'Water', 'Fire', 'Earth',
      'Air', 'Water', 'Fire', 'Earth', 'Air', 'Water',
    ]);
  });

  it('ELEMENT_COLORS has all 4 elements', () => {
    expect(ELEMENT_COLORS.Fire).toBeTruthy();
    expect(ELEMENT_COLORS.Earth).toBeTruthy();
    expect(ELEMENT_COLORS.Air).toBeTruthy();
    expect(ELEMENT_COLORS.Water).toBeTruthy();
  });
});

describe('signElement / signElementColor / signName', () => {
  it('signElement returns the right element per sign index', () => {
    expect(signElement(0)).toBe('Fire');
    expect(signElement(1)).toBe('Earth');
    expect(signElement(2)).toBe('Air');
    expect(signElement(3)).toBe('Water');
    expect(signElement(11)).toBe('Water');
  });

  it('signName returns the right name per sign index', () => {
    expect(signName(0)).toBe('Aries');
    expect(signName(6)).toBe('Libra');
    expect(signName(11)).toBe('Pisces');
  });

  it('signElementColor returns the hex color for the sign', () => {
    expect(signElementColor(0)).toBe(ELEMENT_COLORS.Fire);
    expect(signElementColor(1)).toBe(ELEMENT_COLORS.Earth);
  });

  it('handles out-of-range indices by wrapping (mod 12)', () => {
    expect(signElement(12)).toBe('Fire');
    expect(signElement(14)).toBe('Air');
    expect(signName(12)).toBe('Aries');
  });
});

describe('toSvgAngle', () => {
  it('planet at ASC longitude appears at 9 o\'clock (180°)', () => {
    expect(toSvgAngle(0, 0)).toBe(180);
    expect(toSvgAngle(120, 120)).toBe(180);
  });

  it('planet 90° ahead of ASC appears at IC (6 o\'clock, 90°)', () => {
    expect(toSvgAngle(90, 0)).toBe(90);
  });

  it('planet 180° from ASC appears at DSC (3 o\'clock, 0°)', () => {
    expect(toSvgAngle(180, 0)).toBe(0);
  });

  it('planet 270° from ASC appears at MC (12 o\'clock, 270°)', () => {
    expect(toSvgAngle(270, 0)).toBe(270);
  });

  it('handles wrap-around when longitude < ascendant', () => {
    expect(toSvgAngle(20, 350)).toBe(150);
  });

  it('returns a value in [0, 360)', () => {
    for (let lon = 0; lon < 360; lon += 30) {
      for (let asc = 0; asc < 360; asc += 30) {
        const angle = toSvgAngle(lon, asc);
        expect(angle).toBeGreaterThanOrEqual(0);
        expect(angle).toBeLessThan(360);
      }
    }
  });
});

describe('polarToXY', () => {
  it('angle 0 places point to the right of center', () => {
    const { x, y } = polarToXY(100, 100, 50, 0);
    expect(x).toBeCloseTo(150);
    expect(y).toBeCloseTo(100);
  });

  it('angle 90 places point below center (SVG Y down)', () => {
    const { x, y } = polarToXY(100, 100, 50, 90);
    expect(x).toBeCloseTo(100);
    expect(y).toBeCloseTo(150);
  });

  it('angle 180 places point to the left of center', () => {
    const { x, y } = polarToXY(100, 100, 50, 180);
    expect(x).toBeCloseTo(50);
    expect(y).toBeCloseTo(100);
  });

  it('angle 270 places point above center', () => {
    const { x, y } = polarToXY(100, 100, 50, 270);
    expect(x).toBeCloseTo(100);
    expect(y).toBeCloseTo(50);
  });

  it('zero radius returns the center point', () => {
    const { x, y } = polarToXY(100, 100, 0, 45);
    expect(x).toBe(100);
    expect(y).toBe(100);
  });
});

describe('describeArc', () => {
  it('returns a valid SVG path starting with M', () => {
    const d = describeArc(100, 100, 50, 0, 90);
    expect(d).toMatch(/^M \d+(\.\d+)? \d+(\.\d+)? A 50 50 0 [01] [01] \d+(\.\d+)? \d+(\.\d+)?$/);
  });

  it('uses large-arc flag for arcs > 180°', () => {
    expect(describeArc(0, 0, 10, 0, 270)).toMatch(/A 10 10 0 1 /);
  });

  it('uses small-arc flag for arcs <= 180°', () => {
    expect(describeArc(0, 0, 10, 0, 90)).toMatch(/A 10 10 0 0 /);
  });
});

describe('isHouseCusp / houseLabel / natalDisplayName', () => {
  it('isHouseCusp detects house_N pattern', () => {
    expect(isHouseCusp('house_1')).toBe(true);
    expect(isHouseCusp('house_12')).toBe(true);
    expect(isHouseCusp('sun')).toBe(false);
    expect(isHouseCusp(null)).toBe(false);
    expect(isHouseCusp(undefined)).toBe(false);
    expect(isHouseCusp(123)).toBe(false);
  });

  it('houseLabel strips house_ prefix', () => {
    expect(houseLabel('house_1')).toBe('H1');
    expect(houseLabel('house_12')).toBe('H12');
    expect(houseLabel('sun')).toBe('sun');
  });

  it('natalDisplayName prefixes with "Natal Cusp" for cusps', () => {
    expect(natalDisplayName('house_7')).toBe('Natal Cusp H7');
    expect(natalDisplayName('sun')).toBe('Natal sun');
  });
});

describe('applyFieldSelection', () => {
  const topLevel = [
    { key: 'version', label: 'Version', required: true },
    { key: 'exported_at', label: 'Time' },
    { key: 'charts', label: 'Charts', required: true },
  ];
  const fieldGroups = [
    { key: 'name', label: 'Name', required: true },
    { key: 'city', label: 'City' },
    { key: 'tags', label: 'Tags' },
  ];

  it('filters charts by id set', () => {
    const payload = {
      version: '2.0',
      exported_at: '2026-06-03T00:00:00Z',
      charts: [
        { id: 1, name: 'A', city: 'X', tags: 't' },
        { id: 2, name: 'B', city: 'Y', tags: 'u' },
        { id: 3, name: 'C', city: 'Z', tags: 'v' },
      ],
    };
    const result = applyFieldSelection(
      payload, new Set([1, 3]), new Set(['version', 'exported_at', 'charts', 'name', 'city']),
      topLevel, fieldGroups
    );
    expect(result.charts).toHaveLength(2);
    expect(result.charts.map(c => c.id)).toEqual([1, 3]);
  });

  it('filters fields per selectedFieldKeys', () => {
    const payload = {
      version: '2.0',
      exported_at: '2026-06-03T00:00:00Z',
      charts: [{ id: 1, name: 'A', city: 'X', tags: 't' }],
    };
    const result = applyFieldSelection(
      payload, new Set([1]), new Set(['name']), topLevel, fieldGroups
    );
    expect(result.charts[0]).toEqual({ id: 1, name: 'A' });
    expect(result.version).toBeUndefined();
  });

  it('returns empty charts array when no ids match', () => {
    const payload = { version: '2.0', charts: [{ id: 1, name: 'A' }] };
    const result = applyFieldSelection(
      payload, new Set([99]), new Set(['name']), topLevel, fieldGroups
    );
    expect(result.charts).toEqual([]);
  });

  it('handles payload without charts field', () => {
    const result = applyFieldSelection(
      { version: '2.0' }, new Set(), new Set(['version']),
      topLevel, fieldGroups
    );
    expect(result.charts).toEqual([]);
    expect(result.version).toBe('2.0');
  });
});

describe('toMarkdown', () => {
  const topLevel = [
    { key: 'version', label: 'Version', required: true },
    { key: 'exported_at', label: 'Time', required: true },
    { key: 'system', label: 'System' },
    { key: 'charts', label: 'Charts', required: true },
  ];
  const fieldGroups = [
    { key: 'name', label: 'Name', required: true },
    { key: 'birth_time_iso', label: 'Birth Time' },
    { key: 'city', label: 'City' },
    { key: 'latitude', label: 'Lat' },
    { key: 'longitude', label: 'Lon' },
    { key: 'timezone', label: 'TZ' },
    { key: 'description', label: 'Description' },
    { key: 'tags', label: 'Tags' },
    { key: 'notes', label: 'Notes' },
    { key: 'cached_data', label: 'Cached' },
  ];

  it('emits a top-level heading and metadata', () => {
    const md = toMarkdown(
      { version: '2.0', exported_at: '2026-06-03T00:00:00Z', system: 'test', charts: [] },
      new Set(['version', 'exported_at', 'system']),
      topLevel, fieldGroups
    );
    expect(md).toContain('# Saved Natal Charts Export');
    expect(md).toContain('**Exported**: 2026-06-03T00:00:00Z');
    expect(md).toContain('**System**: test');
    expect(md).toContain('**Schema version**: 2.0');
    expect(md).toContain('**Charts in this export**: 0');
  });

  it('renders a chart section with name and details', () => {
    const md = toMarkdown(
      {
        version: '2.0', exported_at: '2026-06-03', system: 'test',
        charts: [{
          id: 1, name: 'Test Profile',
          birth_time_iso: '1990-01-01T00:00:00',
          city: 'London', latitude: 51.5, longitude: -0.12, timezone: 'Europe/London',
          description: 'A test chart',
          tags: 'test,profile', notes: 'no notes',
        }],
      },
      new Set(fieldGroups.map(f => f.key)),
      topLevel, fieldGroups
    );
    expect(md).toContain('## Test Profile');
    expect(md).toContain('- **Born**: 1990-01-01T00:00:00');
    expect(md).toContain('- **Location**: London');
    expect(md).toContain('- **Description**: A test chart');
    expect(md).toContain('- **Tags**: test,profile');
    expect(md).toContain('- **Notes**: no notes');
  });

  it('expands cached_data into planets, angles, houses', () => {
    const md = toMarkdown(
      {
        version: '2.0', exported_at: '', system: '',
        charts: [{
          id: 1, name: 'Full',
          birth_time_iso: '', city: '', latitude: null, longitude: null, timezone: '',
          description: '', tags: '', notes: '',
          cached_data: {
            datetime: '1990-01-01T00:00:00',
            western: {
              positions: {
                sun: { formatted: 'Capricorn 10.00\u00B0', sign: 'Capricorn', degree: 10 },
                moon: { formatted: 'Cancer 20.00\u00B0', sign: 'Cancer', degree: 20 },
                ascendant: { formatted: 'Scorpio 5.00\u00B0' },
                midheaven: { formatted: 'Leo 12.00\u00B0' },
                north_node: { formatted: 'Libra 30.00\u00B0' },
              },
              houses: {
                house_1: { formatted: 'Scorpio 5.00\u00B0' },
                house_7: { formatted: 'Taurus 5.00\u00B0' },
              },
              dominant_element: 'Water',
              dominant_modality: 'Cardinal',
            },
          },
        }],
      },
      new Set(['name', 'birth_time_iso', 'cached_data']),
      topLevel, fieldGroups
    );
    expect(md).toContain('**Western planets**:');
    expect(md).toContain('Sun');
    expect(md).toContain('Moon');
    expect(md).toContain('**Angles**:');
    expect(md).toContain('ascendant');
    expect(md).toContain('**House cusps**:');
    expect(md).toContain('house_1');
    expect(md).toContain('**Dominant element**: Water');
  });

  it('respects field selection (omits non-selected)', () => {
    const md = toMarkdown(
      {
        version: '2.0', exported_at: '', system: '',
        charts: [{
          id: 1, name: 'A', birth_time_iso: 'X',
          city: 'C', latitude: 1, longitude: 2, timezone: 'TZ',
          description: 'D', tags: 'T', notes: 'N',
        }],
      },
      new Set(['name']),
      topLevel, fieldGroups
    );
    expect(md).toContain('## A');
    expect(md).not.toContain('**Born**');
    expect(md).not.toContain('**Description**');
  });

  it('handles empty charts array', () => {
    const md = toMarkdown(
      { version: '2.0', exported_at: '', system: '', charts: [] },
      new Set(['name']),
      topLevel, fieldGroups
    );
    expect(md).toContain('# Saved Natal Charts Export');
    expect(md).toContain('**Charts in this export**: 0');
  });

  it('handles missing cached_data gracefully', () => {
    const md = toMarkdown(
      {
        version: '2.0', exported_at: '', system: '',
        charts: [{ id: 1, name: 'NoCache' }],
      },
      new Set(['name', 'cached_data']),
      topLevel, fieldGroups
    );
    expect(md).toContain('## NoCache');
    expect(md).not.toContain('**Western planets**');
  });
});
