import { ArrowDownUp, SearchX } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { AgentRow } from '../../api/types'
import { SidePanel, SideSearch } from '../../components/layout/SidePanel'
import { AgentMonogram } from '../../components/ui/AgentMonogram'
import { SourceIcon } from '../../components/ui/SourceTag'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatNumber, formatPercent } from '../../lib/format'
import { hasMetricSignals } from '../../lib/attention'
import { type EvidenceFilter, type SortKey, type StatusFilter, SORT_LABELS, filterAgents, keyFinding } from './agentFilters'

export interface DirectoryState {
  query: string
  status: StatusFilter
  evidence: EvidenceFilter
  sort: SortKey
}

interface Props {
  rows: AgentRow[]
  state: DirectoryState
  onChange: (state: DirectoryState) => void
  selectedId?: string
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={active}
      className={`inline-flex h-7 items-center gap-1 rounded-full px-2.5 text-[12px] font-semibold whitespace-nowrap transition-all ${
        active ? 'bg-gradient-to-br from-accent to-accent-2 text-white shadow-accent' : 'bg-surface/80 text-ink-2 ring-1 ring-line/60 hover:text-accent'
      }`}>
      {children}
    </button>
  )
}

/** Searchable, filterable list of every screened agent. */
export function AgentDirectory({ rows, state, onChange, selectedId }: Props) {
  const datedLink = useDatedLink()
  const set = (patch: Partial<DirectoryState>) => onChange({ ...state, ...patch })
  const visible = filterAgents(rows, state)
  const count = (status: StatusFilter) => rows.filter((r) => status === 'all' || r.status === status).length
  const metricCount = rows.filter(hasMetricSignals).length

  return (
    <SidePanel
      title="Agents"
      count={rows.length}
      toolbar={
        <div className="space-y-3">
          <SideSearch value={state.query} onChange={(query) => set({ query })} placeholder="Search ID or finding…" />
          <div className="flex flex-wrap gap-1.5">
            <Chip active={state.status === 'all'} onClick={() => set({ status: 'all' })}>All {count('all')}</Chip>
            <Chip active={state.status === 'investigation'} onClick={() => set({ status: 'investigation' })}>Deep review {count('investigation')}</Chip>
            <Chip active={state.status === 'findings'} onClick={() => set({ status: 'findings' })}>Findings {count('findings')}</Chip>
            {count('screened') > 0 && (
              <Chip active={state.status === 'screened'} onClick={() => set({ status: 'screened' })}>Clear {count('screened')}</Chip>
            )}
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex gap-1.5">
              <Chip active={state.evidence === 'metric'} onClick={() => set({ evidence: state.evidence === 'metric' ? 'all' : 'metric' })}>
                <SourceIcon source="rule" className={`size-3 ${state.evidence === 'metric' ? 'text-white' : ''}`} /> Metric {metricCount}
              </Chip>
              <Chip active={state.evidence === 'ai-only'} onClick={() => set({ evidence: state.evidence === 'ai-only' ? 'all' : 'ai-only' })}>
                <SourceIcon source="ai" className={`size-3 ${state.evidence === 'ai-only' ? 'text-white' : ''}`} /> AI only
              </Chip>
            </div>
            <label className="relative inline-flex items-center gap-1 text-[12px] font-semibold text-ink-2">
              <ArrowDownUp className="size-3.5 text-ink-3" />
              <span className="sr-only">Sort by</span>
              <select value={state.sort} onChange={(e) => set({ sort: e.target.value as SortKey })}
                className="cursor-pointer appearance-none bg-transparent pr-1 outline-none hover:text-accent">
                {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => <option key={key} value={key}>{SORT_LABELS[key]}</option>)}
              </select>
            </label>
          </div>
        </div>
      }
    >
      {visible.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <SearchX className="mb-2 size-5 text-ink-3" />
          <p className="text-[13px] font-semibold">No agents match</p>
          <button type="button" className="link mt-1 text-[12.5px]"
            onClick={() => onChange({ query: '', status: 'all', evidence: 'all', sort: state.sort })}>Clear filters</button>
        </div>
      ) : (
        <ul className="space-y-1.5">
          {visible.map((row) => {
            const selected = row.agent_id === selectedId
            const finding = keyFinding(row)
            return (
              <li key={row.agent_id}>
                <Link
                  to={datedLink(`/agents/${row.agent_id}`)}
                  aria-current={selected ? 'page' : undefined}
                  className={`group block rounded-[14px] px-3 py-2.5 transition-all duration-200 ${
                    selected ? 'bg-gradient-to-r from-selected to-selected-2 shadow-card' : 'bg-surface/70 hover:bg-surface hover:shadow-card'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <AgentMonogram id={row.agent_id} status={row.status} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[13.5px] font-semibold">Agent {row.agent_id}</p>
                        <StatusBadge status={row.status} compact />
                      </div>
                      <p className="mt-0.5 text-[11.5px] text-ink-3 tabular">
                        {formatNumber(row.metrics?.handled_requests)} requests · {formatPercent(row.metrics?.transfer_rate_percent)} transferred
                      </p>
                    </div>
                  </div>
                  {finding && (
                    <p className="mt-2 flex items-start gap-1.5 text-[12px] leading-snug text-ink-2">
                      <SourceIcon source={finding.source} className="mt-[2px] size-3.5 shrink-0" />
                      <span className="line-clamp-2">{finding.text}</span>
                    </p>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </SidePanel>
  )
}
