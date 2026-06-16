# CommandCenter — decomposition

This directory is the future home of the decomposed `CommandCenter` component.
The current operator console lives as a single 60 KB / ~1326-line monolith at
[`components/UI/CommandCenter.jsx`](../UI/CommandCenter.jsx). Task 3.3 of the
UI/UX overhaul plan splits it into ten sub-components plus three hooks.

## Status

**STUB / IN-PROGRESS** — the original monolith is untouched. This directory
currently contains:

- `index.jsx` — pass-through re-export of the original `CommandCenter`, so new
  imports (`components/CommandCenter`) and legacy imports
  (`components/UI/CommandCenter`) resolve to the same implementation.
- `hooks/useTheme.js` — theme state (`dark` | `light` | `sacred-dawn`) with
  `localStorage` persistence + `document.documentElement.dataset.theme` sync.
- `hooks/useCommands.js` — global keyboard shortcuts: **Cmd/Ctrl+K** opens the
  command palette, **Cmd/Ctrl+S** saves the current conversation.
- `hooks/useSavedChats.js` — `localStorage`-backed list of saved conversations
  with `addChat` / `removeChat` / `renameChat` / `clearAll`.

The three hooks are already usable from any component and are wired for the
future sub-components.

## Planned decomposition

Per the implementation plan
([`docs/superpowers/plans/2026-06-12-ui-ux-overhaul-llm-refactor.md`](../../../docs/superpowers/plans/2026-06-12-ui-ux-overhaul-llm-refactor.md),
Task 3.3), the monolith will be split as follows:

| New file | Responsibility | Source |
| --- | --- | --- |
| `ChatPanel.jsx` | AI chat UI | ~250 lines extracted from monolith |
| `DivinationPanel.jsx` | Divination widgets sidebar | ~200 lines extracted |
| `ContextSidebar.jsx` | Context-injection controls | ~150 lines extracted |
| `StatusBar.jsx` | Connection / operator status | ~100 lines extracted |
| `OperatorActions.jsx` | Operator command buttons | ~100 lines extracted |
| `ContemplationPanel.jsx` | 88 Buddhas widget (refactored) | ~200 lines extracted |
| `CommandPalette.jsx` | **NEW** Cmd+K palette | ~150 lines, uses `useCommands` |
| `SavedConversations.jsx` | **NEW** localStorage + backend list | ~200 lines, uses `useSavedChats` |
| `PromptHistory.jsx` | **NEW** sidebar of past prompts | ~150 lines, uses `useSavedChats` |
| `ThemeToggle.jsx` | **NEW** light/dark/sacred-dawn switch | ~100 lines, uses `useTheme` |

Once all ten sub-components are in place, `index.jsx` will become the real
composition root (Row/Col layout wiring every sub-component and mounting the
`CommandPalette` Modal), and `components/UI/CommandCenter.jsx` will be reduced
to:

```javascript
export { CommandCenter as default, CommandCenter } from '../CommandCenter';
```

## Migration pattern

For each section extracted from the monolith:

1. Identify the JSX block in `components/UI/CommandCenter.jsx`.
2. Cut the block (with its helper functions and imports).
3. Paste into the corresponding new file under this directory.
4. Update imports to be relative to the new location.
5. In the monolith, import the new component and replace the cut block with
   `<NewComponent />`.
6. Run `npm run dev`, verify the section still renders.
7. Commit: `refactor(frontend): extract NewComponent from CommandCenter`.

## Why the stub?

The original `CommandCenter.jsx` is 60 KB of tightly-coupled code (200+ button
instances, AI chat, divination widgets, modals). Migrating it all in one task
risks breaking the working build. The stub approach gives us:

- The new directory structure exists.
- The three hooks are immediately usable.
- The original monolith is untouched — zero risk to the build.
- Future tasks can migrate one section at a time, each independently verifiable.

## Design system alignment

The hooks and future sub-components follow the established Vajra.Stream design
system:

- **Themes:** `dark` (canonical — `colorBgBase: #0F0F1A`), `light`,
  `sacred-dawn` — see `hooks/useTheme.js` and `theme/antdTheme.js`.
- **Colors:** saffron primary (`#D97706`), cream text (`#F5F0E1`),
  vajra-purple / cyan / gold accents — see `lib/colors.js`.
- **AntD v6:** `zeroRuntime` mode enabled (CSS variables); sub-components must
  use AntD tokens, not hardcoded hex values.
- **Icons:** `lucide-react`.
- **JSDoc:** every file begins with a `/** ... */` header comment block.
