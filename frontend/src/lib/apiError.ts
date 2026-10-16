/**
 * Read a FastAPI error body. `detail` may be a string or a validation list.
 */

/** The `detail` text of an error response, or null when the body has none. */
export async function errorDetail(res: Response): Promise<string | null> {
  try {
    const body: unknown = await res.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail
          .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : String(d)))
          .join('; ');
      }
    }
  } catch {
    // body was not JSON
  }
  return null;
}

/** `detail` when present, else `<fallback> (HTTP <status>)`. */
export async function errorMessage(res: Response, fallback: string): Promise<string> {
  return (await errorDetail(res)) ?? `${fallback} (HTTP ${res.status})`;
}
