/**
 * useCommands — global keyboard shortcut handler for the Command Center.
 *
 * Wires two shortcuts on `window`:
 *   - Cmd/Ctrl + K  → open the command palette (calls `onOpenPalette`)
 *   - Cmd/Ctrl + S  → save the current conversation (calls `onSaveChat`,
 *                     and prevents the browser's native save-dialog)
 *
 * The hook is effect-only — it returns nothing. Consumers pass callbacks in
 * and own the resulting UI state (e.g. a Modal visibility flag for the
 * palette). This keeps the hook reusable and side-effect-pure.
 *
 * Part of the CommandCenter decomposition (Task 3.3). Intended for use by
 * the future `CommandPalette.jsx` and `SavedConversations.jsx` sub-components.
 *
 * @param {{
 *   onOpenPalette?: () => void,
 *   onSaveChat?: () => void,
 *   enabled?: boolean,
 * }} [options]
 */
import { useEffect } from 'react';

export const useCommands = ({
  onOpenPalette,
  onSaveChat,
  enabled = true,
} = {}) => {
  useEffect(() => {
    if (!enabled) return undefined;

    /**
     * Single keydown listener — cheaper than two, and makes it trivial to
     * guarantee the browser default is suppressed for the shortcuts we own.
     */
    const handleKeyDown = (event) => {
      const mod = event.metaKey || event.ctrlKey;
      if (!mod) return;

      // Cmd/Ctrl + K — palette (case-insensitive: k or K with shift)
      if (event.key === 'k' || event.key === 'K') {
        event.preventDefault();
        if (typeof onOpenPalette === 'function') onOpenPalette();
        return;
      }

      // Cmd/Ctrl + S — save (suppress native save dialog)
      if (event.key === 's' || event.key === 'S') {
        event.preventDefault();
        if (typeof onSaveChat === 'function') onSaveChat();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onOpenPalette, onSaveChat, enabled]);
};

export default useCommands;
