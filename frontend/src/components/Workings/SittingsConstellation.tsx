/**
 * SittingsConstellation — the Workings ledger as a night sky.
 *
 * Each sealed sitting is a star placed by seal time (x) and the folio's
 * own moon-phase stamp (band). Siblings of one sitting share a
 * constellation line; collapsed duplicates stay visible as faint ghost
 * stars tethered to their keeper. A representation of the folio
 * records — not a second oracle.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  constellationGroups,
  relativeSealTime,
  summaryToStar,
  type Star,
  type StarSummaryInput,
} from './star';

const MOON_GLYPHS = ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘'] as const;
const RIBBON_W = 26;
const PAD = 34;

interface Props {
  workings: StarSummaryInput[];
  onSelect: (workingId: string) => void;
}

export default function SittingsConstellation({ workings, onSelect }: Props): React.ReactElement {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const positionsRef = useRef<Map<string, { x: number; y: number; r: number }>>(new Map());
  const [hover, setHover] = useState<{ star: Star; x: number; y: number } | null>(null);

  const stars = useMemo(
    () => workings.map((s, i) => summaryToStar(s, i, workings)),
    [workings],
  );
  const groups = useMemo(() => constellationGroups(stars), [stars]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // happy-dom and very old browsers ship no 2D context — render nothing
    // rather than throw; the ledger list below remains fully usable.
    const ctx = typeof canvas.getContext === 'function' ? canvas.getContext('2d') : null;
    if (!ctx) return;
    let raf = 0;

    const draw = (now: number) => {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth || 600;
      const h = canvas.clientHeight || 280;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const innerLeft = RIBBON_W + 12;
      const xOf = (t: number) => innerLeft + t * Math.max(0, w - innerLeft - PAD);
      const yOf = (band: number) => PAD + (band / 7) * (h - 2 * PAD);

      // Moon ribbon — the y-axis legend, from the folio's categorical stamps.
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(245, 230, 200, 0.45)';
      MOON_GLYPHS.forEach((glyph, b) => ctx.fillText(glyph, 6, yOf(b)));

      const pos = new Map<string, { x: number; y: number; r: number }>();
      stars.forEach((s) => pos.set(s.working_id, { x: xOf(s.t), y: yOf(s.band), r: s.size }));
      positionsRef.current = pos;

      // Constellation lines between chronological siblings.
      ctx.strokeStyle = 'rgba(245, 230, 200, 0.18)';
      ctx.lineWidth = 1;
      for (const members of groups) {
        ctx.beginPath();
        members.forEach((m, i) => {
          const p = pos.get(m.working_id);
          if (!p) return;
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        });
        ctx.stroke();
      }

      // Ghost tethers: hidden duplicate → its keeper.
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = 'rgba(245, 230, 200, 0.12)';
      for (const s of stars) {
        if (!s.duplicateOf) continue;
        const from = pos.get(s.working_id);
        const to = pos.get(s.duplicateOf);
        if (!from || !to) continue;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // Stars — seeded twinkle, ghosts dim.
      stars.forEach((s, i) => {
        const p = pos.get(s.working_id);
        if (!p) return;
        const twinkle = 0.75 + 0.25 * Math.sin((now / 700) * (1 + (i % 3) * 0.3) + i * 1.7);
        if (!s.ghost) {
          ctx.globalAlpha = s.alpha * twinkle * 0.15;
          ctx.fillStyle = s.hue;
          ctx.beginPath();
          ctx.arc(p.x, p.y, s.size * 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = s.alpha * twinkle;
        ctx.fillStyle = s.hue;
        ctx.beginPath();
        ctx.arc(p.x, p.y, s.size, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      if (hover) {
        const p = pos.get(hover.star.working_id);
        if (p) {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(p.x, p.y, hover.star.size + 3, 0, Math.PI * 2);
          ctx.stroke();
        }
      }

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [stars, groups, hover]);

  const pick = (clientX: number, clientY: number): { star: Star; x: number; y: number } | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const mx = clientX - rect.left;
    const my = clientY - rect.top;
    let best: { star: Star; d: number; x: number; y: number } | null = null;
    for (const s of stars) {
      const p = positionsRef.current.get(s.working_id);
      if (!p) continue;
      const d = Math.hypot(mx - p.x, my - p.y);
      if (d <= s.size + 5 && (!best || d < best.d)) best = { star: s, d, x: p.x, y: p.y };
    }
    return best;
  };

  if (stars.length === 0) {
    return (
      <div
        data-testid="sky-empty"
        className="rounded-lg border border-amber-500/20 bg-amber-950/20 px-4 py-6 text-center text-sm text-amber-200/70"
      >
        No sittings yet — seal one from Command Center and it becomes a star here.
      </div>
    );
  }

  return (
    <div className="relative rounded-lg border border-amber-500/20 bg-amber-950/20">
      <canvas
        ref={canvasRef}
        data-testid="sittings-constellation"
        className="block h-[280px] w-full"
        style={{ cursor: hover ? 'pointer' : 'default' }}
        onMouseMove={(e) => setHover(pick(e.clientX, e.clientY))}
        onMouseLeave={() => setHover(null)}
        onClick={() => hover && onSelect(hover.star.working_id)}
      />
      {hover && (
        <div
          className="pointer-events-none absolute z-10 max-w-[260px] rounded-md border border-amber-500/30 bg-black/85 px-2 py-1.5 text-[10px] font-mono leading-relaxed text-amber-100"
          style={{ left: hover.x + 12, top: hover.y - 10 }}
        >
          <div className="truncate text-amber-200">{hover.star.intention}</div>
          <div className="text-amber-100/60">{hover.star.dials}</div>
          <div className="text-amber-100/60">
            {relativeSealTime(hover.star.sealedAt)}
            {hover.star.multiplier > 1 ? ` · merit ×${hover.star.multiplier.toLocaleString('en-US')}` : ''}
            {hover.star.ghost ? ' · duplicate (hidden)' : ''}
          </div>
        </div>
      )}
    </div>
  );
}
