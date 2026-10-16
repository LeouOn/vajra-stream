/**
 * waitForChatJob — settle an async chat job (POST /llm/chat/async → job id).
 *
 * Two paths race, and whichever reports a terminal status first wins:
 *   - a 1s poll of GET /llm/chat/jobs/{jobId} (also surfaces `phase`), and
 *   - chat-progress events pushed over the WebSocket (chat_tool_start /
 *     chat_tool_error log lines; chat_complete / chat_error / chat_cancelled).
 * A 300s timeout rejects with the last polled status. On settle, the poll,
 * the timer and the WS subscription are all torn down.
 *
 * `waitRejectRef` exposes the pending reject so a user cancel can settle the
 * wait immediately; `cancelledRef` mutes WS events once cancelled.
 */
import type { MutableRefObject } from 'react';
import { apiUrl } from '../../utils/api';
import { subscribe } from '../../hooks/chatProgress';
import { createLogger } from '../../utils/logger';
import type { AddToolLog, ChatJobResult, DebugInfo, ToolCall } from './commandCenterTypes';

export const CHAT_JOB_POLL_MS = 1000;
export const CHAT_JOB_TIMEOUT_MS = 300000;

export interface WaitForChatJobOptions {
  setChatPhase: (phase: string) => void;
  addToolLog: AddToolLog;
  cancelledRef: MutableRefObject<boolean>;
  waitRejectRef: MutableRefObject<((err: Error) => void) | null>;
}

export function waitForChatJob(
  jobId: string,
  { setChatPhase, addToolLog, cancelledRef, waitRejectRef }: WaitForChatJobOptions,
): Promise<ChatJobResult> {
  const start = Date.now();
  const chatLog = createLogger('CommandCenter');
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      clearInterval(poller);
      unsub();
      waitRejectRef.current = null;
      fn();
    };
    const lastPoll = { status: 'pending', phase: '' };
    const applyTerminal = (status: string, payload: Record<string, unknown>) => {
      if (status === 'completed') {
        const debugInfo = payload.debug_info;
        chatLog.info('chat.complete', {
          jobId,
          responseLen: typeof payload.response === 'string' ? payload.response.length : 0,
          tools: Array.isArray(payload.tool_calls) ? payload.tool_calls.length : 0,
          debug: debugInfo,
        });
        finish(() => resolve({
          response: typeof payload.response === 'string' ? payload.response : '',
          tool_calls: Array.isArray(payload.tool_calls) ? payload.tool_calls as ToolCall[] : undefined,
          debug_info: debugInfo && typeof debugInfo === 'object' ? debugInfo as DebugInfo : undefined,
          latencyMs: Date.now() - start,
        }));
        return true;
      }
      if (status === 'error') {
        const errText = typeof payload.error === 'string' ? payload.error : 'Chat job failed';
        chatLog.error('chat.error', { jobId, error: errText });
        finish(() => reject(new Error(errText)));
        return true;
      }
      if (status === 'cancelled') {
        finish(() => {
          const err = new Error('cancelled');
          err.name = 'AbortError';
          reject(err);
        });
        return true;
      }
      return false;
    };
    const timer = setTimeout(() => {
      finish(() => reject(new Error(
        `Chat job timed out after 300s (last status: ${lastPoll.status}${lastPoll.phase ? `, ${lastPoll.phase}` : ''}). The model or a tool never returned.`,
      )));
    }, CHAT_JOB_TIMEOUT_MS);
    waitRejectRef.current = (err: Error) => {
      finish(() => reject(err));
    };
    const pollOnce = () => {
      void (async () => {
        try {
          const res = await fetch(apiUrl(`/llm/chat/jobs/${jobId}`));
          if (!res.ok) return;
          const job = await res.json() as Record<string, unknown>;
          lastPoll.status = String(job.status || 'unknown');
          lastPoll.phase = typeof job.phase === 'string' ? job.phase : '';
          if (lastPoll.phase) setChatPhase(lastPoll.phase);
          chatLog.info('chat.poll', { jobId, status: lastPoll.status, phase: lastPoll.phase });
          applyTerminal(String(job.status || ''), job);
        } catch (err) {
          chatLog.warn('chat.poll failed', err);
        }
      })();
    };
    pollOnce();
    const poller = setInterval(pollOnce, CHAT_JOB_POLL_MS);
    const unsub = subscribe((jid, evt) => {
      if (jid !== jobId) return;
      if (cancelledRef.current) return;
      chatLog.debug('chat.ws', { jobId, type: evt.type, tool: evt.tool });
      if (evt.type === 'chat_tool_start' && typeof evt.tool === 'string') {
        addToolLog('tool', `Calling ${evt.tool}...`, 'pending');
        return;
      }
      if (evt.type === 'chat_tool_error' && typeof evt.tool === 'string') {
        addToolLog('tool', `Tool ${evt.tool} failed: ${String(evt.error || '')}`, 'error');
        return;
      }
      if (evt.type === 'chat_complete') {
        applyTerminal('completed', evt);
      } else if (evt.type === 'chat_error') {
        applyTerminal('error', evt);
      } else if (evt.type === 'chat_cancelled') {
        applyTerminal('cancelled', evt);
      }
    });
  });
}
