/**
 * useTheme — theme state hook with localStorage persistence.
 *
 * Manages the active UI theme ('dark' | 'light' | 'sacred-dawn'), persists the
 * choice to localStorage, and mirrors the value onto
 * `document.documentElement.dataset.theme` so global CSS can react via
 * `[data-theme="..."]` selectors.
 *
 * Part of the CommandCenter decomposition (Task 3.3). Intended for use by the
 * future `ThemeToggle.jsx` sub-component, but is self-contained and may be
 * mounted anywhere in the app.
 *
 * @returns {{
 *   theme: 'dark' | 'light' | 'sacred-dawn',
 *   setTheme: (next: 'dark' | 'light' | 'sacred-dawn') => void,
 *   cycleTheme: () => void,
 * }}
 */
import { useCallback, useEffect, useState } from 'react';

/** Storage key — kept stable across reloads and HMR. */
const STORAGE_KEY = 'vajra.theme';

/** Allowed theme values, in cycle order. */
export const THEMES = ['dark', 'light', 'sacred-dawn'];

/**
 * Read the initial theme from localStorage, falling back to 'dark' (the
 * canonical Vajra.Stream theme — matches antdTheme.js colorBgBase '#0F0F1A').
 * Invalid / unknown values are coerced to 'dark'.
 *
 * @returns {'dark' | 'light' | 'sacred-dawn'}
 */
function readInitialTheme() {
  if (typeof window === 'undefined') return 'dark';
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && THEMES.includes(stored)) return stored;
  } catch {
    // localStorage may be disabled (private mode, sandbox) — fall through.
  }
  return 'dark';
}

/**
 * Persist + apply a theme value. Kept as a module-scope helper so callers
 * outside React (e.g. a future bootstrap script) can reuse it.
 *
 * @param {'dark' | 'light' | 'sacred-dawn'} theme
 */
export function applyTheme(theme) {
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = theme;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Best-effort persistence — ignore write failures.
  }
}

export const useTheme = () => {
  const [theme, setThemeState] = useState(readInitialTheme);

  // Mirror state -> DOM + storage whenever theme changes.
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  /** Explicit setter (validates against THEMES; invalid input is ignored). */
  const setTheme = useCallback((next) => {
    if (THEMES.includes(next)) {
      setThemeState(next);
    }
  }, []);

  /** Convenience cycler: dark -> light -> sacred-dawn -> dark. */
  const cycleTheme = useCallback(() => {
    setThemeState((current) => {
      const idx = THEMES.indexOf(current);
      return THEMES[(idx + 1) % THEMES.length];
    });
  }, []);

  return { theme, setTheme, cycleTheme };
};

export default useTheme;
