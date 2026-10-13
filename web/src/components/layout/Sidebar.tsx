import { LayoutDashboard, Lock, Users, X, Zap } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAppContext, useDatedLink } from '../../app/context'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/agents', label: 'Agents', icon: Users, end: false },
]

export function BrandMark() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className="size-7 shrink-0">
      <rect width="32" height="32" rx="8" className="fill-ink" />
      <path d="M9 21.5V14m7 7.5V10m7 11.5v-5" stroke="white" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  )
}

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const datedLink = useDatedLink()

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center gap-2.5 px-5">
        <BrandMark />
        <div className="min-w-0 leading-tight">
          <p className="text-[14px] font-semibold tracking-[-0.01em] text-ink">Operations Copilot</p>
          <p className="text-[11.5px] text-ink-3">Service center</p>
        </div>
        {onClose && (
          <button type="button" onClick={onClose} className="ml-auto rounded-md p-1.5 text-ink-3 hover:bg-hover" aria-label="Close menu">
            <X className="size-4" />
          </button>
        )}
      </div>

      <nav className="flex-1 px-3 pt-2" aria-label="Main">
        <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-[0.06em] text-ink-3">Workspace</p>
        <ul className="space-y-0.5">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={datedLink(to)}
                end={end}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex h-8 items-center gap-2.5 rounded-lg px-2 text-[13.5px] font-medium transition-colors ${
                    isActive ? 'bg-surface text-ink shadow-panel ring-1 ring-line' : 'text-ink-2 hover:bg-hover hover:text-ink'
                  }`
                }
              >
                <Icon className="size-4 shrink-0" strokeWidth={2} />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <ModeIndicator />
    </div>
  )
}

/** Tells the user whether this server can run paid AI investigations. */
function ModeIndicator() {
  const { config } = useAppContext()
  if (!config) return null

  const live = config.live_investigations_enabled
  return (
    <div className="m-3 rounded-lg border border-line bg-surface p-3">
      <div className="flex items-center gap-2">
        {live ? <Zap className="size-3.5 text-status-clear" /> : <Lock className="size-3.5 text-ink-3" />}
        <p className="text-[12.5px] font-semibold text-ink">{live ? 'Live mode' : 'Demo mode'}</p>
      </div>
      <p className="mt-1 text-[12px] leading-snug text-ink-3">
        {live
          ? 'New AI investigations can be run from agent pages.'
          : 'Read-only. Showing saved AI results on synthetic data.'}
      </p>
    </div>
  )
}
