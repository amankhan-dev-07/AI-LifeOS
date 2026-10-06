import React from 'react'
import { ArrowUpRight, ArrowDownRight, ArrowRight } from 'lucide-react'
import { formatCurrency, parseAmountToCents, centsToNumber } from '../../utils/money'
import type { FinanceSignal } from '../../types'

/**
 * Finance snapshot.
 *
 * A factual read of the backend's `FinanceSignal`: income, expenses, net
 * movement, entry count and the top expense categories for the current calendar
 * month. Arithmetic is done in integer cents and converted once for display, so
 * the figures cannot drift with float error.
 *
 * This is reporting, not advice. Nothing here interprets whether a number is
 * good or bad; the net figure is coloured by sign and nothing else.
 */

interface FinanceSnapshotProps {
  finance: FinanceSignal | null
  onNavigate: (route: string) => void
}

export const FinanceSnapshot: React.FC<FinanceSnapshotProps> = ({ finance, onNavigate }) => {
  if (!finance) {
    return (
      <section aria-label="Finance" className="card-secondary p-6 stagger-in">
        <Header onNavigate={onNavigate} />
        <Empty
          title="No transactions yet"
          body="Log an income or expense and this section summarises the current month. Nothing is inferred before you record something."
          onNavigate={onNavigate}
        />
      </section>
    )
  }

  // Accumulate in integer cents, then convert once for display.
  const incomeCents = parseAmountToCents(finance.income_total)
  const expenseCents = parseAmountToCents(finance.expense_total)
  const netCents = incomeCents - expenseCents

  const income = centsToNumber(incomeCents)
  const expenses = centsToNumber(expenseCents)
  const net = centsToNumber(netCents)
  const isPositive = net >= 0

  // The backend orders these by transaction count, which is what it can
  // support; it deliberately does not rank by amount.
  const topCategories = finance.top_expense_categories.slice(0, 3)

  return (
    <section aria-label="Finance" className="card-secondary p-6 stagger-in">
      <Header onNavigate={onNavigate} period={finance.period_start} count={finance.transaction_count} />

      {/* Net is the figure this panel exists to answer, so it leads and is set
          at display scale. Income and expenses sit beneath as two supporting
          lines with a directional glyph — the previous version gave all three
          equal-size tiles with their own coloured icon boxes, so the panel read
          as three unrelated numbers rather than one result plus its inputs. */}
      <div className="mt-4">
        <p className="typo-micro">Net movement</p>
        <p
          className={`typo-numeric mt-1.5 text-[32px] font-bold leading-none tracking-tight ${
            isPositive ? 'text-[rgb(var(--success))]' : 'text-[rgb(var(--danger))]'
          }`}
        >
          {isPositive ? '+' : '−'}{formatCurrency(Math.abs(net))}
        </p>

        <dl className="mt-4 grid grid-cols-2 gap-3">
          <div className="border-t border-[rgb(var(--border-subtle))] pt-3">
            <dt className="flex items-center gap-1.5 text-[11px] font-medium text-[rgb(var(--text-tertiary))]">
              <ArrowUpRight className="w-3.5 h-3.5 text-[rgb(var(--success))]" aria-hidden="true" />
              Income
            </dt>
            <dd className="typo-numeric mt-1 text-[17px] font-semibold leading-none text-[rgb(var(--text-primary))] truncate">
              {formatCurrency(income)}
            </dd>
          </div>

          <div className="border-t border-[rgb(var(--border-subtle))] pt-3">
            <dt className="flex items-center gap-1.5 text-[11px] font-medium text-[rgb(var(--text-tertiary))]">
              <ArrowDownRight className="w-3.5 h-3.5 text-[rgb(var(--danger))]" aria-hidden="true" />
              Expenses
            </dt>
            <dd className="typo-numeric mt-1 text-[17px] font-semibold leading-none text-[rgb(var(--text-primary))] truncate">
              {formatCurrency(expenses)}
            </dd>
          </div>
        </dl>
      </div>

      {topCategories.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[rgb(var(--border-subtle))]">
          <p className="typo-micro">Most active expense categories</p>
          <ul className="mt-2.5 flex flex-wrap gap-1.5">
            {topCategories.map((category) => (
              <li
                key={category.category}
                className="text-[11px] px-2 py-1 rounded-md bg-[rgb(var(--surface-4))] border border-[rgb(var(--border-subtle))] text-[rgb(var(--text-secondary))]"
                title={`${category.category}: ${formatCurrency(centsToNumber(parseAmountToCents(category.total)))} this period`}
              >
                {category.category}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function formatPeriod(periodStart: string): string {
  const [year, month] = periodStart.split('-');
  const index = Number(month) - 1;
  const names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const name = names[index] ?? month;
  return `${name} ${year}`;
}

const Header: React.FC<{
  onNavigate: (route: string) => void
  period?: string
  count?: number
}> = ({ onNavigate, period, count }) => (
  <div className="section-header">
    <div className="min-w-0">
      <p className="section-header-label flex-wrap">
        Money
        {period && (
          <>
            <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))]" aria-hidden="true" />
            <span className="!normal-case !tracking-[0.06em] !font-normal">{formatPeriod(period)}</span>
          </>
        )}
        {count !== undefined && (
          <>
            <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))]" aria-hidden="true" />
            <span className="!normal-case !tracking-[0.06em] !font-normal">
              {count} entr{count !== 1 ? 'ies' : 'y'}
            </span>
          </>
        )}
      </p>
      <h2 className="section-header-title mt-2">Finance</h2>
    </div>
    <button
      onClick={() => onNavigate('finance')}
      className="shrink-0 inline-flex items-center gap-1 text-[13px] font-medium text-accent text-accent-hover transition-colors focus-ring rounded"
    >
      Open
      <ArrowUpRight className="w-3.5 h-3.5" />
    </button>
  </div>
)

const Empty: React.FC<{
  title: string;
  body: string;
  onNavigate: (route: string) => void
}> = ({ title, body, onNavigate }) => (
  <div className="text-center py-8">
    <p className="typo-body !font-medium">{title}</p>
    <p className="typo-meta mt-1.5 max-w-[42ch] mx-auto mb-5">{body}</p>
    <button onClick={() => onNavigate('finance')} className="btn-secondary btn-sm focus-ring">
      Record a transaction <ArrowRight className="w-3.5 h-3.5" />
    </button>
  </div>
)