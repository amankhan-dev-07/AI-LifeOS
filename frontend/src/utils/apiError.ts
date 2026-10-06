/**
 * Shared helpers for turning Axios failures into user-facing messages.
 *
 * The API layer surfaces FastAPI `detail` payloads in two shapes: a plain
 * string, or a list of Pydantic validation errors. Views should never have to
 * re-derive that branching, so it lives here.
 */

export function extractErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })?.response;
  const detail = response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        const entry = item as { msg?: string; message?: string };
        return entry.msg || entry.message;
      })
      .filter((msg): msg is string => Boolean(msg));

    if (messages.length) return messages.join(' • ');
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

export function extractStatusCode(error: unknown): number | null {
  const status = (error as { response?: { status?: number } })?.response?.status;
  return typeof status === 'number' ? status : null;
}