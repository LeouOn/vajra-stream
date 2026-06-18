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
 * NOTE: Colors are hardcoded (not CSS variables) because the Drawer renders
 * in a portal at document.body — outside the .sanctuary-root scope where
 * the CSS custom properties are defined.
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

const { Text } = Typography;

// --- Sanctuary palette (mirrors StyleBlock in index.jsx) ---
const C = {
  bg:          '#0c0c16',
  surface:     'rgba(245, 240, 230, 0.035)',
  surfaceHover:'rgba(245, 240, 230, 0.06)',
  border:      'rgba(245, 240, 230, 0.07)',
  text:        '#e6dfd2',
  textSoft:    'rgba(230, 223, 210, 0.62)',
  textFaint:   'rgba(230, 223, 210, 0.38)',
  gold:        '#c9a572',
  goldSoft:    'rgba(201, 165, 114, 0.5)',
  goldFaint:   'rgba(201, 165, 114, 0.18)',
  serif:       'Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, serif',
};

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
        <span style={{
          fontFamily: C.serif,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          fontSize: 12,
          color: C.textSoft,
        }}>
          Past Sessions
        </span>
      }
      placement="right"
      open={open}
      onClose={onClose}
      size="default"
      styles={{
        header: {
          borderBottom: `1px solid ${C.border}`,
          background: C.bg,
        },
        body: {
          padding: 0,
          background: C.bg,
        },
        mask: {
          background: 'rgba(4,4,8,0.55)',
          backdropFilter: 'blur(2px)',
        },
        content: {
          background: C.bg,
        },
      }}
    >
      {rows.length === 0 ? (
        <div style={{ padding: '40px 24px', background: C.bg }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text style={{
                color: C.textFaint,
                fontSize: 13,
                fontFamily: C.serif,
              }}>
                No previous sessions. The space is open.
              </Text>
            }
          />
        </div>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, background: C.bg }}>
          {rows.map((s) => {
            const id = s.session_id ?? s.id;
            const isCurrent = currentSessionId != null && String(id) === String(currentSessionId);
            const reached = phaseReachedLabel(s.phases_completed);
            const snip = snippet(s.summary);
            return (
              <li key={id} style={{ borderBottom: `1px solid ${C.border}` }}>
                <button
                  type="button"
                  onClick={() => onSelect && onSelect(id)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    background: isCurrent ? C.goldFaint : 'transparent',
                    border: 'none',
                    padding: '18px 24px',
                    cursor: 'pointer',
                    display: 'block',
                    transition: 'background 240ms ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isCurrent) e.currentTarget.style.background = C.surfaceHover;
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
                        background: isCurrent ? C.gold : C.textFaint,
                        boxShadow: isCurrent ? `0 0 8px ${C.goldSoft}` : 'none',
                      }}
                    />
                    <span
                      style={{
                        fontFamily: C.serif,
                        fontSize: 12,
                        letterSpacing: '0.12em',
                        textTransform: 'uppercase',
                        color: isCurrent ? C.gold : C.textSoft,
                      }}
                    >
                      {reached}
                    </span>
                    {s.ended_at && (
                      <span style={{
                        marginLeft: 'auto',
                        fontSize: 10,
                        color: C.textFaint,
                        letterSpacing: '0.08em',
                        fontFamily: C.serif,
                      }}>
                        sealed
                      </span>
                    )}
                  </div>
                  <div style={{
                    fontSize: 11,
                    color: C.textFaint,
                    fontFamily: C.serif,
                    marginBottom: snip ? 8 : 0,
                  }}>
                    {formatStartedAt(s.started_at) || `Session ${id}`}
                  </div>
                  {snip && (
                    <div
                      style={{
                        fontFamily: C.serif,
                        fontSize: 13,
                        lineHeight: 1.6,
                        color: C.textSoft,
                        fontStyle: 'italic',
                      }}
                    >
                      "{snip}"
                    </div>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {rows.length > 0 && (
        <div style={{
          padding: '16px 24px',
          borderTop: `1px solid ${C.border}`,
          background: C.bg,
        }}>
          <Button
            type="text"
            block
            onClick={onClose}
            style={{
              color: C.textFaint,
              fontFamily: C.serif,
              letterSpacing: '0.08em',
            }}
          >
            Close
          </Button>
        </div>
      )}
    </Drawer>
  );
}
