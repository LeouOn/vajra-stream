/**
 * useOutlookHistory — the stored transmissions list (GET /outlook/history)
 * and row deletion (DELETE /outlook/history/{id}).
 */
import { useState, useCallback } from 'react';
import { message } from 'antd';
import { apiUrl } from '../../../utils/api';
import { audioFeedback } from '../../../utils/audioFeedback';
import type { AddToast, HistoryItem } from './outlookShared';

export function useOutlookHistory(addToast: AddToast) {
  const [historyList, setHistoryList] = useState<HistoryItem[]>([]);

  const fetchHistory = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(apiUrl(`/outlook/history?limit=100`));
      if (res.ok) setHistoryList(((await res.json()) as { history?: HistoryItem[] }).history || []);
    } catch (e) {
      addToast({ type: 'error', title: 'Could not load history', message: 'Backend unreachable.', duration: 3000 });
    }
  }, [addToast]);

  const deleteHistoryItem = useCallback(
    async (item: HistoryItem): Promise<void> => {
      if (item.id == null) {
        message.warning('This entry predates row ids and cannot be deleted.');
        return;
      }
      try {
        const res = await fetch(apiUrl(`/outlook/history/${item.id}`), { method: 'DELETE' });
        if (!res.ok) throw new Error(String(res.status));
        message.success('Transmission deleted.');
        audioFeedback.playClick();
        fetchHistory();
      } catch {
        message.error('Could not delete that transmission.');
        audioFeedback.playError();
      }
    },
    [fetchHistory],
  );

  return { historyList, fetchHistory, deleteHistoryItem };
}
