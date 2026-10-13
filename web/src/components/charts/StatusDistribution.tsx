import type { StatusCounts } from '../../api/types'
import { STATUS_META, STATUS_ORDER, TONE_CLASSES } from '../../lib/status'
import { StatusDot } from '../ui/StatusBadge'

/** Part-to-whole: one segmented bar plus a labelled legend (never color alone). */
export function StatusDistribution({ counts, total }: { counts: StatusCounts; total: number }) {
  const present = STATUS_ORDER.filter((status) => counts[status] > 0)

  return (
    <div>
      <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full bg-line-soft" role="img"
        aria-label={STATUS_ORDER.map((s) => `${STATUS_META[s].label}: ${counts[s]}`).join(', ')}>
        {present.map((status) => (
          <div
            key={status}
            title={`${STATUS_META[status].label}: ${counts[status]}`}
            className={`h-full first:rounded-l-full last:rounded-r-full ${TONE_CLASSES[STATUS_META[status].tone].fill}`}
            style={{ width: `${(counts[status] / Math.max(total, 1)) * 100}%` }}
          />
        ))}
      </div>

      <ul className="mt-4 divide-y divide-line-soft">
        {STATUS_ORDER.map((status) => {
          const count = counts[status]
          return (
            <li key={status} className="flex items-center gap-2.5 py-2">
              <StatusDot status={status} />
              <span className={`flex-1 text-[13px] ${count ? 'text-ink' : 'text-ink-3'}`}>{STATUS_META[status].label}</span>
              <span className={`text-[13px] font-semibold tabular ${count ? 'text-ink' : 'text-ink-3'}`}>{count}</span>
              <span className="w-10 text-right text-[12px] text-ink-3 tabular">
                {total ? Math.round((count / total) * 100) : 0}%
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
