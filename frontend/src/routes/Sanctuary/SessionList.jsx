/**
 * SessionList — a calm drawer of past healing dialogue sessions.
 *
 * Rendered inside an AntD <Drawer> (the parent owns open/close state).
 * Each row shows: a soft phase dot, the session date, the phase reached,
 * and the first few words of the LLM summary (when present). Selecting a
 * row loads that session into the sanctuary via `onSelect(sessionId)`.
 *
 * Design mirrors the sanctuary aesthetic: no bright tags, no busy stats.
 * Just quiet typographic rows separated by hairline dividers.
 *
 * @component
 * @param {Object} props
 * @param {boolean} props.open             Drawer visibility.
 * @param {Function} props.onClose         Close handler.
 * @param {Array} props.sessions           List from GET /healing/sessions.
 * @param {number|string|null} props.currentSessionId  Highlights the active row.
 * @param {Function} props.onSelect        (sessionId) => void
 */
import React from 'react';
import { Drawer, Typography, Empty, Button } from 'antd';
import { History } from 'lucide-react';

const { Text } = Typography;

/** Order of the arc — used to label the furthest phase reached. */
const PHASE_ORDER = ['arrival', 'seeing', 'meeting', 'release', 'dedication', 'completed'];
const PHASE_LABEL = {
  arrival: 'Arrival',
  seeing: 'Seeing',
  meeting: 'Meeting',
  release: 'Release',
  dedication: 'Dedication',
  completed: 'Sealed',
};

function phaseReachedLabel(phasesCompleted) {
  if (!Array.isArray(phasesCompleted) || phasesCompleted.length === 0) return 'Arrival';
  // The furthest phase the session touched.
  let furthestIdx = 0;
  for (const p of phasesCompleted) {
    const idx = PHASE_ORDER.indexOf(p);
    if (idx > furthestIdx) furthestIdx = idx;
  }
  return PHASE_LABEL[PHASE_ORDER[furthestIdx]] || 'Arrival';
}

function formatStartedAt(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function snippet(summary) {
  if (!summary || typeof summary !== 'string') return null;
  const clean = summary.replace(/\s+/g, ' ').trim();
  if (!clean) return null;
  return clean.length > 120 ? `${clean.slice(0, 120)}…` : clean;
}

export default function SessionList({ open, onClose, sessions, currentSessionId, onSelect }) {
  const rows = Array.isArray(sessions) ? sessions : [];

  return (
    <Drawer
      title={
        <span style={{ fontFamily: 'var(--sanctuary-serif)', letterSpacing: '0.14em', textTransform: 'uppercase', fontSize: 12, color: 'var(--sanctuary-text-soft)' }}>
          Past Sessions
        </span>
      }
      placement="right"
      open={open}
      onClose={onClose}
      width={Math.min(420, (typeof window !== 'undefined' ? window.innerWidth : 420) - 32)}
      styles={{
        header: { borderBottom: '1px solid var(--sanctuary-surface-border)' },
        body: { padding: 0 },
        mask: { background: 'rgba(4,4,8,0.55)', backdropFilter: 'blur(2px)' },
      }}
      style={{ background: 'var(--sanctuary-bg-elev)' }}
    >
      <History
        size={0}
        style={{ display: 'none' }}
        aria-hidden="true"
      />
      {rows.length === 0 ? (
        <div style={{ padding: '40px 24px' }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text style={{ color: 'var(--sanctuary-text-faint)', fontSize: 13, fontFamily: 'var(--sanctuary-serif)' }}>
                No previous sessions. The space is open.
              </Text>
            }
          />
        </div>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {rows.map((s) => {
            const id = s.session_id ?? s.id;
            const isCurrent = currentSessionId != null && String(id) === String(currentSessionId);
            const reached = phaseReachedLabel(s.phases_completed);
            const snip = snippet(s.summary);
            return (
              <li key={id} style={{ borderBottom: '1px solid var(--sanctuary-surface-border)' }}>
                <button
                  type="button"
                  onClick={() => onSelect && onSelect(id)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    background: isCurrent ? 'rgba(201,165,114,0.06)' : 'transparent',
                    border: 'none',
                    padding: '18px 24px',
                    cursor: 'pointer',
                    display: 'block',
                    transition: 'background 240ms ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isCurrent) e.currentTarget.style.background = 'rgba(245,240,230,0.025)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isCurrent) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <span
                      aria-hidden="true"
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        flex: '0 0 6px',
                        background: isCurrent ? 'var(--sanctuary-gold)' : 'var(--sanctuary-text-faint)',
                        boxShadow: isCurrent ? '0 0 8px var(--sanctuary-gold-soft)' : 'none',
                      }}
                    />
                    <span
                      style={{
                        fontFamily: 'var(--sanctuary-serif)',
                        fontSize: 12,
                        letterSpacing: '0.12em',
                        textTransform: 'uppercase',
                        color: isCurrent ? 'var(--sanctuary-gold)' : 'var(--sanctuary-text-soft)',
                      }}
                    >
                      {reached}
                    </span>
                    {s.ended_at && (
                      <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--sanctuary-text-faint)', letterSpacing: '0.08em' }}>
                        sealed
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--sanctuary-text-faint)', fontFamily: 'var(--sanctuary-serif)', marginBottom: snip ? 8 : 0 }}>
                    {formatStartedAt(s.started_at) || `Session ${id}`}
                  </div>
                  {snip && (
                    <div
                      style={{
                        fontFamily: 'var(--sanctuary-serif)',
                        fontSize: 13,
                        lineHeight: 1.6,
                        color: 'var(--sanctuary-text-soft)',
                        fontStyle: 'italic',
                      }}
                    >
                      “{snip}”
                    </div>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {rows.length > 0 && (
        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--sanctuary-surface-border)' }}>
          <Button type="text" block onClick={onClose} style={{ color: 'var(--sanctuary-text-faint)', fontFamily: 'var(--sanctuary-serif)', letterSpacing: '0.08em' }}>
            Close
          </Button>
        </div>
      )}
    </Drawer>
  );
}
