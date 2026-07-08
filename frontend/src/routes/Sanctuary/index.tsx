/**
 * SanctuaryPage — the /sanctuary route.
 *
 * A calm, dark, spacious healing-dialogue container. Unlike the busy
 * CommandCenter, this page holds one conversation at a time across the
 * five-phase arc (Arrival → Seeing → Meeting → Release → Dedication),
 * with a thin phase indicator, a quiet message column, and a single
 * input at the bottom.
 *
 * Data flow (all under /api/v1/healing/sessions):
 *   - GET  /sessions              → list recent (for the drawer)
 *   - POST /sessions              → create a new session
 *   - GET  /sessions/{id}         → load full transcript
 *   - POST /sessions/{id}/messages → send a turn → {content, phase, phase_hint}
 *   - POST /sessions/{id}/advance → force-advance one phase
 *
 * On mount we fetch recent sessions; if none exist we auto-create one.
 * The LLM may auto-advance the phase server-side and return a `phase_hint`
 * — we surface that as a gentle inline acknowledgment, and only offer a
 * manual "Advance" control when the hint names a phase beyond the current
 * one (so we never double-advance).
 *
 * @component
 * @route /sanctuary
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Input, Spin, Typography } from 'antd';
import type { InputRef } from 'antd';
import { Send, Plus, Archive } from 'lucide-react';
import { apiUrl } from '../../utils/api';
import { createLogger } from '../../utils/logger';
import { useUIStore } from '../../stores/uiStore';
import SessionList from './SessionList';
import type { SessionListItem } from './SessionList';

const log = createLogger('Sanctuary');

const { Text } = Typography;

/** The five-phase arc (terminal "completed" is handled separately). */
type PhaseKey = 'arrival' | 'seeing' | 'meeting' | 'release' | 'dedication';
type Phase = PhaseKey | 'completed';

interface PhaseMeta {
  key: PhaseKey;
  label: string;
  role: string;
}

/** A single transcript entry — used in the messages list and POST payloads. */
interface HealingMessage {
  role: 'user' | 'assistant';
  content: string;
}

/** Shape returned by POST /sessions. */
interface HealingSessionCreate {
  session_id: string;
  phase?: Phase;
  started_at?: string;
  [key: string]: unknown;
}

/** Shape returned by POST /sessions/{id}/messages — server may auto-advance. */
interface HealingMessageResponse {
  session_id?: string;
  phase?: Phase;
  phase_hint?: string | null;
  content?: string;
  [key: string]: unknown;
}

/** Shape returned by POST /sessions/{id}/advance. */
interface HealingAdvanceResponse {
  session_id?: string;
  phase?: Phase;
  [key: string]: unknown;
}

/** A single entry in `message_history` returned by GET /sessions/{id}. */
interface SessionHistoryEntry {
  role?: unknown;
  content?: unknown;
}

/** Full session detail returned by GET /sessions/{id}. */
interface HealingSessionDetail {
  session_id: string;
  phase?: Phase;
  started_at?: string;
  ended_at?: string | null;
  phases_completed?: PhaseKey[];
  summary?: string | null;
  dedication_text?: string | null;
  message_history?: SessionHistoryEntry[];
  [key: string]: unknown;
}

/** Local copy we use when seeding a freshly created session into the drawer. */
interface LocalSessionSeed {
  session_id: string;
  started_at?: string;
  phases_completed: PhaseKey[];
  summary: string | null;
  ended_at: null;
}

/** A sealed completion bundle (summary + dedication). */
interface CompletedSealPayload {
  summary: string | null;
  dedication: string | null;
}

const PHASES: PhaseMeta[] = [
  { key: 'arrival', label: 'Arrival', role: 'Witness' },
  { key: 'seeing', label: 'Seeing', role: 'Oracle' },
  { key: 'meeting', label: 'Meeting', role: 'Guide' },
  { key: 'release', label: 'Release', role: 'Practitioner' },
  { key: 'dedication', label: 'Dedication', role: 'Officiant' },
];

const PHASE_LABEL: Record<string, string> = Object.fromEntries(
  PHASES.map((p) => [p.key, p.label]),
);
PHASE_LABEL.completed = 'Sealed';

/** Soft copy shown beneath each phase role — sets the tone without clutter. */
const PHASE_INVOCATION: Record<PhaseKey, string> = {
  arrival: 'A space to land. Nothing to fix.',
  seeing: 'The sky above and the body below.',
  meeting: 'Staying present with what is here.',
  release: 'One practice for what is ready to move.',
  dedication: 'Offering the merit outward.',
};

function phaseIndex(key: Phase | null): number | null {
  if (key == null) return null;
  const idx = PHASES.findIndex((p) => p.key === key);
  return idx === -1 ? null : idx;
}

function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/**
 * SanctuaryPage
 */
export default function SanctuaryPage(): React.ReactElement {
  const addToast = useUIStore((s) => s.addToast);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<HealingMessage[]>([]);
  const [currentPhase, setCurrentPhase] = useState<Phase | null>(null);
  const [input, setInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isInitializing, setIsInitializing] = useState<boolean>(true);
  const [phaseHint, setPhaseHint] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [completedSeal, setCompletedSeal] = useState<CompletedSealPayload | null>(null);
  const [wavered, setWavered] = useState<boolean>(false); // gentle error flag

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<InputRef | null>(null);

  // -------------------------------------------------------------------------
  // API helpers (soft failures — the container "wavers" rather than throws).
  // -------------------------------------------------------------------------

  const fetchSessions = useCallback(async (): Promise<SessionListItem[]> => {
    try {
      const res = await fetch(apiUrl('/healing/sessions?limit=30'));
      if (!res.ok) throw new Error(`list ${res.status}`);
      const data = await res.json();
      const list = Array.isArray(data?.sessions) ? (data.sessions as SessionListItem[]) : [];
      return list;
    } catch (err) {
      log.warn('Sanctuary: list sessions wavered', err);
      addToast({
        type: 'error',
        title: 'Could not load sessions',
        message: errMessage(err),
        duration: 5,
      });
      return [];
    }
  }, [addToast]);

  const createSession = useCallback(async (): Promise<HealingSessionCreate> => {
    const res = await fetch(apiUrl('/healing/sessions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error(`create ${res.status}`);
    return res.json();
  }, []);

  const loadSession = useCallback(async (id: string): Promise<HealingSessionDetail> => {
    const res = await fetch(apiUrl(`/healing/sessions/${id}`));
    if (!res.ok) throw new Error(`get ${res.status}`);
    return res.json();
  }, []);

  // -------------------------------------------------------------------------
  // Boot — fetch recent sessions for the drawer. Do NOT auto-create.
  // The user triggers session creation by clicking "Begin".
  // -------------------------------------------------------------------------

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setIsInitializing(true);
      try {
        const recent = await fetchSessions();
        if (cancelled) return;
        setSessions(recent);
        // If there are past sessions, load the most recent one so the user
        // can continue where they left off. But if none exist, leave
        // sessionId null — the landing screen will show a "Begin" button.
        if (recent.length > 0 && recent[0]?.session_id) {
          try {
            const full = await loadSession(recent[0].session_id);
            if (cancelled) return;
            hydrateFromSession(full);
          } catch (err) {
            log.warn('Sanctuary: load latest wavered', err);
            addToast({
              type: 'error',
              title: 'Could not load recent session',
              message: errMessage(err),
              duration: 5,
            });
          }
        }
      } catch (err) {
        log.error('Sanctuary: initialization failed', err);
        addToast({
          type: 'error',
          title: 'Could not initialize Sanctuary',
          message: errMessage(err),
          duration: 5,
        });
        if (!cancelled) setWavered(true);
      } finally {
        if (!cancelled) setIsInitializing(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Populate state from a GET /sessions/{id} response. */
  const hydrateFromSession = useCallback((full: HealingSessionDetail): void => {
    const history = Array.isArray(full?.message_history) ? full.message_history : [];
    setSessionId(full?.session_id ?? null);
    setMessages(
      history
        .filter(
          (m): m is SessionHistoryEntry & { role: 'user' | 'assistant'; content: string } =>
            m != null &&
            (m.role === 'user' || m.role === 'assistant') &&
            typeof m.content === 'string',
        )
        .map((m) => ({ role: m.role, content: m.content })),
    );
    setCurrentPhase(full?.phase ?? 'arrival');
    setPhaseHint(null);
    if (full?.phase === 'completed') {
      setCompletedSeal({
        summary: full?.summary ?? null,
        dedication: full?.dedication_text ?? null,
      });
    } else {
      setCompletedSeal(null);
    }
  }, []);

  // -------------------------------------------------------------------------
  // Scroll handling — glide to the newest message.
  // -------------------------------------------------------------------------

  const scrollToBottom = useCallback((smooth = true): void => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  }, []);

  useEffect(() => {
    scrollToBottom(false);
  }, [sessionId, scrollToBottom]);

  useEffect(() => {
    const t = setTimeout(() => scrollToBottom(true), 40);
    return () => clearTimeout(t);
  }, [messages, isLoading, scrollToBottom]);

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  const handleSend = useCallback(async (): Promise<void> => {
    const text = input.trim();
    if (!text || isLoading || sessionId == null) return;
    setInput('');
    setIsLoading(true);
    setWavered(false);

    // Optimistic user bubble.
    const userMsg: HealingMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const res = await fetch(apiUrl(`/healing/sessions/${sessionId}/messages`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error(`messages ${res.status}`);
      const data: HealingMessageResponse = await res.json();
      const assistantContent = typeof data?.content === 'string' ? data.content : '';
      const assistantMsg: HealingMessage = { role: 'assistant', content: assistantContent };
      setMessages((prev) => [...prev, assistantMsg]);
      if (data?.phase) setCurrentPhase(data.phase);
      setPhaseHint(data?.phase_hint ?? null);

      if (data?.phase === 'completed') {
        // Fetch the sealed summary + dedication.
        try {
          const full = await loadSession(sessionId);
          setCompletedSeal({
            summary: full?.summary ?? null,
            dedication: full?.dedication_text ?? null,
          });
        } catch {
          setCompletedSeal({ summary: null, dedication: null });
        }
        // Refresh the drawer ordering (this session is now sealed).
        fetchSessions().then(setSessions);
      }
    } catch (err) {
      log.warn('Sanctuary: send wavered', err);
      addToast({
        type: 'error',
        title: 'Could not send message',
        message: errMessage(err),
        duration: 5,
      });
      // Roll back the optimistic bubble and surface a gentle notice.
      setMessages((prev) => prev.filter((m) => m !== userMsg));
      setInput(text); // restore the draft so nothing is lost
      setWavered(true);
    } finally {
      setIsLoading(false);
      // Return focus to the input for continuous dialogue.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [input, isLoading, sessionId, loadSession, fetchSessions, addToast]);

  const handleAdvance = useCallback(async (): Promise<void> => {
    if (sessionId == null) return;
    setPhaseHint(null);
    setIsLoading(true);
    setWavered(false);
    try {
      const res = await fetch(apiUrl(`/healing/sessions/${sessionId}/advance`), {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`advance ${res.status}`);
      const data: HealingAdvanceResponse = await res.json();
      if (data?.phase) setCurrentPhase(data.phase);
      if (data?.phase === 'completed') {
        try {
          const full = await loadSession(sessionId);
          setCompletedSeal({
            summary: full?.summary ?? null,
            dedication: full?.dedication_text ?? null,
          });
        } catch {
          setCompletedSeal({ summary: null, dedication: null });
        }
        fetchSessions().then(setSessions);
      }
    } catch (err) {
      log.warn('Sanctuary: advance wavered', err);
      addToast({
        type: 'error',
        title: 'Could not advance phase',
        message: errMessage(err),
        duration: 5,
      });
      setWavered(true);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, loadSession, fetchSessions, addToast]);

  const handleNewSession = useCallback(async (): Promise<void> => {
    setIsInitializing(true);
    setWavered(false);
    try {
      const created = await createSession();
      setSessionId(created.session_id);
      setCurrentPhase(created.phase ?? 'arrival');
      setMessages([]);
      setPhaseHint(null);
      setCompletedSeal(null);
      const seed: LocalSessionSeed = {
        session_id: created.session_id,
        started_at: created.started_at,
        phases_completed: ['arrival'],
        summary: null,
        ended_at: null,
      };
      setSessions((prev) => [seed as SessionListItem, ...prev]);
      requestAnimationFrame(() => inputRef.current?.focus());
    } catch (err) {
      log.error('Sanctuary: new session failed', err);
      addToast({
        type: 'error',
        title: 'Could not start a new session',
        message: errMessage(err),
        duration: 5,
      });
      setWavered(true);
    } finally {
      setIsInitializing(false);
    }
  }, [createSession, addToast]);

  const handleSelectSession = useCallback(
    async (id: string): Promise<void> => {
      setDrawerOpen(false);
      if (id == null) return;
      setIsInitializing(true);
      setWavered(false);
      try {
        const full = await loadSession(id);
        hydrateFromSession(full);
      } catch (err) {
        log.warn('Sanctuary: select session wavered', err);
        addToast({
          type: 'error',
          title: 'Could not load selected session',
          message: errMessage(err),
          duration: 5,
        });
        setWavered(true);
      } finally {
        setIsInitializing(false);
      }
    },
    [loadSession, hydrateFromSession, addToast],
  );

  // -------------------------------------------------------------------------
  // Derived view state
  // -------------------------------------------------------------------------

  const isCompleted = currentPhase === 'completed';
  const activeIdx = useMemo<number | null>(
    () => (isCompleted ? PHASES.length : phaseIndex(currentPhase)),
    [currentPhase, isCompleted],
  );
  const currentPhaseMeta = useMemo<{ label: string; role: string; invocation: string }>(() => {
    if (isCompleted) {
      return { label: 'Sealed', role: '', invocation: 'The container is closed. The merit has been offered.' };
    }
    const p = PHASES.find((x) => x.key === currentPhase);
    return p
      ? { label: p.label, role: p.role, invocation: PHASE_INVOCATION[p.key] || '' }
      : { label: '', role: '', invocation: '' };
  }, [currentPhase, isCompleted]);

  /**
   * The hint is informational. The server may have already auto-advanced
   * (so phase === hint). We only offer a manual advance when the hint
   * names a phase genuinely ahead of the current one.
   */
  const hintAhead = useMemo<string | null>(() => {
    if (!phaseHint || typeof phaseHint !== 'string') return null;
    const target = phaseHint.toLowerCase();
    if (target === 'completed' || target === currentPhase) return null;
    const curIdx = phaseIndex(currentPhase);
    const tgtIdx = phaseIndex(target as PhaseKey);
    if (curIdx == null) return null;
    if (tgtIdx == null) return null;
    if (tgtIdx <= curIdx) return null;
    return PHASE_LABEL[target] || target;
  }, [phaseHint, currentPhase]);

  const hintAcknowledged = useMemo<string | null>(() => {
    if (!phaseHint || typeof phaseHint !== 'string') return null;
    if (phaseHint.toLowerCase() === currentPhase) {
      return PHASE_LABEL[phaseHint.toLowerCase()] || null;
    }
    return null;
  }, [phaseHint, currentPhase]);

  const canSend = input.trim().length > 0 && !isLoading && !isCompleted;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div
      className="sanctuary-root"
      style={{ '--sanctuary-active-idx': activeIdx ?? 0 } as React.CSSProperties}
    >
      <StyleBlock />

      {/* Ambient field — a barely-there warm glow, like a single lamp. */}
      <div className="sanctuary-ambient" aria-hidden="true" />

      {/* Header: phase indicator + quiet controls */}
      <header className="sanctuary-header">
        <div className="sanctuary-header-controls sanctuary-header-controls--left">
          <button
            type="button"
            className="sanctuary-quiet-btn"
            onClick={() => setDrawerOpen(true)}
            title="Past sessions"
          >
            <Archive size={14} />
            <span>Past</span>
            {sessions.length > 0 && <span className="sanctuary-quiet-count">{sessions.length}</span>}
          </button>
        </div>

        <PhaseIndicator
          phases={PHASES}
          activeIdx={activeIdx}
          isCompleted={isCompleted}
          currentLabel={currentPhaseMeta.label}
        />

        <div className="sanctuary-header-controls sanctuary-header-controls--right">
          <button
            type="button"
            className="sanctuary-quiet-btn"
            onClick={handleNewSession}
            disabled={isInitializing}
            title="Begin a new session"
          >
            <Plus size={14} />
            <span>New</span>
          </button>
        </div>
      </header>

      {/* Phase invocation line — one breath of context under the indicator */}
      <div className="sanctuary-invocation" key={currentPhase ?? 'none'}>
        <span className="sanctuary-invocation-role">{currentPhaseMeta.role}</span>
        <span className="sanctuary-invocation-sep" aria-hidden="true">·</span>
        <span className="sanctuary-invocation-text">{currentPhaseMeta.invocation}</span>
      </div>

      {/* Message column */}
      <main className="sanctuary-main" ref={scrollRef}>
        <div className="sanctuary-column">
          {isInitializing ? (
            <div className="sanctuary-held">
              <Spin size="small" />
              <Text className="sanctuary-held-text">The space is being held…</Text>
            </div>
          ) : !sessionId ? (
            /* Landing — no session yet. User clicks Begin to enter. */
            <div className="sanctuary-landing" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
              <Text style={{
                display: 'block', fontSize: '1.5rem', fontFamily: 'Georgia, serif',
                color: 'var(--sanctuary-text-soft, #c4b8a8)', marginBottom: '1rem',
              }}>
                The Sanctuary
              </Text>
              <Text style={{
                display: 'block', fontSize: '0.9rem', lineHeight: 1.8,
                color: 'var(--sanctuary-text-faint, #8a8074)', maxWidth: 420, margin: '0 auto 2rem',
              }}>
                A space to sit with loss, grief, and disruption.<br/>
                When you are ready, you may begin.
              </Text>
              <button
                type="button"
                onClick={handleNewSession}
                style={{
                  padding: '0.6rem 2rem', fontSize: '0.85rem', fontFamily: 'Georgia, serif',
                  letterSpacing: '0.15em', textTransform: 'uppercase',
                  background: 'var(--sanctuary-gold, #c9a45c)', color: '#1a1410',
                  border: 'none', borderRadius: '2px', cursor: 'pointer',
                  transition: 'box-shadow 0.3s',
                }}
              >
                Begin
              </button>
            </div>
          ) : messages.length === 0 ? (
            <OpeningPhrase isCompleted={isCompleted} />
          ) : (
            <>
              {messages.map((m, i) => (
                <MessageBubble key={`${sessionId}-${i}`} role={m.role} content={m.content} index={i} />
              ))}

              {isLoading && (
                <div className="sanctuary-held sanctuary-held--inline">
                  <span className="sanctuary-breath-dot" aria-hidden="true" />
                  <Text className="sanctuary-held-text">The space is being held…</Text>
                </div>
              )}

              {hintAhead && (
                <PhaseTransitionPrompt
                  label={hintAhead}
                  onAdvance={handleAdvance}
                  onDismiss={() => setPhaseHint(null)}
                  disabled={isLoading}
                />
              )}

              {!hintAhead && hintAcknowledged && (
                <div className="sanctuary-ack">
                  The dialogue moves into <em>{hintAcknowledged}</em>.
                </div>
              )}

              {wavered && (
                <div className="sanctuary-ack sanctuary-ack--wavered">
                  The container wavered. Take a breath, then try again.
                </div>
              )}

              {isCompleted && <CompletedSeal seal={completedSeal} onNewSession={handleNewSession} />}
            </>
          )}
        </div>
      </main>

      {/* Input — pinned, calm, hidden until a session is active */}
      {sessionId != null && (
      <footer className="sanctuary-footer">
        <div className="sanctuary-input-wrap">
          <Input.TextArea
            ref={inputRef}
            className="sanctuary-input"
            value={input}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
            onPressEnter={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={
              isCompleted
                ? 'This session is sealed. Begin a new one to continue.'
                : isLoading
                  ? '…'
                  : 'Speak what is here.'
            }
            autoSize={{ minRows: 1, maxRows: 6 }}
            disabled={isLoading || isCompleted || isInitializing}
            variant="borderless"
          />
          <button
            type="button"
            className="sanctuary-send"
            onClick={handleSend}
            disabled={!canSend}
            aria-label="Send"
          >
            <Send size={15} />
          </button>
        </div>
        <div className="sanctuary-footer-hint">
          {isLoading ? 'Listening…' : isCompleted ? 'Sealed.' : 'Enter to send · Shift+Enter for a new line'}
        </div>
      </footer>
      )}

      <SessionList
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sessions={sessions}
        currentSessionId={sessionId}
        onSelect={handleSelectSession}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface PhaseIndicatorProps {
  phases: PhaseMeta[];
  activeIdx: number | null;
  isCompleted: boolean;
  currentLabel: string;
}

/**
 * PhaseIndicator — five dots joined by a hairline; the active one glows.
 * Compact, uppercase labels sit beneath each node.
 */
function PhaseIndicator({ phases, activeIdx, isCompleted, currentLabel }: PhaseIndicatorProps) {
  return (
    <nav className="sanctuary-phase" aria-label="Dialogue phase">
      <div className="sanctuary-phase-track">
        {phases.map((p, i) => {
          const state =
            isCompleted || (activeIdx != null && i < activeIdx)
              ? 'done'
              : i === activeIdx
                ? 'active'
                : 'future';
          return (
            <div
              key={p.key}
              className={`sanctuary-phase-node sanctuary-phase-node--${state}`}
              data-active={i === activeIdx && !isCompleted}
              aria-current={i === activeIdx && !isCompleted ? 'step' : undefined}
              title={currentLabel}
            >
              <span className="sanctuary-phase-dot" />
              <span className="sanctuary-phase-label">{p.label}</span>
            </div>
          );
        })}
      </div>
    </nav>
  );
}

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  index: number;
}

/**
 * MessageBubble — LLM turns read like a letter (serif, soft card, left);
 * user turns are brief, right-aligned, muted lavender.
 */
function MessageBubble({ role, content, index }: MessageBubbleProps) {
  const isUser = role === 'user';
  return (
    <div
      className={isUser ? 'sanctuary-msg sanctuary-msg--user' : 'sanctuary-msg sanctuary-msg--guide'}
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <div className="sanctuary-msg-body">
        {content.split(/\n{2,}/).map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>
    </div>
  );
}

interface OpeningPhraseProps {
  isCompleted: boolean;
}

/** Opening phrase shown when a session has no messages yet. */
function OpeningPhrase({ isCompleted }: OpeningPhraseProps) {
  if (isCompleted) return null;
  return (
    <div className="sanctuary-opening">
      <div className="sanctuary-opening-mark" aria-hidden="true">
        ॐ
      </div>
      <p className="sanctuary-opening-text">
        This is a held space. Speak what weighs on you — the dialogue will walk
        with you through Arrival, Seeing, Meeting, Release, and Dedication.
      </p>
      <p className="sanctuary-opening-sub">There is nothing to fix here. Only to meet.</p>
    </div>
  );
}

interface PhaseTransitionPromptProps {
  label: string;
  onAdvance: () => void;
  onDismiss: () => void;
  disabled: boolean;
}

/** Subtle inline prompt offering a phase advance. */
function PhaseTransitionPrompt({ label, onAdvance, onDismiss, disabled }: PhaseTransitionPromptProps) {
  return (
    <div className="sanctuary-prompt">
      <div className="sanctuary-prompt-text">
        The dialogue suggests moving into <em>{label}</em>. Advance when ready.
      </div>
      <div className="sanctuary-prompt-actions">
        <button type="button" className="sanctuary-prompt-btn sanctuary-prompt-btn--ghost" onClick={onDismiss} disabled={disabled}>
          Not yet
        </button>
        <button type="button" className="sanctuary-prompt-btn sanctuary-prompt-btn--solid" onClick={onAdvance} disabled={disabled}>
          Advance
        </button>
      </div>
    </div>
  );
}

interface CompletedSealProps {
  seal: CompletedSealPayload | null;
  onNewSession: () => void;
}

/** The sealed state — dedication + summary + a way to begin again. */
function CompletedSeal({ seal, onNewSession }: CompletedSealProps) {
  return (
    <div className="sanctuary-seal">
      <div className="sanctuary-seal-rule" aria-hidden="true" />
      <div className="sanctuary-seal-mark" aria-hidden="true">
        ◎
      </div>
      {seal?.dedication && (
        <blockquote className="sanctuary-seal-dedication">{seal.dedication}</blockquote>
      )}
      {seal?.summary && (
        <details className="sanctuary-seal-details">
          <summary>What was witnessed</summary>
          <p>{seal.summary}</p>
        </details>
      )}
      {!seal?.dedication && !seal?.summary && (
        <p className="sanctuary-seal-fallback">
          The session is sealed. The merit of this meeting is dedicated to all beings who suffer loss.
        </p>
      )}
      <button type="button" className="sanctuary-seal-new" onClick={onNewSession}>
        Begin a new session
      </button>
      <p className="sanctuary-seal-continuation">
        If you'd like to continue with 88 Buddhas recitation,{' '}
        <Link to="/buddhas" className="sanctuary-seal-continuation-link">
          enter the practice space
        </Link>
        .
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scoped styles — all selectors live under `.sanctuary-root`.
// Kept inline so the route is self-contained and doesn't touch globals.css.
// ---------------------------------------------------------------------------

function StyleBlock() {
  return (
    <style>{`
      .sanctuary-root {
        /* Palette — deep, calm, candlelit-hall-at-night. */
        --sanctuary-bg: #08080f;
        --sanctuary-bg-elev: #0c0c16;
        --sanctuary-surface: rgba(245, 240, 230, 0.035);
        --sanctuary-surface-hover: rgba(245, 240, 230, 0.06);
        --sanctuary-surface-border: rgba(245, 240, 230, 0.07);
        --sanctuary-text: #e6dfd2;
        --sanctuary-text-soft: rgba(230, 223, 210, 0.62);
        --sanctuary-text-faint: rgba(230, 223, 210, 0.38);
        --sanctuary-gold: #c9a572;
        --sanctuary-gold-soft: rgba(201, 165, 114, 0.5);
        --sanctuary-gold-faint: rgba(201, 165, 114, 0.18);
        --sanctuary-lavender: #9d92c2;
        --sanctuary-lavender-soft: rgba(157, 146, 194, 0.22);

        /* Typography — a readable serif carries the dialogue. */
        --sanctuary-serif: Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, "Times New Roman", serif;

        position: relative;
        height: 100%;
        display: flex;
        flex-direction: column;
        background:
          radial-gradient(120% 80% at 50% -10%, rgba(201, 165, 114, 0.05) 0%, rgba(8, 8, 15, 0) 55%),
          radial-gradient(100% 100% at 50% 50%, #0c0c16 0%, #060609 70%, #040408 100%);
        color: var(--sanctuary-text);
        overflow: hidden;
        isolation: isolate;
      }

      /* Override the app's vivid purple body bg inside the sanctuary only. */
      .sanctuary-root::before {
        content: "";
        position: absolute;
        inset: 0;
        background: var(--sanctuary-bg);
        z-index: -2;
      }

      .sanctuary-ambient {
        position: absolute;
        top: -30%;
        left: 50%;
        transform: translateX(-50%);
        width: 70%;
        height: 60%;
        background: radial-gradient(circle, rgba(201, 165, 114, 0.06) 0%, rgba(201, 165, 114, 0) 60%);
        filter: blur(40px);
        pointer-events: none;
        z-index: -1;
      }

      /* ---- Header ---- */
      .sanctuary-header {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        padding: 22px 28px 14px;
        gap: 16px;
      }
      .sanctuary-header-controls--left { justify-self: start; }
      .sanctuary-header-controls--right { justify-self: end; }

      .sanctuary-quiet-btn {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 7px 12px;
        background: transparent;
        border: 1px solid transparent;
        color: var(--sanctuary-text-faint);
        font-family: var(--sanctuary-serif);
        font-size: 12px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        cursor: pointer;
        border-radius: 999px;
        transition: color 240ms ease, border-color 240ms ease, background 240ms ease;
      }
      .sanctuary-quiet-btn:hover:not(:disabled) {
        color: var(--sanctuary-text-soft);
        border-color: var(--sanctuary-surface-border);
        background: var(--sanctuary-surface);
      }
      .sanctuary-quiet-btn:disabled { opacity: 0.4; cursor: not-allowed; }
      .sanctuary-quiet-count {
        font-size: 10px;
        color: var(--sanctuary-gold);
        letter-spacing: 0.08em;
      }

      /* ---- Phase indicator ---- */
      .sanctuary-phase { display: flex; justify-content: center; }
      .sanctuary-phase-track {
        display: flex;
        align-items: flex-start;
        gap: 0;
      }
      .sanctuary-phase-node {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 0 18px;
        min-width: 78px;
      }
      /* The hairline connecting the dots. */
      .sanctuary-phase-node::before {
        content: "";
        position: absolute;
        top: 4px;
        left: -50%;
        right: 50%;
        height: 1px;
        background: var(--sanctuary-surface-border);
      }
      .sanctuary-phase-node:first-child::before { display: none; }
      .sanctuary-phase-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--sanctuary-text-faint);
        transition: background 400ms ease, box-shadow 400ms ease, transform 400ms ease;
        position: relative;
        z-index: 1;
      }
      .sanctuary-phase-label {
        margin-top: 10px;
        font-family: var(--sanctuary-serif);
        font-size: 10.5px;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--sanctuary-text-faint);
        transition: color 400ms ease;
        white-space: nowrap;
      }
      .sanctuary-phase-node--done .sanctuary-phase-dot {
        background: var(--sanctuary-gold);
        box-shadow: 0 0 6px var(--sanctuary-gold-faint);
      }
      .sanctuary-phase-node--done .sanctuary-phase-label {
        color: var(--sanctuary-text-soft);
      }
      .sanctuary-phase-node--active .sanctuary-phase-dot {
        background: var(--sanctuary-gold);
        box-shadow: 0 0 0 4px rgba(201, 165, 114, 0.12), 0 0 14px var(--sanctuary-gold-soft);
        animation: sanctuary-breathe 3.2s ease-in-out infinite;
      }
      .sanctuary-phase-node--active .sanctuary-phase-label {
        color: var(--sanctuary-gold);
      }
      @keyframes sanctuary-breathe {
        0%, 100% { box-shadow: 0 0 0 4px rgba(201, 165, 114, 0.10), 0 0 10px var(--sanctuary-gold-soft); }
        50%      { box-shadow: 0 0 0 5px rgba(201, 165, 114, 0.16), 0 0 18px var(--sanctuary-gold-soft); }
      }

      /* ---- Invocation line ---- */
      .sanctuary-invocation {
        text-align: center;
        padding: 6px 24px 18px;
        font-family: var(--sanctuary-serif);
        font-size: 12.5px;
        color: var(--sanctuary-text-faint);
        font-style: italic;
        animation: sanctuary-fade-in 600ms ease both;
      }
      .sanctuary-invocation-role {
        letter-spacing: 0.16em;
        text-transform: uppercase;
        font-style: normal;
        color: var(--sanctuary-text-soft);
      }
      .sanctuary-invocation-sep { margin: 0 8px; opacity: 0.5; }
      .sanctuary-invocation-text { white-space: nowrap; }
      @media (max-width: 640px) {
        .sanctuary-invocation-text { white-space: normal; }
      }

      /* ---- Main / message column ---- */
      .sanctuary-main {
        flex: 1 1 auto;
        overflow-y: auto;
        overflow-x: hidden;
        scroll-behavior: smooth;
        padding: 8px 0 32px;
      }
      .sanctuary-main::-webkit-scrollbar { width: 5px; }
      .sanctuary-main::-webkit-scrollbar-track { background: transparent; }
      .sanctuary-main::-webkit-scrollbar-thumb {
        background: rgba(201, 165, 114, 0.12);
        border-radius: 4px;
      }
      .sanctuary-main::-webkit-scrollbar-thumb:hover { background: rgba(201, 165, 114, 0.22); }

      .sanctuary-column {
        max-width: 720px;
        margin: 0 auto;
        padding: 0 28px;
        display: flex;
        flex-direction: column;
        gap: 22px;
      }

      /* ---- Held / loading ---- */
      .sanctuary-held {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 10px 4px;
        animation: sanctuary-fade-in 500ms ease both;
      }
      .sanctuary-held--inline { padding-left: 26px; }
      .sanctuary-held-text {
        color: var(--sanctuary-text-faint) !important;
        font-family: var(--sanctuary-serif) !important;
        font-style: italic;
        font-size: 13px;
      }
      .sanctuary-breath-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--sanctuary-gold-soft);
        animation: sanctuary-breathe 1.8s ease-in-out infinite;
      }

      /* ---- Opening phrase ---- */
      .sanctuary-opening {
        text-align: center;
        padding: 8vh 0 4vh;
        animation: sanctuary-fade-in 800ms ease both;
      }
      .sanctuary-opening-mark {
        font-family: var(--sanctuary-serif);
        font-size: 34px;
        color: var(--sanctuary-gold);
        opacity: 0.55;
        margin-bottom: 24px;
        line-height: 1;
      }
      .sanctuary-opening-text {
        font-family: var(--sanctuary-serif);
        font-size: 17px;
        line-height: 1.85;
        color: var(--sanctuary-text-soft);
        max-width: 520px;
        margin: 0 auto 14px;
      }
      .sanctuary-opening-sub {
        font-family: var(--sanctuary-serif);
        font-style: italic;
        font-size: 13px;
        color: var(--sanctuary-text-faint);
      }

      /* ---- Messages ---- */
      .sanctuary-msg {
        animation: sanctuary-fade-in 560ms ease both;
      }
      @keyframes sanctuary-fade-in {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
      }

      .sanctuary-msg--guide {
        align-self: flex-start;
        max-width: 92%;
      }
      .sanctuary-msg--guide .sanctuary-msg-body {
        background: var(--sanctuary-surface);
        border: 1px solid var(--sanctuary-surface-border);
        border-left: 2px solid var(--sanctuary-gold-faint);
        border-radius: 2px 14px 14px 2px;
        padding: 20px 26px;
        font-family: var(--sanctuary-serif);
        font-size: 16px;
        line-height: 1.85;
        color: var(--sanctuary-text);
        letter-spacing: 0.005em;
      }
      .sanctuary-msg--guide .sanctuary-msg-body p { margin: 0; }
      .sanctuary-msg--guide .sanctuary-msg-body p + p { margin-top: 14px; }

      .sanctuary-msg--user {
        align-self: flex-end;
        max-width: 78%;
      }
      .sanctuary-msg--user .sanctuary-msg-body {
        background: var(--sanctuary-lavender-soft);
        border: 1px solid rgba(157, 146, 194, 0.18);
        border-radius: 14px 2px 2px 14px;
        padding: 12px 18px;
        font-family: var(--sanctuary-serif);
        font-size: 14.5px;
        line-height: 1.7;
        color: var(--sanctuary-text-soft);
        text-align: right;
      }
      .sanctuary-msg--user .sanctuary-msg-body p { margin: 0; }
      .sanctuary-msg--user .sanctuary-msg-body p + p { margin-top: 8px; }

      /* ---- Phase transition prompt ---- */
      .sanctuary-prompt {
        align-self: center;
        max-width: 560px;
        margin: 6px auto 0;
        padding: 16px 22px;
        background: rgba(201, 165, 114, 0.05);
        border: 1px solid var(--sanctuary-gold-faint);
        border-radius: 14px;
        text-align: center;
        animation: sanctuary-fade-in 500ms ease both;
      }
      .sanctuary-prompt-text {
        font-family: var(--sanctuary-serif);
        font-size: 13.5px;
        color: var(--sanctuary-text-soft);
        line-height: 1.6;
        margin-bottom: 12px;
      }
      .sanctuary-prompt-text em { color: var(--sanctuary-gold); font-style: normal; letter-spacing: 0.04em; }
      .sanctuary-prompt-actions { display: flex; gap: 10px; justify-content: center; }
      .sanctuary-prompt-btn {
        padding: 7px 18px;
        font-family: var(--sanctuary-serif);
        font-size: 12px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        border-radius: 999px;
        cursor: pointer;
        transition: all 240ms ease;
      }
      .sanctuary-prompt-btn:disabled { opacity: 0.4; cursor: not-allowed; }
      .sanctuary-prompt-btn--ghost {
        background: transparent;
        border: 1px solid var(--sanctuary-surface-border);
        color: var(--sanctuary-text-faint);
      }
      .sanctuary-prompt-btn--ghost:hover:not(:disabled) { color: var(--sanctuary-text-soft); border-color: var(--sanctuary-text-faint); }
      .sanctuary-prompt-btn--solid {
        background: var(--sanctuary-gold);
        border: 1px solid var(--sanctuary-gold);
        color: #1a1408;
        font-weight: 600;
      }
      .sanctuary-prompt-btn--solid:hover:not(:disabled) { box-shadow: 0 0 16px var(--sanctuary-gold-soft); }

      .sanctuary-ack {
        align-self: center;
        font-family: var(--sanctuary-serif);
        font-style: italic;
        font-size: 12.5px;
        color: var(--sanctuary-text-faint);
        text-align: center;
        padding: 4px 12px;
        animation: sanctuary-fade-in 500ms ease both;
      }
      .sanctuary-ack em { color: var(--sanctuary-gold); font-style: normal; }
      .sanctuary-ack--wavered { color: rgba(220, 160, 140, 0.7); }

      /* ---- Completed seal ---- */
      .sanctuary-seal {
        margin: 30px auto 10px;
        max-width: 600px;
        text-align: center;
        animation: sanctuary-fade-in 800ms ease both;
      }
      .sanctuary-seal-rule {
        width: 60px;
        height: 1px;
        margin: 0 auto 22px;
        background: linear-gradient(90deg, transparent, var(--sanctuary-gold-soft), transparent);
      }
      .sanctuary-seal-mark {
        font-family: var(--sanctuary-serif);
        font-size: 26px;
        color: var(--sanctuary-gold);
        opacity: 0.7;
        margin-bottom: 20px;
      }
      .sanctuary-seal-dedication {
        font-family: var(--sanctuary-serif);
        font-style: italic;
        font-size: 15.5px;
        line-height: 1.9;
        color: var(--sanctuary-text);
        margin: 0 0 18px;
        padding: 0 12px;
      }
      .sanctuary-seal-details {
        text-align: left;
        margin: 18px auto;
        max-width: 520px;
        font-family: var(--sanctuary-serif);
      }
      .sanctuary-seal-details summary {
        cursor: pointer;
        font-size: 11.5px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--sanctuary-text-faint);
        list-style: none;
        text-align: center;
        margin-bottom: 12px;
      }
      .sanctuary-seal-details summary::-webkit-details-marker { display: none; }
      .sanctuary-seal-details p {
        font-size: 14px;
        line-height: 1.8;
        color: var(--sanctuary-text-soft);
        margin: 0;
      }
      .sanctuary-seal-fallback {
        font-family: var(--sanctuary-serif);
        font-style: italic;
        font-size: 14.5px;
        line-height: 1.85;
        color: var(--sanctuary-text-soft);
        max-width: 480px;
        margin: 0 auto 22px;
      }
      .sanctuary-seal-new {
        margin-top: 14px;
        padding: 11px 28px;
        background: transparent;
        border: 1px solid var(--sanctuary-gold-soft);
        color: var(--sanctuary-gold);
        font-family: var(--sanctuary-serif);
        font-size: 12.5px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        border-radius: 999px;
        cursor: pointer;
        transition: all 280ms ease;
      }
      .sanctuary-seal-new:hover {
        background: var(--sanctuary-gold-faint);
        box-shadow: 0 0 18px var(--sanctuary-gold-faint);
      }
      .sanctuary-seal-continuation {
        margin: 18px auto 0;
        max-width: 460px;
        font-family: var(--sanctuary-serif);
        font-style: italic;
        font-size: 13px;
        line-height: 1.75;
        color: var(--sanctuary-text-faint);
        text-align: center;
      }
      .sanctuary-seal-continuation-link {
        color: var(--sanctuary-gold-soft);
        text-decoration: none;
        border-bottom: 1px dotted rgba(201, 165, 114, 0.35);
        padding-bottom: 1px;
        transition: color 240ms ease, border-color 240ms ease;
      }
      .sanctuary-seal-continuation-link:hover {
        color: var(--sanctuary-gold);
        border-bottom-color: var(--sanctuary-gold);
      }

      /* ---- Footer / input ---- */
      .sanctuary-footer {
        flex: 0 0 auto;
        padding: 12px 28px 22px;
        background: linear-gradient(to top, var(--sanctuary-bg) 60%, transparent);
      }
      .sanctuary-input-wrap {
        max-width: 720px;
        margin: 0 auto;
        display: flex;
        align-items: flex-end;
        gap: 10px;
        background: var(--sanctuary-surface);
        border: 1px solid var(--sanctuary-surface-border);
        border-radius: 16px;
        padding: 6px 6px 6px 18px;
        transition: border-color 280ms ease, background 280ms ease;
      }
      .sanctuary-input-wrap:focus-within {
        border-color: var(--sanctuary-gold-faint);
        background: rgba(245, 240, 230, 0.05);
      }
      .sanctuary-input {
        flex: 1 1 auto;
        background: transparent !important;
        font-family: var(--sanctuary-serif) !important;
        font-size: 15px !important;
        line-height: 1.7 !important;
        color: var(--sanctuary-text) !important;
        resize: none;
      }
      .sanctuary-input textarea {
        background: transparent !important;
        color: var(--sanctuary-text) !important;
      }
      .sanctuary-input::placeholder,
      .sanctuary-input textarea::placeholder {
        color: var(--sanctuary-text-faint) !important;
        font-style: italic;
      }
      .sanctuary-input.ant-input[disabled] { color: var(--sanctuary-text-faint) !important; }

      .sanctuary-send {
        flex: 0 0 auto;
        width: 38px;
        height: 38px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        border: none;
        background: var(--sanctuary-gold);
        color: #1a1408;
        cursor: pointer;
        transition: background 240ms ease, box-shadow 240ms ease, opacity 240ms ease, transform 120ms ease;
      }
      .sanctuary-send:hover:not(:disabled) { box-shadow: 0 0 16px var(--sanctuary-gold-soft); }
      .sanctuary-send:active:not(:disabled) { transform: scale(0.94); }
      .sanctuary-send:disabled { opacity: 0.25; cursor: not-allowed; }

      .sanctuary-footer-hint {
        max-width: 720px;
        margin: 8px auto 0;
        font-family: var(--sanctuary-serif);
        font-size: 11px;
        letter-spacing: 0.1em;
        color: var(--sanctuary-text-faint);
        text-align: center;
      }

      @media (max-width: 720px) {
        .sanctuary-header { padding: 16px 16px 10px; grid-template-columns: auto 1fr auto; }
        .sanctuary-phase-node { padding: 0 8px; min-width: 0; }
        .sanctuary-phase-label { font-size: 9px; letter-spacing: 0.16em; }
        .sanctuary-column { padding: 0 16px; }
        .sanctuary-footer { padding: 10px 16px 18px; }
        .sanctuary-quiet-btn span:not(.sanctuary-quiet-count) { display: none; }
      }

      @media (prefers-reduced-motion: reduce) {
        .sanctuary-phase-node--active .sanctuary-phase-dot,
        .sanctuary-breath-dot { animation: none; }
        .sanctuary-msg, .sanctuary-opening, .sanctuary-invocation,
        .sanctuary-prompt, .sanctuary-ack, .sanctuary-seal, .sanctuary-held { animation: none; }
      }
    `}</style>
  );
}
