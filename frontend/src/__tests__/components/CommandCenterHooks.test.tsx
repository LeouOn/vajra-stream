/**
 * Vitest coverage for the three CommandCenter decomposition hooks
 * (Task 3.3 of the UI/UX overhaul plan):
 *
 *   - useTheme       — theme state + localStorage persistence
 *   - useCommands    — Cmd/Ctrl+K and Cmd/Ctrl+S shortcuts
 *   - useSavedChats  — localStorage-backed saved-conversations list
 *
 * Style follows NotFoundRoute.test.tsx: raw `createRoot` + `act`, a tiny
 * per-hook harness component, and the existing localStorage polyfill from
 * setup.ts. No AntD rendering is required for the hook bodies themselves.
 */
import React, { useEffect } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import {
  useTheme,
  applyTheme,
  THEMES,
} from '../../components/CommandCenter/hooks/useTheme';
import { useCommands } from '../../components/CommandCenter/hooks/useCommands';
import { useSavedChats } from '../../components/CommandCenter/hooks/useSavedChats';

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  localStorage.clear();
  document.documentElement.dataset.theme = '';
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
});

/* ------------------------------------------------------------------ *
 * Test harness — renders a hook once and captures its return value
 * into the `captured` variable. Each test re-renders by changing the
 * `rerenderKey` prop so callback identity changes (e.g. setTheme) are
 * picked up by the hook.
 * ------------------------------------------------------------------ */
let captured: any = null;

/* ------------------------------------------------------------------ *
 * useTheme
 * ------------------------------------------------------------------ */
describe('useTheme', () => {
  function ThemeHarness() {
    captured = useTheme();
    return null;
  }

  it('exports the canonical theme list', () => {
    expect(THEMES).toEqual(['dark', 'light', 'sacred-dawn']);
  });

  it('defaults to dark when localStorage is empty', () => {
    act(() => { root.render(<ThemeHarness />); });
    expect(captured.theme).toBe('dark');
  });

  it('reads the initial theme from localStorage', () => {
    localStorage.setItem('vajra.theme', 'light');
    act(() => { root.render(<ThemeHarness />); });
    expect(captured.theme).toBe('light');
  });

  it('coerces an invalid stored value back to dark', () => {
    localStorage.setItem('vajra.theme', 'neon-pink');
    act(() => { root.render(<ThemeHarness />); });
    expect(captured.theme).toBe('dark');
  });

  it('setTheme updates state, persists to localStorage, and mirrors to dataset', () => {
    act(() => { root.render(<ThemeHarness />); });
    act(() => { captured.setTheme('sacred-dawn'); });
    expect(captured.theme).toBe('sacred-dawn');
    expect(localStorage.getItem('vajra.theme')).toBe('sacred-dawn');
    expect(document.documentElement.dataset.theme).toBe('sacred-dawn');
  });

  it('setTheme ignores values not in THEMES', () => {
    act(() => { root.render(<ThemeHarness />); });
    act(() => { captured.setTheme('neon-pink'); });
    expect(captured.theme).toBe('dark');
    expect(localStorage.getItem('vajra.theme')).toBe('dark');
  });

  it('cycleTheme rotates dark -> light -> sacred-dawn -> dark', () => {
    act(() => { root.render(<ThemeHarness />); });
    expect(captured.theme).toBe('dark');

    act(() => { captured.cycleTheme(); });
    expect(captured.theme).toBe('light');

    act(() => { captured.cycleTheme(); });
    expect(captured.theme).toBe('sacred-dawn');

    act(() => { captured.cycleTheme(); });
    expect(captured.theme).toBe('dark');
  });

  it('applyTheme module helper writes to localStorage and dataset', () => {
    applyTheme('light');
    expect(localStorage.getItem('vajra.theme')).toBe('light');
    expect(document.documentElement.dataset.theme).toBe('light');
  });
});

/* ------------------------------------------------------------------ *
 * useCommands
 * ------------------------------------------------------------------ */
describe('useCommands', () => {
  function fireKey(key: string, opts: KeyboardEventInit = {}) {
    const ev = new KeyboardEvent('keydown', {
      key,
      bubbles: true,
      cancelable: true,
      ...opts,
    });
    window.dispatchEvent(ev);
    return ev;
  }

  function CommandsHarness(props: {
    onOpenPalette?: () => void;
    onSaveChat?: () => void;
    enabled?: boolean;
  }) {
    useCommands(props);
    return null;
  }

  it('calls onOpenPalette on Cmd+K and suppresses default', () => {
    const onOpenPalette = vi.fn();
    act(() => {
      root.render(<CommandsHarness onOpenPalette={onOpenPalette} />);
    });
    const ev = fireKey('k', { metaKey: true });
    expect(onOpenPalette).toHaveBeenCalledTimes(1);
    expect(ev.defaultPrevented).toBe(true);
  });

  it('calls onOpenPalette on Ctrl+K', () => {
    const onOpenPalette = vi.fn();
    act(() => {
      root.render(<CommandsHarness onOpenPalette={onOpenPalette} />);
    });
    fireKey('k', { ctrlKey: true });
    expect(onOpenPalette).toHaveBeenCalledTimes(1);
  });

  it('calls onSaveChat on Cmd+S and suppresses default', () => {
    const onSaveChat = vi.fn();
    act(() => {
      root.render(<CommandsHarness onSaveChat={onSaveChat} />);
    });
    const ev = fireKey('s', { metaKey: true });
    expect(onSaveChat).toHaveBeenCalledTimes(1);
    expect(ev.defaultPrevented).toBe(true);
  });

  it('calls onSaveChat on Ctrl+S', () => {
    const onSaveChat = vi.fn();
    act(() => {
      root.render(<CommandsHarness onSaveChat={onSaveChat} />);
    });
    fireKey('s', { ctrlKey: true });
    expect(onSaveChat).toHaveBeenCalledTimes(1);
  });

  it('ignores key presses without a modifier', () => {
    const onOpenPalette = vi.fn();
    const onSaveChat = vi.fn();
    act(() => {
      root.render(
        <CommandsHarness onOpenPalette={onOpenPalette} onSaveChat={onSaveChat} />,
      );
    });
    fireKey('k');
    fireKey('s');
    expect(onOpenPalette).not.toHaveBeenCalled();
    expect(onSaveChat).not.toHaveBeenCalled();
  });

  it('ignores unrelated keys even with modifier', () => {
    const onOpenPalette = vi.fn();
    const onSaveChat = vi.fn();
    act(() => {
      root.render(
        <CommandsHarness onOpenPalette={onOpenPalette} onSaveChat={onSaveChat} />,
      );
    });
    fireKey('j', { metaKey: true });
    expect(onOpenPalette).not.toHaveBeenCalled();
    expect(onSaveChat).not.toHaveBeenCalled();
  });

  it('does nothing when enabled is false', () => {
    const onOpenPalette = vi.fn();
    const onSaveChat = vi.fn();
    act(() => {
      root.render(
        <CommandsHarness
          onOpenPalette={onOpenPalette}
          onSaveChat={onSaveChat}
          enabled={false}
        />,
      );
    });
    fireKey('k', { metaKey: true });
    fireKey('s', { metaKey: true });
    expect(onOpenPalette).not.toHaveBeenCalled();
    expect(onSaveChat).not.toHaveBeenCalled();
  });

  it('handles capital K and S (Shift-held) case-insensitively', () => {
    const onOpenPalette = vi.fn();
    const onSaveChat = vi.fn();
    act(() => {
      root.render(
        <CommandsHarness onOpenPalette={onOpenPalette} onSaveChat={onSaveChat} />,
      );
    });
    fireKey('K', { metaKey: true, shiftKey: true });
    fireKey('S', { ctrlKey: true, shiftKey: true });
    expect(onOpenPalette).toHaveBeenCalledTimes(1);
    expect(onSaveChat).toHaveBeenCalledTimes(1);
  });

  it('removes the listener on unmount', () => {
    const onOpenPalette = vi.fn();
    act(() => {
      root.render(<CommandsHarness onOpenPalette={onOpenPalette} />);
    });
    act(() => { root.unmount(); });
    fireKey('k', { metaKey: true });
    expect(onOpenPalette).not.toHaveBeenCalled();
  });
});

/* ------------------------------------------------------------------ *
 * useSavedChats
 * ------------------------------------------------------------------ */
describe('useSavedChats', () => {
  function SavedChatsHarness(props: { storageKey?: string; maxItems?: number }) {
    captured = useSavedChats(props);
    return null;
  }

  function mountAndCapture() {
    act(() => {
      root.render(<SavedChatsHarness />);
    });
  }

  it('starts empty when localStorage has nothing', () => {
    mountAndCapture();
    expect(captured.chats).toEqual([]);
  });

  it('reads existing chats from localStorage on init', () => {
    const existing = [
      { id: 'a', title: 'Alpha', messages: [], createdAt: 1, updatedAt: 1 },
    ];
    localStorage.setItem('vajra.savedChats', JSON.stringify(existing));
    mountAndCapture();
    expect(captured.chats).toHaveLength(1);
    expect(captured.chats[0].id).toBe('a');
  });

  it('addChat prepends a new chat with a generated id and default title', () => {
    mountAndCapture();
    let created: any = null;
    act(() => {
      created = captured.addChat({ messages: [{ role: 'user', text: 'hi' }] });
    });
    expect(created).not.toBeNull();
    expect(typeof created.id).toBe('string');
    expect(created.id.length).toBeGreaterThan(0);
    expect(created.title).toBe('Untitled conversation');
    expect(created.messages).toEqual([{ role: 'user', text: 'hi' }]);
    expect(captured.chats).toHaveLength(1);
    expect(captured.chats[0].id).toBe(created.id);
  });

  it('addChat honors an explicit title', () => {
    mountAndCapture();
    let created: any = null;
    act(() => {
      created = captured.addChat({ title: 'My vow' });
    });
    expect(created.title).toBe('My vow');
  });

  it('addChat persists to localStorage', () => {
    mountAndCapture();
    act(() => { captured.addChat({ title: 'Persist me' }); });
    const raw = localStorage.getItem('vajra.savedChats');
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw!);
    expect(parsed[0].title).toBe('Persist me');
  });

  it('removeChat removes by id', () => {
    mountAndCapture();
    let id1: string, id2: string;
    act(() => { id1 = captured.addChat({ title: 'one' }).id; });
    act(() => { id2 = captured.addChat({ title: 'two' }).id; });
    expect(captured.chats).toHaveLength(2);
    act(() => { captured.removeChat(id1); });
    expect(captured.chats).toHaveLength(1);
    expect(captured.chats[0].id).toBe(id2);
  });

  it('removeChat is a no-op for unknown id', () => {
    mountAndCapture();
    act(() => { captured.addChat({ title: 'one' }); });
    act(() => { captured.removeChat('does-not-exist'); });
    expect(captured.chats).toHaveLength(1);
  });

  it('renameChat updates title and bumps updatedAt', () => {
    mountAndCapture();
    let created: any;
    act(() => {
      created = captured.addChat({ title: 'old', createdAt: 1000, updatedAt: 1000 });
    });
    act(() => { captured.renameChat(created.id, 'new name'); });
    expect(captured.chats[0].title).toBe('new name');
    expect(captured.chats[0].updatedAt).toBeGreaterThanOrEqual(1000);
  });

  it('renameChat with empty title keeps the existing title', () => {
    mountAndCapture();
    let created: any;
    act(() => { created = captured.addChat({ title: 'keep-me' }); });
    act(() => { captured.renameChat(created.id, ''); });
    expect(captured.chats[0].title).toBe('keep-me');
  });

  it('clearAll empties the list and persists', () => {
    mountAndCapture();
    act(() => { captured.addChat({ title: 'a' }); });
    act(() => { captured.addChat({ title: 'b' }); });
    act(() => { captured.clearAll(); });
    expect(captured.chats).toEqual([]);
    expect(JSON.parse(localStorage.getItem('vajra.savedChats')!)).toEqual([]);
  });

  it('trims to maxItems, keeping the newest', () => {
    act(() => {
      root.render(<SavedChatsHarness maxItems={2} />);
    });
    act(() => { captured.addChat({ title: 'first' }); });
    act(() => { captured.addChat({ title: 'second' }); });
    act(() => { captured.addChat({ title: 'third' }); });
    expect(captured.chats).toHaveLength(2);
    expect(captured.chats.map((c: any) => c.title)).toEqual(['third', 'second']);
    // localStorage also trimmed
    const stored = JSON.parse(localStorage.getItem('vajra.savedChats')!);
    expect(stored).toHaveLength(2);
  });

  it('respects a custom storageKey', () => {
    act(() => {
      root.render(<SavedChatsHarness storageKey="custom-key" />);
    });
    act(() => { captured.addChat({ title: 'custom' }); });
    expect(localStorage.getItem('custom-key')).not.toBeNull();
    expect(localStorage.getItem('vajra.savedChats')).toBeNull();
  });
});
