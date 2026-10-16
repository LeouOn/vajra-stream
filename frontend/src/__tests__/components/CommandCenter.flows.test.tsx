/**
 * CommandCenter — characterization tests for the main flows.
 *
 * Written before splitting the ~1,500-line monolith into hooks and section
 * components, and kept passing through the split: the chat job lifecycle
 * (POST /llm/chat/async → poll /llm/chat/jobs/{id} + chat-progress WS events),
 * cancel, retry, regenerate, operator actions, the context-injection system
 * message, and the polls' cleanup must not change.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';
import { update as pushChatProgress } from '../../hooks/chatProgress';
import type { CrystalStatus, ScalarStatus } from '../../types';
import {
  installFetch, apiPath, flush, byText, allByText, click, typeInto, type FetchCall,
} from './domHelpers';

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({ isConnected: true }),
  getActiveConnectionId: () => 'conn-1',
}));

vi.mock('../../utils/audioFeedback', () => ({
  audioFeedback: {
    enabled: false,
    init: vi.fn(),
    playClick: vi.fn(),
    playTabChange: vi.fn(),
    playSuccess: vi.fn(),
    playError: vi.fn(),
    playTelemetry: vi.fn(),
    playTick: vi.fn(),
    playType: vi.fn(),
  },
}));

vi.mock('../../components/3D/WorldEmanation', () => ({ default: () => null }));
vi.mock('../../components/UI/SakaDawaBanner', () => ({ default: () => null }));
vi.mock('../../components/CommandCenter/WorkingsStrip', () => ({ default: () => null }));
vi.mock('../../components/CommandCenter/SystemMonitorsCard', () => ({ default: () => null }));

import CommandCenter from '../../components/UI/CommandCenter';

// ─── Fixtures ──────────────────────────────────────────────

const ASTRO = {
  western: { sun_sign: 'Leo', moon_sign: 'Pisces', ascendant: 'Virgo' },
  moon_phase: { phase_name: 'Waxing Gibbous', illumination: 81 },
  indian: { nakshatra: 'Rohini' },
};

const CHAKRAS = [
  { name: 'Muladhara', sanskrit: 'Muladhara', element: 'Earth', color: 'Red', frequency: 396 },
  { name: 'Anahata', sanskrit: 'Anahata', element: 'Air', color: 'Green', frequency: [639, 528] },
];

const LEDGER = {
  since: null,
  by_status: { completed: 2, error: 1 },
  by_kind: { working: 2, broadcast: 1 },
  active: 1,
  completed: 2,
  seconds_held: 125,
};

type JobReply = Record<string, unknown>;
let chatAsyncStatus = 200;
let jobReplies: JobReply[] = [];
let nextJob = 0;

const COMPLETED: JobReply = {
  status: 'completed',
  response: 'The river is blessed.',
  tool_calls: [{ tool_name: 'start_rng_session', arguments: { minutes: 5 }, status: 'success', result: {} }],
  debug_info: { model: 'deepseek/deepseek-chat', provider: 'deepseek', input_tokens: 10, output_tokens: 20 },
};

function route(url: string, init: RequestInit | undefined) {
  const p = apiPath(url);
  const method = (init?.method || 'GET').toUpperCase();
  if (p.startsWith('/astrology/current?')) return { body: { astrology: ASTRO } };
  if (p === '/llm/models') {
    return { body: { status: 'success', available: { local: [], api: [], lm_studio: ['qwen-7b'] }, default_model: 'auto', lm_studio_connected: true } };
  }
  if (p === '/llm/models/available') {
    return {
      body: {
        status: 'success', count: 1, fetched_at: null, source: 'test',
        models: [{
          id: 'deepseek/deepseek-chat', name: 'DeepSeek Chat', provider: 'openrouter', context_length: null,
          input_per_m: 0, output_per_m: 0, is_free: true, featured: true, description: '', source: 'openrouter',
        }],
      },
    };
  }
  if (p === '/llm/providers/health') {
    return { body: { providers: [{ provider: 'deepseek', healthy: true, latency_ms: 120, error: null, checked_at: 0 }], healthy_count: 1, total_count: 1 } };
  }
  if (p === '/healing/chakra/all') return { body: { chakras: CHAKRAS } };
  if (p.startsWith('/operations/summary')) return { body: LEDGER };
  if (p === '/llm/chat/async' && method === 'POST') {
    if (chatAsyncStatus !== 200) return { status: chatAsyncStatus, body: {} };
    nextJob += 1;
    return { body: { job_id: `job-${nextJob}`, status: 'pending' } };
  }
  if (p.startsWith('/llm/chat/jobs/') && p.endsWith('/cancel')) return { body: { status: 'cancelled' } };
  if (p.startsWith('/llm/chat/jobs/')) {
    const reply = jobReplies.length > 1 ? jobReplies.shift() : jobReplies[0];
    return { body: reply ?? { status: 'running' } };
  }
  if (p === '/operator/analyze' && method === 'POST') {
    return { body: { analysis: { target: 'lower back', primary_chakra: 'root', recommended_frequency: 174, recommended_mantra_tradition: 'Medicine Buddha' } } };
  }
  if (p === '/operator/working' && method === 'POST') {
    return { body: { working_id: 'wrk_1', intention: 'clean water', target: 'all beings', rate_values: [1, 2, 3], saka_dawa: {} } };
  }
  return undefined;
}

// ─── Harness ───────────────────────────────────────────────

let container: HTMLDivElement;
let root: Root;
let calls: FetchCall[];

const crystalStatus: CrystalStatus = { active: false, intention: '' };
const scalarStatus: ScalarStatus = { active: false, rate: 0 };

async function mount(): Promise<void> {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root.render(
      <ConfigProvider>
        <CommandCenter
          isConnected
          isPlaying={false}
          frequency={528}
          crystalStatus={crystalStatus}
          scalarStatus={scalarStatus}
          sessions={{}}
          sakaDawa={null}
        />
      </ConfigProvider>,
    );
  });
  await flush(20);
}

function input(): HTMLInputElement {
  const el = container.querySelector<HTMLInputElement>('input[placeholder="Instruct the system..."]');
  if (!el) throw new Error('command input not found');
  return el;
}

async function submit(text: string): Promise<void> {
  await typeInto(input(), text);
  const form = container.querySelector('form');
  if (!form) throw new Error('form not found');
  await act(async () => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
}

function chatPosts(): FetchCall[] {
  return calls.filter((c) => c.method === 'POST' && apiPath(c.url) === '/llm/chat/async');
}

// happy-dom has no scrollIntoView; the auto-scroll effects call it.
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}

beforeEach(() => {
  chatAsyncStatus = 200;
  jobReplies = [COMPLETED];
  nextJob = 0;
  calls = installFetch(route).calls;
});

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  vi.restoreAllMocks();
});

// ─── Tests ─────────────────────────────────────────────────

describe('CommandCenter — characterization', () => {
  it('fetches context and model data on mount and clears its polls on unmount', async () => {
    const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    await mount();

    const gets = calls.filter((c) => c.method === 'GET').map((c) => apiPath(c.url));
    const astro = gets.find((p) => p.startsWith('/astrology/current?'));
    expect(astro).toMatch(/datetime_str=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}&latitude=37.7749&longitude=-122.4194$/);
    const ledger = gets.find((p) => p.startsWith('/operations/summary?since='));
    expect(ledger).toBeDefined();
    expect(gets.map((p) => p.split('?')[0]).sort()).toEqual([
      '/astrology/current',
      '/healing/chakra/all',
      '/llm/models',
      '/llm/models/available',
      '/llm/providers/health',
      '/operations/summary',
    ]);

    expect(container.textContent).toContain('Vajra.Stream Command Center Ready');
    expect(container.textContent).toContain('Suggested Intentions');
    expect(container.textContent).toContain('LLM AGENT ACTIVE');
    expect(container.textContent).toContain('1/1 providers');

    const delays = setIntervalSpy.mock.calls.map((c) => c[1]).filter((d) => d === 15000 || d === 30000).sort();
    expect(delays).toEqual([15000, 30000, 30000]);
    const ids = setIntervalSpy.mock.calls
      .map((c, i) => ({ d: c[1], id: setIntervalSpy.mock.results[i].value as unknown }))
      .filter((x) => x.d === 15000 || x.d === 30000)
      .map((x) => x.id);

    act(() => root.unmount());
    for (const id of ids) expect(clearIntervalSpy).toHaveBeenCalledWith(id);
  });

  it('submits a command with the injected context and renders the completed reply', async () => {
    await mount();
    await submit('bless the river');
    await flush(50);

    const [post] = chatPosts();
    const body = post.body as {
      messages: Array<{ role: string; content: string }>;
      [k: string]: unknown;
    };
    expect(body).toMatchObject({
      provider: 'auto',
      model: null,
      include_astrology: true,
      astrology_data: ASTRO,
      include_anatomy: true,
      include_hardware: true,
      debug_mode: true,
      connection_id: 'conn-1',
    });
    expect(body.messages.map((m) => m.role)).toEqual(['system', 'assistant', 'user']);
    expect(body.messages[2].content).toBe('bless the river');
    expect(body.messages[0].content).toBe(
      [
        '🪐 **Current Astrological Context:**\n- Sun: Leo\n- Moon: Pisces\n- Ascendant: Virgo\n- Moon Phase: Waxing Gibbous (81%)\n- Nakshatra: Rohini',
        '💚 **Energetic Anatomy (Chakra System) Context:**\n- Muladhara (Muladhara): Earth element, Red color, 396 Hz\n- Anahata (Anahata): Air element, Green color, 639/528 Hz',
        '📜 **Operations Ledger (today, real operations with measured durations):**\n- Completed: 2 (2m held in total)\n- Active now: 1\n- Failed or interrupted: 1\n- By kind: working 2, broadcast 1',
      ].join('\n\n---\n\n'),
    );

    const polls = calls.filter((c) => apiPath(c.url) === '/llm/chat/jobs/job-1');
    expect(polls.length).toBeGreaterThanOrEqual(1);

    expect(container.textContent).toContain('The river is blessed.');
    expect(container.textContent).toContain('Executed start_rng_session({"minutes":5}) successfully');
    expect(container.textContent).toContain('10→20 tokens');
    expect(container.textContent).toContain('$0.0000');
    expect(container.textContent).toContain('Model: deepseek/deepseek-chat');
    expect(input().value).toBe('');
    expect(byText(container, 'button', 'Send')).toBeDefined();
  });

  it('follows chat-progress WS events until chat_complete', async () => {
    jobReplies = [{ status: 'running', phase: 'calling tools' }];
    await mount();
    await submit('cast the i ching');
    await flush(50);

    expect(container.textContent).toContain('Working… calling tools');
    await act(async () => {
      pushChatProgress('job-1', { type: 'chat_tool_start', tool: 'cast_iching' });
    });
    expect(container.textContent).toContain('Calling cast_iching...');
    await act(async () => {
      pushChatProgress('job-1', { type: 'chat_complete', response: 'Hexagram 11, Peace.', tool_calls: [] });
    });
    await flush(20);
    expect(container.textContent).toContain('Hexagram 11, Peace.');
    expect(container.textContent).not.toContain('Working…');

    // Polling stops once the job is settled.
    const before = calls.length;
    await flush(1200);
    expect(calls.slice(before).filter((c) => apiPath(c.url).startsWith('/llm/chat/jobs/'))).toEqual([]);
  });

  it('cancels a running job (pre-existing: the cancel surfaces as an operator error bubble)', async () => {
    jobReplies = [{ status: 'running', phase: 'thinking' }];
    await mount();
    await submit('long running request');
    await flush(50);

    await click(byText(container, 'button', 'Stop'));
    await flush(20);

    const cancel = calls.filter((c) => c.method === 'POST' && apiPath(c.url) === '/llm/chat/jobs/job-1/cancel');
    expect(cancel).toHaveLength(1);
    expect(container.textContent).toContain('Generation cancelled by user.');
    expect(container.textContent).toContain('Error details: cancelled');
    expect(byText(container, 'button', 'Send')).toBeDefined();
  });

  it('shows an error bubble with Retry, and Retry resends the same text', async () => {
    chatAsyncStatus = 500;
    await mount();
    await submit('this will fail');
    await flush(50);

    expect(container.textContent).toContain('Operator Error');
    expect(container.textContent).toContain('Chat API error: 500');

    chatAsyncStatus = 200;
    await click(byText(container, 'button', 'Retry'));
    await flush(50);

    const posts = chatPosts();
    expect(posts).toHaveLength(2);
    const retried = posts[1].body as { messages: Array<{ role: string; content: string }> };
    expect(retried.messages[retried.messages.length - 1]).toEqual({ role: 'user', content: 'this will fail' });
    // The error bubble and the failed user turn leave the history: the model
    // sees the welcome message and the one resent turn, nothing else.
    expect(retried.messages.map((m) => m.role)).toEqual(['system', 'assistant', 'user']);
    expect(retried.messages.some((m) => m.content.includes('Operator Error'))).toBe(false);
    expect(allByText(container, '.markdown-container', 'Operator Error')).toHaveLength(0);
    expect(allByText(container, '.markdown-container', 'this will fail')).toHaveLength(1);
    expect(container.textContent).toContain('The river is blessed.');
  });

  it('regenerates an assistant message from its prompt messages', async () => {
    await mount();
    await submit('bless the river');
    await flush(50);

    jobReplies = [{ ...COMPLETED, response: 'A second blessing.' }];
    await click(byText(container, 'button', 'Regenerate'));
    await flush(50);

    const posts = chatPosts();
    expect(posts).toHaveLength(2);
    const regen = posts[1].body as { messages: Array<{ role: string; content: string }> };
    expect(regen.messages.map((m) => m.role)).toEqual(['system', 'assistant', 'user']);
    expect(container.textContent).toContain('A second blessing.');
    expect(container.textContent).not.toContain('The river is blessed.');
    expect(container.textContent).toContain('Regeneration complete');
  });

  it('runs an operator action against its endpoint', async () => {
    await mount();
    await click(byText(container, 'button', 'Analyze intention'));
    await flush(20);

    const [post] = calls.filter((c) => c.method === 'POST' && apiPath(c.url) === '/operator/analyze');
    expect(post.body).toEqual({ intention: 'help my friend with chronic back pain' });
    expect(container.textContent).toContain('[Analyze intention] help my friend with chronic back pain');
    expect(container.textContent).toContain('Target: lower back');
    expect(container.textContent).toContain('Analyze intention complete');
  });

  it('uses the typed input as the working intention', async () => {
    await mount();
    await typeInto(input(), 'clean water');
    await click(byText(container, 'button', 'Begin working'));
    await flush(20);

    const [post] = calls.filter((c) => c.method === 'POST' && apiPath(c.url) === '/operator/working');
    expect(post.body).toEqual({ intention: 'clean water', target: 'all beings', broadcast: true, duration_minutes: 5 });
    expect(container.textContent).toContain('Working wrk_1');
  });

  it('sends vajra:quick-command events after a short delay', async () => {
    await mount();
    await act(async () => {
      window.dispatchEvent(new CustomEvent('vajra:quick-command', { detail: { command: 'list populations' } }));
    });
    expect(chatPosts()).toHaveLength(0);
    await flush(300);
    const [post] = chatPosts();
    const body = post.body as { messages: Array<{ role: string; content: string }> };
    expect(body.messages[body.messages.length - 1]).toEqual({ role: 'user', content: 'list populations' });
  });

  it('sends quick-command chips and honours the context toggles', async () => {
    await mount();
    const chakraSwitch = byText(container, '.ant-space', '💚 Chakras').querySelector('button.ant-switch');
    expect(chakraSwitch).not.toBeNull();
    await click(chakraSwitch!);
    await flush(20);

    await click(byText(container, 'button', 'Get statistics'));
    await flush(50);
    const [post] = chatPosts();
    const body = post.body as { include_anatomy: boolean; messages: Array<{ role: string; content: string }> };
    expect(body.include_anatomy).toBe(false);
    expect(body.messages[0].content).not.toContain('Energetic Anatomy');
    expect(body.messages[body.messages.length - 1]).toEqual({ role: 'user', content: 'get statistics' });
  });
});
