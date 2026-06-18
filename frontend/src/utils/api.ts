/**
 * Shared API configuration.
 * Uses window.location.origin so the app works on any port/domain,
 * falling back to localhost:8008 only in non-browser environments.
 */

const DEFAULT_PORT = '8008';

function resolveApiBase(): string {
  if (typeof window !== 'undefined' && window.location) {
    const { protocol, hostname } = window.location;
    const resolvedHostname = hostname === '::1' || hostname === 'localhost' ? '127.0.0.1' : hostname;
    return `${protocol}//${resolvedHostname}:${DEFAULT_PORT}/api/v1`;
  }
  return `http://127.0.0.1:${DEFAULT_PORT}/api/v1`;
}

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

export const API_BASE: string = resolveApiBase();
export const WS_URL: string = resolveWsUrl();
export const BACKEND_PORT: string = DEFAULT_PORT;
