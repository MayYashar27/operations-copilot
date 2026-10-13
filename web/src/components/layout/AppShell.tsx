import { Menu } from 'lucide-react'
import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAppContext } from '../../app/context'
import { BrandMark, Sidebar } from './Sidebar'

/** Sidebar + content area. On small screens the sidebar becomes a drawer. */
export function AppShell() {
  const location = useLocation()
  const { config } = useAppContext()

  // The drawer remembers the page it was opened on, so navigating closes it.
  const [openedOn, setOpenedOn] = useState<string | null>(null)
  const menuOpen = openedOn === location.pathname
  const setMenuOpen = (open: boolean) => setOpenedOn(open ? location.pathname : null)

  return (
    <div className="min-h-screen">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-line bg-canvas lg:block">
        <Sidebar />
      </aside>

      {/* Mobile top bar + drawer */}
      <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-canvas/90 px-4 backdrop-blur lg:hidden">
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          className="-ml-1 rounded-md p-1.5 text-ink-2 hover:bg-hover"
          aria-label="Open menu"
        >
          <Menu className="size-5" />
        </button>
        <BrandMark />
        <span className="text-[14px] font-semibold">Operations Copilot</span>
      </header>
      {menuOpen && (
        <div className="fixed inset-0 z-30 lg:hidden">
          <div className="absolute inset-0 bg-ink/20" onClick={() => setMenuOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] border-r border-line bg-canvas shadow-pop">
            <Sidebar onClose={() => setMenuOpen(false)} />
          </aside>
        </div>
      )}

      <main className="lg:pl-60">
        <div className="mx-auto max-w-[1180px] px-4 pt-6 pb-16 sm:px-6 lg:px-10 lg:pt-10">
          <Outlet />
          {config && (
            <footer className="mt-12 border-t border-line pt-5 text-[12px] leading-relaxed text-ink-3">
              {config.disclaimer}
            </footer>
          )}
        </div>
      </main>
    </div>
  )
}
