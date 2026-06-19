/**
 * AstrologyExtractionPanel — Sweep extraction configuration UI.
 * Tabs: Setup, Sweep, Results, Replay. Only the Setup tab is implemented
 * in this revision; the remaining tabs are placeholders.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Tabs,
  Card,
  Form,
  Select,
  Radio,
  Checkbox,
  InputNumber,
  DatePicker,
  Switch,
  Space,
  Typography,
  Alert,
  Spin,
  Empty,
  Table,
  Popconfirm,
  Tag,
  Button,
  Dropdown,
  message,
  Progress,
  Statistic,
} from 'antd';
import { Copy, Download, Compass, MapPin, Calendar, Sparkles, Settings2 } from 'lucide-react';
const { TabPane } = Tabs;
const { Text } = Typography;

// 11 supported astrological systems with human-friendly labels
const SYSTEM_OPTIONS = [
  { value: 'western', label: 'Western (Tropical)' },
  { value: 'vedic', label: 'Vedic (Jyotish)' },
  { value: 'chinese', label: 'Chinese (Ba Zi)' },
  { value: 'lots', label: 'Lots (Arabic Parts)' },
  { value: 'midpoints', label: 'Midpoints' },
  { value: 'fixed_stars', label: 'Fixed Stars' },
  { value: 'progressions', label: 'Secondary Progressions' },
  { value: 'returns', label: 'Planetary Returns' },
  { value: 'directions', label: 'Primary Directions' },
  { value: 'year_ahead', label: 'Year Ahead (Solar Arc)' },
  { value: 'astrocartography', label: 'Astrocartography' },
];

const HOUSE_SYSTEM_OPTIONS = [
  { value: 'placidus', label: 'Placidus' },
  { value: 'whole_sign', label: 'Whole Sign' },
  { value: 'equal', label: 'Equal' },
  { value: 'koch', label: 'Koch' },
  { value: 'porphyry', label: 'Porphyry' },
];

const DATE_MODES = [
  { value: 'explicit', label: 'Explicit Dates' },
  { value: 'every_n_days', label: 'Every N Days' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'astro_events', label: 'Astronomical Events' },
];

function ReplayTab({ onView, onRecompute }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const r = await fetch(`/api/v1/astrology/runs`);
      if (r.ok) setRuns(await r.json());
    } catch (e) {
      message.error('Failed to load runs: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRuns(); }, []);

  const handleDelete = async (id) => {
    try {
      const r = await fetch(`/api/v1/astrology/runs/${id}`, { method: 'DELETE' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      message.success(`Run ${id} deleted`);
      fetchRuns();
    } catch (e) {
      message.error('Delete failed: ' + e.message);
    }
  };

  const handleRecompute = async (id) => {
    try {
      const r = await fetch(`/api/v1/astrology/runs/${id}/recompute`, { method: 'POST' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      message.success(`Recompute started: run ${data.run_id}`);
      if (onRecompute) onRecompute(data.run_id);
      fetchRuns();
    } catch (e) {
      message.error('Recompute failed: ' + e.message);
    }
  };

  const handleExport = (id, fmt) => {
    const a = document.createElement('a');
    a.href = `/api/v1/astrology/runs/${id}/results/export?fmt=${fmt}`;
    a.download = `run-${id}.${fmt}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Created', dataIndex: 'created_at', key: 'created_at' },
    { title: 'Total', dataIndex: 'total_tuples', key: 'total_tuples', width: 80 },
    { title: 'Completed', dataIndex: 'completed_tuples', key: 'completed_tuples', width: 100 },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s) => <Tag color={s === 'done' ? 'green' : s === 'error' ? 'red' : s === 'partial' ? 'orange' : 'blue'}>{s}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Button size="small" onClick={() => onView && onView(record.id)}>View</Button>
          <Button size="small" type="primary" onClick={() => handleRecompute(record.id)}>Recompute</Button>
          <Popconfirm title="Delete this run?" onConfirm={() => handleDelete(record.id)} okText="Delete" okButtonProps={{ danger: true }}>
            <Button size="small" danger>Delete</Button>
          </Popconfirm>
          <Button size="small" onClick={() => handleExport(record.id, 'jsonl')}>Export</Button>
        </Space>
      ),
    },
  ];

  return (
    <Table
      dataSource={runs}
      columns={columns}
      rowKey="id"
      loading={loading}
      pagination={{ pageSize: 20 }}
      size="small"
    />
  );
}

function ResultsTab({ currentRunId }) {
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(null);

  useEffect(() => {
    if (!currentRunId) return;
    setLoading(true);
    setError(null);
    fetch(`/api/v1/astrology/runs/${currentRunId}/results?format=markdown`)
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setMarkdown)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [currentRunId]);

  const handleCopy = async (fmt) => {
    try {
      let text;
      if (fmt === 'markdown') {
        text = markdown;
      } else {
        const r = await fetch(`/api/v1/astrology/runs/${currentRunId}/results?format=json`);
        text = await r.text();
      }
      await navigator.clipboard.writeText(text);
      setCopied(fmt);
      message.success(`${fmt === 'markdown' ? 'Markdown' : 'JSON'} copied to clipboard`);
      setTimeout(() => setCopied(null), 2000);
    } catch (e) {
      message.error('Copy failed: ' + e.message);
    }
  };

  const handleDownload = (fmt) => {
    const a = document.createElement('a');
    a.href = `/api/v1/astrology/runs/${currentRunId}/results/export?fmt=${fmt}`;
    a.download = `run-${currentRunId}.${fmt}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <Space direction="vertical" className="w-full" size="middle">
      {!currentRunId && <Empty description="No run selected. Launch a sweep first." />}
      {loading && <Spin tip="Loading results..." />}
      {error && <Alert type="error" message={error} showIcon />}
      {currentRunId && !loading && !error && (
        <Card
          title={`Run ${currentRunId} Results`}
          extra={
            <Space>
              <Button icon={<Copy />} onClick={() => handleCopy('markdown')}>
                {copied === 'markdown' ? 'Copied!' : 'Copy MD'}
              </Button>
              <Button icon={<Copy />} onClick={() => handleCopy('json')}>
                {copied === 'json' ? 'Copied!' : 'Copy JSON'}
              </Button>
              <Dropdown
                menu={{
                  items: [
                    { key: 'jsonl', label: 'JSONL', onClick: () => handleDownload('jsonl') },
                    { key: 'csv', label: 'CSV', onClick: () => handleDownload('csv') },
                    { key: 'md', label: 'Markdown', onClick: () => handleDownload('md') },
                  ],
                }}
              >
                <Button icon={<Download />}>Download</Button>
              </Dropdown>
            </Space>
          }
        >
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 12, maxHeight: 600, overflow: 'auto' }}>
            {markdown}
          </pre>
        </Card>
      )}
    </Space>
  );
}

const SweepTab = ({ setupState, onComplete }) => {
  const [currentRunId, setCurrentRunId] = useState(null);
  const [runStatus, setRunStatus] = useState(null);
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  const [elapsed, setElapsed] = useState(0);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);
  const startTimeRef = useRef(null);

  const handleLaunch = async () => {
    if (!setupState) return;
    setLaunching(true);
    setError(null);
    setElapsed(0);
    startTimeRef.current = Date.now();
    try {
      const tuples = (setupState.tuples || []).map((t) => ({
        date_iso: t.date,
        lat: t.lat,
        lon: t.lon,
      }));
      const r = await fetch(`/api/v1/astrology/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tuples,
          config: {
            systems: setupState.systems || ['western'],
            house_system: setupState.houseSystem || 'Placidus',
            sidereal: setupState.sidereal || false,
          },
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setCurrentRunId(data.run_id);
    } catch (e) {
      setError(e.message);
    } finally {
      setLaunching(false);
    }
  };

  useEffect(() => {
    if (!currentRunId) return;
    const elapsedInterval = setInterval(() => {
      if (startTimeRef.current) {
        setElapsed(Math.round((Date.now() - startTimeRef.current) / 1000));
      }
    }, 1000);
    const poll = async () => {
      try {
        const r = await fetch(`/api/v1/astrology/runs/${currentRunId}`);
        if (r.ok) {
          const data = await r.json();
          setRunStatus(data.status);
          setProgress({
            completed: data.completed_tuples || 0,
            total: data.total_tuples || 0,
          });
          if (['done', 'partial', 'error'].includes(data.status)) {
            clearInterval(pollRef.current);
            clearInterval(elapsedInterval);
            if (onComplete) onComplete(currentRunId);
          }
        }
      } catch {}
    };
    pollRef.current = setInterval(poll, 2000);
    poll();
    return () => {
      clearInterval(pollRef.current);
      clearInterval(elapsedInterval);
    };
  }, [currentRunId, onComplete]);

  const pct = progress.total
    ? Math.round((progress.completed / progress.total) * 100)
    : 0;

  const progressStatus =
    runStatus === 'error'
      ? 'exception'
      : runStatus === 'done' || runStatus === 'partial'
        ? 'success'
        : 'active';

  return (
    <Space direction="vertical" className="w-full" size="middle">
      <Card>
        <Space direction="vertical" className="w-full">
          <Space size="large" wrap>
            <Statistic title="Run ID" value={currentRunId || '—'} />
            <Statistic title="Status" value={runStatus || 'idle'} />
            <Statistic title="Elapsed" value={`${elapsed}s`} />
            <Statistic
              title="Tuples"
              value={`${progress.completed} / ${progress.total || '?'}`}
            />
          </Space>
          <Progress percent={pct} status={progressStatus} />
          <Button
            type="primary"
            size="large"
            onClick={handleLaunch}
            loading={launching}
            disabled={
              !setupState ||
              !setupState.tuples ||
              setupState.tuples.length === 0 ||
              currentRunId !== null
            }
          >
            Launch Sweep
          </Button>
          {error && <Alert type="error" message={error} />}
        </Space>
      </Card>
    </Space>
  );
};

const AstrologyExtractionPanel = () => {
  const [locations, setLocations] = useState([]);
  const [locationsLoading, setLocationsLoading] = useState(false);
  const [locationsError, setLocationsError] = useState(null);
  const [selectedLocations, setSelectedLocations] = useState([]);

  const [dateMode, setDateMode] = useState('explicit');
  const [explicitDates, setExplicitDates] = useState([]);
  const [everyNDays, setEveryNDays] = useState(7);
  const [weeklyWeekday, setWeeklyWeekday] = useState(0); // 0 = Sunday
  const [astroEvents, setAstroEvents] = useState([]);

  const [systems, setSystems] = useState(['western', 'vedic', 'chinese']);
  const [houseSystem, setHouseSystem] = useState('placidus');
  const [sidereal, setSidereal] = useState(false);

  const [currentRunId, setCurrentRunId] = useState(null);

  // Fetch available locations on mount
  useEffect(() => {
    let cancelled = false;
    const fetchLocations = async () => {
      setLocationsLoading(true);
      setLocationsError(null);
      try {
        const res = await fetch(`/api/v1/astrology/locations`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          const list = Array.isArray(data)
            ? data
            : Array.isArray(data?.locations)
              ? data.locations
              : [];
          setLocations(list);
        }
      } catch (err) {
        if (!cancelled) {
          setLocationsError(err?.message || 'Failed to load locations');
        }
      } finally {
        if (!cancelled) {
          setLocationsLoading(false);
        }
      }
    };
    fetchLocations();
    return () => {
      cancelled = true;
    };
  }, []);

  const locationOptions = useMemo(
    () =>
      locations.map((loc) => ({
        value: loc.id ?? loc.name,
        label: loc.name || loc.label || String(loc.id),
      })),
    [locations],
  );

  const setupState = useMemo(() => {
    const selectedLocs = selectedLocations
      .map((id) => locations.find((l) => (l.id ?? l.name) === id))
      .filter(Boolean);
    const dates = [];
    if (dateMode === 'explicit' && explicitDates && explicitDates.length) {
      explicitDates.forEach((d) => {
        const dt = d && (d.$d || d);
        if (dt && !Number.isNaN(dt.getTime?.())) {
          dates.push(new Date(dt).toISOString());
        }
      });
    } else if (dateMode === 'every_n_days' && everyNDays > 0) {
      const start = new Date();
      for (let i = 0; i < everyNDays; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + i * everyNDays);
        dates.push(d.toISOString());
      }
    } else if (dateMode === 'weekly') {
      const start = new Date();
      for (let i = 0; i < 4; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + ((weeklyWeekday - start.getDay() + 7) % 7) + i * 7);
        dates.push(d.toISOString());
      }
    }
    const tuples = [];
    selectedLocs.forEach((loc) => {
      if (typeof loc.lat !== 'number' || typeof loc.lon !== 'number') return;
      dates.forEach((iso) => {
        tuples.push({ date: iso, lat: loc.lat, lon: loc.lon });
      });
    });
    return {
      tuples,
      systems,
      houseSystem,
      sidereal,
      dateMode,
      selectedLocations,
    };
  }, [locations, selectedLocations, dateMode, explicitDates, everyNDays, weeklyWeekday, systems, houseSystem, sidereal]);

  const handleSweepComplete = (runId) => {
    if (runId) {
      setCurrentRunId(runId);
    }
  };

  const renderDateModeSubInputs = () => {
    if (dateMode === 'explicit') {
      return (
        <Form.Item label="Pick specific dates" style={{ marginTop: 12 }}>
          <DatePicker.RangePicker
            multiple
            value={explicitDates}
            onChange={(vals) => setExplicitDates(vals || [])}
            style={{ width: '100%' }}
          />
        </Form.Item>
      );
    }
    if (dateMode === 'every_n_days') {
      return (
        <Form.Item label="Step (days)" style={{ marginTop: 12 }}>
          <InputNumber
            min={1}
            max={365}
            value={everyNDays}
            onChange={(v) => setEveryNDays(v ?? 1)}
          />
        </Form.Item>
      );
    }
    if (dateMode === 'weekly') {
      return (
        <Form.Item label="Day of the week" style={{ marginTop: 12 }}>
          <Select
            value={weeklyWeekday}
            onChange={setWeeklyWeekday}
            style={{ width: 180 }}
            options={[
              { value: 0, label: 'Sunday' },
              { value: 1, label: 'Monday' },
              { value: 2, label: 'Tuesday' },
              { value: 3, label: 'Wednesday' },
              { value: 4, label: 'Thursday' },
              { value: 5, label: 'Friday' },
              { value: 6, label: 'Saturday' },
            ]}
          />
        </Form.Item>
      );
    }
    if (dateMode === 'astro_events') {
      return (
        <Form.Item label="Astronomical event types" style={{ marginTop: 12 }}>
          <Checkbox.Group
            value={astroEvents}
            onChange={setAstroEvents}
            options={[
              { value: 'ingress', label: 'Planetary Ingress' },
              { value: 'aspect', label: 'Major Aspect' },
              { value: 'lunar_phase', label: 'Lunar Phase' },
              { value: 'eclipse', label: 'Eclipse' },
              { value: 'retrograde', label: 'Retrograde Station' },
            ]}
          />
        </Form.Item>
      );
    }
    return null;
  };

  const renderSetupTab = () => (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title={
          <Space>
            <MapPin size={16} />
            <span>Locations</span>
          </Space>
        }
        size="small"
      >
        {locationsError ? (
          <Alert
            type="error"
            showIcon
            message="Could not load locations"
            description={locationsError}
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Select
          mode="multiple"
          allowClear
          style={{ width: '100%' }}
          placeholder={
            locationsLoading ? 'Loading locations…' : 'Select one or more locations'
          }
          value={selectedLocations}
          onChange={setSelectedLocations}
          options={locationOptions}
          notFoundContent={
            locationsLoading ? <Spin size="small" /> : <Empty description="No locations" />
          }
          disabled={locationsLoading}
        />
      </Card>

      <Card
        title={
          <Space>
            <Calendar size={16} />
            <span>Date Grid</span>
          </Space>
        }
        size="small"
      >
        <Radio.Group
          options={DATE_MODES}
          value={dateMode}
          onChange={(e) => setDateMode(e.target.value)}
          optionType="button"
          buttonStyle="solid"
        />
        {renderDateModeSubInputs()}
      </Card>

      <Card
        title={
          <Space>
            <Sparkles size={16} />
            <span>Systems</span>
          </Space>
        }
        size="small"
      >
        <Checkbox.Group
          value={systems}
          onChange={(vals) => setSystems(vals || [])}
          options={SYSTEM_OPTIONS}
        />
      </Card>

      <Card
        title={
          <Space>
            <Settings2 size={16} />
            <span>Chart Options</span>
          </Space>
        }
        size="small"
      >
        <Form layout="vertical">
          <Form.Item label="House system">
            <Select
              value={houseSystem}
              onChange={setHouseSystem}
              options={HOUSE_SYSTEM_OPTIONS}
              style={{ width: 220 }}
            />
          </Form.Item>
          <Form.Item label="Sidereal mode">
            <Space>
              <Switch checked={sidereal} onChange={setSidereal} />
              <Text type="secondary">
                {sidereal ? 'Sidereal (ecliptic, star-anchored)' : 'Tropical (default)'}
              </Text>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );

  const renderPlaceholder = (label) => (
    <div
      style={{
        padding: '48px 16px',
        textAlign: 'center',
        color: 'rgba(255,255,255,0.55)',
      }}
    >
      <Compass size={32} style={{ opacity: 0.4, marginBottom: 12 }} />
      <div>{label} — Coming soon</div>
    </div>
  );

  return (
    <Tabs defaultActiveKey="setup" type="card">
      <TabPane tab="Setup" key="setup">
        {renderSetupTab()}
      </TabPane>
      <TabPane tab="Sweep" key="sweep">
        <SweepTab setupState={setupState} onComplete={handleSweepComplete} />
      </TabPane>
      <TabPane tab="Results" key="results">
        <ResultsTab currentRunId={currentRunId} />
      </TabPane>
      <TabPane tab="Replay" key="replay">
        <ReplayTab />
      </TabPane>
    </Tabs>
  );
};

export default AstrologyExtractionPanel;
