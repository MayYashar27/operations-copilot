import { LayoutGrid, Lock, MessageSquareText, Users, Zap, type LucideIcon } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAppContext, useDatedLink } from '../../app/context'

const NAV_ITEMS: { to: string; label: string; icon: LucideIcon; end: boolean }[] = [
  { to: '/', label: 'Overview', icon: LayoutGrid, end: true },
  { to: '/agents', label: 'Agents', icon: Users, end: false },
  { to: '/copilot', label: 'Ask Copilot', icon: MessageSquareText, end: false },
]

export function BrandMark({ className = 'size-10' }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" aria-hidden className={`shrink-0 ${className}`}>
      <defs>
        <linearGradient id="brand-a" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#8c7cf6" />
          <stop offset="1" stopColor="#5b6cf0" />
        </linearGradient>
        <linearGradient id="brand-b" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#c7c0fb" />
          <stop offset="1" stopColor="#a5b0fa" />
        </linearGradient>
      </defs>
      <rect x="4" y="9" width="21" height="21" rx="7" transform="rotate(-12 14.5 19.5)" fill="url(#brand-b)" />
      <rect x="14" y="10" width="21" height="21" rx="7" transform="rotate(12 24.5 20.5)" fill="url(#brand-a)" opacity="0.92" />
    </svg>
  )
}

/** Hover label for an icon-only control. */
function RailTip({ label }: { label: string }) {
  return (
    <span className="pointer-events-none absolute top-1/2 left-full z-40 ml-3 -translate-x-1 -translate-y-1/2 rounded-lg bg-ink px-2.5 py-1.5 text-[12px] font-medium whitespace-nowrap text-white opacity-0 shadow-pop transition-all duration-150 group-hover:translate-x-0 group-hover:opacity-100">
      {label}
    </span>
  )
}

/** Narrow icon navigation. Horizontal on small screens, vertical from lg. */
export function Rail() {
  const datedLink = useDatedLink()
  const { config } = useAppContext()
  const live = config?.live_investigations_enabled ?? false

  return (
    <nav aria-label="Main"
      className="flex shrink-0 items-center gap-3 px-1 lg:w-[64px] lg:flex-col lg:px-0 lg:py-2">
      <div className="flex items-center gap-2 lg:mb-6 lg:flex-col">
        <BrandMark />
        <span className="text-[14px] font-bold tracking-[-0.01em] lg:sr-only">Operations Copilot</span>
      </div>

      <ul className="ml-auto flex gap-1 rounded-2xl bg-surface/60 p-1.5 shadow-card ring-1 ring-white/70 lg:my-auto lg:ml-0 lg:flex-col lg:gap-1.5">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <li key={to} className="group relative">
            <NavLink
              to={datedLink(to)}
              end={end}
              aria-label={label}
              className={({ isActive }) =>
                `flex size-10 items-center justify-center rounded-xl transition-all duration-200 lg:size-11 ${
                  isActive
                    ? 'bg-gradient-to-br from-accent to-accent-2 text-white shadow-accent'
                    : 'text-ink-3 hover:bg-surface hover:text-accent hover:shadow-card'
                }`
              }
            >
              <Icon className="size-[19px]" strokeWidth={1.9} />
            </NavLink>
            <span className="hidden lg:block"><RailTip label={label} /></span>
          </li>
        ))}
      </ul>

      <div className="group relative rounded-2xl bg-surface/60 p-1 shadow-card ring-1 ring-white/70 lg:p-1.5">
        <button
          type="button"
          aria-label={`${live ? 'Live mode' : 'Demo mode'}. About this data`}
          className={`flex size-9 items-center justify-center rounded-xl lg:size-11 ${live ? 'bg-status-clear-bg text-status-clear-ink' : 'text-ink-3 hover:text-accent'}`}
        >
          {live ? <Zap className="size-[18px]" strokeWidth={1.9} /> : <Lock className="size-[18px]" strokeWidth={1.9} />}
        </button>
        {/* Popover: opens on hover or keyboard focus. Mobile: below-left; desktop: beside the rail. */}
        <span role="tooltip"
          className="pointer-events-none absolute top-full right-0 z-40 mt-2 w-64 rounded-xl bg-ink p-3.5 text-white opacity-0 shadow-pop transition-all duration-150 group-focus-within:opacity-100 group-hover:opacity-100 lg:top-auto lg:right-auto lg:bottom-0 lg:left-full lg:mt-0 lg:ml-3">
          <span className="block text-[12.5px] font-semibold">{live ? 'Live mode' : 'Demo mode'}</span>
          <span className="mt-1 block text-[12px] leading-snug text-white/75">
            {live
              ? 'Copilot can run new AI investigations from this machine.'
              : 'Read-only. Saved AI results on synthetic data; no AI calls are made.'}
          </span>
          {config && (
            <span className="mt-2.5 block border-t border-white/15 pt-2.5 text-[11.5px] leading-snug text-white/60">
              {config.disclaimer}
            </span>
          )}
        </span>
      </div>
    </nav>
  )
}
