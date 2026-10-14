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

/** Page title in the display serif, with optional context and actions. */
export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-8 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
        <h1 className="font-display text-[34px] leading-[1.08] tracking-[-0.01em] text-ink sm:text-[40px]">{title}</h1>
        {description && <p className="mt-3 max-w-2xl text-[14.5px] leading-relaxed text-ink-2">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
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
    <label className="relative inline-flex h-9 items-center rounded-lg border border-line bg-surface shadow-panel transition-colors hover:bg-hover">
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
