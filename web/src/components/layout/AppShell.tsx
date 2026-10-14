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

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 lg:block">
        <Sidebar />
      </aside>

      <header className="sticky top-0 z-20 flex h-14 items-center gap-3 bg-night px-4 text-night-ink lg:hidden">
        <button type="button" onClick={() => setOpenedOn(location.pathname)} aria-label="Open menu"
          className="-ml-1 rounded-md p-1.5 text-night-ink-2 hover:bg-night-2">
          <Menu className="size-5" />
        </button>
        <BrandMark className="size-7" />
        <span className="text-[14px] font-semibold">Operations Copilot</span>
      </header>
      {menuOpen && (
        <div className="fixed inset-0 z-30 lg:hidden">
          <div className="absolute inset-0 animate-fade bg-night/40" onClick={() => setOpenedOn(null)} />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] animate-fade shadow-pop">
            <Sidebar onClose={() => setOpenedOn(null)} />
          </aside>
        </div>
      )}

      <main className="lg:pl-64">
        {/* key: replay the entrance animation on each page change */}
        <div key={location.pathname} className="mx-auto max-w-[1240px] animate-rise px-4 pt-6 pb-16 sm:px-6 lg:px-10 lg:pt-10">
          <Outlet />
          {config && (
            <footer className="mt-14 border-t border-line pt-5 text-[12px] leading-relaxed text-ink-3">
              {config.disclaimer}
            </footer>
          )}
        </div>
      </main>
    </div>
  )
}
