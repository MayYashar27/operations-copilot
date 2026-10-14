import { ArrowUpRight, Sparkles, Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { InvestigationSummary } from '../../api/types'
import type { SuggestedQuestion } from '../../lib/questions'

interface Props {
  live: boolean
  suggestions: SuggestedQuestion[]
  examples: InvestigationSummary[]
  onPick: (question: string) => void
}

/** The empty state of a new investigation: what Copilot can do, and where to start. */
export function Welcome({ live, suggestions, examples, onPick }: Props) {
  const datedLink = useDatedLink()

  return (
    <div className="mx-auto flex max-w-[760px] flex-col items-center pt-6 text-center lg:pt-12">
      <span className="flex size-14 animate-rise items-center justify-center rounded-[18px] bg-gradient-to-br from-accent to-accent-2 text-white shadow-accent">
        <Sparkles className="size-6" />
      </span>
      <h2 className="mt-5 text-[24px] font-semibold tracking-[-0.02em]">What should we investigate?</h2>
      <p className="mt-2 max-w-[560px] text-[13.5px] leading-relaxed text-ink-2">
        Copilot investigates with the same deterministic data tools as the rest of the app, then separates observed facts,
        supported patterns and hypotheses. It never states a root cause without direct evidence.
      </p>

      {examples.length > 0 && (
        <div className="mt-8 w-full text-left">
          <p className="mb-2 px-1 text-[12px] font-medium text-ink-3">Open a saved example · instant, no AI call</p>
          <div className="grid gap-2.5 md:grid-cols-3">
            {examples.slice(0, 3).map((ex, i) => (
              <Link key={ex.id} to={datedLink(`/copilot/${ex.id}`)}
                className="group animate-rise rounded-[16px] bg-surface/90 p-4 shadow-card ring-1 ring-white transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lift"
                style={{ animationDelay: `${80 + i * 60}ms` }}>
                <Star className="size-4 text-accent" />
                <p className="mt-2 line-clamp-3 text-[13px] leading-snug font-medium text-ink">{ex.question}</p>
                <p className="mt-2 text-[11.5px] font-semibold text-accent opacity-0 transition group-hover:opacity-100">Open result →</p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {live && suggestions.length > 0 && (
        <div className="mt-6 w-full text-left">
          <p className="mb-2 px-1 text-[12px] font-medium text-ink-3">Suggested for this shift · fills the question box</p>
          <div className="grid gap-2 md:grid-cols-2">
            {suggestions.map((s) => (
              <button key={s.question} type="button" onClick={() => onPick(s.question)}
                className="group flex items-start gap-2 rounded-[14px] bg-surface/80 px-4 py-3 text-left shadow-card ring-1 ring-white transition-all hover:-translate-y-px hover:bg-surface hover:shadow-lift">
                <span className="min-w-0 flex-1">
                  <span className="block text-[13px] leading-snug font-medium">{s.label}</span>
                  <span className="mt-0.5 block text-[11.5px] text-ink-3">{s.reason}</span>
                </span>
                <ArrowUpRight className="mt-0.5 size-4 shrink-0 text-ink-3 group-hover:text-accent" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
