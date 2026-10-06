/**
 * Money helpers.
 *
 * The backend stores amounts as `Numeric(12, 2)` and Pydantic serializes
 * `Decimal` to a JSON string, so amounts arrive as e.g. `"120.00"`. Summing
 * those as JS floats accumulates representation error (0.1 + 0.2 !== 0.3), so
 * totals are accumulated in integer cents and only converted back to a number
 * for display.
 */

export function parseAmountToCents(value: unknown): number {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return 0;
    // Round through a string to sidestep binary float representation.
    return Math.round(Number(value.toFixed(2)) * 100);
  }

  if (typeof value !== 'string') return 0;

  const match = /-?\d+(\.\d+)?/.exec(value.trim());
  if (!match) return 0;

  const cents = Math.round(Number(match[0]) * 100);
  return Number.isFinite(cents) ? cents : 0;
}

export function centsToNumber(cents: number): number {
  return cents / 100;
}

/**
 * Convert a user-entered amount into the decimal string the API expects, so
 * the backend's Decimal parsing never receives float noise (e.g. 12.30 ->
 * "12.30" rather than 12.300000000000001).
 */
export function toAmountString(value: string | number): string {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '0.00';
    return value.toFixed(2);
  }

  const match = /-?\d+(\.\d+)?/.exec(value.trim());
  if (!match) return '0.00';
  return Number(match[0]).toFixed(2);
}

export function formatCurrency(value: number, fractionDigits = 0): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}