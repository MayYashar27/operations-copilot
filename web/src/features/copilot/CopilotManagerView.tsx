import { CheckCircle2, CircleHelp, FileText, Lightbulb, MessageSquareText, Quote, Sparkles } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { formatNumber } from '../../lib/format'
import type { Breakdown, CopilotView } from './copilotSummary'

/** The under-a-minute read. Sections appear only when the saved result supports them. */
export function CopilotManagerView({ view }: { view: CopilotView }) {
  const sections: ReactNode[] = []

  sections.push(
    <Section key="answer" icon={MessageSquareText} title="Direct answer">
      {view.directAnswer.isCausal && (
        <p className={`mb-2.5 flex items-start gap-2 rounded-xl px-3 py-2 text-[13px] ${view.directAnswer.rootCause ? 'bg-status-clear-bg' : 'bg-frame'}`}>
          {view.directAnswer.rootCause
            ? <><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-status-clear" /><span><b>Confirmed cause:</b> {view.directAnswer.rootCause}</span></>
            : <><CircleHelp className="mt-0.5 size-4 shrink-0 text-ink-3" /><span><b>Cause not confirmed.</b> <span className="text-ink-2">What the data shows:</span></span></>}
        </p>
      )}
      <ul className="space-y-1.5">
        {view.directAnswer.lines.map((line) => (
          <li key={line} className="flex gap-2 text-[14px] leading-relaxed text-ink">
            <span aria-hidden className="mt-[9px] size-1.5 shrink-0 rounded-full bg-accent" />{line}
          </li>
        ))}
      </ul>
    </Section>,
  )

  if (view.findings.length > 0) {
    sections.push(
      <Section key="findings" icon={Sparkles} title="Key findings">
        <ol className="space-y-2">
          {view.findings.map((f, i) => (
            <li key={f} className="flex gap-3 rounded-xl bg-subtle px-3 py-2.5 ring-1 ring-line-soft">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-[11.5px] font-bold text-accent tabular">{i + 1}</span>
              <p className="text-[13px] leading-relaxed text-ink">{f}</p>
            </li>
          ))}
        </ol>
      </Section>,
    )
  }

  if (view.breakdowns.length > 0 || view.numbers.length > 0 || view.themes.length > 0) {
    sections.push(
      <Section key="evidence" icon={FileText} title="Supporting evidence" note="Captured from the tools Copilot called">
        {view.numbers.length > 0 && (
          <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {view.numbers.map((n) => (
              <div key={`${n.label}-${n.window}`} className="rounded-xl bg-subtle px-3 py-2.5 ring-1 ring-line-soft">
                <p className="text-[18px] leading-tight font-bold tabular">{n.value}</p>
                <p className="mt-0.5 text-[11.5px] text-ink-2">{n.label}</p>
                {n.window && <p className="text-[11px] text-ink-3 tabular">{n.window}</p>}
                {n.compare && <p className="mt-1 text-[11.5px] text-ink-2 tabular">vs <b>{n.compare.value}</b>{n.compare.window && <span className="text-ink-3"> · {n.compare.window}</span>}</p>}
              </div>
            ))}
          </div>
        )}
        {view.breakdowns.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2">
            {view.breakdowns.map((b) => <BreakdownCard key={`${b.title}-${b.window}`} breakdown={b} />)}
          </div>
        )}
        {view.themes.length > 0 && <Themes view={view} />}
        {view.hiddenEvidence > 0 && (
          <p className="mt-3 text-[11.5px] text-ink-3">{view.hiddenEvidence} more evidence {view.hiddenEvidence === 1 ? 'item is' : 'items are'} in Technical details.</p>
        )}
      </Section>,
    )
  }

  if (view.conclusion || view.nextSteps.length > 0) {
    sections.push(
      <Section key="conclusion" icon={Lightbulb} title="Conclusion and next steps">
        {view.conclusion?.hypothesis && (
          <div className="rounded-xl bg-ai-bg/50 px-3 py-2.5 ring-1 ring-ai/10">
            <p className="text-[11px] font-semibold text-ai-ink">Possible explanation · Requires verification</p>
            <p className="mt-0.5 text-[13px] leading-relaxed text-ink">{view.conclusion.hypothesis}</p>
          </div>
        )}
        {view.conclusion?.needs && (
          <p className="mt-2 text-[12.5px] leading-relaxed text-ink-2"><b className="text-status-findings-ink">To confirm it:</b> {view.conclusion.needs}</p>
        )}
        {view.nextSteps.length > 0 && (
          <ol className="mt-3 space-y-2">
            {view.nextSteps.map((s, i) => (
              <li key={s} className="flex gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-2 text-[11.5px] font-bold text-white tabular">{i + 1}</span>
                <p className="text-[13px] leading-relaxed text-ink">{s}</p>
              </li>
            ))}
          </ol>
        )}
      </Section>,
    )
  }

  return <div className="space-y-3">{sections}</div>
}

function Section({ icon: Icon, title, note, children }: { icon: typeof Sparkles; title: string; note?: string; children: ReactNode }) {
  return (
    <section className="animate-rise rounded-[16px] bg-surface p-4 ring-1 ring-line-soft sm:p-5">
      <h3 className="mb-3 flex items-center gap-2 text-[13.5px] font-semibold">
        <Icon className="size-4 text-accent" strokeWidth={2} />{title}
        {note && <span className="text-[11.5px] font-normal text-ink-3">· {note}</span>}
      </h3>
      {children}
    </section>
  )
}

function BreakdownCard({ breakdown }: { breakdown: Breakdown }) {
  const max = Math.max(...breakdown.rows.map((r) => r.value), 1)
  const total = breakdown.rows.reduce((sum, r) => sum + r.value, 0)
  return (
    <div className="rounded-xl bg-subtle p-3.5 ring-1 ring-line-soft">
      <p className="text-[12.5px] font-semibold">{breakdown.title}</p>
      {breakdown.window && <p className="text-[11px] text-ink-3 tabular">{breakdown.window}</p>}
      {breakdown.kind === 'timeline' ? (
        <div className="mt-3 flex h-16 items-end gap-[2px]" role="img" aria-label={`${breakdown.title}: ${breakdown.rows.map((r) => `${r.label} ${r.value}`).join(', ')}`}>
          {breakdown.rows.map((r) => (
            <span key={r.label} title={`${r.label}: ${r.value}`} className="flex-1 rounded-t-[2px] bg-chart-today/80 hover:bg-accent-strong"
              style={{ height: `${Math.max(3, (r.value / max) * 100)}%` }} />
          ))}
        </div>
      ) : (
        <ul className="mt-2.5 space-y-1.5">
          {breakdown.rows.slice(0, 6).map((r) => (
            <li key={r.label} className="text-[12px]">
              <div className="flex justify-between gap-2"><span className="text-ink-2">{r.label}</span><span className="font-semibold tabular">{formatNumber(r.value)}{total > 0 && <span className="ml-1 font-normal text-ink-3">{Math.round((r.value / total) * 100)}%</span>}</span></div>
              <div className="mt-0.5 h-1.5 rounded-full bg-frame"><div className="h-full rounded-full bg-chart-today" style={{ width: `${(r.value / max) * 100}%` }} /></div>
            </li>
          ))}
          {breakdown.rows.length > 6 && <li className="text-[11px] text-ink-3">+{breakdown.rows.length - 6} more in Technical details</li>}
        </ul>
      )}
    </div>
  )
}

function Themes({ view }: { view: CopilotView }) {
  const [selected, setSelected] = useState<number | null>(null)
  const doc = selected !== null ? view.requestDocs.get(selected) : undefined
  return (
    <div className="mt-3 space-y-2 border-t border-line-soft pt-3">
      <p className="text-[11.5px] font-medium text-ink-3">Recurring themes in the request notes, with the requests behind them</p>
      {view.themes.map((t) => (
        <div key={t.theme}>
          <p className="text-[12.5px] font-semibold">{t.theme} <span className="font-normal text-ink-3">· {t.requestIds.length} requests, {t.confidence} confidence</span></p>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {t.requestIds.slice(0, 10).map((id) => (
              <button key={id} type="button" onClick={() => setSelected(id === selected ? null : id)} aria-pressed={id === selected}
                className={`rounded-md px-1.5 py-0.5 text-[11.5px] font-semibold tabular transition-colors ${id === selected ? 'bg-accent text-white' : 'bg-accent-soft text-accent-strong hover:bg-selected'}`}>
                #{id}
              </button>
            ))}
            {t.requestIds.length > 10 && <span className="px-1 text-[11px] text-ink-3">+{t.requestIds.length - 10} more</span>}
          </div>
        </div>
      ))}
      {selected !== null && (
        <div className="animate-fade rounded-xl bg-subtle p-3 ring-1 ring-line-soft">
          {doc ? (
            <>
              <p className="text-[12.5px] font-semibold">#{selected} {doc.subject && <>· {doc.subject}</>} <span className="font-normal text-ink-3">{doc.classification?.replaceAll('_', ' ')} {doc.time?.slice(11, 16)}</span></p>
              <p className="mt-1.5 flex gap-2 text-[12.5px] leading-relaxed text-ink-2"><Quote className="mt-0.5 size-3.5 shrink-0 text-ink-3" />{doc.documentation || 'No documentation'}</p>
            </>
          ) : (
            <p className="text-[12.5px] text-ink-3">The note for #{selected} was not captured in this investigation’s trace.</p>
          )}
        </div>
      )}
    </div>
  )
}
