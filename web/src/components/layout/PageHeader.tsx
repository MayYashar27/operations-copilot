import { CalendarDays, ChevronDown } from 'lucide-react'
import type { ReactNode } from 'react'
import { useAppContext } from '../../app/context'
import { formatDateOption } from '../../lib/format'

interface PageHeaderProps {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <p className="mb-1.5 text-[12.5px] font-medium text-ink-3">{eyebrow}</p>}
        <h1 className="text-[26px] leading-tight font-semibold tracking-[-0.025em] text-ink">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-ink-2">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}

/** Select which saved daily report to view. */
export function ReportDatePicker() {
  const { reports, date, setDate } = useAppContext()
  if (reports.status !== 'success' || reports.data.length === 0 || !date) return null

  const options = reports.data.some((r) => r.date === date)
    ? reports.data
    : [{ date, total_agents: 0 }, ...reports.data]

  return (
    <label className="relative inline-flex h-9 items-center rounded-lg border border-line bg-surface shadow-panel hover:bg-hover">
      <span className="sr-only">Report date</span>
      <CalendarDays className="pointer-events-none absolute left-3 size-4 text-ink-3" />
      <select
        value={date}
        onChange={(event) => setDate(event.target.value)}
        className="h-full cursor-pointer appearance-none bg-transparent pr-9 pl-9 text-[13px] font-medium text-ink outline-none"
      >
        {options.map((report) => (
          <option key={report.date} value={report.date}>
            {formatDateOption(report.date)}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 size-4 text-ink-3" />
    </label>
  )
}
