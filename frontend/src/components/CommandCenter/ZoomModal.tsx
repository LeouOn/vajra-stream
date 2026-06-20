/**
 * ZoomModal — detail Modal for sigil / tarot / I Ching / geomancy items.
 *
 * Extracted verbatim from `components/UI/CommandCenter.jsx` (lines 786-944) as
 * part of the CommandCenter decomposition (Task 3.3, item 7). Pure
 * presentational component: props-only, zero coupling to CommandCenter state.
 *
 * Opens whenever `activeZoomItem` is non-null; the parent controls visibility
 * by passing either an item or `null`. `onClose` is wired to the Modal's
 * `onCancel` so the parent can clear the active item.
 *
 * @component
 * @param {Object}     props
 * @param {Object|null} props.activeZoomItem - the item payload to render, or null.
 * @param {() => void}  props.onClose        - fired when the user dismisses the modal.
 */
import React from 'react';
import { Modal } from 'antd';

export default function ZoomModal({ activeZoomItem, onClose }) {
  return (
    <Modal
      open={!!activeZoomItem}
      onCancel={onClose}
      footer={null}
      width={800}
      centered
      styles={{ body: { padding: '24px', background: '#0a0a0a', display: 'flex', gap: '24px', maxHeight: '80vh', overflowY: 'auto' } }}
    >
      {activeZoomItem && (
        <>
          {/* Left: Graphic Container */}
          <div className="flex-1 flex items-center justify-center bg-gray-900/60 rounded-xl p-4 border border-white/5 min-h-[300px]">
            {activeZoomItem.type === 'sigil' && activeZoomItem.svg && (
              <div dangerouslySetInnerHTML={{ __html: activeZoomItem.svg }} className="w-full max-w-[280px] h-full flex items-center justify-center shadow-lg" />
            )}
            {activeZoomItem.type === 'sigil_ai' && activeZoomItem.ai_image && (
              <img src={activeZoomItem.ai_image} alt={activeZoomItem.title} className="w-full max-w-[280px] object-contain rounded-xl shadow-lg border border-purple-500/20" />
            )}
            {activeZoomItem.type === 'tarot' && activeZoomItem.svg && (
              <div dangerouslySetInnerHTML={{ __html: activeZoomItem.svg }} className="w-full max-w-[160px] h-full flex items-center justify-center shadow-lg" />
            )}
            {activeZoomItem.type === 'iching' && activeZoomItem.svg && (
              <div dangerouslySetInnerHTML={{ __html: activeZoomItem.svg }} className="w-full max-w-[320px] h-full flex items-center justify-center shadow-lg" />
            )}
            {activeZoomItem.type === 'geomancy' && activeZoomItem.svg && (
              <div dangerouslySetInnerHTML={{ __html: activeZoomItem.svg }} className="w-full max-w-[360px] h-full flex items-center justify-center shadow-lg" />
            )}
          </div>

          {/* Right: Info details */}
          <div className="flex-1 flex flex-col justify-start space-y-4">
            <div>
              <span className="text-[10px] text-purple-400 font-mono font-bold tracking-widest block uppercase">VAJRA.STREAM ORACLE</span>
              <h3 className="text-xl font-bold text-white font-serif">{activeZoomItem.title}</h3>
            </div>

            {/* Tarot details */}
            {activeZoomItem.type === 'tarot' && activeZoomItem.card && (
              <div className="space-y-3 text-sm text-gray-300">
                <div className="flex flex-wrap gap-2">
                  <span className="px-2 py-0.5 bg-purple-950 text-purple-300 border border-purple-500/20 rounded-md text-[10px] font-mono">
                    ELEMENT: {activeZoomItem.card.element}
                  </span>
                  {activeZoomItem.card.ruler && (
                    <span className="px-2 py-0.5 bg-cyan-950 text-cyan-300 border border-cyan-500/20 rounded-md text-[10px] font-mono">
                      RULER: {activeZoomItem.card.ruler}
                    </span>
                  )}
                  {activeZoomItem.card.hebrew && (
                    <span className="px-2 py-0.5 bg-yellow-950 text-yellow-300 border border-yellow-500/20 rounded-md text-[10px] font-mono">
                      LETTER: {activeZoomItem.card.hebrew}
                    </span>
                  )}
                  <span className="px-2 py-0.5 bg-gray-800 text-gray-200 border border-white/5 rounded-md text-[10px] font-mono">
                    {activeZoomItem.card.orientation.toUpperCase()}
                  </span>
                </div>
                <div className="space-y-2 border-t border-white/10 pt-3">
                  <h4 className="text-xs font-bold text-white font-mono uppercase">Esoteric Meaning</h4>
                  <p className="italic text-purple-200 bg-purple-900/10 p-3 rounded-lg border border-purple-500/10">
                    "{activeZoomItem.card.meaning}"
                  </p>
                </div>
              </div>
            )}

            {/* Sigil details */}
            {(activeZoomItem.type === 'sigil' || activeZoomItem.type === 'sigil_ai') && (
              <div className="space-y-3 text-sm text-gray-300">
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-cyan-400 font-mono uppercase">Intention Focus</h4>
                  <p className="italic text-cyan-100 bg-cyan-900/10 p-3 rounded-lg border border-cyan-500/10">
                    "{activeZoomItem.intention}"
                  </p>
                </div>
                <div className="border-t border-white/10 pt-3 text-xs text-gray-400 leading-relaxed font-mono">
                  <p>Frequencies tuned. Kamea grid calculation completed. Scalar intention broadcast set at peak resonance.</p>
                </div>
              </div>
            )}

            {/* I Ching details */}
            {activeZoomItem.type === 'iching' && activeZoomItem.cast && (
              <div className="space-y-3 text-sm text-gray-300">
                <div className="space-y-2">
                  <span className="text-xs font-bold text-white font-mono uppercase block">Primary Hexagram</span>
                  <div className="p-3 bg-gray-900/60 rounded-lg border border-white/5">
                    <span className="font-bold text-cyan-400 block">{activeZoomItem.cast.primary?.name}</span>
                    <p className="text-xs text-gray-300 mt-1">{activeZoomItem.cast.primary?.meaning}</p>
                  </div>
                </div>

                {activeZoomItem.cast.has_changes && (
                  <div className="space-y-2 pt-2 border-t border-white/10">
                    <span className="text-xs font-bold text-purple-300 font-mono uppercase block">Relating Hexagram (After Changes)</span>
                    <div className="p-3 bg-gray-900/60 rounded-lg border border-purple-500/10">
                      <span className="font-bold text-purple-300 block">{activeZoomItem.cast.relating?.name}</span>
                      <p className="text-xs text-gray-300 mt-1">{activeZoomItem.cast.relating?.meaning}</p>
                    </div>
                    <div className="text-[10px] text-gray-400 font-mono">
                      Changing Lines: {activeZoomItem.cast.changing_lines.join(', ')}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Geomancy details */}
            {activeZoomItem.type === 'geomancy' && activeZoomItem.chart && (
              <div className="space-y-3 text-sm text-gray-300">
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2 bg-gray-900/60 border border-white/5 rounded">
                    <span className="text-gray-500 block">THE JUDGE</span>
                    <span className="text-yellow-400 font-bold">{activeZoomItem.chart.figures?.Judge?.name}</span>
                  </div>
                  <div className="p-2 bg-gray-900/60 border border-white/5 rounded">
                    <span className="text-gray-500 block">RECONCILER</span>
                    <span className="text-yellow-400 font-bold">{activeZoomItem.chart.figures?.Reconciler?.name}</span>
                  </div>
                  <div className="p-2 bg-gray-900/60 border border-white/5 rounded">
                    <span className="text-gray-500 block">RIGHT WITNESS</span>
                    <span className="text-gray-300">{activeZoomItem.chart.figures?.['Right Witness']?.name}</span>
                  </div>
                  <div className="p-2 bg-gray-900/60 border border-white/5 rounded">
                    <span className="text-gray-500 block">LEFT WITNESS</span>
                    <span className="text-gray-300">{activeZoomItem.chart.figures?.['Left Witness']?.name}</span>
                  </div>
                </div>

                <div className="border-t border-white/10 pt-3 space-y-2">
                  <h4 className="text-xs font-bold text-white font-mono uppercase">Geomantic Meaning (Judge)</h4>
                  <p className="italic text-yellow-200 bg-yellow-950/10 p-3 rounded-lg border border-yellow-500/10">
                    "{activeZoomItem.chart.figures?.Judge?.meaning}"
                  </p>
                </div>

                <div className="border-t border-white/10 pt-3">
                  <h4 className="text-xs font-bold text-white font-mono uppercase mb-2">Astrological House Projection</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-[10px] max-h-32 overflow-y-auto pr-1">
                    {Array.from({ length: 12 }).map((_, idx) => {
                      const houseNum = idx + 1;
                      const figure = activeZoomItem.chart.houses?.[houseNum];
                      if (!figure) return null;
                      return (
                        <div key={houseNum} className="p-1.5 bg-black/40 border border-white/5 rounded flex flex-col justify-between">
                          <span className="text-gray-500 font-bold">House {houseNum}</span>
                          <span className="text-purple-300 font-semibold truncate">{figure.name}</span>
                          <span className="text-[8px] text-gray-400 font-mono truncate">{figure.element} / {figure.ruler}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
