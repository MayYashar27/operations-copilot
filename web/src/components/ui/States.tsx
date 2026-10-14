import { AlertCircle, RotateCw } from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-xl bg-skeleton ${className}`} />
}

interface MessageProps {
  icon?: ComponentType<{ className?: string; strokeWidth?: number }>
  title: string
  children?: ReactNode
  action?: ReactNode
}

/** Shown when a request worked but there is nothing to display. */
export function EmptyState({ icon: Icon, title, children, action }: MessageProps) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      {Icon && (
        <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-soft to-ai-bg">
          <Icon className="size-5 text-accent" strokeWidth={1.8} />
        </div>
      )}
      <p className="text-[14px] font-semibold text-ink">{title}</p>
      {children && <div className="mt-1.5 max-w-md text-[13px] leading-relaxed text-ink-2">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

/** Shown when a request failed. Always says what happened and offers a retry. */
export function ErrorState({ title = 'Something went wrong', message, onRetry }: {
  title?: string
  message: string
  onRetry?: () => void
}) {
  return (
    <div role="alert" className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-status-review-bg">
        <AlertCircle className="size-5 text-status-review" strokeWidth={1.8} />
      </div>
      <p className="text-[14px] font-semibold text-ink">{title}</p>
      <p className="mt-1.5 max-w-md text-[13px] leading-relaxed text-ink-2">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-secondary mt-5">
          <RotateCw className="size-3.5" /> Try again
        </button>
      )}
    </div>
  )
}
