import { ArrowUp, Loader2, Lock } from 'lucide-react'
import { useEffect, useRef } from 'react'

export const MAX_QUESTION = 600

interface Props {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  /** Why the composer is disabled, if it is. */
  blockedReason: 'demo' | 'running' | null
  submitting: boolean
}

/** The question input, fixed at the bottom of the workspace (as in the reference). */
export function Composer({ value, onChange, onSubmit, blockedReason, submitting }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const demo = blockedReason === 'demo'
  const tooShort = value.trim().length < 5
  const canSend = !blockedReason && !submitting && !tooShort && value.length <= MAX_QUESTION

  // Grow with the text, up to a few lines.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }, [value])

  return (
    <div className="mx-auto max-w-[880px]">
      <form
        onSubmit={(e) => { e.preventDefault(); if (canSend) onSubmit() }}
        className={`flex items-end gap-2 rounded-[20px] bg-surface p-2 pl-4 shadow-lift ring-1 transition ${demo ? 'ring-line/60' : 'ring-line/60 focus-within:ring-2 focus-within:ring-accent/40'}`}
      >
        {demo && <Lock className="mb-3 size-4 shrink-0 text-ink-3" />}
        <label className="sr-only" htmlFor="copilot-question">Question</label>
        <textarea
          id="copilot-question"
          ref={ref}
          rows={1}
          value={value}
          disabled={demo}
          maxLength={MAX_QUESTION + 50}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              if (canSend) onSubmit()
            }
          }}
          placeholder={demo ? 'Demo mode: new investigations are disabled. Open a saved investigation from the history.' : 'Ask about request volume, wait times, transfers or an agent…'}
          className="min-h-[40px] flex-1 resize-none bg-transparent py-2.5 text-[14px] leading-relaxed text-ink outline-none placeholder:text-ink-3 disabled:cursor-not-allowed"
        />
        {value.length > MAX_QUESTION - 100 && (
          <span className={`mb-3 text-[11px] tabular ${value.length > MAX_QUESTION ? 'text-bad' : 'text-ink-3'}`}>{value.length}/{MAX_QUESTION}</span>
        )}
        <button type="submit" disabled={!canSend} aria-label="Start investigation"
          className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-accent to-accent-2 text-white shadow-accent transition-all hover:-translate-y-px disabled:translate-y-0 disabled:from-line disabled:to-line disabled:text-ink-3 disabled:shadow-none">
          {submitting ? <Loader2 className="size-5 animate-spin" /> : <ArrowUp className="size-5" strokeWidth={2.4} />}
        </button>
      </form>
      <p className="mt-2 text-center text-[11.5px] text-ink-3">
        {blockedReason === 'running'
          ? 'An investigation is running. You can start another when it finishes.'
          : demo
            ? 'Read-only demo: saved investigations open instantly and never call the AI.'
            : 'Runs the existing LangGraph workflow with paid AI calls. Results are saved to history. Enter to send, Shift+Enter for a new line.'}
      </p>
    </div>
  )
}
