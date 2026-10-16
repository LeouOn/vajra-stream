/**
 * Iconography screen against a mocked API (no server):
 *   - lists every deity the API returns and opens the first
 *   - detail: names, record provenance, hands, sources as citations
 *   - null fields read "not established / varies by lineage"; notes are shown
 *   - the generic 88 Buddhas entry shows its individual-iconography note
 *   - switching form refetches with ?form=
 *   - reference: upload + pin, server validation message, client checks, unpin via Popconfirm, stale pin
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { ConfigProvider } from 'antd';

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
}));

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>();
  return { ...actual, message: { ...actual.message, ...toast } };
});

import Iconography from '../../components/Operations/Iconography';
import type { DeityDetail, DeityEntry, DeitySummary } from '../../types/iconography';

const REF = 'a'.repeat(64);
const NEW_REF = 'b'.repeat(64);

const TARA: DeityEntry = {
  id: 'green_tara',
  kind: 'bodhisattva',
  names: { english: 'Green Tara', sanskrit: 'Śyāmatārā', tibetan: 'Drolma Jangku', chinese: '綠度母' },
  default_form: 'standard',
  forms: [
    {
      id: 'standard',
      label: 'Green Tara',
      body_colour: 'emerald green',
      faces: 1,
      arms: 2,
      eyes: null,
      posture: 'seated with the right leg extended',
      seat: 'a lotus and moon disc',
      hands: [
        { hand: 'right', position: 'on the right knee', mudra: 'the boon-granting gesture (varada mudra)', holds: null },
        { hand: 'left', position: 'at the heart', mudra: 'the refuge gesture', holds: 'a blue utpala flower' },
      ],
      other_hands: null,
      features: null,
      ornaments: 'sambhogakaya',
      ornament_details: null,
      halo: null,
      notes: 'The utpala is sometimes painted half open.',
    },
  ],
  sources: ['beer_encyclopedia'],
  notes: 'Tara is the mother of the Buddhas.',
};

const CHENREZIG: DeityEntry = {
  id: 'avalokiteshvara',
  kind: 'bodhisattva',
  names: { english: 'Avalokiteshvara', sanskrit: 'Avalokiteśvara', tibetan: 'Chenrezig', chinese: '觀世音' },
  default_form: 'four_armed',
  forms: [
    {
      id: 'four_armed',
      label: 'Four-armed Chenrezig',
      body_colour: 'white',
      faces: 1,
      arms: 4,
      hands: [{ hand: 'principal pair', position: 'at the heart', mudra: 'anjali mudra', holds: 'a jewel' }],
      other_hands: null,
      ornaments: 'sambhogakaya',
    },
    {
      id: 'thousand_armed',
      label: 'Eleven-faced, thousand-armed Avalokiteshvara',
      body_colour: 'white',
      faces: 11,
      arms: 1000,
      hands: [{ hand: 'principal pair', position: 'at the heart', mudra: 'anjali mudra', holds: null }],
      other_hands: 'the remaining arms spread behind in a circular aureole',
      ornaments: 'sambhogakaya',
    },
  ],
  sources: ['har'],
  notes: null,
};

const GENERIC: DeityEntry = {
  id: 'buddha_generic',
  kind: 'buddha',
  generic: true,
  names: { english: 'A Buddha (generic form)', sanskrit: null, tibetan: null, chinese: null },
  default_form: 'generic',
  individual_iconography: null,
  individual_iconography_note: 'The 88 Buddhas of the Chinese repentance liturgy are invoked by name only.',
  forms: [
    {
      id: 'generic',
      label: 'a Buddha in meditation',
      body_colour: 'golden',
      faces: 1,
      arms: 2,
      hands: [{ hand: 'both', position: 'resting in the lap', mudra: 'dhyana mudra', holds: null }],
      ornaments: 'nirmanakaya',
    },
  ],
  sources: ['thirty_two_marks'],
  notes: null,
};

const ENTRIES: Record<string, DeityEntry> = { green_tara: TARA, avalokiteshvara: CHENREZIG, buddha_generic: GENERIC };
const CITATIONS: Record<string, string[]> = {
  green_tara: ['Robert Beer, The Encyclopedia of Tibetan Symbols and Motifs (Boston: Shambhala, 1999)'],
  avalokiteshvara: ['Himalayan Art Resources (himalayanart.org), deity iconography outlines'],
  buddha_generic: ['The thirty-two major marks of a Buddha'],
};

let pins: Record<string, { reference_id: string; set_at: string; available: boolean } | undefined>;
let uploadResponse: { status: number; body: unknown };
let fetchSpy: ReturnType<typeof vi.fn>;
let container: HTMLDivElement;
let root: Root;

function summary(entry: DeityEntry): DeitySummary {
  return {
    id: entry.id,
    name: entry.names.english,
    names: entry.names,
    generic: !!entry.generic,
    default_form: entry.default_form,
    forms: entry.forms.map((f) => ({ id: f.id, label: f.label })),
    sources: CITATIONS[entry.id],
    reference: pins[entry.id] ?? null,
  };
}

function detail(entry: DeityEntry, form: string | null): DeityDetail {
  const pin = pins[entry.id];
  return {
    deity: entry,
    form: form ?? entry.default_form,
    prompt_clause: `Traditional thangka of ${entry.names.english}`,
    caption_facts: [],
    sources: CITATIONS[entry.id],
    reference_id: pin && pin.available ? pin.reference_id : null,
    ornament_sets: {
      sambhogakaya: 'the silks and jewel ornaments of the enjoyment body',
      nirmanakaya: 'the patched robes of a fully ordained monk',
    },
    reference: pin ?? null,
  };
}

function respond(status: number, body: unknown): Promise<Response> {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body } as Response);
}

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  Object.values(toast).forEach((fn) => fn.mockReset());
  pins = {};
  uploadResponse = {
    status: 201,
    body: { reference_id: NEW_REF, sha256: NEW_REF, filename: `${NEW_REF}.png`, width: 600, height: 900 },
  };
  fetchSpy = vi.fn((url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET';
    if (url === '/api/v1/iconography') {
      return respond(200, { deities: [TARA, CHENREZIG, GENERIC].map(summary) });
    }
    if (url === '/api/v1/render/references' && method === 'POST') {
      return respond(uploadResponse.status, uploadResponse.body);
    }
    const pinMatch = /^\/api\/v1\/iconography\/([^/?]+)\/reference$/.exec(url);
    if (pinMatch) {
      const id = decodeURIComponent(pinMatch[1]);
      if (method === 'PUT') {
        const { reference_id } = JSON.parse(String(init?.body)) as { reference_id: string };
        pins[id] = { reference_id, set_at: '2026-10-16T09:00:00+00:00', available: true };
        return respond(200, { deity: id, ...pins[id] });
      }
      if (method === 'DELETE') {
        const removed = !!pins[id];
        delete pins[id];
        return respond(200, { deity: id, removed });
      }
    }
    const detailMatch = /^\/api\/v1\/iconography\/([^/?]+)(?:\?form=(.+))?$/.exec(url);
    if (detailMatch) {
      const entry = ENTRIES[decodeURIComponent(detailMatch[1])];
      if (!entry) return respond(404, { detail: 'unknown deity' });
      return respond(200, detail(entry, detailMatch[2] ? decodeURIComponent(detailMatch[2]) : null));
    }
    return respond(404, { detail: 'not found' });
  });
  vi.stubGlobal('fetch', fetchSpy);
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  document.body.innerHTML = '';
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function flush(): Promise<void> {
  for (let i = 0; i < 3; i += 1) {
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
  }
}

async function renderScreen(): Promise<void> {
  await act(async () => {
    root.render(
      <ConfigProvider>
        <Iconography />
      </ConfigProvider>,
    );
  });
  await flush();
}

function detailEl(): HTMLElement {
  const el = container.querySelector<HTMLElement>('[data-testid="iconography-detail"]');
  if (!el) throw new Error('no detail view');
  return el;
}

/** The `<dd>` of the field labelled `label` in the detail view. */
function field(label: string): HTMLElement {
  const dt = Array.from(detailEl().querySelectorAll('dt')).find((d) => d.textContent === label);
  const dd = dt?.nextElementSibling;
  if (!(dd instanceof HTMLElement)) throw new Error(`no field ${label}`);
  return dd;
}

async function choose(deityId: string): Promise<void> {
  const button = container.querySelector<HTMLButtonElement>(`[data-testid="iconography-deity"][data-deity="${deityId}"]`);
  if (!button) throw new Error(`no deity ${deityId}`);
  await act(async () => {
    button.click();
  });
  await flush();
}

function pick(file: File): Promise<void> {
  const input = container.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error('reference input not found');
  Object.defineProperty(input, 'files', { configurable: true, value: [file] });
  return act(async () => {
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

function png(): File {
  return new File([new Uint8Array([137, 80, 78, 71])], 'tara.png', { type: 'image/png' });
}

function calls(method: string, urlPart: string): unknown[][] {
  return fetchSpy.mock.calls.filter(
    (c) => String(c[0]).includes(urlPart) && ((c[1] as RequestInit | undefined)?.method ?? 'GET') === method,
  );
}

describe('Iconography', () => {
  it('lists every deity from the API and opens the first one', async () => {
    await renderScreen();
    const buttons = Array.from(container.querySelectorAll('[data-testid="iconography-deity"]'));
    expect(buttons.map((b) => b.getAttribute('data-deity'))).toEqual(['green_tara', 'avalokiteshvara', 'buddha_generic']);
    expect(buttons[0].getAttribute('aria-current')).toBe('true');
    expect(buttons[1].textContent).toContain('2 forms');
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/iconography/green_tara');
    expect(detailEl().querySelector('h2')?.textContent).toBe('Green Tara');
  });

  it('shows names, body, hands, ornaments and sources as record values', async () => {
    await renderScreen();
    expect(field('Sanskrit').textContent).toBe('Śyāmatārā');
    expect(field('Tibetan').textContent).toBe('Drolma Jangku');
    expect(field('Chinese').textContent).toBe('綠度母');
    expect(field('Body colour').textContent).toBe('emerald green');
    expect(field('Arms').textContent).toBe('2');
    expect(field('Ornaments').textContent).toBe('the silks and jewel ornaments of the enjoyment body');
    const hands = detailEl().querySelector('[data-testid="iconography-hands"]')?.textContent ?? '';
    expect(hands).toContain('the boon-granting gesture (varada mudra)');
    expect(hands).toContain('a blue utpala flower');
    expect(detailEl().querySelector('[data-testid="iconography-sources"] cite')?.textContent).toContain(
      'Encyclopedia of Tibetan Symbols',
    );
    expect(detailEl().querySelectorAll('[data-provenance="record"]').length).toBeGreaterThanOrEqual(4);
    expect(detailEl().querySelector('[data-provenance="computed"]')).not.toBeNull();
  });

  it('marks null fields as not established and shows the notes', async () => {
    await renderScreen();
    for (const label of ['Eyes', 'Features', 'Halo']) {
      const dd = field(label);
      expect(dd.querySelector('[data-null="true"]')).not.toBeNull();
      expect(dd.textContent).toContain('not established');
      expect(dd.textContent).toContain('varies by lineage');
    }
    // Two arms, two hands listed: no "Other hands" row to leave unestablished.
    expect(Array.from(detailEl().querySelectorAll('dt')).some((d) => d.textContent === 'Other hands')).toBe(false);
    expect(detailEl().textContent).toContain('The utpala is sometimes painted half open.');
    expect(detailEl().textContent).toContain('Tara is the mother of the Buddhas.');
  });

  it('shows the generic 88 Buddhas note', async () => {
    await renderScreen();
    await choose('buddha_generic');
    const note = detailEl().querySelector('[data-testid="iconography-generic-note"]');
    expect(note?.textContent).toContain('The 88 Buddhas of the Chinese repentance liturgy are invoked by name only.');
    expect(note?.querySelector('[data-null="true"]')).not.toBeNull();
    expect(field('Sanskrit').querySelector('[data-null="true"]')).not.toBeNull();
  });

  it('switches form and refetches with ?form=', async () => {
    await renderScreen();
    await choose('avalokiteshvara');
    expect(field('Arms').textContent).toBe('4');
    const radio = Array.from(detailEl().querySelectorAll<HTMLInputElement>('input[type="radio"]')).find(
      (r) => r.value === 'thousand_armed',
    );
    expect(radio).toBeDefined();
    await act(async () => {
      radio?.click();
    });
    await flush();
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/iconography/avalokiteshvara?form=thousand_armed');
    expect(field('Arms').textContent).toBe('1,000');
    expect(field('Faces').textContent).toBe('11');
    expect(field('Other hands').textContent).toContain('circular aureole');
  });

  describe('reference image', () => {
    it('uploads, pins and previews a reference', async () => {
      await renderScreen();
      expect(container.querySelector('[data-testid="iconography-reference-preview"]')).toBeNull();
      await pick(png());
      await flush();
      expect(calls('POST', '/render/references')).toHaveLength(1);
      expect(((calls('POST', '/render/references')[0][1] as RequestInit).body as FormData).get('image')).toBeInstanceOf(
        File,
      );
      const put = calls('PUT', '/iconography/green_tara/reference');
      expect(put).toHaveLength(1);
      expect(JSON.parse(String((put[0][1] as RequestInit).body))).toEqual({ reference_id: NEW_REF });
      const img = container.querySelector<HTMLImageElement>('[data-testid="iconography-reference-preview"] img');
      expect(img?.getAttribute('src')).toBe(`/api/v1/render/references/${NEW_REF}`);
      expect(img?.getAttribute('alt')).toBe('Thangka reference pinned to Green Tara');
      expect(toast.success).toHaveBeenCalledWith('Reference pinned to Green Tara.');
      // The list marks the deity as having a reference.
      expect(container.querySelector('[data-deity="green_tara"]')?.textContent).toContain('ref');
    });

    it("shows the server's validation message and pins nothing", async () => {
      uploadResponse = {
        status: 415,
        body: { detail: 'not a PNG, JPEG or WebP image (checked the file header, not its name)' },
      };
      await renderScreen();
      await pick(png());
      await flush();
      expect(container.querySelector('[data-testid="iconography-reference-error"]')?.textContent).toBe(
        'not a PNG, JPEG or WebP image (checked the file header, not its name)',
      );
      expect(calls('PUT', '/reference')).toHaveLength(0);
    });

    it('refuses an unsupported file before uploading', async () => {
      await renderScreen();
      await pick(new File(['x'], 'tara.gif', { type: 'image/gif' }));
      expect(container.querySelector('[data-testid="iconography-reference-error"]')?.textContent).toBe(
        'A reference must be a PNG, JPEG or WebP image.',
      );
      expect(calls('POST', '/render/references')).toHaveLength(0);
    });

    it('unpins after confirming', async () => {
      pins.green_tara = { reference_id: REF, set_at: '2026-10-15T09:00:00+00:00', available: true };
      await renderScreen();
      expect(container.querySelector('[data-testid="iconography-reference-preview"] img')?.getAttribute('src')).toBe(
        `/api/v1/render/references/${REF}`,
      );
      const unpin = Array.from(container.querySelectorAll('button')).find((b) => b.textContent === 'Unpin');
      await act(async () => {
        unpin?.click();
      });
      await flush();
      expect(calls('DELETE', '/reference')).toHaveLength(0); // nothing until confirmed
      const confirm = Array.from(document.body.querySelectorAll<HTMLButtonElement>('.ant-popconfirm button')).find(
        (b) => b.textContent === 'Unpin',
      );
      expect(confirm).toBeDefined();
      await act(async () => {
        confirm?.click();
      });
      await flush();
      expect(calls('DELETE', '/iconography/green_tara/reference')).toHaveLength(1);
      expect(container.querySelector('[data-testid="iconography-reference-preview"]')).toBeNull();
      expect(Array.from(container.querySelectorAll('button')).some((b) => b.textContent === 'Unpin')).toBe(false);
      expect(toast.info).toHaveBeenCalledWith('Reference unpinned from Green Tara.');
    });

    it('says when a pinned image is no longer stored', async () => {
      pins.green_tara = { reference_id: REF, set_at: '2026-10-15T09:00:00+00:00', available: false };
      await renderScreen();
      expect(container.querySelector('[data-testid="iconography-reference-missing"]')).not.toBeNull();
      expect(container.querySelector('[data-testid="iconography-reference-preview"]')).toBeNull();
      expect(container.querySelector('[data-deity="green_tara"]')?.textContent).toContain('ref missing');
    });
  });
});
