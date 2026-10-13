import type { ScreeningStatus } from '../../api/types'
import { STATUS_META, TONE_CLASSES } from '../../lib/status'

export function StatusDot({ status, className = '' }: { status: ScreeningStatus; className?: string }) {
  const tone = TONE_CLASSES[STATUS_META[status].tone]
  return <span aria-hidden className={`inline-block size-2 shrink-0 rounded-full ${tone.dot} ${className}`} />
}

export function StatusBadge({ status, compact = false }: { status: ScreeningStatus; compact?: boolean }) {
  const meta = STATUS_META[status]
  const tone = TONE_CLASSES[meta.tone]
  return (
    <span
      title={meta.description}
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ${tone.badge}`}
    >
      <StatusDot status={status} className="size-1.5" />
      {compact ? meta.short : meta.label}
    </span>
  )
}
