import { Info, Loader2, Lock, MessageSquareText, Play, RotateCw, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAppContext } from '../../app/context'
import { ApiError, apiPost } from '../../api/client'
import type { AgentDetail, InvestigationRecord } from '../../api/types'
import { useApi } from '../../api/useApi'
import { useElapsed, useInvestigation } from '../../api/useInvestigation'
import { WorkspaceHeader } from '../../components/layout/Workspace'
import { AgentMonogram } from '../../components/ui/AgentMonogram'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States'
import { formatDateLong, formatDayMonth } from '../../lib/format'
import { copilotLink } from '../../lib/questions'
import { STATUS_META } from '../../lib/status'
import { MetricComparison, TrendPanel } from './AgentSections'
import { buildManagerView } from './managerSummary'
import { ManagerView } from './ManagerView'
import { TechnicalView } from './TechnicalView'

/** The full profile for one agent on the selected shift. */
export function AgentProfile({ agentId, date }: { agentId: string; date: string }) {
  const detail = useApi<AgentDetail>(`/reports/${date}/agents/${agentId}`)

  if (detail.status === 'loading') return <ProfileSkeleton />
  if (detail.status === 'error') {
    return detail.error.status === 404
      ? <EmptyState icon={Info} title={`Agent ${agentId} is not in this report`}>Pick an agent from the directory.</EmptyState>
      : <ErrorState title="Could not load this agent" message={detail.error.message} onRetry={detail.reload} />
  }

  const d = detail.data
  const askQuestion = `Investigate agent ${d.agent_id}'s transfer patterns on ${d.date}: which classifications and destinations were involved, and how does this compare with the team?`

  return (
    <>
      <WorkspaceHeader
        sideLabel="Agents"
        title={
          <span className="flex items-center gap-3">
            <AgentMonogram id={d.agent_id} status={d.status} />
            <span>Agent {d.agent_id}</span>
          </span>
        }
        subtitle={<>{formatDateLong(d.date)} · compared with activity since {d.lookback_start ? formatDayMonth(d.lookback_start) : '—'}</>}
        actions={
          <Link to={copilotLink(askQuestion, date)} className="btn-secondary">
            <MessageSquareText className="size-4" /> Ask Copilot
          </Link>
        }
      />

      <div className="space-y-4">
        <div className="flex flex-wrap items-start gap-3 rounded-2xl bg-surface/70 px-4 py-3.5 ring-1 ring-white">
          <StatusBadge status={d.status} />
          <div className="min-w-0 flex-1 text-[13px] leading-relaxed text-ink">
            {d.investigation_reasons.length > 0 ? (
              <>Recommended for review because: {d.investigation_reasons.join('; ').toLowerCase()}.</>
            ) : (
              <>{STATUS_META[d.status].description}</>
            )}{' '}
            <span className="text-ink-3">A review category, not a performance rating.</span>
          </div>
        </div>

        <MetricComparison detail={d} />
        <TrendPanel detail={d} />
        <InvestigationArea detail={d} date={date} onUpdated={detail.reload} />
      </div>
    </>
  )
}

/**
 * The investigation area: one saved result, two views of it.
 * Manager view (default) is a deterministic condensation; Technical details
 * shows the full record. The live-mode action re-runs the existing workflow.
 */
function InvestigationArea({ detail, date, onUpdated }: { detail: AgentDetail; date: string; onUpdated: () => void }) {
  const { config } = useAppContext()
  const live = config?.live_investigations_enabled ?? false
  const [params, setParams] = useSearchParams()
  const tab: 'manager' | 'technical' = params.get('view') === 'technical' ? 'technical' : 'manager'
  const setTab = (next: 'manager' | 'technical') =>
    setParams((current) => {
      const updated = new URLSearchParams(current)
      if (next === 'technical') updated.set('view', 'technical')
      else updated.delete('view')
      return updated
    }, { replace: true })

  const view = useMemo(() => buildManagerView(detail), [detail])

  const [jobId, setJobId] = useState<string | null>(null)
  const [startError, setStartError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const job = useInvestigation(jobId)
  const running = starting || job.record?.status === 'running'
  const elapsed = useElapsed(job.record?.created_at ?? null, running)

  useEffect(() => {
    if (job.record && job.record.status !== 'running') onUpdated()
  }, [job.record, onUpdated])

  const start = async () => {
    setStarting(true)
    setStartError(null)
    try {
      const record = await apiPost<InvestigationRecord>(`/reports/${date}/agents/${detail.agent_id}/investigation`)
      setJobId(record.id)
    } catch (error) {
      setStartError(error instanceof ApiError ? error.message : 'Could not start the investigation.')
    } finally {
      setStarting(false)
    }
  }

  return (
    <section aria-label="Investigation" className="space-y-4 pt-2">
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="text-[18px] font-semibold tracking-[-0.02em]">Investigation</h2>
          <p className="mt-0.5 text-[12.5px] text-ink-3">
            {view.basis === 'investigation'
              ? 'From the saved deep investigation · opened from disk, not re-run'
              : 'From screening signals · no deep investigation is saved for this agent'}
          </p>
        </div>
        <SegmentedControl label="Investigation view" value={tab} onChange={setTab}
          options={[{ value: 'manager', label: 'Manager view' }, { value: 'technical', label: 'Technical details' }]} />
        {live ? (
          <button type="button" className="btn-secondary" onClick={start} disabled={running}>
            {running ? <Loader2 className="size-4 animate-spin" /> : detail.investigation ? <RotateCw className="size-4" /> : <Play className="size-4" />}
            {running ? 'Investigating…' : detail.investigation ? 'Re-run' : 'Run deep investigation'}
          </button>
        ) : (
          <span title="Running new AI investigations is disabled in demo mode"
            className="inline-flex h-10 items-center gap-1.5 rounded-xl bg-frame px-3 text-[12.5px] font-semibold text-ink-3">
            <Lock className="size-3.5" /> Demo: saved results only
          </span>
        )}
      </div>

      {running && (
        <div className="flex items-center gap-3 rounded-[14px] bg-accent-soft/60 p-3.5 text-[13px]">
          <Sparkles className="size-4 animate-pulse text-accent" />
          Claude is analysing this agent’s requests, trends and screening signals… <span className="ml-auto text-ink-3 tabular">{elapsed}s</span>
        </div>
      )}
      {(startError || job.record?.status === 'failed') && (
        <p className="rounded-[14px] bg-status-review-bg p-3.5 text-[13px] text-status-review-ink">
          {startError ?? `The investigation failed: ${job.record?.error?.message ?? 'unknown error'}`}
        </p>
      )}

      <div key={tab} className="animate-fade">
        {tab === 'manager' ? <ManagerView detail={detail} view={view} /> : <TechnicalView detail={detail} view={view} />}
      </div>
    </section>
  )
}

function ProfileSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading agent">
      <Skeleton className="mb-6 h-10 w-72" />
      <Skeleton className="mb-4 h-14 w-full rounded-2xl" />
      <div className="mb-4 grid grid-cols-2 gap-3 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[120px] rounded-[var(--radius-card)]" />)}
      </div>
      <Skeleton className="h-[300px] rounded-[var(--radius-card)]" />
    </div>
  )
}
