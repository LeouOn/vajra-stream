/**
 * Recent sealed workings — the house memory of the table.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiUrl } from '../../utils/api';

interface WorkingSummary {
  working_id: string;
  intention: string;
  target?: string;
  sealed_at?: string;
  rate_values?: number[];
  has_witness?: boolean;
  saka_dawa_duchen?: string;
}

export default function WorkingsStrip() {
  const [items, setItems] = useState<WorkingSummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetch(apiUrl('/operator/workings?limit=8'))
      .then((res) => (res.ok ? res.json() : { workings: [] }))
      .then((data: { workings?: WorkingSummary[] }) => {
        if (!cancelled && Array.isArray(data.workings)) {
          setItems(data.workings);
        }
      })
      .catch(() => {
        /* strip is optional */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (items.length === 0) return null;

  return (
    <div data-testid="workings-strip" className="flex gap-2 overflow-x-auto pb-1">
      <Link
        to="/workings"
        className="flex-shrink-0 w-28 rounded-lg border border-amber-500/30 bg-amber-900/40 px-3 py-2 flex items-center text-xs font-semibold text-amber-100"
      >
        All workings
      </Link>
      {items.map((item) => (
        <Link
          to="/workings"
          key={item.working_id}
          className="flex-shrink-0 w-56 rounded-lg border border-amber-500/20 bg-amber-950/30 px-3 py-2"
        >
          <div className="text-[10px] font-mono text-amber-400/70 truncate">{item.working_id}</div>
          <div className="text-xs text-amber-100 line-clamp-2 mt-0.5">{item.intention}</div>
          <div className="text-[10px] text-amber-300/60 mt-1 font-mono">
            {(item.rate_values || []).join(' · ') || '—'}
            {item.has_witness ? ' · image' : ''}
          </div>
        </Link>
      ))}
    </div>
  );
}
