import type { ReactNode } from 'react'

interface PanelProps {
  title?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  children: ReactNode
  /** Remove body padding, e.g. for edge-to-edge tables. */
  flush?: boolean
  className?: string
}

/** The standard bordered container for a section of content. */
export function Panel({ title, description, actions, children, flush, className = '' }: PanelProps) {
  return (
    <section className={`rounded-xl border border-line bg-surface shadow-panel ${className}`}>
      {(title || actions) && (
        <header className="flex flex-col gap-3 border-b border-line-soft px-5 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0">
            {title && <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">{title}</h2>}
            {description && <p className="mt-0.5 text-[13px] text-ink-3">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={flush ? '' : 'p-5'}>{children}</div>
    </section>
  )
}
