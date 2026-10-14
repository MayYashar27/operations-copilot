import { CircleHelp, ListChecks, Lightbulb, SearchCheck, TriangleAlert } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import type { AgentDetail, AgentInvestigation, AgentMetrics, EvidenceRequest } from '../../api/types'
import { TrendLineChart } from '../../components/charts/TrendLineChart'
import { Panel } from '../../components/ui/Panel'
import { RequestChips } from '../../components/ui/RequestChip'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { SourceTag } from '../../components/ui/SourceTag'
import { formatDayMonth, formatNumber, formatWeekdayShort } from '../../lib/format'
import { signalLabel, signalRequestIds, signalSentence } from '../../lib/signals'

export type SelectRequest = (id: number) => void

// ---------------------------------------------------------
// Metrics against the team (same lookback period on both sides)
// ---------------------------------------------------------

const COMPARE = [
  { label: 'Transfer rate', unit: '%', digits: 1, pick: (m: AgentMetrics) => m.transfer_rate_percent, points: true },
  { label: 'Avg. handling time', unit: ' min', digits: 1, pick: (m: AgentMetrics) => m.average_handling_time_minutes, points: false },
  { label: 'First-line resolution', unit: '%', digits: 1, pick: (m: AgentMetrics) => m.first_line_resolution_rate_percent, points: true },
  { label: 'Requests per hour', unit: '', digits: 2, pick: (m: AgentMetrics) => m.requests_per_scheduled_hour, points: false },
]

export function MetricComparison({ detail }: { detail: AgentDetail }) {
  const agent = detail.lookback_metrics
  const team = detail.team_baseline
  const today = detail.day_metrics
  if (!agent || !team) return null

  return (
    <section aria-label="Metrics compared with the team" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {COMPARE.map((c) => {
        const a = c.pick(agent)
        const t = c.pick(team)
        const diff = a !== null && t !== null ? a - t : null
        return (
          <div key={c.label} className="card p-4">
            <p className="text-[12.5px] font-medium text-ink-2">{c.label}</p>
            <p className="mt-2 flex items-baseline gap-1">
              <span className="text-[22px] leading-none font-bold tracking-[-0.03em] tabular">{formatNumber(a, c.digits)}</span>
              <span className="text-[12px] font-medium text-ink-3">{c.unit.trim()}</span>
            </p>
            <p className="mt-2 text-[12px] text-ink-3 tabular">
              Team {formatNumber(t, c.digits)}{c.unit}
              {diff !== null && (
                <span className="ml-1.5 rounded-full bg-frame px-1.5 py-px font-semibold text-ink-2">
                  {diff > 0 ? '+' : ''}{formatNumber(diff, c.digits)}{c.points ? ' pts' : c.unit}
                </span>
              )}
            </p>
            {today && <p className="mt-1 text-[11.5px] text-ink-3 tabular">On this shift: {formatNumber(c.pick(today), c.digits)}{c.unit}</p>}
          </div>
        )
      })}
    </section>
  )
}

// ---------------------------------------------------------
// Daily trend
// ---------------------------------------------------------

type TrendKey = 'transfer' | 'handling' | 'requests'

export function TrendPanel({ detail }: { detail: AgentDetail }) {
  const [metric, setMetric] = useState<TrendKey>('transfer')
  const team = detail.team_baseline
  const spec = {
    transfer: { pick: (p: AgentDetail['daily_trends'][number]) => p.transfer_rate_percent, ref: team?.transfer_rate_percent, fmt: (v: number) => `${formatNumber(v, 0)}%` },
    handling: { pick: (p: AgentDetail['daily_trends'][number]) => p.average_handling_time_minutes, ref: team?.average_handling_time_minutes, fmt: (v: number) => `${formatNumber(v, 1)}m` },
    requests: { pick: (p: AgentDetail['daily_trends'][number]) => p.handled_requests, ref: undefined, fmt: (v: number) => formatNumber(v, 0) },
  }[metric]

  return (
    <Panel
      title="Daily trend"
      description={`Working days since ${detail.lookback_start ? formatDayMonth(detail.lookback_start) : 'the start of the period'}. The highlighted point is the screened shift.`}
      actions={
        <SegmentedControl label="Trend metric" value={metric} onChange={setMetric}
          options={[{ value: 'transfer', label: 'Transfer rate' }, { value: 'handling', label: 'Handling time' }, { value: 'requests', label: 'Requests' }]} />
      }
    >
      <TrendLineChart
        points={detail.daily_trends.map((p) => ({
          key: p.date, label: formatDayMonth(p.date), tooltip: `${formatWeekdayShort(p.date)} ${formatDayMonth(p.date)}`,
          value: spec.pick(p), highlight: p.date === detail.date,
        }))}
        format={spec.fmt}
        reference={spec.ref != null ? { value: spec.ref, label: 'Team' } : undefined}
      />
    </Panel>
  )
}

// ---------------------------------------------------------
// Evidence: metric signals | AI observations, kept apart
// ---------------------------------------------------------

export function EvidenceColumns({ detail, onSelect, active }: { detail: AgentDetail; onSelect: SelectRequest; active: number | null }) {
  const periods = detail.period_comparison
  const docs = detail.documentation_screening

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title={<span className="flex items-center gap-2">Metric signals <SourceTag source="rule" label="Rules" /></span>}
        description="Deterministic thresholds on request data. Exploratory, and not proof of an error.">
        {detail.rule_signals.length === 0 ? (
          <p className="text-[13px] text-ink-3">No metric signals crossed a threshold for this agent.</p>
        ) : (
          <ul className="space-y-3">
            {detail.rule_signals.map((s) => (
              <li key={s.code} className="rounded-[14px] bg-rule-bg/60 p-3.5">
                <p className="text-[12px] font-semibold text-rule-ink">{signalLabel(s.code)}</p>
                <p className="mt-1 text-[13px] leading-snug text-ink">{signalSentence(s)}</p>
                {signalRequestIds(s).length > 0 && (
                  <div className="mt-2"><RequestChips ids={signalRequestIds(s)} onSelect={onSelect} active={active} /></div>
                )}
              </li>
            ))}
          </ul>
        )}

        {periods && (
          <div className="mt-4">
            <p className="mb-2 text-[12px] font-medium text-ink-3">How the rules compare periods</p>
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="text-left text-[11.5px] text-ink-3">
                  <th className="pb-1.5 font-medium">Period</th>
                  <th className="pb-1.5 text-right font-medium">Requests</th>
                  <th className="pb-1.5 text-right font-medium">Transfer rate</th>
                  <th className="pb-1.5 text-right font-medium">Handling</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft tabular">
                {([['Earlier', periods.earlier], ['Later', periods.later], ['Peers, later', periods.peers_later]] as const).map(([label, p]) => (
                  <tr key={label}>
                    <td className="py-1.5 text-ink-2">{label}{p.dates && <span className="text-ink-3"> · {formatDayMonth(p.dates[0])}–{formatDayMonth(p.dates[1])}</span>}</td>
                    <td className="py-1.5 text-right">{formatNumber(p.requests)}</td>
                    <td className="py-1.5 text-right font-semibold">{formatNumber(p.transfer_rate_percent, 1)}%</td>
                    <td className="py-1.5 text-right">{formatNumber(p.average_handling_time_minutes, 1)} min</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {docs && (
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            {[
              ['Documented', `${docs.documented_requests}/${docs.total_requests}`],
              [`Under ${docs.short_word_threshold} words`, String(docs.short_documentation_count)],
              ['Avg. words', formatNumber(docs.average_documentation_words, 1)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-subtle px-2 py-2.5 ring-1 ring-line-soft">
                <p className="text-[15px] font-bold tabular">{value}</p>
                <p className="mt-0.5 text-[11px] text-ink-3">{label}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel title={<span className="flex items-center gap-2">AI observations <SourceTag source="ai" /></span>}
        description="Claude read every note from this shift. Observations need human validation; repeated or short notes are not problems by themselves.">
        {detail.ai_observation_summary && (
          <p className="mb-3 rounded-[14px] bg-ai-bg/60 p-3.5 text-[13px] leading-relaxed text-ink">{detail.ai_observation_summary}</p>
        )}
        {detail.ai_observations.length === 0 ? (
          <p className="text-[13px] text-ink-3">No AI observations for this agent.</p>
        ) : (
          <ul className="space-y-2">
            {detail.ai_observations.map((o) => <Observation key={o.finding} title={o.finding} body={o.explanation} ids={o.request_ids} onSelect={onSelect} active={active} />)}
          </ul>
        )}
      </Panel>
    </div>
  )
}

function Observation({ title, body, ids, onSelect, active }: { title: string; body: string; ids: number[]; onSelect: SelectRequest; active: number | null }) {
  const [open, setOpen] = useState(false)
  return (
    <li className="rounded-[14px] ring-1 ring-line-soft transition hover:ring-line">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="w-full p-3.5 text-left">
        <p className="text-[13px] leading-snug font-semibold text-ink">{title}</p>
        <p className={`mt-1 text-[12.5px] leading-relaxed text-ink-2 ${open ? '' : 'line-clamp-2'}`}>{body}</p>
      </button>
      <div className="px-3.5 pb-3"><RequestChips ids={ids} onSelect={onSelect} active={active} /></div>
    </li>
  )
}

// ---------------------------------------------------------
// Saved deep investigation
// ---------------------------------------------------------

function Block({ icon: Icon, title, tone, children }: { icon: typeof ListChecks; title: string; tone: string; children: ReactNode }) {
  return (
    <div className={`rounded-[14px] p-4 ${tone}`}>
      <p className="mb-2 flex items-center gap-1.5 text-[12.5px] font-semibold text-ink"><Icon className="size-4" strokeWidth={2} />{title}</p>
      {children}
    </div>
  )
}

function Bullets({ items, empty = 'None recorded.' }: { items: string[]; empty?: string }) {
  if (items.length === 0) return <p className="text-[12.5px] text-ink-3">{empty}</p>
  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item} className="flex gap-2 text-[12.5px] leading-relaxed text-ink-2">
          <span aria-hidden className="mt-[7px] size-1 shrink-0 rounded-full bg-ink-3" />{item}
        </li>
      ))}
    </ul>
  )
}

/** Facts, possible explanations and next steps, deliberately separated. */
export function InvestigationBody({ investigation, onSelect, active }: { investigation: AgentInvestigation; onSelect?: SelectRequest; active?: number | null }) {
  return (
    <div className="space-y-4">
      <p className="text-[14px] leading-relaxed text-ink">{investigation.summary}</p>

      <Block icon={ListChecks} title="Observed facts" tone="bg-subtle ring-1 ring-line-soft">
        <Bullets items={investigation.observed_facts} />
      </Block>

      {investigation.findings.length > 0 && (
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-[12.5px] font-semibold"><SearchCheck className="size-4" />Evidence-backed findings</p>
          <ul className="space-y-2">
            {investigation.findings.map((f) => (
              <li key={f.finding} className="rounded-[14px] p-3.5 ring-1 ring-line-soft">
                <p className="text-[13px] font-semibold">{f.finding}</p>
                <p className="mt-1 text-[12.5px] leading-relaxed text-ink-2">{f.interpretation}</p>
                {f.supporting_metrics.length > 0 && (
                  <p className="mt-2 flex flex-wrap gap-1">
                    {f.supporting_metrics.map((m) => <span key={m} className="rounded-md bg-rule-bg px-1.5 py-0.5 text-[11.5px] text-rule-ink">{m}</span>)}
                  </p>
                )}
                <div className="mt-2"><RequestChips ids={f.supporting_request_ids} onSelect={onSelect} active={active} /></div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <Block icon={CircleHelp} title="Hypotheses · not confirmed" tone="bg-ai-bg/50 ring-1 ring-ai/15">
          <Bullets items={investigation.hypotheses} />
        </Block>
        <Block icon={TriangleAlert} title="Missing evidence" tone="bg-status-findings-bg/60 ring-1 ring-status-findings/20">
          <Bullets items={investigation.missing_evidence} />
        </Block>
      </div>

      <Block icon={Lightbulb} title="Recommended follow-up" tone="bg-accent-soft/60 ring-1 ring-accent/15">
        <Bullets items={investigation.recommendations} />
      </Block>
    </div>
  )
}

// ---------------------------------------------------------
// Cited requests
// ---------------------------------------------------------

export function RequestEvidence({ requests, active }: { requests: EvidenceRequest[]; active: number | null }) {
  return (
    <Panel title="Cited requests" description={`The ${requests.length} requests referenced above, with their documentation. Notes are synthetic.`}>
      {requests.length === 0 ? (
        <p className="text-[13px] text-ink-3">No requests are cited for this agent.</p>
      ) : (
        <ul className="space-y-2">
          {requests.map((r) => (
            <li key={r.request_id} id={`req-${r.request_id}`}
              className={`scroll-mt-24 rounded-[14px] p-3.5 transition-all duration-500 ${active === r.request_id ? 'bg-accent-soft ring-2 ring-accent' : 'bg-subtle ring-1 ring-line-soft'}`}>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-ink-3 tabular">
                <span className="text-[13px] font-bold text-ink">#{r.request_id}</span>
                <span>{r.request_time.slice(11, 16)}</span>
                <span className="text-ink-2">{(r.classification ?? '').replaceAll('_', ' ')}</span>
                <span>{r.status}{r.transferred_to ? ` → ${r.transferred_to.replaceAll('_', ' ')}` : ''}</span>
                <span>{formatNumber(r.handling_time_minutes, 1)} min</span>
              </div>
              {r.subject && <p className="mt-1.5 text-[13px] font-semibold">{r.subject}</p>}
              <p className="mt-1 text-[12.5px] leading-relaxed text-ink-2">{r.documentation || <em className="text-ink-3">No documentation</em>}</p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
