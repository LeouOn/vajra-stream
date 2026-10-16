/**
 * useChatEnvironment — the "Inject Context" switches and debug mode, plus
 * the data they pull in: chakra anatomy (GET /healing/chakra/all, fetched
 * while Chakras is on) and today's operations-ledger summary (refreshed
 * every 30s while Status & Ledger is on). Turning a switch off clears its
 * data; every fetch is best-effort and cancelled on toggle/unmount.
 */
import { useState, useEffect } from 'react';
import { apiUrl } from '../../utils/api';
import { fetchOperationsSummary, startOfLocalDayIso } from '../../lib/operationsSummary';
import type { OperationsSummary } from '../../types/operations';
import type { ChakraEntry } from './commandCenterTypes';

export const LEDGER_REFRESH_MS = 30000;

export function useChatEnvironment() {
  const [includeAstrology, setIncludeAstrology] = useState(true);
  const [includeAnatomy, setIncludeAnatomy] = useState(true);
  const [includeHardware, setIncludeHardware] = useState(true);
  const [debugMode, setDebugMode] = useState(true);
  const [chakraData, setChakraData] = useState<ChakraEntry[] | null>(null);
  const [ledgerSummary, setLedgerSummary] = useState<OperationsSummary | null>(null);

  useEffect(() => {
    if (!includeAnatomy) {
      setChakraData(null);
      return;
    }
    let cancelled = false;
    const fetchChakras = async () => {
      try {
        const res = await fetch(apiUrl('/healing/chakra/all'));
        if (res.ok) {
          const data = await res.json();
          if (!cancelled && data.chakras) {
            setChakraData(data.chakras as ChakraEntry[]);
          }
        }
      } catch {
        /* chakra context is best-effort */
      }
    };
    fetchChakras();
    return () => { cancelled = true; };
  }, [includeAnatomy]);

  useEffect(() => {
    if (!includeHardware) {
      setLedgerSummary(null);
      return;
    }
    let cancelled = false;
    // Ledger context is best-effort: a null summary just omits the section.
    const fetchLedger = async () => {
      const summary = await fetchOperationsSummary(startOfLocalDayIso());
      if (!cancelled) setLedgerSummary(summary);
    };
    fetchLedger();
    const interval = setInterval(fetchLedger, LEDGER_REFRESH_MS);
    return () => { cancelled = true; clearInterval(interval); };
  }, [includeHardware]);

  return {
    includeAstrology, setIncludeAstrology,
    includeAnatomy, setIncludeAnatomy,
    includeHardware, setIncludeHardware,
    debugMode, setDebugMode,
    chakraData,
    ledgerSummary,
  };
}

export type ChatEnvironment = ReturnType<typeof useChatEnvironment>;
