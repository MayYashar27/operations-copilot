import { FileX2 } from 'lucide-react'
import { useAppContext } from '../../app/context'
import type { AgentRow, ReportOverview } from '../../api/types'
import { useApi } from '../../api/useApi'
import { StatusDistribution } from '../../components/charts/StatusDistribution'
import { PageHeader, ReportDatePicker } from '../../components/layout/PageHeader'
import { Panel } from '../../components/ui/Panel'
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States'
import { formatDateLong, formatDateShort, pluralize } from '../../lib/format'
import { AttentionTable } from './AttentionTable'
import { PriorityList } from './PriorityList'
import { ServiceCenterStrip } from './ServiceCenterStrip'
import { VolumePanel } from './VolumePanel'

export function DashboardPage() {
  const { reports, date, setDate } = useAppContext()
  const overview = useApi<ReportOverview>(date ? `/reports/${date}` : null)
  const agents = useApi<AgentRow[]>(date ? `/reports/${date}/agents` : null)

  // 1. The list of saved reports decides everything else.
  if (reports.status === 'loading') return <DashboardSkeleton />
  if (reports.status === 'error') {
    return <ErrorState title="Could not load reports" message={reports.error.message} onRetry={reports.reload} />
  }
  if (reports.data.length === 0 || !date) return <NoReports />

  // 2. The selected report.
  if (overview.status === 'loading') return <DashboardSkeleton />
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
    return <ErrorState title="Could not load this report" message={overview.error.message} onRetry={overview.reload} />
  }

  const report = overview.data

  return (
    <>
      <PageHeader
        eyebrow="Daily operations review"
        title={formatDateLong(report.date)}
        description={
          <>
            {pluralize(report.total_agents, 'agent')} screened
            {report.lookback_start && <> against activity since {formatDateShort(report.lookback_start)}</>}.
            Findings are prompts for review, not judgments of performance.
          </>
        }
        actions={<ReportDatePicker />}
      />

      <div className="space-y-6">
        {report.day_metrics && <ServiceCenterStrip metrics={report.day_metrics} />}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <VolumePanel profile={report.volume_profile} />
          <Panel title="Agent screening" description={`${pluralize(report.total_agents, 'agent')} active on this day`}>
            <StatusDistribution counts={report.status_counts} total={report.total_agents} />
          </Panel>
        </div>

        <PriorityList items={report.priority_items} />

        {agents.status === 'loading' && <Skeleton className="h-80 w-full rounded-xl" />}
        {agents.status === 'error' && (
          <Panel title="Agents to review">
            <ErrorState title="Could not load agents" message={agents.error.message} onRetry={agents.reload} />
          </Panel>
        )}
        {agents.status === 'success' && <AttentionTable rows={agents.data} />}
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

function DashboardSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading dashboard">
      <Skeleton className="mb-2 h-4 w-40" />
      <Skeleton className="mb-3 h-8 w-80 max-w-full" />
      <Skeleton className="mb-8 h-4 w-[28rem] max-w-full" />
      <div className="space-y-6">
        <Skeleton className="h-[104px] w-full rounded-xl" />
        <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
          <Skeleton className="h-[320px] rounded-xl" />
          <Skeleton className="h-[320px] rounded-xl" />
        </div>
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    </div>
  )
}
