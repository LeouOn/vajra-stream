/**
 * Command Center — primary operator console for Vajra.Stream.
 *
 * Central hub for issuing text commands to the unified orchestrator.
 * Features a terminal-style input, live WebSocket job progress, operations-
 * ledger context for the LLM, and quick-action buttons for common radionics
 * and blessing operations.
 *
 * Composition root: the pieces live in components/CommandCenter/ —
 * hooks for the sky context (useAstroContext), model picker (useLlmModels),
 * context switches (useChatEnvironment), tool log (useToolLogs), the chat
 * job lifecycle (useCommandChat) and scroll/sound feedback
 * (useConsoleFeedback); sections for the header, message list, shortcuts,
 * env bar and input.
 *
 * @component
 */
import React, { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { Card } from 'antd';
import type { CrystalStatus, SakaDawaResult, ScalarStatus } from '../../types';
import SakaDawaBanner from './SakaDawaBanner';
import PageHeader from './PageHeader';
import WorldEmanation from '../3D/WorldEmanation';
import WorkingsStrip from '../CommandCenter/WorkingsStrip';
import SystemMonitorsCard from '../CommandCenter/SystemMonitorsCard';
import LogsCard from '../CommandCenter/LogsCard';
import ZoomModal from '../CommandCenter/ZoomModal';
import ChatHeader from '../CommandCenter/ChatHeader';
import ChatMessageList from '../CommandCenter/ChatMessageList';
import CommandShortcuts from '../CommandCenter/CommandShortcuts';
import ContextInjectionBar from '../CommandCenter/ContextInjectionBar';
import CommandInputBar from '../CommandCenter/CommandInputBar';
import type { ZoomItem } from '../CommandCenter/RenderMessageWidgets';
import type { LogTab } from '../CommandCenter/commandCenterTypes';
import { createOperatorActions } from '../CommandCenter/constants';
import { buildModelOptions } from '../CommandCenter/buildModelOptions';
import { useAstroContext } from '../CommandCenter/useAstroContext';
import { useLlmModels } from '../CommandCenter/useLlmModels';
import { useChatEnvironment } from '../CommandCenter/useChatEnvironment';
import { useToolLogs } from '../CommandCenter/useToolLogs';
import { useCommandChat } from '../CommandCenter/useCommandChat';
import { useConsoleFeedback } from '../CommandCenter/useConsoleFeedback';

interface CommandCenterProps {
  isConnected: boolean;
  isPlaying: boolean;
  frequency: number;
  crystalStatus: CrystalStatus;
  scalarStatus: ScalarStatus;
  sessions: Record<string, unknown>;
  sakaDawa: SakaDawaResult | null;
}

export default function CommandCenter({
  isConnected,
  isPlaying,
  frequency,
  crystalStatus,
  scalarStatus,
  sessions,
  sakaDawa
}: CommandCenterProps) {
  const [activeZoomItem, setActiveZoomItem] = useState<ZoomItem | null>(null);
  const [activeLogTab, setActiveLogTab] = useState<LogTab>('tools');

  // Hook order keeps the original effect order: sky poll, model lists,
  // catalog, provider health, chakras, ledger, quick-command listener,
  // then scroll and sound feedback.
  const astroData = useAstroContext();
  const llm = useLlmModels();
  const env = useChatEnvironment();
  const { toolLogs, addToolLog, clearToolLogs } = useToolLogs();
  const chat = useCommandChat({
    env,
    astroData,
    selectedModel: llm.selectedModel,
    availableModelList: llm.availableModelList,
    modelPricing: llm.modelPricing,
    addToolLog,
  });
  const { messagesEndRef, logEndRef } = useConsoleFeedback(chat.messages, toolLogs);

  const modelOptions = buildModelOptions(llm.availableModelList, llm.availableModels);
  const operatorActions = createOperatorActions({ frequency, isPlaying, sessions, crystalStatus, scalarStatus, currentInput: chat.input });

  return (
    <div className="h-full flex flex-col gap-4 p-4 md:p-6 overflow-hidden">
      <PageHeader
        icon={<Sparkles className="w-7 h-7 text-purple-400" />}
        title="Command Center"
        subtitle="Issue intentions, monitor broadcasts, and orchestrate the unified system."
      />

      {/* Saka Dawa Banner */}
      <SakaDawaBanner sakaDawa={sakaDawa} />
      <WorkingsStrip />

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">

        {/* Left Column: Chat and Commands */}
        <Card className="flex-1 flex flex-col min-h-0 bg-gray-900/80 border-purple-500/20 overflow-hidden" styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', flex: 1 } }}>
          <ChatHeader isConnected={isConnected} />
          <ChatMessageList
            messages={chat.messages}
            isLoading={chat.isLoading}
            chatPhase={chat.chatPhase}
            modelOptions={modelOptions}
            providerHealth={llm.providerHealth}
            messagesEndRef={messagesEndRef}
            onZoomItemClick={setActiveZoomItem}
            onRetry={chat.retryMessage}
            onRegenerate={(index, model) => chat.handleRegenerate(index, model)}
            onSuggest={chat.setInput}
          />
          <CommandShortcuts
            isLoading={chat.isLoading}
            operatorActions={operatorActions}
            onQuickCommand={(text) => chat.handleSendMessage(text)}
            onOperatorAction={(action) => chat.handleOperatorAction(action)}
          />
          {/* LLM Environmental Context Injection Panel */}
          <ContextInjectionBar
            env={env}
            selectedModel={llm.selectedModel}
            onSelectModel={llm.setSelectedModel}
            modelOptions={modelOptions}
            providerHealth={llm.providerHealth}
          />
          <CommandInputBar
            input={chat.input}
            isLoading={chat.isLoading}
            onInputChange={chat.setInput}
            onSubmit={() => chat.handleSendMessage()}
            onCancel={chat.handleCancelGeneration}
          />
        </Card>

        {/* Right Column: Status & Tool execution logs */}
        <div className="w-full lg:w-80 flex flex-col gap-6 h-full min-h-0 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">

          {/* World Emanation Compact Live 3D Globe */}
          <WorldEmanation variant="compact" />

          {/* Status Monitors Card */}
          <SystemMonitorsCard
            isPlaying={isPlaying}
            scalarStatus={scalarStatus}
            sessions={sessions}
          />

          {/* Tool Execution / LLM Debug Logs (Terminal UI) */}
          <LogsCard
            activeLogTab={activeLogTab}
            toolLogs={toolLogs}
            debugPayload={chat.debugPayload}
            logEndRef={logEndRef}
            onTabChange={(key) => setActiveLogTab(key === 'debug' ? 'debug' : 'tools')}
            onClearLogs={clearToolLogs}
            onResetDebug={() => chat.setDebugPayload(null)}
          />

        </div>
      </div>

      {/* Zoom Modal */}
      <ZoomModal activeZoomItem={activeZoomItem} onClose={() => setActiveZoomItem(null)} />

    </div>
  );
}
