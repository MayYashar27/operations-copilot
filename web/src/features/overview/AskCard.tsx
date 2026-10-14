import { ArrowUp, ArrowUpRight, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { DailyTrendItem } from '../../api/types'
import { copilotLink, suggestedQuestions } from '../../lib/questions'

/**
 * The entry point to Ask Copilot, styled like its composer. Links only
 * pre-fill a question; nothing runs until it is submitted on that screen.
 */
export function AskCard({ date, trend }: { date: string; trend: DailyTrendItem[] }) {
  const questions = suggestedQuestions(date, trend).slice(0, 4)

  return (
    <section className="relative overflow-hidden rounded-[var(--radius-card)] bg-gradient-to-br from-accent-soft via-surface to-ai-bg p-5 shadow-card ring-1 ring-white">
      <div aria-hidden className="absolute -top-16 -right-16 size-48 rounded-full bg-accent-2/15 blur-3xl" />
      <div className="relative">
        <div className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-[10px] bg-gradient-to-br from-accent to-accent-2 text-white shadow-accent">
            <Sparkles className="size-4" strokeWidth={2} />
          </span>
          <div>
            <h2 className="text-[15px] font-semibold tracking-[-0.01em]">Ask Copilot</h2>
            <p className="text-[12px] text-ink-3">Investigates with the same data tools</p>
          </div>
        </div>

        <ul className="mt-4 space-y-2">
          {questions.map((q) => (
            <li key={q.question}>
              <Link to={copilotLink(q.question, date)}
                className="group flex items-start gap-2 rounded-xl bg-surface/80 px-3.5 py-2.5 shadow-card ring-1 ring-white transition-all duration-200 hover:-translate-y-px hover:bg-surface hover:shadow-lift">
                <span className="min-w-0 flex-1 text-[12.5px] leading-snug font-medium text-ink">{q.label}</span>
                <ArrowUpRight className="mt-px size-3.5 shrink-0 text-ink-3 transition group-hover:text-accent" />
              </Link>
            </li>
          ))}
        </ul>

        <Link to={copilotLink('', date)}
          className="mt-4 flex h-12 items-center gap-2 rounded-2xl bg-surface pr-1.5 pl-4 shadow-card ring-1 ring-line/60 transition hover:shadow-lift">
          <span className="flex-1 text-[13px] text-ink-3">Ask something about this shift…</span>
          <span className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-accent-2 text-white shadow-accent">
            <ArrowUp className="size-4" strokeWidth={2.4} />
          </span>
        </Link>
      </div>
    </section>
  )
}
