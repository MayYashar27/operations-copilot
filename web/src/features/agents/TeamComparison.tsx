import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { AgentMetrics, AgentRow } from '../../api/types'
import { Panel } from '../../components/ui/Panel'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { StatusDot } from '../../components/ui/StatusBadge'
import { formatNumber } from '../../lib/format'
import { STATUS_META, STATUS_ORDER, TONE_CLASSES } from '../../lib/status'

type MetricKey = 'transfer' | 'handling' | 'resolution' | 'requests'

const METRICS: Record<MetricKey, { label: string; unit: string; digits: number; pick: (m: AgentMetrics) => number | null }> = {
  transfer: { label: 'Transfer rate', unit: '%', digits: 0, pick: (m) => m.transfer_rate_percent },
  handling: { label: 'Handling time', unit: ' min', digits: 1, pick: (m) => m.average_handling_time_minutes },
  resolution: { label: 'Resolution', unit: '%', digits: 0, pick: (m) => m.first_line_resolution_rate_percent },
  requests: { label: 'Requests', unit: '', digits: 0, pick: (m) => m.handled_requests },
}

/**
 * Every agent on one metric, ranked, against the team value. Neutral bars:
 * being above or below the team is a prompt to look at case mix, not a verdict.
 */
export function TeamComparison({ rows, team }: { rows: AgentRow[]; team: AgentMetrics | null }) {
  const [metric, setMetric] = useState<MetricKey>('transfer')
  const navigate = useNavigate()
  const datedLink = useDatedLink()
  const spec = METRICS[metric]

  const ranked = rows
    .map((row) => ({ row, value: row.metrics ? spec.pick(row.metrics) : null }))
    .sort((a, b) => (b.value ?? -1) - (a.value ?? -1))
  // Team "requests" is a total; compare with the per-agent average instead.
  const teamValue = !team ? null : metric === 'requests' ? team.handled_requests / Math.max(1, rows.length) : spec.pick(team)
  const max = Math.max(...ranked.map((r) => r.value ?? 0), teamValue ?? 0, 1)
  const fmt = (v: number | null) => (v === null ? '—' : `${formatNumber(v, spec.digits)}${spec.unit}`)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {STATUS_ORDER.map((status) => {
          const count = rows.filter((r) => r.status === status).length
          return (
            <div key={status} className="card px-4 py-3.5">
              <p className="flex items-center gap-2 text-[12px] font-medium text-ink-2">
                <span className={`size-2 rounded-full ${TONE_CLASSES[STATUS_META[status].tone].dot}`} />
                {STATUS_META[status].label}
              </p>
              <p className="mt-1.5 text-[22px] leading-none font-bold tracking-[-0.03em] tabular">{count}</p>
            </div>
          )
        })}
      </div>

      <Panel
        title="Performance comparison"
        description={
          <>
            Each agent on the selected shift against the team ({teamValue === null ? 'no baseline' : `${fmt(teamValue)}${metric === 'requests' ? ' per agent' : ''}`}).
            Small request counts make rates volatile, so each row shows its sample size.
          </>
        }
        actions={
          <SegmentedControl label="Metric" value={metric} onChange={setMetric}
            options={(Object.keys(METRICS) as MetricKey[]).map((m) => ({ value: m, label: METRICS[m].label }))} />
        }
      >
        <ul className="relative space-y-0.5 pt-5">
          {teamValue !== null && (
            <span aria-hidden className="pointer-events-none absolute top-0 bottom-0 z-10 w-px bg-ink-3/60"
              style={{ left: `calc(136px + (100% - 252px) * ${teamValue / max})` }}>
              <span className="absolute top-0 -translate-x-1/2 rounded-full bg-ink px-1.5 py-px text-[10px] font-semibold whitespace-nowrap text-white">
                Team
              </span>
            </span>
          )}
          {ranked.map(({ row, value }, i) => (
            <li key={row.agent_id} className="animate-rise" style={{ animationDelay: `${i * 25}ms` }}>
              <button type="button" onClick={() => navigate(datedLink(`/agents/${row.agent_id}`))}
                className="group flex w-full items-center gap-3 rounded-xl px-2 py-1.5 text-left transition-colors hover:bg-hover">
                <span className="flex w-[116px] shrink-0 items-center gap-2">
                  <StatusDot status={row.status} />
                  <span className="text-[13px] font-semibold tabular group-hover:text-accent">{row.agent_id}</span>
                  <span className="text-[11px] text-ink-3 tabular">n={row.metrics?.handled_requests ?? 0}</span>
                </span>
                <span className="relative h-2.5 flex-1 rounded-full bg-frame">
                  <span className="absolute inset-y-0 left-0 rounded-full bg-chart-today transition-all duration-500 group-hover:bg-accent-strong"
                    style={{ width: `${((value ?? 0) / max) * 100}%` }} />
                </span>
                <span className="w-[96px] shrink-0 text-right text-[13px] font-semibold tabular">{fmt(value)}</span>
              </button>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  )
}
