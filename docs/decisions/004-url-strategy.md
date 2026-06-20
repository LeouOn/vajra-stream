# ADR 004: Proxy-relative frontend URL strategy

- **Status:** Accepted
- **Date:** 2026-06-18
- **Blocks:** Task 25 (URL standardization migration)
- **Depends on:** Wave 0 Task 2 (preflight evidence), Wave 1 Task 8 (commit `c8aa56e`)
- **Supersedes:** The absolute `${API_BASE}` pattern in `frontend/src/utils/api.ts:13`

## Context

Two URL strategies coexist in the frontend today (per evaluation Issue 2.2):

1. **Absolute** — `frontend/src/utils/api.ts:13` exports `API_BASE` as
   `${protocol}//${hostname}:8008/api/v1`. Every `${API_BASE}/foo` call hits
   backend port `:8008` directly, bypassing the dev proxy and depending on
   per-origin CORS in production. Approximately **30 files** use this form.
2. **Proxy-relative** — a minority (~10 files) already call `/api/v1/...`
   directly and ride the Vite dev proxy. `DharmaTales.jsx:14` even defines a
   local `const API_BASE = '/api/v1'`, proving the pattern works.

Wave 0 Task 2 (`.omo/evidence/wave0-task2-url-strategy.md`) performed a
read-only preflight and confirmed the migration is safe:

- **0 matches** for `VITE_API_BASE` anywhere in `frontend/`.
- **0 matches** for `import.meta.env` anywhere in `frontend/`.
- **No `.env*` files** under `frontend/` (no `.env.production`,
  `.env.local`, or `.env.development` exist).
- The Vite proxy (`vite.config.ts:10-18`) forwards `/api` and `/ws` to
  `localhost:8008` and is already functional.

There is **no env-var override mechanism to break** — the migration is a pure
source-code change with no operator-facing surface area.

The doubled-prefix bug class is real: Wave 1 Task 8 (commit `c8aa56e`)
fixed `AstrologyExtractionPanel.jsx:390`, where `${API_BASE}/api/v1/...`
resolved to `/api/v1/api/v1/...` and returned 404. The bug was caused by
mixing an `API_BASE` already ending in `/api/v1` with manual concatenation.
A single proxy-relative helper eliminates this class of mistake.

Metis EC3 edge case: a production frontend build served without a backend
on the same origin must still resolve gracefully — proxy-relative URLs
return a clean 502/404 from the reverse proxy rather than failing DNS/TLS
on a hardcoded `:8008`.

## Decision

Standardize on **proxy-relative URLs** of the form `/api/v1/...`.

Rationale:

1. The Vite proxy is already wired (`vite.config.ts:10-18`) and proven
   working by `DharmaTales.jsx`.
2. Removes the hardcoded `127.0.0.1:8008` deployment hazard baked into
   `resolveApiBase()`.
3. Eliminates the doubled-prefix bug class at its root (Task 8, `c8aa56e`).
4. Matches the existing WebSocket strategy, so HTTP and WS agree.

## Migration Plan (for Task 25)

1. **`frontend/src/utils/api.ts`** — replace the absolute `API_BASE` form
   with a helper:

   ```ts
   const baseUrl = import.meta.env.VITE_API_BASE || '';
   export const apiUrl = (p: string) => `${baseUrl}/api/v1${p}`;
   ```

   `VITE_API_BASE` is an empty string by default (proxy-relative). For
   non-localhost deployments without a reverse proxy, set
   `VITE_API_BASE=https://api.example.com` at build time.
2. **Convert call sites** — replace `${API_BASE}/foo` with `apiUrl('/foo')`
   across the ~30 files currently importing `API_BASE`.
3. **Outliers** — `AstrologyExtractionPanel.jsx` (already fixed by `c8aa56e`)
   and `DharmaTales.jsx` (already proxy-relative) need no further change.
4. **README** — document the `VITE_API_BASE` env var and the reverse-proxy
   deployment pattern.
5. **No changes to `scripts/`** (Guardrail G1).

## WebSocket Strategy

**Unchanged.** WebSocket URLs are already proxy-relative at
`frontend/src/hooks/useWebSocketStable.ts:85-88`:

```ts
const getDefaultWsUrl = (): string => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProtocol}//${window.location.host}/ws`;
};
```

The Vite proxy forwards `/ws` → `ws://localhost:8008`. Task 25 touches HTTP
URLs only.

## Consequences

- **Positive:** Single URL strategy; no hardcoded port; no CORS in
  same-origin deployments; bug class from Task 8 structurally impossible.
- **Positive:** Zero env-var migration risk — nothing exists to break
  (Wave 0 Task 2 evidence).
- **Negative:** Production deployment requires a reverse proxy (nginx,
  Caddy, Cloudflare) routing `/api/*` → backend. This is the standard
  pattern; the absolute-URL form merely hid the requirement.
- **Negative:** Operators who currently rely on `:8008` being directly
  reachable must add a reverse-proxy rule. No such operators are known.
- **Migration cost:** ~30 files, mechanical refactor in Task 25.
