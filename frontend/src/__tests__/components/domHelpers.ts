/**
 * Small DOM helpers for component tests that render with createRoot + act
 * (the repo does not ship @testing-library).
 */
import { act } from 'react-dom/test-utils';

/** One recorded fetch call. */
export interface FetchCall {
  url: string;
  method: string;
  body: unknown;
}

export interface MockResponseSpec {
  ok?: boolean;
  status?: number;
  body?: unknown;
}

/** A route returns a response spec, or undefined to fall through to the default `{}`. */
export type FetchRoute = (url: string, init: RequestInit | undefined) => MockResponseSpec | undefined;

/**
 * Install a fetch stub on globalThis. Every call is recorded in `calls`;
 * unmatched URLs answer 200 `{}` so offline renders stay clean.
 */
export function installFetch(route: FetchRoute): { calls: FetchCall[] } {
  const calls: FetchCall[] = [];
  const stub = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    let body: unknown = undefined;
    if (init && typeof init.body === 'string') {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    calls.push({ url, method: (init?.method || 'GET').toUpperCase(), body });
    const spec = route(url, init) ?? {};
    const status = spec.status ?? 200;
    const ok = spec.ok ?? (status >= 200 && status < 300);
    const payload = spec.body === undefined ? {} : spec.body;
    const response = {
      ok,
      status,
      statusText: ok ? 'OK' : 'Error',
      json: async () => payload,
    };
    return Promise.resolve(response as unknown as Response);
  };
  globalThis.fetch = stub as typeof fetch;
  return { calls };
}

/** Path part of an apiUrl() URL, e.g. `/outlook/history?limit=100`. */
export function apiPath(url: string): string {
  const i = url.indexOf('/api/v1');
  return i >= 0 ? url.slice(i + '/api/v1'.length) : url;
}

/** Let pending promises and React updates settle. */
export async function flush(ms = 0): Promise<void> {
  await act(async () => {
    await new Promise((r) => setTimeout(r, ms));
  });
}

/** Elements matching `selector` whose text content includes `text`. */
export function allByText(root: ParentNode, selector: string, text: string): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(selector)).filter((el) =>
    (el.textContent || '').includes(text),
  );
}

/** The innermost element matching `selector` whose text includes `text`. */
export function byText(root: ParentNode, selector: string, text: string): HTMLElement {
  const matches = allByText(root, selector, text);
  if (matches.length === 0) throw new Error(`No <${selector}> containing "${text}"`);
  return matches[matches.length - 1];
}

export async function click(el: Element): Promise<void> {
  await act(async () => {
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
}

/** Type into a React-controlled <input>/<textarea> (bypasses React's value tracker). */
export async function typeInto(el: HTMLInputElement | HTMLTextAreaElement, value: string): Promise<void> {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  await act(async () => {
    setter?.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });
}
