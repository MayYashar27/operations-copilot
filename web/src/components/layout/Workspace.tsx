import { PanelLeftClose, PanelLeftOpen, X } from 'lucide-react'
import { createContext, useContext, useState, type ReactNode } from 'react'

interface WorkspaceState {
  hasSide: boolean
  sideOpen: boolean
  toggleSide: () => void
}

const WorkspaceContext = createContext<WorkspaceState>({ hasSide: false, sideOpen: false, toggleSide: () => {} })

interface WorkspaceProps {
  /** Optional contextual panel (shifts, agent directory, history). */
  side?: ReactNode
  children: ReactNode
}

/**
 * The layered workspace: [contextual side panel] + [main area].
 * Desktop: the side panel can be collapsed. Small screens: it opens as a drawer.
 */
export function Workspace({ side, children }: WorkspaceProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const isDesktop = () => window.matchMedia('(min-width: 1024px)').matches

  const state: WorkspaceState = {
    hasSide: Boolean(side),
    sideOpen: !collapsed,
    toggleSide: () => (isDesktop() ? setCollapsed((c) => !c) : setDrawerOpen(true)),
  }

  return (
    <WorkspaceContext.Provider value={state}>
      <div className="flex min-h-0 flex-1 gap-3">
        {side && !collapsed && (
          <aside className="hidden w-[304px] shrink-0 animate-fade flex-col overflow-hidden rounded-[var(--radius-pane)] bg-pane lg:flex">
            {side}
          </aside>
        )}

        <main className="scroll-soft relative min-w-0 flex-1 overflow-y-auto rounded-[var(--radius-pane)] bg-pane">
          {/* Soft lavender glow, echoing the reference's light, airy depth */}
          <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-72 bg-[radial-gradient(60%_100%_at_50%_100%,rgb(140_124_246/0.10),transparent)]" />
          <div className="relative mx-auto max-w-[1180px] animate-rise px-4 py-5 sm:px-6 lg:px-8 lg:py-7">{children}</div>
        </main>
      </div>

      {side && drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 animate-fade bg-ink/25 backdrop-blur-[2px]" onClick={() => setDrawerOpen(false)} />
          <aside className="absolute inset-y-2 left-2 flex w-[320px] max-w-[88vw] animate-rise flex-col overflow-hidden rounded-[var(--radius-pane)] bg-pane shadow-pop">
            <button type="button" onClick={() => setDrawerOpen(false)} aria-label="Close panel"
              className="absolute top-4 right-4 z-10 rounded-lg p-1.5 text-ink-3 hover:bg-hover hover:text-ink">
              <X className="size-4" />
            </button>
            <div className="flex min-h-0 flex-1 flex-col" onClick={(e) => (e.target as HTMLElement).closest('a') && setDrawerOpen(false)}>
              {side}
            </div>
          </aside>
        </div>
      )}
    </WorkspaceContext.Provider>
  )
}

interface WorkspaceHeaderProps {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  /** Label for the side-panel toggle on small screens, e.g. "Shifts". */
  sideLabel?: string
}

/** Compact page header: title, context line, actions; plus the side-panel toggle. */
export function WorkspaceHeader({ title, subtitle, actions, sideLabel = 'Panel' }: WorkspaceHeaderProps) {
  const { hasSide, sideOpen, toggleSide } = useContext(WorkspaceContext)

  return (
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        {hasSide && (
          <>
            <button type="button" onClick={toggleSide} className="icon-btn hidden lg:inline-flex"
              aria-label={sideOpen ? `Hide ${sideLabel.toLowerCase()}` : `Show ${sideLabel.toLowerCase()}`}>
              {sideOpen ? <PanelLeftClose className="size-[18px]" strokeWidth={1.8} /> : <PanelLeftOpen className="size-[18px]" strokeWidth={1.8} />}
            </button>
            <button type="button" onClick={toggleSide} className="icon-btn lg:hidden" aria-label={`Open ${sideLabel.toLowerCase()}`}>
              <PanelLeftOpen className="size-[18px]" strokeWidth={1.8} />
            </button>
          </>
        )}
        <div className="min-w-0">
          <h1 className="text-[22px] leading-tight font-semibold tracking-[-0.02em] text-ink">{title}</h1>
          {subtitle && <p className="mt-0.5 truncate text-[13px] text-ink-3">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}
