/**
 * OutlookDashboard — characterization tests for the main flows.
 *
 * Written before splitting the ~2,000-line monolith into hooks and section
 * components, and kept passing through the split: the API calls (paths,
 * methods, bodies), the poll lifecycles and the visible UI must not change.
 *
 * Heavy or network-bound children are stubbed; the module paths are the
 * components' own, so the stubs apply wherever the parent imports them from.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';
import type { VideoTaskPollOptions } from '../../lib/videoTaskPoll';
import {
  installFetch, apiPath, flush, byText, allByText, click, type FetchCall,
} from './domHelpers';

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({ isConnected: true, idleReflectionCount: 0 }),
  getActiveConnectionId: () => null,
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

vi.mock('../../components/2D/RothkoGenerator', () => ({ default: () => null }));
vi.mock('../../components/UI/GuidedRitualFlow', () => ({
  default: () => <div data-testid="guided-flow-stub">guided flow</div>,
}));
vi.mock('../../components/UI/JourneyCard', () => ({
  default: () => <div data-testid="journey-stub">journey</div>,
}));
vi.mock('../../components/UI/SadhanaVisualization', () => ({ default: () => null }));
vi.mock('../../components/UI/RitualVisualization', () => ({ default: () => null }));
vi.mock('../../components/UI/EpicStoryViewer', () => ({
  default: ({ narrativeParts }: { narrativeParts?: Array<{ title: string }> }) => (
    <div data-testid="epic-stub">{(narrativeParts || []).map((p) => p.title).join('|')}</div>
  ),
}));

const ttsSpeak = vi.fn();
vi.mock('../../components/UI/NarrativeTTSPlayer', () => ({
  default: ({ text, role, onSpeakRef }: {
    text?: string;
    role?: string;
    onSpeakRef?: { current: (() => void) | null };
  }) => {
    if (onSpeakRef) onSpeakRef.current = ttsSpeak;
    return <div data-testid="tts-stub" data-role={role}>{text ? `tts:${text.length}` : 'tts:none'}</div>;
  },
}));

const pollState: { opts: VideoTaskPollOptions | null; stop: ReturnType<typeof vi.fn> } = {
  opts: null,
  stop: vi.fn(),
};
vi.mock('../../lib/videoTaskPoll', () => ({
  pollVideoTask: (opts: VideoTaskPollOptions) => {
    pollState.opts = opts;
    return pollState.stop;
  },
}));

import OutlookDashboard from '../../components/UI/OutlookDashboard';

// ─── Fixtures ──────────────────────────────────────────────

const SECTION_BODY = 'Light pours from the lapis heaven across every valley and every sleeping town.';
const NARRATIVE =
  `A quiet preamble opens the rite.\n\n**I. Invocatio** ${SECTION_BODY}\n\n**II. Pacificatio** ${SECTION_BODY}`;

const GENERATED = {
  id: 42,
  type: 'single',
  genre: 'healing',
  narrative: NARRATIVE,
  model_used: 'test/model',
  provider_used: 'openrouter',
  astrology_used: 'Sun in Leo',
  divination_used: 'The Star speaks of renewal',
  entities_used: 'Green Tara',
  divination_raw: {
    tarot: { name: 'The Star' },
    iching: { name: 'Peace' },
    sigil: { kamea: 'Saturn', reduced: 'XYZ', svg: '<svg data-testid="sigil-svg"></svg>' },
  },
};

const POPULATIONS = [
  { id: 1, name: 'Pop A' },
  { id: 2, name: 'Pop B' },
  { id: 3, name: 'Pop C' },
  { id: 4, name: 'Pop D' },
];

let bgActiveOnServer = false;

function route(url: string, init: RequestInit | undefined) {
  const p = apiPath(url);
  const method = (init?.method || 'GET').toUpperCase();
  if (p === '/populations/') return { body: POPULATIONS };
  if (p === '/outlook/locations') return { body: [{ id: 'r1', name: 'Bodh Gaya', is_metaphysical: false, latitude: 24.69, longitude: 84.99 }] };
  if (p === '/outlook/characters') return { body: [] };
  if (p === '/outlook/history?limit=100') {
    return {
      body: {
        history: [
          { id: 7, type: 'single', genre: 'victory', content: 'An older transmission about victory.', date_generated: '2026-01-01T00:00:00' },
        ],
      },
    };
  }
  if (p === '/llm/models/defaults') return { body: { defaults: { outlook_narrative: { model_id: 'test/default-model:free' } } } };
  if (p === '/llm/models') return { body: { status: 'success', available: { lm_studio: [], local: [], api: [] } } };
  if (p === '/llm/models/available') return { body: { status: 'success', models: [] } };
  if (p === '/llm/providers/health') return { body: { providers: [] } };
  if (p === '/outlook/background/status') return { body: { active: bgActiveOnServer, config: {}, stats: {} } };
  if (p === '/outlook/background/start' && method === 'POST') {
    bgActiveOnServer = true;
    return { body: { status: 'started' } };
  }
  if (p === '/outlook/background/stop' && method === 'POST') {
    bgActiveOnServer = false;
    return { body: { status: 'stopped' } };
  }
  if (p === '/outlook/generate_single' && method === 'POST') return { body: GENERATED };
  if (p === '/outlook/illustration' && method === 'POST') {
    return {
      body: {
        image_data_url: 'data:image/png;base64,AAAA',
        model: 'img-model',
        provider_used: 'img-provider',
        cost_usd: 0.0123,
        revised_prompt: 'a lotus over still water',
        caption_facts: [{ label: 'Moon', value: '44%', provenance: 'computed' }],
      },
    };
  }
  if (p === '/videos/from-narrative' && method === 'POST') {
    return { body: { task_id: 'task-1', model: 'MiniMax-H3', status: 'submitted', video_prompt: 'slow lotus bloom' } };
  }
  if (p === '/radionics/affirmation/generate' && method === 'POST') return { body: { affirmation: 'I am whole and well.' } };
  return undefined;
}

// ─── Harness ───────────────────────────────────────────────

let container: HTMLDivElement;
let root: Root;
let calls: FetchCall[];

async function mount(): Promise<void> {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root.render(
      <ConfigProvider>
        <OutlookDashboard />
      </ConfigProvider>,
    );
  });
  await flush(20);
}

function posts(path: string): FetchCall[] {
  return calls.filter((c) => c.method === 'POST' && apiPath(c.url) === path);
}

async function chooseSegment(label: string): Promise<void> {
  const item = byText(container, '.ant-segmented-item', label);
  const input = item.querySelector('input');
  if (!input) throw new Error(`segment ${label} has no input`);
  await click(input);
}

async function generateSingle(): Promise<void> {
  await chooseSegment('Quick Generate');
  await click(byText(container, 'button', 'Initiate Narrative Stream'));
  await flush(20);
}

/** Wait out the 1.5s-per-section progressive reveal (2 sections). */
async function waitForReveal(): Promise<void> {
  await flush(3200);
}

beforeEach(() => {
  bgActiveOnServer = false;
  ttsSpeak.mockReset();
  pollState.opts = null;
  pollState.stop = vi.fn();
  window.localStorage.clear();
  calls = installFetch(route).calls;
});

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  vi.restoreAllMocks();
});

// ─── Tests ─────────────────────────────────────────────────

describe('OutlookDashboard — characterization', () => {
  it('fetches the same endpoints on mount (initial + isConnected refresh)', async () => {
    await mount();
    const gets = calls.filter((c) => c.method === 'GET').map((c) => apiPath(c.url)).sort();
    const once = [
      '/llm/models',
      '/llm/models/available',
      '/llm/models/defaults',
      '/llm/providers/health',
      '/outlook/background/status',
      '/outlook/characters',
      '/outlook/characters/roles/list',
      '/outlook/history?limit=100',
      '/outlook/locations',
      '/outlook/locations/types/list',
      '/populations/',
    ];
    expect(gets).toEqual([...once, ...once].sort());
    expect(container.textContent).toContain('Narrative Generation & Outlook');
    expect(container.querySelector('[data-testid="guided-flow-stub"]')).not.toBeNull();
    expect(container.textContent).toContain('Awaiting Narrative Beacon');
  });

  it('quick-generates a single narrative with the form defaults', async () => {
    await mount();
    await generateSingle();

    const [gen] = posts('/outlook/generate_single');
    expect(gen).toBeDefined();
    const body = gen.body as Record<string, unknown>;
    expect(body).toMatchObject({
      lat: 37.7749,
      lon: -122.4194,
      languages: ['English'],
      genre: 'healing',
      custom_context: null,
      difficulty: 'moderate',
      realm_id: null,
      // The first three populations are auto-selected once they load.
      population_ids: [1, 2, 3],
      character_ids: null,
      excluded_forces: null,
      include_dialogue: false,
      model: 'test/default-model:free',
      random: null,
      include_astrology: true,
      include_tarot: true,
      include_iching: true,
      randomize_realm: false,
      randomize_characters: false,
    });
    expect(typeof body.date).toBe('string');
    expect(body.stages).toBeUndefined();

    // Success refreshes history and universe data.
    const after = calls.slice(calls.indexOf(gen) + 1).map((c) => apiPath(c.url));
    expect(after).toContain('/outlook/history?limit=100');
    expect(after).toContain('/outlook/locations');

    expect(container.textContent).toContain('Transmission');
    expect(container.textContent).toContain('healing Revelation');
    expect(container.textContent).toContain('openrouter/test/model');
    expect(container.textContent).toContain('The Star');
    expect(container.textContent).toContain('Sun in Leo');
    expect(container.textContent).toContain('Entities Invoked');
  });

  it('reveals ritual sections, then the summary; Replay drives the TTS player', async () => {
    await mount();
    await generateSingle();

    const tts = container.querySelector('[data-testid="tts-stub"]');
    expect(tts?.getAttribute('data-role')).toBe('outlook_narrative');
    expect(tts?.textContent).toBe(`tts:${NARRATIVE.length}`);

    expect(container.textContent).toContain('Unveiling phase 1 of 2');
    expect(container.textContent).not.toContain('Ritual Summary');
    await waitForReveal();
    expect(container.textContent).not.toContain('Unveiling phase');
    expect(container.textContent).toContain('Ritual Summary');
    expect(container.textContent).toContain('Sigil: XYZ on Saturn grid');
    expect(container.textContent).toContain('Pacificatio');

    await click(byText(container, 'button', 'Replay'));
    expect(ttsSpeak).toHaveBeenCalledTimes(1);

    await click(byText(container, 'button', 'Save Ritual'));
    const saved = JSON.parse(window.localStorage.getItem('vajra.savedRituals.v1') || '[]') as Array<Record<string, unknown>>;
    expect(saved).toHaveLength(1);
    expect(saved[0]).toMatchObject({ genre: 'healing', narrative: NARRATIVE, entities: 'Green Tara', model: 'test/model', provider: 'openrouter' });
  }, 15000);

  it('illustrates a stored narrative by id and captions the facts', async () => {
    await mount();
    await generateSingle();
    await click(byText(container, 'button', 'Illustrate'));
    await flush(20);

    const [ill] = posts('/outlook/illustration');
    expect(ill.body).toEqual({ narrative_id: 42 });
    expect(container.textContent).toContain('Sacred Illustration');
    expect(container.textContent).toContain('$0.0123');
    expect(container.textContent).toContain('img-provider');
    expect(container.textContent).toContain('Moon');
    expect(container.textContent).toContain('44%');
    expect(container.textContent).toContain('a lotus over still water');
    expect(container.querySelector('img[src="data:image/png;base64,AAAA"]')).not.toBeNull();
  });

  it('submits a video task, polls it, and stops the poll on unmount', async () => {
    await mount();
    await generateSingle();
    await waitForReveal();
    await click(byText(container, 'button', 'Generate Manifestation Video'));
    await flush(20);

    const [vid] = posts('/videos/from-narrative');
    expect(vid.body).toEqual({
      narrative: NARRATIVE,
      genre: 'healing',
      entities: 'Green Tara',
      divination: 'The Star speaks of renewal',
      narrative_id: 42,
    });
    expect(pollState.opts?.taskId).toBe('task-1');
    expect(pollState.opts?.model).toBe('MiniMax-H3');
    expect(container.textContent).toContain('slow lotus bloom');
    expect(container.textContent).toContain('Generating video...');

    expect(pollState.stop).not.toHaveBeenCalled();
    act(() => root.unmount());
    expect(pollState.stop).toHaveBeenCalledTimes(1);
  }, 15000);

  it('renders the finished video and does not stop a finished poll again', async () => {
    await mount();
    await generateSingle();
    await waitForReveal();
    await click(byText(container, 'button', 'Generate Manifestation Video'));
    await flush(20);

    const opts = pollState.opts;
    expect(opts).not.toBeNull();
    await act(async () => {
      opts?.onStatus({ status: 'succeeded', video_url: '/media/v.mp4' });
      opts?.onFinish({ status: 'succeeded', video_url: '/media/v.mp4' });
    });
    expect(container.querySelector('video[src="/media/v.mp4"]')).not.toBeNull();
    expect(container.textContent).toContain('Download video');

    act(() => root.unmount());
    expect(pollState.stop).not.toHaveBeenCalled();
  }, 15000);

  it('forges an affirmation from the narrative genre', async () => {
    await mount();
    await generateSingle();
    await click(byText(container, '.ant-tabs-tab-btn', 'Affirmation'));
    await click(byText(container, 'button', 'Generate Affirmation'));
    await flush(20);

    const [aff] = posts('/radionics/affirmation/generate');
    expect(aff.body).toEqual({ intention: 'healing', style: 'empowering' });
    expect(container.textContent).toContain('I am whole and well.');
    expect(container.textContent).toContain('Regenerate');
  });

  it('starts background generation, polls every 30s, and clears the poll on unmount', async () => {
    const setIntervalSpy = vi.spyOn(window, 'setInterval');
    const clearIntervalSpy = vi.spyOn(window, 'clearInterval');
    await mount();

    const bgSwitch = allByText(container, 'button.ant-switch', 'Off')[0];
    expect(bgSwitch).toBeDefined();
    await click(bgSwitch);
    await flush(20);

    const [start] = posts('/outlook/background/start');
    expect(start.body).toEqual({
      interval_minutes: 60,
      loop_mode: 'sequential_delay',
      cycle_genres: true,
      cycle_intentions: true,
      include_astrology: true,
      include_tarot: true,
      include_iching: true,
      include_geomancy: true,
      lat: 37.7749,
      lon: -122.4194,
      languages: ['English'],
    });
    expect(container.textContent).toContain('Running every 60 min');

    const pollCall = setIntervalSpy.mock.calls.find((c) => c[1] === 30000);
    expect(pollCall).toBeDefined();
    const pollIndex = setIntervalSpy.mock.calls.indexOf(pollCall!);
    const pollId = setIntervalSpy.mock.results[pollIndex].value as number;

    const before = calls.length;
    await act(async () => {
      (pollCall![0] as () => void)();
    });
    const polled = calls.slice(before).map((c) => apiPath(c.url));
    expect(polled).toEqual(['/outlook/background/status', '/outlook/history?limit=100']);

    act(() => root.unmount());
    expect(clearIntervalSpy).toHaveBeenCalledWith(pollId);
  });

  it('stops background generation when toggled off', async () => {
    bgActiveOnServer = true;
    await mount();
    const onSwitch = allByText(container, 'button.ant-switch', 'On')[0];
    await click(onSwitch);
    await flush(20);
    expect(posts('/outlook/background/stop')).toHaveLength(1);
    expect(container.textContent).not.toContain('Running every');
  });

  it('loads a history item into the generator', async () => {
    await mount();
    await chooseSegment('History');
    expect(container.textContent).toContain('An older transmission about victory.');
    const loadBtn = container.querySelector('.ant-card-actions button');
    expect(loadBtn).not.toBeNull();
    await click(loadBtn!);
    await flush(20);
    expect(container.textContent).toContain('victory Revelation');
    expect(container.textContent).toContain('An older transmission about victory.');
  });

  it('shows the journey tab', async () => {
    await mount();
    await chooseSegment('Journey');
    expect(container.querySelector('[data-testid="journey-stub"]')).not.toBeNull();
  });
});
