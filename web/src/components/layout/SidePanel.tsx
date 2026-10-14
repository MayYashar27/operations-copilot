import { Search } from 'lucide-react'
import type { ReactNode } from 'react'

/** Contextual side panel: title + count, optional search, scrolling sections. */
export function SidePanel({ title, count, children, toolbar }: {
  title: string
  count?: number
  toolbar?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-2 pr-8 lg:pr-0">
          <h2 className="text-[19px] font-semibold tracking-[-0.02em]">{title}</h2>
          {count !== undefined && (
            <span className="rounded-full bg-gradient-to-br from-accent to-accent-2 px-2 py-0.5 text-[11px] font-semibold text-white tabular">
              {count}
            </span>
          )}
        </div>
        {toolbar && <div className="mt-4">{toolbar}</div>}
      </div>
      <div className="scroll-soft min-h-0 flex-1 space-y-5 overflow-y-auto px-3 pb-5">{children}</div>
    </div>
  )
}

export function SideSearch({ value, onChange, placeholder }: {
  value: string
  onChange: (value: string) => void
  placeholder: string
}) {
  return (
    <label className="flex h-11 items-center gap-2.5 rounded-xl bg-surface px-3.5 shadow-card ring-1 ring-line/60 transition focus-within:ring-2 focus-within:ring-accent/40">
      <Search className="size-4 shrink-0 text-ink-3" strokeWidth={2} />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-ink-3"
      />
    </label>
  )
}

export function SideSection({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section>
      <p className="mb-2 px-2 text-[12px] font-medium text-ink-3">{label}</p>
      <div className="space-y-2">{children}</div>
    </section>
  )
}

/** A list item card. Selected items get the soft lavender wash from the reference. */
export function SideItem({ selected, children, className = '' }: {
  selected?: boolean
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={`group relative rounded-[14px] px-3.5 py-3 transition-all duration-200 ${
        selected
          ? 'bg-gradient-to-r from-selected to-selected-2 shadow-card'
          : 'bg-surface/70 hover:bg-surface hover:shadow-card'
      } ${className}`}
    >
      {children}
    </div>
  )
}
