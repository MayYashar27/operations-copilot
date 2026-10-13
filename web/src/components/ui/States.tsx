import { AlertCircle, RotateCw } from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-md bg-line-soft ${className}`} />
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
        <div className="mb-3 flex size-10 items-center justify-center rounded-lg border border-line bg-subtle">
          <Icon className="size-5 text-ink-3" strokeWidth={1.75} />
        </div>
      )}
      <p className="font-medium text-ink">{title}</p>
      {children && <div className="mt-1 max-w-md text-[13px] leading-relaxed text-ink-2">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
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
      <div className="mb-3 flex size-10 items-center justify-center rounded-lg border border-red-200 bg-red-50">
        <AlertCircle className="size-5 text-red-700" strokeWidth={1.75} />
      </div>
      <p className="font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-md text-[13px] leading-relaxed text-ink-2">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-secondary mt-4">
          <RotateCw className="size-3.5" /> Try again
        </button>
      )}
    </div>
  )
}
