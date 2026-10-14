import { FileText } from 'lucide-react'

/**
 * A cited request ID. When `onSelect` is given, clicking jumps to that
 * request's documentation; otherwise it is a static reference.
 */
export function RequestChip({ id, onSelect, active }: { id: number; onSelect?: (id: number) => void; active?: boolean }) {
  const base = 'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11.5px] font-semibold tabular transition-colors'
  if (!onSelect) {
    return <span className={`${base} bg-frame text-ink-2`}>#{id}</span>
  }
  return (
    <button
      type="button"
      onClick={() => onSelect(id)}
      title={`Show request #${id}`}
      className={`${base} ${active ? 'bg-accent text-white' : 'bg-accent-soft text-accent-strong hover:bg-accent hover:text-white'}`}
    >
      <FileText className="size-3" strokeWidth={2.2} />#{id}
    </button>
  )
}

export function RequestChips({ ids, onSelect, active }: { ids: number[]; onSelect?: (id: number) => void; active?: number | null }) {
  if (ids.length === 0) return null
  return (
    <span className="flex flex-wrap gap-1">
      {ids.map((id) => <RequestChip key={id} id={id} onSelect={onSelect} active={active === id} />)}
    </span>
  )
}
