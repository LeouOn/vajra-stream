/**
 * useConsoleFeedback — keeps the chat and the tool log scrolled to their
 * newest entry and plays the matching UI sound when either grows (assistant
 * reply vs user turn; tool success / error / other).
 */
import { useEffect, useRef } from 'react';
import { audioFeedback } from '../../utils/audioFeedback';
import type { ChatMessage, ToolLogEntry } from './commandCenterTypes';

export function useConsoleFeedback(messages: ChatMessage[], toolLogs: ToolLogEntry[]) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of messages and logs
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [toolLogs]);

  // Play sound when messages update
  useEffect(() => {
    if (messages.length > 1) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === 'assistant') {
        audioFeedback.playTabChange();
      } else {
        audioFeedback.playClick();
      }
    }
  }, [messages]);

  // Play sound when tool execution logs update
  useEffect(() => {
    if (toolLogs.length > 1) {
      const lastLog = toolLogs[toolLogs.length - 1];
      if (lastLog.status === 'success') {
        audioFeedback.playSuccess();
      } else if (lastLog.status === 'error') {
        audioFeedback.playError();
      } else {
        audioFeedback.playTick();
      }
    }
  }, [toolLogs]);

  return { messagesEndRef, logEndRef };
}
