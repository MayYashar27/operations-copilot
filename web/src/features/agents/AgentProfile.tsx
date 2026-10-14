import { Info, Loader2, Lock, MessageSquareText, Play, RotateCw, Sparkles } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAppContext } from '../../app/context'
import { ApiError, apiPost } from '../../api/client'
import type { AgentDetail, InvestigationRecord } from '../../api/types'
import { useApi } from '../../api/useApi'
import { useElapsed, useInvestigation } from '../../api/useInvestigation'
import { WorkspaceHeader } from '../../components/layout/Workspace'
import { AgentMonogram } from '../../components/ui/AgentMonogram'
import { Panel } from '../../components/ui/Panel'
import { SourceTag } from '../../components/ui/SourceTag'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States'
import { formatDateLong, formatDayMonth } from '../../lib/format'
import { copilotLink } from '../../lib/questions'
import { STATUS_META } from '../../lib/status'
import { EvidenceColumns, InvestigationBody, MetricComparison, RequestEvidence, TrendPanel } from './AgentSections'

/** The full profile for one agent on the selected shift. */
export function AgentProfile({ agentId, date }: { agentId: string; date: string }) {
  const detail = useApi<AgentDetail>(`/reports/${date}/agents/${agentId}`)
  const [highlight, setHighlight] = useState<number | null>(null)

  // Clicking a cited request ID scrolls to its documentation and highlights it.
  const selectRequest = useCallback((id: number) => {
    setHighlight(id)
    document.getElementById(`req-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [])

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
        <EvidenceColumns detail={d} onSelect={selectRequest} active={highlight} />
        <InvestigationPanel detail={d} date={date} onSelect={selectRequest} active={highlight} onUpdated={detail.reload} />
        <RequestEvidence requests={d.evidence_requests} active={highlight} />
      </div>
    </>
  )
}

/** The saved deep investigation, plus the (live-mode only) action to run a new one. */
function InvestigationPanel({ detail, date, onSelect, active, onUpdated }: {
  detail: AgentDetail; date: string; onSelect: (id: number) => void; active: number | null; onUpdated: () => void
}) {
  const { config } = useAppContext()
  const live = config?.live_investigations_enabled ?? false
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

  const action = live ? (
    <button type="button" className="btn-primary" onClick={start} disabled={running}>
      {running ? <Loader2 className="size-4 animate-spin" /> : detail.investigation ? <RotateCw className="size-4" /> : <Play className="size-4" />}
      {running ? 'Investigating…' : detail.investigation ? 'Re-run investigation' : 'Run deep investigation'}
    </button>
  ) : (
    <span title="Running new AI investigations is disabled in demo mode"
      className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-frame px-3 text-[12.5px] font-semibold text-ink-3">
      <Lock className="size-3.5" /> Demo: saved results only
    </span>
  )

  return (
    <Panel
      title={<span className="flex items-center gap-2">Deep investigation <SourceTag source="ai" label="AI · saved" /></span>}
      description={detail.investigation
        ? 'Saved result from the existing LangGraph workflow. Shown from disk; opening this page never re-runs the AI.'
        : 'No deep investigation has been saved for this agent and shift.'}
      actions={action}
    >
      {running && (
        <div className="mb-4 flex items-center gap-3 rounded-[14px] bg-accent-soft/60 p-3.5 text-[13px]">
          <Sparkles className="size-4 animate-pulse text-accent" />
          Claude is analysing this agent’s requests, trends and screening signals… <span className="ml-auto text-ink-3 tabular">{elapsed}s</span>
        </div>
      )}
      {(startError || job.record?.status === 'failed') && (
        <p className="mb-4 rounded-[14px] bg-status-review-bg p-3.5 text-[13px] text-status-review-ink">
          {startError ?? `The investigation failed: ${job.record?.error?.message ?? 'unknown error'}`}
        </p>
      )}
      {detail.investigation ? (
        <InvestigationBody investigation={detail.investigation} onSelect={onSelect} active={active} />
      ) : (
        !running && (
          <p className="text-[13px] leading-relaxed text-ink-3">
            Deep investigations run automatically only when screening recommends one.
            {live ? ' You can run one now; it uses paid AI calls.' : ' In demo mode, only saved investigations are shown.'}
          </p>
        )
      )}
    </Panel>
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
