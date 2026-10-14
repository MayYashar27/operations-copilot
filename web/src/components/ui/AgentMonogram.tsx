import type { ScreeningStatus } from '../../api/types'
import { STATUS_META, TONE_CLASSES } from '../../lib/status'

/** A compact identity mark for an agent, with a status dot. Never a face or a score. */
export function AgentMonogram({ id, status, size = 'md' }: { id: string; status?: ScreeningStatus; size?: 'md' | 'lg' }) {
  const box = size === 'lg' ? 'size-14 text-[16px] rounded-2xl' : 'size-10 text-[12px] rounded-xl'
  return (
    <span className={`relative inline-flex shrink-0 items-center justify-center bg-gradient-to-br from-accent-soft to-ai-bg font-bold text-accent-strong tabular ${box}`}>
      {id}
      {status && (
        <span aria-hidden
          className={`absolute -right-0.5 -bottom-0.5 size-3 rounded-full ring-2 ring-surface ${TONE_CLASSES[STATUS_META[status].tone].dot}`} />
      )}
    </span>
  )
}
