import React from 'react'
import { Bell } from 'lucide-react'
import { ReminderModal } from './ReminderModal'

type LinkTarget =
  | { kind: 'task'; id: number; label: string }
  | { kind: 'planner_event'; id: number; label: string }

/**
 * Compact "Remind me" trigger for a task or planner event.
 *
 * It owns nothing but the overlay's open state — the form, the list and every
 * write go through `ReminderModal`, so a reminder created here is identical to
 * one created from the header.
 */
export const RemindMeButton: React.FC<{
  target: LinkTarget
  className?: string
  title?: string
}> = ({ target, className = '', title = 'Set a reminder' }) => {
  const [open, setOpen] = React.useState(false)

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label={`${title} for ${target.label}`}
        title={title}
        // 32px -> 40px. This sits inside dense card action rows, where the old
        // box was below the 44px touch target guideline and genuinely awkward
        // to hit on a touchscreen.
        className={`shrink-0 w-10 h-10 grid place-items-center rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--accent))] hover:border-[rgb(var(--border-hover))] hover:bg-[rgb(var(--surface-hover))] transition-colors focus-ring ${className}`}
      >
        <Bell className="w-4 h-4" />
      </button>

      {open && <ReminderModal open={open} onClose={() => setOpen(false)} target={target} />}
    </>
  )
}
