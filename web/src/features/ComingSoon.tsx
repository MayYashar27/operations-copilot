import { ArrowLeft, Construction } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useDatedLink } from '../app/context'
import { Workspace, WorkspaceHeader } from '../components/layout/Workspace'
import { EmptyState } from '../components/ui/States'

/** Temporary placeholder for screens being redesigned next. */
export function ComingSoon({ title }: { title: string }) {
  const { agentId } = useParams()
  const [params] = useSearchParams()
  const question = params.get('q')
  const datedLink = useDatedLink()

  return (
    <Workspace>
      <WorkspaceHeader title={agentId ? `Agent ${agentId}` : title} />
      <div className="card">
        <EmptyState
          icon={Construction}
          title={`${title} is being redesigned next`}
          action={
            <Link to={datedLink('/')} className="btn-secondary">
              <ArrowLeft className="size-3.5" /> Back to overview
            </Link>
          }
        >
          {question && <p>Pre-filled question: <span className="text-ink">“{question}”</span></p>}
        </EmptyState>
      </div>
    </Workspace>
  )
}
