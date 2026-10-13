import { createContext, useCallback, useContext } from 'react'
import type { AppConfig, ReportListItem } from '../api/types'
import type { ApiState } from '../api/useApi'

export interface AppContextValue {
  config: AppConfig | null
  reports: ApiState<ReportListItem[]> & { reload: () => void }
  /** Selected report date: from ?date=, else the newest saved report. */
  date: string | null
  setDate: (date: string) => void
}

export const AppContext = createContext<AppContextValue | null>(null)

export function useAppContext(): AppContextValue {
  const value = useContext(AppContext)
  if (!value) throw new Error('useAppContext must be used inside <AppProvider>')
  return value
}

/** Build an in-app link that keeps the selected report date. */
export function useDatedLink() {
  const { date } = useAppContext()
  return useCallback((path: string) => (date ? `${path}?date=${date}` : path), [date])
}
