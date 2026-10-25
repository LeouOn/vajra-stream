/**
 * HomeLocationSettings — where workings are sealed, so each witness shows
 * the true sky from there instead of the default location.
 *
 * Three ways to set it: the browser's geolocation, a typed place name
 * (geocoded on the server) or typed coordinates ("27.7, 85.3"); and Clear.
 * Coordinates are only ever shown rounded to one decimal place.
 */
import React, { useEffect, useState } from 'react';
import { Button, Card, Input, Space, Typography } from 'antd';
import { LocateFixed, MapPin, X } from 'lucide-react';
import {
  clearHomeLocation,
  describeLocation,
  fetchHomeLocation,
  formatCoords,
  parseTypedCoords,
  saveHomeLocation,
  type HomeLocationInput,
  type HomeLocationResponse,
} from '../../lib/homeLocationApi';

const { Text } = Typography;

const SOURCE_WORDS: Record<string, string> = {
  browser: 'from this browser',
  typed: 'typed',
  geocoded: 'looked up',
};

export default function HomeLocationSettings(): React.ReactElement {
  const [state, setState] = useState<HomeLocationResponse | null>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchHomeLocation()
      .then((res) => { if (!cancelled) setState(res); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, []);

  const run = async (action: () => Promise<HomeLocationResponse>) => {
    setBusy(true);
    setError(null);
    try {
      setState(await action());
      setText('');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const saveTyped = () => {
    const typed = text.trim();
    if (!typed) return;
    const coords = parseTypedCoords(typed);
    const input: HomeLocationInput = coords ? { ...coords, source: 'typed' } : { place: typed };
    void run(() => saveHomeLocation(input));
  };

  const useBrowser = () => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setError('This browser cannot share its location.');
      return;
    }
    setBusy(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        void run(() => saveHomeLocation({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          label: text.trim() || null,
          source: 'browser',
        }));
      },
      (err) => {
        setBusy(false);
        setError(err.message || 'Location permission was denied.');
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    );
  };

  const current = state?.location ?? null;
  const fallback = state?.default;

  return (
    <Card size="small" title={<Space size={8}><MapPin className="w-4 h-4" />Home location</Space>}>
      <Space orientation="vertical" size={8} style={{ width: '100%' }}>
        <Text data-testid="home-location-current">
          {current
            ? `${describeLocation(current)} · ${SOURCE_WORDS[current.source] ?? current.source}`
            : `Not set — workings use the default location${fallback ? ` (${formatCoords(fallback.latitude, fallback.longitude)})` : ''}.`}
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          New workings are sealed here, so their witness shows the sky from this place. Captions show only the
          name and coordinates rounded to ~11 km.
        </Text>
        <Space.Compact style={{ width: '100%', maxWidth: 480 }}>
          <Input
            aria-label="Place name or coordinates"
            placeholder="Place name, or 27.7, 85.3"
            value={text}
            maxLength={200}
            onChange={(e) => setText(e.target.value)}
            onPressEnter={saveTyped}
            disabled={busy}
          />
          <Button onClick={saveTyped} disabled={busy || !text.trim()} data-testid="home-location-save">
            Set
          </Button>
        </Space.Compact>
        <Space size={8} wrap>
          <Button
            size="small"
            icon={<LocateFixed className="w-3 h-3" />}
            onClick={useBrowser}
            loading={busy}
            data-testid="home-location-browser"
          >
            Use my location
          </Button>
          <Button
            size="small"
            icon={<X className="w-3 h-3" />}
            onClick={() => { void run(clearHomeLocation); }}
            disabled={busy || !current}
            data-testid="home-location-clear"
          >
            Clear
          </Button>
        </Space>
        {error && <Text type="danger" data-testid="home-location-error">{error}</Text>}
      </Space>
    </Card>
  );
}
