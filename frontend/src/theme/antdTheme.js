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
    // Header navigation menu. AntD's default itemPaddingInline (20px) is too
    // generous for 7 routes + brand + status badge at ~1038px viewport width,
    // which forces the horizontal Menu into its "ellipsis" overflow mode and
    // hides the trailing items (Grimoire / Settings). Measured at 1038px:
    // brand+badge occupies 223px + 24px margin, leaving ~774px for the menu,
    // while the seven default-width items total ~818px — a 44px deficit.
    // Tightening the inline padding (6px, from the 20px default) reclaims
    // ~14px/side across the seven items, clearing the deficit with comfortable
    // headroom. A 1px font reduction (14 → 13) adds further buffer for
    // scrollbar/viewport variance. Selected/hover states use the brand
    // purple/cyan so the active route reads clearly against the glass header.
    // NOTE: the Menu carries `theme="dark"` in MainLayout, so AntD's dark
    // algorithm overrides itemSelectedBg/itemSelectedColor with its own
    // brand-purple derivative; these tokens are still defined so the menu
    // respects them the moment `theme="dark"` is dropped.
    // NOTE: `iconSize` is intentionally omitted — it is not honoured by the
    // horizontal Menu in AntD v6 cssinjs (verified at runtime); the default
    // 16px lucide icons already look correct.
    Menu: {
      itemPaddingInline: 6,                           // default 20 → 6 (reclaim 14px/side)
      fontSize: 13,                                   // default 14 → 13 (extra buffer)
      itemHeight: 48,                                 // keep comfortable touch height
      itemSelectedBg: 'rgba(139, 92, 246, 0.15)',     // subtle vajra-purple highlight
      itemSelectedColor: '#06b6d4',                   // vajra-cyan for active label
      itemHoverBg: 'rgba(139, 92, 246, 0.08)',        // subtle purple hover wash
      itemHoverColor: '#c4b5fd',                      // soft purple-200 on hover
    },
  },
};
