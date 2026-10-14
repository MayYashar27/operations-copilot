import { ArrowRight, ChevronRight, CircleCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { AgentRow, StatusCounts } from '../../api/types'
import { AgentMonogram } from '../../components/ui/AgentMonogram'
import { SourceIcon } from '../../components/ui/SourceTag'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { attentionShortlist } from '../../lib/attention'
import { signalSentence } from '../../lib/signals'
import { STATUS_META, STATUS_ORDER, TONE_CLASSES } from '../../lib/status'

/** Priority attention: a short list. The full roster lives on the Agents screen. */
export function AttentionCard({ rows, counts, total }: { rows: AgentRow[]; counts: StatusCounts; total: number }) {
  const datedLink = useDatedLink()
  const shortlist = attentionShortlist(rows)
  const aiOnly = rows.filter((r) => r.status === 'findings' && r.rule_signal_codes.length === 0).length

  return (
    <section className="card flex flex-col">
      <header className="px-5 pt-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[15px] font-semibold tracking-[-0.01em]">Priority attention</h2>
          <span className="text-[12px] text-ink-3 tabular">{shortlist.length} of {total} agents</span>
        </div>
        <ScreeningBar counts={counts} total={total} />
      </header>

      {shortlist.length === 0 ? (
        <div className="flex flex-col items-center px-5 py-10 text-center">
          <CircleCheck className="mb-2 size-6 text-status-clear" strokeWidth={1.75} />
          <p className="font-semibold">Nothing needs a closer look</p>
          <p className="mt-1 text-[12.5px] text-ink-3">No deep reviews and no metric signals on this shift.</p>
        </div>
      ) : (
        <ul className="flex-1 space-y-1.5 p-2.5 pt-3">
          {shortlist.map((row, i) => (
            <li key={row.agent_id} className="animate-rise" style={{ animationDelay: `${120 + i * 50}ms` }}>
              <Link
                to={datedLink(`/agents/${row.agent_id}`)}
                className="group block rounded-[14px] p-3 transition-all duration-200 hover:bg-hover"
              >
                <div className="flex items-center gap-3">
                  <AgentMonogram id={row.agent_id} status={row.status} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13.5px] font-semibold">Agent {row.agent_id}</p>
                    <div className="mt-1"><StatusBadge status={row.status} /></div>
                  </div>
                  <ChevronRight className="size-4 text-ink-3 transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
                </div>
                <WhyLines row={row} />
              </Link>
            </li>
          ))}
        </ul>
      )}

      <footer className="mx-5 border-t border-line-soft py-3.5">
        <Link to={datedLink('/agents')} className="link inline-flex items-center gap-1.5 text-[13px]">
          View all {total} agents <ArrowRight className="size-3.5" />
        </Link>
        {aiOnly > 0 && <p className="mt-1 text-[12px] text-ink-3">{aiOnly} more have AI observations on their notes only.</p>}
      </footer>
    </section>
  )
}

/**
 * The specific "why": the strongest metric signal stated with its own
 * numbers, then the lead AI observation. Both are labelled by source.
 */
function WhyLines({ row }: { row: AgentRow }) {
  const [lead, ...rest] = row.rule_signals ?? []
  const aiLead = row.ai_finding_titles[0]
  return (
    <div className="mt-2.5 space-y-1.5 pl-[52px]">
      {lead && (
        <p className="flex items-start gap-1.5 text-[12.5px] leading-snug text-ink-2">
          <SourceIcon source="rule" className="mt-[2px] size-3.5 shrink-0" />
          <span>
            {signalSentence(lead)}
            {rest.length > 0 && <span className="text-ink-3"> · +{rest.length} more {rest.length === 1 ? 'signal' : 'signals'}</span>}
          </span>
        </p>
      )}
      {aiLead && (
        <p className="flex items-start gap-1.5 text-[12.5px] leading-snug text-ink-2">
          <SourceIcon source="ai" className="mt-[2px] size-3.5 shrink-0" />
          <span className="line-clamp-2">{aiLead}</span>
        </p>
      )}
    </div>
  )
}

function ScreeningBar({ counts, total }: { counts: StatusCounts; total: number }) {
  const present = STATUS_ORDER.filter((s) => counts[s] > 0)
  return (
    <div className="mt-3.5">
      <div className="flex h-2 gap-[3px] overflow-hidden rounded-full">
        {present.map((s) => (
          <div key={s} title={`${STATUS_META[s].label}: ${counts[s]}`}
            className={`rounded-full ${TONE_CLASSES[STATUS_META[s].tone].fill}`}
            style={{ width: `${(counts[s] / Math.max(total, 1)) * 100}%` }} />
        ))}
      </div>
      <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11.5px] text-ink-3">
        {present.map((s) => (
          <span key={s} className="inline-flex items-center gap-1">
            <span className={`size-1.5 rounded-full ${TONE_CLASSES[STATUS_META[s].tone].dot}`} />
            <span className="font-semibold text-ink-2 tabular">{counts[s]}</span> {STATUS_META[s].short.toLowerCase()}
          </span>
        ))}
      </p>
    </div>
  )
}
