/**
 * Shared API configuration.
 * Uses window.location.origin so the app works on any port/domain,
 * falling back to localhost:8008 only in non-browser environments.
 */

const DEFAULT_PORT = '8008';

function resolveApiBase() {
  if (typeof window !== 'undefined' && window.location) {
    const { protocol, hostname, port } = window.location;
    // If served from the backend port or a custom port, use that origin
    const origin = port ? `${protocol}//${hostname}:${port}` : `${protocol}//${hostname}`;
    return `${origin}/api/v1`;
  }
  // Fallback for SSR / non-browser contexts
  return `http://localhost:${DEFAULT_PORT}/api/v1`;
}

function resolveWsUrl() {
  if (typeof window !== 'undefined' && window.location) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname === '::1' ? '127.0.0.1' : window.location.hostname;
    const port = window.location.port || DEFAULT_PORT;
    return `${wsProtocol}//${hostname}:${port}/ws`;
  }
  return `ws://127.0.0.1:${DEFAULT_PORT}/ws`;
}

export const API_BASE = resolveApiBase();
export const WS_URL = resolveWsUrl();
export const BACKEND_PORT = DEFAULT_PORT;
