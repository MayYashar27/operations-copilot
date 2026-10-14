import { FileQuestion, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useAppContext, useDatedLink } from '../../app/context'
import { ApiError, apiPost } from '../../api/client'
import type { InvestigationRecord, InvestigationSummary, ReportOverview } from '../../api/types'
import { useApi } from '../../api/useApi'
import { useInvestigation } from '../../api/useInvestigation'
import { Workspace, WorkspaceHeader } from '../../components/layout/Workspace'
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States'
import { formatDateLong } from '../../lib/format'
import { suggestedQuestions } from '../../lib/questions'
import { Composer } from './Composer'
import { HistoryPanel } from './HistoryPanel'
import { InvestigationView } from './InvestigationView'
import { Welcome } from './Welcome'

/**
 * /copilot           a new investigation (welcome + composer)
 * /copilot/:id       a saved or running investigation, loaded from history
 */
export function CopilotPage() {
  const { investigationId } = useParams()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const datedLink = useDatedLink()
  const { config, date } = useAppContext()
  const live = config?.live_investigations_enabled ?? false

  const history = useApi<InvestigationSummary[]>('/copilot/investigations')
  const overview = useApi<ReportOverview>(date ? `/reports/${date}` : null)
  const current = useInvestigation(investigationId ?? null)

  const [draft, setDraft] = useState(() => params.get('q') ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // When the open investigation finishes, refresh the history list.
  const finishedStatus = current.record?.status
  const { reload: reloadHistory } = history
  useEffect(() => {
    if (finishedStatus && finishedStatus !== 'running') reloadHistory()
  }, [finishedStatus, reloadHistory])

  const items = history.status === 'success' ? history.data : null
  const anyRunning = (items ?? []).some((i) => i.status === 'running') || current.record?.status === 'running'
  const blockedReason = !live ? 'demo' : anyRunning ? 'running' : null

  const submit = async () => {
    setSubmitting(true)
    setSubmitError(null)
    try {
      const record = await apiPost<InvestigationRecord>('/copilot/investigations', { question: draft.trim(), report_date: date })
      setDraft('')
      reloadHistory()
      navigate(datedLink(`/copilot/${record.id}`))
    } catch (error) {
      setSubmitError(error instanceof ApiError ? error.message : 'Could not start the investigation.')
    } finally {
      setSubmitting(false)
    }
  }

  const reuse = (question: string) => {
    setDraft(question)
    if (investigationId) navigate(datedLink('/copilot'))
  }

  let main
  if (investigationId) {
    if (current.loading) main = <Skeleton className="mx-auto h-[420px] max-w-[880px] rounded-[22px]" />
    else if (current.error) {
      main = current.error.status === 404
        ? <EmptyState icon={FileQuestion} title="This investigation is not in the history"
            action={<Link to={datedLink('/copilot')} className="btn-secondary">Start a new one</Link>} />
        : <ErrorState title="Could not open this investigation" message={current.error.message} onRetry={current.reload} />
    } else if (current.record) main = <InvestigationView record={current.record} onReuse={reuse} />
  } else {
    main = (
      <Welcome
        live={live}
        suggestions={overview.status === 'success' && date ? suggestedQuestions(date, overview.data.daily_trend) : []}
        examples={(items ?? []).filter((i) => i.origin === 'example')}
        onPick={setDraft}
      />
    )
  }

  return (
    <Workspace
      scrollKey={investigationId ?? 'new'}
      side={<HistoryPanel items={items} selectedId={investigationId} loading={history.status === 'loading'} />}
      footer={
        <>
          {submitError && (
            <p role="alert" className="mx-auto mb-2 max-w-[880px] rounded-xl bg-status-review-bg px-3 py-2 text-[12.5px] text-status-review-ink">{submitError}</p>
          )}
          <Composer value={draft} onChange={setDraft} onSubmit={submit} blockedReason={blockedReason} submitting={submitting} />
        </>
      }
    >
      <WorkspaceHeader
        sideLabel="History"
        title={investigationId ? 'Investigation' : 'Ask Copilot'}
        subtitle={date ? `Context: shift of ${formatDateLong(date)}` : undefined}
        actions={investigationId && (
          <Link to={datedLink('/copilot')} className="btn-secondary"><Plus className="size-4" /> New</Link>
        )}
      />
      {main}
    </Workspace>
  )
}
