# Frontend Styling Guide: Tailwind CSS ↔ Ant Design Boundary

> **Deferred Task 6.** This guide documents the deliberate coexistence of
> **Tailwind CSS** and **Ant Design (antd v6)** in `frontend/`. Both systems
> stay. The goal is a clear, predictable split of responsibilities so new
> components match existing patterns without fighting either library.

---

## 1. TL;DR — The Boundary

| Use case | Use this |
| --- | --- |
| Page layout, flexbox/grid, spacing, padding, sizing | **Tailwind** (`className`) |
| Brand color utilities, text color, background tints, opacity | **Tailwind** (`className`) |
| Typography scale, font families, responsive breakpoints | **Tailwind** (`className`) |
| Animations, transitions, transforms, hover/focus states on raw elements | **Tailwind** (`className`) |
| Icons (lucide-react) sizing/color | **Tailwind** (`className`) |
| Custom reusable visual primitives (`.glassmorphism`, `.vajra-button-*`, `.cyber-panel`) | **Tailwind `@layer components`** in `globals.css` |
| Tables, Modals, Drawers, Forms, Selects, Date pickers, Tabs, Menus, Uploads, Popconfirm, Toasts | **Ant Design** components + props |
| Buttons that participate in a Form/Modal footer or need `loading`/`danger`/`icon` props | **Ant Design `Button`** |
| Theming a whole widget tree (dark mode, brand color tokens) | **Ant Design `ConfigProvider`** |

**One-sentence rule:** *Tailwind paints the box; AntD provides the interactive widget.*

**Never** fight AntD's internal DOM with Tailwind overrides on its components.
If you find yourself writing `className="[.ant-table-cell]:!p-4"` to force
AntD internals, stop — use the component's documented API (`size`, `style`,
`token` overrides via `ConfigProvider`) instead.

---

## 2. Why Both?

- **Tailwind** is unmatched for the bespoke mystic/cyberdeck aesthetic of this
  app (radial gradient backgrounds, glow shadows, scanlines, glassmorphism,
  custom keyframe animations). These effects are project-specific visual
  styling, not generic widget behavior — exactly what utility CSS is for.
- **Ant Design** provides battle-tested, accessible complex widgets
  (`Table`, `Form`, `DatePicker`, `Drawer`, `Popconfirm`, `Tabs`...) that would
  be prohibitively expensive to rebuild. Their internal state, keyboard
  handling, and a11y are the value — not their visual skin.

The two systems are not redundant; they address different layers of the UI.

---

## 3. Tailwind — When & How

### Reach for Tailwind when...

- You're laying out a page, panel, or card grid.
- You're coloring/text-sizing plain HTML elements (`<div>`, `<span>`, `<p>`, `<h2>`, `<button>` that is *not* part of an AntD form/dialog).
- You're animating or transforming a plain element.
- You're styling a 3D canvas wrapper (`<Canvas>` from `@react-three/fiber`).
- You're styling icon size/color (lucide-react `<Icon className="w-4 h-4 text-purple-400" />`).

### Canonical patterns from the codebase

**Page route wrapper** (`frontend/src/App.jsx`):

```jsx
<Route path="/operations" element={
  <div className="flex-1 h-full overflow-hidden">
    <OperationsPanel />
  </div>
} />
```

**Floating info panel with Tailwind layout + opacity tints**
(`frontend/src/App.jsx`):

```jsx
<div className="absolute top-4 left-4 bg-gray-900/80 backdrop-blur-md
                border border-white/10 rounded-xl p-4 max-w-sm
                shadow-2xl z-10 pointer-events-none">
  <h3 className="text-sm font-semibold mb-3 text-vajra-cyan glow-cyan">
    Active Session
  </h3>
  ...
</div>
```

**Icon coloring via Tailwind utility** (`frontend/src/routes/Buddhas/SessionHistory.jsx`):

```jsx
<History size={16} className="text-purple-400" />
```

### Custom component classes

Reusable visual primitives live in `@layer components` inside
`frontend/src/styles/globals.css` and compose Tailwind utilities with raw CSS:

- `.glassmorphism`, `.mystical-card`, `.mystical-input`, `.mystical-border`
- `.vajra-button`, `.vajra-button-primary`, `.vajra-button-secondary`,
  `.vajra-button-success`, `.vajra-button-danger`
- `.cyber-panel`, `.cyber-grid`, `.scanline`, `.crt-screen`
- `.frequency-display`, `.glow-text`, `.glow-gold`, `.glow-cyan`
- `.pulse-glow`, `.rotate-glow`, `.float-animation`

Prefer these over re-deriving the same glow/gradient every time.

### Brand color tokens in Tailwind

`frontend/tailwind.config.js` exposes named brand colors:

```js
colors: {
  vajra: {
    cyan: '#06b6d4',
    purple: '#8b5cf6',
    'deep-purple': '#7c3aed',
    gold: '#ffd700',
    // ...
  }
}
```

Use them as `text-vajra-purple`, `bg-vajra-cyan`, `border-vajra-gold/40`, etc.

---

## 4. Ant Design — When & How

### Reach for AntD when...

- The UI element has **behavior** beyond pure presentation: dropdowns,
  modals, drawers, popovers, popconfirms, tooltips, tabs, menus, carousels,
  steppers, pagination, autocomplete, file upload, date pickers.
- You need a **data `Table`** with sorting, filtering, pagination, row
  selection, or virtualization.
- You need a **`Form`** with validation, field binding, and submit handling.
- You're showing a transient **toast/notification** — use `message.*` /
  `notification.*` from antd, not a hand-rolled `<div>`.

### Reach for AntD `Button` specifically when...

- It lives inside an AntD `Modal`/`Drawer`/`Form` footer (props like
  `htmlType="submit"`, `loading`, `danger` matter).
- It needs the `icon`, `size`, `type="text"|"link"`, or `disabled` AntD API.

For free-floating decorative buttons on canvases or hero sections, the
custom `.vajra-button-*` classes (Tailwind-based) are fine and idiomatic.

### Canonical pattern from the codebase

**`SessionHistory.jsx`** — a full AntD widget tree (`Card`, `Button`,
`Typography`, `Tag`, `Space`, `Popconfirm`, `message`) with Tailwind *only*
on the lucide icon inside:

```jsx
import { Card, Button, Typography, Tag, Space, Popconfirm, message } from 'antd';

<Card
  size="small"
  title={
    <Space size={8} align="center">
      <History size={16} className="text-purple-400" />     {/* Tailwind on icon only */}
      <Title level={5} style={{ margin: 0 }}>Session History</Title>
      <Tag color="purple">{sessions.length}</Tag>
    </Space>
  }
  extra={
    <Popconfirm title="Clear all session history?" okText="Clear" cancelText="Keep"
                onConfirm={handleClear}>
      <Button type="text" size="small" danger icon={<Trash2 size={14} />}>
        Clear
      </Button>
    </Popconfirm>
  }
>
  {/* ... list body ... */}
</Card>
```

Notice:
- The icon gets `className="text-purple-400"` — that's Tailwind on a lucide
  SVG, which AntD does not own. Fine.
- The `Card`, `Button`, `Tag` use **AntD props** (`size`, `type`, `color`,
  `danger`, `level`). No Tailwind utilities are applied to those components.

### `SavedChartsDrawer.jsx` — AntD `Drawer` + `Select` inside a Tailwind shell

The outer `<div>` shell is Tailwind (`bg-gray-950/40 rounded-xl border ...`),
but every interactive widget inside (`Drawer`, `Select`, `Input`, `Button`,
`Popconfirm`) is AntD with prop-driven styling. This is the canonical
"Tailwind shell, AntD internals" layout.

---

## 5. The Single Source of Truth for Brand Colors

Three files cooperate. **Keep them in sync.**

| File | Role | Format |
| --- | --- | --- |
| `frontend/src/lib/colors.js` | **Authoritative hex values** | `COLORS.primary = '#8b5cf6'`, etc. |
| `frontend/src/styles/globals.css` | CSS variables for raw CSS + Tailwind `bg-[var(--primary)]` | `--primary: 139 92 246;` (space-separated RGB) |
| `frontend/src/theme/antdTheme.js` | AntD theme tokens | `colorPrimary`, `colorBgBase`, ... |

The CSS variables in `globals.css` are intentionally space-separated RGB
triplets so they can be composed with alpha: `rgb(var(--primary) / 0.5)`.

### How AntD receives the brand color

In `frontend/src/App.jsx`, `ConfigProvider` overrides AntD's theme tokens with
the **authoritative** values from `COLORS`:

```jsx
import { ConfigProvider, theme } from 'antd';
import { COLORS } from './lib/colors';
import { antdTheme } from './theme/antdTheme';

<ConfigProvider
  theme={{
    ...antdTheme,
    algorithm: theme.darkAlgorithm,
    token: {
      ...antdTheme.token,
      colorPrimary: COLORS.primary,    // vajra-purple  → matches --primary
      colorInfo:   COLORS.secondary,   // vajra-cyan    → matches --secondary
    },
  }}
>
  {/* app */}
</ConfigProvider>
```

> **Note:** `antdTheme.js` ships a placeholder `colorPrimary: '#D97706'`
> (saffron). The `App.jsx` override is **canonical** — it always wins because
> the `token` spread happens after `...antdTheme.token`. When in doubt, edit
> `lib/colors.js`, not `antdTheme.js`.

### How Tailwind receives the brand color

Two interchangeable options — pick based on readability:

```jsx
// (a) Named tokens from tailwind.config.js
<span className="text-vajra-purple" />

// (b) Direct CSS-variable reference (works for any custom alpha)
<span className="bg-[rgb(var(--primary)/0.4)]" />
```

Both resolve to the same hex because `tailwind.config.js` mirrors
`lib/colors.js`. If you change a brand color, update **both** files plus
`globals.css`.

---

## 6. Decision Flowchart

```
Am I building an interactive widget (table, modal, drawer, form,
select, date picker, tabs, menu, upload, popover, toast)?
│
├─ YES → Use the AntD component. Drive appearance via props and
│        ConfigProvider tokens. Do NOT slam Tailwind on it.
│
└─ NO (it's layout, color, typography, animation, or a plain
        element like an icon, div, span, h2, canvas wrapper)
        │
        └─ Use Tailwind className. Prefer @layer components
           primitives in globals.css when the pattern repeats.
```

---

## 7. Anti-patterns to Avoid

1. **`<Button className="bg-purple-600 !important ...">` on an AntD `Button`.**
   AntD manages its own background via tokens. Use `<Button type="primary">`
   so it picks up `colorPrimary` from `ConfigProvider`. If the look is wrong,
   fix the token, not the button.

2. **Re-skinning AntD internals with arbitrary selectors**
   (`className="[.ant-modal-body]:!p-8"`). Use the component's documented API
   (`styles.body` on `Modal`, `bodyStyle` where applicable) or a
   `ConfigProvider` `components.Modal` token override.

3. **Reimplementing an AntD widget in Tailwind** because "it's just a
   dropdown." It is not — a11y, keyboard nav, and focus trapping are hard.
   Use AntD.

4. **Reimplementing a glow/gradient** inline when `.vajra-button-*`,
   `.glassmorphism`, or `.mystical-card` already exists. Extend the
   `@layer components` library instead.

5. **Duplicating a brand hex literal** in component code. Import from
   `lib/colors.js` or reference the CSS variable / Tailwind token.

---

## 8. Optional Enforcement (Convention)

There is no off-the-shelf ESLint rule that reliably distinguishes "Tailwind
on a plain `<div>`" (allowed) from "Tailwind fighting AntD `<Button>`"
(forbidden) without adding a new dependency. We therefore rely on **code
review + this guide** rather than a brittle lint rule.

When a reviewer flags a violation, the agreed fix is one of:

- **Convert** the Tailwind-styled AntD component to use its props / tokens.
- **Replace** the AntD component with a plain element + Tailwind if no
  widget behavior is actually needed.
- **Add a scoped `// STYLING: <reason>` comment** if a genuine edge case
  requires overriding AntD internals, so future readers know it's
  intentional.

If the team later wants automated enforcement, the lightweight path is a
custom `no-restricted-syntax` rule in `frontend/.eslintrc.json` that flags
`className` on a configurable allow/deny list of JSX elements — out of
scope for this documentation pass.

---

## 9. Quick Reference

- Authoritative colors: `frontend/src/lib/colors.js`
- CSS variables + Tailwind `@layer` primitives: `frontend/src/styles/globals.css`
- Tailwind brand tokens: `frontend/tailwind.config.js`
- AntD theme tokens: `frontend/src/theme/antdTheme.js`
- AntD theme wiring (`ConfigProvider`): `frontend/src/App.jsx`
- Reference component (mixed usage done right):
  `frontend/src/routes/Buddhas/SessionHistory.jsx`,
  `frontend/src/components/UI/SavedChartsDrawer.jsx`

---

_May this guide keep our stylesheets empty of inherent existence yet perfectly functional in conventional reality._
