import type { DayMetrics } from '../../api/types'
import { formatNumber } from '../../lib/format'

interface Stat {
  label: string
  value: string
  unit?: string
  hint: string
}

/** The day's service-center numbers in one compact row. */
export function ServiceCenterStrip({ metrics }: { metrics: DayMetrics }) {
  const stats: Stat[] = [
    { label: 'Requests received', value: formatNumber(metrics.total_requests), hint: '08:00 – 17:00' },
    {
      label: 'Average wait',
      value: formatNumber(metrics.average_wait_time_minutes, 1),
      unit: 'min',
      hint: 'Per request',
    },
    { label: 'Abandoned calls', value: formatNumber(metrics.abandoned_calls), hint: 'From monitor snapshots' },
    {
      label: 'Available agents',
      value: formatNumber(metrics.average_available_agents, 1),
      hint: 'Average across the day',
    },
  ]

  return (
    <section aria-label="Service center today" className="rounded-xl border border-line bg-surface shadow-panel">
      <dl className="grid grid-cols-2 md:grid-cols-4">
        {stats.map((stat, i) => (
          <div
            key={stat.label}
            className={`px-5 py-4 ${i % 2 === 1 ? 'border-l border-line-soft' : ''} ${
              i >= 2 ? 'border-t border-line-soft md:border-t-0' : ''
            } ${i === 2 ? 'md:border-l' : ''}`}
          >
            <dt className="text-[12.5px] font-medium text-ink-3">{stat.label}</dt>
            <dd className="mt-1.5 flex items-baseline gap-1">
              <span className="text-[24px] leading-none font-semibold tracking-[-0.02em] text-ink">{stat.value}</span>
              {stat.unit && <span className="text-[13px] font-medium text-ink-3">{stat.unit}</span>}
            </dd>
            <dd className="mt-1.5 text-[12px] text-ink-3">{stat.hint}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
