import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  DollarSign, Plus, ArrowUpRight, ArrowDownRight, TrendingUp, TrendingDown, Wallet, CreditCard,
  Trash2, Loader2, PieChart, BarChart3, Pencil, AlertCircle, Filter, Check,
} from 'lucide-react'
import { transactionService } from '../services/services'
import { extractErrorMessage } from '../utils/apiError'
import { runLegacyMigration, getLegacyMigrationSummary } from '../utils/legacyMigration'
import { useAuth } from '../context/AuthContext'
import { centsToNumber, formatCurrency, parseAmountToCents } from '../utils/money'
import { formatShortDate, toLocalDateKey } from '../utils/datetime'
import type { Transaction, TransactionType } from '../types'

// === SUMMARY CARD ===
// Small metric card used in the finance summary grid. Inline to keep the
// component self-contained and avoid a separate export for a single-use pattern.
const SummaryCard: React.FC<{
  label: string
  value: number
  prefix: string
  icon: React.ElementType
  color: string
  bg: string
  index: number
}> = ({ label, value, prefix, icon: Icon, color, bg, index }) => (
  <div className={`card-secondary p-5 stagger-in ${bg}`} style={{ animationDelay: `${index * 60}ms` }}>
    <p className="typo-micro text-[rgb(var(--text-tertiary))]">{label}</p>
    <div className="mt-1 flex items-end gap-1.5">
      <Icon className={`w-4 h-4 ${color}`} aria-hidden="true" />
      <p className={`typo-numeric text-[22px] font-semibold leading-none ${color}`}>
        {prefix}{formatCurrency(Math.abs(value))}
      </p>
    </div>
  </div>
)

/**
 * The header used three display-serif counters on tinted cards, each with a
 * 40px icon tile and a coloured blob at the top. Net balance led with income
 * and expenses equal-weight, so the page answered "what is the number?" three
 * times instead of "what happened this period?" once.
 *
 * The new layout: Net leads at display scale (it's the result), Income and
 * Expenses sit below as supporting lines with directional glyphs. No icon
 * tiles, no coloured blobs, no display-serif numbers.
 */
const SummaryHeader: React.FC<{
  totals: { income: number; expense: number; net: number }
}> = ({ totals }) => {
  const isPositive = totals.net >= 0
  return (
    <section aria-label="Finance summary" className="card-secondary p-6 stagger-in">
      {/* Net is the figure this panel exists to answer, so it leads and is set
          at display scale. Income and expenses sit beneath as two supporting
          lines with a directional glyph — the previous version gave all three
          equal-size tiles with their own coloured icon boxes, so the panel read
          as three unrelated numbers rather than one result plus its inputs. */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
        <div className="lg:col-span-1">
          <p className="typo-micro">Net movement</p>
          <p
            className={`typo-numeric mt-1.5 text-[32px] font-bold leading-none tracking-tight ${
              isPositive ? 'text-[rgb(var(--success))]' : 'text-[rgb(var(--danger))]'
            }`}
          >
            {isPositive ? '+' : '−'}{formatCurrency(Math.abs(totals.net))}
          </p>
        </div>

        <dl className="lg:col-span-2 mt-2 lg:mt-0 grid grid-cols-2 gap-4">
          <div className="border-t border-[rgb(var(--border-subtle))] pt-4 lg:pt-0">
            <dt className="flex items-center gap-1.5 typo-micro !text-[11px] !normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--success))]">
              <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
              Income
            </dt>
            <dd className="typo-numeric mt-1 text-[22px] font-semibold leading-none text-[rgb(var(--text-primary))] truncate">
              {formatCurrency(totals.income)}
            </dd>
          </div>

          <div className="border-t border-[rgb(var(--border-subtle))] pt-4 lg:pt-0">
            <dt className="flex items-center gap-1.5 typo-micro !text-[11px] !normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--danger))]">
              <ArrowDownRight className="w-3.5 h-3.5" aria-hidden="true" />
              Expenses
            </dt>
            <dd className="typo-numeric mt-1 text-[22px] font-semibold leading-none text-[rgb(var(--text-primary))] truncate">
              {formatCurrency(totals.expense)}
            </dd>
          </div>
        </dl>
      </div>
    </section>
  )
}

// === CATEGORY BREAKDOWN ===
const CategoryBreakdown: React.FC<{ transactions: Transaction[]; index: number }> = ({ transactions, index }) => {
  // Accumulate in integer cents so category totals don't drift with float error.
  const categories = useMemo(() => {
    const map = new Map<string, { income: number; expense: number }>()
    transactions.forEach(t => {
      const cents = parseAmountToCents(t.amount)
      const existing = map.get(t.category) || { income: 0, expense: 0 }
      if (t.type === 'income') existing.income += cents
      else existing.expense += cents
      map.set(t.category, existing)
    })
    return Array.from(map.entries()).map(([name, data]) => ({
      name,
      income: centsToNumber(data.income),
      expense: centsToNumber(data.expense),
    })).sort((a, b) => b.expense - a.expense)
  }, [transactions])

  if (categories.length === 0) return null

  return (
    <section aria-label="Category breakdown" className="card-secondary p-5 stagger-in" style={{ animationDelay: `${200 + index * 60}ms` }}>
      <div className="section-header">
        <div className="min-w-0">
          <p className="section-header-label">
            <PieChart className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" aria-hidden="true" />
            Categories
          </p>
          <h3 className="section-header-title mt-2">Expense breakdown</h3>
        </div>
        <span className="typo-micro">{categories.length} categories</span>
      </div>

      <ul className="row-stack mt-4">
        {categories.slice(0, 5).map(cat => (
          <li key={cat.name} className="row-item !p-3 !items-start !gap-3">
            <div className="flex-1 min-w-0">
              <p className="typo-body-sm !font-medium !text-[rgb(var(--text-primary))] truncate">{cat.name}</p>
              <div className="flex items-center gap-3 mt-1 typo-micro">
                {cat.income > 0 && (
                  <span className="!normal-case !tracking-normal text-[rgb(var(--accent-secondary))]">+{formatCurrency(cat.income)}</span>
                )}
                {cat.expense > 0 && (
                  <span className="!normal-case !tracking-normal text-[rgb(var(--danger))]">−{formatCurrency(cat.expense)}</span>
                )}
              </div>
            </div>
            {cat.expense > 0 && (
              <div className="w-24 h-1.5 rounded-full bg-[rgb(var(--surface-4))] overflow-hidden shrink-0">
                <div
                  className="h-full rounded-full bg-[rgb(var(--danger))] transition-all duration-700 ease-out"
                  style={{ width: `${Math.min(100, (cat.expense / Math.max(...categories.map(c => c.expense), 1))) * 100}%` }}
                />
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

// === TRANSACTION ROW ===
interface TransactionRowProps {
  transaction: Transaction
  onDelete: (transaction: Transaction) => void
  onEdit: (transaction: Transaction) => void
  index: number
  busyId: number | null
  editingId: number | null
}

const TransactionRow: React.FC<TransactionRowProps> = ({ transaction, onDelete, onEdit, index, busyId, editingId }) => {
  const isBusy = busyId === transaction.id
  const isIncome = transaction.type === 'income'

  return (
    <button
      type="button"
      className={`row-item !p-3 !gap-3 stagger-in-fast ${
        editingId === transaction.id ? '!border-l-2 !border-l-[rgb(var(--accent))] !pl-[15px]' : ''
      }`}
      style={{ animationDelay: `${100 + index * 30}ms` }}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <span className={`w-2 h-2 rounded-full shrink-0 ${isIncome ? 'bg-[rgb(var(--accent-secondary))]' : 'bg-[rgb(var(--danger))]'}`} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <h4 className="typo-body !font-semibold !leading-tight !text-[rgb(var(--text-primary))] truncate">
            {transaction.title}
          </h4>
          <div className="mt-1 flex items-center gap-2 typo-micro">
            <span className="!normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--text-tertiary))]">{transaction.category}</span>
            <span className="!normal-case !tracking-normal text-[rgb(var(--text-muted))]">{formatShortDate(transaction.transaction_date)}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <span
          className={`typo-numeric text-[14px] font-bold ${
            isIncome ? 'text-[rgb(var(--accent-secondary))]' : 'text-[rgb(var(--danger))]'
          }`}
        >
          {isIncome ? '+' : '−'}{formatCurrency(transaction.amount, 2)}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onEdit(transaction) }}
          disabled={isBusy}
          aria-label={`Edit ${transaction.title}`}
          className="btn-icon focus-ring hover:!text-[rgb(var(--accent))] disabled:opacity-50"
        >
          <Pencil className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(transaction) }}
          disabled={isBusy}
          aria-label={`Delete ${transaction.title}`}
          className="btn-icon focus-ring hover:!text-[rgb(var(--danger))] hover:!bg-[rgb(var(--danger)/0.1)] disabled:opacity-50"
          title="Delete transaction"
        >
          {isBusy ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Trash2 className="w-4 h-4" />}
        </button>
      </div>
    </button>
  )
}

// === TRANSACTION FORM (create + edit) ===
interface TransactionFormProps {
  editing: Transaction | null
  submitting: boolean
  error: string | null
  onSubmit: (data: { title: string; amount: number; type: TransactionType; category: string; transactionDate: string }) => void
  onCancel: () => void
}

const TransactionForm: React.FC<TransactionFormProps> = ({ editing, submitting, error, onSubmit, onCancel }) => {
  const [title, setTitle] = useState(editing?.title || '')
  const [amount, setAmount] = useState(editing ? String(editing.amount) : '')
  const [type, setType] = useState<TransactionType>(editing?.type || 'expense')
  const [category, setCategory] = useState(editing?.category || 'Tech')
  const [transactionDate, setTransactionDate] = useState(editing?.transaction_date || toLocalDateKey(new Date()))

  const amountValid = /^\d+(\.\d{1,2})?$/.test(amount.trim()) && parseAmountToCents(amount) > 0

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !amountValid) return
    onSubmit({
      title: title.trim(),
      amount: parseAmountToCents(amount) / 100,
      type,
      category: category.trim() || 'General',
      transactionDate,
    })
    if (!editing) {
      setTitle('')
      setAmount('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card-input p-5 space-y-4 stagger-in" style={{ animationDelay: '80ms' }}>
      <p className="typo-label">{editing ? `Edit · ${editing.title}` : 'Add transaction'}</p>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="relative">
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Title…"
            aria-label="Transaction title"
            required
            className="input input-icon-left"
          />
          <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>
        <div className="relative">
          <input
            type="number"
            value={amount}
            onChange={e => setAmount(e.target.value)}
            placeholder="Amount ($)"
            aria-label="Amount in dollars"
            required
            min="0.01"
            step="0.01"
            className="input input-icon-left"
          />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-mono text-[rgb(var(--text-tertiary))] pointer-events-none">$</span>
        </div>
        <div className="relative">
          <select
            value={type}
            onChange={e => setType(e.target.value as TransactionType)}
            aria-label="Transaction type"
            className="input input-icon-left"
          >
            <option value="expense">Expense</option>
            <option value="income">Income</option>
          </select>
          {type === 'income' ? (
            <ArrowUpRight className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--accent-secondary))] pointer-events-none" aria-hidden="true" />
          ) : (
            <ArrowDownRight className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--danger))] pointer-events-none" aria-hidden="true" />
          )}
        </div>
        <div className="relative">
          <input
            value={category}
            onChange={e => setCategory(e.target.value)}
            placeholder="Category"
            aria-label="Category"
            className="input input-icon-left"
          />
          <BarChart3 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="relative md:col-span-1">
          <input
            type="date"
            value={transactionDate}
            onChange={e => setTransactionDate(e.target.value)}
            aria-label="Transaction date"
            required
            className="input input-icon-left"
          />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 typo-micro pointer-events-none">DATE</span>
        </div>
      </div>

      {error && (
        <p role="alert" className="text-[13px] text-[rgb(var(--danger))] flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" /> {error}
        </p>
      )}

      <div className="flex justify-end gap-2">
        {editing && (
          <button type="button" onClick={onCancel} className="btn-secondary focus-ring">
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={submitting || !title.trim() || !amountValid}
          className="btn-primary focus-ring disabled:opacity-50"
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : editing ? <Check className="w-4 h-4" aria-hidden="true" /> : <Plus className="w-4 h-4" aria-hidden="true" />}
          {editing ? 'Save changes' : 'Add transaction'}
        </button>
      </div>
    </form>
  )
}

// === FILTER BAR ===
const FilterBar: React.FC<{
  typeFilter: TransactionType | ''
  setTypeFilter: (v: TransactionType | '') => void
  categoryFilter: string
  setCategoryFilter: (v: string) => void
  categories: string[]
  total: number
  filtered: number
}> = ({ typeFilter, setTypeFilter, categoryFilter, setCategoryFilter, categories, total, filtered }) => (
  <div className="flex flex-wrap items-center gap-2">
    <Filter className="w-4 h-4 text-[rgb(var(--text-tertiary))] shrink-0" aria-hidden="true" />
    <div role="group" aria-label="Filter by type" className="inline-flex p-1 rounded-lg bg-[rgb(var(--surface-3))] border border-[rgb(var(--border-subtle))]">
      {(['', 'income', 'expense'] as const).map(t => (
        <button
          key={t || 'all'}
          onClick={() => setTypeFilter(t)}
          aria-pressed={typeFilter === t}
          className={`h-9 px-3.5 rounded-lg text-xs font-mono whitespace-nowrap transition-colors duration-200 focus-ring capitalize ${
            typeFilter === t
              ? 'bg-[rgb(var(--surface-4))] text-[rgb(var(--accent))] shadow-[var(--depth-1)]'
              : 'text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--text-primary))]'
          }`}
        >
          {t || 'All'}
        </button>
      ))}
    </div>

    <select
      value={categoryFilter}
      onChange={e => setCategoryFilter(e.target.value)}
      aria-label="Filter by category"
      className="input input-sm !w-auto !h-9 !pl-2.5 !pr-9 !text-[12px] !border-dashed cursor-pointer max-w-[14rem]"
    >
      <option value="">All categories</option>
      {categories.map(c => <option key={c} value={c}>{c}</option>)}
    </select>

    {(typeFilter || categoryFilter) && (
      <span className="ml-auto typo-micro">Showing {filtered} of {total}</span>
    )}
  </div>
)

// === EMPTY STATE ===
const EmptyState: React.FC<{ hasFilter: boolean }> = ({ hasFilter }) => (
  <div className="card-secondary p-10 flex flex-col items-center justify-center text-center stagger-in">
    <span className="grid place-items-center w-12 h-12 rounded-xl mb-4 bg-[rgb(var(--surface-4))] border border-[rgb(var(--border-subtle))] text-[rgb(var(--text-tertiary))]" aria-hidden="true">
      <DollarSign className="w-5 h-5" />
    </span>
    <h3 className="typo-card-title">{hasFilter ? 'No matching transactions' : 'No transactions yet'}</h3>
    <p className="typo-body-sm mt-1.5 max-w-sm">
      {hasFilter
        ? 'Try clearing the type or category filter.'
        : 'Record your first income or expense above and the summaries update as you add more.'}
    </p>
  </div>
)

// === ERROR STATE ===
const ErrorState: React.FC<{ message: string; onRetry: () => void }> = ({ message, onRetry }) => (
  <div className="card-secondary p-8 flex flex-col items-center justify-center text-center stagger-in">
    <span className="grid place-items-center w-10 h-10 rounded-xl mb-3 bg-[rgb(var(--danger)/0.1)] border border-[rgb(var(--danger)/0.25)] text-[rgb(var(--danger))]" aria-hidden="true">
      <AlertCircle className="w-5 h-5" />
    </span>
    <h3 className="typo-card-title">Could not load your transactions</h3>
    <p className="typo-body-sm mt-1.5 max-w-sm">{message}</p>
    <button onClick={onRetry} className="btn-primary btn-sm mt-5 focus-ring">
      <Loader2 className="w-4 h-4" aria-hidden="true" /> Try again
    </button>
  </div>
)

// === LOADING SKELETON ===
const FinanceSkeleton: React.FC = () => (
  <div className="space-y-6" aria-busy="true" aria-label="Loading transactions">
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="card-secondary p-5">
          <div className="h-4 w-24 skeleton rounded" />
          <div className="mt-3 h-8 w-32 skeleton rounded" />
        </div>
      ))}
    </div>
    <section aria-label="Transactions" className="card-secondary p-5">
      <div className="row-stack">
        {[1, 2, 3].map(i => (
          <div key={i} className="row-item !p-3">
            <div className="w-2 h-2 rounded-full skeleton shrink-0" />
            <div className="flex-1 min-w-0 space-y-1">
              <div className="w-32 h-4 skeleton rounded" />
              <div className="w-20 h-3 skeleton rounded" />
            </div>
            <div className="w-16 h-4 skeleton rounded shrink-0" />
          </div>
        ))}
      </div>
    </section>
  </div>
)

// === MAIN COMPONENT ===
export const FinanceView: React.FC = () => {
  const { user } = useAuth()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<TransactionType | ''>('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [migrationNotice, setMigrationNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      // Date-range and category filters are applied client-side against the
      // loaded set so the filter chips stay derived from real categories.
      const data = await transactionService.getTransactions()
      setTransactions(data)
    } catch (e) {
      setTransactions([])
      setLoadError(extractErrorMessage(e, 'Failed to load transactions.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // One-time import of any legacy localStorage finance records.
  useEffect(() => {
    if (!user?.id) return
    let active = true
    const migrate = async () => {
      try {
        const result = await runLegacyMigration(user.id, user.id)
        if (!active) return
        const summary = getLegacyMigrationSummary(result)
        if (summary) {
          setMigrationNotice(summary)
          setLoadError(null)
          await load()
        }
      } catch {
        /* migration is best-effort */
      }
    }
    migrate()
    return () => { active = false }
  }, [user?.id])

  const categories = useMemo(() => [...new Set(transactions.map(t => t.category))].sort(), [transactions])

  const filteredTransactions = useMemo(() => {
    return transactions.filter(t => {
      const matchesType = !typeFilter || t.type === typeFilter
      const matchesCategory = !categoryFilter || t.category === categoryFilter
      return matchesType && matchesCategory
    })
  }, [transactions, typeFilter, categoryFilter])

  // Totals accumulate in integer cents, then convert once for display.
  const totals = useMemo(() => {
    const incomeCents = transactions.filter(t => t.type === 'income').reduce((sum, t) => sum + parseAmountToCents(t.amount), 0)
    const expenseCents = transactions.filter(t => t.type === 'expense').reduce((sum, t) => sum + parseAmountToCents(t.amount), 0)
    return {
      income: centsToNumber(incomeCents),
      expense: centsToNumber(expenseCents),
      net: centsToNumber(incomeCents - expenseCents),
      average: transactions.length > 0 ? centsToNumber(Math.round(transactions.reduce((s, t) => s + parseAmountToCents(t.amount), 0) / transactions.length)) : 0,
    }
  }, [transactions])

  const incomeCount = useMemo(() => transactions.filter(t => t.type === 'income').length, [transactions])
  const expenseCount = useMemo(() => transactions.filter(t => t.type === 'expense').length, [transactions])

  const sortedTransactions = useMemo(() => {
    return [...filteredTransactions].sort((a, b) => {
      if (a.transaction_date !== b.transaction_date) return b.transaction_date.localeCompare(a.transaction_date)
      return b.created_at.localeCompare(a.created_at)
    })
  }, [filteredTransactions])

  const handleSubmit = async (data: { title: string; amount: number; type: TransactionType; category: string; transactionDate: string }) => {
    setSubmitting(true)
    setFormError(null)
    try {
      if (editing) {
        await transactionService.updateTransaction(editing.id, {
          title: data.title,
          amount: data.amount,
          type: data.type,
          category: data.category,
          transaction_date: data.transactionDate,
        })
        setEditing(null)
      } else {
        await transactionService.createTransaction({
          title: data.title,
          amount: data.amount,
          type: data.type,
          category: data.category,
          transaction_date: data.transactionDate,
        })
      }
      await load()
    } catch (e) {
      setFormError(extractErrorMessage(e, 'Could not save the transaction.'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (transaction: Transaction) => {
    if (!window.confirm(`Delete "${transaction.title}"? This cannot be undone.`)) return
    setBusyId(transaction.id)
    try {
      await transactionService.deleteTransaction(transaction.id)
      if (editing?.id === transaction.id) setEditing(null)
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not delete the transaction.'))
    } finally {
      setBusyId(null)
    }
  }

  if (loading) return <FinanceSkeleton />

  return (
    <div className="space-y-6 animate-fadeInUp">
      {/* === HEADER ===
          No 40px icon tile: a label carries the orientation, the title is
          typography. */}
      <div className="stagger-in">
        <p className="section-header-label !m-0 !p-0">
          <DollarSign className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" aria-hidden="true" />
          Money
        </p>
        <h1 className="typo-h1 mt-2">Finance</h1>
        <p className="typo-meta mt-1.5">
          Income and expenses you have recorded. Totals are calculated from those records.
        </p>
      </div>

      {migrationNotice && (
        <div
          role="status"
          className="card px-4 py-3 rounded-xl border border-[rgb(var(--accent-secondary) / 0.3)] bg-[rgb(var(--accent-secondary) / 0.08)] flex items-center gap-2 text-sm text-[rgb(var(--accent-secondary))] animate-fadeInUp"
        >
          <Check className="w-4 h-4 shrink-0" />
          {migrationNotice}
          <button
            onClick={() => setMigrationNotice(null)}
            className="ml-auto text-xs font-mono opacity-70 hover:opacity-100 focus-ring rounded px-1"
          >
            dismiss
          </button>
        </div>
      )}

      {/* === SUMMARY CARDS === */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard
          label="Net Balance"
          value={totals.net}
          prefix={totals.net >= 0 ? '$' : '-$'}
          icon={Wallet}
          color={totals.net >= 0 ? 'text-[rgb(var(--accent-secondary))]' : 'text-[rgb(var(--danger))]'}
          bg={totals.net >= 0 ? 'bg-[rgb(var(--accent-secondary) / 0.12)]' : 'bg-[rgb(var(--danger) / 0.12)]'}
          index={0}
        />
        <SummaryCard
          label="Total Income"
          value={totals.income}
          prefix="$"
          icon={TrendingUp}
          color="text-[rgb(var(--accent-tertiary))]"
          bg="bg-[rgb(var(--accent-tertiary) / 0.12)]"
          index={1}
        />
        <SummaryCard
          label="Total Expenses"
          value={totals.expense}
          prefix="$"
          icon={TrendingDown}
          color="text-[rgb(var(--danger))]"
          bg="bg-[rgb(var(--danger) / 0.12)]"
          index={2}
        />
      </div>

      {/* === TRANSACTION FORM === */}
      <TransactionForm
        editing={editing}
        submitting={submitting}
        error={formError}
        onSubmit={handleSubmit}
        onCancel={() => { setEditing(null); setFormError(null) }}
      />

      {/* === MAIN CONTENT GRID === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="stagger-in card p-6">
            <div className="flex items-center justify-between mb-4 gap-3">
              <h2 className="font-display font-semibold text-base flex items-center gap-2 text-[rgb(var(--text-primary))]">
                <span className="w-10 h-10 grid place-items-center rounded-xl bg-[rgb(var(--accent) / 0.12)] border border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))]">
                  <CreditCard className="w-4 h-4" />
                </span>
                Transactions
              </h2>
              {transactions.length > 0 && (
                <span className="px-2.5 py-1 rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-xs font-mono text-[rgb(var(--text-secondary))] shrink-0">
                  {transactions.length} total
                </span>
              )}
            </div>

            {transactions.length > 0 && (
              <div className="mb-4">
                <FilterBar
                  typeFilter={typeFilter}
                  setTypeFilter={setTypeFilter}
                  categoryFilter={categoryFilter}
                  setCategoryFilter={setCategoryFilter}
                  categories={categories}
                  total={transactions.length}
                  filtered={filteredTransactions.length}
                />
              </div>
            )}

            {loadError && transactions.length === 0 ? (
              <ErrorState message={loadError} onRetry={load} />
            ) : sortedTransactions.length === 0 ? (
              <EmptyState hasFilter={!!typeFilter || !!categoryFilter} />
            ) : (
              <div className="space-y-2.5">
                {loadError && (
                  <div role="alert" className="flex items-start gap-2 text-xs font-mono text-[rgb(var(--danger))] px-1">
                    <AlertCircle className="w-4 h-4 shrink-0" /> {loadError}
                  </div>
                )}
                {sortedTransactions.map((tx, i) => (
                  <TransactionRow
                    key={tx.id}
                    transaction={tx}
                    onDelete={handleDelete}
                    onEdit={(t) => { setEditing(t); setFormError(null) }}
                    index={i}
                    busyId={busyId}
                    editingId={editing?.id ?? null}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: Category Breakdown + Quick Stats */}
        <div className="space-y-6">
          <CategoryBreakdown transactions={transactions} index={0} />

          <div className="stagger-in card p-5" style={{ animationDelay: '120ms' }}>
            <h3 className="font-display font-semibold text-base flex items-center gap-2 text-[rgb(var(--text-primary))] mb-4">
              <span className="w-10 h-10 grid place-items-center rounded-xl bg-[rgb(var(--accent) / 0.12)] border border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))]">
                <BarChart3 className="w-4 h-4" />
              </span>
              Quick stats
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-[rgb(var(--surface) / 0.6)] border border-[rgb(var(--border))]">
                <span className="text-[rgb(var(--text-secondary))]">Avg. transaction</span>
                <span className="font-mono font-semibold text-[rgb(var(--text-primary))]">
                  ${formatCurrency(totals.average, 2)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-[rgb(var(--surface) / 0.6)] border border-[rgb(var(--border))]">
                <span className="text-[rgb(var(--text-secondary))]">Income / expense</span>
                <span className="font-mono font-semibold">
                  <span className="text-[rgb(var(--accent-secondary))]">{incomeCount}</span>
                  <span className="text-[rgb(var(--text-muted))] mx-1">/</span>
                  <span className="text-[rgb(var(--danger))]">{expenseCount}</span>
                </span>
              </div>
              <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-[rgb(var(--surface) / 0.6)] border border-[rgb(var(--border))]">
                <span className="text-[rgb(var(--text-secondary))]">Categories</span>
                <span className="font-mono font-semibold text-[rgb(var(--text-primary))]">
                  {categories.length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}