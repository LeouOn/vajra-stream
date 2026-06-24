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

// Canonical Nakshatra order — used to compute "next nakshatra" in transit line.
const NAKSHATRA_ORDER = [
  'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira',
  'Ardra', 'Punarvasu', 'Pushya', 'Ashlesha', 'Magha',
  'Purva Phalguni', 'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati',
  'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha',
  'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha',
  'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati',
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

// ----------------------------------------------------------------------
// Live astrology export (current day / location)
// ----------------------------------------------------------------------
// Accepts the full shape returned by GET /astrology/current:
//   {
//     datetime: ISO string,
//     location: { latitude, longitude },
//     western:  { positions, elements, modalities, aspects },
//     indian:   { tithi, nakshatra, yoga, karana, vara, ascendant, planets },
//     chinese:  { ... },
//     moon_phase: { phase_name, illumination, ... },
//     planetary_positions: alias of western.positions,
//     auspicious_times: { ... },
//     timestamp,
//   }
// ----------------------------------------------------------------------

function buildLiveWesternPlanetTable(positions) {
  if (!positions || typeof positions !== 'object') return [];
  const rows = [];
  for (const [key, info] of Object.entries(positions)) {
    if (!info || typeof info !== 'object') continue;
    const sign = info.sign || '\u2014';
    const degree = formatDegree(info.degree);
    const house = info.house != null ? info.house : (info.house_placidus ?? '\u2014');
    const retro = info.retrograde ? ' (R)' : '';
    const label = planetLabel(key);
    rows.push(`| ${label} | ${sign}${retro} | ${degree} | ${house} |`);
  }
  return rows;
}

function buildLiveAspectLines(aspects) {
  if (!Array.isArray(aspects) || aspects.length === 0) return ['_No active aspects._'];
  const lines = [];
  for (const a of aspects) {
    const p1 = titleCase(a.planet1 || '');
    const p2 = titleCase(a.planet2 || '');
    const aspect = titleCase(a.aspect || '');
    const orb = formatOrb(aspectOrb(a));
    lines.push(`- ${p1} ${aspect} ${p2} \u2014 orb ${orb}`);
  }
  return lines;
}

function buildLiveElementLines(elements) {
  if (!elements || typeof elements !== 'object') return [];
  const rows = [];
  const order = ['fire', 'earth', 'air', 'water'];
  for (const e of order) {
    const cap = titleCase(e);
    const v = elements[e] != null ? elements[e] : (elements[cap] ?? '\u2014');
    const suffix = v === 1 ? 'pt' : 'pts';
    rows.push(`- ${cap} ${v} ${suffix}`);
  }
  const dom = dominantKey(elements);
  if (dom) rows.push(`- Dominant: ${titleCase(dom)}`);
  return rows;
}

function buildLiveModalityLines(modalities) {
  if (!modalities || typeof modalities !== 'object') return [];
  const rows = [];
  const order = ['cardinal', 'fixed', 'mutable'];
  for (const m of order) {
    const cap = titleCase(m);
    const v = modalities[m] != null ? modalities[m] : (modalities[cap] ?? '\u2014');
    const suffix = v === 1 ? 'pt' : 'pts';
    rows.push(`- ${cap} ${v} ${suffix}`);
  }
  return rows;
}

// Wu Xing (Five Elements) char → English name.
const WU_XING_MAP = { '\u6728': 'Wood', '\u706B': 'Fire', '\u571F': 'Earth', '\u91D1': 'Metal', '\u6C34': 'Water' };
const WU_XING_ORDER = ['Wood', 'Fire', 'Earth', 'Metal', 'Water'];
const WU_XING_EMOJI = { Wood: '\uD83C\uDF33', Fire: '\uD83D\uDD25', Earth: '\u26F0\uFE0F', Metal: '\u2694\uFE0F', Water: '\uD83D\uDCA7' };

// Compute Five Element Balance from BaZi pillar strings.
// Each pillar value like "丙午/Bing-Wu-Horse (火火)" contains Wu Xing chars
// in parentheses. Mirrors ChineseBaZi.tsx countWuXing() logic.
function computeWuXingBalance(bazi) {
  const counts = { Wood: 0, Fire: 0, Earth: 0, Metal: 0, Water: 0 };
  if (!bazi || typeof bazi !== 'object') return counts;
  for (const val of Object.values(bazi)) {
    if (typeof val !== 'string') continue;
    const match = val.match(/\(([^)]+)\)/);
    if (!match || !match[1]) continue;
    for (const ch of match[1]) {
      const eng = WU_XING_MAP[ch];
      if (eng) counts[eng]++;
    }
  }
  return counts;
}

function buildLiveVedicLines(indian) {
  if (!indian || typeof indian !== 'object') return [];
  const lines = [];
  // Panchanga fields — backend nests under `panchanga`, NOT top-level.
  // VedicPanchanga.tsx reads indianData.panchanga.tithi etc.
  const panchanga = indian.panchanga || {};
  const tithi = panchanga.tithi || indian.tithi;
  if (tithi) {
    const name = tithi.name || '\u2014';
    const paksha = tithi.paksha || '';
    const pct = tithi.percentage != null ? `${Math.round(tithi.percentage)}%`
      : (tithi.progress != null ? `${Math.round(Number(tithi.progress) * 100)}%` : '');
    lines.push(`- Tithi: ${name}${paksha ? ' (' + paksha + ')' : ''}${pct ? ', ' + pct : ''}`);
  }
  const nakshatra = panchanga.nakshatra || indian.nakshatra;
  if (nakshatra) {
    const n = nakshatra;
    const pct = n.percentage != null ? `${Math.round(n.percentage)}%`
      : (n.progress != null ? `${Math.round(Number(n.progress) * 100)}%` : '');
    lines.push(`- Nakshatra: ${n.name || '\u2014'}${pct ? ' (' + pct + ')' : ''}`);
    // Nakshatra Transit / Next — mirrors the progress bar on the page.
    const nextNak = NAKSHATRA_ORDER[(NAKSHATRA_ORDER.indexOf(n.name) + 1) % NAKSHATRA_ORDER.length];
    if (nextNak) lines.push(`- Nakshatra Transit: ${n.name || '\u2014'} \u2192 Next: ${nextNak}`);
  }
  const yoga = panchanga.yoga || indian.yoga;
  if (yoga) lines.push(`- Yoga: ${yoga.name || '\u2014'}`);
  const karana = panchanga.karana || indian.karana;
  if (karana) lines.push(`- Karana: ${karana.name || '\u2014'}`);
  const vara = panchanga.vara || indian.vara;
  if (vara) {
    const v = vara;
    lines.push(`- Vara: ${v.name || '\u2014'}${v.lord ? ' (' + v.lord + ')' : ''}`);
  }
  // Sidereal positions — backend uses `sidereal_positions`, not `planets`.
  const sidereal = indian.sidereal_positions || indian.ascendant_pos || {};
  if (indian.ascendant || sidereal.ascendant) {
    const a = indian.ascendant || sidereal.ascendant;
    lines.push(`- Ascendant: ${a.formatted || (a.rashi_name || a.rashi || a.sign || '\u2014') + ' ' + formatDegree(a.degree)}`);
  }
  const planets = indian.planets || sidereal;
  if (planets && typeof planets === 'object') {
    for (const [key, info] of Object.entries(planets)) {
      if (!info || key === 'ascendant') continue;
      const label = planetLabel(key);
      const sign = info.rashi_name || info.rashi || info.sign || '\u2014';
      const degree = formatDegree(info.degree);
      const retro = info.retrograde ? ' (R)' : '';
      lines.push(`- ${label}: ${sign}${retro} ${degree}`);
    }
  }
  return lines;
}

function buildLiveMoonPhaseLines(moonPhase) {
  if (!moonPhase || typeof moonPhase !== 'object') return [];
  const lines = [];
  const name = moonPhase.phase_name || moonPhase.name || '\u2014';
  const illum = moonPhase.illumination != null
    ? `${Number(moonPhase.illumination).toFixed(1)}%`
    : '';
  const desc = moonPhase.description || '';
  lines.push(`- **${name}**${illum ? ' (' + illum + ' illuminated)' : ''}`);
  if (desc) lines.push(`- ${desc}`);
  return lines;
}

function buildLiveAuspiciousLines(auspicious) {
  if (!auspicious || typeof auspicious !== 'object') return [];
  const lines = [];
  // Filter out obviously non-useful keys
  const skip = new Set(['description']);
  for (const [k, v] of Object.entries(auspicious)) {
    if (skip.has(k) || v == null) continue;
    const label = titleCase(k.replace(/_/g, ' '));
    let val = v;
    if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(v)) {
      // ISO datetime \u2014 keep as-is
      val = v;
    } else if (typeof v === 'object') {
      val = JSON.stringify(v);
    }
    lines.push(`- ${label}: ${val}`);
  }
  return lines;
}

export function formatLiveAstrologyMarkdown(data) {
  if (!data || typeof data !== 'object') {
    return '# Current Astrology\n\nNo data available.';
  }

  const sections = [];
  // --- Header -----------------------------------------------------------
  const dt = data.datetime || (data.timestamp ? new Date(data.timestamp * 1000).toISOString() : '');
  const loc = data.location;
  const locStr = loc && (loc.latitude != null && loc.longitude != null)
    ? `${Number(loc.latitude).toFixed(4)}, ${Number(loc.longitude).toFixed(4)}`
    : '';
  const titleLine = `# Current Astrology${dt ? ' \u2014 ' + dt.slice(0, 16).replace('T', ' ') : ''}`;
  sections.push([titleLine, '']);
  if (locStr) sections.push([`**Location:** ${locStr}`, '']);
  sections.push(['**Systems:** Tropical / Vedic (Lahiri) / BaZi (Lahiri ayanamsa)', '']);

  // --- Moon Phase --------------------------------------------------------
  if (data.moon_phase) {
    sections.push(['## Moon Phase', '', ...buildLiveMoonPhaseLines(data.moon_phase), '']);
  }

  // --- Western ----------------------------------------------------------
  const western = data.western;
  if (western) {
    sections.push(['## Western Tropical', '*(Tropical / Placidus Houses \u00B7 Geocentric)*', '']);
    // Summary block — the page prominently displays Sun Sign, Moon Sign, Ascendant
    // as three big cards above the planet table. Mirror that here so an LLM sees
    // the same overview the user sees on screen.
    const positions = western.positions || {};
    const sunSign = positions.sun && positions.sun.sign;
    const sunDeg = positions.sun && positions.sun.degree;
    const sunHouse = positions.sun && positions.sun.house;
    const moonSign = positions.moon && positions.moon.sign;
    const moonDeg = positions.moon && positions.moon.degree;
    const moonHouse = positions.moon && positions.moon.house;
    const ascSign = positions.ascendant && positions.ascendant.sign;
    const ascDeg = positions.ascendant && positions.ascendant.degree;
    const summary = [];
    if (sunSign) {
      summary.push(`- **Sun Sign:** ${sunSign}${sunDeg != null ? ' ' + formatDegree(sunDeg) : ''}${sunHouse != null ? ' \u00B7 H' + sunHouse : ''}`);
    }
    if (moonSign) {
      summary.push(`- **Moon Sign:** ${moonSign}${moonDeg != null ? ' ' + formatDegree(moonDeg) : ''}${moonHouse != null ? ' \u00B7 H' + moonHouse : ''}`);
    }
    if (ascSign) {
      summary.push(`- **Ascendant:** ${ascSign}${ascDeg != null ? ' ' + formatDegree(ascDeg) : ''} \u00B7 H1 Cusp`);
    }
    if (summary.length > 0) {
      sections.push(['### Summary', '', ...summary, '']);
    }
    if (western.positions && Object.keys(western.positions).length > 0) {
      const planetRows = buildLiveWesternPlanetTable(western.positions);
      if (planetRows.length > 0) {
        sections.push([
          '### Planetary Coordinates',
          '',
          '| Planet | Sign | Degree | House |',
          '|--------|------|--------|-------|',
          ...planetRows,
          '',
        ]);
      }
    }
    if (western.elements) {
      sections.push(['### Elements', '', ...buildLiveElementLines(western.elements), '']);
    }
    if (western.modalities) {
      sections.push(['### Modalities', '', ...buildLiveModalityLines(western.modalities), '']);
    }
    if (Array.isArray(western.aspects) && western.aspects.length > 0) {
      sections.push([
        '### Active Conflux Aspects',
        '',
        ...buildLiveAspectLines(western.aspects),
        '',
      ]);
    }
  }

  // --- Vedic (Indian) ---------------------------------------------------
  if (data.indian) {
    const vedicLines = buildLiveVedicLines(data.indian);
    if (vedicLines.length > 0) {
      sections.push(['## Vedic Sidereal (Lahiri Ayanamsa)', '', ...vedicLines, '']);
    }
  }

  // --- Chinese (BaZi) ---------------------------------------------------
  if (data.chinese && typeof data.chinese === 'object') {
    const c = data.chinese;
    const chineseLines = [];
    if (c.sheng_xiao || c.zodiac_animal) {
      chineseLines.push(`- Sheng Xiao: ${c.sheng_xiao || c.zodiac_animal || '\u2014'}`);
    }
    if (c.solar_term && c.solar_term !== 'None' && c.solar_term !== 'null') {
      chineseLines.push(`- Solar Term: ${c.solar_term}`);
    }
    // Shichen (Chinese hour) — the page shows this as a column. Backend may
    // send it as c.shichen = { name, branch, ... } or as a plain string.
    if (c.shichen) {
      const sh = typeof c.shichen === 'string' ? c.shichen : (c.shichen.name || c.shichen.branch);
      if (sh) chineseLines.push(`- Shichen (Hour): ${sh}`);
    }
    // Four pillars: backend sends as 'bazi' with year/month/day/hour keys
    const fourPillars = c.four_pillars || c.bazi;
    if (fourPillars && typeof fourPillars === 'object') {
      for (const [k, v] of Object.entries(fourPillars)) {
        if (v) chineseLines.push(`- ${titleCase(k)}: ${v}`);
      }
    }
    // Five Element Balance — computed from pillar Wu Xing chars, matching
    // the ChineseBaZi.tsx component. The backend doesn't send this pre-computed.
    if (fourPillars && typeof fourPillars === 'object') {
      const wuXing = computeWuXingBalance(fourPillars);
      const total = Object.values(wuXing).reduce((a, b) => a + b, 0);
      if (total > 0) {
        const elemLines = WU_XING_ORDER.map((elem) => {
          const count = wuXing[elem] || 0;
          const pct = Math.round((count / total) * 100);
          return `  - ${WU_XING_EMOJI[elem]} ${elem}: ${count} (${pct}%)`;
        });
        chineseLines.push('- Five Element Balance (\u4E94\u884C):', ...elemLines);
      }
    }
    // Fallback: if backend DID send five_elements_balance, use it too
    if (c.five_elements_balance) {
      const fb = c.five_elements_balance;
      if (typeof fb === 'object' && !Array.isArray(fb) && !fourPillars) {
        const lines = Object.entries(fb).map(([elem, count]) => `- ${titleCase(elem)}: ${count}`);
        chineseLines.push('- Element Balance:', ...lines);
      }
    }
    // Lunar Date — page shows "Month 5 Day 11"
    if (c.lunar_date) {
      const ld = c.lunar_date;
      if (typeof ld === 'string') {
        chineseLines.push(`- Lunar Date: ${ld}`);
      } else if (typeof ld === 'object') {
        const parts = [];
        if (ld.month != null) parts.push(`Month ${ld.month}`);
        if (ld.day != null) parts.push(`Day ${ld.day}`);
        if (ld.year != null) parts.push(`Year ${ld.year}`);
        if (ld.is_leap_month) parts.push('(Leap Month)');
        if (parts.length) chineseLines.push(`- Lunar Date: ${parts.join(' ')}`);
      }
    }
    if (chineseLines.length > 0) {
      sections.push(['## Chinese Lunisolar (BaZi)', '*(Sheng Xiao System \u00B7 八字)*', '', ...chineseLines, '']);
    }
  }

  // --- Auspicious Times -------------------------------------------------
  if (data.auspicious_times && Object.keys(data.auspicious_times).length > 0) {
    const lines = buildLiveAuspiciousLines(data.auspicious_times);
    if (lines.length > 0) {
      sections.push(['## Auspicious Times', '', ...lines, '']);
    }
  }

  return joinLines(sections);
}
