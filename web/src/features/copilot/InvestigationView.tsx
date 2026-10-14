import {
  CheckCircle2, ChevronDown, CircleAlert, CircleHelp, Copy, Check, Layers, Lightbulb, ListChecks, MessageSquareQuote,
  Sparkles, TriangleAlert, Wrench,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import type { AgentInvestigation, InvestigationRecord, PatternTheme, QuestionResult, TraceStep } from '../../api/types'
import { useElapsed } from '../../api/useInvestigation'
import { RequestChips } from '../../components/ui/RequestChip'
import { formatDateShort, formatDateTime, formatDuration } from '../../lib/format'
import { toolLabel } from '../../lib/signals'
import { InvestigationBody } from '../agents/AgentSections'

/** One investigation as a conversation: the question, then Copilot's answer. */
export function InvestigationView({ record, onReuse }: { record: InvestigationRecord; onReuse: (question: string) => void }) {
  return (
    <div className="mx-auto max-w-[880px] space-y-5">
      <div className="flex justify-end">
        <div className="max-w-[640px] animate-rise rounded-[18px] rounded-tr-md bg-surface px-4 py-3 shadow-card ring-1 ring-line/60">
          <p className="text-[14px] leading-relaxed text-ink">{record.question}</p>
          <p className="mt-1.5 text-right text-[11.5px] text-ink-3">
            Asked {formatDateTime(record.created_at)}{record.report_date && <> · viewing shift {formatDateShort(record.report_date)}</>}
          </p>
        </div>
      </div>

      <div className="animate-rise rounded-[22px] bg-surface/80 p-5 shadow-card ring-1 ring-white [animation-delay:80ms] sm:p-6">
        <AnswerHeader record={record} />
        {record.status === 'running' && <Running record={record} />}
        {record.status === 'failed' && <Failed record={record} onReuse={onReuse} />}
        {record.status === 'completed' && record.result && (
          <>
            {record.kind === 'agent'
              ? <InvestigationBody investigation={record.result as AgentInvestigation} />
              : <QuestionAnswer result={record.result as QuestionResult} themes={record.pattern_themes} />}
            <Trace steps={record.trace} />
            {record.narrative && <Narrative text={record.narrative} />}
            <Actions record={record} onReuse={onReuse} />
          </>
        )}
      </div>
    </div>
  )
}

function AnswerHeader({ record }: { record: InvestigationRecord }) {
  const seconds = record.completed_at ? Math.round((+new Date(record.completed_at) - +new Date(record.created_at)) / 1000) : null
  return (
    <div className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2">
      <span className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-accent-2 text-white shadow-accent">
        <Sparkles className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-semibold">Operations Copilot</p>
        <p className="text-[11.5px] text-ink-3">
          {record.date_range && <>Examined {formatDateShort(record.date_range.start)}{record.date_range.end !== record.date_range.start && <>–{formatDateShort(record.date_range.end)}</>} · </>}
          {record.model && <>{record.model} · </>}
          {seconds !== null && record.status !== 'running' && <>took {formatDuration(seconds)}</>}
        </p>
      </div>
      {record.status !== 'running' && (
        <span className={`rounded-full px-2.5 py-1 text-[11.5px] font-semibold ${record.origin === 'example' ? 'bg-ai-bg text-ai-ink' : 'bg-accent-soft text-accent-strong'}`}
          title="Loaded from saved history. Opening it did not call the AI again.">
          {record.origin === 'example' ? 'Pre-generated example' : 'Saved result'} · not re-run
        </span>
      )}
    </div>
  )
}

function Running({ record }: { record: InvestigationRecord }) {
  const elapsed = useElapsed(record.created_at, true)
  return (
    <div className="rounded-[16px] bg-accent-soft/50 p-5">
      <div className="flex items-center gap-2">
        {[0, 1, 2].map((i) => (
          <span key={i} className="size-2 animate-bounce rounded-full bg-accent" style={{ animationDelay: `${i * 150}ms` }} />
        ))}
        <span className="ml-2 text-[13.5px] font-semibold">Investigating</span>
        <span className="ml-auto text-[12.5px] text-ink-3 tabular">{formatDuration(elapsed)}</span>
      </div>
      <p className="mt-2 text-[13px] leading-relaxed text-ink-2">
        Claude is choosing data tools, checking request details and separating facts from hypotheses. This usually takes one to three minutes.
        You can leave this page: the result is saved to your history either way.
      </p>
    </div>
  )
}

function Failed({ record, onReuse }: { record: InvestigationRecord; onReuse: (q: string) => void }) {
  return (
    <div className="rounded-[16px] bg-status-review-bg p-4">
      <p className="flex items-center gap-2 text-[13.5px] font-semibold text-status-review-ink">
        <CircleAlert className="size-4" /> The investigation did not complete
      </p>
      <p className="mt-1 text-[13px] text-ink-2">{record.error?.message ?? 'Unknown error.'}</p>
      <button type="button" className="btn-secondary mt-3" onClick={() => onReuse(record.question)}>Ask again</button>
    </div>
  )
}

// ---------------------------------------------------------
// The structured answer (InvestigationResult)
// ---------------------------------------------------------

function Section({ icon: Icon, title, count, tone = '', children }: { icon: typeof ListChecks; title: string; count?: number; tone?: string; children: ReactNode }) {
  return (
    <section className={`rounded-[16px] p-4 ${tone}`}>
      <h3 className="mb-2.5 flex items-center gap-2 text-[13px] font-semibold text-ink">
        <Icon className="size-4" strokeWidth={2} /> {title}
        {count !== undefined && <span className="rounded-full bg-surface/80 px-1.5 text-[11px] text-ink-3 tabular">{count}</span>}
      </h3>
      {children}
    </section>
  )
}

function List({ items }: { items: string[] }) {
  if (!items.length) return <p className="text-[12.5px] text-ink-3">None recorded.</p>
  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item} className="flex gap-2 text-[13px] leading-relaxed text-ink-2">
          <span aria-hidden className="mt-[8px] size-1 shrink-0 rounded-full bg-ink-3" />{item}
        </li>
      ))}
    </ul>
  )
}

function QuestionAnswer({ result, themes }: { result: QuestionResult; themes: PatternTheme[] }) {
  return (
    <div className="space-y-3">
      <div className={`flex items-start gap-2.5 rounded-[16px] p-4 ${result.confirmed_root_cause ? 'bg-status-clear-bg' : 'bg-frame'}`}>
        {result.confirmed_root_cause ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-status-clear" /> : <CircleHelp className="mt-0.5 size-4 shrink-0 text-ink-3" />}
        <p className="text-[13px] leading-relaxed">
          {result.confirmed_root_cause ? (
            <><span className="font-semibold">Confirmed root cause: </span>{result.confirmed_root_cause}</>
          ) : (
            <><span className="font-semibold">Root cause not confirmed.</span> <span className="text-ink-2">The data supports the facts and patterns below; explanations remain hypotheses until the missing evidence is checked.</span></>
          )}
        </p>
      </div>

      <Section icon={ListChecks} title="Observed facts" count={result.observed_facts.length} tone="bg-subtle ring-1 ring-line-soft">
        <List items={result.observed_facts} />
      </Section>

      {(result.supported_patterns.length > 0 || themes.length > 0) && (
        <Section icon={Layers} title="Supported patterns" count={result.supported_patterns.length} tone="ring-1 ring-line-soft">
          <List items={result.supported_patterns} />
          {themes.length > 0 && (
            <div className="mt-3 space-y-2 border-t border-line-soft pt-3">
              <p className="text-[11.5px] font-medium text-ink-3">Recurring themes found in request text (pattern analysis)</p>
              {themes.map((t) => (
                <div key={t.theme} className="rounded-xl bg-subtle p-3">
                  <p className="flex flex-wrap items-center gap-2 text-[12.5px] font-semibold">
                    {t.theme}
                    <span className="rounded-full bg-surface px-1.5 py-px text-[10.5px] font-semibold text-ink-3 ring-1 ring-line">{t.evidence_count} requests · {t.confidence} confidence</span>
                  </p>
                  <div className="mt-2"><RequestChips ids={t.request_ids.slice(0, 18)} /></div>
                  {t.request_ids.length > 18 && <p className="mt-1 text-[11px] text-ink-3">+{t.request_ids.length - 18} more</p>}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <Section icon={CircleHelp} title="Hypotheses · not confirmed" count={result.hypotheses.length} tone="bg-ai-bg/50 ring-1 ring-ai/15">
          <List items={result.hypotheses} />
        </Section>
        <Section icon={TriangleAlert} title="Missing evidence" count={result.missing_evidence.length} tone="bg-status-findings-bg/60 ring-1 ring-status-findings/20">
          <List items={result.missing_evidence} />
        </Section>
      </div>

      <Section icon={Lightbulb} title="Recommended next steps" count={result.recommendations.length} tone="bg-accent-soft/60 ring-1 ring-accent/15">
        <List items={result.recommendations} />
      </Section>
    </div>
  )
}

// ---------------------------------------------------------
// How Copilot investigated: the tool trace
// ---------------------------------------------------------

function formatArg(key: string, value: unknown): string {
  const text = String(value)
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(text)) return `${key.replace('_time', '')} ${text.slice(5, 10)} ${text.slice(11, 16)}`
  return `${key.replaceAll('_', ' ')}: ${text.replaceAll('_', ' ')}`
}

/** A short, readable summary of a tool result (key numbers first). */
function resultSummary(step: TraceStep): string {
  if (step.result && typeof step.result === 'object' && !Array.isArray(step.result)) {
    const entries = Object.entries(step.result as Record<string, unknown>)
      .filter(([k]) => !['start_time', 'end_time', 'start_date', 'end_date', 'requests'].includes(k))
      .slice(0, 4)
      .map(([k, v]) => {
        if (v && typeof v === 'object' && !Array.isArray(v)) {
          const inner = Object.entries(v as Record<string, unknown>).slice(0, 4).map(([ik, iv]) => `${ik.replaceAll('_', ' ')} ${String(iv)}`)
          return `${k.replaceAll('_', ' ')}: ${inner.join(', ')}`
        }
        return `${k.replaceAll('_', ' ')}: ${Array.isArray(v) ? `${v.length} items` : String(v)}`
      })
    return entries.join(' · ')
  }
  return (step.result_preview ?? '').slice(0, 200)
}

function Trace({ steps }: { steps: TraceStep[] }) {
  const [open, setOpen] = useState(false)
  if (!steps.length) return null
  return (
    <div className="mt-4 rounded-[16px] ring-1 ring-line-soft">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-3 text-left text-[13px] font-semibold hover:text-accent">
        <Wrench className="size-4" /> How Copilot investigated
        <span className="rounded-full bg-frame px-1.5 text-[11px] text-ink-3 tabular">{steps.length} tool calls</span>
        <ChevronDown className={`ml-auto size-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <ol className="space-y-1 px-3 pb-3">
          {steps.map((step, i) => (
            <li key={i} className="flex animate-fade gap-3 rounded-xl px-2 py-2 hover:bg-subtle">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-[11px] font-bold text-accent tabular">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="text-[12.5px] font-semibold">{toolLabel(step.tool)} <span className="font-normal text-ink-3">· {step.tool}</span></p>
                <p className="mt-1 flex flex-wrap gap-1">
                  {Object.entries(step.args).map(([k, v]) => (
                    <span key={k} className="rounded-md bg-frame px-1.5 py-0.5 text-[11px] text-ink-2 tabular">{formatArg(k, v)}</span>
                  ))}
                </p>
                <p className="mt-1 line-clamp-2 text-[12px] text-ink-3 tabular">{resultSummary(step)}{step.result_truncated && ' (truncated)'}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function Narrative({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-3 rounded-[16px] ring-1 ring-line-soft">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-3 text-left text-[13px] font-semibold hover:text-accent">
        <MessageSquareQuote className="size-4" /> Copilot’s written answer
        <ChevronDown className={`ml-auto size-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <p className="animate-fade px-4 pb-4 text-[13px] leading-relaxed whitespace-pre-wrap text-ink-2">{text}</p>}
    </div>
  )
}

function Actions({ record, onReuse }: { record: InvestigationRecord; onReuse: (q: string) => void }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    const r = record.result as Partial<QuestionResult & AgentInvestigation>
    const lines = [
      `Q: ${record.question}`,
      ...(r.summary ? ['', r.summary] : []),
      '', 'Observed facts:', ...(r.observed_facts ?? []).map((f) => `- ${f}`),
      '', 'Hypotheses (not confirmed):', ...(r.hypotheses ?? []).map((h) => `- ${h}`),
      '', 'Recommendations:', ...(r.recommendations ?? []).map((h) => `- ${h}`),
    ]
    try {
      await navigator.clipboard.writeText(lines.join('\n'))
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // Clipboard can be unavailable (permissions); nothing else to do.
    }
  }
  return (
    <div className="mt-4 flex items-center gap-1">
      <button type="button" onClick={copy} className="btn-ghost-sm" aria-label="Copy answer">
        {copied ? <Check className="size-4 text-good" /> : <Copy className="size-4" />} {copied ? 'Copied' : 'Copy'}
      </button>
      {record.kind === 'question' && (
        <button type="button" onClick={() => onReuse(record.question)} className="btn-ghost-sm">
          <MessageSquareQuote className="size-4" /> Reuse question
        </button>
      )}
    </div>
  )
}
