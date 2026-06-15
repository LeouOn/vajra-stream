/**
 * astrologyExport.js — LLM-optimized, glyph-free Markdown formatters for
 * natal charts and transit reports.
 *
 * Design rules (enforced across all output):
 *   - ZERO astrological glyphs (no ☉☽△□☌, no zodiac glyphs).
 *   - Plain English, Title Case for planet / sign names.
 *   - Dense Markdown tables for positions; bullets for aspects.
 *   - Every number is labeled ("Fire: 4 points", "orb 7.96°").
 *   - No duplicate words: aspect strings are rebuilt from planet1/planet2,
 *     never from the backend `description` field (which already contains the
 *     aspect name and caused "…Conjunction…Conjunction" duplication).
 */

// ---------------------------------------------------------------------------
// Static lookup tables
// ---------------------------------------------------------------------------

const PLANET_DISPLAY = {
  sun: 'Sun',
  moon: 'Moon',
  mercury: 'Mercury',
  venus: 'Venus',
  mars: 'Mars',
  jupiter: 'Jupiter',
  saturn: 'Saturn',
  uranus: 'Uranus',
  neptune: 'Neptune',
  pluto: 'Pluto',
  north_node: 'North Node',
  south_node: 'South Node',
  chiron: 'Chiron',
  rahu: 'Rahu',
  ketu: 'Ketu',
  ascendant: 'Ascendant',
  midheaven: 'Midheaven',
};

// Canonical display order for tropical natal positions.
const PLANET_ORDER = [
  'sun', 'moon', 'mercury', 'venus', 'mars',
  'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
  'north_node', 'chiron',
  'ascendant', 'midheaven',
];

// Canonical display order for sidereal (Vedic) positions.
const VEDIC_PLANET_ORDER = [
  'sun', 'moon', 'mercury', 'venus', 'mars',
  'jupiter', 'saturn', 'rahu', 'ketu',
];

// Standard aspect angles — used to compute orb when the backend does not
// emit an explicit `orb` field (natal aspects from get_western_astrology
// carry `angle` + `exactness` only).
const ASPECT_ANGLES = {
  conjunction: 0,
  sextile: 60,
  square: 90,
  trine: 120,
  opposition: 180,
  quincunx: 150,
};

const HARMONIOUS_ASPECTS = new Set(['conjunction', 'trine', 'sextile']);
const CHALLENGING_ASPECTS = new Set(['square', 'opposition']);

// Vedic paksha → lunar phase word.
const PAKSHA_PHASE = {
  shukla: 'waxing',
  krishna: 'waning',
  amavasya: 'new moon',
  purnima: 'full moon',
};

// Max orb (in degrees) for an aspect to be included in the natal report.
const NATAL_ASPECT_MAX_ORB = 8;

// ---------------------------------------------------------------------------
// Pure formatting helpers
// ---------------------------------------------------------------------------

function titleCase(s) {
  if (s == null) return '';
  return String(s)
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

function planetLabel(key) {
  if (key == null) return '\u2014';
  const k = String(key).toLowerCase();
  return PLANET_DISPLAY[k] || titleCase(k);
}

function formatDegree(deg) {
  if (deg == null || deg === '' || isNaN(Number(deg))) return '\u2014';
  return `${Number(deg).toFixed(2)}\u00B0`;
}

function isRetrograde(info) {
  return Boolean(
    info && (info.retrograde || info.is_retro || info.is_retrograde || info.retrograde === true),
  );
}

function signLabel(info) {
  if (!info) return '\u2014';
  return info.sign || info.rashi_name || info.rashi || '\u2014';
}

function signWithRetro(info) {
  const sign = signLabel(info);
  return isRetrograde(info) ? `${sign} (R)` : sign;
}

function aspectOrb(a) {
  if (!a) return null;
  if (typeof a.orb === 'number') return a.orb;
  const std = ASPECT_ANGLES[String(a.aspect || '').toLowerCase()];
  if (typeof a.angle === 'number' && typeof std === 'number') {
    return Math.abs(a.angle - std);
  }
  // Last resort: parse from the backend `description` string.
  const m = String(a.description || '').match(/Orb:\s*(-?[0-9]+(?:\.[0-9]+)?)\u00B0/i);
  return m ? parseFloat(m[1]) : null;
}

function formatOrb(orb) {
  if (orb == null || isNaN(Number(orb))) return '?';
  return `${Number(orb).toFixed(2)}\u00B0`;
}

function percentFromProgress(info) {
  if (!info) return '';
  if (info.percentage != null) return `${Math.round(Number(info.percentage))}%`;
  if (info.progress != null) return `${Math.round(Number(info.progress) * 100)}%`;
  return '';
}

function dominantKey(obj) {
  let best = null;
  let bestVal = -Infinity;
  for (const [k, v] of Object.entries(obj || {})) {
    const n = Number(v);
    if (Number.isFinite(n) && n > bestVal) {
      bestVal = n;
      best = k;
    }
  }
  return best;
}

function orderedKeys(obj, canonicalOrder) {
  const present = new Set(Object.keys(obj || {}));
  const ordered = canonicalOrder.filter((k) => present.has(k));
  for (const k of Object.keys(obj || {})) {
    if (!ordered.includes(k)) ordered.push(k);
  }
  return ordered;
}

function isHouseCuspName(name) {
  return typeof name === 'string' && /^house_\d+$/i.test(name);
}

function cuspLabel(name) {
  const m = String(name || '').match(/house_(\d+)/i);
  return m ? `House ${m[1]}` : String(name || '\u2014');
}

function resolveHouse(houses, positions, planet) {
  const fromHouses =
    houses && houses[planet] && (houses[planet].house_placidus ?? houses[planet].house);
  if (fromHouses != null) return fromHouses;
  const fromPos = positions && positions[planet] && positions[planet].house;
  if (fromPos != null) return fromPos;
  return null;
}

function formatBirthTime(iso) {
  return iso ? String(iso) : '';
}

function formatLocation(loc) {
  if (!loc) return '';
  const parts = [];
  if (loc.latitude != null && !isNaN(Number(loc.latitude))) {
    parts.push(Number(loc.latitude).toFixed(4));
  }
  if (loc.longitude != null && !isNaN(Number(loc.longitude))) {
    parts.push(Number(loc.longitude).toFixed(4));
  }
  return parts.join(', ');
}

function joinLines(sections) {
  // `sections` is an array of arrays of lines. Each section is rendered
  // verbatim then separated by a single blank line. Trailing whitespace is
  // trimmed and the document ends with a single newline.
  return sections.map((s) => s.join('\n')).join('\n\n').replace(/\n{3,}/g, '\n\n').trimEnd() + '\n';
}

// ---------------------------------------------------------------------------
// Natal chart formatter
// ---------------------------------------------------------------------------

function buildNatalAspectLine(a) {
  const p1 = planetLabel(a.planet1);
  const p2 = planetLabel(a.planet2);
  const asp = String(a.aspect || '').toLowerCase();
  return `- ${p1} ${asp} ${p2} \u2014 orb ${formatOrb(aspectOrb(a))}`;
}

function partitionNatalAspects(aspects, maxOrb) {
  const harmonious = [];
  const challenging = [];
  for (const a of aspects || []) {
    const orb = aspectOrb(a);
    if (orb == null || orb >= maxOrb) continue;
    const name = String(a.aspect || '').toLowerCase();
    if (HARMONIOUS_ASPECTS.has(name)) harmonious.push(a);
    else if (CHALLENGING_ASPECTS.has(name)) challenging.push(a);
  }
  // Tightest orbs first (most exact).
  harmonious.sort((a, b) => aspectOrb(a) - aspectOrb(b));
  challenging.sort((a, b) => aspectOrb(a) - aspectOrb(b));
  return { harmonious, challenging };
}

function buildVedicPositionLine(label, info) {
  const name = signLabel(info);
  const deg = formatDegree(info && info.degree);
  return `- ${label}: ${name} ${deg}`;
}

function buildVedicSection(vedic) {
  const lines = [];
  const tithi = vedic.tithi || {};
  const nakshatra = vedic.nakshatra || {};
  const yoga = vedic.yoga || {};
  const karana = vedic.karana || {};
  const vara = vedic.vara || {};

  // Tithi: "Prathama (Shukla/waxing, 12%)"
  const tithiName = tithi.name || '\u2014';
  const tithiParts = [];
  if (tithi.paksha) {
    const phase = PAKSHA_PHASE[String(tithi.paksha).toLowerCase()] || '';
    tithiParts.push(phase ? `${titleCase(tithi.paksha)}/${phase}` : titleCase(tithi.paksha));
  }
  const tithiPct = percentFromProgress(tithi);
  if (tithiPct) tithiParts.push(tithiPct);
  lines.push(
    tithiParts.length ? `- Tithi: ${tithiName} (${tithiParts.join(', ')})` : `- Tithi: ${tithiName}`,
  );

  // Nakshatra: "Ardra (12%)"
  const nakName = nakshatra.name || '\u2014';
  const nakPct = percentFromProgress(nakshatra);
  lines.push(nakPct ? `- Nakshatra: ${nakName} (${nakPct})` : `- Nakshatra: ${nakName}`);

  // Yoga / Karana / Vara
  lines.push(`- Yoga: ${yoga.name || '\u2014'}`);
  lines.push(`- Karana: ${karana.name || '\u2014'}`);
  lines.push(`- Vara: ${vara.name || '\u2014'}`);

  // Sidereal positions: ascendant then canonical planets.
  const asc = vedic.ascendant;
  if (asc && Object.keys(asc).length > 0) {
    lines.push(buildVedicPositionLine('Ascendant', asc));
  }
  const planets = vedic.planets || {};
  for (const key of orderedKeys(planets, VEDIC_PLANET_ORDER)) {
    lines.push(buildVedicPositionLine(planetLabel(key), planets[key]));
  }

  return lines;
}

export function formatNatalChartMarkdown(data) {
  if (!data || typeof data !== 'object') {
    return '# Natal Chart\n\nNo data available.';
  }

  const western = data.western || {};
  const positions = western.positions || {};
  const elements = western.elements || {};
  const modalities = western.modalities || {};
  const aspects = western.aspects || [];
  const vedic = data.vedic || {};
  const houses = data.houses || {};

  const sections = [];

  // --- Header -------------------------------------------------------------
  const header = [];
  header.push(`# Natal Chart: ${data.name || 'Unnamed'}`);
  const headerMeta = [];
  const birth = formatBirthTime(data.birth_time_iso);
  if (birth) headerMeta.push(`**Birth:** ${birth}`);
  const loc = formatLocation(data.birth_location);
  if (loc) headerMeta.push(`**Location:** ${loc}`);
  headerMeta.push('**System:** Tropical / Placidus');
  if (headerMeta.length) header.push(headerMeta.join('  \n'));
  sections.push(header);

  // --- Planetary Placements ----------------------------------------------
  const placements = ['## Planetary Placements', ''];
  if (positions && Object.keys(positions).length > 0) {
    placements.push('| Planet | Sign | Degree | House |');
    placements.push('|--------|------|--------|-------|');
    for (const key of orderedKeys(positions, PLANET_ORDER)) {
      const info = positions[key] || {};
      const house = resolveHouse(houses, positions, key);
      placements.push(
        `| ${planetLabel(key)} | ${signWithRetro(info)} | ${formatDegree(info.degree)} | ${
          house != null ? house : '\u2014'
        } |`,
      );
    }
  } else {
    placements.push('No positional data.');
  }
  sections.push(placements);

  // --- Element Balance ----------------------------------------------------
  const domEl = western.dominant_element || dominantKey(elements);
  const elementLines = ['## Element Balance', ''];
  for (const el of ['Fire', 'Earth', 'Air', 'Water']) {
    const v = elements[el];
    const marker = el === domEl ? ' (dominant)' : '';
    elementLines.push(`- ${el}: ${v != null ? v : 0} points${marker}`);
  }
  sections.push(elementLines);

  // --- Modalities ---------------------------------------------------------
  const domMod = western.dominant_modality || dominantKey(modalities);
  const modalityLines = ['## Modalities', ''];
  for (const m of ['Cardinal', 'Fixed', 'Mutable']) {
    const v = modalities[m];
    const marker = m === domMod ? ' (dominant)' : '';
    modalityLines.push(`- ${m}: ${v != null ? v : 0} points${marker}`);
  }
  sections.push(modalityLines);

  // --- Major Aspects ------------------------------------------------------
  const { harmonious, challenging } = partitionNatalAspects(aspects, NATAL_ASPECT_MAX_ORB);
  const aspectLines = [`## Major Aspects (orb < ${NATAL_ASPECT_MAX_ORB}\u00B0)`, ''];
  aspectLines.push('**Harmonious:**');
  if (harmonious.length === 0) {
    aspectLines.push('- None within orb');
  } else {
    for (const a of harmonious) aspectLines.push(buildNatalAspectLine(a));
  }
  aspectLines.push('');
  aspectLines.push('**Challenging:**');
  if (challenging.length === 0) {
    aspectLines.push('- None within orb');
  } else {
    for (const a of challenging) aspectLines.push(buildNatalAspectLine(a));
  }
  sections.push(aspectLines);

  // --- Vedic (Sidereal / Lahiri) -----------------------------------------
  const vedicLines = ['## Vedic (Sidereal / Lahiri)', ''];
  vedicLines.push(...buildVedicSection(vedic));
  sections.push(vedicLines);

  return joinLines(sections);
}

// ---------------------------------------------------------------------------
// Transit report formatter (uses the existing transit-export JSON shape)
// ---------------------------------------------------------------------------

function buildHouseTableLines(houses) {
  const lines = [];
  if (!houses || typeof houses !== 'object' || Object.keys(houses).length === 0) {
    lines.push('No data.');
    return lines;
  }
  lines.push('| Planet | Sign | Degree | House (P) | House (WS) |');
  lines.push('|--------|------|--------|----------|------------|');
  for (const key of orderedKeys(houses, PLANET_ORDER)) {
    const info = houses[key] || {};
    const hp = info.house_placidus != null ? info.house_placidus : '\u2014';
    const hw = info.house_whole_sign != null ? info.house_whole_sign : '\u2014';
    lines.push(
      `| ${planetLabel(key)} | ${signWithRetro(info)} | ${formatDegree(info.degree)} | ${hp} | ${hw} |`,
    );
  }
  return lines;
}

function buildTransitListLines(transits) {
  const lines = [];
  if (!Array.isArray(transits) || transits.length === 0) {
    lines.push('None within orb.');
    return lines;
  }
  transits.slice(0, 10).forEach((t, i) => {
    const tp = planetLabel(t.transit_planet);
    const asp = String(t.aspect || '').toLowerCase();
    const np = isHouseCuspName(t.natal_planet)
      ? cuspLabel(t.natal_planet)
      : planetLabel(t.natal_planet);
    const pct =
      t.exactness != null && !isNaN(Number(t.exactness))
        ? `${Math.round(Number(t.exactness) * 100)}% exact`
        : '';
    const orbRaw = t.orb != null ? t.orb : aspectOrb(t);
    const orb = `${formatOrb(orbRaw)} orb`;
    const detail = [pct, orb].filter(Boolean).join(' \u00B7 ');
    lines.push(`${i + 1}. Transit ${tp} ${asp} Natal ${np} \u2014 ${detail}`);
  });
  return lines;
}

function buildBaziLines(bazi) {
  const lines = [];
  const interactions = bazi && bazi.interactions;
  if (!Array.isArray(interactions) || interactions.length === 0) {
    lines.push('No BaZi interactions found.');
    return lines;
  }
  for (const ix of interactions) {
    const type = titleCase(ix.type || '');
    const pillar = titleCase(ix.pillar || '');
    lines.push(`- ${pillar} ${type}: ${ix.description || 'No description'}`);
  }
  return lines;
}

function buildGocharaLines(gochara) {
  const lines = [];
  if (!gochara || typeof gochara !== 'object' || Object.keys(gochara).length === 0) {
    lines.push('No Gochara data available.');
    return lines;
  }
  for (const key of Object.keys(gochara)) {
    const info = gochara[key] || {};
    const house = info.gochara_house != null ? info.gochara_house : '?';
    const rashiFull = info.transit_rashi || '';
    const rashi = rashiFull.split(' ')[0] || rashiFull || '?';
    const deg = info.transit_degree != null ? formatDegree(info.transit_degree) : '';
    const degPart = deg && deg !== '\u2014' ? ` (${deg})` : '';
    lines.push(`- ${planetLabel(key)}: House ${house} from Moon (${rashi})${degPart}`);
  }
  return lines;
}

export function formatTransitReportMarkdown(data) {
  if (!data || typeof data !== 'object') {
    return '# Transit Report\n\nNo data available.';
  }

  const sections = [];

  // --- Header -------------------------------------------------------------
  const header = [`# Transit Report: ${data.name || 'Unnamed'}`];
  const meta = [];
  const birth = formatBirthTime(data.birth_time_iso);
  if (birth) meta.push(`**Birth:** ${birth}`);
  const transit = formatBirthTime(data.transit_time);
  if (transit) meta.push(`**Transit:** ${transit}`);
  if (meta.length) header.push(meta.join('  \n'));
  sections.push(header);

  // --- Natal Placements ---------------------------------------------------
  sections.push(['## Natal Placements', '', ...buildHouseTableLines(data.natal_houses)]);

  // --- Transit Placements -------------------------------------------------
  sections.push(['## Transit Placements', '', ...buildHouseTableLines(data.transit_houses)]);

  // --- Harmonious / Challenging Transits ---------------------------------
  sections.push(['## Harmonious Transits', '', ...buildTransitListLines(data.top_harmonious)]);
  sections.push(['## Challenging Transits', '', ...buildTransitListLines(data.top_challenging)]);

  // --- BaZi ---------------------------------------------------------------
  sections.push(['## BaZi', '', ...buildBaziLines(data.bazi_clashes)]);

  // --- Gochara ------------------------------------------------------------
  sections.push(['## Gochara (from Natal Moon)', '', ...buildGocharaLines(data.gochara)]);

  return joinLines(sections);
}

export function formatTransitReportJSON(data) {
  return JSON.stringify(data ?? null, null, 2);
}
