# CommandCenter — decomposition

The operator console is composed in
[`components/UI/CommandCenter.tsx`](../UI/CommandCenter.tsx) (the route
component `App.tsx` mounts). It holds only UI state (zoom modal, log tab) and
wires the hooks and sections in this directory together. The split was done
on 2026-10-16 (roadmap Phase 3); the flows are pinned by
`src/__tests__/components/CommandCenter.flows.test.tsx`.

## Hooks (state, effects, requests)

Called in this order so the effects run in the original order:

| Hook | Owns |
| --- | --- |
| `useAstroContext` | Current sky for the astrology context (GET `/astrology/current`, 15s poll) |
| `useLlmModels` | Model lists, priced catalog, provider health (30s poll), selected model |
| `useChatEnvironment` | Inject-context switches, debug mode, chakra data, ledger summary (30s poll) |
| `useToolLogs` | Tool-execution log entries |
| `useCommandChat` | Messages, input, send / cancel / retry / regenerate, operator actions, `vajra:quick-command` listener |
| `useConsoleFeedback` | Auto-scroll and UI sounds for messages and logs |

`waitForChatJob.ts` settles an async chat job: a 1s poll of
`/llm/chat/jobs/{id}` races the chat-progress WebSocket events, with a 300s
timeout; everything is torn down on settle.

## Sections (presentational)

| Component | Renders |
| --- | --- |
| `ChatHeader` | Title and LLM agent connection badge |
| `ChatMessageList` | Bubbles, tool widgets, Retry, `MessageControls`, working indicator, suggestions |
| `MessageControls` | Per-message debug, model re-pick, regenerate, tokens / latency / cost |
| `CommandShortcuts` | Quick-command chips and operator actions |
| `ContextInjectionBar` | Context switches, model picker, provider health, debug toggle |
| `CommandInputBar` | Input with Send / Stop |
| `SystemMonitorsCard`, `LogsCard`, `ZoomModal`, `WorkingsStrip`, `WorkingInstrument` | Earlier extractions |
| `CosmicAlignmentCard` | Earlier extraction, currently not imported anywhere (deletion candidate) |
| `RenderMessageWidgets`, `RichMarkdownRenderer` | Message rendering |

## Pure modules

- `commandCenterTypes.ts` — chat, model, health and log shapes.
- `chatFormatting.ts` — context system message, stutter collapse, cost,
  operator-action summaries.
- `buildModelOptions.tsx` — grouped model Select options.
- `constants.js` — quick commands and operator-action definitions.

## Design system alignment

- **Styling split:** Tailwind for layout, spacing and color utilities; Ant
  Design for interactive widgets (see `docs/frontend-styling-guide.md`).
- **Colors:** saffron primary (`#D97706`), cream text (`#F5F0E1`),
  vajra-purple / cyan / gold accents — see `lib/colors.js`.
- **Icons:** `lucide-react`.
- **JSDoc:** every file begins with a `/** ... */` header comment block.
