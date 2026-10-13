import { ArrowRight, CircleCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { PriorityItem } from '../../api/types'
import { Panel } from '../../components/ui/Panel'
import { SourceTag } from '../../components/ui/SourceTag'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { EmptyState } from '../../components/ui/States'

/** Agents whose signals combine into a pattern that merits a deeper review. */
export function PriorityList({ items }: { items: PriorityItem[] }) {
  const datedLink = useDatedLink()

  return (
    <Panel
      title="Recommended for deep review"
      description="Combinations of signals that suggest a closer look. These are prompts for a manager, not conclusions about an employee."
      flush
    >
      {items.length === 0 ? (
        <EmptyState icon={CircleCheck} title="No deep reviews recommended for this day">
          No agent met the criteria that combine multiple signals into a pattern.
        </EmptyState>
      ) : (
        <ul className="divide-y divide-line-soft">
          {items.map((item) => (
            <li key={item.agent_id} className="px-5 py-5">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <Link to={datedLink(`/agents/${item.agent_id}`)} className="text-[15px] font-semibold tracking-[-0.01em] text-ink hover:text-accent">
                  Agent {item.agent_id}
                </Link>
                <StatusBadge status="investigation" />
                <Link to={datedLink(`/agents/${item.agent_id}`)} className="link ml-auto inline-flex items-center gap-1 text-[13px]">
                  Open agent <ArrowRight className="size-3.5" />
                </Link>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <p className="text-[12px] font-medium text-ink-3">Why it was flagged</p>
                    <SourceTag source="rule" label="Rules" />
                  </div>
                  <ul className="space-y-1.5">
                    {item.reasons.map((reason) => (
                      <li key={reason} className="flex gap-2 text-[13px] leading-snug text-ink">
                        <span aria-hidden className="mt-[7px] size-1 shrink-0 rounded-full bg-rule" />
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-lg border border-line-soft bg-subtle p-3.5">
                  <div className="mb-1.5 flex items-center gap-2">
                    <p className="text-[12px] font-medium text-ink-3">Investigation summary</p>
                    <SourceTag source="ai" />
                  </div>
                  {item.investigation_summary ? (
                    <p className="line-clamp-4 text-[13px] leading-relaxed text-ink-2">{item.investigation_summary}</p>
                  ) : (
                    <p className="text-[13px] text-ink-3">No saved investigation yet.</p>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
