import React, { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, Sparkles, Trash2, Terminal, AlertCircle, Loader2, BarChart3, CheckSquare, Target, Flame, Check, X, Clock, Shield } from 'lucide-react'
import { aiService } from '../services/services'
import { useAuth } from '../context/AuthContext'
import { ThreeSceneFallback } from './three/ThreeSceneFallback'
import { useWebGLCapability } from '../hooks/useWebGLCapability'
import type { ActionStep, ActionPlanSummary, ActionStepStatus } from '../types'

/**
 * The 3D core code-splits here.
 *
 * `AICore3D` transitively imports `three` and `@react-three/fiber` (~600 KB
 * minified). This file used to import it eagerly, and because this view is
 * statically imported by `AppAuthenticated`, that entire payload landed in the
 * initial authenticated chunk for every signed-in user — even the ~none of them
 * who ever open this tab. Deferring it means it downloads the first time the
 * AI tab is actually opened.
 *
 * The visual result is unchanged: `ThreeSceneFallback` was already the
 * component shown while the scene initialised, so it is now doing the same job
 * for the module fetch. Do not make this import eager.
 */
const AICore3D = React.lazy(() =>
  import('./three/AICore3D').then(m => ({ default: m.AICore3D }))
)

type Msg = {
  sender: 'user' | 'ai';
  text: string;
  timestamp?: number;
  // For AI responses that contain action plans
  plan?: any;
  context_used?: string[];
  ai_online?: boolean;
  intent?: string;
  awaiting_user?: boolean;
  clarification_question?: string;
}
const DEFAULT_MSG: Msg[] = [{ sender: 'ai', text: 'AI assistant ready. Ask me about your tasks, goals, habits, schedule or finances.' }]

function storageKey(user: { id?: number; email?: string } | null) {
  const id = user?.id ?? user?.email ?? 'guest'
  return `ai_lifeos_chat_${id}`
}

function loadMessages(key: string): Msg[] {
  try {
    const raw = localStorage.getItem(key)
    if (raw) {
      const p = JSON.parse(raw)
      if (Array.isArray(p) && p.length) return p
    }
  } catch {}
  return DEFAULT_MSG
}

// === 3D / CSS AI CORE VISUAL ===
const AICore = ({ state }: { state: 'idle' | 'thinking' | 'processing' }) => {
  const { canRender3D, detected } = useWebGLCapability()

  // Until detection has run, and on any device we know cannot afford the scene,
  // render the lightweight CSS fallback. The core is an ambient visual for the
  // chat header; skipping it costs no functionality, and on a low-end laptop or
  // phone it avoids a permanent WebGL render loop competing with everything else.
  if (!detected || !canRender3D) {
    return (
      <div className="shrink-0">
        <ThreeSceneFallback />
      </div>
    )
  }

  return (
    <React.Suspense fallback={<ThreeSceneFallback />}>
      <AICore3D
        state={state}
        size={112} // 28 * 4 = 112px (matches md:w-28 md:h-28)
        className="shrink-0"
        enablePointerInteraction={true}
        fallback={<ThreeSceneFallback />}
      />
    </React.Suspense>
  )
}

// === MESSAGE BUBBLE ===
interface MessageBubbleProps {
  message: Msg
  index: number
}

// === STATUS BADGE ===
const StatusBadge: React.FC<{ status: ActionStepStatus }> = ({ status }) => {
  const configs: Record<ActionStepStatus, { icon: React.ReactNode; color: string; label: string }> = {
    pending: { icon: <Clock className="w-3 h-3" />, color: 'text-[rgb(var(--warning))]', label: 'Pending' },
    succeeded: { icon: <Check className="w-3 h-3" />, color: 'text-[rgb(var(--success))]', label: 'Done' },
    failed: { icon: <X className="w-3 h-3" />, color: 'text-[rgb(var(--danger))]', label: 'Failed' },
    skipped: { icon: <Clock className="w-3 h-3" />, color: 'text-[rgb(var(--text-tertiary))]', label: 'Skipped' },
  }
  const { icon, color, label } = configs[status]
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-medium ${color}`}>
      {icon} {label}
    </span>
  )
}

// === ACTION PLAN PANEL ===
interface ActionPlanPanelProps {
  plan: ActionPlanSummary
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

const ActionPlanPanel: React.FC<ActionPlanPanelProps> = ({ plan, onConfirm, onCancel, loading }) => {
  const stepsWithConfirmation = plan.steps.filter(s => s.confirmation_required)

  return (
    <div className="relative mt-4 rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--surface-2))] p-4 animate-fadeInUp">
      <div className="flex items-center justify-between mb-3">
        <h4 className="typo-card-title flex items-center gap-2">
          <Shield className="w-4 h-4 text-[rgb(var(--accent))]" />
          Action plan {plan.requires_confirmation && <span className="text-[12px] text-[rgb(var(--warning))]">(requires confirmation)</span>}
        </h4>
      </div>

      <div className="space-y-2">
        {plan.steps.map((step, idx) => (
          <div key={idx} className="flex items-start gap-2.5 p-3 rounded-lg bg-[rgb(var(--surface-3))] border border-[rgb(var(--border-subtle))]">
            <span className="w-5 h-5 mt-0.5 flex-shrink-0 grid place-items-center text-[11px] font-mono text-[rgb(var(--text-muted))]">
              {step.order}.
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-[rgb(var(--text-primary))]">{step.description}</span>
                <StatusBadge status={step.status} />
                {step.confirmation_required && (
                  <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-[rgb(var(--warning)/0.15)] text-[rgb(var(--warning))] font-medium">
                    Confirm
                  </span>
                )}
              </div>
              {step.target_label && (
                <span className="text-[11px] text-[rgb(var(--text-tertiary))]">
                  Target: {step.target_label} #{step.target_id}
                </span>
              )}
              {step.result_message && step.status !== 'pending' && (
                <span className="text-[11px] mt-1 text-[rgb(var(--text-secondary))]">
                  {step.result_message}
                </span>
              )}
              {step.parameters && Object.keys(step.parameters).length > 0 && step.status !== 'pending' && (
                <details className="mt-1">
                  <summary className="text-[11px] text-[rgb(var(--text-muted))] cursor-pointer">Parameters</summary>
                  <pre className="mt-1 text-[10px] font-mono text-[rgb(var(--text-tertiary))] bg-[rgb(var(--surface-4))] p-2 rounded">
                    {JSON.stringify(step.parameters, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        ))}
      </div>

      {plan.requires_confirmation && stepsWithConfirmation.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[rgb(var(--border-subtle))] flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={loading}
            className="btn-secondary btn-sm"
          >
            <X className="w-3.5 h-3.5" /> Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="btn-danger btn-sm"
          >
            <Check className="w-3.5 h-3.5" /> Confirm & Execute
          </button>
        </div>
      )}
    </div>
  )
}

// === MESSAGE BUBBLE ===
const MessageBubble: React.FC<MessageBubbleProps> = ({ message, index }) => {
  const isUser = message.sender === 'user'

  return (
    // Entrance is a pure-CSS `animation` with a delay, not a `setTimeout` that
    // flips React state. The old version scheduled a state update per bubble on
    // every render pass of the list, so scrolling a long conversation re-rendered
    // every message to recompute a boolean that was already visible.
    <div
      className={`flex items-start gap-2.5 animate-fadeInUp ${isUser ? 'flex-row-reverse' : ''}`}
      style={{ animationDelay: `${Math.min(index, 8) * 30}ms` }}
    >
      {/* A 28px glyph, not a 40px filled avatar tile. Two coloured 40px boxes
          per turn meant the avatar column outweighed the first words of every
          message in a conversation, which is a list, not a social feed. */}
      <span
        className={`w-7 h-7 mt-0.5 rounded-lg grid place-items-center shrink-0 ${
          isUser
            ? 'text-[rgb(var(--text-tertiary))]'
            : 'bg-[rgb(var(--accent))] text-[rgb(var(--text-inverse))]'
        }`}
        aria-hidden="true"
      >
        {isUser ? <User className="w-[15px] h-[15px]" /> : <Bot className="w-[15px] h-[15px]" />}
      </span>

      {/* The AI reply sits on the page surface with a hairline; the user's own
          message is the one filled jade bubble. That inversion is deliberate —
          the accent marks *what you said*, and the assistant's answer reads as
          the neutral document you came to read. */}
      <div
        className={`relative max-w-[78%] px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-[rgb(var(--accent))] text-[rgb(var(--text-inverse))] rounded-xl rounded-tr-sm'
            : 'bg-[rgb(var(--surface-2))] border border-[rgb(var(--border-subtle))] text-[rgb(var(--text-primary))] rounded-xl rounded-tl-sm'
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{message.text}</p>
        {message.timestamp && (
          <span className="absolute -bottom-4 right-0 text-[10px] font-mono text-[rgb(var(--text-muted))]">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  )
}

// === QUICK ACTION ===
interface QuickActionProps {
  label: string
  onClick: () => void
  index: number
  icon: React.ComponentType<{ className?: string }>
}

/* Lucide glyphs rather than the emoji that used to lead each label (📊 ✅ 🎯 🔥).
   The emoji rendered at the platform's own colour — outside the token system,
   and mismatched between Windows, macOS and mobile — so four chips in one row
   looked like they came from four different products. */
const QuickAction: React.FC<QuickActionProps> = ({ label, onClick, index, icon: Icon }) => (
  <button
    onClick={onClick}
    className="inline-flex items-center gap-2 h-10 px-3.5 rounded-lg bg-[rgb(var(--surface-4))] border border-[rgb(var(--border))] text-[13px] font-medium text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))] hover:border-[rgb(var(--accent)/0.4)] hover:bg-[rgb(var(--accent)/0.08)] transition-colors focus-ring animate-fadeInUp"
    style={{ animationDelay: `${150 + index * 50}ms` }}
  >
    <Icon className="w-4 h-4 text-[rgb(var(--accent))]" aria-hidden="true" />
    {label}
  </button>
)

// === MAIN COMPONENT ===
export const AICommandView: React.FC = () => {
  const { user } = useAuth()
  const key = storageKey(user as any)
  const [messages, setMessages] = useState<Msg[]>(() => loadMessages(key))
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [aiState, setAiState] = useState<'idle' | 'thinking' | 'processing'>('idle')
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { setMessages(loadMessages(key)) }, [key])

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(messages.slice(-200)))
    } catch {}
  }, [messages, key])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!loading) inputRef.current?.focus()
  }, [loading])

  const doClear = () => {
    setMessages(DEFAULT_MSG)
    try { localStorage.removeItem(key) } catch {}
    setConfirmOpen(false)
  }

  const handleClear = () => {
    if (messages.length <= 1 && messages[0]?.text === DEFAULT_MSG[0].text) return
    setConfirmOpen(true)
  }

  const [pendingPlan, setPendingPlan] = useState<ActionPlanSummary | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    const conversationId = `conv_${Date.now()}`
    setInput('')
    setMessages(p => [...p, { sender: 'user', text: userMsg, timestamp: Date.now() }])
    setLoading(true)
    setAiState('thinking')

    try {
      const res = await aiService.queryBrain(userMsg, conversationId)
      setAiState('processing')

      // Small delay so the processing state is perceptible rather than a flash.
      await new Promise(r => setTimeout(r, 300))

      const reply = res.response || res.answer || res.message || 'Processed query successfully.'
      const aiMsg: Msg = {
        sender: 'ai',
        text: reply,
        timestamp: Date.now(),
        plan: res.plan,
        context_used: res.context_used,
        ai_online: res.ai_online,
        intent: res.intent,
        awaiting_user: res.awaiting_user,
        clarification_question: res.clarification_question,
      }
      setMessages(p => [...p, aiMsg])

      if (res.awaiting_user && res.plan) {
        setPendingPlan(res.plan)
      }

      setAiState('idle')
    } catch {
      setMessages(p => [...p, { sender: 'ai', text: 'Something went wrong. Please try again.' }])
      setAiState('idle')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    if (!pendingPlan || loading) return
    setLoading(true)
    setAiState('processing')

    try {
      const res = await aiService.confirmAction(pendingPlan.plan_id, `conv_${Date.now()}`)
      setPendingPlan(null)

      const reply = res.response || 'Confirmed and executed.'
      setMessages(p => [...p, {
        sender: 'ai',
        text: reply,
        timestamp: Date.now(),
        plan: res.plan,
        context_used: res.context_used,
        ai_online: res.ai_online,
        intent: res.intent,
      }])
      setAiState('idle')
    } catch {
      setMessages(p => [...p, { sender: 'ai', text: 'Something went wrong during confirmation. Please try again.' }])
      setAiState('idle')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!pendingPlan || loading) return
    setLoading(true)
    setAiState('processing')

    try {
      const res = await aiService.cancelAction(pendingPlan.plan_id, `conv_${Date.now()}`)
      setPendingPlan(null)

      const reply = res.response || 'Cancelled. Nothing was changed.'
      setMessages(p => [...p, {
        sender: 'ai',
        text: reply,
        timestamp: Date.now(),
      }])
      setAiState('idle')
    } catch {
      setMessages(p => [...p, { sender: 'ai', text: 'Something went wrong. Please try again.' }])
      setAiState('idle')
    } finally {
      setLoading(false)
    }
  }

  const quickActions = [
    { label: 'Analyze my productivity', action: 'Analyze my productivity for this week', icon: BarChart3 },
    { label: 'Create a task', action: 'Create a task to study Python tomorrow', icon: CheckSquare },
    { label: 'Track a goal', action: 'Help me track progress on my fitness goal', icon: Target },
    { label: 'Check my habits', action: 'Show me my habit streaks', icon: Flame },
  ]

  const handleQuickAction = (action: string) => {
    if (loading) return
    setInput(action)
    inputRef.current?.focus()
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-10rem)] animate-fadeInUp relative">
      {/* One static radial wash. This page previously carried three
          `blur-3xl` orbs on infinite float animations plus a full-bleed grid
          animating `background-position` across a 30-second loop — the single
          most expensive background in the app, for decoration that conveyed
          nothing and never changed. */}
      <div
        className="absolute inset-0 -z-10 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 0%, rgb(var(--accent) / 0.07) 0%, transparent 65%)' }}
      />

      {/* === HEADER ===
          The command surface this view is named for. It is the only page in the
          app whose primary heading sits beside a live system visual, so the
          heading gets the display treatment and the core gets the space. */}
      <div className="relative flex items-start justify-between gap-4 mb-6 stagger-in">
        <div className="flex items-center gap-4 min-w-0">
          <AICore state={aiState} />
          <div className="min-w-0">
            <p className="section-header-label !m-0 !p-0">
              <Sparkles className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" />
              Command center
            </p>
            <h1 className="typo-h1 mt-1.5">AI Assistant</h1>
            <p className="typo-meta mt-1">
              Reads and writes your LifeOS records
            </p>
          </div>
        </div>
        <button
          onClick={handleClear}
          title="Clear chat history"
          className="btn-ghost btn-sm shrink-0 !text-[rgb(var(--text-tertiary))] hover:!text-[rgb(var(--danger))] hover:!bg-[rgb(var(--danger)/0.1)] focus-ring"
        >
          <Trash2 className="w-4 h-4" /> Clear chat
        </button>
      </div>

      {/* === CONVERSATION ===
          Level-4 elevated surface: the composer is the thing you touch on this
          page, so the whole conversation sits one step above the content cards. */}
      <div
        className="relative card-hero p-5 md:p-6 flex flex-col min-h-[440px] stagger-in"
        style={{ animationDelay: '80ms' }}
      >
        <div ref={listRef} className="relative z-10 flex-1 overflow-y-auto space-y-5 pb-4 scroll-y">
          {messages.length === 1 && messages[0]?.text === DEFAULT_MSG[0].text ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12 animate-fadeInUp">
              <span className="grid place-items-center w-14 h-14 rounded-xl bg-[rgb(var(--accent)/0.08)] border border-[rgb(var(--accent)/0.22)] mb-5">
                <Terminal className="w-6 h-6 text-[rgb(var(--accent))]" aria-hidden="true" />
              </span>
              <h2 className="typo-card-title">Ask your AI assistant</h2>
              <p className="typo-body mt-2 mb-6 max-w-[42ch]">
                Ask a question, or use a quick action below to get started.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {quickActions.map((qa, i) => (
                  <QuickAction
                    key={qa.action}
                    label={qa.label}
                    icon={qa.icon}
                    onClick={() => handleQuickAction(qa.action)}
                    index={i}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {messages.map((msg, idx) => (
                <MessageBubble key={idx} message={msg} index={idx} />
              ))}
              {/* Action plan panel when awaiting confirmation */}
              {pendingPlan && (
                <ActionPlanPanel
                  plan={pendingPlan}
                  onConfirm={handleConfirm}
                  onCancel={handleCancel}
                  loading={loading}
                />
              )}
              {loading && (
                <div className="flex items-start gap-2.5 animate-fadeInUp">
                  <span className="w-7 h-7 mt-0.5 rounded-lg bg-[rgb(var(--accent))] grid place-items-center text-[rgb(var(--text-inverse))] shrink-0">
                    <Bot className="w-[15px] h-[15px]" aria-hidden="true" />
                  </span>
                  {/* One honest pending line. There is no streaming, no staged
                      "thinking" copy and no progress percentage — the request
                      either resolves or it fails, and the label says which of
                      the two real phases it is in. */}
                  <span className="px-3.5 py-2.5 rounded-xl rounded-tl-sm bg-[rgb(var(--surface-2))] border border-[rgb(var(--border-subtle))] text-[13px] text-[rgb(var(--text-tertiary))] flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[rgb(var(--accent))]" aria-hidden="true" />
                    {aiState === 'thinking' ? 'Reading your records…' : 'Applying the change…'}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* === COMPOSER ===
            The one place on this page where a border-and-fill control is right,
            because it is the page's primary action. */}
        <form
          onSubmit={handleSubmit}
          className="relative z-10 pt-4 border-t border-[rgb(var(--border-subtle))] stagger-in"
          style={{ animationDelay: '160ms' }}
        >
          <div className="flex items-center gap-2">
            <div className="relative flex-1 min-w-0">
              <input
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                aria-label="Message the AI assistant"
                placeholder="Ask anything, or describe a change to make…"
                disabled={loading}
                className="input pr-4"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !input.trim()}
              aria-label="Send message"
              className="btn-primary shrink-0 !px-4"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="w-4 h-4" aria-hidden="true" />
              )}
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>
        </form>
      </div>

      {/* === CLEAR CHAT CONFIRMATION === */}
      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fadeIn">
          <button aria-label="Close" onClick={() => setConfirmOpen(false)} className="modal-backdrop absolute inset-0" />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="clear-chat-title"
            className="relative w-full max-w-sm surface-4 p-6 animate-scaleInBounce"
          >
            <div className="flex items-center gap-3 mb-4">
              <span className="w-9 h-9 rounded-lg bg-[rgb(var(--danger)/0.1)] border border-[rgb(var(--danger)/0.28)] grid place-items-center text-[rgb(var(--danger))] shrink-0">
                <AlertCircle className="w-4 h-4" aria-hidden="true" />
              </span>
              <h3 id="clear-chat-title" className="typo-card-title !text-base">Clear chat history?</h3>
            </div>
            <p className="typo-body-sm">
              This will remove your AI assistant conversation for this account. Your tasks, goals, habits and other LifeOS data will not be affected.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <button onClick={() => setConfirmOpen(false)} className="btn-secondary btn-sm focus-ring">
                Cancel
              </button>
              <button onClick={doClear} className="btn-danger btn-sm focus-ring">
                <Trash2 className="w-4 h-4" /> Delete chat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
