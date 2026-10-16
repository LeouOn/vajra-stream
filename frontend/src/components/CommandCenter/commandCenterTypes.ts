/**
 * commandCenterTypes.ts — shapes shared by the Command Center's chat,
 * model picker, context injection and log panes.
 */
import type { ToolCall as WidgetToolCall } from './RenderMessageWidgets';

/**
 * A single tool-call result from the chat API. `result` is typed as the
 * superset the widget renderer reads (see RenderMessageWidgets.ToolCall).
 */
export interface ToolCall extends WidgetToolCall {
  arguments: Record<string, unknown>;
  error?: string | null;
}

/** One row in the tool-execution log (LogsCard). */
export interface ToolLogEntry {
  timestamp: string;
  type: string;
  message: string;
  status?: string;
}

export type AddToolLog = (type: string, message: string, status?: string) => void;

export type LogTab = 'tools' | 'debug';

/** Per-message debug telemetry returned by /api/v1/llm/chat (debug_mode=true). */
export interface DebugInfo {
  model?: string;
  provider?: string;
  provider_selected?: string;
  model_selected?: string;
  input_tokens?: number;
  output_tokens?: number;
  finish_reason?: string;
  reasoning_content?: string;
  reasoning_tokens?: number;
  system_prompt?: string;
  messages_sent?: Array<{ role: string; content: string }>;
  tools_available?: string[];
  timestamp?: number;
  [key: string]: unknown;
}

/** A chat message (user or assistant) with optional debug telemetry. */
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  action?: string;
  toolCalls?: ToolCall[];
  debugInfo?: DebugInfo | null;
  reasoningContent?: string | null;
  modelUsed?: string | null;
  providerUsed?: string | null;
  inputTokens?: number | null;
  outputTokens?: number | null;
  latencyMs?: number | null;
  costUsd?: number | null;
  promptMessages?: ChatMessage[];
  isError?: boolean;
  retryInput?: string;
}

/** Settled chat job, as returned by waitForChatJob. */
export interface ChatJobResult {
  response: string;
  tool_calls?: ToolCall[];
  debug_info?: DebugInfo;
  latencyMs: number;
}

/** Rich model metadata from GET /api/v1/llm/models/available. */
export interface AvailableModelMeta {
  id: string;
  name: string;
  provider: string;
  context_length: number | null;
  input_per_m: number;
  output_per_m: number;
  is_free: boolean;
  featured: boolean;
  description: string;
  source: string;
}

/** Response shape of GET /api/v1/llm/models/available. */
export interface AvailableModelsResponse {
  status: string;
  count: number;
  fetched_at: number | null;
  source: string;
  models: AvailableModelMeta[];
}

/** Per-model pricing entry for client-side cost computation. */
export interface ModelPricing {
  input_per_m: number;
  output_per_m: number;
  is_free: boolean;
}

/** Provider health entry from GET /api/v1/llm/providers/health. */
export interface ProviderHealthEntry {
  provider: string;
  healthy: boolean;
  latency_ms: number | null;
  error: string | null;
  checked_at: number;
}

/** Response shape of GET /api/v1/llm/providers/health. */
export interface ProviderHealthResponse {
  providers: ProviderHealthEntry[];
  healthy_count: number;
  total_count: number;
  message?: string;
}

/** Chakra entry from GET /api/v1/healing/chakra/all. */
export interface ChakraEntry {
  name?: string;
  sanskrit?: string;
  english?: string;
  element?: string;
  color?: string;
  frequency?: number | number[];
  qualities?: string[];
  location?: string;
  [key: string]: unknown;
}

/** Local / API / LM Studio model ids from GET /api/v1/llm/models. */
export interface BasicModelLists {
  local: string[];
  api: string[];
  lm_studio: string[];
}

/** Basic models endpoint response (GET /api/v1/llm/models). */
export interface BasicModelsResponse {
  status: string;
  available: BasicModelLists;
  default_model: string;
  lm_studio_connected: boolean;
}

/** An operator quick action (see constants.createOperatorActions). */
export interface OperatorAction {
  key: string;
  label: string;
  icon: string;
  prompt: string;
  endpoint: string;
  body: () => Record<string, unknown>;
}
