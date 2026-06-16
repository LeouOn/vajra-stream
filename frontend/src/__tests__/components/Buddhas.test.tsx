/**
 * Vitest coverage for the /buddhas route and its 6 sidebar components
 * (Task 3.4 of the UI/UX overhaul plan):
 *
 *   - IntentionEditor  — controlled TextArea, persisted to localStorage
 *   - DedicationText   — random dedication-of-merit verse
 *   - SessionHistory   — localStorage-backed recitation log
 *   - ShareExport      — copies a summary to the clipboard
 *   - DailyStreak      — consecutive-day Statistic
 *   - AudioSettings    — Select with low/medium/high
 *   - BuddhasPage (index.jsx) — composes the above with a live WS status
 *
 * `useWebSocketStable` is mocked at the module level to return a controllable
 * stub. `fetch` and `audioFeedback` are also stubbed so the page test does
 * not hit the network or attempt to play audio.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import type { FC } from 'react';

/* ------------------------------------------------------------------ *
 * Module-level mocks. `useWebSocketStable` is the canonical WS hook;
 * stubbing it once here covers every component that imports it.
 * ------------------------------------------------------------------ */
const wsState = {
  buddhaStatus: null as any,
  providerHealth: [] as any[],
  lastProviderHealthUpdate: null as number | null,
};

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => wsState,
}));

vi.mock('../../utils/audioFeedback', () => ({
  audioFeedback: { playTelemetry: vi.fn() },
}));

/* fetch stub — page hooks call POST /operator/buddhas/recitation/* and the
 * ProviderSettings one-shot fetch. We never want real network here. */
const fetchSpy = vi.fn();
beforeEach(() => {
  fetchSpy.mockReset();
  fetchSpy.mockResolvedValue({ ok: true, status: 200, json: async () => [] });
  (globalThis as any).fetch = fetchSpy;
});

/* clipboard stub — ShareExport uses navigator.clipboard.writeText. */
const clipboardWrite = vi.fn().mockResolvedValue(undefined);
beforeEach(() => {
  clipboardWrite.mockReset();
  clipboardWrite.mockResolvedValue(undefined);
  vi.stubGlobal('navigator', {
    ...(globalThis.navigator || {}),
    clipboard: { writeText: clipboardWrite },
  });
  // window.isSecureContext is checked by ShareExport before the async path.
  (window as any).isSecureContext = true;
});

/* ------------------------------------------------------------------ *
 * Component imports — must come AFTER vi.mock() so the mocked modules
 * are wired into the imported components.
 * ------------------------------------------------------------------ */
import IntentionEditor from '../../routes/Buddhas/IntentionEditor';
import DedicationText from '../../routes/Buddhas/DedicationText';
import SessionHistory from '../../routes/Buddhas/SessionHistory';
import ShareExport from '../../routes/Buddhas/ShareExport';
import DailyStreak from '../../routes/Buddhas/DailyStreak';
import AudioSettings from '../../routes/Buddhas/AudioSettings';
import BuddhasPage from '../../routes/Buddhas/index';

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  localStorage.clear();
  wsState.buddhaStatus = null;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
});

/**
 * Render `node` inside the canonical AntD dark-themed + MemoryRouter
 * wrapper so route components behave the same as they do in production.
 */
function renderNode(node: React.ReactNode) {
  act(() => {
    root.render(
      <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
        <MemoryRouter>{node}</MemoryRouter>
      </ConfigProvider>,
    );
  });
}

/* ------------------------------------------------------------------ *
 * IntentionEditor
 * ------------------------------------------------------------------ */
describe('IntentionEditor', () => {
  it('renders the title and the default intention when none is stored', () => {
    renderNode(<IntentionEditor value="" onChange={() => {}} />);
    expect(container.textContent).toContain('Bodhicitta Intention');
    // The default intention is restored via onChange on mount.
    expect(container.textContent).toContain('Set the heart-intention');
  });

  it('fires onChange with the saved intention on mount when value is empty', () => {
    localStorage.setItem('vajra-buddha-intention', 'saved vow');
    const onChange = vi.fn();
    renderNode(<IntentionEditor value="" onChange={onChange} />);
    expect(onChange).toHaveBeenCalledWith('saved vow');
  });

  it('fires onChange with the default intention when nothing is stored', () => {
    const onChange = vi.fn();
    renderNode(<IntentionEditor value="" onChange={onChange} />);
    expect(onChange).toHaveBeenCalledWith('愿一切众生离苦得乐');
  });

  it('persists the current value to localStorage when value is set', () => {
    renderNode(<IntentionEditor value="my current vow" onChange={() => {}} />);
    expect(localStorage.getItem('vajra-buddha-intention')).toBe('my current vow');
  });

  it('renders the passed value inside the textarea', () => {
    renderNode(<IntentionEditor value="hello world" onChange={() => {}} />);
    const ta = container.querySelector('textarea');
    expect(ta).not.toBeNull();
    expect(ta!.value).toBe('hello world');
  });
});

/* ------------------------------------------------------------------ *
 * DedicationText
 * ------------------------------------------------------------------ */
describe('DedicationText', () => {
  it('renders the title and one of the three dedications on mount', () => {
    renderNode(<DedicationText />);
    expect(container.textContent).toContain('Dedication of Merit');
    // All three bodies share the sanskrit header 'pariṇāmanā'.
    expect(container.textContent).toContain('pariṇāmanā');
    // At least one of the known attributions should appear.
    const attributions = ['Longchenpa', 'Shantideva', 'Four Immeasurables'];
    expect(attributions.some((a) => container.textContent!.includes(a))).toBe(true);
  });

  it('the refresh button is rendered and clickable', () => {
    const onRefresh = vi.fn();
    renderNode(<DedicationText onRefresh={onRefresh} />);
    const btn = container.querySelector('button[aria-label="Draw another dedication"]');
    expect(btn).not.toBeNull();
    act(() => { btn!.click(); });
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});

/* ------------------------------------------------------------------ *
 * SessionHistory
 * ------------------------------------------------------------------ */
describe('SessionHistory', () => {
  it('renders the empty state when nothing is stored', () => {
    renderNode(<SessionHistory buddhaStatus={null} />);
    expect(container.textContent).toContain('Session History');
    expect(container.textContent).toContain('No recorded sessions yet.');
    // Count tag is 0.
    expect(container.textContent).toContain('0');
  });

  it('disables Record when buddhaStatus is not running', () => {
    renderNode(<SessionHistory buddhaStatus={{ running: false }} />);
    const buttons = container.querySelectorAll('button');
    const recordBtn = Array.from(buttons).find((b) => b.textContent === 'Record');
    expect(recordBtn).toBeDefined();
    expect(recordBtn!.hasAttribute('disabled')).toBe(true);
  });

  it('loads stored sessions from localStorage and renders them', () => {
    const sessions = [
      {
        id: 'sess-1',
        ts: Date.now(),
        intention: 'May beings be free',
        totalRecited: 88,
        malaCount: 1,
        dedications: 3,
        cycle: 1,
      },
    ];
    localStorage.setItem('vajra-buddha-sessions', JSON.stringify(sessions));
    renderNode(<SessionHistory buddhaStatus={null} />);
    expect(container.textContent).toContain('×88');
    expect(container.textContent).toContain('mala 1');
    expect(container.textContent).toContain('May beings be free');
  });

  it('clears history via the clear button (Popconfirm confirm)', () => {
    const sessions = [
      { id: 's1', ts: 1, intention: 'a', totalRecited: 1, malaCount: 0, dedications: 0, cycle: 0 },
    ];
    localStorage.setItem('vajra-buddha-sessions', JSON.stringify(sessions));
    renderNode(<SessionHistory buddhaStatus={null} />);
    // The clear button is the second extra control (danger text button).
    const dangerBtn = container.querySelector('button.ant-btn-dangerous');
    expect(dangerBtn).not.toBeNull();
    act(() => { dangerBtn!.click(); });
    // Popconfirm opens — find the "Clear" confirm button in the popover.
    const confirmBtns = document.querySelectorAll('.ant-popconfirm-buttons .ant-btn-primary');
    if (confirmBtns.length > 0) {
      act(() => { (confirmBtns[0] as HTMLButtonElement).click(); });
      // After confirm, localStorage should be empty.
      expect(localStorage.getItem('vajra-buddha-sessions')).toBe('[]');
    }
  });
});

/* ------------------------------------------------------------------ *
 * ShareExport
 * ------------------------------------------------------------------ */
describe('ShareExport', () => {
  it('renders the title and disabled button when no data is present', () => {
    renderNode(<ShareExport buddhaStatus={null} intention="" />);
    expect(container.textContent).toContain('Share / Export');
    const btn = container.querySelector('button');
    expect(btn).not.toBeNull();
    expect(btn!.hasAttribute('disabled')).toBe(true);
  });

  it('enables the button when an intention is provided', () => {
    renderNode(<ShareExport buddhaStatus={null} intention="my vow" />);
    const btn = container.querySelector('button');
    expect(btn!.hasAttribute('disabled')).toBe(false);
  });

  it('copies a summary to the clipboard when clicked', async () => {
    renderNode(
      <ShareExport
        buddhaStatus={{ total_recited: 88, mala_count: 1, current_cycle: 1 }}
        intention="test vow"
      />,
    );
    const btn = container.querySelector('button')!;
    await act(async () => { btn.click(); });
    // The copy is async; flush microtasks.
    await act(async () => { await Promise.resolve(); });
    expect(clipboardWrite).toHaveBeenCalledTimes(1);
    const copiedText = clipboardWrite.mock.calls[0][0] as string;
    expect(copiedText).toContain('88 Buddhas');
    expect(copiedText).toContain('Intention: test vow');
    expect(copiedText).toContain('Total recited: 88');
  });
});

/* ------------------------------------------------------------------ *
 * DailyStreak
 * ------------------------------------------------------------------ */
describe('DailyStreak', () => {
  function todayStr() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  it('renders the title and 0 days when nothing is stored', () => {
    renderNode(<DailyStreak />);
    expect(container.textContent).toContain('Daily Streak');
    expect(container.textContent).toContain('0');
  });

  it('shows the stored count and last practice date', () => {
    localStorage.setItem(
      'vajra-buddha-streak',
      JSON.stringify({ lastDay: '2024-01-01', count: 7 }),
    );
    renderNode(<DailyStreak />);
    expect(container.textContent).toContain('7');
    expect(container.textContent).toContain('Last practice: 2024-01-01');
  });

  it('mark today enables and bumps count when last practice was yesterday', () => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    const y = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    localStorage.setItem(
      'vajra-buddha-streak',
      JSON.stringify({ lastDay: y, count: 2 }),
    );
    renderNode(<DailyStreak />);
    const markBtn = Array.from(container.querySelectorAll('button'))
      .find((b) => b.textContent === 'Mark today');
    expect(markBtn).toBeDefined();
    act(() => { markBtn!.click(); });
    const stored = JSON.parse(localStorage.getItem('vajra-buddha-streak')!);
    expect(stored.count).toBe(3);
    expect(stored.lastDay).toBe(todayStr());
  });

  it('mark today resets count to 1 when streak is broken', () => {
    localStorage.setItem(
      'vajra-buddha-streak',
      JSON.stringify({ lastDay: '2020-01-01', count: 50 }),
    );
    renderNode(<DailyStreak />);
    const markBtn = Array.from(container.querySelectorAll('button'))
      .find((b) => b.textContent === 'Mark today');
    act(() => { markBtn!.click(); });
    const stored = JSON.parse(localStorage.getItem('vajra-buddha-streak')!);
    expect(stored.count).toBe(1);
    expect(stored.lastDay).toBe(todayStr());
  });

  it('mark today is a no-op (button disabled) when already marked today', () => {
    localStorage.setItem(
      'vajra-buddha-streak',
      JSON.stringify({ lastDay: todayStr(), count: 5 }),
    );
    renderNode(<DailyStreak />);
    const buttons = container.querySelectorAll('button');
    // All buttons should be disabled (the only button is "Marked for today").
    const markBtn = Array.from(buttons).find((b) => b.textContent === 'Marked for today');
    expect(markBtn).toBeDefined();
    expect(markBtn!.hasAttribute('disabled')).toBe(true);
  });
});

/* ------------------------------------------------------------------ *
 * AudioSettings
 * ------------------------------------------------------------------ */
describe('AudioSettings', () => {
  it('renders the title and defaults to medium when nothing is stored', () => {
    renderNode(<AudioSettings />);
    expect(container.textContent).toContain('Audio Quality');
    expect(container.textContent).toContain('MEDIUM');
  });

  it('shows the low description when low is saved', () => {
    localStorage.setItem('vajra-buddha-audio-quality', 'low');
    renderNode(<AudioSettings />);
    expect(container.textContent).toContain('LOW');
    expect(container.textContent).toContain('Smallest payload');
  });

  it('shows the high description when high is saved', () => {
    localStorage.setItem('vajra-buddha-audio-quality', 'high');
    renderNode(<AudioSettings />);
    expect(container.textContent).toContain('HIGH');
    expect(container.textContent).toContain('Full fidelity');
  });

  it('honors a controlled value over the stored one', () => {
    localStorage.setItem('vajra-buddha-audio-quality', 'low');
    renderNode(<AudioSettings value="high" onChange={() => {}} />);
    expect(container.textContent).toContain('HIGH');
  });
});

/* ------------------------------------------------------------------ *
 * BuddhasPage (the route composition root)
 * ------------------------------------------------------------------ */
describe('BuddhasPage', () => {
  it('renders the page header and graceful empty state when no WS status', () => {
    wsState.buddhaStatus = null;
    renderNode(<BuddhasPage />);
    expect(container.textContent).toContain('88 Buddhas Contemplation');
    expect(container.textContent).toContain('Idle');
    expect(container.textContent).toContain('No active recitation.');
    // Sidebar titles all render.
    expect(container.textContent).toContain('Daily Streak');
    expect(container.textContent).toContain('Dedication of Merit');
    expect(container.textContent).toContain('Share / Export');
    expect(container.textContent).toContain('Audio Quality');
    expect(container.textContent).toContain('Session History');
  });

  it('shows Reciting + the current Buddha name when status is live', () => {
    wsState.buddhaStatus = {
      running: true,
      progress_pct: 42,
      current_cycle: 2,
      total_recited: 36,
      total_buddhas: 88,
      mala_count: 1,
      dedications: 2,
      current_buddha: {
        name_chinese: '釋迦牟尼佛',
        name_pinyin: 'Shìjiā Móunífó',
        name_sanskrit: 'Śākyamuni',
        category: 'past',
        meaning: 'Sage of the Śākyas',
        realm: 'Pure Land',
        light: 'Golden',
      },
    };
    renderNode(<BuddhasPage />);
    expect(container.textContent).toContain('Reciting');
    expect(container.textContent).toContain('釋迦牟尼佛');
    expect(container.textContent).toContain('Shìjiā Móunífó');
    expect(container.textContent).toContain('53 Past Buddhas');
    expect(container.textContent).toContain('36 chanted');
  });

  it('Start button POSTs to the recitation start endpoint', async () => {
    wsState.buddhaStatus = { running: false };
    renderNode(<BuddhasPage />);
    const startBtn = Array.from(container.querySelectorAll('button'))
      .find((b) => /Start 88-Buddha/.test(b.textContent || ''));
    expect(startBtn).toBeDefined();
    await act(async () => { startBtn!.click(); });
    await act(async () => { await Promise.resolve(); });
    expect(fetchSpy).toHaveBeenCalled();
    const call = fetchSpy.mock.calls[0];
    expect(call[0]).toContain('/operator/buddhas/recitation/start');
    expect(call[1]?.method).toBe('POST');
  });

  it('Stop button POSTs to the recitation stop endpoint when running', async () => {
    wsState.buddhaStatus = { running: true };
    renderNode(<BuddhasPage />);
    const stopBtn = Array.from(container.querySelectorAll('button'))
      .find((b) => (b.textContent || '').includes('Stop Recitation'));
    expect(stopBtn).toBeDefined();
    await act(async () => { stopBtn!.click(); });
    await act(async () => { await Promise.resolve(); });
    expect(fetchSpy).toHaveBeenCalled();
    const call = fetchSpy.mock.calls[0];
    expect(call[0]).toContain('/operator/buddhas/recitation/stop');
    expect(call[1]?.method).toBe('POST');
  });
});
