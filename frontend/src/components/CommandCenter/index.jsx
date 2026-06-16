/**
 * CommandCenter — decomposition entry point (STUB).
 *
 * This module is the future home of the decomposed CommandCenter: ten
 * sub-components (ChatPanel, DivinationPanel, ContextSidebar, StatusBar,
 * OperatorActions, ContemplationPanel, CommandPalette, SavedConversations,
 * PromptHistory, ThemeToggle) composed in a Row/Col layout.
 *
 * Status: SAFETY STUB. The 60 KB / ~1326-line monolith at
 * `components/UI/CommandCenter.jsx` is left untouched for this task — the
 * migration is deferred to follow-up steps per the "RECOMMENDED APPROACH"
 * in Task 3.3 to avoid breaking the working build. The three hooks under
 * `./hooks/` are already wired for the future sub-components to consume.
 *
 * Import path note: existing callers still import from
 * `components/UI/CommandCenter` and continue to work unchanged. New code may
 * import from `components/CommandCenter` instead; both resolve to the same
 * implementation today.
 *
 * @see ./README.md for the full decomposition plan
 * @see ../../../docs/superpowers/plans/2026-06-12-ui-ux-overhaul-llm-refactor.md (Task 3.3)
 */
// Re-export the original so both import paths resolve to the same component.
// Using `export ... from` keeps this a pure pass-through with zero runtime
// cost — no wrapper component is introduced.
export { default } from '../UI/CommandCenter';
export { default as CommandCenter } from '../UI/CommandCenter';
