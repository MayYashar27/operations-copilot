import { ClipboardList, FileX2, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAppContext } from '../../app/context'
import type { AgentRow, ReportOverview } from '../../api/types'
import { useApi } from '../../api/useApi'
import { Workspace, WorkspaceHeader } from '../../components/layout/Workspace'
import { Panel } from '../../components/ui/Panel'
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States'
import { formatDateLong, formatDateShort, formatNumber, pluralize } from '../../lib/format'
import { copilotLink } from '../../lib/questions'
import { ActivityPanel } from './ActivityPanel'
import { AskCard } from './AskCard'
import { AttentionCard } from './AttentionCard'
import { KpiCards } from './KpiCards'
import { RecentShiftsCard } from './RecentShiftsCard'
import { ShiftsPanel } from './ShiftsPanel'

const NUMBER_WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']

/**
 * The summary sentence is a template filled with real numbers, not
 * AI-generated text, so it can never overstate what the data shows.
 */
function summary(report: ReportOverview): string {
  const unusual = report.hourly_activity.filter((h) => h.above_threshold)
  const requests = report.day_metrics?.total_requests
  const volume =
    requests === undefined
      ? ''
      : `${formatNumber(requests)} requests, ${
          unusual.length ? `with unusual volume at ${unusual.map((h) => h.hour.slice(0, 5)).join(', ')}` : 'no unusual hours'
        }. `
  const deep = report.status_counts.investigation
  const word = NUMBER_WORDS[deep] ?? String(deep)
  return `${volume}${deep ? `${word} ${deep === 1 ? 'agent' : 'agents'}` : 'No agents'} recommended for a deep review.`
}

export function OverviewPage() {
  const { reports, date, setDate } = useAppContext()
  const overview = useApi<ReportOverview>(date ? `/reports/${date}` : null)
  const agents = useApi<AgentRow[]>(date ? `/reports/${date}/agents` : null)

  const trend = overview.status === 'success' ? overview.data.daily_trend : []

  return (
    <Workspace side={<ShiftsPanel trend={trend} />}>
      {(() => {
        if (reports.status === 'loading') return <OverviewSkeleton />
        if (reports.status === 'error') {
          return <ErrorState title="Could not load reports" message={reports.error.message} onRetry={reports.reload} />
        }
        if (reports.data.length === 0 || !date) return <NoReports />
        if (overview.status === 'loading') return <OverviewSkeleton />
        if (overview.status === 'error') {
          if (overview.error.status === 404) {
            return (
              <EmptyState icon={FileX2} title={`No saved report for ${formatDateShort(date)}`}
                action={
                  <button type="button" className="btn-secondary" onClick={() => setDate(reports.data[0].date)}>
                    View latest report ({formatDateShort(reports.data[0].date)})
                  </button>
                } />
            )
          }
          return <ErrorState title="Could not load this shift" message={overview.error.message} onRetry={overview.reload} />
        }

        const report = overview.data
        const baselineDays = Math.max(0, report.daily_trend.length - 1)
        return (
          <>
            <WorkspaceHeader
              sideLabel="Shifts"
              title="Shift overview"
              subtitle={
                <>
                  {formatDateLong(report.date)} · {pluralize(report.total_agents, 'agent')} screened
                  {report.lookback_start && <> since {formatDateShort(report.lookback_start)}</>}
                </>
              }
              actions={
                <Link to={copilotLink('', date)} className="btn-primary">
                  <Sparkles className="size-4" /> Ask Copilot
                </Link>
              }
            />

            <div className="mb-5 flex items-start gap-3 rounded-2xl bg-surface/70 px-4 py-3 ring-1 ring-white">
              <ClipboardList className="mt-px size-4 shrink-0 text-accent" strokeWidth={2} />
              <p className="text-[13.5px] leading-relaxed text-ink">
                {summary(report)}{' '}
                <span className="text-ink-3">Findings are prompts for a manager’s review, not judgments of performance.</span>
              </p>
            </div>

            {report.daily_trend.length > 0 && <KpiCards trend={report.daily_trend} date={report.date} />}

            <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
              <div className="min-w-0 space-y-4">
                <ActivityPanel hours={report.hourly_activity} baselineDays={baselineDays} />
                {report.daily_trend.length > 0 && <RecentShiftsCard trend={report.daily_trend} date={report.date} />}
              </div>
              <div className="min-w-0 space-y-4">
                {agents.status === 'loading' && <Skeleton className="h-[440px] rounded-[var(--radius-card)]" />}
                {agents.status === 'error' && (
                  <Panel title="Priority attention">
                    <ErrorState title="Could not load agents" message={agents.error.message} onRetry={agents.reload} />
                  </Panel>
                )}
                {agents.status === 'success' && (
                  <AttentionCard rows={agents.data} counts={report.status_counts} total={report.total_agents} />
                )}
                <AskCard date={report.date} trend={report.daily_trend} />
              </div>
            </div>
          </>
        )
      })()}
    </Workspace>
  )
}

function NoReports() {
  return (
    <EmptyState icon={FileX2} title="No saved reports yet">
      <p>Reports are generated ahead of time so the app never calls the AI on page load. Generate one from the project root:</p>
      <code className="mt-3 inline-block rounded-lg bg-surface px-2.5 py-1.5 text-[12px] text-ink ring-1 ring-line">
        python scripts/generate_report.py 2026-09-07
      </code>
    </EmptyState>
  )
}

function OverviewSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading overview">
      <Skeleton className="mb-2 h-6 w-48" />
      <Skeleton className="mb-6 h-4 w-80 max-w-full" />
      <Skeleton className="mb-5 h-12 w-full rounded-2xl" />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[150px] rounded-[var(--radius-card)]" />)}
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_340px]">
        <Skeleton className="h-[380px] rounded-[var(--radius-card)]" />
        <Skeleton className="h-[380px] rounded-[var(--radius-card)]" />
      </div>
    </div>
  )
}
