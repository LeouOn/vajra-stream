// frontend/src/theme/antdTheme.js
// Ant Design v6 theme with CSS-variable mode enabled.
// Brand tokens mirror frontend/src/lib/colors.js (single source of truth):
//   vajra-purple #8b5cf6 (primary), vajra-cyan #06b6d4 (info/secondary),
//   vajra-gold #ffd700 (accent). Fonts: Alegreya Sans (body/UI),
//   Alegreya (serif headings), JetBrains Mono (code/data).
export const antdTheme = {
  cssVar: true,      // Use CSS variables for tokens
  hashed: true,      // Hash class names for SSR safety
  token: {
    colorPrimary: '#8b5cf6',      // vajra-purple (matches colors.js / --primary)
    colorInfo: '#06b6d4',         // vajra-cyan (matches colors.js / --secondary)
    colorBgBase: '#0F0F1A',       // Dark sacred background
    colorTextBase: '#F5F0E1',     // Cream text
    fontFamily: '"Alegreya Sans", sans-serif',
    borderRadius: 8,
  },
  components: {
    Button: {
      primaryShadow: '0 0 8px rgba(139, 92, 246, 0.3)',
    },
    Card: {
      colorBgContainer: '#1A1A2E',
      borderRadius: 8,
      paddingLG: 20,
    },
  },
};
