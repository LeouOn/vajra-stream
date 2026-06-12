import { planetGlyph, aspectGlyph } from './astroHelpers.js';

function formatPlanetTable(houses) {
  if (!houses || typeof houses !== 'object' || Object.keys(houses).length === 0) {
    return 'No data';
  }
  const lines = [];
  lines.push('| Planet | Sign | Degree | House (Placidus) | House (Whole Sign) |');
  lines.push('|--------|------|--------|-------------------|--------------------|');
  for (const [planet, info] of Object.entries(houses)) {
    const glyph = planetGlyph(planet);
    const sign = info.sign || '\u2014';
    const degree = info.degree != null ? `${Number(info.degree).toFixed(2)}\u00B0` : '\u2014';
    const hp = info.house_placidus != null ? info.house_placidus : '\u2014';
    const hw = info.house_whole_sign != null ? info.house_whole_sign : '\u2014';
    lines.push(`| ${glyph} ${planet} | ${sign} | ${degree} | ${hp} | ${hw} |`);
  }
  return lines.join('\n');
}

function formatTransitList(transits, label) {
  if (!transits || !Array.isArray(transits) || transits.length === 0) {
    return `No ${label.toLowerCase()} found.`;
  }
  const lines = [];
  const items = transits.slice(0, 10);
  items.forEach((t, i) => {
    const tg = planetGlyph(t.transit_planet);
    const ag = aspectGlyph(t.aspect);
    const ng = planetGlyph(t.natal_planet);
    const pct = t.exactness != null ? (t.exactness * 100).toFixed(0) : '0';
    const orb = t.orb != null ? Number(t.orb).toFixed(1) : '?';
    const tpName = t.transit_planet || '?';
    const aspectName = t.aspect || '?';
    const npName = t.natal_planet || '?';
    lines.push(`${i + 1}. ${tg}${ag}${ng} Transit ${tpName} ${aspectName} Natal ${npName} \u2014 ${pct}% exact \u00B7 ${orb}\u00B0 orb`);
  });
  return lines.join('\n');
}

export function formatTransitExportMarkdown(data) {
  if (!data || typeof data !== 'object') {
    return '# Transit Report\n\nNo data available.';
  }

  const lines = [];

  lines.push(`# Transit Report: ${data.name || 'Unnamed'}`);
  lines.push('');

  lines.push('## Natal Planetary Placements');
  lines.push('');
  lines.push(formatPlanetTable(data.natal_houses));
  lines.push('');

  lines.push('## Current Transit Placements');
  lines.push('');
  lines.push(formatPlanetTable(data.transit_houses));
  lines.push('');

  lines.push('## Top 10 Harmonious Transits');
  lines.push('');
  lines.push(formatTransitList(data.top_harmonious, 'Harmonious Transits'));
  lines.push('');

  lines.push('## Top 10 Challenging Transits');
  lines.push('');
  lines.push(formatTransitList(data.top_challenging, 'Challenging Transits'));
  lines.push('');

  lines.push('## BaZi Transit Interactions');
  lines.push('');
  const interactions = data.bazi_clashes?.interactions;
  if (!interactions || !Array.isArray(interactions) || interactions.length === 0) {
    lines.push('No BaZi interactions found.');
  } else {
    for (const item of interactions) {
      lines.push(`- **${item.pillar || 'Unknown'}** (${item.type || '\u2014'}): ${item.description || 'No description'}`);
    }
  }
  lines.push('');

  lines.push('## Vedic Gochara (from Natal Moon)');
  lines.push('');
  const gochara = data.gochara;
  if (!gochara || typeof gochara !== 'object' || Object.keys(gochara).length === 0) {
    lines.push('No Gochara data available.');
  } else {
    for (const [planet, info] of Object.entries(gochara)) {
      const glyph = planetGlyph(planet);
      const house = info.gochara_house != null ? info.gochara_house : '?';
      const formatted = info.formatted || `House ${house}`;
      lines.push(`- ${glyph} ${planet}: ${formatted}`);
    }
  }

  return lines.join('\n');
}

export function formatTransitExportJSON(data) {
  return JSON.stringify(data ?? null, null, 2);
}
