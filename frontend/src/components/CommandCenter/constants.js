/**
 * CommandCenter constants — quick-command chips + operator action definitions.
 *
 * Extracted from `components/UI/CommandCenter.jsx` (lines 632-674) as part of
 * the CommandCenter decomposition (Task 3.3).
 *
 * - `quickCommands`: pure static data (label/text pairs for the suggestion
 *   chip row). Imported directly by CommandCenter.
 * - `createOperatorActions(deps)`: factory returning the operator-action
 *   definitions. A factory is required rather than a plain export because the
 *   `insight` action's `body()` closure captures live CommandCenter props
 *   (`frequency`, `isPlaying`, `sessions`, `crystalStatus`, `scalarStatus`).
 *   Passing these as `deps` preserves the original closure semantics exactly
 *   while keeping the data definition out of the component body.
 *
 * @see components/UI/CommandCenter.jsx for the original inline definitions.
 */
/**
 * Quick-command suggestion chips rendered above the input bar.
 * @type {Array<{label: string, text: string}>}
 */
export const quickCommands = [
  { label: 'Begin a working', text: 'Begin a working: may all beings be free from suffering' },
  { label: 'Start automation', text: 'start automation' },
  { label: 'Stop automation', text: 'stop automation' },
  { label: 'List populations', text: 'list populations' },
  { label: 'Start RNG session', text: 'start rng session' },
  { label: 'Get statistics', text: 'get statistics' },
  { label: 'Dharma Wisdom', text: 'tell me a dharma tale' }
];

/**
 * Build the operator-actions array, injecting the live CommandCenter props the
 * `insight` action needs into its `body()` closure.
 *
 * @param {Object}  deps
 * @param {number}  deps.frequency     - current audio carrier frequency.
 * @param {boolean} deps.isPlaying     - whether the carrier is active.
 * @param {Object}  deps.sessions      - active blessing-rotation sessions map.
 * @param {Object}  [deps.crystalStatus] - crystal broadcaster status object.
 * @param {Object}  [deps.scalarStatus]  - scalar array status object.
 * @returns {Array} operator action definitions (key/label/icon/prompt/endpoint/body).
 */
export function createOperatorActions({ frequency, isPlaying, sessions, crystalStatus, scalarStatus, currentInput }) {
  const typed = typeof currentInput === 'string' ? currentInput.trim() : '';
  const intention = typed || 'help my friend with chronic back pain';
  const rateQuery = typed || 'emotional healing after loss';
  return [
    {
      key: 'working',
      label: 'Begin working',
      icon: '✦',
      prompt: intention,
      endpoint: `/api/v1/operator/working`,
      body: () => ({ intention, target: 'all beings', broadcast: true, duration_minutes: 5 }),
    },
    {
      key: 'analyze',
      label: 'Analyze intention',
      icon: '🎯',
      prompt: intention,
      endpoint: `/api/v1/operator/analyze`,
      body: () => ({ intention }),
    },
    {
      key: 'rates',
      label: 'Suggest rates',
      icon: '📊',
      prompt: rateQuery,
      endpoint: `/api/v1/operator/suggest-rates`,
      body: () => ({ intention_or_condition: rateQuery, count: 5 }),
    },
    {
      key: 'insight',
      label: 'Session insight',
      icon: '👁',
      prompt: 'what do my current readings suggest?',
      endpoint: `/api/v1/operator/insights`,
      body: () => ({
        session_context: {
          currentFrequency: frequency,
          isPlaying,
          activeSessions: Object.values(sessions || {}).filter(s => s.status === 'running').length,
          crystalActive: crystalStatus?.active || false,
          scalarRate: scalarStatus?.rate || null,
        },
      }),
    },
  ];
}
