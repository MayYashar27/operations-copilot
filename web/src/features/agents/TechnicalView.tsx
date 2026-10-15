import { Cpu, ExternalLink, GitBranch, ListTree } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { AgentDetail, InvestigationSummary } from '../../api/types'
import { useApi } from '../../api/useApi'
import { Panel } from '../../components/ui/Panel'
import { SourceTag } from '../../components/ui/SourceTag'
import { formatDateShort, formatDateTime } from '../../lib/format'
import { EvidenceColumns, InvestigationBody, RequestEvidence } from './AgentSections'
import type { ManagerView } from './managerSummary'

/** The full saved record, for audit and technical review. Nothing is regenerated. */
export function TechnicalView({ detail, view }: { detail: AgentDetail; view: ManagerView }) {
  const [highlight, setHighlight] = useState<number | null>(null)
  const select = useCallback((id: number) => {
    setHighlight(id)
    document.getElementById(`req-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [])

  return (
    <div className="space-y-4">
      <Derivation detail={detail} view={view} />
      <EvidenceColumns detail={detail} onSelect={select} active={highlight} />
      <Panel title={<span className="flex items-center gap-2">Deep investigation, complete <SourceTag source="ai" label="AI · saved" /></span>}
        description="Every field of the saved AgentInvestigationResult: summary, observed facts, findings with metrics and request IDs, hypotheses, missing evidence and all recommendations.">
        {detail.investigation
          ? <InvestigationBody investigation={detail.investigation} onSelect={select} active={highlight} />
          : <p className="text-[13px] text-ink-3">No deep investigation is saved for this agent and shift.</p>}
      </Panel>
      <RequestEvidence requests={detail.evidence_requests} active={highlight} />
      <WorkflowMetadata detail={detail} />
    </div>
  )
}

/** How the Manager view was derived from the saved record: auditable, rule by rule. */
function Derivation({ detail, view }: { detail: AgentDetail; view: ManagerView }) {
  const inv = detail.investigation
  const rows: [string, string][] = inv
    ? [
        ['Key findings', `${inv.findings.length} saved investigation findings grouped into ${view.findings.length} themes. Theme = the earliest theme keyword in each finding title (transfers, documentation, handling time). The first finding in each theme is the headline.`],
        ['Observed facts', 'First readable supporting metric of each grouped finding, up to 3 per card. Raw field dumps are left to this view.'],
        ['Interpretation', 'First sentence of the lead finding’s saved interpretation, labelled “not confirmed”.'],
        ['Conclusion', `Leading sentences of the saved summary, plus the first 2 of ${inv.missing_evidence.length} saved missing-evidence items.`],
        ['Next steps', `First ${view.nextSteps.items.length} of ${inv.recommendations.length} saved recommendations, first sentence each, duplicates removed.`],
      ]
    : [
        ['Key findings', `${detail.rule_signals.length} rule signals and ${detail.ai_observations.length} AI observations grouped into ${view.findings.length} themes. Rule signals are stated as measured facts; AI observations are labelled as needing validation.`],
        ['Conclusion', 'A fixed template stating that no deep investigation was run.'],
        ['Next steps', 'Fixed standard checks per theme. Not AI-generated.'],
      ]

  return (
    <Panel title={<span className="flex items-center gap-2"><ListTree className="size-4 text-accent" />How the Manager view was built</span>}
      description="Both views read the same saved result. The Manager view is a deterministic selection and grouping of it; no AI is called to summarise.">
      <dl className="divide-y divide-line-soft">
        {rows.map(([label, text]) => (
          <div key={label} className="grid gap-1 py-2.5 sm:grid-cols-[140px_1fr] sm:gap-4">
            <dt className="text-[12.5px] font-semibold text-ink">{label}</dt>
            <dd className="text-[12.5px] leading-relaxed text-ink-2">{text}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  )
}

/**
 * What is actually known about how the result was produced. The agent
 * investigation workflow makes no dynamic tool calls, so there is no tool
 * trace to show; the workflow steps below are its fixed structure.
 */
function WorkflowMetadata({ detail }: { detail: AgentDetail }) {
  const datedLink = useDatedLink()
  const history = useApi<InvestigationSummary[]>('/copilot/investigations')
  const localRun = history.status === 'success'
    ? history.data.find((h) => h.kind === 'agent' && h.agent_id === detail.agent_id && h.report_date === detail.date)
    : undefined

  const steps = [
    ['Screening', 'Deterministic (tools.py)', 'Documentation screening, performance signals over the lookback window, transfer concentration.'],
    ['Documentation review', 'One structured Claude call', 'analyze_agent_documentation reads every note of the shift and returns DocumentationAnalysisResult.'],
    ['Escalation rule', 'Deterministic', 'Signals are combined into "deep review recommended" only by fixed rules; a model opinion alone cannot escalate.'],
    ['collect_evidence', 'Deterministic LangGraph node', 'get_agent_performance, get_agent_daily_trends and get_agent_request_evidence for the shift.'],
    ['analyze_evidence', 'One structured Claude call', 'Returns AgentInvestigationResult. Cited request IDs, agent ID and date are validated against the evidence.'],
  ]

  return (
    <Panel title={<span className="flex items-center gap-2"><Cpu className="size-4 text-accent" />Workflow and run metadata</span>}
      description="Stored provenance only. This workflow does not call tools dynamically, so there is no tool trace to show.">
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-[12px] font-semibold text-ink-3"><GitBranch className="size-3.5" />Workflow (langgraph_agent.py)</p>
          <ol className="space-y-2">
            {steps.map(([name, kind, text], i) => (
              <li key={name} className="flex gap-3 rounded-xl bg-subtle p-3 ring-1 ring-line-soft">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-[11px] font-bold text-accent tabular">{i + 1}</span>
                <div>
                  <p className="text-[12.5px] font-semibold">{name} <span className="font-normal text-ink-3">· {kind}</span></p>
                  <p className="mt-0.5 text-[12px] leading-relaxed text-ink-2">{text}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
        <div className="space-y-3">
          <dl className="space-y-2 rounded-xl bg-subtle p-3.5 text-[12.5px] ring-1 ring-line-soft">
            <div className="flex justify-between gap-3"><dt className="text-ink-3">Shift</dt><dd className="font-semibold">{formatDateShort(detail.date)}</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-ink-3">Lookback window</dt><dd className="font-semibold">{detail.lookback_start ? formatDateShort(detail.lookback_start) : '—'} – {formatDateShort(detail.date)}</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-ink-3">Screening status</dt><dd className="font-semibold">{detail.status}</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-ink-3">Investigation source</dt>
              <dd className="text-right font-semibold">
                {!detail.investigation ? 'None saved' : localRun ? 'On-demand run (live mode)' : 'Daily report batch'}
              </dd>
            </div>
          </dl>
          {detail.investigation && (localRun ? (
            <p className="text-[12.5px] leading-relaxed text-ink-2">
              Re-run on {formatDateTime(localRun.created_at)} ({localRun.status}).{' '}
              <Link to={datedLink(`/copilot/${localRun.id}`)} className="link inline-flex items-center gap-1">Open run record <ExternalLink className="size-3" /></Link>
            </p>
          ) : (
            <p className="text-[12.5px] leading-relaxed text-ink-2">
              Produced by <code className="rounded bg-frame px-1 text-[11.5px]">scripts/generate_report.py</code>. The batch saves the result but not the model name or timing per agent, so none are shown.
            </p>
          ))}
          {detail.methodology && (
            <div className="rounded-xl bg-status-findings-bg/50 p-3.5 ring-1 ring-status-findings/20">
              <p className="text-[11.5px] font-semibold text-status-findings-ink">Saved methodology note</p>
              <p className="mt-1 text-[12.5px] leading-relaxed text-ink-2">{detail.methodology}</p>
            </div>
          )}
        </div>
      </div>
    </Panel>
  )
}
