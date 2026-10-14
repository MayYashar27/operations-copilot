import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppProvider } from './app/AppProvider'
import { AppShell } from './components/layout/AppShell'
import { AgentsPage } from './features/agents/AgentsPage'
import { CopilotPage } from './features/copilot/CopilotPage'
import { OverviewPage } from './features/overview/OverviewPage'

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<OverviewPage />} />
            {/* Optional segments keep one mounted page (and its filters) while switching items. */}
            <Route path="agents/:agentId?" element={<AgentsPage />} />
            <Route path="copilot/:investigationId?" element={<CopilotPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AppProvider>
    </BrowserRouter>
  )
}
