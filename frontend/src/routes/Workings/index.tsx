/**
 * Workings — house ledger of sealed sittings, with hide/show and rate tools.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Eye, EyeOff, Flame, Trash2 } from 'lucide-react';
import { Input, Switch } from 'antd';
import { apiUrl } from '../../utils/api';
import PageHeader from '../../components/UI/PageHeader';
import { WorkingFolioCard, type WorkingResult } from '../../components/CommandCenter/RenderMessageWidgets';
import { useRateStore } from '../../stores/rateStore';
import { audioFeedback } from '../../utils/audioFeedback';

interface WorkingSummary {
  working_id: string;
  intention: string;
  target?: string;
  sealed_at?: string;
  rate_values?: number[];
  frequencies?: number[];
  solfeggio_names?: string[];
  source?: string;
  hidden?: boolean;
  has_witness?: boolean;
}

export default function WorkingsPage(): React.ReactElement {
  const [items, setItems] = useState<WorkingSummary[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [folio, setFolio] = useState<WorkingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [showHidden, setShowHidden] = useState(false);
  const [showRates, setShowRates] = useState(true);
  const [showInstrument, setShowInstrument] = useState(true);
  const [collapsing, setCollapsing] = useState(false);
  const [collapseMsg, setCollapseMsg] = useState<string | null>(null);
  const loadWorkingRates = useRateStore((s) => s.loadWorkingRates);

  const refreshList = () => {
    fetch(apiUrl(`/operator/workings?limit=50&include_hidden=${showHidden ? 'true' : 'false'}`))
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('list failed'))))
      .then((data: { workings?: WorkingSummary[] }) => {
        setItems(Array.isArray(data.workings) ? data.workings : []);
      })
      .catch(() => setError('Could not load workings'));
  };

  useEffect(() => {
    refreshList();
  }, [showHidden]);

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

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => {
      const hay = `${item.intention || ''} ${item.target || ''} ${item.working_id} ${item.source || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [items, query]);

  const patchWorking = async (id: string, body: { hidden?: boolean; rate_values?: number[] }) => {
    const res = await fetch(apiUrl(`/operator/workings/${id}`), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`patch ${res.status}`);
    const data = await res.json() as WorkingResult;
    if (openId === id) setFolio(data);
    refreshList();
    return data;
  };

  const hideWorking = async (item: WorkingSummary, hidden: boolean) => {
    try {
      await patchWorking(item.working_id, { hidden });
      audioFeedback.playClick();
      if (hidden && openId === item.working_id && !showHidden) {
        setOpenId(null);
      }
    } catch {
      setError('Could not update visibility');
    }
  };

  const deleteWorking = async (id: string) => {
    if (!window.confirm('Delete this working folio from disk?')) return;
    try {
      const res = await fetch(apiUrl(`/operator/workings/${id}`), { method: 'DELETE' });
      if (!res.ok) throw new Error(`delete ${res.status}`);
      if (openId === id) {
        setOpenId(null);
        setFolio(null);
      }
      refreshList();
      audioFeedback.playSuccess();
    } catch {
      setError('Could not delete that working');
    }
  };

  const loadBoard = (item: WorkingSummary) => {
    if (!item.rate_values || item.rate_values.length < 2) return;
    loadWorkingRates(item.rate_values, { name: item.intention, working_id: item.working_id });
    audioFeedback.playSuccess();
  };

  const collapseDuplicates = async () => {
    setCollapsing(true);
    try {
      const res = await fetch(apiUrl('/operator/workings/collapse_duplicates'), { method: 'POST' });
      if (!res.ok) throw new Error(`collapse ${res.status}`);
      const data = await res.json() as { hidden?: string[]; unique_sittings?: number };
      audioFeedback.playSuccess();
      setError(null);
      setCollapseMsg(
        `Collapsed ${data.hidden?.length ?? 0} duplicate${(data.hidden?.length ?? 0) === 1 ? '' : 's'} — ` +
        `${data.unique_sittings ?? 0} unique sitting${(data.unique_sittings ?? 0) === 1 ? '' : 's'} remain.`,
      );
      refreshList();
    } catch {
      setError('Could not collapse duplicates');
    } finally {
      setCollapsing(false);
    }
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-4">
      <PageHeader
        icon={<Flame className="w-7 h-7 text-amber-400" />}
        title="Workings"
        subtitle="Manage sealed sittings — hide, retune, load rates onto the board."
      />
      {error && <p className="text-sm text-red-300">{error}</p>}
      {collapseMsg && !error && <p className="text-sm text-emerald-300/90" data-testid="collapse-msg">{collapseMsg}</p>}

      <div className="flex flex-wrap items-center gap-4">
        <Input
          allowClear
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search intention, source, id…"
          className="max-w-sm"
        />
        <button
          type="button"
          data-testid="collapse-duplicates"
          onClick={() => { void collapseDuplicates(); }}
          disabled={collapsing}
          className="text-[10px] px-2 py-1 rounded border border-emerald-500/30 text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-50"
        >
          {collapsing ? 'Collapsing…' : 'Collapse duplicates'}
        </button>
        <label className="flex items-center gap-2 text-xs text-amber-100/80">
          <Switch size="small" checked={showRates} onChange={setShowRates} />
          Show rates
        </label>
        <label className="flex items-center gap-2 text-xs text-amber-100/80">
          <Switch size="small" checked={showInstrument} onChange={setShowInstrument} />
          Show instrument
        </label>
        <label className="flex items-center gap-2 text-xs text-amber-100/80">
          <Switch size="small" checked={showHidden} onChange={setShowHidden} />
          Show hidden
        </label>
      </div>

      {visible.length === 0 && !error && (
        <p className="text-sm text-amber-200/70">
          No workings here. Seal one from Command Center or Ritual Composer.
        </p>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-2">
          {visible.map((item) => (
            <div
              key={item.working_id}
              className={`rounded-lg border px-3 py-2 ${
                openId === item.working_id
                  ? 'border-amber-400/50 bg-amber-950/50'
                  : 'border-amber-500/20 bg-amber-950/20'
              } ${item.hidden ? 'opacity-60' : ''}`}
            >
              <button
                type="button"
                onClick={() => setOpenId(item.working_id)}
                className="w-full text-left"
              >
                <div className="flex justify-between gap-2">
                  <div className="text-[10px] font-mono text-amber-400/70">{item.working_id}</div>
                  <div className="text-[10px] text-amber-300/50">{item.source || ''}</div>
                </div>
                <div className="text-sm text-amber-50">{item.intention}</div>
                {showRates && (
                  <div className="text-[10px] text-amber-300/60 font-mono mt-1">
                    {(item.rate_values || []).join(' · ') || '—'}
                    {item.has_witness ? ' · image' : ''}
                  </div>
                )}
              </button>
              <div className="flex flex-wrap gap-2 mt-2">
                <button
                  type="button"
                  onClick={() => loadBoard(item)}
                  className="text-[10px] px-2 py-1 rounded border border-cyan-500/30 text-cyan-200"
                >
                  Load rates
                </button>
                <button
                  type="button"
                  data-testid="hide-working"
                  onClick={() => { void hideWorking(item, !item.hidden); }}
                  className="text-[10px] px-2 py-1 rounded border border-amber-500/30 text-amber-200 inline-flex items-center gap-1"
                >
                  {item.hidden ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                  {item.hidden ? 'Show' : 'Hide'}
                </button>
                <button
                  type="button"
                  data-testid="delete-working"
                  onClick={() => { void deleteWorking(item.working_id); }}
                  className="text-[10px] px-2 py-1 rounded border border-red-500/30 text-red-300 inline-flex items-center gap-1"
                >
                  <Trash2 className="w-3 h-3" />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
        <div>
          {folio && folio.working_id && (
            <WorkingFolioCard
              initial={folio}
              autoSpeak={false}
              showInstrument={showInstrument}
              showRates={showRates}
            />
          )}
        </div>
      </div>
    </div>
  );
}
