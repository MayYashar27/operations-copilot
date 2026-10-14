import { Gauge, Lock, MessageSquareText, Users, X, Zap } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAppContext, useDatedLink } from '../../app/context'
import { formatDateShort } from '../../lib/format'

const NAV_ITEMS = [
  { to: '/', label: 'Overview', hint: 'Understand the shift', icon: Gauge, end: true },
  { to: '/agents', label: 'Agents', hint: 'What needs attention', icon: Users, end: false },
  { to: '/copilot', label: 'Ask Copilot', hint: 'Investigate questions', icon: MessageSquareText, end: false },
]

export function BrandMark({ className = 'size-8' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={`shrink-0 ${className}`}>
      <rect width="32" height="32" rx="9" className="fill-canvas" />
      <path d="M9.5 21.5V15m6.5 6.5V10m6.5 11.5v-4" className="stroke-night" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="22.5" cy="11.5" r="2.2" className="fill-accent" />
    </svg>
  )
}

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const datedLink = useDatedLink()
  const { date } = useAppContext()

  return (
    <div className="flex h-full flex-col bg-night text-night-ink">
      <div className="flex h-[68px] items-center gap-3 px-5">
        <BrandMark />
        <div className="min-w-0 leading-tight">
          <p className="text-[14.5px] font-semibold tracking-[-0.01em]">Operations Copilot</p>
          <p className="text-[12px] text-night-ink-3">Service center workspace</p>
        </div>
        {onClose && (
          <button type="button" onClick={onClose} aria-label="Close menu"
            className="ml-auto rounded-md p-1.5 text-night-ink-2 hover:bg-night-2">
            <X className="size-4" />
          </button>
        )}
      </div>

      <nav className="flex-1 px-3 pt-4" aria-label="Main">
        <ul className="space-y-1">
          {NAV_ITEMS.map(({ to, label, hint, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={datedLink(to)}
                end={end}
                onClick={onClose}
                className={({ isActive }) =>
                  `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors ${
                    isActive ? 'bg-night-2 text-white' : 'text-night-ink-2 hover:bg-night-2/60 hover:text-night-ink'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      aria-hidden
                      className={`absolute top-1/2 left-0 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-accent transition-opacity ${
                        isActive ? 'opacity-100' : 'opacity-0'
                      }`}
                    />
                    <Icon className="size-[18px] shrink-0" strokeWidth={1.9} />
                    <span className="min-w-0">
                      <span className="block text-[13.5px] font-medium">{label}</span>
                      <span className={`block text-[11.5px] ${isActive ? 'text-night-ink-2' : 'text-night-ink-3'}`}>{hint}</span>
                    </span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {date && (
        <div className="mx-5 mb-3 border-t border-night-line pt-4">
          <p className="text-[11px] font-semibold tracking-[0.08em] text-night-ink-3 uppercase">Viewing shift</p>
          <p className="mt-1 text-[13px] font-medium tabular">{formatDateShort(date)}</p>
        </div>
      )}
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
    <div className="m-3 rounded-xl bg-night-2 p-3.5">
      <div className="flex items-center gap-2">
        <span className={`flex size-5 items-center justify-center rounded-md ${live ? 'bg-status-clear/20' : 'bg-night-line'}`}>
          {live ? <Zap className="size-3 text-night-good" /> : <Lock className="size-3 text-night-ink-2" />}
        </span>
        <p className="text-[12.5px] font-semibold">{live ? 'Live mode' : 'Demo mode'}</p>
      </div>
      <p className="mt-1.5 text-[12px] leading-snug text-night-ink-3">
        {live
          ? 'Copilot can run new AI investigations on this machine.'
          : 'Read-only. Saved AI results on synthetic data; no AI calls are made.'}
      </p>
    </div>
  )
}
