/**
 * Astrology Panel — Western, Vedic, and Chinese astrology display.
 * Handles saved natal charts, transit analysis, synastry comparison,
 * traditional techniques, and backup exports.
 */
import { useState, useEffect, useRef, Suspense, lazy } from 'react';
import { Compass, Sun, RefreshCw, Copy } from 'lucide-react';
import { Card, Row, Col, Tag, Button, Space, Segmented, Switch } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';
import { apiUrl } from '../../utils/api';
import { formatMoonIllumination } from '../../lib/moonIllumination';
import { fieldProvenance } from '../../lib/provenance';
import type { Provenance } from '../../types/operations';
import Reading from './Reading';
import { useAudioStore } from '../../stores/audioStore';
import { useUIStore } from '../../stores/uiStore';
import VedicPanchanga from './VedicPanchanga';
import ChineseBaZi from './ChineseBaZi';
import {
  sortAspectsByExactness,
  skyReadingLine,
} from '../../lib/astroHelpers';

// Always-visible sub-components — imported eagerly
import SavedChartsDrawer from './SavedChartsDrawer';
import NatalCalculator from './NatalCalculator';
import NatalChartWheel from './NatalChartWheel';
import ErrorBoundary from './ErrorBoundary';
import type { ImportedChartsPayload } from './SavedChartsDrawer';
import type {
  AstrologySnapshot,
  CurrentAstrologyResponse,
  GeocodeResponse,
  ImportChartsResponse,
  RecalculateChartResponse,
  SavedNatalChart,
  WesternAspect,
  WesternPositions,
} from '../../types/astrology';

/** Values NatalCalculator hands to `onSubmit` (kept in sync with its props). */
type NatalCalculatorValues = Parameters<React.ComponentProps<typeof NatalCalculator>['onSubmit']>[0];

type WuXing = 'Wood' | 'Fire' | 'Earth' | 'Metal' | 'Water';

/** Narrow a caught value to a message without assuming it is an Error. */
const errorMessage = (e: unknown): string => (e instanceof Error ? e.message : String(e));

// Tabbed sub-components — lazy-loaded to reduce initial bundle
const TransitComparison = lazy(() => import('./TransitComparison'));
const SynastryViewer = lazy(() => import('./SynastryViewer'));

// 3D mandala — lazy-loaded (Three.js ~600 kB isolated into separate chunk)
const LazySacredMandala = lazy(() => import('./LazySacredMandala'));
const AspectChart = lazy(() => import('../2D/AspectChart'));

// Extraction panel — lazy-loaded
const LazyAstrologyExtractionPanel = lazy(() => import('./AstrologyExtractionPanel'));
const AuspiciousTimingWheel = lazy(() => import('./AuspiciousTimingWheel'));
const CelestialSkyDome = lazy(() => import('./CelestialSkyDome'));
const AdvancedAstrologyPanel = lazy(() => import('./AdvancedAstrologyPanel'));

// Fallback skeleton for lazy components
const LazyFallback = () => (
  <div className="bg-gray-900/60 rounded-xl border border-white/5 p-8 text-center text-xs text-gray-500 italic animate-pulse">
    Loading component…
  </div>
);

export default function AstrologyPanel() {
  const { isPlaying, frequency } = useAudioStore();
  const addToast = useUIStore((s) => s.addToast);
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState('');
  const [liveData, setLiveData] = useState<AstrologySnapshot | null>(null);
  const [customData, setCustomData] = useState<AstrologySnapshot | null>(null);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [activeSystem, setActiveSystem] = useState('all'); // all, western, vedic, chinese

  // Database-backed state
  const [charts, setCharts] = useState<SavedNatalChart[]>([]);
  const [activeChart, setActiveChart] = useState<SavedNatalChart | null>(null);
  const [transitChart, setTransitChart] = useState<SavedNatalChart | null>(null);
  const [subjectA, setSubjectA] = useState<SavedNatalChart | null>(null);
  const [subjectB, setSubjectB] = useState<SavedNatalChart | null>(null);
  const [editingChart, setEditingChart] = useState<SavedNatalChart | null>(null);
  
  // Navigation tabs: 'wheel' (Consolidated Charts), 'transits' (Transit aspect comparison), 'synastry' (Synastry matching)
  const [activeTab, setActiveTab] = useState('wheel');

  // Privacy toggle for LLM-export paths — defaults ON so personal info is
  // stripped unless the user explicitly opts in to sharing it.
  const [stripPii, setStripPii] = useState<boolean>(true);
  const [saka, setSaka] = useState<{
    saka_dawa_duchen?: string;
    days_until_duchen?: number | null;
    is_saka_dawa?: boolean;
  } | null>(null);
  const [sealingHour, setSealingHour] = useState(false);
  const [skyError, setSkyError] = useState<string | null>(null);
  const [placeSource, setPlaceSource] = useState<'device' | 'default'>('default');

  // Geolocation guard — stop retrying after user blocks permission.
  // A successful fix is remembered so the 20s sky poll does not ask again.
  const geoBlocked = useRef(false);
  const geoCoords = useRef<{ lat: number; lon: number } | null>(null);
  const liveSeen = useRef(false);

  // Load saved charts from database
  const fetchSavedCharts = async () => {
    try {
      const response = await fetch(apiUrl('/astrology/charts'));
      if (response.ok) {
        const data: SavedNatalChart[] = await response.json();
        setCharts(data);
      }
    } catch (e) {
      console.error("Error fetching saved charts:", e);
    }
  };

  const fetchLiveAstrology = async (announce = false) => {
    if (!isLiveMode) return;
    const doFetch = async (lat: number | null, lon: number | null, fromDevice: boolean) => {
      try {
        const d = new Date();
        const pad = (n: number) => String(n).padStart(2, '0');
        const localTime = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;

        const params = new URLSearchParams();
        params.append('datetime_str', localTime);
        if (lat !== null && lon !== null) {
          params.append('latitude', lat.toString());
          params.append('longitude', lon.toString());
        }

        const response = await fetch(apiUrl(`/astrology/current?${params.toString()}`));
        if (response.ok) {
          const result: CurrentAstrologyResponse = await response.json();
          if (result?.astrology?.western) {
            setLiveData(result.astrology);
            setPlaceSource(fromDevice ? 'device' : 'default');
            liveSeen.current = true;
            setSkyError(null);
            return;
          }
          const message = 'Ephemeris returned no western chart.';
          if (!liveSeen.current) setSkyError(message);
          else if (announce) addToast({ type: 'error', title: message, duration: 4 });
          return;
        }
        const message = `Sky request failed (HTTP ${response.status}).`;
        if (!liveSeen.current) setSkyError(message);
        else if (announce) addToast({ type: 'error', title: message, duration: 4 });
      } catch (e) {
        console.error("Error in live astrology fetch:", e);
        const message = 'Could not reach the astrology service.';
        if (!liveSeen.current) setSkyError(message);
        else if (announce) addToast({ type: 'error', title: message, duration: 4 });
      }
    };

    if (geoCoords.current) {
      doFetch(geoCoords.current.lat, geoCoords.current.lon, true);
      return;
    }
    if (navigator.geolocation && !geoBlocked.current) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          geoCoords.current = {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
          };
          doFetch(position.coords.latitude, position.coords.longitude, true);
        },
        (err) => {
          // PERMISSION_DENIED = user blocked — stop retrying to avoid console spam
          if (err.code === 1) geoBlocked.current = true;
          doFetch(null, null, false);
        },
        { timeout: 5000 }
      );
    } else {
      doFetch(null, null, false);
    }
  };

  // Poll for live transits and fetch saved charts on mount
  useEffect(() => {
    fetchSavedCharts();
    fetchLiveAstrology();
    fetch(apiUrl('/operator/saka-dawa'))
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data) setSaka(data); })
      .catch(() => {});
    const interval = setInterval(() => {
      if (isLiveMode) fetchLiveAstrology();
    }, 20000);
    return () => clearInterval(interval);
  }, [isLiveMode]);

  useEffect(() => {
    if (charts.length > 0 && !activeChart && !isLiveMode) {
      setActiveChart(charts[0]);
      setTransitChart(charts[0]);
    }
  }, [charts, activeChart, isLiveMode]);

  // Helper: extract error detail from a failed fetch response
  const _readError = async (response: Response): Promise<string> => {
    try {
      const body: { detail?: unknown; message?: unknown } = await response.json();
      return String(body.detail || body.message || `HTTP ${response.status}`);
    } catch {
      return `HTTP ${response.status}: ${response.statusText}`;
    }
  };

  // Helper: compute and display a chart from raw birth data (city + time)
  const _computeTemporaryChart = async (birthTimeIso: string, cityName: string): Promise<AstrologySnapshot> => {
    // Resolve coordinates via geocode
    const geoResponse = await fetch(apiUrl('/astrology/geocode'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city_name: cityName })
    });
    if (!geoResponse.ok) {
      const err = await _readError(geoResponse);
      throw new Error(`Could not geocode "${cityName}": ${err}`);
    }
    const geo: GeocodeResponse = await geoResponse.json();

    // Hit /current with resolved coordinates
    const params = new URLSearchParams({
      datetime_str: birthTimeIso,
      latitude: geo.latitude.toString(),
      longitude: geo.longitude.toString()
    }).toString();
    const response = await fetch(apiUrl(`/astrology/current?${params}`));
    if (!response.ok) {
      const err = await _readError(response);
      throw new Error(`Chart calculation failed: ${err}`);
    }
    const result: CurrentAstrologyResponse = await response.json();
    return result.astrology;
  };

  // Handle calculator submission
  const handleCalculateSubmit = async (values: NatalCalculatorValues) => {
    setLoading(true);
    setLoadingStatus('Geocoding city…');
    audioFeedback.playTelemetry();
    try {
      const shouldSave = values.saveToDb || !!editingChart;
      const birthTimeIso = values.birth_time_iso;
      const cityName = values.city;

      if (shouldSave) {
        // Strip internal fields before sending to server
        const payload = {
          name: values.name,
          birth_time_iso: birthTimeIso,
          city: cityName,
          description: values.description || '',
          tags: values.tags || '',
          notes: values.notes || '',
        };

        let savedChart: SavedNatalChart | null = null;
        if (editingChart) {
          setLoadingStatus('Updating saved profile…');
          const response = await fetch(apiUrl(`/astrology/charts/${editingChart.id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (response.ok) {
            savedChart = await response.json();
            addToast({ type: 'success', title: 'Natal profile updated successfully', duration: 3 });
            setEditingChart(null);
          } else {
            const err = await _readError(response);
            addToast({ type: 'error', title: `Update failed: ${err}`, duration: 5 });
            // Fall through to compute temporary chart anyway
          }
        } else {
          setLoadingStatus('Saving to database…');
          const response = await fetch(apiUrl('/astrology/charts'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (response.ok) {
            savedChart = await response.json();
            addToast({ type: 'success', title: 'Natal profile saved successfully', duration: 3 });
          } else {
            const err = await _readError(response);
            addToast({ type: 'warning', title: `Could not save: ${err}. Showing temporary chart instead.`, duration: 4 });
            // Fall through to compute temporary chart
          }
        }

        // Reload saved charts list and display the chart
        if (savedChart) {
          fetchSavedCharts();
          loadNatalChart(savedChart);
        } else {
          // Save failed — fall back to temporary display
          setLoadingStatus('Computing chart positions…');
          const astroData = await _computeTemporaryChart(birthTimeIso, cityName);
          setCustomData(astroData);
          setIsLiveMode(false);
          setActiveChart(null);
        }
      } else {
        // Temporary calculation only (no save)
        setLoadingStatus('Computing chart positions…');
        const astroData = await _computeTemporaryChart(birthTimeIso, cityName);
        setCustomData(astroData);
        setIsLiveMode(false);
        setActiveChart(null);
        addToast({ type: 'info', title: 'Temporary chart computed successfully', duration: 3 });
        audioFeedback.playSuccess();
      }
    } catch (err) {
      console.error(err);
      addToast({ type: 'error', title: (err instanceof Error && err.message) || 'Error processing request', duration: 5 });
      audioFeedback.playError();
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  };

  const loadNatalChart = (chart: SavedNatalChart) => {
    if (chart && chart.cached_chart_data) {
      try {
        const parsed: AstrologySnapshot = JSON.parse(chart.cached_chart_data);
        setCustomData(parsed);
        setIsLiveMode(false);
        setActiveChart(chart);
        setActiveTab('wheel'); // Toggle back to consolidated wheel view
      } catch (e) {
        console.error("Error parsing cached chart data, falling back to recalculation", e);
        recalculateChart(chart.id);
      }
    } else {
      recalculateChart(chart.id);
    }
  };

  const recalculateChart = async (id: SavedNatalChart['id']) => {
    setLoading(true);
    try {
      const response = await fetch(apiUrl(`/astrology/charts/${id}/recalculate`), {
        method: 'POST'
      });
      if (response.ok) {
        const result: RecalculateChartResponse = await response.json();
        setCustomData(result.cached_chart_data);
        setIsLiveMode(false);
        const matched = charts.find(c => c.id === id);
        if (matched) setActiveChart(matched);
        fetchSavedCharts();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteChart = async (id: SavedNatalChart['id']) => {
    try {
      const response = await fetch(apiUrl(`/astrology/charts/${id}`), {
        method: 'DELETE'
      });
      if (response.ok) {
        addToast({ type: 'success', title: 'Profile deleted successfully', duration: 3 });
        if (activeChart?.id === id) {
          handleResetToLive();
        }
        fetchSavedCharts();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleExportCharts = async () => {
    try {
      const response = await fetch(apiUrl('/astrology/charts/export'));
      if (response.ok) {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `vajra_astrology_profiles_backup.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        addToast({ type: 'success', title: 'Backup downloaded successfully', duration: 3 });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleImportCharts = async (jsonData: ImportedChartsPayload) => {
    try {
      const response = await fetch(apiUrl('/astrology/charts/import'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jsonData)
      });
      if (response.ok) {
        const result: ImportChartsResponse = await response.json();
        addToast({ type: 'success', title: `Successfully imported ${result.imported} profiles`, duration: 3 });
        fetchSavedCharts();
      } else {
        addToast({ type: 'error', title: 'Failed to import profiles', duration: 5 });
      }
    } catch (e) {
      console.error(e);
      addToast({ type: 'error', title: 'Import failed', duration: 5 });
    }
  };

  const handleCopyForLLM = async () => {
    // Live mode: copy current day/location astrology (no saved chart needed)
    if (isLiveMode) {
      if (!liveData) {
        addToast({ type: 'error', title: 'Live data not yet loaded — wait for it to fetch', duration: 5 });
        return;
      }
      try {
        const { formatLiveAstrologyMarkdown } = await import('../../lib/astrologyExport');
        const markdown = formatLiveAstrologyMarkdown(liveData, { pii: !stripPii });
        await navigator.clipboard.writeText(markdown);
        addToast({
          type: 'success',
          title: stripPii ? 'Current astrology copied (PII stripped) for LLM' : 'Current astrology copied for LLM',
          duration: 3,
        });
      } catch (e) {
        console.error(e);
        addToast({ type: 'error', title: 'Live astrology copy failed: ' + errorMessage(e), duration: 5 });
      }
      return;
    }
    // Natal mode: copy saved chart's natal data
    if (!activeChart?.id) {
      addToast({ type: 'error', title: 'Load a saved chart first to copy its natal data', duration: 5 });
      return;
    }
    try {
      const response = await fetch(
        apiUrl(`/astrology/charts/${activeChart.id}/natal-export`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ strip_pii: stripPii }),
        },
      );
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const result = await response.json();
      const data = result.data || result;
      const { formatNatalChartMarkdown } = await import('../../lib/astrologyExport');
      const markdown = formatNatalChartMarkdown(data, { pii: !stripPii });
      await navigator.clipboard.writeText(markdown);
      addToast({
        type: 'success',
        title: stripPii ? 'Natal chart copied (PII stripped) for LLM' : 'Natal chart copied for LLM',
        duration: 3,
      });
    } catch (e) {
      console.error(e);
      addToast({ type: 'error', title: 'Natal chart copy failed: ' + errorMessage(e), duration: 5 });
    }
  };

  const handleBeginWorkingFromHour = async () => {
    const sky = isLiveMode ? liveData : customData;
    const hour = sky?.planetary_hours?.current_planetary_hour;
    const moon = sky?.moon_phase?.phase_name;
    const chartName = isLiveMode ? 'live sky' : (activeChart?.name || 'natal');
    const intention = isLiveMode
      ? `Working in the ${hour || 'present'} hour under a ${moon || 'changing'} moon`
      : `Working from ${chartName}'s chart in the ${hour || 'present'} hour`;
    setSealingHour(true);
    audioFeedback.playTelemetry();
    try {
      const res = await fetch(apiUrl('/operator/working'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          intention,
          target: 'all beings',
          broadcast: true,
          source: 'cosmic-clock',
          chart_name: chartName,
          planetary_hour: hour || undefined,
          moon_phase: moon || undefined,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const folio = await res.json();
      addToast({
        type: 'success',
        title: `Working sealed ${folio.working_id || ''}`,
        message: 'See Workings for the folio, charge, and manifestation image.',
        duration: 5,
      });
      audioFeedback.playSuccess();
    } catch (e) {
      addToast({ type: 'error', title: 'Could not seal working from this hour', duration: 5 });
      audioFeedback.playError();
    } finally {
      setSealingHour(false);
    }
  };

  // SynastryViewer hands back one of the `charts` we passed it (or undefined
  // when cleared); resolve it by id so subject state keeps the full row type.
  const findChart = (id: SavedNatalChart['id'] | undefined): SavedNatalChart | null =>
    (id === undefined ? undefined : charts.find((c) => c.id === id)) ?? null;

  const handleResetToLive = () => {
    setIsLiveMode(true);
    setActiveChart(null);
    audioFeedback.playClick();
    fetchLiveAstrology();
  };

  const activeData = isLiveMode ? liveData : customData;
  // Every block of a snapshot is computed; the backend marks placeholders decorative.
  const kindOf = (block: string): Provenance => fieldProvenance(activeData?.provenance, block, 'computed');

  const rankedAspects = sortAspectsByExactness(activeData?.western?.aspects).slice(0, 8);
  const reading = skyReadingLine(activeData?.western, activeData?.moon_phase);
  const dominantElement = activeData?.western?.dominant_element;
  const place = activeData?.location;

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 bg-transparent space-y-6">
      
      {/* Top Banner Header */}
      <div className="bg-gradient-to-r from-indigo-900/30 via-purple-900/30 to-cyan-900/30 rounded-xl p-5 border border-purple-500/20 relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIyMCIgY3k9IjIwIiByPSIxIiBmaWxsPSJyZ2JhKDE2OCw4NSwyNDcsMC4xKSIvPjwvc3ZnPg==')] opacity-30" />
        <div className="relative flex flex-col gap-4">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center shadow-[0_0_20px_rgba(34,211,238,0.3)]">
              <Compass className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-wide">Cosmic Clockwork</h2>
              <p className="text-xs text-gray-400">Tropical · Sidereal · BaZi — Swiss Ephemeris v2.10</p>
              {saka?.saka_dawa_duchen && (
                <p className="text-[11px] text-amber-300/80 mt-1" data-testid="cosmic-clock-saka">
                  Next Saka Dawa Duchen {saka.saka_dawa_duchen}
                  {saka.days_until_duchen != null ? ` · ${saka.days_until_duchen} days` : ''}
                  {saka.is_saka_dawa ? ' · holy month' : ''}
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            {isLiveMode ? (
              <Tag color="green" className="font-mono text-[10px] mr-0">LIVE SKY</Tag>
            ) : (
              <Button size="small" onClick={handleResetToLive}>
                Back to live sky
              </Button>
            )}
            <Button
              size="small"
              type="primary"
              loading={sealingHour}
              onClick={handleBeginWorkingFromHour}
              style={{ fontSize: 10 }}
              data-testid="begin-working-from-hour"
            >
              Begin working from this hour
            </Button>
            <Button
              size="small"
              icon={<Copy className="w-3 h-3" />}
              onClick={handleCopyForLLM}
            >
              Copy for LLM
            </Button>
            <span
              className="inline-flex items-center gap-1.5 text-[10px] font-mono text-slate-300 select-none"
              title="When ON, personal info (name, birth time, exact location) is stripped before copying."
            >
              <Switch
                size="small"
                checked={stripPii}
                onChange={(v) => { setStripPii(v); audioFeedback.playClick(); }}
              />
              <span>Strip personal data</span>
            </span>
            <Button
              size="small"
              shape="circle"
              type="text"
              aria-label="Refresh chart"
              onClick={() => isLiveMode ? fetchLiveAstrology(true) : (activeChart ? loadNatalChart(activeChart) : fetchLiveAstrology(true))}
              icon={<RefreshCw className={loading ? 'animate-spin' : ''} />}
            />
          </div>
          </div>
          <Segmented
            size="small"
            value={activeSystem}
            onChange={(val) => { audioFeedback.playClick(); setActiveSystem(String(val)); }}
            options={[
              { value: 'all', label: 'All systems' },
              { value: 'western', label: 'Western' },
              { value: 'vedic', label: 'Vedic' },
              { value: 'chinese', label: 'Chinese' },
            ]}
          />
        </div>
      </div>

      <div className="flex flex-col xl:flex-row gap-6 items-start">
        {/* Left Side: Saved Database profiles panel */}
        <div className="w-full xl:w-[320px] flex-shrink-0">
          <SavedChartsDrawer
            charts={charts}
            onLoadNatal={loadNatalChart}
            onSelectTransit={(c) => { setTransitChart(c); setActiveTab('transits'); audioFeedback.playSuccess(); }}
            onSetSubjectA={setSubjectA}
            onSetSubjectB={setSubjectB}
            onEdit={setEditingChart}
            onDelete={handleDeleteChart}
            onExport={handleExportCharts}
            onImport={handleImportCharts}
            subjectA={subjectA}
            subjectB={subjectB}
            activeChartId={activeChart?.id}
          />
        </div>

        {/* Right Side: Main display container */}
        <div className="flex-1 w-full space-y-6">
          {/* Main Navigation tabs */}
          <div className="max-w-full overflow-x-auto">
            <Segmented
              options={[
                { value: 'wheel', label: 'Celestial Positions' },
                { value: 'dome', label: 'Night-Sky Dome' },
                { value: 'timing', label: 'Auspicious Timing' },
                { value: 'transits', label: 'Transit-to-Natal' },
                { value: 'synastry', label: 'Synastry (Compatibility)' },
                { value: 'techniques', label: 'Techniques' },
                { value: 'extraction', label: 'Extraction' }
              ]}
              value={activeTab}
              onChange={(val) => { audioFeedback.playTabChange(); setActiveTab(val); }}
              className="bg-black/40 border border-white/5 p-1 text-xs"
              style={{ width: 'max-content' }}
            />
          </div>

          {activeTab === 'wheel' && (
            <Space orientation="vertical" size={24} style={{ width: '100%' }}>
              {/* Form Input + Overview Card */}
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={10}>
                  <NatalCalculator
                    onSubmit={handleCalculateSubmit}
                    loading={loading}
                    loadingStatus={loadingStatus}
                    editingChart={editingChart}
                    onCancelEdit={() => setEditingChart(null)}
                  />
                </Col>
                
                <Col xs={24} lg={14}>
                  <Card className="bg-gray-900/80 border-purple-500/20" styles={{ body: { padding: '20px' } }}>
                    <Row justify="space-between" align="top" style={{ marginBottom: 16 }}>
                      <Col>
                        <Tag color="purple" className="font-mono text-[9px]">
                          {isLiveMode ? 'LIVE SKY' : `NATAL: ${activeChart ? activeChart.name : 'CUSTOM'}`}
                        </Tag>
                      </Col>
                      <Col>
                        <Space size={8} align="center">
                          <span className="text-[10px] text-gray-500 font-mono">COORD: GEOCENTRIC</span>
                        </Space>
                      </Col>
                    </Row>
                    
                    <h3 className="text-xl font-bold text-white tracking-wide font-mono mb-1">
                      {isLiveMode ? 'Live celestial clockwork' : `Natal details: ${activeChart ? activeChart.name : 'Custom'}`}
                    </h3>
                    <p className="text-xs text-gray-400 font-mono mb-1">
                      Date & Time: {activeData?.datetime ? new Date(activeData.datetime).toLocaleString() : (skyError ? 'Unavailable' : 'Loading…')}
                    </p>
                    {place && Number.isFinite(Number(place.latitude)) && Number.isFinite(Number(place.longitude)) && (
                      <p className="text-[11px] text-gray-500 font-mono mb-1">
                        Place: {Number(place.latitude).toFixed(2)}, {Number(place.longitude).toFixed(2)}
                        {isLiveMode
                          ? (placeSource === 'device' ? ' · this device' : ' · default coordinates')
                          : (activeChart?.city ? ` · ${activeChart.city}` : '')}
                      </p>
                    )}
                    <p className="text-xs text-amber-200/90 font-mono mb-4" data-testid="sky-reading">
                      {reading || 'Waiting for the ephemeris.'}
                    </p>
                    
                    <Row gutter={[12, 12]}>
                      <Col xs={12} sm={6}>
                        <Card size="small" className="bg-gray-800/60 border-white/5" styles={{ body: { padding: '10px' } }}>
                          <span className="text-[9px] text-gray-500 font-mono block">PLANETARY HOUR</span>
                          <Reading
                            value={activeData?.planetary_hours?.current_planetary_hour || '—'}
                            provenance={kindOf('planetary_hours')}
                            className="mt-1 flex items-baseline gap-1"
                            valueClassName="text-sm font-bold text-yellow-400"
                          />
                        </Card>
                      </Col>
                      <Col xs={12} sm={6}>
                        <Card size="small" className="bg-gray-800/60 border-white/5" styles={{ body: { padding: '10px' } }}>
                          <span className="text-[9px] text-gray-500 font-mono block">VEDIC TITHI</span>
                          <Reading
                            value={activeData?.indian?.panchanga?.tithi?.name || '—'}
                            provenance={kindOf('indian')}
                            className="mt-1 flex items-baseline gap-1"
                            valueClassName="text-sm font-bold text-purple-400"
                          />
                        </Card>
                      </Col>
                      <Col xs={12} sm={6}>
                        <Card size="small" className="bg-gray-800/60 border-white/5" styles={{ body: { padding: '10px' } }}>
                          <span className="text-[9px] text-gray-500 font-mono block">BAZI YEAR PILLAR</span>
                          <Reading
                            value={activeData?.chinese?.bazi?.year?.split(' ')[0] || '—'}
                            provenance={kindOf('chinese')}
                            className="mt-1 flex items-baseline gap-1"
                            valueClassName="text-sm font-bold text-emerald-400"
                          />
                        </Card>
                      </Col>
                      <Col xs={12} sm={6}>
                        <Card size="small" className="bg-gray-800/60 border-white/5" styles={{ body: { padding: '10px' } }}>
                          <span className="text-[9px] text-gray-500 font-mono block">MOON ILLUMINATION</span>
                          <Reading
                            value={formatMoonIllumination(activeData?.moon_phase?.illumination)}
                            provenance={kindOf('moon_phase')}
                            className="mt-1 flex items-baseline gap-1"
                            valueClassName="text-sm font-bold text-cyan-400"
                          />
                        </Card>
                      </Col>
                    </Row>
                    
                    {activeChart && activeChart.notes && (
                      <div className="mt-4 p-3 bg-white/3 border border-white/5 rounded-xl">
                        <span className="text-[9px] text-gray-500 font-mono block uppercase font-bold">Notes</span>
                        <p className="text-xs text-gray-400 mb-0 mt-0.5">{activeChart.notes}</p>
                      </div>
                    )}
                  </Card>
                </Col>
              </Row>

              {activeData ? (
                <div className="space-y-6">
                  {/* Western astrology layout */}
                  {(activeSystem === 'all' || activeSystem === 'western') && (
                    <Card
                      title={<span className="text-cyan-400 font-mono text-xs tracking-wider uppercase"><Sun className="w-4 h-4 inline mr-2" />{isLiveMode ? 'I. Western Tropical — Live Sky' : 'I. Western Tropical — Natal'}</span>}
                      extra={<Tag color="purple" className="font-mono text-[9px]">TROPICAL / PLACIDUS HOUSES</Tag>}
                      className="bg-gray-900/80 border-purple-500/20"
                      styles={{ body: { padding: '20px' } }}
                    >
                      <Row gutter={[16, 16]}>
                        <Col xs={24} md={8}>
                          <Card size="small" className="bg-purple-950/20 border-purple-500/20" styles={{ body: { padding: '12px' } }}>
                            <span className="text-[8px] font-mono text-amber-400 block">SUN SIGN</span>
                            <div className="text-base font-bold text-white mt-1">{activeData.western?.positions?.sun?.sign || 'Unknown'}</div>
                            <Reading
                              value={`${activeData.western?.positions?.sun?.degree?.toFixed(2) ?? '—'}° · H${activeData.western?.positions?.sun?.house || '?'}`}
                              provenance={kindOf('western')}
                              valueClassName="text-[10px] text-gray-400 font-mono"
                            />
                          </Card>
                        </Col>
                        <Col xs={24} md={8}>
                          <Card size="small" className="bg-purple-950/20 border-purple-500/20" styles={{ body: { padding: '12px' } }}>
                            <span className="text-[8px] font-mono text-blue-300 block">MOON SIGN</span>
                            <div className="text-base font-bold text-white mt-1">{activeData.western?.positions?.moon?.sign || 'Unknown'}</div>
                            <Reading
                              value={`${activeData.western?.positions?.moon?.degree?.toFixed(2) ?? '—'}° · H${activeData.western?.positions?.moon?.house || '?'}`}
                              provenance={kindOf('western')}
                              valueClassName="text-[10px] text-gray-400 font-mono"
                            />
                          </Card>
                        </Col>
                        <Col xs={24} md={8}>
                          <Card size="small" className="bg-purple-950/20 border-purple-500/20" styles={{ body: { padding: '12px' } }}>
                            <span className="text-[8px] font-mono text-cyan-400 block">ASCENDANT</span>
                            <div className="text-base font-bold text-white mt-1">{activeData.western?.positions?.ascendant?.sign || 'Unknown'}</div>
                            <Reading
                              value={`${activeData.western?.positions?.ascendant?.degree?.toFixed(2) ?? '—'}° · H1 Cusp`}
                              provenance={kindOf('western')}
                              valueClassName="text-[10px] text-gray-400 font-mono"
                            />
                          </Card>
                        </Col>
                      </Row>

                      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
                        <Col xs={24} xl={10}>
                          <NatalChartWheel
                            data={activeData}
                            name={isLiveMode ? 'Live sky' : (activeChart?.name || 'Chart')}
                            heading={isLiveMode ? 'Tropical wheel' : 'Natal chart wheel'}
                          />
                        </Col>
                        <Col xs={24} xl={7}>
                          <div className="space-y-4 font-mono">
                            <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase mb-0">PLANETARY COORDINATES</h4>
                            <div className="grid grid-cols-1 gap-1.5 max-h-[300px] overflow-y-auto pr-1">
                              {Object.entries(activeData.western?.positions || {}).map(([planet, pos]) => {
                                const isRetrograde = pos?.retrograde;
                                return (
                                  <div key={planet} className="flex items-center justify-between px-2.5 py-2 bg-white/3 hover:bg-white/8 rounded-md text-[11px] border border-white/5">
                                    <Space size={8}>
                                      <span className="font-semibold capitalize text-slate-300">{planet.replace('_',' ')}</span>
                                      {isRetrograde && <Tag color="red" className="text-[8px] leading-none">℞</Tag>}
                                    </Space>
                                    <Space size={4}>
                                      <Reading value={pos.formatted} provenance={kindOf('western')} valueClassName="text-slate-200" />
                                      {pos.house && <Tag className="text-[8px] font-mono" color="purple">H{pos.house}</Tag>}
                                    </Space>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </Col>
                        <Col xs={24} xl={7}>
                          <div className="space-y-4 font-mono">
                            <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase">ELEMENTS & TIGHTEST ASPECTS</h4>
                            <div className="grid grid-cols-4 gap-2 text-center text-xs bg-black/45 p-3 rounded-xl border border-white/5">
                              {Object.entries(activeData.western?.elements || {}).map(([elem, weight]) => {
                                let color = 'text-gray-400';
                                if (elem === 'Fire') color = 'text-rose-400';
                                else if (elem === 'Earth') color = 'text-amber-400';
                                else if (elem === 'Air') color = 'text-sky-400';
                                else if (elem === 'Water') color = 'text-emerald-400';
                                const dominant = elem === dominantElement;
                                return (
                                  <div key={elem} className={dominant ? 'ring-1 ring-white/25 rounded-md' : ''}>
                                    <span className="text-[9px] text-gray-500 font-mono block leading-none">{elem.toUpperCase()}</span>
                                    <Reading
                                      value={weight}
                                      unit=" pts"
                                      provenance={kindOf('western')}
                                      className="mt-1.5 flex items-baseline justify-center gap-1"
                                      valueClassName={`font-bold ${color}`}
                                    />
                                  </div>
                                );
                              })}
                            </div>
                            <div className="bg-black/45 border border-white/5 rounded-xl p-3 max-h-[240px] overflow-y-auto space-y-2">
                              <span className="text-[9px] text-gray-500 font-mono block mb-1">TIGHTEST ASPECTS</span>
                              {rankedAspects.length > 0 ? (
                                rankedAspects.map((asp, idx) => {
                                  const exact = Number(asp.exactness);
                                  const pct = Number.isFinite(exact) ? `${Math.round(exact * 100)}%` : '';
                                  const label = asp.description || `${asp.planet1 || ''} ${asp.aspect || ''} ${asp.planet2 || ''}`.trim();
                                  return (
                                    <div key={`${asp.planet1}-${asp.planet2}-${idx}`} className="flex justify-between items-center gap-2 text-[10px] p-2 bg-white/5 border border-white/5 rounded-lg">
                                      <span className="font-medium text-gray-300">{label}</span>
                                      <Space size={4}>
                                        {pct && <span className="text-gray-500 font-mono">{pct}</span>}
                                        <Tag color={asp.aspect === 'Conjunction' || asp.aspect === 'Trine' || asp.aspect === 'Sextile' ? 'blue' : 'red'} className="font-mono text-[8px]">
                                          {asp.aspect}
                                        </Tag>
                                      </Space>
                                    </div>
                                  );
                                })
                              ) : (
                                <div className="text-xs text-gray-500 italic py-2 text-center">No active aspects in orb</div>
                              )}
                            </div>
                          </div>
                        </Col>
                      </Row>

                      {activeData?.planetary_positions && (
                        <div style={{ marginTop: 20 }}>
                          <Suspense fallback={<div className="text-center text-xs text-gray-500 py-8">Loading aspect chart…</div>}>
                            <AspectChart positions={activeData.planetary_positions} size={400} />
                          </Suspense>
                        </div>
                      )}
                    </Card>
                  )}

                  {/* Vedic Astrology layout */}
                  {(activeSystem === 'all' || activeSystem === 'vedic') && (
                    <VedicPanchanga indianData={activeData.indian} provenance={kindOf('indian')} />
                  )}

                  {/* 3D Sacred Mandala planetary visualizer (lazy-loaded) */}
                  {(activeSystem === 'all' || activeSystem === 'western') && (
                    <Card
                      title={<span className="text-purple-400 font-mono text-xs tracking-wider uppercase">🌀 Sacred Mandala — Planetary Resonance Field</span>}
                      className="bg-gray-900/80 border-purple-500/20"
                      styles={{ body: { padding: '0', height: 'min(60vh, 480px)' } }}
                    >
                      <ErrorBoundary fallbackTitle="3D mandala failed to load">
                        <Suspense fallback={
                          <div className="flex items-center justify-center h-full text-xs text-gray-500 italic animate-pulse">
                            Loading 3D mandala…
                          </div>
                        }>
                          <LazySacredMandala isPlaying={isPlaying} frequency={frequency} />
                        </Suspense>
                      </ErrorBoundary>
                    </Card>
                  )}

                  {/* Chinese Astrology layout */}
                  {(activeSystem === 'all' || activeSystem === 'chinese') && (
                    <ChineseBaZi chineseData={activeData.chinese} provenance={kindOf('chinese')} />
                  )}
                </div>
              ) : (
                <div className="bg-gray-900/60 p-8 border border-white/5 rounded-xl text-center text-gray-400 font-mono text-xs" data-testid="sky-status">
                  {skyError || 'Computing ephemeris coordinates…'}
                </div>
              )}
            </Space>
          )}

          {activeTab === 'dome' && (
            <div key="dome" className="animate-slide-up">
              <ErrorBoundary fallbackTitle="Celestial night-sky dome failed to load">
                <Suspense fallback={<LazyFallback />}>
                  <CelestialSkyDome />
                </Suspense>
              </ErrorBoundary>
            </div>
          )}

          {activeTab === 'timing' && (
            <div key="timing" className="animate-slide-up">
              <ErrorBoundary fallbackTitle="Auspicious timing wheel failed to load">
                <Suspense fallback={<LazyFallback />}>
                  <AuspiciousTimingWheel />
                </Suspense>
              </ErrorBoundary>
            </div>
          )}

          {activeTab === 'transits' && (
            <div key="transits" className="animate-slide-up">
              <ErrorBoundary fallbackTitle="Transit comparison failed to load">
                <Suspense fallback={<LazyFallback />}>
                  <TransitComparison chart={transitChart || activeChart} />
                </Suspense>
              </ErrorBoundary>
            </div>
          )}

          {activeTab === 'synastry' && (
            <div key="synastry" className="animate-slide-up">
              <ErrorBoundary fallbackTitle="Synastry viewer failed to load">
                <Suspense fallback={<LazyFallback />}>
                  <SynastryViewer 
                    charts={charts} 
                    subjectA={subjectA} 
                    subjectB={subjectB} 
                    onSetSubjectA={(c) => setSubjectA(findChart(c?.id))}
                    onSetSubjectB={(c) => setSubjectB(findChart(c?.id))}
                  />
                </Suspense>
              </ErrorBoundary>
            </div>
          )}

          {activeTab === 'techniques' && (
            <div key="techniques" className="animate-slide-up">
              <ErrorBoundary fallbackTitle="Astrology techniques failed to load">
                <Suspense fallback={<LazyFallback />}>
                  <AdvancedAstrologyPanel activeChart={activeChart} />
                </Suspense>
              </ErrorBoundary>
            </div>
          )}

          {activeTab === 'extraction' && (
            <div key="extraction" className="animate-slide-up">
              <Suspense fallback={<LazyFallback />}>
                <LazyAstrologyExtractionPanel />
              </Suspense>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
