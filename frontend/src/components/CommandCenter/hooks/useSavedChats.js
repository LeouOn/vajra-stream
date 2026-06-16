/**
 * useSavedChats — localStorage-backed saved-conversations list.
 *
 * Stores an array of `{ id, title, messages, createdAt, updatedAt }` records
 * under `vajra.savedChats`. Provides `addChat`, `removeChat`, `renameChat`,
 * and `clearAll` operations. All mutations are reflected both in React state
 * and in localStorage.
 *
 * Design notes:
 *   - IDs are generated via `crypto.randomUUID()` when available, with a
 *     timestamp+random fallback for older browsers / non-secure contexts.
 *   - localStorage access is wrapped in try/catch — private-mode browsers and
 *     sandboxed iframes can throw on write.
 *   - The hook is SSR-safe (`typeof window === 'undefined'` guards), though
 *     Vajra.Stream is a pure SPA so this is mostly defensive.
 *
 * Part of the CommandCenter decomposition (Task 3.3). Intended for use by the
 * future `SavedConversations.jsx` and `PromptHistory.jsx` sub-components.
 *
 * @param {{
 *   storageKey?: string,
 *   maxItems?: number,
 * }} [options]
 * @returns {{
 *   chats: Array<SavedChat>,
 *   addChat: (chat: Partial<SavedChat>) => SavedChat | null,
 *   removeChat: (id: string) => void,
 *   renameChat: (id: string, title: string) => void,
 *   clearAll: () => void,
 * }}
 *
 * @typedef {Object} SavedChat
 * @property {string} id
 * @property {string} title
 * @property {Array<Record<string, unknown>>} messages
 * @property {number} createdAt
 * @property {number} updatedAt
 */
import { useCallback, useEffect, useState } from 'react';

const DEFAULT_STORAGE_KEY = 'vajra.savedChats';
const DEFAULT_MAX_ITEMS = 100;

/**
 * Generate a stable unique id. Prefers the platform UUID, falls back to a
 * timestamp+random slug.
 * @returns {string}
 */
function makeId() {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
  } catch {
    // fall through to manual id
  }
  return `chat_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Read + parse the stored chat list. Returns `[]` on any parse / access error
 * so the UI always has a valid array to render.
 *
 * @param {string} storageKey
 * @returns {Array<SavedChat>}
 */
function readStoredChats(storageKey) {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export const useSavedChats = ({
  storageKey = DEFAULT_STORAGE_KEY,
  maxItems = DEFAULT_MAX_ITEMS,
} = {}) => {
  const [chats, setChats] = useState(() => readStoredChats(storageKey));

  // Persist on every change. Trims to maxItems (newest first) to avoid
  // unbounded localStorage growth.
  useEffect(() => {
    try {
      const trimmed = chats.slice(0, maxItems);
      window.localStorage.setItem(storageKey, JSON.stringify(trimmed));
    } catch {
      // Quota exceeded or storage disabled — state still updates in-memory.
    }
  }, [chats, storageKey, maxItems]);

  /** Create + prepend a new chat. Returns the created record, or null if invalid. */
  const addChat = useCallback((partial = {}) => {
    const now = Date.now();
    const chat = {
      id: partial.id || makeId(),
      title: typeof partial.title === 'string' && partial.title.length
        ? partial.title
        : 'Untitled conversation',
      messages: Array.isArray(partial.messages) ? partial.messages : [],
      createdAt: partial.createdAt || now,
      updatedAt: partial.updatedAt || now,
    };
    setChats((prev) => [chat, ...prev].slice(0, maxItems));
    return chat;
  }, [maxItems]);

  /** Remove a chat by id (no-op if not found). */
  const removeChat = useCallback((id) => {
    setChats((prev) => prev.filter((c) => c.id !== id));
  }, []);

  /** Rename a chat by id (updates `updatedAt`). No-op if not found. */
  const renameChat = useCallback((id, title) => {
    setChats((prev) => prev.map((c) => (
      c.id === id ? { ...c, title: String(title) || c.title, updatedAt: Date.now() } : c
    )));
  }, []);

  /** Wipe the entire list. */
  const clearAll = useCallback(() => {
    setChats([]);
  }, []);

  return { chats, addChat, removeChat, renameChat, clearAll };
};

export default useSavedChats;
