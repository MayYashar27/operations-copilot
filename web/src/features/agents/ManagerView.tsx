import { ArrowRight, ArrowRightLeft, CircleCheck, FileText, Flag, Info, Lightbulb, Quote, Sparkles, Timer, type LucideIcon } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import type { AgentDetail } from '../../api/types'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { formatNumber } from '../../lib/format'
import { type KeyFinding, type ManagerView as View, type Theme, THEME_LABELS, citedBy, requestFacts } from './managerSummary'

const THEME_ICONS: Record<Theme, LucideIcon> = {
  transfers: ArrowRightLeft,
  documentation: FileText,
  handling: Timer,
  other: Flag,
}

const SOURCE_LABEL: Record<KeyFinding['headlineSource'], { text: string; className: string }> = {
  investigation: { text: 'From AI investigation', className: 'bg-ai-bg text-ai-ink' },
  rule: { text: 'Metric signal', className: 'bg-rule-bg text-rule-ink' },
  'ai-observation': { text: 'AI observation · needs validation', className: 'bg-ai-bg text-ai-ink' },
}

/** The one-minute read: findings, the requests behind them, a conclusion, next steps. */
export function ManagerView({ detail, view }: { detail: AgentDetail; view: View }) {
  const [active, setActive] = useState(0)

  const showRequests = (index: number) => {
    setActive(index)
    document.getElementById('supporting-requests')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (view.findings.length === 0) {
    return (
      <div className="card flex items-center gap-3 p-5 text-[13.5px] text-ink-2">
        <CircleCheck className="size-5 text-status-clear" /> No findings for this agent on this shift.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <section aria-label="Key findings">
        <SectionTitle n={1} title="Key findings" note={`${view.findings.length} distinct ${view.findings.length === 1 ? 'pattern' : 'patterns'}, most important first`} />
        <div className="grid gap-3 lg:grid-cols-2">
          {view.findings.map((finding, i) => (
            <FindingCard key={finding.theme} finding={finding} index={i} onShowRequests={() => showRequests(i)} />
          ))}
        </div>
      </section>

      <SupportingRequests detail={detail} findings={view.findings} active={active} onActive={setActive} />

      <div className="grid gap-3 lg:grid-cols-2">
        <section className="card p-5" aria-label="Conclusion">
          <SectionTitle n={3} title="Conclusion" inline />
          <p className="mt-3 text-[13.5px] leading-relaxed text-ink">{view.conclusion.established}</p>
          {view.conclusion.toValidate.length > 0 && (
            <div className="mt-4 rounded-[14px] bg-status-findings-bg/60 p-3.5 ring-1 ring-status-findings/20">
              <p className="mb-1.5 text-[12px] font-semibold text-status-findings-ink">Still needs validation</p>
              <ul className="space-y-1">
                {view.conclusion.toValidate.map((item) => (
                  <li key={item} className="flex gap-2 text-[12.5px] leading-relaxed text-ink-2">
                    <span aria-hidden className="mt-[7px] size-1 shrink-0 rounded-full bg-status-findings" />{item}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {view.conclusion.isTemplate && <TemplateNote>Standard wording: no deep investigation is saved for this agent.</TemplateNote>}
        </section>

        <section className="card p-5" aria-label="Recommended next steps">
          <SectionTitle n={4} title="Recommended next steps" inline />
          <ol className="mt-3 space-y-2.5">
            {view.nextSteps.items.map((step, i) => (
              <li key={step} className="flex gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-2 text-[11.5px] font-bold text-white tabular">{i + 1}</span>
                <p className="text-[13px] leading-relaxed text-ink">{step}</p>
              </li>
            ))}
          </ol>
          {view.nextSteps.isTemplate
            ? <TemplateNote>Standard checks for these signal types, not AI-generated.</TemplateNote>
            : view.nextSteps.totalAvailable > view.nextSteps.items.length && (
              <p className="mt-3 text-[11.5px] text-ink-3">Top {view.nextSteps.items.length} of {view.nextSteps.totalAvailable} saved recommendations. All are in Technical details.</p>
            )}
        </section>
      </div>
    </div>
  )
}

function SectionTitle({ n, title, note, inline }: { n: number; title: string; note?: string; inline?: boolean }) {
  return (
    <div className={`flex items-baseline gap-2.5 ${inline ? '' : 'mb-2.5 px-1'}`}>
      <span className="text-[11px] font-bold text-accent tabular">0{n}</span>
      <h3 className="text-[15px] font-semibold tracking-[-0.01em]">{title}</h3>
      {note && <span className="text-[12px] text-ink-3">{note}</span>}
    </div>
  )
}

function TemplateNote({ children }: { children: ReactNode }) {
  return <p className="mt-3 flex items-center gap-1.5 text-[11.5px] text-ink-3"><Info className="size-3.5" />{children}</p>
}

function FindingCard({ finding, index, onShowRequests }: { finding: KeyFinding; index: number; onShowRequests: () => void }) {
  const Icon = THEME_ICONS[finding.theme]
  const source = SOURCE_LABEL[finding.headlineSource]
  const combined = finding.sources.investigationFindings + finding.sources.ruleSignals + finding.sources.aiObservations

  return (
    <article className="card flex animate-rise flex-col p-5" style={{ animationDelay: `${index * 60}ms` }}>
      <div className="flex items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-[10px] bg-gradient-to-br from-accent-soft to-ai-bg text-accent">
          <Icon className="size-4" strokeWidth={2} />
        </span>
        <p className="text-[12.5px] font-semibold text-ink-2">{THEME_LABELS[finding.theme]}</p>
        <span className={`ml-auto rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${source.className}`}>{source.text}</span>
      </div>

      <p className="mt-3 text-[14px] leading-snug font-semibold text-ink">{finding.headline}</p>

      {finding.observed.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-[11px] font-semibold tracking-wide text-rule-ink uppercase">Observed</p>
          <ul className="space-y-1">
            {finding.observed.map((fact) => (
              <li key={fact} className="flex gap-2 text-[12.5px] leading-relaxed text-ink-2">
                <CircleCheck className="mt-[3px] size-3.5 shrink-0 text-rule" />{fact}
              </li>
            ))}
          </ul>
        </div>
      )}

      {finding.aiNotes.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-[11px] font-semibold tracking-wide text-ai-ink uppercase">Also noted by AI · needs validation</p>
          <ul className="space-y-1">
            {finding.aiNotes.map((note) => (
              <li key={note} className="flex gap-2 text-[12.5px] leading-relaxed text-ink-2">
                <Sparkles className="mt-[3px] size-3.5 shrink-0 text-ai" />{note}
              </li>
            ))}
          </ul>
        </div>
      )}

      {finding.interpretation && (
        <div className="mt-3 rounded-xl bg-ai-bg/50 px-3 py-2.5 ring-1 ring-ai/10">
          <p className="text-[11px] font-semibold text-ai-ink">Possible interpretation · not confirmed</p>
          <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink-2">{finding.interpretation.text}</p>
        </div>
      )}

      {finding.caveat && (
        <p className="mt-2.5 flex gap-1.5 text-[11.5px] leading-snug text-ink-3"><Info className="mt-px size-3.5 shrink-0" />{finding.caveat}</p>
      )}

      <div className="mt-auto flex items-center justify-between gap-2 pt-4">
        {finding.requestIds.length > 0 ? (
          <button type="button" onClick={onShowRequests} className="link inline-flex items-center gap-1 text-[12.5px]">
            {finding.requestIds.length} supporting {finding.requestIds.length === 1 ? 'request' : 'requests'} <ArrowRight className="size-3.5" />
          </button>
        ) : <span className="text-[12px] text-ink-3">No request-level evidence cited</span>}
        {combined > 1 && <span className="text-[11px] text-ink-3">Combines {combined} saved items</span>}
      </div>
    </article>
  )
}

const VISIBLE_CHIPS = 8

function SupportingRequests({ detail, findings, active, onActive }: {
  detail: AgentDetail; findings: KeyFinding[]; active: number; onActive: (i: number) => void
}) {
  const finding = findings[Math.min(active, findings.length - 1)]
  const [selected, setSelected] = useState<number | null>(null)
  const [expanded, setExpanded] = useState(false)
  const byId = useMemo(() => new Map(detail.evidence_requests.map((r) => [r.request_id, r])), [detail.evidence_requests])

  const ids = finding.requestIds
  const current = selected !== null && ids.includes(selected) ? selected : ids[0] ?? null
  const request = current !== null ? byId.get(current) : undefined
  const shown = expanded ? ids : ids.slice(0, VISIBLE_CHIPS)

  return (
    <section id="supporting-requests" className="card scroll-mt-6 p-5" aria-label="Supporting requests">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTitle n={2} title="Supporting requests" inline />
        {findings.length > 1 && (
          <SegmentedControl
            label="Finding"
            value={String(active)}
            onChange={(v) => { onActive(Number(v)); setExpanded(false) }}
            options={findings.map((f, i) => ({ value: String(i), label: THEME_LABELS[f.theme], count: f.requestIds.length }))}
          />
        )}
      </div>

      {ids.length === 0 ? (
        <p className="mt-3 text-[13px] text-ink-3">This finding is based on aggregate metrics; no individual requests are cited.</p>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          <div>
            <p className="mb-2 text-[12px] text-ink-3">Select a request to see its note and why it is cited.</p>
            <div className="flex flex-wrap gap-1.5">
              {shown.map((id) => (
                <button key={id} type="button" onClick={() => setSelected(id)} aria-pressed={id === current}
                  className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[12px] font-semibold tabular transition-all ${
                    id === current ? 'bg-gradient-to-br from-accent to-accent-2 text-white shadow-accent' : 'bg-accent-soft text-accent-strong hover:bg-selected'
                  }`}>
                  <FileText className="size-3" />#{id}
                </button>
              ))}
              {ids.length > VISIBLE_CHIPS && (
                <button type="button" onClick={() => setExpanded((v) => !v)} className="btn-ghost-sm">
                  {expanded ? 'Show fewer' : `+${ids.length - VISIBLE_CHIPS} more`}
                </button>
              )}
            </div>
          </div>

          {current !== null && (
            <div key={current} className="animate-fade rounded-[16px] bg-subtle p-4 ring-1 ring-line-soft">
              {request ? (
                <>
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <p className="text-[14px] font-bold tabular">#{request.request_id}</p>
                    <p className="text-[13px] font-semibold">{request.subject}</p>
                    <p className="ml-auto text-[11.5px] text-ink-3 tabular">
                      {request.request_time.slice(11, 16)} · {formatNumber(request.handling_time_minutes, 1)} min
                    </p>
                  </div>
                  <blockquote className="mt-3 flex gap-2 rounded-xl bg-surface px-3 py-2.5 text-[13px] leading-relaxed text-ink ring-1 ring-line-soft">
                    <Quote className="mt-0.5 size-3.5 shrink-0 text-ink-3" />
                    {request.documentation || <em className="text-ink-3">No documentation</em>}
                  </blockquote>
                  <p className="mt-3 mb-1 text-[11px] font-semibold tracking-wide text-ink-3 uppercase">Request facts</p>
                  <ul className="flex flex-wrap gap-1.5">
                    {requestFacts(request, detail.evidence_requests).map((fact) => (
                      <li key={fact} className="rounded-md bg-surface px-2 py-0.5 text-[11.5px] text-ink-2 ring-1 ring-line-soft">{fact}</li>
                    ))}
                  </ul>
                  <p className="mt-3 mb-1 text-[11px] font-semibold tracking-wide text-ink-3 uppercase">Why it is cited</p>
                  <ul className="space-y-1">
                    {citedBy(detail, request.request_id).slice(0, 3).map((reason) => (
                      <li key={reason} className="flex gap-2 text-[12.5px] leading-snug text-ink-2">
                        <Lightbulb className="mt-px size-3.5 shrink-0 text-accent" />{reason}
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="text-[13px] text-ink-3">The documentation for #{current} is not available in this report.</p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
