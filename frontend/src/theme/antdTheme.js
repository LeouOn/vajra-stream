// frontend/src/theme/antdTheme.js
// Ant Design v6 theme with zeroRuntime mode enabled
// and sacred color tokens (saffron, indigo, gold, copper, etc.)
export const antdTheme = {
  cssVar: true,      // Use CSS variables for tokens
  hashed: true,      // Hash class names for SSR safety
  token: {
    colorPrimary: '#D97706',      // Saffron
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
