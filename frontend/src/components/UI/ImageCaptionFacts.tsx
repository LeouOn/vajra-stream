/**
 * ImageCaptionFacts — the real values behind an image, shown under it with
 * their provenance ("computed", "record", "drawn").
 *
 * Images never carry numbers (the prompts forbid lettering and numerals, see
 * core/image_prompts.py); this caption is where the moon's illumination, the
 * sealing time or a festival date are read. Renders nothing when there are no
 * facts, so it can sit under any image.
 *
 * @component
 */
import React from 'react';
import ProvenanceTag from './ProvenanceTag';
import { toCaptionFacts } from '../../lib/captionFacts';

interface ImageCaptionFactsProps {
  /** `caption_facts` straight from a payload; it is validated here. */
  facts: unknown;
  className?: string;
}

export default function ImageCaptionFacts({ facts, className = '' }: ImageCaptionFactsProps): React.ReactElement | null {
  const list = toCaptionFacts(facts);
  if (list.length === 0) return null;
  return (
    <dl
      data-testid="image-caption-facts"
      title="Real values, captioned beside the image. The image itself carries no numbers."
      className={`m-0 mt-1 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-[10px] font-mono ${className}`}
    >
      {list.map((fact, i) => (
        <React.Fragment key={`${fact.label}-${i}`}>
          <dt className="text-gray-500">{fact.label}</dt>
          <dd className="m-0 min-w-0 break-words text-gray-300" data-provenance={fact.provenance}>
            {fact.value} <ProvenanceTag kind={fact.provenance} />
          </dd>
        </React.Fragment>
      ))}
    </dl>
  );
}
