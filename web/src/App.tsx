import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppProvider } from './app/AppProvider'
import { AppShell } from './components/layout/AppShell'
import { ComingSoon } from './features/ComingSoon'
import { OverviewPage } from './features/overview/OverviewPage'

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<OverviewPage />} />
            <Route path="agents" element={<ComingSoon title="Agents" />} />
            <Route path="agents/:agentId" element={<ComingSoon title="Agent detail" />} />
            <Route path="copilot" element={<ComingSoon title="Ask Copilot" />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AppProvider>
    </BrowserRouter>
  )
}
