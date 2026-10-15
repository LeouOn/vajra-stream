// frontend/src/theme/antdTheme.js
// Ant Design v6 theme with sacred color tokens (saffron, indigo, gold, copper, etc.).
// v6 always emits CSS variables, so there is no `cssVar` switch: the v5-era
// `cssVar: true` here did not match v6's `ThemeConfig` (it takes `{prefix, key}`).
/** @type {import('antd').ThemeConfig} */
export const antdTheme = {
  hashed: true,      // Hash class names for SSR safety
  token: {
    colorBgBase: '#0F0F1A',       // Dark sacred background
    colorTextBase: '#F5F0E1',     // Cream text
    fontFamily: 'system-ui, -apple-system, sans-serif',
    borderRadius: 4,
  },
  components: {
    Button: {
      primaryShadow: '0 0 8px rgba(217, 119, 6, 0.3)',
    },
    Card: {
      colorBgContainer: '#1A1A2E',
    },
  },
};
