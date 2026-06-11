/**
 * Single source of truth for the app's brand colors.
 *
 * Used by:
 * - frontend/src/styles/globals.css (CSS variables)
 * - frontend/src/App.jsx (Antd ConfigProvider theme tokens)
 * - Any other JS code that needs to reference the brand colors
 *
 * Values are kept in sync with --primary and --secondary in globals.css.
 * The hex form is what Antd's theme tokens expect.
 */
export const COLORS = {
  /** vajra-purple — primary brand color (matches --primary in globals.css) */
  primary: '#8b5cf6',
  /** vajra-cyan — secondary accent (matches --secondary in globals.css) */
  secondary: '#06b6d4',
  /** vajra-gold — highlight (matches --accent in globals.css) */
  accent: '#ffd700',
  /** destructive / error red */
  destructive: '#dc2626',
};

/**
 * Renders a CSS `rgb(R G B / alpha)` color value from a hex string.
 * Useful for applying alpha-channel effects via CSS variables.
 */
export function hexToRgb(hex) {
  const cleaned = hex.replace('#', '');
  const r = parseInt(cleaned.substring(0, 2), 16);
  const g = parseInt(cleaned.substring(2, 4), 16);
  const b = parseInt(cleaned.substring(4, 6), 16);
  return `${r} ${g} ${b}`;
}
