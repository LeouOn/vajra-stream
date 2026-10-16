/**
 * Reading — one displayed value with its provenance ("the honest instrument",
 * docs/DEVELOPMENT_ROADMAP.md, Phase 2).
 *
 * Every value the UI shows is a record, computed, a draw or decorative. A
 * Reading renders the value with its `ProvenanceTag`, so the label is the same
 * everywhere. Two rules are structural here rather than left to review:
 *
 * - A draw reads as "drawn" and is never drawn as a meter. `ReadingMeter` (and
 *   `Reading`'s `meter` prop) only accept `record` or `computed` in their
 *   types, and refuse anything else at runtime too (payload labels arrive as
 *   untyped JSON).
 * - Decorative values carry no information, so they get no meter either.
 *
 * Raw bars (`<Progress>`, percentage widths) outside this file are guarded by
 * `src/__tests__/no-draw-meters.test.ts`.
 *
 * @component
 */
import React from 'react';
import type { Provenance } from '../../types/operations';
import ProvenanceTag from './ProvenanceTag';

/** The provenances a bar may represent: a real count or a deterministic value. */
export type MeterProvenance = Extract<Provenance, 'record' | 'computed'>;

/** True when a value of this provenance may be shown as a bar. */
export function isMeterProvenance(kind: unknown): kind is MeterProvenance {
  return kind === 'record' || kind === 'computed';
}

const PROVENANCE_TITLES: Record<Provenance, string> = {
  record: 'A persisted record',
  computed: 'Computed from real inputs',
  draw: 'Drawn at random, read as a divinatory method; not a measurement',
  decorative: 'Decorative; carries no information',
};

interface ReadingMeterProps {
  /** 0–100; clamped. */
  percent: number;
  provenance: MeterProvenance;
  /** Classes for the filled part (color, gradient, transition). */
  fillClassName?: string;
  fillStyle?: React.CSSProperties;
  /** Classes for the track. */
  className?: string;
  /** Accessible name of the bar. */
  label?: string;
}

/**
 * A bar for a record or computed value. It renders nothing for any other
 * provenance, so a draw that reaches it through untyped payload data still
 * never becomes a meter.
 */
export function ReadingMeter({
  percent,
  provenance,
  fillClassName = 'bg-cyan-500',
  fillStyle,
  className = 'h-1.5 bg-gray-800',
  label,
}: ReadingMeterProps): React.ReactElement | null {
  if (!isMeterProvenance(provenance)) return null;
  const pct = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
  return (
    <span
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      data-meter={provenance}
      className={`block w-full overflow-hidden rounded-full ${className}`}
    >
      <span
        className={`block h-full rounded-full ${fillClassName}`}
        style={{ ...fillStyle, width: `${pct}%` }}
      />
    </span>
  );
}

interface ReadingBaseProps {
  /** The value as shown (already formatted). */
  value: React.ReactNode;
  label?: React.ReactNode;
  unit?: React.ReactNode;
  className?: string;
  labelClassName?: string;
  valueClassName?: string;
  /** Hide the tag when a surrounding heading already names the provenance. */
  hideTag?: boolean;
  testId?: string;
}

interface MeterReadingProps extends ReadingBaseProps {
  provenance: MeterProvenance;
  /** Optional bar under the value, 0–100. Only record/computed values may have one. */
  meter?: number;
  meterFillClassName?: string;
  meterFillStyle?: React.CSSProperties;
  meterClassName?: string;
}

interface PlainReadingProps extends ReadingBaseProps {
  provenance: Exclude<Provenance, MeterProvenance>;
  meter?: never;
  meterFillClassName?: never;
  meterFillStyle?: never;
  meterClassName?: never;
}

export type ReadingProps = MeterReadingProps | PlainReadingProps;

/** A labeled value with its provenance tag, and an optional bar for record/computed values. */
export default function Reading(props: ReadingProps): React.ReactElement {
  const {
    value,
    provenance,
    label,
    unit,
    className = 'inline-flex items-baseline gap-1',
    labelClassName = 'text-gray-500',
    valueClassName = '',
    hideTag = false,
    testId,
  } = props;
  const row = (
    <span
      data-reading={provenance}
      data-testid={testId}
      title={PROVENANCE_TITLES[provenance]}
      className={className}
    >
      {/* The ' ' text nodes keep the words apart for copy and screen readers;
          flex layout ignores whitespace-only children, so spacing stays the gap. */}
      {label != null && <span className={labelClassName}>{label}</span>}
      {label != null && ' '}
      <span className="inline-flex items-baseline gap-1">
        <span className={valueClassName}>
          {value}
          {unit}
        </span>
        {!hideTag && ' '}
        {!hideTag && <ProvenanceTag kind={provenance} />}
      </span>
    </span>
  );
  if (props.meter == null || !isMeterProvenance(provenance)) return row;
  return (
    <span className="block space-y-1">
      {row}
      <ReadingMeter
        percent={props.meter}
        provenance={provenance}
        fillClassName={props.meterFillClassName}
        fillStyle={props.meterFillStyle}
        className={props.meterClassName}
        label={typeof label === 'string' ? label : undefined}
      />
    </span>
  );
}
