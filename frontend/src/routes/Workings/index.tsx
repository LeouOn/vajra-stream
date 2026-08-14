/**
 * Workings — the house ledger of sealed sittings.
 */
import React, { useEffect, useState } from 'react';
import { Flame } from 'lucide-react';
import { apiUrl } from '../../utils/api';
import PageHeader from '../../components/UI/PageHeader';
import { WorkingFolioCard, type WorkingResult } from '../../components/CommandCenter/RenderMessageWidgets';

interface WorkingSummary {
  working_id: string;
  intention: string;
  target?: string;
  sealed_at?: string;
  rate_values?: number[];
  has_witness?: boolean;
}

export default function WorkingsPage(): React.ReactElement {
  const [items, setItems] = useState<WorkingSummary[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [folio, setFolio] = useState<WorkingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(apiUrl('/operator/workings?limit=40'))
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('list failed'))))
      .then((data: { workings?: WorkingSummary[] }) => {
        if (!cancelled) setItems(Array.isArray(data.workings) ? data.workings : []);
      })
      .catch(() => {
        if (!cancelled) setError('Could not load workings');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!openId) {
      setFolio(null);
      return;
    }
    let cancelled = false;
    fetch(apiUrl(`/operator/workings/${openId}`))
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('load failed'))))
      .then((data: WorkingResult) => {
        if (!cancelled) setFolio(data);
      })
      .catch(() => {
        if (!cancelled) setError('Could not open that working');
      });
    return () => {
      cancelled = true;
    };
  }, [openId]);

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-4">
      <PageHeader
        icon={<Flame className="w-7 h-7 text-amber-400" />}
        title="Workings"
        subtitle="Sealed sittings — rates, charge, witness, and manifestation."
      />
      {error && <p className="text-sm text-red-300">{error}</p>}
      {items.length === 0 && !error && (
        <p className="text-sm text-amber-200/70">
          No workings yet. Seal one from Command Center with Begin working.
        </p>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-2">
          {items.map((item) => (
            <button
              key={item.working_id}
              type="button"
              onClick={() => setOpenId(item.working_id)}
              className={`w-full text-left rounded-lg border px-3 py-2 ${
                openId === item.working_id
                  ? 'border-amber-400/50 bg-amber-950/50'
                  : 'border-amber-500/20 bg-amber-950/20 hover:bg-amber-950/40'
              }`}
            >
              <div className="text-[10px] font-mono text-amber-400/70">{item.working_id}</div>
              <div className="text-sm text-amber-50">{item.intention}</div>
              <div className="text-[10px] text-amber-300/60 font-mono mt-1">
                {(item.rate_values || []).join(' · ') || '—'}
                {item.has_witness ? ' · witness' : ''}
              </div>
            </button>
          ))}
        </div>
        <div>
          {folio && folio.working_id && (
            <WorkingFolioCard initial={folio} autoSpeak={false} />
          )}
        </div>
      </div>
    </div>
  );
}
