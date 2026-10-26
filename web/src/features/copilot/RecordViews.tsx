import { useMemo, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { AgentInvestigation, InvestigationRecord, QuestionResult } from '../../api/types'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { formatDateTime, formatDuration } from '../../lib/format'
import { firstSentences } from '../agents/managerSummary'
import { CopilotManagerView } from './CopilotManagerView'
import { buildCopilotView, questionType } from './copilotSummary'

/**
 * Two views of ONE saved record. Switching only changes what is rendered from
 * the record already in memory: no request to the AI, no new fetch.
 */
export function RecordViews({ record, technical }: { record: InvestigationRecord; technical: ReactNode }) {
  const [params, setParams] = useSearchParams()
  const tab: 'manager' | 'technical' = params.get('view') === 'technical' ? 'technical' : 'manager'
  const setTab = (next: 'manager' | 'technical') =>
    setParams((current) => {
      const updated = new URLSearchParams(current)
      if (next === 'technical') updated.set('view', 'technical')
      else updated.delete('view')
      return updated
    }, { replace: true })

  return (
    <>
      <div className="mb-4">
        <SegmentedControl label="Investigation view" value={tab} onChange={setTab}
          options={[{ value: 'manager', label: 'Manager view' }, { value: 'technical', label: 'Technical details' }]} />
      </div>
      <div key={tab} className="animate-fade">
        {tab === 'manager' ? <ManagerTab record={record} /> : technical}
      </div>
    </>
  )
}

function ManagerTab({ record }: { record: InvestigationRecord }) {
  const view = useMemo(() => (record.kind === 'question' ? buildCopilotView(record) : null), [record])
  return view ? <CopilotManagerView view={view} /> : <AgentRecordSummary record={record} />
}

/** Agent investigations (started from an agent profile): compact summary plus a link back. */
function AgentRecordSummary({ record }: { record: InvestigationRecord }) {
  const datedLink = useDatedLink()
  const result = record.result as AgentInvestigation
  return (
    <div className="space-y-3 rounded-[16px] bg-surface p-5 ring-1 ring-line-soft">
      <p className="text-[14px] leading-relaxed text-ink">{firstSentences(result.summary, 2, 320)}</p>
      <ul className="space-y-1.5">
        {result.findings.slice(0, 3).map((f) => (
          <li key={f.finding} className="flex gap-2 text-[13px] leading-relaxed text-ink-2">
            <span aria-hidden className="mt-[8px] size-1.5 shrink-0 rounded-full bg-accent" />{firstSentences(f.finding, 1, 180)}
          </li>
        ))}
      </ul>
      {record.agent_id && (
        <Link to={datedLink(`/agents/${record.agent_id}`)} className="link inline-block text-[13px]">
          Open agent {record.agent_id}’s profile for the full manager view →
        </Link>
      )}
    </div>
  )
}

/** How the Manager view was derived from the saved record (auditable rules). */
export function Derivation({ record }: { record: InvestigationRecord }) {
  const result = record.result as QuestionResult
  const type = questionType(record.question)
  const rows: [string, string][] = [
    ['Question type', type === 'causal'
      ? 'Explanatory (why, cause, investigate…): leads with where the change came from, then next steps.'
      : 'Factual (how many, which…): shows the answer and evidence only.'],
    ['Direct answer', `${type === 'causal' ? 'A lead sentence when one category holds at least half of a captured breakdown in the investigated window, then the first 2' : 'The first 3'} of ${result.observed_facts.length} saved observed facts. "Confirmed cause" appears only if the saved result confirms one (${result.confirmed_root_cause ? 'it does' : 'it does not'}).`],
    ['Key findings', `Up to ${type === 'causal' ? 3 : 2} of ${result.supported_patterns.length} saved supported patterns, excluding repeats of the answer.`],
    ['Supporting evidence', `Breakdowns and numbers read from ${record.trace.length} captured tool results (duplicates removed, truncated results skipped), plus ${record.pattern_themes.length} pattern-analysis themes.`],
    ['Next steps', type === 'causal' ? `Top 2 of ${result.recommendations.length} saved recommendations.` : 'Not shown for factual questions.'],
    ['Kept here only', `${result.hypotheses.length} hypotheses and ${result.missing_evidence.length} missing-evidence items appear in this view, not in the Manager view.`],
  ]
  return (
    <section className="rounded-[16px] bg-surface p-4 ring-1 ring-line-soft">
      <p className="text-[13px] font-semibold">How the Manager view was built</p>
      <p className="mt-0.5 text-[12px] text-ink-3">Both views read this same saved record. No AI is called to summarise or to switch views.</p>
      <dl className="mt-2 divide-y divide-line-soft">
        {rows.map(([label, text]) => (
          <div key={label} className="grid gap-1 py-2 sm:grid-cols-[140px_1fr] sm:gap-4">
            <dt className="text-[12.5px] font-semibold">{label}</dt>
            <dd className="text-[12.5px] leading-relaxed text-ink-2">{text}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

const CHECK_LABELS: Record<string, string> = {
  unverified_number: 'Number not found in the evidence',
  unknown_identifier: 'Identifier not returned by any tool',
  scope_wording: 'Period-wide wording',
  unequal_periods: 'Unequal periods compared',
  confirmed_root_cause: 'Confirmed root cause',
}

/** Deterministic, non-blocking warnings computed after the answer was produced. */
export function AnswerChecks({ record }: { record: InvestigationRecord }) {
  const checks = record.answer_checks
  return (
    <section className="rounded-[16px] bg-surface p-4 ring-1 ring-line-soft">
      <p className="text-[13px] font-semibold">Answer checks</p>
      <p className="mt-0.5 text-[12px] text-ink-3">
        Automatic, deterministic checks of the saved answer against the tool results. Warnings are prompts to look,
        not verdicts; the answer is never changed or blocked.
      </p>
      {checks == null ? (
        <p className="mt-2 text-[12.5px] text-ink-2">Not available: this record was created before answer checks were added.</p>
      ) : checks.length === 0 ? (
        <p className="mt-2 text-[12.5px] text-ink-2">No warnings.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {checks.map((c, i) => (
            <li key={i} className="rounded-lg bg-status-review-bg px-3 py-2 text-[12.5px] text-status-review-ink">
              <b>{CHECK_LABELS[c.kind] ?? c.kind}:</b> {c.message}
              {c.excerpt && <span className="mt-1 block text-[12px] opacity-80">“{c.excerpt}”</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/** What the deterministic planner collected before Claude started, and why. */
export function EvidencePlanPanel({ record }: { record: InvestigationRecord }) {
  const plan = record.evidence_plan
  if (plan == null) return null
  return (
    <section className="rounded-[16px] bg-surface p-4 ring-1 ring-line-soft">
      <p className="text-[13px] font-semibold">Evidence collected before the AI started</p>
      <p className="mt-0.5 text-[12px] text-ink-3">
        Chosen by fixed rules from the question’s dates and intent, not by the AI. The AI could still request any other tool.
      </p>
      <ul className="mt-2 space-y-1 text-[12.5px] leading-relaxed text-ink-2">
        {plan.reasons.map((r) => <li key={r}>{r}</li>)}
      </ul>
      {plan.executed.length > 0 && (
        <p className="mt-2 text-[12px] text-ink-3">
          {plan.executed.length} pre-fetched call{plan.executed.length === 1 ? '' : 's'}; they appear first in the tool trace.
        </p>
      )}
    </section>
  )
}

/** Stored provenance only: what was sent, when, with which model, and the graph's fixed structure. */
export function RunMetadata({ record }: { record: InvestigationRecord }) {
  const seconds = record.completed_at ? Math.round((+new Date(record.completed_at) - +new Date(record.created_at)) / 1000) : null
  const rows: [string, ReactNode][] = [
    ['Record ID', <code key="id" className="text-[11.5px]">{record.id}</code>],
    ['Origin', record.origin === 'example' ? 'Pre-generated example' : 'Run on this machine (live mode)'],
    ['Status', record.status],
    ['Model', record.model ?? 'Not recorded'],
    ['Started', formatDateTime(record.created_at)],
    ['Duration', seconds !== null ? formatDuration(seconds) : '—'],
    ['Dates examined', record.date_range ? `${record.date_range.start} – ${record.date_range.end}` : 'Not recorded'],
    ['Tool calls captured', String(record.trace.length)],
  ]
  return (
    <section className="rounded-[16px] bg-surface p-4 ring-1 ring-line-soft">
      <p className="text-[13px] font-semibold">Run metadata and workflow</p>
      <dl className="mt-2 grid gap-x-6 text-[12.5px] sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3 border-b border-line-soft py-1.5">
            <dt className="text-ink-3">{label}</dt><dd className="text-right font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      {record.error && (
        <p className="mt-3 rounded-lg bg-status-review-bg px-3 py-2 text-[12px] text-status-review-ink"><b>{record.error.type}:</b> {record.error.message}</p>
      )}
      <p className="mt-3 text-[12px] font-semibold text-ink-3">Text appended to the question</p>
      <p className="mt-1 rounded-lg bg-subtle px-3 py-2 text-[12px] leading-relaxed text-ink-2 ring-1 ring-line-soft">
        {record.prompt_context ?? 'None recorded (this record was created before date context was added).'}
      </p>
      {record.kind === 'question' && (
        <>
          <p className="mt-3 text-[12px] font-semibold text-ink-3">Workflow: the existing graph in langgraph_agent.py</p>
          <ol className="mt-1 space-y-1 text-[12px] leading-relaxed text-ink-2">
            <li><b className="text-ink">plan_evidence</b>: fixed rules collect day-level, anomaly and staffing evidence when the question needs it (no AI).</li>
            <li><b className="text-ink">claude</b>: decides whether to call tools or to answer.</li>
            <li><b className="text-ink">tools</b>: runs the requested deterministic tools (each call is listed above).</li>
            <li><b className="text-ink">pattern_analysis</b>: runs after request details are fetched and produces the themes.</li>
            <li><b className="text-ink">final_investigation</b>: one structured call that files the InvestigationResult.</li>
            <li><b className="text-ink">check_answer</b>: deterministic, non-blocking checks of the answer against the evidence.</li>
            <li className="text-ink-3">The API caps the loop with a recursion limit of 40 steps. Records saved before these nodes existed show none of their output.</li>
          </ol>
        </>
      )}
    </section>
  )
}
