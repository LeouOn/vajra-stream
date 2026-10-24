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
 * The planetary-hour readout (W3-J) sits directly under the dome in the same
 * column: beside it, not inside it (the spec words it as "shown on the dome").
 * It follows the same store and takes no props.
 */
import React, { useCallback, useMemo } from 'react';

import { useSkyStore } from '../../stores/skyStore';
import { WorldStrip } from '../2D/WorldStrip';
import CelestialSkyDome from './CelestialSkyDome';
import PlanetaryHourReadout from './PlanetaryHourReadout';
import SkyTimeControls from './SkyTimeControls';
import ProvenanceTag from './ProvenanceTag';

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
        {/* Same wording as the dome's own scrub banner: one description, not two. */}
        <p
          data-testid="earth-sky-caption"
          className="text-[11px] leading-snug text-gray-400 flex flex-wrap items-center gap-1.5"
        >
          {scrubbed
            ? 'Scrubbed: Sun, Moon, planets, stars: computed for that instant.'
            : 'Live: positions computed for the current instant.'}
          <ProvenanceTag kind="computed" />
        </p>
      </header>

      {/* Strip and dome side by side from lg; stacked on a narrow screen. */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <div className="min-w-0">
          <WorldStrip observer={observer} onPick={onPick} />
        </div>
        <div className="min-w-0 space-y-3">
          <CelestialSkyDome />
          <PlanetaryHourReadout />
        </div>
      </div>

      <SkyTimeControls />
    </section>
  );
}
