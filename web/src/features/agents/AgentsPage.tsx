import { Users } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAppContext } from '../../app/context'
import type { AgentRow, ReportOverview } from '../../api/types'
import { useApi } from '../../api/useApi'
import { Workspace, WorkspaceHeader } from '../../components/layout/Workspace'
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States'
import { formatDateLong, pluralize } from '../../lib/format'
import { AgentDirectory, type DirectoryState } from './AgentDirectory'
import { AgentProfile } from './AgentProfile'
import { TeamComparison } from './TeamComparison'

/** /agents shows the team comparison; /agents/:agentId shows one profile. */
export function AgentsPage() {
  const { agentId } = useParams()
  const { date, reports } = useAppContext()
  const agents = useApi<AgentRow[]>(date ? `/reports/${date}/agents` : null)
  const overview = useApi<ReportOverview>(date && !agentId ? `/reports/${date}` : null)
  const [directory, setDirectory] = useState<DirectoryState>({ query: '', status: 'all', evidence: 'all', sort: 'attention' })

  const side = agents.status === 'success'
    ? <AgentDirectory rows={agents.data} state={directory} onChange={setDirectory} selectedId={agentId} />
    : <div className="p-5"><Skeleton className="mb-4 h-7 w-32" /><Skeleton className="h-11 w-full" /></div>

  let main
  if (reports.status === 'error') main = <ErrorState title="Could not load reports" message={reports.error.message} onRetry={reports.reload} />
  else if (!date) main = <EmptyState icon={Users} title="No saved report to show agents for" />
  else if (agentId) main = <AgentProfile key={agentId} agentId={agentId} date={date} />
  else if (agents.status === 'error') main = <ErrorState title="Could not load agents" message={agents.error.message} onRetry={agents.reload} />
  else if (agents.status === 'loading') main = <Skeleton className="h-[480px] rounded-[var(--radius-card)]" />
  else {
    main = (
      <>
        <WorkspaceHeader sideLabel="Agents" title="Agents"
          subtitle={`${pluralize(agents.data.length, 'agent')} screened · ${formatDateLong(date)} · select an agent for the full profile`} />
        <TeamComparison rows={agents.data} team={overview.status === 'success' ? overview.data.team_day_metrics : null} />
      </>
    )
  }

  return <Workspace side={side} scrollKey={agentId}>{main}</Workspace>
}
