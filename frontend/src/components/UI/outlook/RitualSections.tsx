/**
 * RitualSections — the narrative body: phase dots plus progressively
 * revealed ritual sections (or the plain text when it has no sections),
 * then the sigil once every section is shown.
 *
 * @component
 */
import React from 'react';
import { RefreshCw } from 'lucide-react';
import { Tooltip, Typography } from 'antd';
import { RITUAL_PHASES } from './outlookConstants';
import type { CurrentNarrative } from './outlookNarrative';

const { Text, Paragraph } = Typography;

interface RitualSectionsProps {
  narrative: CurrentNarrative;
  sections: string[];
  revealedSections: number;
}

export default function RitualSections({ narrative, sections, revealedSections }: RitualSectionsProps) {
  return (
    <>
      {sections.length > 1 ? (
        <>
          <div
            className="ritual-phase-dots"
            aria-label="Ritual phases"
            style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 12 }}
          >
            {RITUAL_PHASES.map((phase, i) => (
              <Tooltip key={phase} title={`${i + 1}. ${phase}`}>
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: i < revealedSections ? '#06b6d4' : 'rgba(148, 163, 184, 0.25)',
                    boxShadow: i < revealedSections ? '0 0 8px rgba(6, 182, 212, 0.6)' : 'none',
                    transition: 'background 0.6s ease, box-shadow 0.6s ease',
                  }}
                />
              </Tooltip>
            ))}
          </div>
          {sections.slice(0, revealedSections).map((section, i) => (
            <Paragraph
              key={`section-${i}-${section.slice(0, 24)}`}
              className="ritual-section-fade"
              style={{
                whiteSpace: 'pre-wrap',
                fontSize: 14,
                lineHeight: 1.8,
                fontFamily: 'Georgia, serif',
                color: '#e5e7eb',
                marginBottom: 12,
              }}
            >
              {section}
            </Paragraph>
          ))}
          {revealedSections < sections.length && (
            <div style={{ textAlign: 'center', padding: '8px 0' }}>
              <Text type="secondary" style={{ fontSize: 11, fontStyle: 'italic' }}>
                <RefreshCw className="w-3 h-3 inline mr-1 animate-spin" />
                Unveiling phase {revealedSections + 1} of {sections.length}…
              </Text>
            </div>
          )}
        </>
      ) : (
        <Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.8, fontFamily: 'Georgia, serif', color: '#e5e7eb' }}>
          {narrative.narrative}
        </Paragraph>
      )}
      {revealedSections >= sections.length && sections.length > 0 && narrative.divination_raw?.sigil?.svg && (
        <div style={{ marginTop: 16, textAlign: 'center' }}>
          <div
            dangerouslySetInnerHTML={{ __html: narrative.divination_raw.sigil.svg }}
            className="svg-container"
            style={{ maxWidth: 280, margin: '0 auto' }}
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            Sigil: {narrative.divination_raw.sigil.reduced} on {narrative.divination_raw.sigil.kamea} grid
          </Text>
        </div>
      )}
    </>
  );
}
