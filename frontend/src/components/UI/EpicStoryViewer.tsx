/**
 * Epic Story Viewer — immersive liberation narrative display.
 * Cinematic reading mode for Blessing Narratives stories with
 * chapter navigation and dedication display.
 * @component
 * @param {{ story }} props
 */
import React, { useState } from 'react';
import { BookOpen, Sparkles, Compass, Moon, Sun, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import NarrativeTTSPlayer from './NarrativeTTSPlayer';
import { stripThinking } from '../../utils/thinkStrip';

interface SigilData {
  kamea?: string;
  reduced?: string;
  svg?: string;
  [key: string]: unknown;
}

interface DivinationRawPayload {
  tarot?: { svg?: string; name?: string; orientation?: string; [k: string]: unknown };
  iching?: { svg?: string; name?: string; [k: string]: unknown };
  sigil?: SigilData;
  [key: string]: unknown;
}

interface EpicStoryViewerProps {
  narrativeParts?: Array<{ chapter: number; title: string; content: string }>;
  astrologyContext?: string;
  divinationContext?: string;
  divinationRaw?: DivinationRawPayload | null;
  entitiesInvoked?: string;
}

export default function EpicStoryViewer({
  narrativeParts = [],
  astrologyContext = '',
  divinationContext = '',
  divinationRaw = null,
  entitiesInvoked = ''
}: EpicStoryViewerProps = {}) {
  const [currentChapterIndex, setCurrentChapterIndex] = useState(0);

  const allText = (narrativeParts || [])
    .map(p => {
      const raw = (typeof p === 'object' && p ? p.content : '') || '';
      return stripThinking(raw).clean;
    })
    .filter(Boolean)
    .join('\n\n');
  const currentTextRaw = narrativeParts[currentChapterIndex]?.content || '';
  const { clean: currentTextClean, reasoning: currentReasoning } = stripThinking(currentTextRaw);

  if (!narrativeParts || narrativeParts.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500 italic">
        No epic narrative chapters loaded.
      </div>
    );
  }

  const currentChapter = narrativeParts[currentChapterIndex];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full overflow-hidden">
      <style>{`
        .svg-container svg,
        .divination-card-container svg {
          width: 100% !important;
          height: 100% !important;
          max-width: 100% !important;
          max-height: 100% !important;
        }
      `}</style>
      {/* Narrative Section - Main Col Span 2 */}
      <div className="lg:col-span-2 flex flex-col justify-between bg-gray-950/40 p-5 rounded-xl border border-white/5 space-y-4 overflow-y-auto">
        <div className="space-y-4">
          <div className="flex justify-between items-center border-b border-white/10 pb-3 gap-3 flex-wrap">
            <div className="flex-1 min-w-0">
              <span className="text-[10px] text-vajra-purple font-mono font-bold tracking-widest uppercase">
                EPIC NARRATIVE OUTLOOK
              </span>
              <h3 className="text-xl font-bold text-white mt-1">
                Chapter {currentChapter.chapter}: {currentChapter.title}
              </h3>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <NarrativeTTSPlayer
                text={currentTextClean}
                role="outlook_epic"
                label="Speak chapter"
                showAdvanced={false}
              />
              <NarrativeTTSPlayer
                text={allText}
                role="outlook_epic"
                label="Speak full epic"
                showAdvanced
              />
              <div className="text-xs bg-purple-950/50 text-purple-300 px-3 py-1 rounded-full border border-purple-500/20 font-mono">
                Stage {currentChapterIndex + 1} of {narrativeParts.length}
              </div>
            </div>
          </div>

          <div className="text-sm md:text-base text-gray-200 whitespace-pre-wrap leading-relaxed space-y-4 py-2 font-serif">
            {currentTextClean}
            {currentReasoning && (
              <details className="text-xs opacity-60 mt-3 block">
                <summary>💭 Reasoning</summary>
                <div className="mt-1 whitespace-pre-wrap">{currentReasoning}</div>
              </details>
            )}
          </div>
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-between items-center border-t border-white/10 pt-4 mt-4 bg-gray-950/20 p-2 rounded-lg">
          <button
            onClick={() => setCurrentChapterIndex(prev => Math.max(0, prev - 1))}
            disabled={currentChapterIndex === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous Stage
          </button>

          <div className="flex gap-1.5 overflow-x-auto max-w-xs py-1">
            {narrativeParts.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentChapterIndex(idx)}
                className={`w-2.5 h-2.5 rounded-full transition-all ${
                  idx === currentChapterIndex 
                    ? 'bg-vajra-cyan scale-125 shadow-[0_0_8px_rgba(6,182,212,0.6)]' 
                    : 'bg-white/20 hover:bg-white/40'
                }`}
                title={`Go to Stage ${idx + 1}`}
              />
            ))}
          </div>

          <button
            onClick={() => setCurrentChapterIndex(prev => Math.min(narrativeParts.length - 1, prev + 1))}
            disabled={currentChapterIndex === narrativeParts.length - 1}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-600 to-teal-600 text-white hover:from-cyan-700 hover:to-teal-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            Next Stage
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Esoteric Metadata Sidebar */}
      <div className="space-y-6 overflow-y-auto pr-1">
        {/* Oracular/Divination Cards */}
        {divinationRaw && (
          <div className="bg-gray-950/40 p-4 rounded-xl border border-white/5 space-y-4">
            <h4 className="text-xs font-bold font-mono text-vajra-cyan tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              ORACLE READING
            </h4>
            
            <div className="grid grid-cols-2 gap-3">
              {/* Tarot Draw */}
              {divinationRaw.tarot && divinationRaw.tarot.svg && (
                <div className="flex flex-col items-center bg-black/40 p-2.5 rounded-lg border border-white/5 text-center">
                  <span className="text-[9px] text-gray-500 font-mono block uppercase">TAROT RULER</span>
                  <div className="w-20 h-28 my-1.5 flex items-center justify-center relative overflow-hidden rounded">
                    <div 
                      dangerouslySetInnerHTML={{ __html: divinationRaw.tarot.svg }} 
                      className="divination-card-container w-full h-full flex justify-center" 
                    />
                  </div>
                  <span className="text-[10px] font-bold text-white truncate max-w-full block">
                    {divinationRaw.tarot.name}
                  </span>
                  <span className="text-[8px] text-purple-400 font-serif italic block truncate max-w-full">
                    {divinationRaw.tarot.orientation}
                  </span>
                </div>
              )}

              {/* I Ching Draw */}
              {divinationRaw.iching && divinationRaw.iching.svg && (
                <div className="flex flex-col items-center bg-black/40 p-2.5 rounded-lg border border-white/5 text-center">
                  <span className="text-[9px] text-gray-500 font-mono block uppercase">HEXAGRAM</span>
                  <div className="w-20 h-28 my-1.5 flex items-center justify-center relative overflow-hidden rounded">
                    <div 
                      dangerouslySetInnerHTML={{ __html: divinationRaw.iching.svg }} 
                      className="divination-card-container w-full h-full flex justify-center" 
                    />
                  </div>
                  <span className="text-[10px] font-bold text-white truncate max-w-full block">
                    {divinationRaw.iching.name.split(' / ')[0]}
                  </span>
                  <span className="text-[8px] text-cyan-400 font-serif italic block truncate max-w-full">
                    {divinationRaw.iching.name.split(' / ')[1] || 'Hexagram'}
                  </span>
                </div>
              )}
            </div>

            {divinationContext && (
              <p className="text-[11px] text-gray-400 leading-snug italic font-serif border-t border-white/5 pt-2">
                "{divinationContext}"
              </p>
            )}
          </div>
        )}

        {/* Sigil Kamea Trace */}
        {divinationRaw?.sigil?.svg && (
          <div className="bg-gray-950/40 p-4 rounded-xl border border-white/5 space-y-2">
            <h4 className="text-xs font-bold font-mono text-vajra-cyan tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              KAMEA SIGIL
            </h4>
            <div
              dangerouslySetInnerHTML={{ __html: divinationRaw.sigil.svg }}
              className="svg-container w-full max-w-[220px] mx-auto"
            />
            <p className="text-[10px] text-gray-400 font-mono text-center">
              {divinationRaw.sigil.reduced} · {divinationRaw.sigil.kamea} grid
            </p>
          </div>
        )}

        {/* Astrological Snapshot */}
        {astrologyContext && (
          <div className="bg-gray-950/40 p-4 rounded-xl border border-white/5 space-y-2">
            <h4 className="text-xs font-bold font-mono text-yellow-500 tracking-wider flex items-center gap-2">
              <Sun className="w-4 h-4" />
              ASTROLOGICAL TIMING
            </h4>
            <p className="text-xs text-gray-300 leading-relaxed">
              {astrologyContext}
            </p>
          </div>
        )}

        {/* Sacred Entities Invoked */}
        {entitiesInvoked && (
          <div className="bg-gray-950/40 p-4 rounded-xl border border-white/5 space-y-2">
            <h4 className="text-xs font-bold font-mono text-vajra-purple tracking-wider flex items-center gap-2">
              <BookOpen className="w-4 h-4" />
              SACRED INVOCATION
            </h4>
            <p className="text-xs text-gray-300 leading-relaxed font-serif">
              {entitiesInvoked}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
