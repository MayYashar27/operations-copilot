import { ArrowDownRight, ArrowUpRight, Clock3, Inbox, Minus, PhoneMissed, UsersRound, type LucideIcon } from 'lucide-react'
import type { DailyTrendItem } from '../../api/types'
import { Sparkline } from '../../components/charts/Sparkline'
import { average, formatDayMonth, formatNumber, formatWeekdayShort, percentChange } from '../../lib/format'

type Direction = 'up-good' | 'up-bad' | 'neutral'

interface KpiSpec {
  label: string
  icon: LucideIcon
  unit?: string
  digits: number
  direction: Direction
  pick: (d: DailyTrendItem) => number | null
}

const KPIS: KpiSpec[] = [
  { label: 'Requests', icon: Inbox, digits: 0, direction: 'neutral', pick: (d) => d.total_requests },
  { label: 'Average wait', icon: Clock3, unit: 'min', digits: 1, direction: 'up-bad', pick: (d) => d.average_wait_time_minutes },
  { label: 'Abandoned calls', icon: PhoneMissed, digits: 0, direction: 'up-bad', pick: (d) => d.abandoned_calls },
  { label: 'Available agents', icon: UsersRound, digits: 1, direction: 'up-good', pick: (d) => d.average_available_agents },
]

/** Compact KPI cards, each compared with the earlier days in the report window. */
export function KpiCards({ trend, date }: { trend: DailyTrendItem[]; date: string }) {
  const today = trend.find((d) => d.date === date)
  if (!today) return null
  const earlier = trend.filter((d) => d.date !== date)

  return (
    <section aria-label="Shift metrics" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {KPIS.map((kpi, i) => {
        const value = kpi.pick(today)
        const change = percentChange(value, average(earlier.map(kpi.pick)))
        return (
          <div key={kpi.label} className="card animate-rise p-4 pb-3 transition-shadow duration-200 hover:shadow-lift"
            style={{ animationDelay: `${i * 50}ms` }}>
            <div className="flex items-center gap-2.5">
              <span className="flex size-8 items-center justify-center rounded-[10px] bg-gradient-to-br from-accent-soft to-ai-bg text-accent">
                <kpi.icon className="size-4" strokeWidth={2} />
              </span>
              <p className="text-[12.5px] font-medium text-ink-2">{kpi.label}</p>
            </div>
            <div className="mt-3 flex flex-wrap items-end justify-between gap-x-2 gap-y-1.5">
              <p className="flex items-baseline gap-1">
                <span className="text-[22px] sm:text-[24px] leading-none font-bold tracking-[-0.03em] text-ink">{formatNumber(value, kpi.digits)}</span>
                {kpi.unit && <span className="text-[12.5px] font-medium text-ink-3">{kpi.unit}</span>}
              </p>
              <Delta change={change} direction={kpi.direction} />
            </div>
            <p className="mt-1 text-[11px] text-ink-3">vs {earlier.length}-day average</p>
            <div className="mt-2">
              <Sparkline
                points={trend.map((d) => ({
                  key: d.date,
                  label: `${formatWeekdayShort(d.date)} ${formatDayMonth(d.date)}`,
                  value: kpi.pick(d),
                  highlight: d.date === date,
                }))}
                format={(v) => `${formatNumber(v, kpi.digits)}${kpi.unit ? ` ${kpi.unit}` : ''}`}
              />
            </div>
          </div>
        )
      })}
    </section>
  )
}

function Delta({ change, direction }: { change: number | null; direction: Direction }) {
  if (change === null) return null
  const flat = Math.abs(change) < 0.5
  const up = change > 0
  const good = direction === 'neutral' || flat ? null : (direction === 'up-good') === up
  const Icon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight
  const tone = good === null ? 'bg-frame text-ink-2' : good ? 'bg-status-clear-bg text-good' : 'bg-status-review-bg text-bad'

  return (
    <span className={`inline-flex items-center gap-0.5 rounded-full px-2 py-[3px] text-[11.5px] font-semibold tabular ${tone}`}>
      <Icon className="size-3" strokeWidth={2.6} />
      {flat ? 'Flat' : `${Math.abs(change).toFixed(1)}%`}
    </span>
  )
}
