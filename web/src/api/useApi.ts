import { useCallback, useEffect, useState } from 'react'
import { ApiError, apiGet } from './client'

type Settled<T> = { status: 'error'; error: ApiError } | { status: 'success'; data: T }

export type ApiState<T> = { status: 'loading' } | Settled<T>

/**
 * Fetch a read-only API resource. Re-fetches when `path` changes; pass null
 * to wait (e.g. until a report date is known). Read endpoints never call
 * Claude, so refetching is always cheap and safe.
 */
export function useApi<T>(path: string | null): ApiState<T> & { reload: () => void } {
  const [attempt, setAttempt] = useState(0)
  // Each result remembers which request produced it. "Loading" is derived:
  // there is simply no result yet for the current path + attempt.
  const [result, setResult] = useState<{ key: string; state: Settled<T> } | null>(null)
  const key = `${path}#${attempt}`

  useEffect(() => {
    if (path === null) return
    const controller = new AbortController()

    apiGet<T>(path, controller.signal)
      .then((data) => setResult({ key, state: { status: 'success', data } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const apiError = error instanceof ApiError ? error : new ApiError(0, 'Unexpected error')
        setResult({ key, state: { status: 'error', error: apiError } })
      })

    return () => controller.abort()
  }, [path, key])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  const state: ApiState<T> = result?.key === key ? result.state : { status: 'loading' }
  return { ...state, reload }
}
