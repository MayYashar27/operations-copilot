import { MessageSquareText, Star } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAppContext } from '../../app/context'
import type { DailyTrendItem } from '../../api/types'
import { SidePanel, SideItem, SideSearch, SideSection } from '../../components/layout/SidePanel'
import { formatDateOption, formatNumber } from '../../lib/format'
import { copilotLink } from '../../lib/questions'

/**
 * Shift navigation. Screened reports are pinned and selectable; other recent
 * days have operational data only (no screening report), shown with their
 * real unusual hours and a shortcut to ask Copilot about them.
 */
export function ShiftsPanel({ trend }: { trend: DailyTrendItem[] }) {
  const { reports, date, setDate } = useAppContext()
  const [query, setQuery] = useState('')

  const matches = (iso: string) => formatDateOption(iso).toLowerCase().includes(query.trim().toLowerCase())
  const screened = reports.status === 'success' ? reports.data.filter((r) => matches(r.date)) : []
  const screenedDates = new Set(screened.map((r) => r.date))
  const earlier = [...trend].reverse().filter((d) => !d.has_report && !screenedDates.has(d.date) && matches(d.date))

  return (
    <SidePanel
      title="Shifts"
      count={trend.length || undefined}
      toolbar={<SideSearch value={query} onChange={setQuery} placeholder="Search shifts…" />}
    >
      <SideSection label="Screened reports">
        {screened.length === 0 && <p className="px-2 text-[12.5px] text-ink-3">No matching reports.</p>}
        {screened.map((report) => {
          const selected = report.date === date
          return (
            <SideItem key={report.date} selected={selected}>
              <button type="button" onClick={() => setDate(report.date)} className="flex w-full items-start gap-2.5 text-left">
                <Star className={`mt-0.5 size-4 shrink-0 ${selected ? 'fill-accent text-accent' : 'text-ink-3'}`} strokeWidth={1.8} />
                <span className="min-w-0">
                  <span className="block text-[13.5px] font-semibold text-ink">{formatDateOption(report.date)}</span>
                  <span className="mt-0.5 block text-[12px] text-ink-3">{report.total_agents} agents screened</span>
                </span>
              </button>
            </SideItem>
          )
        })}
      </SideSection>

      {earlier.length > 0 && (
        <SideSection label="Earlier shifts · operational data only">
          {earlier.map((day) => {
            const unusual = day.unusual_hours[0]
            const [start, end] = unusual ? unusual.hour.split('-') : []
            const question = unusual
              ? `There was an unusually high workload on ${day.date} between ${start} and ${end}. Investigate what happened and explain the likely cause.`
              : `Summarize operations on ${day.date}: request volume, main classifications, wait time and transfers.`
            return (
              <SideItem key={day.date}>
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-[13.5px] font-medium text-ink">{formatDateOption(day.date)}</p>
                    <p className="mt-0.5 text-[12px] text-ink-3 tabular">
                      {formatNumber(day.total_requests)} requests · {formatNumber(day.average_wait_time_minutes, 1)} min wait
                    </p>
                    {unusual && (
                      <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-status-review-bg px-2 py-[2px] text-[11px] font-semibold text-status-review-ink tabular">
                        Unusual {start}–{end}
                      </span>
                    )}
                  </div>
                  <Link
                    to={copilotLink(question, date)}
                    title="Ask Copilot about this shift"
                    aria-label={`Ask Copilot about ${formatDateOption(day.date)}`}
                    className="flex size-8 shrink-0 items-center justify-center rounded-lg text-ink-3 opacity-60 transition hover:bg-ai-bg hover:text-ai group-hover:opacity-100"
                  >
                    <MessageSquareText className="size-4" strokeWidth={1.9} />
                  </Link>
                </div>
              </SideItem>
            )
          })}
        </SideSection>
      )}
    </SidePanel>
  )
}
