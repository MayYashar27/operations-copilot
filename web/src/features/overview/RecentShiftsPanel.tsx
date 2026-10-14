import { MessageSquareText } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { DailyTrendItem } from '../../api/types'
import { ShiftHeatmap } from '../../components/charts/ShiftHeatmap'
import { Panel } from '../../components/ui/Panel'
import { formatDayMonth, formatWeekdayShort } from '../../lib/format'
import { copilotLink } from '../../lib/questions'

/** Recent shifts at a glance, and the unusual hours worth asking about. */
export function RecentShiftsPanel({ trend, date }: { trend: DailyTrendItem[]; date: string }) {
  const anomalies = trend
    .flatMap((day) => day.unusual_hours.map((hour) => ({ day, hour })))
    .sort((a, b) => b.day.date.localeCompare(a.day.date))

  return (
    <Panel
      title="Recent shifts"
      description={`Requests per hour over the last ${trend.length} working days.`}
    >
      <ShiftHeatmap days={trend} selectedDate={date} />

      <div className="mt-6 border-t border-line-soft pt-5">
        <p className="mb-3 text-[13px] font-semibold text-ink">
          Unusual hours <span className="font-normal text-ink-3">· {anomalies.length} in this period</span>
        </p>
        {anomalies.length === 0 ? (
          <p className="text-[13px] text-ink-3">No hour reached 1.5× its day’s average.</p>
        ) : (
          <ol className="relative space-y-1 before:absolute before:top-2 before:bottom-2 before:left-[5px] before:w-px before:bg-line">
            {anomalies.map(({ day, hour }) => {
              const [start, end] = hour.hour.split('-')
              const question = `There was an unusually high workload on ${day.date} between ${start} and ${end}. Investigate what happened and explain the likely cause.`
              return (
                <li key={`${day.date}-${hour.hour}`}
                  className="group relative flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg py-2 pr-2 pl-6 transition-colors hover:bg-hover">
                  <span aria-hidden className="absolute top-1/2 left-0 size-[11px] -translate-y-1/2 rounded-full border-2 border-surface bg-chart-unusual" />
                  <span className="w-[92px] text-[13px] font-medium text-ink tabular">
                    {formatWeekdayShort(day.date)} {formatDayMonth(day.date)}
                  </span>
                  <span className="text-[13px] text-ink-2 tabular">{start} – {end}</span>
                  <span className="text-[13px] text-ink-2">
                    <span className="font-semibold text-ink tabular">{hour.requests}</span> requests ·{' '}
                    <span className="tabular">{hour.ratio_to_average}×</span> the day’s average
                  </span>
                  <Link to={copilotLink(question, date)}
                    className="ml-auto inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[12.5px] font-medium text-ai opacity-80 transition hover:bg-ai-bg hover:opacity-100 group-hover:opacity-100">
                    <MessageSquareText className="size-3.5" /> Ask Copilot
                  </Link>
                </li>
              )
            })}
          </ol>
        )}
      </div>
    </Panel>
  )
}
