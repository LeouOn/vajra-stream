import React from 'react';
import type { Provenance } from '../../types/operations';
import { PROVENANCE_LABELS } from '../../lib/provenance';

interface ProvenanceTagProps {
  kind: Provenance;
  className?: string;
}

/** A small, calm label naming where a value came from (e.g. "drawn"). */
export default function ProvenanceTag({ kind, className = '' }: ProvenanceTagProps) {
  return (
    <span
      data-provenance={kind}
      title={kind === 'draw' ? 'Drawn at random, read as a divinatory method; not a measurement' : undefined}
      className={`inline-block rounded border border-white/10 px-1 text-[8px] font-mono lowercase tracking-wide text-gray-500 ${className}`}
    >
      {PROVENANCE_LABELS[kind]}
    </span>
  );
}
