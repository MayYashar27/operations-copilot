import { useCallback, useEffect, useState } from 'react'
import { ApiError, apiGet } from './client'
import type { InvestigationRecord } from './types'

const POLL_MS = 2500

/**
 * Load a saved investigation by ID. While it is still "running", poll until
 * it completes or fails. Reading never re-runs the AI.
 */
export function useInvestigation(id: string | null) {
  const [record, setRecord] = useState<InvestigationRecord | null>(null)
  const [failure, setFailure] = useState<{ id: string; error: ApiError } | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    const load = async () => {
      try {
        const next = await apiGet<InvestigationRecord>(`/copilot/investigations/${id}`)
        if (cancelled) return
        setRecord(next)
        setFailure(null)
        if (next.status === 'running') timer = setTimeout(load, POLL_MS)
      } catch (error) {
        if (!cancelled) setFailure({ id, error: error instanceof ApiError ? error : new ApiError(0, 'Unexpected error') })
      }
    }
    void load()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [id, attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  const current = record && record.id === id ? record : null
  const error = failure && failure.id === id ? failure.error : null
  return { record: current, error, loading: Boolean(id) && !current && !error, reload }
}

/** Seconds since an ISO timestamp, refreshed every second while `active`. */
export function useElapsed(since: string | null, active: boolean): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [active])
  return since ? Math.max(0, Math.round((now - new Date(since).getTime()) / 1000)) : 0
}
