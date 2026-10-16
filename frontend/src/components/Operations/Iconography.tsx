/**
 * Iconography — the curated deity iconography (knowledge/iconography.json) and
 * the thangka reference a user may pin to each deity.
 *
 * Left: every deity the API returns (the screen is generic; it hardcodes no ids).
 * Right: one deity's names, forms, body, hands and attributes, ornaments and
 * sources, plus its pinned reference image.
 *
 * Honesty rules (docs/DEVELOPMENT_ROADMAP.md, "the honest instrument"):
 *   - Every curated value is a `record`; the image-prompt clause built from it
 *     is `computed`.
 *   - A `null` field is one the cited references do not settle. It is shown as
 *     "not established" (it may vary by lineage), never hidden or guessed, and
 *     the entry's and form's notes are shown with it.
 *
 * A pinned reference conditions that deity's witness renders (all its forms;
 * the backend pins per deity). The image is stored on this machine and only
 * the local renderer reads it.
 *
 * @component
 * @route /operations/iconography
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Popconfirm, Radio, message } from 'antd';
import { ImageOff, RefreshCw, Upload } from 'lucide-react';
import ProvenanceTag from '../UI/ProvenanceTag';
import { ErrorState, LoadingState } from '../UI/States';
import { fetchDeities, fetchDeity, pinDeityReference, unpinDeityReference } from '../../lib/iconographyApi';
import { REFERENCE_ACCEPT, referenceImageUrl, uploadReferenceImage, validateReferenceFile } from '../../lib/renderApi';
import { formatDateTime } from '../../lib/operationFormat';
import type { DeityDetail, DeityForm, DeityHand, DeityReferencePin, DeitySummary } from '../../types/iconography';

const NOT_ESTABLISHED_TITLE = 'The cited references do not settle this; it may vary by lineage. Nothing is guessed.';

function NotEstablished(): React.ReactElement {
  return (
    <span data-null="true" title={NOT_ESTABLISHED_TITLE} className="italic text-amber-300/90">
      not established <span className="text-amber-300/60">/ varies by lineage</span>
    </span>
  );
}

function NotRecorded(): React.ReactElement {
  return (
    <span data-null="true" className="italic text-gray-500">
      not recorded
    </span>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }): React.ReactElement {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[9rem_1fr] gap-x-3 gap-y-0.5 py-1.5 border-b border-white/5">
      <dt className="text-xs uppercase tracking-wide text-gray-500">{label}</dt>
      <dd className="m-0 text-sm text-gray-200 break-words">{children}</dd>
    </div>
  );
}

function valueOrNull(value: React.ReactNode | null | undefined): React.ReactNode {
  return value === null || value === undefined || value === '' ? <NotEstablished /> : value;
}

function formatCount(n: number | null | undefined): React.ReactNode {
  return typeof n === 'number' ? n.toLocaleString('en-US') : <NotEstablished />;
}

/** How many arms a hand label stands for ("both" / "principal pair" are two). */
function armsInHand(hand: DeityHand): number {
  return hand.hand === 'both' || hand.hand === 'principal pair' ? 2 : 1;
}

function humanize(key: string): string {
  return key.replace(/_/g, ' ');
}

function Notes({ title, text }: { title: string; text: string | null | undefined }): React.ReactElement | null {
  if (!text) return null;
  return (
    <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-xs text-gray-300">
      <span className="font-semibold text-gray-200">{title}: </span>
      {text}
    </div>
  );
}

function SectionHeading({ children, provenance }: { children: React.ReactNode; provenance?: 'record' | 'computed' }) {
  return (
    <h3 className="m-0 mb-1 flex items-center gap-2 text-sm font-semibold text-vajra-cyan">
      {children}
      {provenance && <ProvenanceTag kind={provenance} />}
    </h3>
  );
}

function Hands({ form }: { form: DeityForm }): React.ReactElement {
  const hands = form.hands ?? [];
  const covered = hands.reduce((n, h) => n + armsInHand(h), 0);
  const showOther = !!form.other_hands || (typeof form.arms === 'number' && form.arms > covered);
  return (
    <div>
      <SectionHeading provenance="record">Hands: gestures and held attributes</SectionHeading>
      {hands.length === 0 ? (
        <p className="m-0 text-sm">
          <NotEstablished />
        </p>
      ) : (
        <ul className="m-0 p-0 grid grid-cols-1 sm:grid-cols-2 gap-2" data-testid="iconography-hands">
          {hands.map((hand, i) => (
            <li key={`${hand.hand}-${i}`} className="list-none rounded-md border border-white/10 bg-gray-900/50 p-2">
              <div className="text-xs font-semibold capitalize text-vajra-gold">{hand.hand}</div>
              <dl className="m-0 mt-1 grid grid-cols-[4.5rem_1fr] gap-x-2 gap-y-0.5 text-xs">
                <dt className="text-gray-500">Position</dt>
                <dd className="m-0 text-gray-200">{hand.position || <NoneMarker />}</dd>
                <dt className="text-gray-500">Mudra</dt>
                <dd className="m-0 text-gray-200">{hand.mudra || <NoneMarker />}</dd>
                <dt className="text-gray-500">Holds</dt>
                <dd className="m-0 text-gray-200">{hand.holds || <NoneMarker />}</dd>
              </dl>
            </li>
          ))}
        </ul>
      )}
      {showOther && (
        <dl className="m-0 mt-2">
          <Field label="Other hands">{valueOrNull(form.other_hands)}</Field>
        </dl>
      )}
    </div>
  );
}

/** A hand with no recorded position, gesture or object (it holds nothing, say). */
function NoneMarker(): React.ReactElement {
  return (
    <span className="text-gray-600" aria-label="none recorded" title="none recorded">
      —
    </span>
  );
}

function FormFacts({
  form,
  ornamentSets,
}: {
  form: DeityForm;
  ornamentSets: Record<string, string>;
}): React.ReactElement {
  const ornaments = form.ornaments
    ? [ornamentSets[form.ornaments] ?? humanize(form.ornaments), form.ornament_details].filter(Boolean).join('; ')
    : null;
  return (
    <div className="flex flex-col gap-4">
      <div>
        <SectionHeading provenance="record">Body</SectionHeading>
        <dl className="m-0">
          <Field label="Body colour">{valueOrNull(form.body_colour)}</Field>
          <Field label="Faces">{formatCount(form.faces)}</Field>
          <Field label="Arms">{formatCount(form.arms)}</Field>
          <Field label="Eyes">{valueOrNull(form.eyes)}</Field>
          <Field label="Posture">{valueOrNull(form.posture)}</Field>
          <Field label="Seat">{valueOrNull(form.seat)}</Field>
          <Field label="Features">{valueOrNull(form.features)}</Field>
          <Field label="Ornaments">{valueOrNull(ornaments)}</Field>
          <Field label="Halo">{valueOrNull(form.halo)}</Field>
        </dl>
      </div>
      <Hands form={form} />
      <Notes title="Form note" text={form.notes} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reference image
// ---------------------------------------------------------------------------

function ReferencePanel({
  deityId,
  name,
  pin,
  onChange,
}: {
  deityId: string;
  name: string;
  pin: DeityReferencePin | null;
  onChange: (pin: DeityReferencePin | null) => void;
}): React.ReactElement {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const available = !!pin && pin.available !== false;

  useEffect(() => {
    setError(null);
    setImageFailed(false);
  }, [deityId, pin?.reference_id]);

  const handleFile = async (file: File): Promise<void> => {
    const problem = validateReferenceFile(file);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const stored = await uploadReferenceImage(file);
      const pinned = await pinDeityReference(deityId, stored.reference_id);
      onChange(pinned);
      message.success(`Reference pinned to ${name}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const unpin = async (): Promise<void> => {
    setError(null);
    setBusy(true);
    try {
      await unpinDeityReference(deityId);
      onChange(null);
      message.info(`Reference unpinned from ${name}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="flex flex-col gap-2" data-testid="iconography-reference" aria-labelledby="iconography-reference-heading">
      <h3 id="iconography-reference-heading" className="m-0 text-sm font-semibold text-vajra-cyan">
        Thangka reference
      </h3>
      <p className="m-0 text-xs text-gray-400">
        A pinned thangka conditions every witness render of this deity (all its forms) alongside the description
        above; it stays on this machine and only the local renderer reads it.
      </p>

      {pin && available && (
        <div className="flex flex-col sm:flex-row gap-3 sm:items-start" data-testid="iconography-reference-preview">
          {imageFailed ? (
            <span className="flex h-40 w-full sm:w-40 flex-col items-center justify-center gap-1 rounded border border-white/10 text-[11px] text-gray-500">
              <ImageOff className="w-5 h-5" />
              could not load the image
            </span>
          ) : (
            <a
              href={referenceImageUrl(pin.reference_id)}
              target="_blank"
              rel="noreferrer"
              className="block rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400"
            >
              <img
                src={referenceImageUrl(pin.reference_id)}
                alt={`Thangka reference pinned to ${name}`}
                onError={() => setImageFailed(true)}
                className="max-h-72 w-full sm:w-auto sm:max-w-xs rounded border border-white/10 object-contain bg-black/40"
              />
            </a>
          )}
          <div className="text-[11px] text-gray-400 font-mono flex flex-col gap-0.5 min-w-0">
            <span className="truncate">sha256 {pin.reference_id.slice(0, 12)}…</span>
            {pin.set_at && <span>pinned {formatDateTime(pin.set_at)}</span>}
          </div>
        </div>
      )}

      {pin && !available && (
        <p className="m-0 text-xs text-amber-300" data-testid="iconography-reference-missing">
          A reference is pinned but its image is no longer stored, so renders go ahead without it. Upload it again or
          unpin it.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept={REFERENCE_ACCEPT}
          aria-label={`Reference image for ${name}`}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = '';
            if (file) void handleFile(file);
          }}
        />
        <Button
          size="small"
          icon={<Upload className="w-3.5 h-3.5" />}
          loading={busy}
          onClick={() => inputRef.current?.click()}
        >
          {pin ? 'Replace image…' : 'Upload image…'}
        </Button>
        {pin && (
          <Popconfirm
            title="Unpin this reference?"
            description={`Witness renders of ${name} go back to the curated description alone. The image file is kept.`}
            okText="Unpin"
            cancelText="Keep"
            onConfirm={() => unpin()}
          >
            <Button size="small" danger disabled={busy}>
              Unpin
            </Button>
          </Popconfirm>
        )}
        <span className="text-[11px] text-gray-500">PNG, JPEG or WebP, up to 20 MB.</span>
      </div>

      {error && (
        <span className="text-xs text-amber-300" role="alert" data-testid="iconography-reference-error">
          {error}
        </span>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Detail
// ---------------------------------------------------------------------------

function DeityDetailView({
  detail,
  summary,
  formId,
  onFormChange,
  onReferenceChange,
}: {
  detail: DeityDetail;
  summary: DeitySummary | undefined;
  formId: string;
  onFormChange: (form: string) => void;
  onReferenceChange: (pin: DeityReferencePin | null) => void;
}): React.ReactElement {
  const entry = detail.deity;
  const form = entry.forms.find((f) => f.id === formId) ?? entry.forms.find((f) => f.id === entry.default_form);
  const pin = summary ? summary.reference : (detail.reference ?? null);
  const generic = !!entry.generic || 'individual_iconography' in entry;
  const names = entry.names;
  const sources = detail.sources ?? [];

  return (
    <article className="flex flex-col gap-5" data-testid="iconography-detail" aria-labelledby="iconography-detail-heading">
      <header className="flex flex-col gap-1">
        <h2 id="iconography-detail-heading" className="m-0 text-lg font-semibold text-gray-100">
          {names.english}
        </h2>
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
          {entry.kind && <span className="capitalize">{entry.kind.replace(/_/g, ' ')}</span>}
          {generic && <span className="rounded border border-vajra-gold/40 px-1 text-vajra-gold">generic form</span>}
        </div>
      </header>

      <div>
        <SectionHeading provenance="record">Names</SectionHeading>
        <dl className="m-0">
          <Field label="Sanskrit">{names.sanskrit || <NotRecorded />}</Field>
          <Field label="Tibetan">{names.tibetan || <NotRecorded />}</Field>
          <Field label="Chinese">
            {names.chinese ? <span lang="zh">{names.chinese}</span> : <NotRecorded />}
          </Field>
        </dl>
      </div>

      {generic && (
        <div
          className="rounded-md border border-vajra-gold/30 bg-vajra-gold/5 px-3 py-2 text-xs text-gray-200"
          data-testid="iconography-generic-note"
        >
          <div className="mb-1 font-semibold text-vajra-gold">
            Individual iconography: <NotEstablished />
          </div>
          {entry.individual_iconography_note ??
            'These figures have no individually established iconography; images use the generic form below.'}
        </div>
      )}
      <Notes title="Note" text={entry.notes} />

      {entry.forms.length > 1 && (
        <div className="flex flex-col gap-1">
          <span id="iconography-form-label" className="text-xs text-gray-400">
            Form
          </span>
          <Radio.Group
            aria-labelledby="iconography-form-label"
            value={form?.id}
            onChange={(e) => onFormChange(String(e.target.value))}
            options={entry.forms.map((f) => ({
              value: f.id,
              label: f.id === entry.default_form ? `${f.label} (default)` : f.label,
            }))}
          />
        </div>
      )}

      {form ? (
        <div className="flex flex-col gap-1">
          {entry.forms.length === 1 && <div className="text-sm text-gray-300">{form.label}</div>}
          <FormFacts form={form} ornamentSets={detail.ornament_sets ?? {}} />
        </div>
      ) : (
        <p className="m-0 text-sm text-amber-300">This entry has no forms recorded.</p>
      )}

      <div>
        <SectionHeading provenance="record">Sources</SectionHeading>
        {sources.length > 0 ? (
          <ol className="m-0 pl-5 text-xs text-gray-300 flex flex-col gap-1" data-testid="iconography-sources">
            {sources.map((s) => (
              <li key={s}>
                <cite className="not-italic">{s}</cite>
              </li>
            ))}
          </ol>
        ) : (
          <p className="m-0 text-xs text-amber-300">No sources are recorded for this entry.</p>
        )}
      </div>

      {detail.prompt_clause && (
        <details className="rounded-md border border-white/10 bg-gray-900/40 px-3 py-2">
          <summary className="cursor-pointer text-xs text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 rounded">
            What an image model is told <ProvenanceTag kind="computed" />
          </summary>
          <p className="m-0 mt-2 text-xs text-gray-300">{detail.prompt_clause}</p>
        </details>
      )}

      <ReferencePanel deityId={entry.id} name={names.english} pin={pin} onChange={onReferenceChange} />
    </article>
  );
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export default function Iconography(): React.ReactElement {
  const [deities, setDeities] = useState<DeitySummary[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formId, setFormId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DeityDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const detailRequest = useRef(0);

  const loadList = useCallback(async (): Promise<void> => {
    setListError(null);
    try {
      const list = await fetchDeities();
      setDeities(list);
      setSelectedId((current) => (current && list.some((d) => d.id === current) ? current : (list[0]?.id ?? null)));
    } catch (err) {
      setListError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const loadDetail = useCallback(async (deityId: string, form: string | null): Promise<void> => {
    const request = ++detailRequest.current;
    setDetailLoading(true);
    setDetailError(null);
    try {
      const body = await fetchDeity(deityId, form);
      if (request === detailRequest.current) setDetail(body);
    } catch (err) {
      if (request === detailRequest.current) setDetailError(err instanceof Error ? err.message : String(err));
    } finally {
      if (request === detailRequest.current) setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedId) void loadDetail(selectedId, formId);
  }, [selectedId, formId, loadDetail]);

  const select = (id: string): void => {
    if (id === selectedId) return;
    setFormId(null);
    setSelectedId(id);
  };

  const updatePin = (pin: DeityReferencePin | null): void => {
    if (!selectedId) return;
    setDeities((list) => (list ? list.map((d) => (d.id === selectedId ? { ...d, reference: pin } : d)) : list));
    setDetail((d) =>
      d && d.deity.id === selectedId
        ? { ...d, reference_id: pin && pin.available !== false ? pin.reference_id : null, reference: pin }
        : d,
    );
  };

  if (listError) {
    return <ErrorState message="Could not load the iconography" description={listError} onRetry={() => void loadList()} />;
  }
  if (!deities) return <LoadingState message="Loading the iconography…" />;
  if (deities.length === 0) {
    return <p className="p-4 text-sm text-gray-400">No deities are curated yet (knowledge/iconography.json).</p>;
  }

  const summary = deities.find((d) => d.id === selectedId);
  const shownDetail = detail && detail.deity.id === selectedId ? detail : null;

  return (
    <div className="flex flex-col gap-3" data-testid="iconography">
      <p className="m-0 text-xs text-gray-400 max-w-3xl">
        Curated iconography after standard references. Fields the references do not settle are marked not established
        rather than guessed. Witness renders of a deity use this description and, if pinned, your thangka reference.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-[16rem_1fr] gap-4 min-w-0">
        <nav aria-label="Deities" className="min-w-0">
          <ul className="m-0 p-0 flex flex-col gap-1 max-h-56 md:max-h-none overflow-y-auto rounded-lg border border-white/10 bg-gray-900/40 p-1">
            {deities.map((d) => {
              const active = d.id === selectedId;
              return (
                <li key={d.id} className="list-none">
                  <button
                    type="button"
                    data-testid="iconography-deity"
                    data-deity={d.id}
                    aria-current={active ? 'true' : undefined}
                    onClick={() => select(d.id)}
                    className={`w-full text-left rounded-md px-2 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 ${
                      active ? 'bg-vajra-purple/25 text-gray-100' : 'text-gray-300 hover:bg-white/5'
                    }`}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate">{d.name}</span>
                      {d.reference && (
                        <span
                          className={`shrink-0 text-[10px] ${d.reference.available === false ? 'text-amber-300' : 'text-vajra-gold'}`}
                          title={d.reference.available === false ? 'Pinned image is missing' : 'Thangka reference pinned'}
                        >
                          {d.reference.available === false ? 'ref missing' : 'ref'}
                        </span>
                      )}
                    </span>
                    {d.forms.length > 1 && <span className="block text-[11px] text-gray-500">{d.forms.length} forms</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="min-w-0 rounded-lg border border-white/10 bg-gray-900/30 p-3 sm:p-4">
          {detailError ? (
            <div className="flex flex-col items-start gap-2">
              <p className="m-0 text-sm text-amber-300" role="alert">
                {detailError}
              </p>
              <Button
                size="small"
                icon={<RefreshCw className="w-3.5 h-3.5" />}
                onClick={() => selectedId && void loadDetail(selectedId, formId)}
              >
                Retry
              </Button>
            </div>
          ) : shownDetail ? (
            <DeityDetailView
              detail={shownDetail}
              summary={summary}
              formId={formId ?? shownDetail.form}
              onFormChange={setFormId}
              onReferenceChange={updatePin}
            />
          ) : detailLoading ? (
            <LoadingState message="Loading…" height="h-40" />
          ) : null}
        </div>
      </div>
    </div>
  );
}
