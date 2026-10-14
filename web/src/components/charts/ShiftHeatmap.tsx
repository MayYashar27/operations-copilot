import { useState } from 'react'
import type { DailyTrendItem } from '../../api/types'
import { formatDayMonth, formatWeekdayShort } from '../../lib/format'
import { ChartTooltip, TooltipRow } from './ChartTooltip'
import { useElementWidth } from './useElementWidth'

const HOURS = ['08', '09', '10', '11', '12', '13', '14', '15', '16']
// Sequential blue ramp (one hue, light -> dark). Unusual hours use orange instead.
const RAMP = ['var(--color-seq-1)', 'var(--color-seq-2)', 'var(--color-seq-3)', 'var(--color-seq-4)',
  'var(--color-seq-5)', 'var(--color-seq-6)', 'var(--color-seq-7)']

interface Props {
  days: DailyTrendItem[]
  selectedDate: string
}

/** Days x working hours. Color = request volume; orange = an unusual hour. */
export function ShiftHeatmap({ days, selectedDate }: Props) {
  const [containerRef, width] = useElementWidth<HTMLDivElement>()
  const [hovered, setHovered] = useState<{ day: number; hour: number } | null>(null)

  const all = days.flatMap((d) => d.hourly_requests)
  const min = Math.min(...all)
  const max = Math.max(...all)
  const shade = (v: number) => RAMP[Math.min(RAMP.length - 1, Math.floor(((v - min) / Math.max(1, max - min)) * RAMP.length))]
  const isUnusual = (day: DailyTrendItem, hour: number) =>
    day.unusual_hours.some((u) => u.hour.startsWith(HOURS[hour]))

  const labelWidth = 76
  const gap = 3
  const cell = width ? (width - labelWidth - gap * (HOURS.length - 1)) / HOURS.length : 0
  const rowHeight = 20

  const active = hovered ? days[hovered.day] : null

  return (
    <div ref={containerRef} className="relative" onMouseLeave={() => setHovered(null)}>
      <div className="mb-1.5 flex" style={{ paddingLeft: labelWidth }}>
        {HOURS.map((h) => (
          <span key={h} className="text-center text-[11px] text-ink-3 tabular" style={{ width: cell, marginRight: gap }}>{h}</span>
        ))}
      </div>
      <div className="space-y-[3px]" role="img" aria-label="Requests per hour for each recent working day">
        {days.map((day, d) => {
          const selected = day.date === selectedDate
          return (
            <div key={day.date} className="flex items-center">
              <span className={`flex shrink-0 items-baseline gap-1.5 text-[12px] tabular ${selected ? 'font-semibold text-ink' : 'text-ink-2'}`}
                style={{ width: labelWidth }}>
                <span className="w-7 text-ink-3">{formatWeekdayShort(day.date)}</span>
                {formatDayMonth(day.date)}
              </span>
              {day.hourly_requests.map((value, h) => {
                const unusual = isUnusual(day, h)
                const isHovered = hovered?.day === d && hovered.hour === h
                return (
                  <span
                    key={h}
                    onMouseEnter={() => setHovered({ day: d, hour: h })}
                    className={`block rounded-[6px] transition-transform duration-150 ${isHovered ? 'scale-110 ring-2 ring-accent shadow-lift' : ''} ${
                      selected && !isHovered ? 'ring-1 ring-accent/40' : ''
                    }`}
                    style={{
                      width: cell, height: rowHeight, marginRight: h < HOURS.length - 1 ? gap : 0,
                      background: unusual ? 'var(--color-chart-unusual)' : shade(value),
                    }}
                  />
                )
              })}
            </div>
          )
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-[11.5px] text-ink-3">
        <span className="inline-flex items-center gap-1.5">
          Fewer
          <span className="inline-flex gap-[2px]">
            {RAMP.map((c) => <span key={c} className="h-2.5 w-3 rounded-[3px]" style={{ background: c }} />)}
          </span>
          More requests
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-3 rounded-[3px] bg-chart-unusual" /> Unusual hour (≥ 1.5× the day’s average)
        </span>
      </div>

      {active && hovered && (
        <ChartTooltip
          x={labelWidth + (cell + gap) * hovered.hour + cell / 2}
          y={22 + (rowHeight + 3) * hovered.day}
          containerWidth={width}
        >
          <p className="mb-1 text-[11.5px] text-ink-3 tabular">
            {formatWeekdayShort(active.date)} {formatDayMonth(active.date)} · {HOURS[hovered.hour]}:00
          </p>
          <TooltipRow label="Requests" value={String(active.hourly_requests[hovered.hour])} />
          {isUnusual(active, hovered.hour) && <p className="mt-1 text-[11.5px] font-medium text-chart-unusual-ink">Unusual hour</p>}
        </ChartTooltip>
      )}
    </div>
  )
}
