import { ArrowRight, ChevronRight, CircleCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { AgentRow, StatusCounts } from '../../api/types'
import { AgentMonogram } from '../../components/ui/AgentMonogram'
import { SourceIcon } from '../../components/ui/SourceTag'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { attentionShortlist } from '../../lib/attention'
import { signalLabel } from '../../lib/signals'
import { STATUS_META, STATUS_ORDER, TONE_CLASSES } from '../../lib/status'

/** A short, prioritized list. The full roster lives on the Agents screen. */
export function AttentionQueue({ rows, counts, total }: { rows: AgentRow[]; counts: StatusCounts; total: number }) {
  const datedLink = useDatedLink()
  const shortlist = attentionShortlist(rows)
  const aiOnly = rows.filter((r) => r.status === 'findings' && r.rule_signal_codes.length === 0).length

  return (
    <section className="rounded-2xl border border-line bg-surface shadow-panel">
      <header className="px-5 pt-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[15px] font-semibold tracking-[-0.01em]">Needs attention</h2>
          <span className="text-[12.5px] text-ink-3 tabular">{shortlist.length} of {total} agents</span>
        </div>
        <ScreeningBar counts={counts} total={total} />
      </header>

      {shortlist.length === 0 ? (
        <div className="flex flex-col items-center px-5 py-10 text-center">
          <CircleCheck className="mb-2 size-6 text-status-clear" strokeWidth={1.75} />
          <p className="font-medium">Nothing needs a closer look</p>
          <p className="mt-1 text-[13px] text-ink-3">No deep reviews and no metric signals on this shift.</p>
        </div>
      ) : (
        <ul className="space-y-1 p-2 pt-3">
          {shortlist.map((row) => (
            <li key={row.agent_id}>
              <Link
                to={datedLink(`/agents/${row.agent_id}`)}
                className="group block rounded-xl p-3 transition-all duration-200 hover:-translate-y-px hover:bg-subtle hover:shadow-lift"
              >
                <div className="flex items-center gap-3">
                  <AgentMonogram id={row.agent_id} status={row.status} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[14px] font-semibold">Agent {row.agent_id}</p>
                    <div className="mt-0.5"><StatusBadge status={row.status} /></div>
                  </div>
                  <ChevronRight className="size-4 text-ink-3 transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
                </div>
                <WhyLine row={row} />
              </Link>
            </li>
          ))}
        </ul>
      )}

      <footer className="border-t border-line-soft px-5 py-3.5">
        <Link to={datedLink('/agents')} className="link inline-flex items-center gap-1.5 text-[13px]">
          View all {total} agents <ArrowRight className="size-3.5" />
        </Link>
        {aiOnly > 0 && (
          <p className="mt-1 text-[12px] text-ink-3">
            {aiOnly} more have AI observations on their notes only.
          </p>
        )}
      </footer>
    </section>
  )
}

/** The concise "why": metric signals first, then the lead AI observation. */
function WhyLine({ row }: { row: AgentRow }) {
  const signals = row.rule_signal_codes
  const aiLead = row.ai_finding_titles[0]
  return (
    <div className="mt-2.5 space-y-1.5 pl-[52px]">
      {signals.length > 0 && (
        <p className="flex items-start gap-1.5 text-[12.5px] leading-snug text-ink-2">
          <SourceIcon source="rule" className="mt-[2px] size-3.5 shrink-0" />
          <span>
            {signals.slice(0, 2).map(signalLabel).join(' · ')}
            {signals.length > 2 && <span className="text-ink-3"> · +{signals.length - 2}</span>}
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
  return (
    <div className="mt-3">
      <div className="flex h-1.5 gap-0.5 overflow-hidden rounded-full bg-line-soft">
        {STATUS_ORDER.filter((s) => counts[s] > 0).map((s) => (
          <div key={s} title={`${STATUS_META[s].label}: ${counts[s]}`}
            className={TONE_CLASSES[STATUS_META[s].tone].fill} style={{ width: `${(counts[s] / Math.max(total, 1)) * 100}%` }} />
        ))}
      </div>
      <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11.5px] text-ink-3">
        {STATUS_ORDER.filter((s) => counts[s] > 0).map((s) => (
          <span key={s} className="inline-flex items-center gap-1">
            <span className={`size-1.5 rounded-full ${TONE_CLASSES[STATUS_META[s].tone].dot}`} />
            <span className="font-semibold text-ink-2 tabular">{counts[s]}</span> {STATUS_META[s].short.toLowerCase()}
          </span>
        ))}
      </p>
    </div>
  )
}
