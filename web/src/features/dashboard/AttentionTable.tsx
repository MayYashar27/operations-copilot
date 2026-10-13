import { ChevronRight, FileSearch, Inbox } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { AgentRow } from '../../api/types'
import { Panel } from '../../components/ui/Panel'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { SourceIcon } from '../../components/ui/SourceTag'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { EmptyState } from '../../components/ui/States'
import { formatMinutes, formatNumber, formatPercent } from '../../lib/format'
import { signalLabel } from '../../lib/signals'
import { STATUS_ORDER } from '../../lib/status'

type Filter = 'all' | 'metric' | 'ai-only'

const needsReview = (row: AgentRow) => row.status === 'investigation' || row.status === 'findings'
const hasMetricSignals = (row: AgentRow) => row.rule_signal_codes.length > 0

/** Most actionable first: status, then hard metric signals, then AI observations. */
function compareRows(a: AgentRow, b: AgentRow): number {
  return (
    STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) ||
    b.rule_signal_codes.length - a.rule_signal_codes.length ||
    b.ai_observation_count - a.ai_observation_count ||
    a.agent_id.localeCompare(b.agent_id)
  )
}

export function AttentionTable({ rows }: { rows: AgentRow[] }) {
  const [filter, setFilter] = useState<Filter>('all')
  const navigate = useNavigate()
  const datedLink = useDatedLink()

  const reviewRows = useMemo(() => rows.filter(needsReview).sort(compareRows), [rows])
  const metricCount = reviewRows.filter(hasMetricSignals).length
  const visible = reviewRows.filter((row) =>
    filter === 'all' ? true : filter === 'metric' ? hasMetricSignals(row) : !hasMetricSignals(row),
  )

  return (
    <Panel
      title="Agents to review"
      description={`${reviewRows.length} of ${rows.length} agents have findings. Metric signals come from threshold rules; AI observations come from reading documentation.`}
      actions={
        <SegmentedControl
          label="Filter by evidence"
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'all', label: 'All', count: reviewRows.length },
            { value: 'metric', label: 'Metric signals', count: metricCount },
            { value: 'ai-only', label: 'AI only', count: reviewRows.length - metricCount },
          ]}
        />
      }
      flush
    >
      {visible.length === 0 ? (
        <EmptyState icon={Inbox} title="No agents in this view" />
      ) : (
        <div className="relative overflow-x-auto">
          <table className="w-full min-w-[720px] text-[13px]">
            <thead>
              <tr className="border-b border-line-soft bg-subtle text-left text-[12px] whitespace-nowrap text-ink-3">
                <th className="py-2.5 pr-3 pl-5 font-medium">Agent</th>
                <th className="px-3 py-2.5 font-medium">Status</th>
                <th className="px-3 py-2.5 text-right font-medium">Requests</th>
                <th className="px-3 py-2.5 text-right font-medium">Transfer rate</th>
                <th className="hidden px-3 py-2.5 text-right font-medium md:table-cell">Avg. handling</th>
                <th className="px-3 py-2.5 font-medium">Metric signals</th>
                <th className="px-3 py-2.5 font-medium">AI observations</th>
                <th className="py-2.5 pr-5 pl-3"><span className="sr-only">Open</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {visible.map((row) => (
                <tr
                  key={row.agent_id}
                  onClick={() => navigate(datedLink(`/agents/${row.agent_id}`))}
                  className="group cursor-pointer transition-colors hover:bg-hover"
                >
                  <td className="py-3 pr-3 pl-5">
                    <Link
                      to={datedLink(`/agents/${row.agent_id}`)}
                      onClick={(event) => event.stopPropagation()}
                      className="font-semibold text-ink tabular hover:text-accent"
                    >
                      {row.agent_id}
                    </Link>
                  </td>
                  <td className="px-3 py-3"><StatusBadge status={row.status} compact /></td>
                  <td className="px-3 py-3 text-right tabular">{formatNumber(row.metrics?.handled_requests)}</td>
                  <td className="px-3 py-3 text-right tabular">{formatPercent(row.metrics?.transfer_rate_percent)}</td>
                  <td className="hidden px-3 py-3 text-right tabular md:table-cell">
                    {formatMinutes(row.metrics?.average_handling_time_minutes)}
                  </td>
                  <td className="px-3 py-3">
                    <MetricSignalsCell codes={row.rule_signal_codes} />
                  </td>
                  <td className="px-3 py-3">
                    {row.ai_observation_count > 0 ? (
                      <span className="inline-flex items-center gap-1.5 text-ink-2">
                        <SourceIcon source="ai" />
                        <span className="tabular">{row.ai_observation_count}</span>
                        {row.has_investigation && (
                          <span title="A saved investigation is available" className="ml-1 inline-flex items-center gap-1 text-[12px] text-ink-3">
                            <FileSearch className="size-3.5" /> Investigated
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-ink-3">None</span>
                    )}
                  </td>
                  <td className="py-3 pr-5 pl-3 text-right">
                    <ChevronRight className="ml-auto size-4 text-ink-3 transition-transform group-hover:translate-x-0.5 group-hover:text-ink-2" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}

function MetricSignalsCell({ codes }: { codes: string[] }) {
  if (codes.length === 0) return <span className="text-ink-3">None</span>
  const [first, ...rest] = codes
  return (
    <span className="inline-flex max-w-[260px] items-center gap-1.5" title={codes.map(signalLabel).join('\n')}>
      <SourceIcon source="rule" className="size-3.5 shrink-0" />
      <span className="truncate text-ink">{signalLabel(first)}</span>
      {rest.length > 0 && <span className="shrink-0 text-ink-3 tabular">+{rest.length}</span>}
    </span>
  )
}
