/**
 * Date helpers shared by the Planner and Finance views.
 *
 * The backend stores planner timestamps as naive UTC datetimes and finance
 * transactions as plain dates. Both are formatted for display using the
 * browser's locale.
 */

/**
 * Parse a backend naive-UTC timestamp (`2026-10-03T09:00:00`) as a real
 * `Date` by treating the string as UTC.
 *
 * `new Date('2026-10-03T09:00:00')` is interpreted as *local* time by the
 * browser, which silently shifts every reminder by the machine's UTC offset —
 * the classic off-by-a-day bug near midnight. Appending an explicit `Z` pins
 * the parse to UTC and then lets `toLocale*` render it wherever the user is.
 */
export function parseNaiveUtc(value: string): Date {
  // A value that already carries an offset (or `Z`) is parsed as-is.
  if (/[Zz]|[+-]\d{2}:?\d{2}$/.test(value)) return new Date(value);

  const normalized = value.includes('T') ? value : `${value}T00:00:00`;
  return new Date(`${normalized}Z`);
}

/** The product's default display timezone, used before preferences load. */
export const DEFAULT_TIMEZONE = 'Asia/Kolkata';

/** Only two time formats exist; anything else falls back to 24-hour. */
export type TimeFormat = '12h' | '24h';

export const DEFAULT_TIME_FORMAT: TimeFormat = '24h';

export function normalizeTimeFormat(value: unknown): TimeFormat {
  return value === '12h' ? '12h' : '24h';
}

/** Whether the runtime can render a named IANA zone. */
function canResolveZone(timeZone: string): boolean {
  try {
    new Intl.DateTimeFormat('en-US', { timeZone }).format();
    return true;
  } catch {
    return false;
  }
}

/**
 * Whether `value` is an IANA zone name the app can actually format with.
 *
 * `Intl` raises a RangeError for anything it cannot resolve, so this rejects
 * arbitrary strings and fixed UTC offsets alike — an offset is a moment, not a
 * zone, and has no DST rules.
 *
 * This mirrors the backend's `is_valid_timezone` (`app/core/timezones.py`),
 * which asks `zoneinfo` the same question. The two agree by construction: a
 * zone accepted here is a name the backend will not reject with a 400.
 */
export function isValidTimezone(value: unknown): boolean {
  if (typeof value !== 'string' || !value.trim()) return false;
  return canResolveZone(value.trim());
}

/**
 * Coerce a stored timezone into a usable IANA name.
 *
 * Empty and unknown values fall back to the product default, matching the
 * backend's `normalize_timezone`, so a row written before the column existed
 * can never reach a formatter as an unusable string.
 */
export function normalizeTimezone(value: unknown): string {
  const candidate = typeof value === 'string' ? value.trim() : '';
  if (!isValidTimezone(candidate)) return DEFAULT_TIMEZONE;
  return candidate;
}

/**
 * Resolve the zone to format in.
 *
 * The browser's own zone is used only when it can actually resolve an
 * explicit time zone — otherwise an unsupported runtime would silently shift
 * every timestamp. Once the user is authenticated the AI-LifeOS preference
 * wins, so a machine set to a different zone never overrides their choice.
 */
function resolveTimeZone(timeZone?: string): string | undefined {
  if (timeZone && canResolveZone(timeZone)) return timeZone;

  try {
    new Intl.DateTimeFormat('en-US', { timeZone: DEFAULT_TIMEZONE }).format();
    return DEFAULT_TIMEZONE;
  } catch {
    return undefined;
  }
}

/**
 * Wall-clock fields of an instant, in a given zone.
 *
 * Used instead of `toLocaleString` with a `timeZone` option because that
 * option is unavailable in older runtimes; enumerating the zone's parts and
 * formatting them by hand works everywhere.
 */
function zonedParts(date: Date, timeZone: string): {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  weekday: string;
} {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    weekday: 'short',
  });

  const parts: Record<string, string> = {};
  for (const part of fmt.formatToParts(date)) {
    parts[part.type] = part.value;
  }

  let hour = Number(parts.hour);
  // Some ICU builds report midnight as 24 under hour12: false.
  if (hour === 24) hour = 0;

  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour,
    minute: Number(parts.minute),
    weekday: parts.weekday || 'Mon',
  };
}

/**
 * Convert a wall-clock time *in the user's zone* to the single UTC instant it
 * represents.
 *
 * `datetime-local` gives wall-clock text with no offset, so the zone has to be
 * attached to it before the value can mean anything. The first guess is built
 * by formatting that wall clock as if it were already UTC; comparing that guess
 * against the true zone reading gives the zone's offset at that date, which is
 * applied once. Around a DST transition the offset can land on the wrong side,
 * so the result is corrected with a second pass — still no hardcoded offsets.
 */
export function zonedWallClockToUtc(
  dateKey: string,
  time: string,
  timeZone: string,
): Date {
  const [year, month, day] = dateKey.split('-').map(Number);
  const [hour, minute] = time.split(':').map(Number);

  const asUtc = new Date(Date.UTC(year, month - 1, day, hour, minute, 0, 0));

  const firstGuess = zonedParts(asUtc, timeZone);
  const guessAsUtc = Date.UTC(
    firstGuess.year,
    firstGuess.month - 1,
    firstGuess.day,
    firstGuess.hour,
    firstGuess.minute,
  );

  const offsetMs = guessAsUtc - asUtc.getTime();
  let result = new Date(asUtc.getTime() - offsetMs);

  // Verify by reading the result back in the zone; if the wall clock drifted
  // (DST edge), the offset was wrong and is corrected once.
  const check = zonedParts(result, timeZone);
  const drift =
    Date.UTC(check.year, check.month - 1, check.day, check.hour, check.minute) -
    Date.UTC(year, month - 1, day, hour, minute);

  if (drift !== 0) {
    result = new Date(result.getTime() - drift);
  }

  return result;
}

/** `YYYY-MM-DD` wall-clock date for an instant in the user's zone. */
export function toZonedDateKey(date: Date, timeZone?: string): string {
  const zone = resolveTimeZone(timeZone);

  if (!zone) {
    return toLocalDateKey(date);
  }

  const parts = zonedParts(date, zone);
  return `${parts.year}-${pad2(parts.month)}-${pad2(parts.day)}`;
}

function pad2(value: number): string {
  return String(value).padStart(2, '0');
}

const WEEKDAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/** Format the hour/minute of an instant in the user's zone and time format. */
export function formatZonedTime(
  value: string | Date,
  timeFormat: TimeFormat = DEFAULT_TIME_FORMAT,
  timeZone?: string,
): string {
  const date = typeof value === 'string' ? parseNaiveUtc(value) : value;
  if (Number.isNaN(date.getTime())) return typeof value === 'string' ? value : '';

  const zone = resolveTimeZone(timeZone);

  if (!zone) {
    // No explicit zone support in this runtime: fall back to the platform.
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: timeFormat === '12h',
    });
  }

  const { hour, minute } = zonedParts(date, zone);

  if (timeFormat === '12h') {
    const suffix = hour < 12 ? 'AM' : 'PM';
    const hour12 = hour % 12 === 0 ? 12 : hour % 12;
    return `${hour12}:${pad2(minute)} ${suffix}`;
  }

  return `${pad2(hour)}:${pad2(minute)}`;
}

/**
 * Format a stored UTC timestamp for display in the user's zone and format.
 *
 * This is the single display conversion: stored UTC in, wall clock out.
 */
export function formatLocalDateTime(
  value: string,
  timeFormat: TimeFormat = DEFAULT_TIME_FORMAT,
  timeZone?: string,
): string {
  const parsed = parseNaiveUtc(value);
  if (Number.isNaN(parsed.getTime())) return value;

  const zone = resolveTimeZone(timeZone);

  if (!zone) {
    return parsed.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: timeFormat === '12h',
    });
  }

  const parts = zonedParts(parsed, zone);
  const date = `${MONTH_NAMES[parts.month - 1] ?? ''} ${parts.day}`;

  return `${date}, ${formatZonedTime(parsed, timeFormat, zone)}`;
}

/** Weekday + date for an instant in the user's zone, e.g. "Sat, Oct 3". */
export function formatZonedDayAndDate(
  value: string | Date,
  timeZone?: string,
): string {
  const date = typeof value === 'string' ? parseNaiveUtc(value) : value;
  if (Number.isNaN(date.getTime())) return '';

  const zone = resolveTimeZone(timeZone);

  if (!zone) {
    return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  }

  const parts = zonedParts(date, zone);
  return `${WEEKDAY_NAMES[new Date(Date.UTC(parts.year, parts.month - 1, parts.day)).getUTCDay()] ?? ''}, ${MONTH_NAMES[parts.month - 1] ?? ''} ${parts.day}`;
}

/**
 * Relative label for a future instant: "in 5 min", "in 2 h", "in 3 days".
 *
 * Purely a difference of two absolute instants, so it is independent of both
 * the display timezone and the 12/24-hour choice.
 */
export function formatUntil(value: string, now: Date = new Date()): string {
  const parsed = parseNaiveUtc(value);
  if (Number.isNaN(parsed.getTime())) return '';

  const seconds = Math.round((parsed.getTime() - now.getTime()) / 1000);
  if (seconds <= 0) return 'due now';

  if (seconds < 60) return `in ${seconds}s`;

  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `in ${minutes} min`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `in ${hours}h`;

  return `in ${Math.round(hours / 24)}d`;
}

/**
 * Convert a `datetime-local` input value (`2026-10-03T09:00`) — a wall-clock
 * time in the user's configured zone — into the naive-UTC string the backend
 * persists. This is the ONE place local wall-clock becomes UTC.
 */
export function localInputToNaiveUtc(value: string, timeZone?: string): string {
  if (!value) return value;

  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(value);
  if (!match) return value;

  const zone = resolveTimeZone(timeZone);
  const [, dateKey, time] = match;

  const asUtc = zone ? zonedWallClockToUtc(dateKey, time, zone) : parseNaiveUtc(value);

  if (Number.isNaN(asUtc.getTime())) return value;

  // `toISOString` yields UTC with a `Z` suffix; the backend convention is
  // naive, so the suffix is stripped here rather than at the call site.
  return asUtc.toISOString().slice(0, 19);
}

/** Default value for a `datetime-local` input, `offsetMinutes` from now. */
export function defaultLocalInputValue(offsetMinutes = 60, timeZone?: string): string {
  const date = new Date(Date.now() + offsetMinutes * 60_000);
  return defaultLocalInputValueFor(date, timeZone);
}

/**
 * Render a stored UTC timestamp back into a `datetime-local` value — the
 * inverse of `localInputToNaiveUtc`, in the user's zone.
 */
export function naiveUtcToLocalInput(value: string, timeZone?: string): string {
  const parsed = parseNaiveUtc(value);
  if (Number.isNaN(parsed.getTime())) return '';

  return defaultLocalInputValueFor(parsed, timeZone);
}

function defaultLocalInputValueFor(date: Date, timeZone?: string): string {
  const zone = resolveTimeZone(timeZone);
  const parts = zone ? zonedParts(date, zone) : {
    year: date.getFullYear(),
    month: date.getMonth() + 1,
    day: date.getDate(),
    hour: date.getHours(),
    minute: date.getMinutes(),
  };

  return `${parts.year}-${pad2(parts.month)}-${pad2(parts.day)}T${pad2(parts.hour)}:${pad2(parts.minute)}`;
}

/** Today as a `YYYY-MM-DD` string in the user's local timezone. */
export function toLocalDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function shiftDateKey(dateKey: string, days: number): string {
  const [year, month, day] = dateKey.split('-').map(Number);
  const date = new Date(year, (month || 1) - 1, day || 1);
  date.setDate(date.getDate() + days);
  return toLocalDateKey(date);
}

export function parseDateKey(dateKey: string): Date {
  const [year, month, day] = dateKey.split('-').map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

/**
 * Build a naive ISO datetime (`2026-10-03T09:00:00`) for a given local date
 * key and `HH:MM` time. The backend stores these as naive UTC values, so no
 * timezone suffix is attached.
 */
export function toNaiveIso(dateKey: string, time: string): string {
  return `${dateKey}T${time.length === 5 ? `${time}:00` : time}`;
}

export function formatTimeOnly(value: string): string {
  const match = /T(\d{2}:\d{2})/.exec(value);
  if (match) return match[1];

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

export function formatLongDate(value: string | Date): string {
  const date = typeof value === 'string' ? parseDateKey(value) : value;
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatShortDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/**
 * Extract the `YYYY-MM-DD` portion of a backend naive datetime. Used for
 * client-side day grouping so we don't have to re-parse with the local zone
 * (which would shift events across midnight).
 */
export function dateKeyOfNaive(value: string): string {
  return value.slice(0, 10);
}