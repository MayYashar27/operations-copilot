import type { ScreeningStatus } from '../../api/types'
import { STATUS_META, TONE_CLASSES } from '../../lib/status'

/** A compact identity mark for an agent, with a status dot. Never a face or a score. */
export function AgentMonogram({ id, status, size = 'md' }: { id: string; status?: ScreeningStatus; size?: 'md' | 'lg' }) {
  const box = size === 'lg' ? 'size-14 text-[17px] rounded-2xl' : 'size-10 text-[12.5px] rounded-xl'
  return (
    <span className={`relative inline-flex shrink-0 items-center justify-center border border-line bg-subtle font-semibold text-ink-2 tabular ${box}`}>
      {id}
      {status && (
        <span aria-hidden
          className={`absolute -right-0.5 -bottom-0.5 size-3 rounded-full border-2 border-surface ${TONE_CLASSES[STATUS_META[status].tone].dot}`} />
      )}
    </span>
  )
}
