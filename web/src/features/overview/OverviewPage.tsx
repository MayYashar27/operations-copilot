import { FileX2, MessageSquareText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAppContext } from '../../app/context'
import type { AgentRow, ReportOverview } from '../../api/types'
import { useApi } from '../../api/useApi'
import { PageHeader, ReportDatePicker } from '../../components/layout/PageHeader'
import { Panel } from '../../components/ui/Panel'
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States'
import { formatDateLong, formatDateShort, formatNumber, pluralize } from '../../lib/format'
import { copilotLink } from '../../lib/questions'
import { ActivityPanel } from './ActivityPanel'
import { AskPanel } from './AskPanel'
import { AttentionQueue } from './AttentionQueue'
import { KpiBand } from './KpiBand'
import { RecentShiftsPanel } from './RecentShiftsPanel'

const NUMBER_WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']

/**
 * The headline is a template filled with real numbers, not AI-generated text,
 * so it can never overstate what the data shows.
 */
function headline(report: ReportOverview): { lead: string; follow: string } {
  const unusual = report.hourly_activity.filter((h) => h.above_threshold)
  const requests = report.day_metrics?.total_requests
  const lead =
    requests === undefined
      ? 'Shift summary.'
      : `${formatNumber(requests)} requests, ${
          unusual.length ? `with unusual volume at ${unusual.map((h) => h.hour.slice(0, 5)).join(', ')}.` : 'no unusual hours.'
        }`
  const deep = report.status_counts.investigation
  const word = NUMBER_WORDS[deep] ?? String(deep)
  const follow = deep
    ? `${word} ${deep === 1 ? 'agent' : 'agents'} recommended for a deep review.`
    : 'No agents recommended for a deep review.'
  return { lead, follow }
}

export function OverviewPage() {
  const { reports, date, setDate } = useAppContext()
  const overview = useApi<ReportOverview>(date ? `/reports/${date}` : null)
  const agents = useApi<AgentRow[]>(date ? `/reports/${date}/agents` : null)

  if (reports.status === 'loading') return <OverviewSkeleton />
  if (reports.status === 'error') {
    return <ErrorState title="Could not load reports" message={reports.error.message} onRetry={reports.reload} />
  }
  if (reports.data.length === 0 || !date) return <NoReports />

  if (overview.status === 'loading') return <OverviewSkeleton />
  if (overview.status === 'error') {
    if (overview.error.status === 404) {
      return (
        <EmptyState
          icon={FileX2}
          title={`No saved report for ${formatDateShort(date)}`}
          action={
            <button type="button" className="btn-secondary" onClick={() => setDate(reports.data[0].date)}>
              View latest report ({formatDateShort(reports.data[0].date)})
            </button>
          }
        />
      )
    }
    return <ErrorState title="Could not load this shift" message={overview.error.message} onRetry={overview.reload} />
  }

  const report = overview.data
  const { lead, follow } = headline(report)
  const baselineDays = Math.max(0, report.daily_trend.length - 1)

  return (
    <>
      <PageHeader
        eyebrow={`Shift overview · ${formatDateLong(report.date)}`}
        title={
          <>
            {lead} <span className="text-ink-3 italic">{follow}</span>
          </>
        }
        description={
          <>
            {pluralize(report.total_agents, 'agent')} screened
            {report.lookback_start && <> against activity since {formatDateShort(report.lookback_start)}</>}.
            Findings are prompts for a manager’s review, not judgments of performance.
          </>
        }
        actions={
          <>
            <ReportDatePicker />
            <Link to={copilotLink('', date)} className="btn-primary">
              <MessageSquareText className="size-4" /> Ask about this shift
            </Link>
          </>
        }
      />

      {report.daily_trend.length > 0 && <KpiBand trend={report.daily_trend} date={report.date} />}

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="min-w-0 space-y-6">
          <ActivityPanel hours={report.hourly_activity} baselineDays={baselineDays} />
          {report.daily_trend.length > 0 && <RecentShiftsPanel trend={report.daily_trend} date={report.date} />}
        </div>

        <div className="min-w-0 space-y-6">
          {agents.status === 'loading' && <Skeleton className="h-[420px] rounded-2xl" />}
          {agents.status === 'error' && (
            <Panel title="Needs attention">
              <ErrorState title="Could not load agents" message={agents.error.message} onRetry={agents.reload} />
            </Panel>
          )}
          {agents.status === 'success' && (
            <AttentionQueue rows={agents.data} counts={report.status_counts} total={report.total_agents} />
          )}
          <AskPanel date={report.date} trend={report.daily_trend} />
        </div>
      </div>
    </>
  )
}

function NoReports() {
  return (
    <EmptyState icon={FileX2} title="No saved reports yet">
      <p>
        Reports are generated ahead of time so the app never calls the AI on page load. Generate one from the
        project root:
      </p>
      <code className="mt-3 inline-block rounded-md border border-line bg-subtle px-2.5 py-1.5 text-[12px] text-ink">
        python scripts/generate_report.py 2026-09-07
      </code>
    </EmptyState>
  )
}

function OverviewSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading overview">
      <Skeleton className="mb-3 h-3 w-56" />
      <Skeleton className="mb-2 h-10 w-[36rem] max-w-full" />
      <Skeleton className="mb-8 h-10 w-[28rem] max-w-full" />
      <Skeleton className="h-[164px] w-full rounded-2xl" />
      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_380px]">
        <Skeleton className="h-[380px] rounded-2xl" />
        <Skeleton className="h-[380px] rounded-2xl" />
      </div>
    </div>
  )
}
