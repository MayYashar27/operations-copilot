import { useCallback, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { AppConfig, ReportListItem } from '../api/types'
import { useApi } from '../api/useApi'
import { AppContext } from './context'

/** Loads what every page needs: server config and the list of saved reports. */
export function AppProvider({ children }: { children: ReactNode }) {
  const config = useApi<AppConfig>('/config')
  const reports = useApi<ReportListItem[]>('/reports')
  const [params, setParams] = useSearchParams()

  const newest = reports.status === 'success' ? (reports.data[0]?.date ?? null) : null
  const date = params.get('date') ?? newest

  const setDate = useCallback(
    (next: string) =>
      setParams((current) => {
        const updated = new URLSearchParams(current)
        updated.set('date', next)
        return updated
      }),
    [setParams],
  )

  // Retrying after the API was down should recover the config too.
  const { reload: reloadConfig } = config
  const { reload: reloadReports } = reports
  const reloadAll = useCallback(() => {
    reloadConfig()
    reloadReports()
  }, [reloadConfig, reloadReports])

  return (
    <AppContext.Provider
      value={{
        config: config.status === 'success' ? config.data : null,
        reports: { ...reports, reload: reloadAll },
        date,
        setDate,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}
