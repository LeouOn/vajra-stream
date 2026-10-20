/**
 * astroHelpers.js — pure logic shared across astrology UI components.
 *
 * Extracted from NatalChartWheel.jsx, ExportPanel.jsx, TransitComparison.jsx,
 * and SynastryViewer.jsx so the math and classification logic can be
 * unit-tested without mounting React. All functions are pure (no
 * closures, no side effects, no I/O) and node-environment safe.
 */

export const HARMONIOUS_ASPECTS = new Set(['trine', 'sextile', 'conjunction']);
export const CHALLENGING_ASPECTS = new Set(['square', 'opposition']);

export function aspectCategory(name) {
  const n = (typeof name === 'string' ? name : '').toLowerCase();
  if (HARMONIOUS_ASPECTS.has(n)) return 'harmonious';
  if (CHALLENGING_ASPECTS.has(n)) return 'challenging';
  return 'minor';
}

export function aspectGlyph(name) {
  const glyphs = {
    conjunction: '\u260C',
    sextile: '\u26B9',
    square: '\u25A1',
    trine: '\u25B3',
    opposition: '\u260D',
    quincunx: '\u26BB',
    quintile: '\u26F6',
  };
  return glyphs[(name || '').toLowerCase()] || '\u25CB';
}

export function isHarmonious(name) {
  return aspectCategory(name) === 'harmonious';
}

export function isChallenging(name) {
  return aspectCategory(name) === 'challenging';
}

export function countByCategory(aspects) {
  const counts = { harmonious: 0, challenging: 0, minor: 0 };
  for (const a of aspects || []) {
    const c = aspectCategory(a.aspect);
    counts[c]++;
  }
  return counts;
}

export const SIGN_GLYPHS = [
  '\u2648', '\u2649', '\u264A', '\u264B', '\u264C', '\u264D',
  '\u264E', '\u264F', '\u2650', '\u2651', '\u2652', '\u2653',
];

export const SIGN_NAMES = [
  'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
  'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces',
];

export const SIGN_ELEMENT = [
  'Fire', 'Earth', 'Air', 'Water', 'Fire', 'Earth',
  'Air', 'Water', 'Fire', 'Earth', 'Air', 'Water',
];

export const ELEMENT_COLORS = {
  Fire: '#dc2626',
  Earth: '#a16207',
  Air: '#ca8a04',
  Water: '#2563eb',
};

export function signElement(signIndex) {
  return SIGN_ELEMENT[signIndex % 12];
}

export function signElementColor(signIndex) {
  return ELEMENT_COLORS[signElement(signIndex)];
}

export function signName(signIndex) {
  return SIGN_NAMES[signIndex % 12];
}

export function toSvgAngle(longitude, ascendant) {
  const offset = (longitude - ascendant + 360) % 360;
  return (180 - offset + 360) % 360;
}

export function polarToXY(cx, cy, r, deg) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

export function describeArc(cx, cy, r, startDeg, endDeg) {
  const start = polarToXY(cx, cy, r, startDeg);
  const end = polarToXY(cx, cy, r, endDeg);
  const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  const sweep = endDeg > startDeg ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} ${sweep} ${end.x} ${end.y}`;
}

export const PLANET_GLYPHS = {
  sun: '\u2609', moon: '\u263D', mercury: '\u263F', venus: '\u2640', mars: '\u2642',
  jupiter: '\u2643', saturn: '\u2644', uranus: '\u2645', neptune: '\u2646', pluto: '\u2647',
  north_node: '\u260A', south_node: '\u260B', chiron: '\u26B7',
  ascendant: '\u27EA', midheaven: '\u27EA',
};

export function planetGlyph(name) {
  return PLANET_GLYPHS[name] || '\u25CF';
}

export function isHouseCusp(name) {
  return typeof name === 'string' && name.startsWith('house_');
}

export function houseLabel(name) {
  return isHouseCusp(name) ? name.replace('house_', 'H') : name;
}

export function natalDisplayName(name) {
  return isHouseCusp(name) ? `Natal Cusp ${houseLabel(name)}` : `Natal ${name}`;
}

/**
 * Narrow an export payload to the selected charts and field keys.
 *
 * @param {{ charts?: Array<{ id: unknown, [key: string]: unknown }>, [key: string]: unknown }} payload
 * @param {Set<unknown>} selectedChartIds
 * @param {Set<string>} selectedFieldKeys
 * @param {Array<{ key: string }>} topLevelFields
 * @param {Array<{ key: string }>} fieldGroups
 * @returns {{ charts: Array<{ id: unknown, [key: string]: unknown }>, [key: string]: unknown }}
 */
export function applyFieldSelection(payload, selectedChartIds, selectedFieldKeys, topLevelFields, fieldGroups) {
  const filteredCharts = (payload.charts || []).filter((c) => selectedChartIds.has(c.id));
  /** @type {Record<string, unknown>} */
  const topLevel = {};
  for (const f of topLevelFields) {
    if (selectedFieldKeys.has(f.key) && payload[f.key] !== undefined) {
      topLevel[f.key] = payload[f.key];
    }
  }
  const charts = filteredCharts.map((c) => {
    /** @type {{ id: unknown, [key: string]: unknown }} */
    const out = { id: c.id };
    for (const f of fieldGroups) {
      if (selectedFieldKeys.has(f.key) && c[f.key] !== undefined) {
        out[f.key] = c[f.key];
      }
    }
    return out;
  });
  return { ...topLevel, charts };
}

export function toMarkdown(payload, selectedFieldKeys, topLevelFields, fieldGroups, planetGlyphs = PLANET_GLYPHS) {
  const lines = [];
  lines.push('# Saved Natal Charts Export');
  lines.push('');
  if (selectedFieldKeys.has('exported_at') && payload.exported_at) {
    lines.push(`**Exported**: ${payload.exported_at}`);
  }
  if (selectedFieldKeys.has('system')) {
    lines.push(`**System**: ${payload.system || 'vajra-stream-astrology'}`);
  }
  if (selectedFieldKeys.has('version')) {
    lines.push(`**Schema version**: ${payload.version}`);
  }
  lines.push(`**Charts in this export**: ${payload.charts?.length || 0}`);
  lines.push('');
  lines.push('---');
  lines.push('');

  for (const c of payload.charts || []) {
    lines.push(`## ${c.name || 'Unnamed'}`);
    lines.push('');
    if (selectedFieldKeys.has('birth_time_iso') && c.birth_time_iso) {
      lines.push(`- **Born**: ${c.birth_time_iso}`);
    }
    const loc = [];
    if (selectedFieldKeys.has('city') && c.city) loc.push(c.city);
    if (selectedFieldKeys.has('latitude') && c.latitude != null) loc.push(`${c.latitude.toFixed(4)}\u00B0`);
    if (selectedFieldKeys.has('longitude') && c.longitude != null) loc.push(`${c.longitude.toFixed(4)}\u00B0`);
    if (selectedFieldKeys.has('timezone') && c.timezone) loc.push(c.timezone);
    if (loc.length) lines.push(`- **Location**: ${loc.join(' \u00B7 ')}`);
    if (selectedFieldKeys.has('description') && c.description) {
      lines.push(`- **Description**: ${c.description}`);
    }
    if (selectedFieldKeys.has('tags') && c.tags) {
      lines.push(`- **Tags**: ${c.tags}`);
    }
    if (selectedFieldKeys.has('notes') && c.notes) {
      lines.push(`- **Notes**: ${c.notes}`);
    }
    if (selectedFieldKeys.has('cached_data') && c.cached_data && typeof c.cached_data === 'object') {
      const cd = c.cached_data;
      if (cd.datetime) lines.push(`- **Chart datetime**: ${cd.datetime}`);
      const western = cd.western || {};
      const positions = western.positions || {};
      const planetLines = Object.entries(positions)
        .filter(([k]) => !['ascendant', 'midheaven', 'north_node', 'south_node'].includes(k))
        .map(([k, v]) => `  - ${k.charAt(0).toUpperCase() + k.slice(1)} (${planetGlyphs[k] || '\u25CF'}): ${v.formatted || `${v.degree?.toFixed(2)}\u00B0 ${v.sign || ''}`}`);
      if (planetLines.length) {
        lines.push('');
        lines.push('**Western planets**:');
        lines.push(...planetLines);
      }
      const angles = ['ascendant', 'midheaven', 'north_node']
        .filter((k) => positions[k])
        .map((k) => `  - ${k.replace('_', ' ')}: ${positions[k].formatted}`);
      if (angles.length) {
        lines.push('');
        lines.push('**Angles**:');
        lines.push(...angles);
      }
      const houses = western.houses || {};
      const houseLines = Object.entries(houses)
        .sort(([a], [b]) => Number(a.replace('house_', '')) - Number(b.replace('house_', '')))
        .map(([k, v]) => `  - ${k}: ${v.formatted}`);
      if (houseLines.length) {
        lines.push('');
        lines.push('**House cusps**:');
        lines.push(...houseLines);
      }
      if (western.dominant_element) {
        lines.push('');
        lines.push(`**Dominant element**: ${western.dominant_element} \u00B7 **Dominant modality**: ${western.dominant_modality}`);
      }
    }
    lines.push('');
    lines.push('---');
    lines.push('');
  }
  return lines.join('\n');
}

const MAJOR_ASPECT_ORBS = {
  conjunction: 8,
  sextile: 6,
  square: 8,
  trine: 8,
  opposition: 8,
};

export function sortAspectsByExactness(aspects) {
  const list = Array.isArray(aspects) ? aspects.slice() : [];
  return list.sort((a, b) => {
    const ea = Number(a && a.exactness);
    const eb = Number(b && b.exactness);
    const na = Number.isFinite(ea) ? ea : Number.NEGATIVE_INFINITY;
    const nb = Number.isFinite(eb) ? eb : Number.NEGATIVE_INFINITY;
    return nb - na;
  });
}

export function aspectOrbDegrees(aspect) {
  if (!aspect || typeof aspect !== 'object') return null;
  if (typeof aspect.orb === 'number' && Number.isFinite(aspect.orb)) return aspect.orb;
  const max = MAJOR_ASPECT_ORBS[String(aspect.aspect || '').toLowerCase()];
  const exact = Number(aspect.exactness);
  if (max == null || !Number.isFinite(exact)) return null;
  const clamped = Math.min(1, Math.max(0, exact));
  return (1 - clamped) * max;
}

export function formatIllumination(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return Math.min(100, Math.max(0, value));
}

function titleBody(name) {
  return String(name || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function skyReadingLine(western, moonPhase) {
  if (!western || typeof western !== 'object') return '';
  const parts = [];
  const balance = [western.dominant_modality, western.dominant_element]
    .filter((part) => typeof part === 'string' && part.length > 0)
    .join(' ');
  if (balance) parts.push(balance);
  const phase = moonPhase && typeof moonPhase.phase_name === 'string' ? moonPhase.phase_name : '';
  if (phase) parts.push(`${phase} moon`);
  const tightest = sortAspectsByExactness(western.aspects)[0];
  if (tightest && tightest.planet1 && tightest.planet2 && tightest.aspect) {
    const orb = aspectOrbDegrees(tightest);
    const orbText = orb == null ? '' : ` (${orb.toFixed(1)}°)`;
    parts.push(
      `tightest ${titleBody(tightest.planet1)} ${tightest.aspect} ${titleBody(tightest.planet2)}${orbText}`,
    );
  }
  return parts.join(' · ');
}

/**
 * Radial stack index for chart bodies. Bodies farther apart than
 * minSepDeg stay on ring 0. A cluster, including one that wraps past
 * 0°, stacks 0, 1, 2… in longitude order so glyphs do not share a point.
 */
export function collisionRings(bodies, minSepDeg = 6) {
  const clean = (Array.isArray(bodies) ? bodies : []).filter(
    (body) => body && typeof body.name === 'string' && Number.isFinite(Number(body.longitude)),
  );
  const rings = {};
  if (clean.length === 0) return rings;
  const sep = Number(minSepDeg);
  const sorted = [...clean].sort((a, b) => Number(a.longitude) - Number(b.longitude));
  const clusters = [];
  let current = [sorted[0]];
  for (let i = 1; i < sorted.length; i++) {
    const prev = Number(current[current.length - 1].longitude);
    const lon = Number(sorted[i].longitude);
    if (Number.isFinite(sep) && lon - prev <= sep) current.push(sorted[i]);
    else {
      clusters.push(current);
      current = [sorted[i]];
    }
  }
  clusters.push(current);
  if (clusters.length > 1 && Number.isFinite(sep)) {
    const first = clusters[0];
    const last = clusters[clusters.length - 1];
    const wrapGap = (Number(first[0].longitude) + 360) - Number(last[last.length - 1].longitude);
    if (wrapGap <= sep) {
      clusters[0] = last.concat(first);
      clusters.pop();
    }
  }
  for (const cluster of clusters) {
    cluster.forEach((body, index) => {
      rings[body.name] = index;
    });
  }
  return rings;
}
