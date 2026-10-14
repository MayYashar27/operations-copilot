import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import type { DailyTrendItem } from '../../api/types'
import { Sparkline } from '../../components/charts/Sparkline'
import { average, formatDayMonth, formatNumber, formatWeekdayShort, percentChange } from '../../lib/format'

type Direction = 'up-good' | 'up-bad' | 'neutral'

interface KpiSpec {
  label: string
  unit?: string
  digits: number
  direction: Direction
  pick: (d: DailyTrendItem) => number | null
}

const KPIS: KpiSpec[] = [
  { label: 'Requests', digits: 0, direction: 'neutral', pick: (d) => d.total_requests },
  { label: 'Average wait', unit: 'min', digits: 1, direction: 'up-bad', pick: (d) => d.average_wait_time_minutes },
  { label: 'Abandoned calls', digits: 0, direction: 'up-bad', pick: (d) => d.abandoned_calls },
  { label: 'Available agents', digits: 1, direction: 'up-good', pick: (d) => d.average_available_agents },
]

/** The shift's headline numbers, each compared with the earlier days in the report window. */
export function KpiBand({ trend, date }: { trend: DailyTrendItem[]; date: string }) {
  const today = trend.find((d) => d.date === date)
  if (!today) return null
  const earlier = trend.filter((d) => d.date !== date)

  return (
    <section aria-label="Shift metrics" className="grid grid-cols-2 overflow-hidden rounded-2xl border border-line bg-surface shadow-panel lg:grid-cols-4">
      {KPIS.map((kpi, i) => {
        const value = kpi.pick(today)
        const baseline = average(earlier.map(kpi.pick))
        const change = percentChange(value, baseline)
        return (
          <div
            key={kpi.label}
            className={`flex flex-col px-5 pt-5 pb-4 ${i % 2 === 1 ? 'border-l border-line-soft' : ''} ${
              i >= 2 ? 'border-t border-line-soft lg:border-t-0' : ''
            } ${i === 2 ? 'lg:border-l' : ''}`}
          >
            <p className="text-[12.5px] font-medium text-ink-3">{kpi.label}</p>
            <p className="mt-2 flex items-baseline gap-1">
              <span className="text-[30px] leading-none font-semibold tracking-[-0.03em] text-ink">
                {formatNumber(value, kpi.digits)}
              </span>
              {kpi.unit && <span className="text-[13px] font-medium text-ink-3">{kpi.unit}</span>}
            </p>
            <Delta change={change} direction={kpi.direction} days={earlier.length} />
            <div className="mt-4">
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

function Delta({ change, direction, days }: { change: number | null; direction: Direction; days: number }) {
  if (change === null || days === 0) return <p className="mt-2 h-5 text-[12px] text-ink-3">No baseline</p>

  const flat = Math.abs(change) < 0.5
  const up = change > 0
  const good = direction === 'neutral' || flat ? null : (direction === 'up-good') === up
  const Icon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight
  const tone = good === null ? 'text-ink-2 bg-line-soft' : good ? 'text-good bg-good/8' : 'text-bad bg-bad/8'

  return (
    <p className="mt-2 flex h-5 items-center gap-1.5 text-[12px] text-ink-3">
      <span className={`inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-semibold tabular ${tone}`}>
        <Icon className="size-3" strokeWidth={2.5} />
        {flat ? 'Flat' : `${Math.abs(change).toFixed(1)}%`}
      </span>
      vs {days}-day avg
    </p>
  )
}
