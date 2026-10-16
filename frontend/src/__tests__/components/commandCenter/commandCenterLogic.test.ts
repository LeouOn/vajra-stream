/**
 * CommandCenter extracted logic: chat formatting, model option groups and
 * the chat-job waiter (poll + WS race, timeout, cancel, teardown).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { update as pushChatProgress } from '../../../hooks/chatProgress';
import {
  buildContextSystemMessage, collapseChatStutter, computeCostUsd, formatOperatorSummary,
} from '../../../components/CommandCenter/chatFormatting';
import { buildModelOptions } from '../../../components/CommandCenter/buildModelOptions';
import {
  waitForChatJob, CHAT_JOB_POLL_MS, CHAT_JOB_TIMEOUT_MS,
} from '../../../components/CommandCenter/waitForChatJob';
import type { AvailableModelMeta } from '../../../components/CommandCenter/commandCenterTypes';

describe('chatFormatting', () => {
  it('collapses a repeated phrase but leaves short or clean text alone', () => {
    expect(collapseChatStutter('om mani om mani om mani om mani om mani padme')).toBe('om mani padme');
    expect(collapseChatStutter('short')).toBe('short');
    expect(collapseChatStutter('A perfectly ordinary sentence with no stutter.')).toBe('A perfectly ordinary sentence with no stutter.');
  });

  it('prices a reply from the catalog (free = 0, unknown = null)', () => {
    const pricing = {
      paid: { input_per_m: 1, output_per_m: 2, is_free: false },
      free: { input_per_m: 5, output_per_m: 5, is_free: true },
    };
    expect(computeCostUsd(pricing, 'paid', 1000, 500)).toBe(0.002);
    expect(computeCostUsd(pricing, 'free', 1000, 500)).toBe(0);
    expect(computeCostUsd(pricing, 'other', 1000, 500)).toBeNull();
    expect(computeCostUsd(pricing, 'paid', null, 500)).toBeNull();
    expect(computeCostUsd(pricing, null, 1, 1)).toBeNull();
  });

  it('summarizes operator responses per action', () => {
    expect(formatOperatorSummary('rates', { rates: [{ name: 'Calm', values: [1, 2] }, { values: 7 }] }))
      .toBe('📊 1. Calm → 1-2\n2. Rate 2 → 7');
    expect(formatOperatorSummary('analyze', {})).toContain('🎯 Target: —');
    expect(formatOperatorSummary('insight', { insight: 'Steady.' })).toBe('Steady.');
    expect(formatOperatorSummary('insight', { other: 1 })).toBe('{"other":1}');
    expect(formatOperatorSummary('working', { working_id: 'w1', rate_values: [3, 4], spoken_charge: 'Go.' }))
      .toBe('✦ Working w1\nIntention: —\nTarget: —\nDials: 3 · 4\nNext Duchen: — (— days)\n\nGo.');
  });

  it('builds the context system message only from enabled, loaded sources', () => {
    const base = {
      includeAstrology: true, includeAnatomy: true, includeHardware: true,
      astroData: null, chakraData: [], ledgerSummary: null,
    };
    expect(buildContextSystemMessage(base)).toBeNull();
    expect(buildContextSystemMessage({ ...base, astroData: { western: { sun_sign: 'Leo' } } }))
      .toBe('🪐 **Current Astrological Context:**\n- Sun: Leo');
    expect(buildContextSystemMessage({ ...base, includeAstrology: false, astroData: { western: { sun_sign: 'Leo' } } }))
      .toBeNull();
  });
});

describe('buildModelOptions', () => {
  const meta = (id: string, provider: string, featured: boolean): AvailableModelMeta => ({
    id, name: id, provider, context_length: null, input_per_m: 1, output_per_m: 2,
    is_free: false, featured, description: '', source: 'test',
  });

  it('groups auto, recommended, LM Studio, local and other providers (sorted)', () => {
    const groups = buildModelOptions(
      [meta('f/one', 'openrouter', true), meta('z/two', 'zeta', false), meta('a/three', 'alpha', false)],
      { lm_studio: ['qwen'], local: ['local:llama', 'mistral'], api: ['deepseek (chat)'] },
    );
    expect(groups.map((g) => g.title)).toEqual(['Auto-select', 'Recommended', 'LM Studio (Active)', 'Local GGUF', 'alpha', 'zeta']);
    expect(groups[3].options).toEqual([
      { value: 'local:llama', label: 'llama' },
      { value: 'local:mistral', label: 'mistral' },
    ]);
  });

  it('falls back to the built-in featured list and the basic API list when the catalog is empty', () => {
    const groups = buildModelOptions([], { lm_studio: [], local: [], api: ['deepseek (chat)', 'garbage'] });
    expect(groups.map((g) => g.title)).toEqual(['Auto-select', 'Recommended', 'API Providers']);
    expect(groups[2].options).toEqual([{ value: 'deepseek:chat', label: 'deepseek (chat)' }]);
  });
});

describe('waitForChatJob', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let jobStatus: Record<string, unknown>;

  const refs = () => ({
    cancelledRef: { current: false },
    waitRejectRef: { current: null as ((err: Error) => void) | null },
  });

  beforeEach(() => {
    vi.useFakeTimers();
    jobStatus = { status: 'running', phase: 'thinking' };
    fetchMock = vi.fn(async () => ({ ok: true, json: async () => jobStatus }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function settle(): Promise<void> {
    for (let i = 0; i < 5; i += 1) await Promise.resolve();
  }

  it('polls every second, reports the phase, and resolves on a completed poll', async () => {
    const setChatPhase = vi.fn();
    const r = refs();
    const p = waitForChatJob('j-poll', { setChatPhase, addToolLog: vi.fn(), ...r });
    await settle();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/api\/v1\/llm\/chat\/jobs\/j-poll$/);
    expect(setChatPhase).toHaveBeenCalledWith('thinking');
    expect(r.waitRejectRef.current).toBeTypeOf('function');

    jobStatus = { status: 'completed', response: 'done', tool_calls: [], debug_info: { model: 'm' } };
    await vi.advanceTimersByTimeAsync(CHAT_JOB_POLL_MS);
    await expect(p).resolves.toMatchObject({ response: 'done', tool_calls: [], debug_info: { model: 'm' } });
    expect(r.waitRejectRef.current).toBeNull();

    const calls = fetchMock.mock.calls.length;
    await vi.advanceTimersByTimeAsync(CHAT_JOB_POLL_MS * 3);
    expect(fetchMock.mock.calls.length).toBe(calls);
  });

  it('logs WS tool events and rejects on chat_error', async () => {
    const addToolLog = vi.fn();
    const p = waitForChatJob('j-ws', { setChatPhase: vi.fn(), addToolLog, ...refs() });
    const assertion = expect(p).rejects.toThrow('tool exploded');
    pushChatProgress('j-other', { type: 'chat_tool_start', tool: 'ignored' });
    pushChatProgress('j-ws', { type: 'chat_tool_start', tool: 'cast_iching' });
    pushChatProgress('j-ws', { type: 'chat_tool_error', tool: 'cast_iching', error: 'bad' });
    expect(addToolLog.mock.calls).toEqual([
      ['tool', 'Calling cast_iching...', 'pending'],
      ['tool', 'Tool cast_iching failed: bad', 'error'],
    ]);
    pushChatProgress('j-ws', { type: 'chat_error', error: 'tool exploded' });
    await assertion;
  });

  it('ignores WS events once cancelled, and settles through waitRejectRef', async () => {
    const r = refs();
    const addToolLog = vi.fn();
    const p = waitForChatJob('j-cancel', { setChatPhase: vi.fn(), addToolLog, ...r });
    r.cancelledRef.current = true;
    pushChatProgress('j-cancel', { type: 'chat_tool_start', tool: 'x' });
    expect(addToolLog).not.toHaveBeenCalled();

    const err = new Error('cancelled');
    err.name = 'AbortError';
    r.waitRejectRef.current?.(err);
    await expect(p).rejects.toThrow('cancelled');
    expect(r.waitRejectRef.current).toBeNull();
  });

  it('times out after 300s with the last polled status', async () => {
    const p = waitForChatJob('j-slow', { setChatPhase: vi.fn(), addToolLog: vi.fn(), ...refs() });
    const assertion = expect(p).rejects.toThrow('Chat job timed out after 300s (last status: running, thinking)');
    await vi.advanceTimersByTimeAsync(CHAT_JOB_TIMEOUT_MS);
    await assertion;
  });
});
