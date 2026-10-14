import { CircleAlert, Loader2, Plus, SearchX, Star, Users } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useDatedLink } from '../../app/context'
import type { InvestigationSummary } from '../../api/types'
import { SidePanel, SideSearch, SideSection } from '../../components/layout/SidePanel'
import { formatDateTime, formatTime, isToday } from '../../lib/format'

interface Props {
  items: InvestigationSummary[] | null
  selectedId?: string
  loading: boolean
}

/** Saved investigation history: examples pinned, then this machine's runs. */
export function HistoryPanel({ items, selectedId, loading }: Props) {
  const datedLink = useDatedLink()
  const [query, setQuery] = useState('')
  const needle = query.trim().toLowerCase()
  const visible = (items ?? []).filter((i) => !needle || i.question.toLowerCase().includes(needle) || (i.agent_id ?? '').toLowerCase().includes(needle))

  const examples = visible.filter((i) => i.origin === 'example')
  const local = visible.filter((i) => i.origin === 'local')
  const today = local.filter((i) => isToday(i.created_at))
  const earlier = local.filter((i) => !isToday(i.created_at))

  const renderItem = (item: InvestigationSummary) => {
    const selected = item.id === selectedId
    return (
      <Link key={item.id} to={datedLink(`/copilot/${item.id}`)} aria-current={selected ? 'page' : undefined}
        className={`group flex gap-2.5 rounded-[14px] px-3.5 py-3 transition-all duration-200 ${
          selected ? 'bg-gradient-to-r from-selected to-selected-2 shadow-card' : 'bg-surface/70 hover:bg-surface hover:shadow-card'
        }`}>
        <span className="mt-0.5 shrink-0">
          {item.status === 'running' ? <Loader2 className="size-4 animate-spin text-accent" />
            : item.status === 'failed' ? <CircleAlert className="size-4 text-status-review" />
            : item.kind === 'agent' ? <Users className="size-4 text-ink-3" />
            : item.origin === 'example' ? <Star className={`size-4 ${selected ? 'fill-accent text-accent' : 'text-ink-3'}`} />
            : <span className="mt-1.5 block size-1.5 rounded-full bg-chart-today" />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="line-clamp-2 text-[13px] leading-snug font-medium text-ink">{item.question}</span>
          <span className="mt-1 block text-[11.5px] text-ink-3">
            {item.status === 'running' ? 'Running…' : item.status === 'failed' ? 'Failed · ' : ''}
            {item.status !== 'running' && (isToday(item.created_at) && item.origin === 'local' ? formatTime(item.created_at) : formatDateTime(item.created_at))}
          </span>
        </span>
      </Link>
    )
  }

  return (
    <SidePanel
      title="Investigations"
      count={items?.length}
      toolbar={
        <div className="space-y-3">
          <Link to={datedLink('/copilot')} className="btn-primary w-full justify-center">
            <Plus className="size-4" strokeWidth={2.4} /> New investigation
          </Link>
          <SideSearch value={query} onChange={setQuery} placeholder="Search investigations…" />
        </div>
      }
    >
      {loading && <p className="px-2 text-[12.5px] text-ink-3">Loading history…</p>}
      {!loading && visible.length === 0 && (
        <div className="flex flex-col items-center px-4 py-8 text-center">
          <SearchX className="mb-2 size-5 text-ink-3" />
          <p className="text-[13px] font-semibold">{needle ? 'No matching investigations' : 'No saved investigations yet'}</p>
        </div>
      )}
      {examples.length > 0 && <SideSection label="Pre-generated examples">{examples.map(renderItem)}</SideSection>}
      {today.length > 0 && <SideSection label="Today">{today.map(renderItem)}</SideSection>}
      {earlier.length > 0 && <SideSection label="Earlier">{earlier.map(renderItem)}</SideSection>}
    </SidePanel>
  )
}
