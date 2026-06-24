/**
 * Shared API configuration — proxy-relative URL strategy (ADR 004).
 *
 * Frontend HTTP traffic rides the reverse-proxy-relative `/api/v1/...`
 * form. In dev, the Vite proxy (`vite.config.ts`) forwards `/api` to
 * `localhost:8008`. In production, a reverse proxy (nginx/Caddy/Cloudflare)
 * routes `/api/*` to the backend. This eliminates hardcoded-port coupling
 * and makes the doubled-prefix bug class structurally impossible
 * (Wave 1 Task 8 / commit `c8aa56e`).
 *
 * `VITE_API_BASE` (build-time env) provides an escape hatch for
 * non-localhost deployments that cannot use a reverse proxy — set
 * `VITE_API_BASE=https://api.example.com` and every `apiUrl('/foo')`
 * call resolves to `https://api.example.com/api/v1/foo`. Defaults to
 * empty string (proxy-relative).
 *
 * WebSocket URLs are unchanged (ADR 004 § WebSocket Strategy).
 */

const DEFAULT_PORT = '8008';

/**
 * Build-time override for the API origin. Empty by default → proxy-relative.
 * Set via `VITE_API_BASE=https://api.example.com` to use an absolute origin.
 */
const API_ORIGIN: string =
  (import.meta.env?.VITE_API_BASE as string | undefined)?.replace(/\/+$/, '') ?? '';

/**
 * Compose a proxy-relative API URL. `path` must begin with `/`
 * (e.g. `apiUrl('/healing/chakra/all')` → `/api/v1/healing/chakra/all`).
 */
export function apiUrl(path: string): string {
  if (path.length > 0 && !path.startsWith('/')) {
    throw new Error(`apiUrl(): path must start with '/', got ${JSON.stringify(path)}`);
  }
  return `${API_ORIGIN}/api/v1${path}`;
}

/**
 * Resolve a WebSocket URL. Unchanged by ADR 004 — left as-is per Task 25
 * guardrail (WS strategy was already in scope elsewhere via
 * useWebSocketStable.ts). This export is kept for legacy consumers.
 */
function resolveWsUrl(): string {
  if (typeof window !== 'undefined' && window.location) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname === '::1' ? '127.0.0.1' : window.location.hostname;
    // Always connect directly to the backend port — the Vite proxy is
    // unreliable for WebSocket upgrades and causes connection failures.
    return `${wsProtocol}//${hostname}:${DEFAULT_PORT}/ws`;
  }
  return `ws://127.0.0.1:${DEFAULT_PORT}/ws`;
}

/**
 * @deprecated Use `apiUrl('/foo')` instead. Kept as a backward-compatible
 *   alias ending in `/api/v1` so legacy call sites that concatenated the
 *   API_BASE export with a path continue to resolve while they are
 *   migrated. New code MUST NOT use this.
 */
export const API_BASE: string = apiUrl('');

export const WS_URL: string = resolveWsUrl();
export const BACKEND_PORT: string = DEFAULT_PORT;

/**
 * Resolve the backend HTTP base URL (e.g. `http://localhost:8008`).
 * Mirrors the WS_URL logic — always connects directly to the backend port,
 * bypassing the Vite proxy. Used for the `/ready` readiness check in
 * useWebSocketStable and any other direct-to-backend HTTP call.
 */
function resolveBackendUrl(): string {
  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    const hostname = window.location.hostname === '::1' ? '127.0.0.1' : window.location.hostname;
    return `${protocol}//${hostname}:${DEFAULT_PORT}`;
  }
  return `http://127.0.0.1:${DEFAULT_PORT}`;
}

export const BACKEND_URL: string = resolveBackendUrl();
