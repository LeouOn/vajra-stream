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
 * Layout (W3-M2, measured in a real browser): the card is two columns from 1280 px.
 * LEFT = where and when: the flat strip, the planetary-hour readout under it
 * (it is about the place and the instant, like the strip) and the time
 * controls. RIGHT = the sky: the dome, alone. The dome is the tall element
 * (~600-790 px); strip + readout alone leave ~300 px empty under them at 1440 px,
 * while the controls (~210 px) belong with the place and time anyway, so the
 * two columns end near each other.
 *
 * W3-M5 (measured 2026-10-24 in real Chromium, docs/notes/earthsky/w3-m5/):
 * how near is a property of the SKY, not of this layout. The dome's side
 * panel grows with what is overhead - the planet list is 180..352 px and the
 * nakshatra chip list 76..134 px - and in daylight it also carries the "stars
 * hidden" banner and an extra switch row. So the difference between the two
 * column bottoms was 1..98 px over twelve observer longitudes at one instant
 * (1440 px), 170 px at 1280 px (the dome's 610 px column floor squeezes the
 * left column there) and 99..163 px with seven visible planets. With a fixed
 * night sky (the reference fixture in frontend/e2e/fixtures) it is 53 px at
 * 1440 px. The strict bound is asserted against that
 * fixed sky in frontend/e2e/earth-sky-layout.spec.ts; the live smoke records
 * the live number instead of pretending it is a layout invariant.
 *
 * W3-M4 (measured at 1100 / 1280 / 1366 / 1440 / 1920 / 420 px, docs/notes/earthsky/wave3/c1/card-matrix.mjs):
 * - Equal columns below ~1330 px gave the dome a column too narrow to keep its canvas and side panel side by side
 *   (554 px inside + its own ~50 px of padding), so it stacked and ran 280-460 px taller than the left column.
 *   The dome's column is now never narrower than 610 px; the left column takes what is left, and above ~1330 px
 *   the columns are equal again (1440 px is exactly as before).
 * - Below 1280 px the left column would be under ~500 px, so the card is one column there (an uncapped 2:1 strip
 *   is 480-620 px tall in a single column, hence the strip cap below).
 * - The strip is capped at 720 px (360 px tall) and centred: at 1920 px an 887 px strip made the left column 170 px
 *   taller than the dome. 720 px is wider than the strip is anywhere from 1280 to 1440 px, so those are unchanged.
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

      {/*
        Two columns from 1280 px, one stacked column below it; the DOM order IS the narrow order (no `order-*`).
        The right column is never narrower than 610 px: the dome needs 554 px inside to keep canvas and panel side
        by side. 610 px follows the dome's `flex-[2_1_280px]` / `flex-[1_1_250px]` minimums and its own padding;
        change them together.
      */}
      <div className="grid grid-cols-1 min-[1280px]:grid-cols-[minmax(0,1fr)_minmax(610px,1fr)] gap-4 items-start">
        <div data-testid="earth-sky-left" className="min-w-0 space-y-3">
          <WorldStrip className="mx-auto max-w-[720px]" observer={observer} onPick={onPick} />
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
