/**
 * useCommandChat — the Command Center conversation: input, messages, the
 * async chat job lifecycle (send → POST /llm/chat/async → waitForChatJob),
 * cancel, retry, regenerate, operator quick actions, and the
 * `vajra:quick-command` window event (fired by SakaDawaBanner and others).
 *
 * Handlers are plain functions recreated each render, as they were inline,
 * so each one reads the model, context switches and messages of the render
 * that invoked it. The window listener goes through a ref so it always
 * calls the latest send.
 */
import { useState, useEffect, useRef } from 'react';
import { apiUrl } from '../../utils/api';
import { audioFeedback } from '../../utils/audioFeedback';
import { resolveChatRoute } from '../../utils/chatRoute';
import { getActiveConnectionId } from '../../hooks/useWebSocketStable';
import { createLogger } from '../../utils/logger';
import { buildContextSystemMessage, collapseChatStutter, computeCostUsd, formatOperatorSummary } from './chatFormatting';
import { waitForChatJob } from './waitForChatJob';
import type {
  AddToolLog, AvailableModelMeta, ChatJobResult, ChatMessage, DebugInfo, ModelPricing,
  OperatorAction, ToolCall,
} from './commandCenterTypes';
import type { ChatEnvironment } from './useChatEnvironment';

export const WELCOME_MESSAGE: ChatMessage = {
  role: 'assistant',
  content: '🔮 **Vajra.Stream Command Center Ready**\n\nI am your AI operator. I can assist you with system calibration, crystal programming, automated population blessings, and scalar broadcasts. How shall we direct the intention today?'
};

/** Delay between a vajra:quick-command event filling the input and sending it. */
export const QUICK_COMMAND_SEND_DELAY_MS = 200;

interface CommandChatDeps {
  env: ChatEnvironment;
  astroData: Record<string, unknown> | null;
  selectedModel: string;
  availableModelList: AvailableModelMeta[];
  modelPricing: Record<string, ModelPricing>;
  addToolLog: AddToolLog;
}

interface ChatOptions {
  model?: string;
  astrology?: boolean;
  anatomy?: boolean;
  hardware?: boolean;
  debug?: boolean;
}

export function useCommandChat({ env, astroData, selectedModel, availableModelList, modelPricing, addToolLog }: CommandChatDeps) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatPhase, setChatPhase] = useState('');
  const [debugPayload, setDebugPayload] = useState<DebugInfo | Record<string, unknown> | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);
  const jobIdRef = useRef<string | null>(null);
  const waitRejectRef = useRef<((err: Error) => void) | null>(null);

  const costOf = (modelId: string | null, inputTokens: number | null, outputTokens: number | null) =>
    computeCostUsd(modelPricing, modelId, inputTokens, outputTokens);

  async function callChatAPI(msgs: ChatMessage[], opts: ChatOptions = {}): Promise<ChatJobResult> {
    const {
      model = selectedModel,
      astrology = env.includeAstrology,
      anatomy = env.includeAnatomy,
      hardware = env.includeHardware,
      debug = env.debugMode,
    } = opts;

    const contextSystem = buildContextSystemMessage({
      includeAstrology: env.includeAstrology,
      includeAnatomy: env.includeAnatomy,
      includeHardware: env.includeHardware,
      astroData,
      chakraData: env.chakraData,
      ledgerSummary: env.ledgerSummary,
    });
    const messagesToSend = contextSystem
      ? [{ role: 'system' as const, content: contextSystem }, ...msgs]
      : msgs;

    abortRef.current = new AbortController();
    cancelledRef.current = false;
    jobIdRef.current = null;
    const connectionId = getActiveConnectionId();
    const routed = resolveChatRoute(model, availableModelList);
    const chatLog = createLogger('CommandCenter');
    chatLog.info('chat.send', {
      provider: routed.provider,
      model: routed.model,
      connectionId,
      messages: messagesToSend.length,
      debug,
    });
    if (!connectionId) {
      chatLog.warn('chat.send: no WebSocket connection id — will poll job status');
    }
    const chatResponse = await fetch(apiUrl('/llm/chat/async'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: messagesToSend.map(m => ({ role: m.role, content: m.content })),
        provider: routed.provider,
        model: routed.model,
        include_astrology: astrology,
        astrology_data: astrology ? astroData : null,
        include_anatomy: anatomy,
        include_hardware: hardware,
        debug_mode: debug,
        connection_id: connectionId || undefined,
      }),
      signal: abortRef.current.signal,
    });
    if (!chatResponse.ok) {
      throw new Error(`Chat API error: ${chatResponse.status} ${chatResponse.statusText}`);
    }
    const json = await chatResponse.json();
    const jobId: string = json.job_id;
    jobIdRef.current = jobId;
    createLogger('CommandCenter').info('chat.accepted', { jobId, status: json.status });

    return await waitForChatJob(jobId, { setChatPhase, addToolLog, cancelledRef, waitRejectRef });
  }

  async function handleSendMessage(textToSend?: string) {
    const text = textToSend || input;
    if (!text.trim()) return;

    setInput('');
    setIsLoading(true);
    setChatPhase('sending');
    setLastError(null);
    audioFeedback.playTelemetry();

    const priorMessages = messages;
    const userMsg: ChatMessage = { role: 'user', content: text };
    const newMessages = [...priorMessages, userMsg];
    setMessages(newMessages);
    addToolLog('user', `User requested: "${text}"`);

    try {
      addToolLog('llm', 'Analyzing intent and planning operations...', 'pending');

      const data = await callChatAPI(newMessages);
      if (cancelledRef.current) {
        return;
      }
      const latencyMs = data.latencyMs;
      if (data.debug_info) {
        setDebugPayload(data.debug_info);
      } else {
        setDebugPayload(null);
      }

      if (data.tool_calls && data.tool_calls.length > 0) {
        data.tool_calls.forEach((tc: ToolCall) => {
          if (tc.status === 'success') {
            addToolLog(
              'tool',
              `Executed ${tc.tool_name}(${JSON.stringify(tc.arguments)}) successfully`,
              'success'
            );
          } else {
            addToolLog(
              'tool',
              `Failed executing ${tc.tool_name}: ${tc.error}`,
              'error'
            );
          }
        });
      } else {
        addToolLog('llm', 'Request processed. No mechanical tool calls required.');
      }

      const dbg = data.debug_info || null;
      const modelUsed = dbg?.model || (selectedModel !== 'auto' ? selectedModel : null);
      const inputTokens = dbg?.input_tokens ?? null;
      const outputTokens = dbg?.output_tokens ?? null;
      const replyText = collapseChatStutter((data.response || '').trim())
        || (data.tool_calls && data.tool_calls.length
          ? `The operator ran: ${data.tool_calls.map((t) => t.tool_name).join(', ')}. See the cards below.`
          : '');
      if (!replyText) {
        throw new Error('The model returned an empty reply. Check the console [vajra:CommandCenter] logs.');
      }
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: replyText,
        toolCalls: data.tool_calls,
        debugInfo: dbg,
        reasoningContent: dbg?.reasoning_content || null,
        modelUsed,
        providerUsed: dbg?.provider || dbg?.provider_selected || null,
        inputTokens,
        outputTokens,
        latencyMs,
        costUsd: costOf(modelUsed, inputTokens, outputTokens),
        promptMessages: newMessages,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      const errMsg = error instanceof Error ? error.message : String(error);
      console.error('Chat error:', error);
      addToolLog('system', `Error: ${errMsg}`, 'error');
      setLastError(errMsg);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant' as const,
          content: `⚠️ **Operator Error**: Connection failure or API request blocked.\n\nError details: \`${errMsg}\``,
          isError: true,
          retryInput: text,
        },
      ]);
    } finally {
      setIsLoading(false);
      setChatPhase('');
      abortRef.current = null;
    }
  }

  /** Drop the error bubble at `index` and resend its text. */
  function retryMessage(index: number, text: string) {
    setMessages(prev => prev.filter((_, i) => i !== index));
    handleSendMessage(text);
  }

  function handleCancelGeneration() {
    cancelledRef.current = true;
    const jobId = jobIdRef.current;
    if (jobId) {
      void fetch(apiUrl(`/llm/chat/jobs/${jobId}/cancel`), { method: 'POST' });
    }
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    const rejectWait = waitRejectRef.current;
    if (rejectWait) {
      const err = new Error('cancelled');
      err.name = 'AbortError';
      rejectWait(err);
    }
    setIsLoading(false);
    addToolLog('system', 'Generation cancelled by user.', 'error');
  }

  async function handleRegenerate(index: number, newModel: string | null = null) {
    const target = messages[index];
    if (!target || target.role !== 'assistant' || isLoading) return;
    const promptMessages = Array.isArray(target.promptMessages)
      ? target.promptMessages
      : messages.slice(0, index).filter(m => m.role === 'user' || m.role === 'assistant');
    if (promptMessages.length === 0) return;

    setIsLoading(true);
    audioFeedback.playTelemetry();
    addToolLog('llm', `Regenerating message #${index}${newModel ? ` with ${newModel}` : ''}...`, 'pending');
    try {
      const data = await callChatAPI(promptMessages, newModel ? { model: newModel } : {});
      const dbg = data.debug_info || target.debugInfo || null;
      const modelUsed = dbg?.model || newModel || target.modelUsed || (selectedModel !== 'auto' ? selectedModel : null);
      const inputTokens = dbg?.input_tokens ?? target.inputTokens ?? null;
      const outputTokens = dbg?.output_tokens ?? target.outputTokens ?? null;
      const updated: ChatMessage = {
        ...target,
        content: data.response,
        toolCalls: data.tool_calls ?? target.toolCalls,
        debugInfo: dbg,
        reasoningContent: dbg?.reasoning_content || null,
        modelUsed,
        providerUsed: dbg?.provider || dbg?.provider_selected || target.providerUsed || null,
        inputTokens,
        outputTokens,
        latencyMs: data.latencyMs ?? target.latencyMs ?? null,
        costUsd: costOf(modelUsed, inputTokens, outputTokens),
        isError: false,
        promptMessages,
      };
      setMessages(prev => prev.map((m, i) => (i === index ? updated : m)));
      if (data.debug_info) setDebugPayload(data.debug_info);
      addToolLog('llm', 'Regeneration complete', 'success');
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : String(error);
      console.error('Regenerate error:', error);
      addToolLog('system', `Regenerate error: ${errMsg}`, 'error');
      setLastError(errMsg);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleOperatorAction(action: OperatorAction) {
    if (isLoading) return;
    setIsLoading(true);
    audioFeedback.playTelemetry();
    setMessages(prev => [...prev, { role: 'user' as const, content: `[${action.label}] ${action.prompt}`, action: action.key }]);
    addToolLog('user', `Operator action: ${action.label}`);
    addToolLog('llm', `Calling ${action.endpoint.split('/').pop()}...`, 'pending');
    try {
      const res = await fetch(apiUrl(action.endpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(action.body()),
      });
      if (res.ok) {
        const data = await res.json();
        const summary = formatOperatorSummary(action.key, data);
        setMessages(prev => [...prev, {
          role: 'assistant' as const,
          content: summary,
          action: action.key,
          toolCalls: action.key === 'working'
            ? [{ tool_name: 'run_working', arguments: {}, status: 'success', result: data }]
            : undefined,
        }]);
        addToolLog('llm', `${action.label} complete`, 'success');
      } else {
        setMessages(prev => [...prev, { role: 'assistant' as const, content: 'Operator service unavailable.', action: 'error' }]);
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant' as const, content: 'Unable to reach operator.', action: 'error' }]);
    }
    setIsLoading(false);
  }

  // Ref to hold latest handleSendMessage (avoids stale closure in event listener)
  const handleSendMessageRef = useRef(handleSendMessage);
  handleSendMessageRef.current = handleSendMessage;

  // Listen for vajra:quick-command custom events (fired by SakaDawaBanner, etc.)
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ command?: string }>).detail;
      if (detail?.command) {
        setInput(detail.command);
        setTimeout(() => {
          handleSendMessageRef.current(detail.command);
        }, QUICK_COMMAND_SEND_DELAY_MS);
      }
    };
    window.addEventListener('vajra:quick-command', handler);
    return () => window.removeEventListener('vajra:quick-command', handler);
  }, []);

  return {
    messages,
    input,
    setInput,
    isLoading,
    chatPhase,
    lastError,
    debugPayload,
    setDebugPayload,
    handleSendMessage,
    retryMessage,
    handleCancelGeneration,
    handleRegenerate,
    handleOperatorAction,
  };
}

export type CommandChat = ReturnType<typeof useCommandChat>;
