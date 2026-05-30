/**
 * useWebSocket — thin re-export of useWebSocketStable.
 *
 * For backward compatibility. All components should eventually import
 * directly from useWebSocketStable. App.jsx already does:
 *   import { useWebSocketStable as useWebSocket } from './hooks/useWebSocketStable'
 */

export { useWebSocketStable as useWebSocket } from './useWebSocketStable';
