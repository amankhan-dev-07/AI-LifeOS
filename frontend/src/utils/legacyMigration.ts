import { noteService, transactionService } from '../services/services';
import { toLocalDateKey } from './datetime';

/**
 * One-time import of legacy localStorage notes and finance records into the
 * authenticated user's database rows.
 *
 * Guarantees:
 *  - Records are always scoped to the *current* authenticated user (the
 *    backend derives ownership from the access token).
 *  - A per-user marker in localStorage prevents re-importing on refresh.
 *  - Existing backend records are never overwritten; duplicates are skipped
 *    by a title/date/amount signature match.
 *  - The legacy keys are only removed after every record has been confirmed
 *    persisted. On any failure the data is left untouched.
 */

const NOTES_KEY = 'ai_lifeos_notes';
const FINANCE_KEY = 'ai_lifeos_finance';
const MIGRATION_KEY = 'ai_lifeos_migration_v1';

type MigrationState = Record<string, unknown>;

interface MigrationResult {
  notesImported: number;
  notesSkipped: number;
  transactionsImported: number;
  transactionsSkipped: number;
}

function readState(): MigrationState {
  try {
    const raw = localStorage.getItem(MIGRATION_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as MigrationState) : {};
  } catch {
    return {};
  }
}

function writeState(state: MigrationState) {
  try {
    localStorage.setItem(MIGRATION_KEY, JSON.stringify(state));
  } catch {}
}

function readLegacy<T>(key: string): T[] | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as T[]) : null;
  } catch {
    return null;
  }
}

interface LegacyNote {
  id?: number;
  title?: string;
  content?: string;
  tag?: string;
}

interface LegacyTransaction {
  id?: number;
  title?: string;
  amount?: number | string;
  type?: string;
  category?: string;
  date?: string;
}

/** "2026-10-01" -> "2026-10-01"; otherwise today. */
function normalizeDate(value: unknown): string {
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    return value.slice(0, 10);
  }
  return toLocalDateKey(new Date());
}

function isUsableTitle(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

async function migrateNotes(): Promise<{ imported: number; skipped: number; done: boolean }> {
  const legacy = readLegacy<LegacyNote>(NOTES_KEY);
  if (!legacy) return { imported: 0, skipped: 0, done: true };

  const existing = await noteService.getNotes({ isArchived: false });
  const seen = new Set(existing.map((n) => `${n.title}::${n.tag}`));

  let imported = 0;
  let skipped = 0;

  for (const item of legacy) {
    if (!isUsableTitle(item?.title)) {
      skipped += 1;
      continue;
    }

    const title = item.title.trim();
    const tag = typeof item.tag === 'string' && item.tag.trim() ? item.tag.trim() : 'General';
    const signature = `${title}::${tag}`;
    if (seen.has(signature)) {
      skipped += 1;
      continue;
    }

    await noteService.createNote({
      title,
      content: typeof item.content === 'string' ? item.content : '',
      tag,
    });

    seen.add(signature);
    imported += 1;
  }

  return { imported, skipped, done: true };
}

async function migrateTransactions(): Promise<{ imported: number; skipped: number; done: boolean }> {
  const legacy = readLegacy<LegacyTransaction>(FINANCE_KEY);
  if (!legacy) return { imported: 0, skipped: 0, done: true };

  const existing = await transactionService.getTransactions();
  const seen = new Set(existing.map((t) => `${t.title}::${t.transaction_date}::${t.amount}::${t.type}`));

  let imported = 0;
  let skipped = 0;

  for (const item of legacy) {
    const amount = Number(item?.amount);
    const type = item?.type === 'income' ? 'income' : item?.type === 'expense' ? 'expense' : null;

    if (!isUsableTitle(item?.title) || !Number.isFinite(amount) || amount <= 0 || !type) {
      skipped += 1;
      continue;
    }

    const title = item.title.trim();
    const transactionDate = normalizeDate(item.date);
    const category = typeof item.category === 'string' && item.category.trim() ? item.category.trim() : 'General';
    const normalizedAmount = Number(amount.toFixed(2));
    const signature = `${title}::${transactionDate}::${normalizedAmount}::${type}`;

    if (seen.has(signature)) {
      skipped += 1;
      continue;
    }

    await transactionService.createTransaction({
      title,
      amount: normalizedAmount,
      type,
      category,
      transaction_date: transactionDate,
    });

    seen.add(signature);
    imported += 1;
  }

  return { imported, skipped, done: true };
}

/**
 * Runs the legacy import once per authenticated user. Safe to call on every
 * authenticated bootstrap — subsequent calls are no-ops.
 */
export async function runLegacyMigration(
  userId: number,
  currentUserId: number,
): Promise<MigrationResult> {
  const empty: MigrationResult = {
    notesImported: 0,
    notesSkipped: 0,
    transactionsImported: 0,
    transactionsSkipped: 0,
  };

  if (!userId || userId !== currentUserId) return empty;

  const state = readState();
  const notesDone = state[`notes:${userId}`] === true;
  const financeDone = state[`finance:${userId}`] === true;

  if (notesDone && financeDone) return empty;

  const nextState: MigrationState = { ...state };
  let notesImported = 0;
  let notesSkipped = 0;
  let transactionsImported = 0;
  let transactionsSkipped = 0;

  if (!notesDone) {
    try {
      const result = await migrateNotes();
      notesImported = result.imported;
      notesSkipped = result.skipped;
      // Only flip the marker (and allow key removal) once every record landed.
      nextState[`notes:${userId}`] = true;
      localStorage.removeItem(NOTES_KEY);
    } catch {
      return {
        notesImported,
        notesSkipped,
        transactionsImported,
        transactionsSkipped,
      };
    }
  }

  if (!financeDone) {
    try {
      const result = await migrateTransactions();
      transactionsImported = result.imported;
      transactionsSkipped = result.skipped;
      nextState[`finance:${userId}`] = true;
      localStorage.removeItem(FINANCE_KEY);
    } catch {
      writeState(nextState);
      return {
        notesImported,
        notesSkipped,
        transactionsImported,
        transactionsSkipped,
      };
    }
  }

  writeState(nextState);

  return {
    notesImported,
    notesSkipped,
    transactionsImported,
    transactionsSkipped,
  };
}

export function getLegacyMigrationSummary(result: MigrationResult): string | null {
  const parts: string[] = [];
  if (result.notesImported > 0) {
    parts.push(`${result.notesImported} note${result.notesImported === 1 ? '' : 's'}`);
  }
  if (result.transactionsImported > 0) {
    parts.push(
      `${result.transactionsImported} transaction${result.transactionsImported === 1 ? '' : 's'}`,
    );
  }
  if (!parts.length) return null;
  return `Imported ${parts.join(' and ')} from this browser into your account.`;
}