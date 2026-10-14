import { ArrowUpRight, MessageSquareText } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { DailyTrendItem } from '../../api/types'
import { copilotLink, suggestedQuestions } from '../../lib/questions'

/**
 * The entry point to Ask Copilot. Dark, so it reads as a different kind of
 * action from the read-only panels around it. Links only pre-fill a question;
 * nothing runs until the user submits it on the Ask Copilot screen.
 */
export function AskPanel({ date, trend }: { date: string; trend: DailyTrendItem[] }) {
  const questions = suggestedQuestions(date, trend)

  return (
    <section className="overflow-hidden rounded-2xl bg-night text-night-ink shadow-lift">
      <div className="px-5 pt-5">
        <div className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-lg bg-ai/25">
            <MessageSquareText className="size-4 text-night-ai" />
          </span>
          <h2 className="text-[15px] font-semibold tracking-[-0.01em]">Ask about this shift</h2>
        </div>
        <p className="mt-2 text-[12.5px] leading-relaxed text-night-ink-2">
          Copilot investigates with the same data tools, then separates facts from hypotheses.
        </p>

        <Link
          to={copilotLink('', date)}
          className="mt-4 flex h-10 items-center rounded-lg border border-night-line bg-night-2 px-3 text-[13px] text-night-ink-3 transition-colors hover:border-night-ink-3 hover:text-night-ink-2"
        >
          Ask a question about operations…
        </Link>
      </div>

      <p className="mt-5 px-5 text-[11px] font-semibold tracking-[0.08em] text-night-ink-3 uppercase">Suggested</p>
      <ul className="p-2 pt-1.5">
        {questions.map((q) => (
          <li key={q.question}>
            <Link to={copilotLink(q.question, date)}
              className="group flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-night-2">
              <span className="min-w-0 flex-1">
                <span className="block text-[13px] leading-snug font-medium text-night-ink">{q.label}</span>
                <span className="mt-0.5 block text-[11.5px] text-night-ink-3">{q.reason}</span>
              </span>
              <ArrowUpRight className="mt-0.5 size-4 shrink-0 text-night-ink-3 transition group-hover:-translate-y-px group-hover:translate-x-px group-hover:text-night-ink" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
