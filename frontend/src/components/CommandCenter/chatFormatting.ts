/**
 * chatFormatting.ts — pure text builders for the Command Center: the
 * context system message injected ahead of a chat (astrology, chakras,
 * operations ledger), reply clean-up, per-message cost, and the operator
 * action summaries.
 */
import { formatHeld } from '../../lib/operationsSummary';
import type { OperationsSummary } from '../../types/operations';
import type { ChakraEntry, ModelPricing } from './commandCenterTypes';

/** Collapse a model's stutter (a phrase or word repeated 5+ times in a row). */
export function collapseChatStutter(text: string): string {
  if (!text || text.length < 24) return text;
  let current = text;
  for (let i = 0; i < 4; i += 1) {
    const next = current
      .replace(/(.{6,60}?)\1{4,}/g, '$1')
      .replace(/\b(\S{3,40})(?:[ \t]+\1){4,}\b/g, '$1');
    if (next === current) break;
    current = next;
  }
  return current;
}

export function formatWorkingSummary(data: Record<string, unknown>): string {
  const values = Array.isArray(data.rate_values) ? (data.rate_values as unknown[]).join(' · ') : '—';
  const saka = (data.saka_dawa && typeof data.saka_dawa === 'object')
    ? data.saka_dawa as Record<string, unknown>
    : {};
  const charge = typeof data.spoken_charge === 'string' ? data.spoken_charge : '';
  const duchen = typeof saka.saka_dawa_duchen === 'string' ? saka.saka_dawa_duchen : '—';
  const days = saka.days_until_duchen != null ? String(saka.days_until_duchen) : '—';
  return (
    `✦ Working ${data.working_id || ''}\n` +
    `Intention: ${data.intention || '—'}\n` +
    `Target: ${data.target || '—'}\n` +
    `Dials: ${values}\n` +
    `Next Duchen: ${duchen} (${days} days)\n` +
    (charge ? `\n${charge}` : '')
  );
}

/** Chat text for an operator action's response (working / analyze / rates / insight). */
export function formatOperatorSummary(actionKey: string, data: Record<string, unknown>): string {
  if (actionKey === 'working') return formatWorkingSummary(data);
  if (actionKey === 'analyze') {
    const analysis = (data.analysis && typeof data.analysis === 'object')
      ? data.analysis as Record<string, unknown>
      : undefined;
    return `🎯 Target: ${analysis?.target || '—'}\n🌀 Chakra: ${analysis?.primary_chakra || '—'}\n📡 Freq: ${analysis?.recommended_frequency || '—'} Hz\n🕉️ Mantra: ${analysis?.recommended_mantra_tradition || '—'}`;
  }
  if (actionKey === 'rates') {
    const rates = (data.rates || []) as Array<Record<string, unknown>>;
    return `📊 ${rates.map((r: Record<string, unknown>, i: number) => `${i + 1}. ${r.name || 'Rate ' + (i + 1)} → ${Array.isArray(r.values) ? (r.values as unknown[]).join('-') : r.values}`).join('\n')}`;
  }
  return (data.insight as string) || JSON.stringify(data);
}

export function formatAstrologyContext(data: Record<string, unknown>): string {
  const lines: string[] = ['🪐 **Current Astrological Context:**'];
  const western = data.western as Record<string, unknown> | undefined;
  if (western) {
    if (western.sun_sign) lines.push(`- Sun: ${western.sun_sign}`);
    if (western.moon_sign) lines.push(`- Moon: ${western.moon_sign}`);
    if (western.ascendant) lines.push(`- Ascendant: ${western.ascendant}`);
  }
  const moonPhase = data.moon_phase as Record<string, unknown> | undefined;
  if (moonPhase) {
    if (moonPhase.phase_name) lines.push(`- Moon Phase: ${moonPhase.phase_name} (${moonPhase.illumination ?? ''}%)`);
  }
  const indian = data.indian as Record<string, unknown> | undefined;
  if (indian) {
    if (indian.nakshatra) lines.push(`- Nakshatra: ${indian.nakshatra}`);
  }
  return lines.join('\n');
}

export function formatChakraContext(chakras: ChakraEntry[]): string {
  const lines: string[] = ['💚 **Energetic Anatomy (Chakra System) Context:**'];
  for (const c of chakras.slice(0, 7)) {
    const freq = Array.isArray(c.frequency) ? c.frequency.join('/') : (c.frequency ?? '');
    lines.push(`- ${c.name || c.sanskrit || 'Unknown'} (${c.sanskrit || ''}): ${c.element || ''} element, ${c.color || ''} color${freq ? `, ${freq} Hz` : ''}`);
  }
  return lines.join('\n');
}

export function formatLedgerContext(summary: OperationsSummary): string {
  const lines: string[] = [
    '📜 **Operations Ledger (today, real operations with measured durations):**',
    `- Completed: ${summary.completed} (${formatHeld(summary.seconds_held)} held in total)`,
    `- Active now: ${summary.active}`,
  ];
  const failed = (summary.by_status.error ?? 0) + (summary.by_status.interrupted ?? 0);
  if (failed > 0) lines.push(`- Failed or interrupted: ${failed}`);
  const kinds = Object.entries(summary.by_kind)
    .map(([kind, n]) => `${kind} ${n}`)
    .join(', ');
  if (kinds) lines.push(`- By kind: ${kinds}`);
  return lines.join('\n');
}

export interface ContextSources {
  includeAstrology: boolean;
  includeAnatomy: boolean;
  includeHardware: boolean;
  astroData: Record<string, unknown> | null;
  chakraData: ChakraEntry[] | null;
  ledgerSummary: OperationsSummary | null;
}

/** The system message prepended to a chat, or null when no context is enabled and loaded. */
export function buildContextSystemMessage(src: ContextSources): string | null {
  const parts: string[] = [];
  if (src.includeAstrology && src.astroData) {
    const ctx = formatAstrologyContext(src.astroData);
    if (ctx) parts.push(ctx);
  }
  if (src.includeAnatomy && src.chakraData && src.chakraData.length > 0) {
    parts.push(formatChakraContext(src.chakraData));
  }
  if (src.includeHardware && src.ledgerSummary) {
    parts.push(formatLedgerContext(src.ledgerSummary));
  }
  return parts.length > 0 ? parts.join('\n\n---\n\n') : null;
}

/** USD cost of one reply from the catalog pricing; null when unknown. */
export function computeCostUsd(
  modelPricing: Record<string, ModelPricing>,
  modelId: string | null,
  inputTokens: number | null,
  outputTokens: number | null,
): number | null {
  if (!modelId || inputTokens == null || outputTokens == null) return null;
  const pricing = modelPricing[modelId];
  if (!pricing) return null;
  if (pricing.is_free) return 0;
  const cost = (inputTokens * pricing.input_per_m / 1_000_000) + (outputTokens * pricing.output_per_m / 1_000_000);
  return Math.round(cost * 1e6) / 1e6;
}
