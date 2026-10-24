/**
 * Earth & Sky card (W3-G) — the flat world strip, the observer's sky dome and
 * the time controls, all wired through `skyStore`.
 *
 * The 3D globe stays where it already is on the Broadcast tab (the full
 * `WorldEmanation` above `BroadcastPanel`); this card deliberately adds no
 * WebGL canvas. It is mounted lazily from `BroadcastPanel` so the strip, the
 * dome and the controls are not in the initial bundle.
 *
 * Picking on the strip sets the shared observer; the dome takes no props and
 * follows the same store; the controls write the shared instant.
 *
 * The caption names the selected MODE only (live, or scrubbed to an instant). It makes no claim that anything
 * was computed: whether the strip, the dome, the readout or the controls have a value, are still loading or are
 * unavailable is each one's own status, and each carries its own provenance. A card-level "computed" would be
 * true only while every child happened to succeed (and the card cannot see the dome's own night-sky status).
 *
 * Layout (W3-M2, measured in a real browser): the card is two columns from lg.
 * LEFT = where and when: the flat strip, the planetary-hour readout under it
 * (it is about the place and the instant, like the strip) and the time
 * controls. RIGHT = the sky: the dome, alone. The dome is the tall element
 * (~760 px); strip + readout alone leave ~300 px empty under them at 1440 px,
 * while the controls (~210 px) belong with the place and time anyway, so the
 * two columns end within ~80 px of each other.
 *
 * On a narrow screen the columns stack in DOM order: strip, readout,
 * controls, dome. The facts come first, and the slider sits right under the
 * two things it moves instead of ~1,000 px below them under the dome. No
 * `order-*` utility is used, so reading order, tab order and visual order are
 * the same on both layouts. The readout is beside the dome, not inside it
 * (the spec words it as "shown on the dome"); it follows the same store and
 * takes no props.
 */
import React, { useCallback, useMemo } from 'react';

import { useSkyStore } from '../../stores/skyStore';
import { WorldStrip } from '../2D/WorldStrip';
import CelestialSkyDome from './CelestialSkyDome';
import PlanetaryHourReadout from './PlanetaryHourReadout';
import SkyTimeControls from './SkyTimeControls';

/** "2026-10-24 09:00:00 UTC" from the store's normalised `...Z` instant (anything else is shown as given). */
function formatUtc(at: string): string {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/.exec(at);
  return match === null ? at : `${match[1]} ${match[2]} UTC`;
}

interface Props {
  className?: string;
}

export default function EarthSkyCard({ className = '' }: Props): React.ReactElement {
  const lat = useSkyStore((state) => state.lat);
  const lng = useSkyStore((state) => state.lng);
  const at = useSkyStore((state) => state.at);
  const scrubbed = at !== null;

  const observer = useMemo(() => ({ lat, lng }), [lat, lng]);
  const onPick = useCallback((pickedLat: number, pickedLng: number) => {
    useSkyStore.getState().setObserver(pickedLat, pickedLng);
  }, []);

  return (
    <section
      data-testid="earth-sky-card"
      aria-label="Earth and Sky"
      className={`bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-4 space-y-4 ${className}`.trim()}
    >
      <header className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h3 className="text-sm font-bold text-white tracking-wider">EARTH &amp; SKY</h3>
        <p data-testid="earth-sky-caption" className="text-[11px] leading-snug text-gray-400">
          {scrubbed ? `Scrubbed to ${formatUtc(at)}.` : 'Live: following the current instant.'}
        </p>
      </header>

      {/* Two columns from lg, one stacked column below it; the DOM order IS the narrow order (no `order-*`). */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <div data-testid="earth-sky-left" className="min-w-0 space-y-3">
          <WorldStrip observer={observer} onPick={onPick} />
          <PlanetaryHourReadout />
          <SkyTimeControls />
        </div>
        <div data-testid="earth-sky-right" className="min-w-0">
          <CelestialSkyDome />
        </div>
      </div>
    </section>
  );
}
