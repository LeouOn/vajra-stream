/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Build-time API origin override (ADR 004). Unset in dev — the Vite proxy handles /api. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
