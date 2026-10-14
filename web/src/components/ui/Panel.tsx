import type { ReactNode } from 'react'

interface PanelProps {
  title?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  children: ReactNode
  /** Remove body padding, e.g. for edge-to-edge lists. */
  flush?: boolean
  className?: string
}

/** The standard white card. Headers sit inside the card without a divider. */
export function Panel({ title, description, actions, children, flush, className = '' }: PanelProps) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="px-5 pt-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            {title && <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">{title}</h2>}
            {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
          </div>
          {description && <p className="mt-1 text-[12.5px] leading-relaxed text-ink-3">{description}</p>}
        </header>
      )}
      <div className={flush ? 'pt-3' : 'p-5 pt-4'}>{children}</div>
    </section>
  )
}
